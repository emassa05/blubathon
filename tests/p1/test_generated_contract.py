"""The generated artifacts and the published examples stay in step with the models.

`python -m tools.contracts.generate` followed by `git diff --exit-code
packages/shared/generated` is the gate; these tests fail first and say why.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from packages.shared.constants import CONTRACT_VERSION, SPEC_VERSION
from packages.shared.schema.registry import PUBLISHED_MODELS
from tools.contracts import examples as example_tool
from tools.contracts import generate as generator

REPO_ROOT = Path(__file__).resolve().parents[2]
GENERATED = REPO_ROOT / "packages" / "shared" / "generated"
EXAMPLES = REPO_ROOT / "packages" / "shared" / "examples"

# The handoff keeps representative v0.4 request, response and event payloads.
REQUIRED_EXAMPLES = (
    "child.list.json",
    "form_plan.request.json",
    "form_plan.response.json",
    "form_submission.request.json",
    "form_submission.response.json",
    "recommendation.matched.json",
    "recommendation.abstained.json",
    "recommendation.today.json",
    "feedback.request.json",
    "notification.ready.json",
)


@pytest.fixture(scope="module")
def schema() -> dict[str, Any]:
    return json.loads((GENERATED / "blubathon.schema.json").read_text(encoding="utf-8"))


def _validator(schema: dict[str, Any], model_name: str) -> Draft202012Validator:
    document = {"$ref": f"#/$defs/{model_name}", "$defs": schema["$defs"]}
    return Draft202012Validator(document)


# --- generation -----------------------------------------------------------


def test_generation_is_deterministic() -> None:
    assert generator.generate_in_memory() == generator.generate_in_memory()


def test_committed_artifacts_match_a_fresh_generation() -> None:
    stale = []
    for filename, content in generator.generate_in_memory().items():
        path = GENERATED / filename
        if not path.is_file() or path.read_text(encoding="utf-8") != content:
            stale.append(filename)
    assert stale == [], "run `python -m tools.contracts.generate` and commit the result"


def test_the_lock_publishes_the_contract_version_and_schema_hash() -> None:
    lock = json.loads((GENERATED / "contract.lock.json").read_text(encoding="utf-8"))
    assert lock["contract_version"] == CONTRACT_VERSION
    assert lock["spec_version"] == SPEC_VERSION
    assert len(lock["schema_hash"]) == 64
    assert lock["schema_hash"] == generator.schema_hash(generator.build_schema())
    assert sorted(lock["published_models"]) == sorted(PUBLISHED_MODELS)


def test_the_schema_bundle_is_valid_json_schema(schema: dict[str, Any]) -> None:
    Draft202012Validator.check_schema({"$defs": schema["$defs"]})
    for name in PUBLISHED_MODELS:
        assert name in schema["$defs"], f"{name} is published but has no definition"


def test_api_boundary_models_forbid_unknown_fields(schema: dict[str, Any]) -> None:
    """CONVENTIONS 6: `extra="forbid"` at every API boundary."""

    for name, definition in schema["$defs"].items():
        if definition.get("type") == "object" and "properties" in definition:
            assert definition.get("additionalProperties") is False, f"{name} accepts extra fields"


def test_typescript_and_zod_cover_every_published_model() -> None:
    types = (GENERATED / "contract.ts").read_text(encoding="utf-8")
    zod = (GENERATED / "contract.zod.ts").read_text(encoding="utf-8")
    for name in PUBLISHED_MODELS:
        assert f"export interface {name} " in types or f"export type {name} " in types
        assert f"export const {name}Schema = " in zod


def test_generated_files_carry_the_do_not_edit_banner() -> None:
    for filename in ("contract.ts", "contract.zod.ts", "constants.ts", "field-catalog.ts"):
        assert (GENERATED / filename).read_text(encoding="utf-8").startswith(generator.BANNER)


def test_the_frontend_gets_the_constants_and_the_source_matrix() -> None:
    constants_ts = (GENERATED / "constants.ts").read_text(encoding="utf-8")
    catalog_ts = (GENERATED / "field-catalog.ts").read_text(encoding="utf-8")
    assert (
        '"C09"' in constants_ts
        and '"decisionClass": "policy"'
        in constants_ts.replace("decisionClass:", '"decisionClass":')
    ) or "decisionClass" in constants_ts
    assert '"allowedSources"' in catalog_ts
    assert '"defaultAllowlistV1"' in catalog_ts


def test_the_emergency_limit_reaches_the_frontend() -> None:
    """SPEC 13.2: the limit is shown permanently, so it cannot live only in Python."""

    texts_ts = (GENERATED / "texts.ts").read_text(encoding="utf-8")
    assert "emergencyLimitEs" in texts_ts
    assert "no vigila emergencias" in texts_ts


# --- examples -------------------------------------------------------------


def test_every_example_named_in_tareas_exists() -> None:
    for filename in REQUIRED_EXAMPLES:
        assert (EXAMPLES / "valid" / filename).is_file(), f"{filename} is missing"


def test_committed_examples_match_a_fresh_render() -> None:
    stale = []
    for relative, content in example_tool.render().items():
        path = EXAMPLES / relative
        if not path.is_file() or path.read_text(encoding="utf-8") != content:
            stale.append(relative)
    assert stale == [], "run `python -m tools.contracts.examples` and commit the result"


def test_the_index_lists_every_example_with_its_model() -> None:
    index = json.loads((EXAMPLES / "index.json").read_text(encoding="utf-8"))
    assert index["contract_version"] == CONTRACT_VERSION
    listed = {entry["file"] for entry in index["valid"]} | {
        entry["file"] for entry in index["invalid"]
    }
    on_disk = {
        f"{parent}/{path.name}"
        for parent in ("valid", "invalid")
        for path in (EXAMPLES / parent).glob("*.json")
    }
    assert listed == on_disk
    for entry in index["invalid"]:
        assert entry["violates"], f"{entry['file']} must name the rule it breaks"


def _index_entries(kind: str) -> list[dict[str, Any]]:
    index = json.loads((EXAMPLES / "index.json").read_text(encoding="utf-8"))
    return index[kind]


@pytest.mark.parametrize("entry", _index_entries("valid"), ids=lambda entry: entry["file"])
def test_a_valid_example_validates_against_its_model(entry: dict[str, Any]) -> None:
    payload = json.loads((EXAMPLES / entry["file"]).read_text(encoding="utf-8"))
    PUBLISHED_MODELS[entry["model"]].model_validate(payload)


@pytest.mark.parametrize("entry", _index_entries("valid"), ids=lambda entry: entry["file"])
def test_a_valid_example_validates_against_the_published_schema(
    entry: dict[str, Any], schema: dict[str, Any]
) -> None:
    payload = json.loads((EXAMPLES / entry["file"]).read_text(encoding="utf-8"))
    _validator(schema, entry["model"]).validate(payload)


@pytest.mark.parametrize("entry", _index_entries("invalid"), ids=lambda entry: entry["file"])
def test_an_invalid_example_is_rejected_for_the_reason_it_documents(
    entry: dict[str, Any],
) -> None:
    payload = json.loads((EXAMPLES / entry["file"]).read_text(encoding="utf-8"))
    with pytest.raises(ValidationError):
        PUBLISHED_MODELS[entry["model"]].model_validate(payload)


def test_no_example_carries_a_real_person_or_source() -> None:
    """CONVENTIONS 15: versioned tests and examples use fictional data only."""

    forbidden = ("PAC-00", "REG-00", "SES-00", "EVT-00", "OBJ-00")
    for path in EXAMPLES.rglob("*.json"):
        text = path.read_text(encoding="utf-8")
        for marker in forbidden:
            assert marker not in text, f"{path.name} looks like it came from an export"
