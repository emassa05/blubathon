"""Render `data/source-evidence.manifest.json` from an untracked evidence export.

TAREAS M0/P1.3 asks for a non-identifiable manifest with hashes, schemas and
counts so the repository can state what evidence exists without versioning a
single clinical row. The export itself stays out of Git (see `.gitignore`); this
manifest is the only artifact that travels.

Disclosure policy per column kind:

``identifier``
    Counts and an order-independent digest of the distinct values, never the
    values themselves.
``quasi_identifier``
    Same as ``identifier``: an age band plus a diagnosis is linkable when the
    cohort has four people.
``free_text``
    Counts and length statistics only. Clinical free text never leaves the
    clinical boundary (SPEC 2.23).
``closed_category``
    The sorted distinct raw values, because a closed vocabulary is exactly what
    an adapter has to map (SPEC 5.3) and it carries no per-subject information.
``date`` / ``timestamp``
    Month-granularity span and distinct-day counts, never the exact dates of a
    given subject.

Run:

    python -m tools.contracts.source_evidence
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import unicodedata
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EXPORT_DIR = REPO_ROOT / "Datos base"
DEFAULT_OUTPUT = REPO_ROOT / "data" / "source-evidence.manifest.json"

MANIFEST_KIND = "source_evidence"
MANIFEST_VERSION = "1"
SPEC_VERSION = "0.3.0"

ColumnKind = Literal[
    "identifier",
    "quasi_identifier",
    "free_text",
    "closed_category",
    "date",
    "timestamp",
]


@dataclass(frozen=True)
class ColumnPolicy:
    """What may be published about one source column."""

    name: str
    kind: ColumnKind


@dataclass(frozen=True)
class FilePolicy:
    """One expected file of the export and the entity it describes."""

    filename: str
    entity: str
    delimiter: str
    columns: tuple[ColumnPolicy, ...]


def _cols(**kinds: ColumnKind) -> tuple[ColumnPolicy, ...]:
    return tuple(ColumnPolicy(name=name, kind=kind) for name, kind in kinds.items())


# The export is the Bluba client extract. Column names are Spanish because that
# is what the source system emits; the canonical vocabulary lives in
# `packages/shared/field_catalog.py` and the mapping in `ml/adapters`.
EXPORT_POLICY: tuple[FilePolicy, ...] = (
    FilePolicy(
        filename="1_casos_anonimizados.csv",
        entity="subject",
        delimiter=";",
        columns=_cols(
            id_caso="identifier",
            rango_edad="quasi_identifier",
            diagnostico_principal="quasi_identifier",
            perfil_sensorial_predominante="quasi_identifier",
        ),
    ),
    FilePolicy(
        filename="2_programas_y_objetivos.csv",
        entity="care_goal",
        delimiter=";",
        columns=_cols(
            id_objetivo="identifier",
            id_caso="identifier",
            profesion_responsable="closed_category",
            area_intervencion="closed_category",
            descripcion_objetivo="free_text",
            estado_objetivo="closed_category",
        ),
    ),
    FilePolicy(
        filename="3_sesiones_profesionales.csv",
        entity="professional_session",
        delimiter=";",
        columns=_cols(
            id_sesion="identifier",
            id_caso="identifier",
            fecha_sesion="date",
            profesion="closed_category",
            estado_asistencia="closed_category",
            nivel_alerta_inicial="closed_category",
            actividades_realizadas="free_text",
            nivel_alerta_final="closed_category",
            observaciones_profesional="free_text",
        ),
    ),
    FilePolicy(
        filename="4_seguimiento_diario_tutor.csv",
        entity="caregiver_daily_record",
        delimiter=";",
        columns=_cols(
            id_registro_diario="identifier",
            id_caso="identifier",
            fecha="date",
            calidad_sueno="closed_category",
            modo_despertar="closed_category",
            adherencia_medicacion="closed_category",
            estado_gastrointestinal="closed_category",
            nivel_regulacion_general_dia="closed_category",
        ),
    ),
    FilePolicy(
        filename="5_eventos_desregulacion_tutor.csv",
        entity="dysregulation_event",
        delimiter=";",
        columns=_cols(
            id_evento="identifier",
            id_caso="identifier",
            fecha_hora="timestamp",
            tipo_evento="closed_category",
            intensidad="closed_category",
            detonante_gatillante="free_text",
            estrategia_calma_aplicada="free_text",
            resultado_estrategia="closed_category",
        ),
    ),
)

# SPEC 4.3: this label proves the category exists in the export. It does not
# define how a new person should answer, and it is not a target definition.
SEVERE_INTENSITY_LABEL = "Severa (8-10)"
EVENT_FILE = "5_eventos_desregulacion_tutor.csv"
SUBJECT_FILE = "1_casos_anonimizados.csv"
INTENSITY_COLUMN = "intensidad"


def _sha256_hex(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _digest_of_values(values: Iterable[str]) -> str:
    """Order-independent digest of a value set, published instead of the values."""

    joined = "\x00".join(sorted(values))
    return _sha256_hex(joined.encode("utf-8"))


def _normalize(value: str) -> str:
    return unicodedata.normalize("NFC", value).strip()


def _read_rows(path: Path, delimiter: str) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=delimiter)
        header = [_normalize(name) for name in (reader.fieldnames or [])]
        rows = [{_normalize(k): _normalize(v or "") for k, v in row.items()} for row in reader]
    return header, rows


def _month(value: str) -> str | None:
    """Month granularity only: `2026-07-01 16:30` becomes `2026-07`."""

    text = value.strip()
    if len(text) < 7 or text[4] != "-":
        return None
    return text[:7]


def _describe_column(policy: ColumnPolicy, values: Sequence[str]) -> dict[str, Any]:
    present = [value for value in values if value != ""]
    described: dict[str, Any] = {
        "name": policy.name,
        "kind": policy.kind,
        "count": len(values),
        "non_empty_count": len(present),
        "empty_count": len(values) - len(present),
        "distinct_non_empty_count": len(set(present)),
        "distinct_value_digest_sha256": _digest_of_values(present),
    }
    if policy.kind == "closed_category":
        described["distinct_values"] = sorted(set(present))
    elif policy.kind == "free_text":
        lengths = [len(value) for value in present]
        described["character_length"] = {
            "min": min(lengths) if lengths else None,
            "max": max(lengths) if lengths else None,
        }
        described["disclosure_note"] = "clinical free text is never published (SPEC 2.23)"
    elif policy.kind in {"date", "timestamp"}:
        months = sorted({month for value in present if (month := _month(value)) is not None})
        described["month_span"] = {
            "first": months[0] if months else None,
            "last": months[-1] if months else None,
            "distinct_months": len(months),
        }
        described["distinct_day_count"] = len({value[:10] for value in present})
    else:
        described["disclosure_note"] = "values withheld: linkable in a four-subject cohort"
    return described


def _describe_file(policy: FilePolicy, export_dir: Path) -> dict[str, Any]:
    path = export_dir / policy.filename
    if not path.is_file():
        return {
            "filename": policy.filename,
            "entity": policy.entity,
            "status": "missing",
        }
    raw = path.read_bytes()
    header, rows = _read_rows(path, policy.delimiter)
    expected = [column.name for column in policy.columns]
    return {
        "filename": policy.filename,
        "entity": policy.entity,
        "status": "present",
        "bytes": len(raw),
        "content_sha256": _sha256_hex(raw),
        "delimiter": policy.delimiter,
        "encoding": "utf-8",
        "row_count": len(rows),
        "declared_columns": expected,
        "observed_columns": header,
        "schema_matches_policy": header == expected,
        "columns": [
            _describe_column(column, [row.get(column.name, "") for row in rows])
            for column in policy.columns
        ],
    }


def _severe_event_count(export_dir: Path) -> int:
    policy = next(entry for entry in EXPORT_POLICY if entry.filename == EVENT_FILE)
    path = export_dir / policy.filename
    if not path.is_file():
        return 0
    _, rows = _read_rows(path, policy.delimiter)
    counts = Counter(row.get(INTENSITY_COLUMN, "") for row in rows)
    return counts.get(SEVERE_INTENSITY_LABEL, 0)


def _readiness(files: Sequence[dict[str, Any]], export_dir: Path) -> dict[str, Any]:
    """Recompute SPEC 1.2 status from the data instead of hardcoding it."""

    by_name = {entry["filename"]: entry for entry in files}
    subject_count = int(by_name.get(SUBJECT_FILE, {}).get("row_count", 0) or 0)
    event_count = int(by_name.get(EVENT_FILE, {}).get("row_count", 0) or 0)

    return {
        "computed_from": "export row counts, not hardcoded state",
        "real_subject_count": subject_count,
        "real_dysregulation_event_count": event_count,
        "explicit_severe_event_count": _severe_event_count(export_dir),
        "verified_negative_outcome_count": 0,
        "verified_negative_note": (
            "the export records events, not a verified set of non-events; the absence "
            "of a report is never a negative outcome (SPEC 2.9)"
        ),
        "tracks": {
            "synthetic_reference": "simulation_only",
            "real_personal_baseline": "collecting_outcomes",
            "real_logit_challenger": "not_trainable_single_class",
            "rag_catalog": "not_ready",
        },
    }


def build_manifest(export_dir: Path) -> dict[str, Any]:
    files = [_describe_file(policy, export_dir) for policy in EXPORT_POLICY]
    present = [entry for entry in files if entry.get("status") == "present"]
    return {
        "manifest_kind": MANIFEST_KIND,
        "manifest_version": MANIFEST_VERSION,
        "spec_version": SPEC_VERSION,
        "generated_by": "tools.contracts.source_evidence",
        "export": {
            "label": "bluba_client_export",
            "data_origin": "real",
            "cohort_kind": "real_subject",
            "tracked_in_git": False,
            "local_path": "Datos base/",
            "rights_basis": "undeclared",
            "rights_status": "blocked",
            "rights_note": (
                "no licence, consent or institutional basis has been recorded for this "
                "export; until one is, it may not train, calibrate or evaluate a model, "
                "and it may never enter the RAG corpus (SPEC 13.1)"
            ),
            "intended_use": "operational_support",
            "may_mix_with_synthetic": False,
        },
        "disclosure_policy": {
            "identifier": "counts and digest only",
            "quasi_identifier": "counts and digest only",
            "free_text": "counts and length statistics only",
            "closed_category": "sorted distinct raw values",
            "date": "month granularity and distinct-day counts",
            "timestamp": "month granularity and distinct-day counts",
        },
        "files": files,
        "totals": {
            "files_declared": len(EXPORT_POLICY),
            "files_present": len(present),
            "row_count": sum(int(entry.get("row_count", 0) or 0) for entry in present),
        },
        "readiness": _readiness(files, export_dir),
    }


def render(export_dir: Path, output: Path) -> dict[str, Any]:
    manifest = build_manifest(export_dir)
    payload = json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(payload, encoding="utf-8")
    return manifest


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render the source evidence manifest.")
    parser.add_argument("--export-dir", type=Path, default=DEFAULT_EXPORT_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)

    manifest = render(args.export_dir, args.output)
    present = manifest["totals"]["files_present"]
    declared = manifest["totals"]["files_declared"]
    print(f"wrote {args.output} ({present}/{declared} files present)")
    if present != declared:
        print("warning: some declared files are missing from the export directory")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
