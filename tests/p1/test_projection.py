"""`project_as_of` keeps history and refuses to guess."""

from __future__ import annotations

from datetime import timedelta

from packages.shared.enums import FieldCode, Source
from packages.shared.projection import project_as_of, unique_active
from tests.p1.factories import NOW, TENANT, ident, observation

LATER = NOW + timedelta(hours=1)
MUCH_LATER = NOW + timedelta(days=1)


def test_a_row_ingested_after_the_cutoff_is_invisible() -> None:
    row = observation("late", ingested_at=MUCH_LATER, effective_at=NOW)
    assert project_as_of([row], NOW).leaves == ()
    assert project_as_of([row], MUCH_LATER).leaves == (row,)


def test_a_row_effective_after_the_cutoff_is_invisible() -> None:
    row = observation("future", effective_at=MUCH_LATER, ingested_at=NOW)
    assert project_as_of([row], NOW).leaves == ()


def test_a_correction_chain_contributes_only_its_leaf() -> None:
    original = observation("original", value=False)
    correction = observation(
        "correction",
        value=True,
        effective_at=NOW,
        ingested_at=LATER,
        supersedes_id=original.field_observation_id,
    )
    projection = project_as_of([original, correction], LATER)
    assert projection.leaves == (correction,)
    assert projection.projected_ids == (correction.field_observation_id,)
    assert projection.is_clean


def test_a_later_correction_does_not_rewrite_an_earlier_snapshot() -> None:
    original = observation("original", value=False)
    correction = observation(
        "correction",
        value=True,
        effective_at=NOW,
        ingested_at=MUCH_LATER,
        supersedes_id=original.field_observation_id,
    )
    rows = [original, correction]
    assert project_as_of(rows, LATER).leaves == (original,)
    assert project_as_of(rows, MUCH_LATER).leaves == (correction,)


def test_two_corrections_of_the_same_row_are_a_branch_not_a_winner() -> None:
    original = observation("original")
    first = observation("branch-a", ingested_at=LATER, supersedes_id=original.field_observation_id)
    second = observation("branch-b", ingested_at=LATER, supersedes_id=original.field_observation_id)
    projection = project_as_of([original, first, second], LATER)
    assert not projection.is_clean
    assert {conflict.reason for conflict in projection.conflicts} == {"branch"}
    assert projection.leaves == ()


def test_a_cycle_invalidates_the_chain() -> None:
    first_id = ident("cycle-a")
    second_id = ident("cycle-b")
    first = observation("cycle-a", supersedes_id=second_id)
    second = observation("cycle-b", ingested_at=LATER, supersedes_id=first_id)
    projection = project_as_of([first, second], LATER)
    assert "cycle" in {conflict.reason for conflict in projection.conflicts}
    assert projection.leaves == ()


def test_a_cross_tenant_correction_is_a_conflict() -> None:
    original = observation("original")
    foreign = observation(
        "foreign",
        tenant_id=ident("other-tenant"),
        ingested_at=LATER,
        supersedes_id=original.field_observation_id,
    )
    projection = project_as_of([original, foreign], LATER)
    assert "cross_tenant" in {conflict.reason for conflict in projection.conflicts}


def test_a_dangling_correction_is_its_own_root_not_a_conflict() -> None:
    """The superseded row is not known at this cutoff, so there is nothing to merge."""

    correction = observation("orphan", supersedes_id=ident("never-ingested"))
    projection = project_as_of([correction], NOW)
    assert projection.leaves == (correction,)
    assert projection.is_clean


def test_two_active_leaves_for_one_field_day_are_a_conflict() -> None:
    first = observation("first", value=False)
    second = observation("second", value=True)
    projection = project_as_of([first, second], NOW)
    assert projection.is_clean

    grouped = unique_active(projection, key=lambda row: row.field_day())
    assert not grouped.is_clean
    assert "duplicate_active_leaf" in {conflict.reason for conflict in grouped.conflicts}
    assert grouped.rows == {}


def test_different_field_days_stay_separate() -> None:
    home = observation("home", source=Source.HOME, field_code=FieldCode.ALERTNESS, value="calm")
    school = observation(
        "school", source=Source.SCHOOL, field_code=FieldCode.ALERTNESS, value="high"
    )
    grouped = unique_active(project_as_of([home, school], NOW), key=lambda row: row.field_day())
    assert grouped.is_clean
    assert len(grouped.rows) == 2


def test_the_projection_records_the_exact_ids_a_snapshot_persists() -> None:
    rows = [observation("a"), observation("b", field_code=FieldCode.ROUTINE_CHANGES, value=True)]
    projection = project_as_of(rows, NOW)
    assert set(projection.projected_ids) == {row.field_observation_id for row in rows}


def test_stratum_never_merges_tenants_or_contexts() -> None:
    row = observation("row")
    assert row.stratum() == (TENANT, row.subject_id, Source.HOME, FieldCode.FOOD_CHANGES)
