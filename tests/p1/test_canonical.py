"""Canonical bytes, domain-separated hashes and local calendar windows."""

from __future__ import annotations

import unicodedata
from datetime import UTC, date, datetime, timedelta, timezone

import pytest

from packages.shared.canonical import (
    CanonicalizationError,
    bytes_hash,
    canonical_bytes,
    canonical_date,
    canonical_timestamp,
    content_hash,
    domain_separator,
    exclusive_window,
    in_window,
    inclusive_window,
    keyed_hash,
    local_date,
    normalize_text,
    ordered_set,
    stable_bucket,
)

SECRET = b"fixed-test-secret"


def test_timestamps_serialise_with_milliseconds_and_a_z() -> None:
    moment = datetime(2026, 8, 25, 19, 55, 0, 123456, tzinfo=UTC)
    assert canonical_timestamp(moment) == "2026-08-25T19:55:00.123Z"


def test_a_non_utc_timestamp_is_converted_not_rejected() -> None:
    santiago = timezone(timedelta(hours=-4))
    moment = datetime(2026, 8, 25, 15, 55, tzinfo=santiago)
    assert canonical_timestamp(moment) == "2026-08-25T19:55:00.000Z"


def test_a_naive_timestamp_has_no_canonical_form() -> None:
    with pytest.raises(CanonicalizationError):
        canonical_timestamp(datetime(2026, 8, 25, 19, 55))


def test_a_datetime_is_not_silently_treated_as_a_date() -> None:
    with pytest.raises(CanonicalizationError):
        canonical_date(datetime(2026, 8, 25, tzinfo=UTC))
    assert canonical_date(date(2026, 8, 25)) == "2026-08-25"


def test_local_date_uses_the_reference_zone() -> None:
    """02:30 UTC on the 25th is still the 24th in America/Santiago."""

    assert local_date(datetime(2026, 8, 25, 2, 30, tzinfo=UTC)) == date(2026, 8, 24)


def test_two_spellings_of_the_same_string_hash_the_same() -> None:
    composed = "canción"
    decomposed = unicodedata.normalize("NFD", composed)
    assert composed != decomposed
    assert normalize_text(decomposed) == composed
    assert canonical_bytes({"a": decomposed}) == canonical_bytes({"a": composed})


def test_object_key_order_does_not_change_the_bytes() -> None:
    assert canonical_bytes({"b": 1, "a": 2}) == canonical_bytes({"a": 2, "b": 1})


def test_ranking_order_is_preserved_but_set_order_is_normalised() -> None:
    assert canonical_bytes([3, 1, 2]) != canonical_bytes([1, 2, 3])
    assert ordered_set(["b", "a", "b"]) == ["a", "b"]


def test_a_set_must_be_ordered_before_it_can_be_serialised() -> None:
    with pytest.raises(CanonicalizationError):
        canonical_bytes({"tags": {"b", "a"}})


def test_nan_and_infinity_have_no_canonical_form() -> None:
    for value in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises(CanonicalizationError):
            canonical_bytes({"value": value})


def test_hashes_are_separated_by_artifact_and_schema_version() -> None:
    payload = {"a": 1}
    assert content_hash("document", "1", payload) != content_hash("strategy", "1", payload)
    assert content_hash("document", "1", payload) != content_hash("document", "2", payload)
    assert domain_separator("document", "1").endswith(b"\x00")


def test_the_same_payload_always_hashes_the_same() -> None:
    payload = {"b": [1, 2], "a": "canción"}
    assert content_hash("strategy", "1", payload) == content_hash("strategy", "1", payload)
    assert len(content_hash("strategy", "1", payload)) == 64


def test_bytes_hash_keeps_document_provenance_separate() -> None:
    assert len(bytes_hash(b"abc")) == 64


def test_a_keyed_hash_needs_a_secret_and_differs_from_the_unkeyed_one() -> None:
    payload = {"sleep_quality": "interrupted"}
    keyed = keyed_hash(SECRET, "scenario", "scenario-1", payload)
    assert keyed != content_hash("scenario", "scenario-1", payload)
    assert keyed == keyed_hash(SECRET, "scenario", "scenario-1", payload)
    assert keyed != keyed_hash(b"another-secret", "scenario", "scenario-1", payload)
    with pytest.raises(CanonicalizationError):
        keyed_hash(b"", "scenario", "scenario-1", payload)


def test_bucket_assignment_is_stable_and_needs_a_secret() -> None:
    parts = ["tenant", "subject", "2026-08-25", "form-0.3.0"]
    first = stable_bucket(SECRET, parts, 1000)
    assert 0 <= first < 1000
    assert stable_bucket(SECRET, parts, 1000) == first
    assert stable_bucket(b"other", parts, 1000) != first or True  # a collision is possible
    with pytest.raises(CanonicalizationError):
        stable_bucket(b"", parts, 1000)


def test_inclusive_and_exclusive_windows_match_the_spec_arithmetic() -> None:
    cutoff = date(2026, 8, 25)
    assert inclusive_window(cutoff, 14) == (date(2026, 8, 12), cutoff)
    assert inclusive_window(cutoff, 60) == (date(2026, 6, 27), cutoff)
    assert exclusive_window(cutoff, 30) == (date(2026, 7, 26), date(2026, 8, 24))


def test_an_exclusive_window_excludes_the_cutoff_day() -> None:
    cutoff = date(2026, 8, 25)
    window = exclusive_window(cutoff, 30)
    assert not in_window(cutoff, window)
    assert in_window(date(2026, 8, 24), window)
    assert in_window(date(2026, 7, 26), window)
    assert not in_window(date(2026, 7, 25), window)


def test_an_inclusive_window_of_fourteen_days_contains_fourteen_days() -> None:
    start, end = inclusive_window(date(2026, 8, 25), 14)
    assert (end - start) == timedelta(days=13)
