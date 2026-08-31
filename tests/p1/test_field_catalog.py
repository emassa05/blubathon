"""The 19 daily fields, the source matrix and the allowlists."""

from __future__ import annotations

import pytest

from packages.shared.enums import FieldCode, FieldKind, Source
from packages.shared.field_catalog import (
    CANONICAL_FIELD_ORDER,
    DEFAULT_ALLOWLIST_V1,
    DQI_REQUIRED_FIELDS,
    FIELD_CATALOG,
    HIGH_SIGNAL_NO_DEFAULT,
    KINDS_WITHOUT_DEFAULTS,
    MONITORED_FIELD_PRIORITY,
    MONITORED_FIELDS,
    SCENARIO_ALLOWLIST_V1,
    UnknownFieldValueError,
    applicable_fields,
    default_is_estimable,
    validate_field_value,
)

SOURCE_MATRIX = {
    FieldCode.SLEEP_HOURS: (True, False, False),
    FieldCode.SLEEP_QUALITY: (True, False, False),
    FieldCode.NIGHT_AWAKENINGS: (True, False, False),
    FieldCode.WAKE_STATE: (True, False, False),
    FieldCode.MORNING_SUPPORT_NEED: (True, False, False),
    FieldCode.GI_STATUS: (True, True, False),
    FieldCode.MEDICATION_ADHERENCE: (True, True, False),
    FieldCode.FOOD_CHANGES: (True, False, False),
    FieldCode.ROUTINE_CHANGES: (True, False, False),
    FieldCode.ALERTNESS: (True, True, True),
    FieldCode.DYSREGULATION_EVENT_COUNT: (True, True, True),
    FieldCode.DAILY_REGULATION_STATE: (True, True, True),
    FieldCode.ACTIVITY_PARTICIPATION: (True, True, True),
    FieldCode.SOCIAL_INTERACTIONS: (True, True, True),
    FieldCode.EATING_STATUS: (True, False, True),
    FieldCode.ATTENDANCE_STATUS: (False, True, True),
    FieldCode.RELEVANT_EVENT_FLAG: (True, True, True),
    FieldCode.BEHAVIOR_TAGS: (True, True, True),
    FieldCode.NOTES: (True, True, True),
}


def test_the_catalogue_has_exactly_the_nineteen_daily_fields() -> None:
    assert len(FIELD_CATALOG) == 19
    assert set(FIELD_CATALOG) == set(FieldCode)
    assert len(CANONICAL_FIELD_ORDER) == 19


def test_the_outcome_is_not_a_daily_field() -> None:
    """`major_dysregulation_24h` lives in OutcomeReport, not in the catalogue."""

    assert "major_dysregulation_24h" not in {str(code) for code in FieldCode}


@pytest.mark.parametrize(
    ("code", "expected"), sorted(SOURCE_MATRIX.items(), key=lambda i: str(i[0]))
)
def test_source_matrix_matches_the_catalogue(
    code: FieldCode, expected: tuple[bool, bool, bool]
) -> None:
    spec = FIELD_CATALOG[code]
    actual = (
        spec.allows(Source.HOME),
        spec.allows(Source.THERAPY),
        spec.allows(Source.SCHOOL),
    )
    assert actual == expected


def test_applicable_fields_keeps_canonical_order_and_only_permitted_fields() -> None:
    for source in Source:
        fields = applicable_fields(source)
        assert list(fields) == [code for code in CANONICAL_FIELD_ORDER if code in fields]
        for code in fields:
            assert FIELD_CATALOG[code].allows(source)


def test_default_allowlist_is_exactly_five_fields() -> None:
    assert {
        FieldCode.FOOD_CHANGES,
        FieldCode.ACTIVITY_PARTICIPATION,
        FieldCode.SOCIAL_INTERACTIONS,
        FieldCode.EATING_STATUS,
        FieldCode.ATTENDANCE_STATUS,
    } == DEFAULT_ALLOWLIST_V1


def test_the_allowlist_matches_the_default_column_of_the_field_table() -> None:
    marked = {code for code, spec in FIELD_CATALOG.items() if spec.default_allowed}
    assert marked == DEFAULT_ALLOWLIST_V1


def test_high_signal_fields_never_get_a_default() -> None:
    assert HIGH_SIGNAL_NO_DEFAULT.isdisjoint(DEFAULT_ALLOWLIST_V1)
    for code in HIGH_SIGNAL_NO_DEFAULT:
        assert not default_is_estimable(code)


