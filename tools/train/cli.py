"""Local training CLI (TAREAS P1.8).

Training happens offline, never inside the API. The command reads an export of
already-validated domain rows, builds an origin-separated snapshot, re-checks
consent at the moment the run starts, and writes a manifest P2 can import.

It writes counts, hashes and versions. No clinical row, no note and no
identifier beyond the tenant, snapshot and run identifiers leaves this command.
"""

from __future__ import annotations

import argparse
import json
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from packages.shared.domain.identity import Consent
from packages.shared.domain.observation import FieldObservation
from packages.shared.domain.outcome import OutcomeResolution
from packages.shared.domain.prediction import PredictionEpisode
from packages.shared.enums import DataOrigin
from tools.train.run import run_challenger_training, run_report
from tools.train.snapshot import SnapshotInputs

RUN_NAMESPACE = uuid.UUID("2b0c9a51-8f42-4d6e-9c37-1a5b8e2f4d70")


def _identifier(label: str) -> uuid.UUID:
    raw = bytearray(uuid.uuid5(RUN_NAMESPACE, label).bytes)
    raw[6] = (raw[6] & 0x0F) | 0x40
    raw[8] = (raw[8] & 0x3F) | 0x80
    return uuid.UUID(bytes=bytes(raw))


def load_inputs(payload: dict[str, Any]) -> SnapshotInputs:
    """Validate an export against the published contract before using it."""

    return SnapshotInputs(
        tenant_id=uuid.UUID(payload["tenant_id"]),
        data_origin=DataOrigin(payload["data_origin"]),
        target_definition_version=payload["target_definition_version"],
        cutoff_at=datetime.fromisoformat(payload["cutoff_at"]),
        episodes=tuple(
            PredictionEpisode.model_validate(row) for row in payload.get("episodes", ())
        ),
        resolutions=tuple(
            OutcomeResolution.model_validate(row) for row in payload.get("resolutions", ())
        ),
        observations=tuple(
            FieldObservation.model_validate(row) for row in payload.get("observations", ())
        ),
        consents=tuple(Consent.model_validate(row) for row in payload.get("consents", ())),
    )


def run(export_path: Path, out_dir: Path, *, label: str, now: datetime | None = None) -> int:
    payload = json.loads(export_path.read_text(encoding="utf-8"))
    inputs = load_inputs(payload)
    started_at = now or datetime.now(UTC)

    outcome = run_challenger_training(
        inputs,
        training_run_id=_identifier(f"run:{label}"),
        dataset_snapshot_id=_identifier(f"snapshot:{label}"),
        started_at=started_at,
    )
    report = run_report(outcome)

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{label}.run.manifest.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    # A run that honestly reports `not_trainable` succeeded at its job.
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="tools.train", description=__doc__)
    parser.add_argument("--export", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--label", default="challenger")
    args = parser.parse_args(argv)
    return run(args.export, args.out, label=args.label)


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
