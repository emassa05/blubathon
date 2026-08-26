"""The SPEC 15 registry is complete, classified and the only home of its literals."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from packages.shared import constants
from packages.shared.constants import CONSTANTS, ConstantSpec

REPO_ROOT = Path(__file__).resolve().parents[2]

EXPECTED_VALUES = {
    "C01": "0.4.0",
    "C02": "/v1",
    "C03": "America/Santiago",
    "C04": 24,
    "C05": 48,
    "C06": 60,
    "C07": 1,
    "C08": 0.05,
    "C09": 0.70,
    "C10": 0.10,
    "C11": 2,
    "C12": 3,
    "C13": 0.50,
    "C14": 7,
    "C16": 0.05,
    "C17": 2.0,
    "C18": 60,
    "C19": 5,
    "C20": None,
    "C21": 30,
    "C22": 5,
    "C23": 2,
    "C24": (0.01, 0.1, 1.0, 10.0, 100.0),
    "C25": 20,
    "C26": 20,
    "C27": 60,
    "C28": 8,
    "C29": 0,
    "C30": 3,
    "C31": 2,
    "C32": 0,
    "C33": "sha256",
    "C34": 42,
    "C36": "1.2",
    "C37": None,
    "C38": 14,
    "C39": 2,
    "C40": 0.5,
    "C41": 0.5,
    "C42": 0.05,
    "C43": 0.95,
    "C44": 1e-12,
    "C45": 2000,
    "C46": 0.90,
    "C47": 0.80,
    "C48": 10,
    "C49": 5,
    "C50": 5,
}


def test_registry_covers_c01_to_c50() -> None:
    assert sorted(CONSTANTS) == [f"C{index:02d}" for index in range(1, 51)]


@pytest.mark.parametrize(("constant_id", "expected"), sorted(EXPECTED_VALUES.items()))
def test_registry_values_match_the_spec(constant_id: str, expected: object) -> None:
    assert CONSTANTS[constant_id].value == expected


def test_every_constant_declares_a_valid_class_and_reference() -> None:
    valid = {"mathematical", "evidence", "policy", "engineering"}
    for spec in CONSTANTS.values():
        assert isinstance(spec, ConstantSpec)
        assert spec.decision_class in valid
        assert spec.spec_ref.startswith("SPEC ")
        assert spec.spec_ref.endswith(f"/ {spec.constant_id}")


def test_no_simulation_parameter_is_labelled_as_evidence() -> None:
    """SPEC 0.1 rule 5: a synthetic weight is never presented as clinical evidence."""

    evidence = [spec for spec in CONSTANTS.values() if spec.decision_class == "evidence"]
    assert evidence == []


def test_module_level_names_read_the_registry_instead_of_restating_a_literal() -> None:
    """CONVENTIONS 7 forbids duplicating a registry literal anywhere in the module."""

    source = (REPO_ROOT / "packages" / "shared" / "constants.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    registry_end = max(
        node.end_lineno or 0
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign | ast.AnnAssign)
        and getattr(getattr(node, "target", None), "id", "") == "CONSTANTS_BY_NAME"
    )
    for node in ast.walk(tree):
        if not isinstance(node, ast.AnnAssign) or node.value is None:
            continue
        if (node.lineno or 0) <= registry_end:
            continue
        assert isinstance(node.value, ast.Call), (
            f"{ast.unparse(node.target)} must read the registry, not restate a literal"
        )


def test_module_names_agree_with_their_registry_entry() -> None:
    for spec in CONSTANTS.values():
        assert getattr(constants, spec.name) == spec.value


def test_no_decision_policy_and_no_interval_width_gate_exist() -> None:
    """SPEC 8.5 and 8.6: without a validated policy there are no bands, and the
    old interval-width gate was unreachable and is retired."""

    assert constants.DECISION_POLICY_VERSION is None
    assert constants.BASELINE_MAX_INTERVAL_WIDTH is None


def test_runtime_never_calls_an_llm() -> None:
    assert constants.RUNTIME_LLM_CALLS == 0