def test_no_continuous_count_text_or_tag_field_can_have_a_default() -> None:
    """A default there would require an unvalidated tolerance or bin."""

    for code, spec in FIELD_CATALOG.items():
        if spec.kind in KINDS_WITHOUT_DEFAULTS:
            assert not default_is_estimable(code)


def test_monitored_fields_carry_the_exact_tie_break_priority() -> None:
    assert MONITORED_FIELDS == (
        FieldCode.SLEEP_QUALITY,
        FieldCode.WAKE_STATE,
        FieldCode.GI_STATUS,
        FieldCode.MEDICATION_ADHERENCE,
        FieldCode.DAILY_REGULATION_STATE,
    )
    assert MONITORED_FIELD_PRIORITY[FieldCode.SLEEP_QUALITY] == 1
    assert MONITORED_FIELD_PRIORITY[FieldCode.DAILY_REGULATION_STATE] == 5


def test_dqi_uses_the_same_five_fields() -> None:
    assert DQI_REQUIRED_FIELDS == MONITORED_FIELDS
    assert len(DQI_REQUIRED_FIELDS) == 5


def test_scenario_allowlist_is_five_fields() -> None:
    assert {
        FieldCode.SLEEP_QUALITY,
        FieldCode.ALERTNESS,
        FieldCode.GI_STATUS,
        FieldCode.MEDICATION_ADHERENCE,
        FieldCode.DAILY_REGULATION_STATE,
    } == SCENARIO_ALLOWLIST_V1


def test_categories_are_never_ordered_scales() -> None:
    """INV-35: a nominal field keeps a closed support, never a 1-5 encoding."""

    for code in (
        FieldCode.SLEEP_QUALITY,
        FieldCode.WAKE_STATE,
        FieldCode.GI_STATUS,
        FieldCode.DAILY_REGULATION_STATE,
        FieldCode.ATTENDANCE_STATUS,
        FieldCode.ALERTNESS,
        FieldCode.MEDICATION_ADHERENCE,
    ):
        spec = FIELD_CATALOG[code]
        assert spec.kind is FieldKind.NOMINAL
        assert spec.minimum is None and spec.maximum is None
        assert spec.allowed_values()


def test_medication_not_applicable_is_a_present_answer() -> None:
    assert validate_field_value(FieldCode.MEDICATION_ADHERENCE, "not_applicable") == (
        "not_applicable"
    )


def test_an_unknown_category_fails_instead_of_becoming_null() -> None:
    with pytest.raises(UnknownFieldValueError):
        validate_field_value(FieldCode.SLEEP_QUALITY, "reparador")


def test_a_boolean_is_not_a_count_and_a_count_is_not_a_boolean() -> None:
    with pytest.raises(UnknownFieldValueError):
        validate_field_value(FieldCode.NIGHT_AWAKENINGS, True)
    with pytest.raises(UnknownFieldValueError):
        validate_field_value(FieldCode.FOOD_CHANGES, 1)


def test_numeric_bounds_come_from_the_field_table() -> None:
    assert validate_field_value(FieldCode.SLEEP_HOURS, 16.0) == 16.0
    with pytest.raises(UnknownFieldValueError):
        validate_field_value(FieldCode.SLEEP_HOURS, 16.5)
    assert validate_field_value(FieldCode.DYSREGULATION_EVENT_COUNT, 0) == 0
    with pytest.raises(UnknownFieldValueError):
        validate_field_value(FieldCode.DYSREGULATION_EVENT_COUNT, 21)
    assert validate_field_value(FieldCode.ACTIVITY_PARTICIPATION, 5) == 5
    with pytest.raises(UnknownFieldValueError):
        validate_field_value(FieldCode.ACTIVITY_PARTICIPATION, 0)


def test_notes_are_capped_at_five_hundred_characters() -> None:
    assert validate_field_value(FieldCode.NOTES, "a" * 500)
    with pytest.raises(UnknownFieldValueError):
        validate_field_value(FieldCode.NOTES, "a" * 501)


def test_behavior_tags_are_deduplicated_and_sorted() -> None:
    assert validate_field_value(FieldCode.BEHAVIOR_TAGS, ["b_tag", "a_tag", "b_tag"]) == (
        "a_tag",
        "b_tag",
    )
    with pytest.raises(UnknownFieldValueError):
        validate_field_value(FieldCode.BEHAVIOR_TAGS, ["Not A Tag"])
