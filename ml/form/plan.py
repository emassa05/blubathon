"""The order the form asks in (SPEC 6.9, 6.10).

Six blocks, in this order: the pending outcome, the questions that are overdue,
one exploration slot, VoI, canonical order to fill the remaining slots, and then
the full queue.

Two rules matter more than the ordering itself. Every applicable field stays
reachable, so highlighting is about attention, not access (INV-10). And a field
stops being overdue when it was either highlighted in a session whose source
allowed it, or actually answered there: sitting in the tail does not reset the
clock, but an answer does.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

from ml.spec_constants import (
    DEFAULT_WINDOW_DAYS,
    EXPLORATION_WEEKDAY_MODULUS,
    FORM_HIGHLIGHTED_DEFAULT,
    FORM_HIGHLIGHTED_LOW_COVERAGE,
    FORM_MAX_MONITORED_HIGHLIGHTS,
    LOW_COVERAGE_THRESHOLD,
    STALENESS_CEILING_DAYS,
)
from packages.shared.canonical import in_window, inclusive_window, stable_bucket
from packages.shared.domain.observation import FieldObservation, QuestionPresentation
from packages.shared.domain.prediction import VoiEstimate
from packages.shared.enums import FieldCode, QuestionReason, Source, VoiStatus
from packages.shared.field_catalog import (
    CANONICAL_FIELD_ORDER,
    FIELD_CATALOG,
    MONITORED_FIELD_PRIORITY,
    MONITORED_FIELDS,
    applicable_fields,
)
from packages.shared.projection import project_as_of

# Fields outside the monitored list have no declared priority; they sort after
# every monitored field and then by field code (SPEC 6.10).
UNRANKED_PRIORITY = len(MONITORED_FIELDS) + 1


@dataclass(frozen=True, slots=True)
class PlannedQuestion:
    """One field in the plan and why it is there."""

    field_code: FieldCode
    reason: QuestionReason
    highlighted: bool
    voi: VoiEstimate | None = None
    days_since_presented: int | None = None


@dataclass(frozen=True, slots=True)
class FormPlan:
    """Highlighted questions, the full tail, and the slots that produced them."""

    highlighted: tuple[PlannedQuestion, ...]
    tail: tuple[PlannedQuestion, ...]
    base_slots: int
    outcome_pending: bool
    exploration_weekday: int
    exploration_field: FieldCode | None
    voi_status: VoiStatus

    @property
    def field_codes(self) -> tuple[FieldCode, ...]:
        return tuple(question.field_code for question in self.highlighted + self.tail)


def base_slots_for(coverage: float) -> int:
    """Three slots while coverage is below the low-coverage threshold, else two."""

    return (
        FORM_HIGHLIGHTED_LOW_COVERAGE
        if coverage < LOW_COVERAGE_THRESHOLD
        else FORM_HIGHLIGHTED_DEFAULT
    )


def _priority(field_code: FieldCode) -> int:
    return MONITORED_FIELD_PRIORITY.get(field_code, UNRANKED_PRIORITY)


def _tie_break(field_code: FieldCode) -> tuple[int, str]:
    return (_priority(field_code), str(field_code))


def last_highlighted_dates(
    presentations: Iterable[QuestionPresentation], *, cutoff: datetime
) -> dict[FieldCode, date]:
    """Most recent day each field was actually highlighted.

    Only highlighted presentations count, and only from a session whose source
    allowed the field (SPEC 6.10).
    """

    latest: dict[FieldCode, date] = {}
    for row in project_as_of(presentations, cutoff).leaves:
        if not row.highlighted:
            continue
        if not FIELD_CATALOG[row.field_code].allows(row.source):
            continue
        current = latest.get(row.field_code)
        if current is None or row.local_date > current:
            latest[row.field_code] = row.local_date
    return latest


def last_answered_dates(
    observations: Iterable[FieldObservation], *, cutoff: datetime
) -> dict[FieldCode, date]:
    """Most recent day each field actually carried an answer.

    A presentation says the question was put; an observation says it was
    answered. Answering is the stronger signal of the two, and it is the one a
    caregiver means by "ya lo registré", so it resets the same clock.
    """

    latest: dict[FieldCode, date] = {}
    for row in project_as_of(observations, cutoff).leaves:
        if row.value is None:
            continue
        if not FIELD_CATALOG[row.field_code].allows(row.source):
            continue
        current = latest.get(row.field_code)
        if current is None or row.local_date > current:
            latest[row.field_code] = row.local_date
    return latest


def _staleness_order(
    candidates: Sequence[FieldCode],
    *,
    last_seen: Mapping[FieldCode, date],
    today: date,
) -> list[tuple[FieldCode, int | None]]:
    """Never-asked first, then most days since the last presentation.

    A never-asked field sorts ahead of every asked one, so the first session
    follows the declared priority exactly.
    """

    scored = [
        (
            field_code,
            None if field_code not in last_seen else (today - last_seen[field_code]).days,
        )
        for field_code in candidates
    ]
    return sorted(
        scored,
        key=lambda item: (
            0 if item[1] is None else 1,
            -(item[1] or 0),
            *_tie_break(item[0]),
        ),
    )


def exploration_weekday(
    *,
    secret: bytes,
    tenant_id: UUID,
    subject_id: UUID,
    iso_week: str,
    policy_version: str,
) -> int:
    """One weekday per ISO week, chosen by HMAC (SPEC 6.10).

    A week whose chosen weekday has no session is simply not compensated, which
    is why the frequency is approximately, not exactly, one in seven.
    """

    return stable_bucket(
        secret,
        [str(tenant_id), str(subject_id), iso_week, policy_version],
        EXPLORATION_WEEKDAY_MODULUS,
    )


def _exploration_pick(
    candidates: Sequence[FieldCode],
    *,
    presentations: Iterable[QuestionPresentation],
    cutoff: datetime,
    today: date,
    window_days: int = DEFAULT_WINDOW_DAYS,
) -> FieldCode | None:
    """The least highlighted applicable field over the inclusive 60-day window."""

    if not candidates:
        return None
    window = inclusive_window(today, window_days)
    counts = dict.fromkeys(candidates, 0)
    for row in project_as_of(presentations, cutoff).leaves:
        if row.highlighted and row.field_code in counts and in_window(row.local_date, window):
            counts[row.field_code] += 1
    return min(candidates, key=lambda field_code: (counts[field_code], *_tie_break(field_code)))


def build_form_plan(
    *,
    source: Source,
    today: date,
    cutoff: datetime,
    coverage: float,
    outcome_pending: bool,
    presentations: Iterable[QuestionPresentation] = (),
    observations: Iterable[FieldObservation] = (),
    answered_fields: frozenset[FieldCode] = frozenset(),
    voi: Mapping[FieldCode, VoiEstimate] | None = None,
    exploration_secret: bytes = b"",
    tenant_id: UUID | None = None,
    subject_id: UUID | None = None,
    policy_version: str = "",
    staleness_ceiling_days: int = STALENESS_CEILING_DAYS,
) -> FormPlan:
    """Build the plan for one session, in the exact SPEC 6.9 order.

    Recalculating after an answer keeps the already-answered fields out of the
    plan and never presents the same question twice in one session.
    """

    presentation_rows = list(presentations)
    voi_map = dict(voi or {})

    applicable = [
        field_code for field_code in applicable_fields(source) if field_code not in answered_fields
    ]
    available = set(applicable)
    base_slots = base_slots_for(coverage)

    last_seen = last_highlighted_dates(presentation_rows, cutoff=cutoff)
    for field_code, answered_on in last_answered_dates(observations, cutoff=cutoff).items():
        current = last_seen.get(field_code)
        if current is None or answered_on > current:
            last_seen[field_code] = answered_on
    monitored = [field_code for field_code in MONITORED_FIELDS if field_code in available]
    ordered_monitored = _staleness_order(monitored, last_seen=last_seen, today=today)

    selected: list[PlannedQuestion] = []
    chosen: set[FieldCode] = set()

    # 2. Overdue questions. Every field at or past the ceiling is included even
    #    when that expands the usual two or three slots, capped by the number of
    #    monitored fields there are.
    for field_code, days_since in ordered_monitored:
        overdue = days_since is None or days_since >= staleness_ceiling_days
        if not overdue or len(selected) >= FORM_MAX_MONITORED_HIGHLIGHTS:
            continue
        selected.append(
            PlannedQuestion(
                field_code=field_code,
                reason=QuestionReason.STALENESS,
                highlighted=True,
                voi=voi_map.get(field_code),
                days_since_presented=days_since,
            )
        )
        chosen.add(field_code)

    # 3. Exploration takes at most one remaining slot and never displaces an
    #    overdue field.
    weekday = -1
    exploration_field: FieldCode | None = None
    if exploration_secret and tenant_id is not None and subject_id is not None:
        iso_year, iso_week_number, iso_weekday = today.isocalendar()
        weekday = exploration_weekday(
            secret=exploration_secret,
            tenant_id=tenant_id,
            subject_id=subject_id,
            iso_week=f"{iso_year:04d}-W{iso_week_number:02d}",
            policy_version=policy_version,
        )
        if (iso_weekday - 1) == weekday and len(selected) < base_slots:
            exploration_field = _exploration_pick(
                [field_code for field_code in applicable if field_code not in chosen],
                presentations=presentation_rows,
                cutoff=cutoff,
                today=today,
            )
            if exploration_field is not None:
                selected.append(
                    PlannedQuestion(
                        field_code=exploration_field,
                        reason=QuestionReason.EXPLORATION,
                        highlighted=True,
                        voi=voi_map.get(exploration_field),
                    )
                )
                chosen.add(exploration_field)

    # 4. VoI fills remaining slots, descending, ties by priority and field code.
    available_voi = [
        (field_code, estimate)
        for field_code, estimate in voi_map.items()
        if field_code in available
        and field_code not in chosen
        and estimate.status is VoiStatus.AVAILABLE
        and estimate.voi_nats is not None
    ]
    for field_code, estimate in sorted(
        available_voi,
        key=lambda item: (-(item[1].voi_nats or 0.0), *_tie_break(item[0])),
    ):
        if len(selected) >= base_slots:
            break
        selected.append(
            PlannedQuestion(
                field_code=field_code,
                reason=QuestionReason.VOI,
                highlighted=True,
                voi=estimate,
            )
        )
        chosen.add(field_code)

    # 5. Canonical catalogue order fills whatever is left.
    for field_code in applicable:
        if len(selected) >= base_slots:
            break
        if field_code in chosen:
            continue
        selected.append(
            PlannedQuestion(
                field_code=field_code,
                reason=QuestionReason.CANONICAL_ORDER,
                highlighted=True,
                voi=voi_map.get(field_code),
            )
        )
        chosen.add(field_code)

    # 6. The full queue. Every applicable field stays reachable.
    tail = tuple(
        PlannedQuestion(
            field_code=field_code,
            reason=QuestionReason.TAIL,
            highlighted=False,
            voi=voi_map.get(field_code),
        )
        for field_code in CANONICAL_FIELD_ORDER
        if field_code in available and field_code not in chosen
    )

    statuses = {estimate.status for estimate in voi_map.values()}
    if VoiStatus.AVAILABLE in statuses:
        voi_status = VoiStatus.AVAILABLE
    elif statuses:
        voi_status = sorted(statuses, key=str)[0]
    else:
        voi_status = VoiStatus.UNAVAILABLE_MODEL

    return FormPlan(
        highlighted=tuple(selected),
        tail=tail,
        base_slots=base_slots,
        outcome_pending=outcome_pending,
        exploration_weekday=weekday,
        exploration_field=exploration_field,
        voi_status=voi_status,
    )
