"""Translate Bluba platform exports into canonical DailyLog records (SPEC 2.1).

Bluba captures the same clinical reality with a smaller, categorical vocabulary:
three sleep states instead of a 1-5 scale, a day-level regulation summary instead
of an episode count. The 15 canonical fields do not change; this module is the
only place where Bluba wording becomes canonical values, so the mapping stays
auditable in one file instead of scattered across ingestion code.

Pure by CONVENTIONS section 2: it receives already-parsed rows and returns
dictionaries. Reading the CSV files is the caller's job (apps/api/store).
"""

from __future__ import annotations

import hashlib
from collections import defaultdict
from collections.abc import Iterable, Mapping
from typing import Any

from ml.errors import ContractViolationError
from ml.spec_constants import DYSREGULATION_EVENTS_MAX, MEDICATION_ADHERENCE_VALUES, TEXT_MAX_LENGTH

_UUID_NAMESPACE = "faro.bluba"

# Bluba wording -> canonical 1-5 value. Every level Bluba distinguishes keeps a
# distinct canonical value; levels Bluba does not use simply never appear.
BLUBA_SLEEP_QUALITY = {
    "Reparador": 5,
    "Interrumpido": 3,
    "Dificultad de Conciliación": 2,
}
BLUBA_WAKE_STATE = {
    "Tranquilo/Alegre": 5,
    "Cansado/Con Sueño": 3,
    "Irritable/Llorando": 1,
}
BLUBA_GI_STATUS = {
    "Normal": 5,
    "Estreñimiento": 3,
    "Diarrea": 2,
}
BLUBA_MEDICATION_ADHERENCE = {
    "Sí": MEDICATION_ADHERENCE_VALUES[0],
    "Si": MEDICATION_ADHERENCE_VALUES[0],
    "No": MEDICATION_ADHERENCE_VALUES[1],
    "No Aplica": MEDICATION_ADHERENCE_VALUES[2],
}
# The tutor day-level summary is a coarse read of the minor-episode count.
BLUBA_REGULATION_EVENTS = {
    "Excelente": 0,
    "Estable con Apoyo": 1,
    "Desregulación Frecuente": 4,
}
# Session alertness, reported by a professional at session start and end.
BLUBA_ALERTNESS = {
    "Bajo (Letárgico)": 1,
    "Calmado": 2,
    "Óptimo (Regulado)": 3,
    "Alto (Sobreexcitado)": 5,
}
BLUBA_ATTENDANCE_PARTICIPATION = {
    "Presente": 4,
    "Ausente": None,
}
# SPEC section 3: only a major event counts as crisis_occurred. Bluba grades
# intensity on a 1-10 scale bucketed into three labels.
BLUBA_SEVERE_INTENSITY = "Severa (8-10)"

_EVENT_ENRICHED_FIELDS = (
    "dysregulation_events",
    "observed_behavior_tags",
    "relevant_event_flag",
    "relevant_events_note",
    "other_notes",
    "crisis_occurred",
)
_DAILY_PROVENANCE_FIELDS = (
    "sleep_quality",
    "wake_state",
    "gi_status",
    "medication_adherence",
    *_EVENT_ENRICHED_FIELDS,
)


def deterministic_uuid4(*parts: str) -> str:
    """Derive a stable RFC-4122 version 4 UUID from text, for reproducible ids.

    Bluba identifies cases as ``PAC-001`` while the contract requires UUID4.
    Hashing keeps two runs byte-identical (SPEC rule 0.9) without inventing
    randomness that would change between seedings.
    """
    payload = "|".join((_UUID_NAMESPACE, *parts)).encode("utf-8")
    digest = bytearray(hashlib.sha256(payload).digest()[:16])
    digest[6] = (digest[6] & 0x0F) | 0x40
    digest[8] = (digest[8] & 0x3F) | 0x80
    raw = digest.hex()
    return f"{raw[:8]}-{raw[8:12]}-{raw[12:16]}-{raw[16:20]}-{raw[20:32]}"


def _lookup(table: Mapping[str, Any], raw: object, field: str) -> Any:
    if raw is None or not str(raw).strip():
        return None
    value = str(raw).strip()
    if value not in table:
        raise ContractViolationError(f"unmapped Bluba value for {field}: {value!r}")
    return table[value]


def _behavior_tag(intensity: str) -> str:
    """SPEC section 2.2. A severe event is a meltdown by the operational
    definition of section 3; lighter events are recorded as irritability."""
    return "meltdown" if intensity == BLUBA_SEVERE_INTENSITY else "irritable"


def _empty_day() -> dict[str, Any]:
    return {
        "dysregulation_events": None,
        "observed_behavior_tags": [],
        "relevant_event_flag": None,
        "relevant_events_note": None,
        "other_notes": None,
        "crisis_occurred": None,
    }


def _join(existing: str | None, addition: str) -> str:
    return addition if not existing else f"{existing} | {addition}"


def _truncate(text: str | None) -> str | None:
    if text is None:
        return None
    return text if len(text) <= TEXT_MAX_LENGTH else f"{text[: TEXT_MAX_LENGTH - 1]}…"


