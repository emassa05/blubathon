"""The offline authoring CLI (P1.6, H4).

The build writes manifests and hashes; document bodies, extracted text and
indices stay out of Git.
"""

from __future__ import annotations

import json
from pathlib import Path

from tests.p1 import rag_factories as rf
from tools.rag_authoring.cli import (
    BUILD_MANIFEST_PATH,
    CORPUS_CANDIDATES,
    MODEL_CANDIDATES,
    build_status_manifest,
    main,
    resolved_retrieval_mode,
    status_report,
)


def _manifests() -> tuple[dict, dict]:
    return (
        json.loads(CORPUS_CANDIDATES.read_text(encoding="utf-8")),
        json.loads(MODEL_CANDIDATES.read_text(encoding="utf-8")),
    )


def _write_corpus(directory: Path, *, rights_basis: str) -> None:
    (directory / "sleep.txt").write_text(rf.SLEEP_TEXT, encoding="utf-8")
    (directory / "sleep.source.json").write_text(
        json.dumps(
            {
                "source_id": "11111111-2222-4333-8444-555555555001",
                "publisher": "Fixture Publisher",
                "title": "Fixture document sleep",
                "document_version": "1",
                "publication_date": "2026-01-15",
                "retrieved_at": "2026-08-20T09:00:00+00:00",
                "canonical_url": "https://example.invalid/fixtures/sleep",
                "rights_basis": rights_basis,
                "language": "es",
                "text_file": "sleep.txt",
            }
        ),
        encoding="utf-8",
    )


class TestStatus:
    def test_todays_state_resolves_to_lexical_only_and_corpus_not_ready(self) -> None:
        corpus, models = _manifests()
        report = status_report(corpus, models)
        assert report["retrieval_mode"] == "lexical_only"
        assert report["catalog_readiness"] == "corpus_not_ready"
        assert report["catalog_status"] == "blocked_corpus"
        assert report["cleared_document_count"] == 0
        assert report["runtime_llm_calls"] == 0

    def test_a_registered_embedding_model_would_resolve_to_hybrid(self) -> None:
        _, models = _manifests()
        assert resolved_retrieval_mode(models).value == "lexical_only"
        registered = {**models, "embedding_models": [{"model_id": "declared"}]}
        assert resolved_retrieval_mode(registered).value == "hybrid"

    def test_the_command_prints_the_report(self, capsys, tmp_path: Path) -> None:
        assert main(["status"]) == 0
        printed = json.loads(capsys.readouterr().out)
        assert printed["catalog_readiness"] == "corpus_not_ready"


class TestBuild:
    def test_a_cleared_document_produces_a_lexical_only_manifest(
        self, tmp_path: Path, capsys
    ) -> None:
        corpus_dir = tmp_path / "corpus"
        corpus_dir.mkdir()
        _write_corpus(corpus_dir, rights_basis=rf.FIXTURE_RIGHTS)
        out = tmp_path / "out"

        assert main(["build", "--corpus-dir", str(corpus_dir), "--out", str(out)]) == 0
        printed = json.loads(capsys.readouterr().out)
        assert printed["retrieval_mode"] == "lexical_only"
        assert printed["catalog_status"] == "blocked_clinical_review"

        report = json.loads((out / "build.manifest.json").read_text(encoding="utf-8"))
        assert report["manifest"]["retrieval_mode"] == "lexical_only"
        assert report["chunks"]
        # Hashes and locators travel; text never does.
        assert all("text" not in chunk for chunk in report["chunks"])

    def test_an_undeclared_rights_basis_reports_corpus_not_ready(
        self, tmp_path: Path, capsys
    ) -> None:
        corpus_dir = tmp_path / "corpus"
        corpus_dir.mkdir()
        _write_corpus(corpus_dir, rights_basis="undeclared")
        out = tmp_path / "out"

        assert main(["build", "--corpus-dir", str(corpus_dir), "--out", str(out)]) == 1
        printed = json.loads(capsys.readouterr().out)
        assert printed["reason"] == "corpus_not_ready"
        assert not out.exists()

    def test_an_empty_corpus_reports_corpus_not_ready(self, tmp_path: Path, capsys) -> None:
        corpus_dir = tmp_path / "corpus"
        corpus_dir.mkdir()
        assert main(["build", "--corpus-dir", str(corpus_dir), "--out", str(tmp_path / "out")]) == 1
        assert json.loads(capsys.readouterr().out)["reason"] == "corpus_not_ready"


class TestHandoffManifest:
    def test_the_committed_manifest_matches_what_the_code_produces(self) -> None:
        corpus, models = _manifests()
        expected = build_status_manifest(corpus, models)
        committed = json.loads(BUILD_MANIFEST_PATH.read_text(encoding="utf-8"))
        assert committed == expected

    def test_the_manifest_carries_every_version_that_fixes_a_result(self) -> None:
        corpus, models = _manifests()
        pipeline = build_status_manifest(corpus, models)["pipeline"]
        assert set(pipeline) == {
            "extractor_version",
            "ocr_version",
            "normalization_version",
            "chunker_version",
            "chunk_size",
            "chunk_overlap",
            "tokenizer_version",
            "bm25_version",
            "bm25_parameters",
            "lexical_top_k",
            "dense_top_k",
            "rrf_k",
            "final_chunk_count",
            "prompt_version",
            "prompt_sha256",
        }
        assert len(pipeline["prompt_sha256"]) == 64

    def test_the_manifest_declares_the_blocked_corpus_rather_than_a_catalogue(self) -> None:
        corpus, models = _manifests()
        manifest = build_status_manifest(corpus, models)
        assert manifest["catalog_status"] == "blocked_corpus"
        assert manifest["catalog_readiness"] == "corpus_not_ready"
        assert manifest["corpus_versions"] == []
        assert manifest["catalog_versions"] == []
        assert manifest["runtime"]["llm_calls"] == 0

    def test_the_command_rewrites_the_manifest(self, tmp_path: Path, capsys) -> None:
        target = tmp_path / "rag-build.manifest.json"
        assert main(["manifest", "--out", str(target)]) == 0
        capsys.readouterr()
        assert json.loads(target.read_text(encoding="utf-8"))["manifest_kind"] == "rag_build"
