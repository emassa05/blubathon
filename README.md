# Faro

Faro is a deterministic next-day dysregulation risk engine. The repository contains a pure
Python ML domain and a thin FastAPI transport under `/api/v1`.

## Setup

Python 3.12 is the supported runtime.

```bash
python -m pip install -e ".[dev]"
```

Generate the reproducible synthetic dataset:

```bash
python -m ml.synth.generate --output-dir data
```

Run the API:

```bash
uvicorn apps.api.main:app --reload --port 8000
```

OpenAPI is available at `http://localhost:8000/docs`. Concrete persistence, VoI, narrative,
strategy, and evaluation services are registered through `apps.api.services.configure_services`.

## Verification

```bash
ruff check .
ruff format --check .
pytest tests/p1 -q
lint-imports
```

## Architecture

Dependencies flow in one direction:

```text
apps/api -> ml/engine -> ml/features -> ml/synth
                    -> ml/spec_constants
                    -> packages/shared
```

The `ml` package never imports application, HTTP, SQLite, or filesystem concerns. Generated
datasets and trained models remain local and are excluded from version control.
