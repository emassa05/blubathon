"""The prompt, index and feature audit of the M6 gate (M6, INV-22).

Has one exception and it is documentary: only versioned, rights-cleared
literature may be fragmented, indexed or placed in an authoring prompt. Notes,
messages and anything a caregiver or professional typed never enter that
pipeline, and neither do identifiers.

This module is the audit that proves it for the three surfaces where free text
could plausibly leak: the prompts, the index, and the features a model reads.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ml.prediction.challenger import PREDICTOR_ENCODINGS, encode_predictor
from ml.prediction.landmarks import CHALLENGER_PREDICTORS
from packages.shared.domain.rag import ScenarioV1
from packages.shared.enums import FieldCode, FieldKind
from packages.shared.field_catalog import (
    DEFAULT_ALLOWLIST_V1,
    DQI_REQUIRED_FIELDS,
    FIELD_CATALOG,
    MONITORED_FIELDS,
    SCENARIO_ALLOWLIST_V1,
)
from rag.authoring.bm25 import Bm25Index, tokenize
from rag.authoring.drafting import DraftRequest, load_prompt, render_fragments, request_draft
from rag.domain.text_guard import (
    FREE_TEXT_FIELDS,
    FreeTextLeakError,
    TextProvenance,
    assert_literature_only,
    assert_no_clinical_text,
)
from tests.p1 import rag_factories as rf

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]

# A fictional note and a fictional identifier, used only as things that must
# never be found anywhere downstream.
CLINICAL_NOTE = "Hoy Martina durmio mal y estuvo irritable toda la manana."
CLINICAL_IDENTIFIER = "11111111-2222-4333-8444-555555555555"


class TestFeatureSurface:
    def test_the_free_text_fields_are_exactly_the_text_and_tag_fields(self) -> None:
        expected = {
            code
            for code, spec in FIELD_CATALOG.items()
            if spec.kind in {FieldKind.TEXT, FieldKind.TAG_SET}
        }
        assert expected == FREE_TEXT_FIELDS
        assert FieldCode.NOTES in FREE_TEXT_FIELDS
        assert FieldCode.BEHAVIOR_TAGS in FREE_TEXT_FIELDS

    def test_no_feature_surface_includes_a_free_text_field(self) -> None:
        surfaces = {
            "default_allowlist": DEFAULT_ALLOWLIST_V1,
            "scenario_allowlist": SCENARIO_ALLOWLIST_V1,
            "dqi_required_fields": frozenset(DQI_REQUIRED_FIELDS),
            "monitored_fields": frozenset(MONITORED_FIELDS),
            "challenger_predictors": frozenset(CHALLENGER_PREDICTORS),
            "challenger_encodings": frozenset(PREDICTOR_ENCODINGS),
        }
        for name, surface in surfaces.items():
            assert not surface & FREE_TEXT_FIELDS, name

    def test_a_note_cannot_be_encoded_as_a_challenger_predictor(self) -> None:
        with pytest.raises(ValueError, match="preregistered"):
            encode_predictor(FieldCode.NOTES, CLINICAL_NOTE)

    def test_a_scenario_refuses_a_field_outside_its_allowlist(self) -> None:
        with pytest.raises(ValueError, match="allowlist"):
            ScenarioV1(field_values={FieldCode.NOTES: CLINICAL_NOTE})


class TestPromptSurface:
    def test_the_prompt_declares_only_two_placeholders(self) -> None:
        template = load_prompt().template
        placeholders = {
            segment.split("}")[0] for segment in template.split("{")[1:] if "}" in segment
        }
        assert placeholders == {"generalized_question_es", "fragments"}

    def test_the_prompt_names_no_clinical_field_or_identifier(self) -> None:
        prompt = load_prompt()
        raw = json.dumps(
            {
                "template": prompt.template,
                "input": prompt.input_schema,
                "output": prompt.output_schema,
            }
        ).lower()
        for forbidden in (
            "subject_id",
            "tenant_id",
            "actor_id",
            "prediction_episode",
            "scenario_hash",
            "notes",
            "behavior_tags",
        ):
            assert forbidden not in raw

    def test_the_prompt_input_schema_is_closed(self) -> None:
        schema = load_prompt().input_schema
        assert schema["additionalProperties"] is False
        fragment_schema = schema["properties"]["fragments"]["items"]
        assert fragment_schema["additionalProperties"] is False
        # A fragment carries a document version, a locator and text. Nothing
        # about a person can ride along.
        assert set(fragment_schema["properties"]) == {
            "document_version_id",
            "locator",
            "text",
        }

    def test_a_rendered_prompt_contains_only_the_fragments_it_was_given(self) -> None:
        build = rf.fixture_build()
        rendered = render_fragments(build.chunks)
        assert CLINICAL_NOTE not in rendered
        assert CLINICAL_IDENTIFIER not in rendered
        assert_no_clinical_text(rendered, sentinels=(CLINICAL_NOTE, CLINICAL_IDENTIFIER))

    def test_a_clinical_sentinel_anywhere_in_the_prompt_stops_the_draft(self) -> None:
        build = rf.fixture_build()

        class Transport:
            model_id = "fixture-llm"
            model_sha256 = "e" * 64

            def complete(self, prompt: str) -> str:  # pragma: no cover - never reached
                raise AssertionError("the guard must run before the transport")

        with pytest.raises(FreeTextLeakError):
            request_draft(
                DraftRequest("consulta generalizada de autoria", build.chunks),
                transport=Transport(),
                authorised_document_version_ids=build.authorised_document_version_ids,
                clinical_sentinels=("Rutina",),
            )


class TestIndexSurface:
    def test_every_indexed_chunk_traces_to_an_authorised_document_version(self) -> None:
        build = rf.fixture_build()
        authorised = build.authorised_document_version_ids
        assert authorised
        for chunk in build.chunks:
            assert chunk.document_version_id in authorised

    def test_a_clinical_note_cannot_be_offered_to_the_chunker_or_the_index(self) -> None:
        build = rf.fixture_build()
        with pytest.raises(FreeTextLeakError):
            assert_literature_only(
                (TextProvenance(text=CLINICAL_NOTE, kind="clinical_free_text"),),
                authorised=build.authorised_document_version_ids,
            )

    def test_the_index_holds_no_token_of_a_clinical_note(self) -> None:
        build = rf.fixture_build()
        index = Bm25Index(build.chunks)
        # A distinctive token from the note retrieves nothing, because it was
        # never indexed in the first place.
        assert index.search("Martina", top_k=8) == ()
        for chunk in build.chunks:
            assert CLINICAL_NOTE not in chunk.text
            assert CLINICAL_IDENTIFIER not in chunk.text

    def test_the_tokenizer_is_not_the_thing_protecting_the_index(self) -> None:
        # Tokenising a note works fine; the guard is provenance, not filtering.
        assert "martina" in tokenize(CLINICAL_NOTE)


class TestSourceAudit:
    def test_no_rag_module_reads_a_free_text_field(self) -> None:
        forbidden = ("FieldCode.NOTES", "FieldCode.BEHAVIOR_TAGS")
        for path in sorted((REPOSITORY_ROOT / "rag").rglob("*.py")):
            text = path.read_text(encoding="utf-8")
            for token in forbidden:
                assert token not in text, f"{path} references {token}"

    def test_no_rag_module_imports_the_clinical_domain_or_the_application(self) -> None:
        forbidden = ("from apps", "import apps", "from ml", "import ml", "import sqlite3")
        for path in sorted((REPOSITORY_ROOT / "rag").rglob("*.py")):
            text = path.read_text(encoding="utf-8")
            for token in forbidden:
                assert token not in text, f"{path} imports {token}"