def _summarise_events(
    event_rows: Iterable[Mapping[str, Any]],
) -> dict[tuple[str, str], dict[str, Any]]:
    """Collapse the event log into one contribution per case and day."""
    by_day: dict[tuple[str, str], dict[str, Any]] = defaultdict(_empty_day)
    for event in event_rows:
        case_id = str(event["id_caso"]).strip()
        day = str(event["fecha_hora"]).strip()[:10]
        intensity = str(event.get("intensidad") or "").strip()
        entry = by_day[(case_id, day)]
        entry["dysregulation_events"] = min(
            DYSREGULATION_EVENTS_MAX, (entry["dysregulation_events"] or 0) + 1
        )
        entry["relevant_event_flag"] = True
        tag = _behavior_tag(intensity)
        if tag not in entry["observed_behavior_tags"]:
            entry["observed_behavior_tags"].append(tag)
        if intensity == BLUBA_SEVERE_INTENSITY:
            # Only a severe event licenses a positive label. Its absence is not
            # evidence of calm (SPEC rule 0.7), so every other day stays null.
            entry["crisis_occurred"] = True
        trigger = str(event.get("detonante_gatillante") or "").strip()
        if trigger:
            entry["relevant_events_note"] = _join(entry["relevant_events_note"], trigger)
        strategy = str(event.get("estrategia_calma_aplicada") or "").strip()
        outcome = str(event.get("resultado_estrategia") or "").strip()
        if strategy:
            entry["other_notes"] = _join(
                entry["other_notes"], f"{strategy} ({outcome})" if outcome else strategy
            )
    return dict(by_day)


def _provenance(log: Mapping[str, Any], fields: Iterable[str]) -> dict[str, str]:
    return {field: "observed" for field in fields if log.get(field) not in (None, [])}


def _daily_log(
    case_id: str,
    row: Mapping[str, Any],
    event_entry: Mapping[str, Any] | None,
) -> dict[str, Any]:
    day = str(row["fecha"]).strip()
    entry = event_entry if event_entry is not None else _empty_day()
    summary = _lookup(
        BLUBA_REGULATION_EVENTS,
        row.get("nivel_regulacion_general_dia"),
        "nivel_regulacion_general_dia",
    )
    log: dict[str, Any] = {
        "log_id": deterministic_uuid4("log", case_id, day, "home"),
        "child_id": deterministic_uuid4("child", case_id),
        "date": day,
        "source": "home",
        "sleep_quality": _lookup(BLUBA_SLEEP_QUALITY, row.get("calidad_sueno"), "calidad_sueno"),
        "wake_state": _lookup(BLUBA_WAKE_STATE, row.get("modo_despertar"), "modo_despertar"),
        "gi_status": _lookup(
            BLUBA_GI_STATUS, row.get("estado_gastrointestinal"), "estado_gastrointestinal"
        ),
        "medication_adherence": _lookup(
            BLUBA_MEDICATION_ADHERENCE, row.get("adherencia_medicacion"), "adherencia_medicacion"
        ),
        # An explicit event count outranks the coarse day summary.
        "dysregulation_events": (
            entry["dysregulation_events"] if entry["dysregulation_events"] is not None else summary
        ),
        "observed_behavior_tags": list(entry["observed_behavior_tags"]),
        "relevant_event_flag": entry["relevant_event_flag"],
        "relevant_events_note": _truncate(entry["relevant_events_note"]),
        "other_notes": _truncate(entry["other_notes"]),
        "crisis_occurred": entry["crisis_occurred"],
        "capture_method": "form",
        "created_at": f"{day}T21:00:00Z",
    }
    log["field_provenance"] = _provenance(log, _DAILY_PROVENANCE_FIELDS)
    return log


def _session_log(case_id: str, row: Mapping[str, Any]) -> dict[str, Any] | None:
    """SPEC section 2.3: a therapy source may only report its own observations."""
    attendance = str(row.get("estado_asistencia") or "").strip()
    participation = BLUBA_ATTENDANCE_PARTICIPATION.get(attendance)
    alertness = _lookup(BLUBA_ALERTNESS, row.get("nivel_alerta_final"), "nivel_alerta_final")
    if participation is None and alertness is None:
        return None
    day = str(row["fecha_sesion"]).strip()
    log: dict[str, Any] = {
        "log_id": deterministic_uuid4("log", case_id, day, "therapy", str(row["id_sesion"])),
        "child_id": deterministic_uuid4("child", case_id),
        "date": day,
        "source": "therapy",
        "alertness": alertness,
        "activity_participation": participation,
        "observed_behavior_note": _truncate(
            str(row.get("observaciones_profesional") or "").strip() or None
        ),
        "capture_method": "form",
        "created_at": f"{day}T18:00:00Z",
    }
    log["field_provenance"] = _provenance(
        log, ("alertness", "activity_participation", "observed_behavior_note")
    )
    return log


def build_bluba_logs(
    daily_rows: Iterable[Mapping[str, Any]],
    session_rows: Iterable[Mapping[str, Any]] = (),
    event_rows: Iterable[Mapping[str, Any]] = (),
) -> list[dict[str, Any]]:
    """Map one Bluba export into DailyLog dictionaries, sorted deterministically.

    Tutor rows become ``home`` logs enriched with that day's dysregulation
    events; professional sessions become ``therapy`` logs. Days Bluba never
    recorded stay absent rather than becoming zeros (SPEC rule 0.6).
    """
    events = _summarise_events(event_rows)
    logs: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for row in daily_rows:
        case_id = str(row["id_caso"]).strip()
        day = str(row["fecha"]).strip()
        if (case_id, day) in seen:
            raise ContractViolationError(f"duplicate Bluba daily row for {case_id} on {day}")
        seen.add((case_id, day))
        logs.append(_daily_log(case_id, row, events.get((case_id, day))))

    for (case_id, day), entry in sorted(events.items()):
        if (case_id, day) in seen:
            continue
        # An event with no tutor log is exactly the NMAR case this project is
        # about: something happened on a day nobody filled in.
        logs.append(_daily_log(case_id, {"id_caso": case_id, "fecha": day}, entry))

    for row in session_rows:
        session = _session_log(str(row["id_caso"]).strip(), row)
        if session is not None:
            logs.append(session)

    logs.sort(key=lambda log: (log["child_id"], log["date"], log["source"], log["log_id"]))
    return logs
