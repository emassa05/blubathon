"""M0/P1: the evidence and candidate manifests describe reality without leaking it.

SPEC 1.2 states a verifiable repository state. These tests recompute it from the
manifest instead of trusting the prose, and they assert the disclosure rules that
let the manifest be committed while the export itself never is.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from tools.contracts import source_evidence

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"
SOURCE_EVIDENCE = DATA_DIR / "source-evidence.manifest.json"
CORPUS_CANDIDATES = DATA_DIR / "corpus-candidates.manifest.json"
MODEL_CANDIDATES = DATA_DIR / "model-candidates.manifest.json"

WITHHELD_KINDS = {"identifier", "quasi_identifier", "free_text"}


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def evidence() -> dict[str, Any]:
    return _load(SOURCE_EVIDENCE)


def test_every_manifest_is_committed() -> None:
    for path in (SOURCE_EVIDENCE, CORPUS_CANDIDATES, MODEL_CANDIDATES):
        assert path.is_file(), f"{path.name} must be committed"


def test_evidence_manifest_never_publishes_identifiers_or_free_text(
    evidence: dict[str, Any],
) -> None:
    for entry in evidence["files"]:
        for column in entry.get("columns", []):
            if column["kind"] in WITHHELD_KINDS:
                assert "distinct_values" not in column, (
                    f"{entry['filename']}.{column['name']} would publish {column['kind']} values"
                )
                assert column["distinct_value_digest_sha256"]


def test_evidence_manifest_publishes_closed_vocabularies(evidence: dict[str, Any]) -> None:
    """An adapter needs the source vocabulary; that is the whole point (SPEC 5.3)."""

    published = [
        column
        for entry in evidence["files"]
        for column in entry.get("columns", [])
        if column["kind"] == "closed_category"
    ]
    assert published, "the export has closed categories and they must be listed"
    for column in published:
        assert isinstance(column["distinct_values"], list)
        assert len(column["distinct_values"]) == column["distinct_non_empty_count"]


def test_evidence_manifest_keeps_dates_at_month_granularity(evidence: dict[str, Any]) -> None:
    for entry in evidence["files"]:
        for column in entry.get("columns", []):
            if column["kind"] in {"date", "timestamp"}:
                span = column["month_span"]
                for bound in (span["first"], span["last"]):
                    assert bound is None or len(bound) == len("YYYY-MM")


def test_evidence_manifest_records_hashes_and_schema_match(evidence: dict[str, Any]) -> None:
    present = [entry for entry in evidence["files"] if entry["status"] == "present"]
    assert present, "run `python -m tools.contracts.source_evidence` first"
    for entry in present:
        assert len(entry["content_sha256"]) == 64
        assert entry["schema_matches_policy"], f"{entry['filename']} columns drifted"


def test_readiness_matches_the_state_spec_1_2_describes(evidence: dict[str, Any]) -> None:
    readiness = evidence["readiness"]
    assert readiness["real_subject_count"] == 4
    assert readiness["real_dysregulation_event_count"] == 7
    assert readiness["explicit_severe_event_count"] == 2
    assert readiness["verified_negative_outcome_count"] == 0
    assert readiness["tracks"] == {
        "synthetic_reference": "simulation_only",
        "real_personal_baseline": "collecting_outcomes",
        "real_logit_challenger": "not_trainable_single_class",
        "rag_catalog": "not_ready",
    }


def test_real_export_is_never_declared_mixable_with_synthetic(evidence: dict[str, Any]) -> None:
    export = evidence["export"]
    assert export["data_origin"] == "real"
    assert export["may_mix_with_synthetic"] is False
    assert export["tracked_in_git"] is False


def test_export_rights_are_declared_blocked_not_invented(evidence: dict[str, Any]) -> None:
    export = evidence["export"]
    assert export["rights_basis"] == "undeclared"
    assert export["rights_status"] == "blocked"


def test_corpus_candidates_declare_publishers_without_claiming_a_licence() -> None:
    manifest = _load(CORPUS_CANDIDATES)
    publishers = {entry["publisher"] for entry in manifest["publishers"]}
    assert publishers == {
        "MINSAL",
        "MINEDUC",
        "NICE",
        "PubMed Central",
        "SciELO",
        "Cochrane",
    }
    for entry in manifest["publishers"]:
        assert entry["rights_basis"] == "undeclared"
        assert entry["rights_status"] == "blocked"
        assert entry["blocking_reason"]
    assert manifest["documents"] == []
    assert manifest["status"] == "blocked"


def test_model_candidates_resolve_to_lexical_only_without_inventing_a_model() -> None:
    manifest = _load(MODEL_CANDIDATES)
    assert manifest["embedding_models"] == []
    assert manifest["llm_models"] == []
    assert manifest["resolved_build_mode"] == "lexical_only"
    assert manifest["runtime_llm_calls"] == 0
    assert manifest["status"] == "blocked"


def test_gitignore_keeps_the_export_out_and_manifests_in() -> None:
    ignored = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "Datos base/" in ignored
    assert "data/*" in ignored
    assert "!data/*.manifest.json" in ignored


def test_manifest_can_be_rebuilt_deterministically() -> None:
    export_dir = source_evidence.DEFAULT_EXPORT_DIR
    if not export_dir.is_dir():
        pytest.skip("the untracked export is not present on this machine")
    first = source_evidence.build_manifest(export_dir)
    second = source_evidence.build_manifest(export_dir)
    assert first == second
    assert first == _load(SOURCE_EVIDENCE), (
        "committed manifest is stale; run `python -m tools.contracts.source_evidence`"
    )
