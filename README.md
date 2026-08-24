# Faro

Faro estimates the risk that a neurodivergent child has a behavioural crisis
**tomorrow**, from what families, therapists and schools record today. It is
built for the case that actually happens: the data is incomplete, and the days
with least data are the days that matter most.

Three things make that workable:

- **It abstains.** Below a data-quality floor it returns "not enough yet"
  instead of a number, and says which answer would help most.
- **It asks for the least it can.** A Value-of-Information loop ranks the
  unanswered questions by how much each would move today's estimate, so a
  family answers two or three instead of fifteen.
- **The number is never written by a language model.** A calibrated LightGBM
  ensemble produces the probability and its interval; the local LLM only puts
  it into words, and falls back to a deterministic template.

`SPEC.v0.2.0.bak.md` is the frozen contract. `CONVENTIONS.md` is how the code is
written. `TAREAS.md` is the division of work.

## Setup

Python 3.12 is the supported runtime.

```bash
python -m pip install -e ".[dev]"
```

Three commands take you from an empty checkout to a running API:

```bash
python -m ml.synth.generate --output-dir data     # 200 children x 180 days
python -m ml.train --data-dir data                # 20 models + the SPEC 13 report
python -m apps.api.store.seed --limit-children 12 # fixtures + Bluba + a demo cohort
```

Then:

```bash
uvicorn apps.api.main:app --reload --port 8000
```

OpenAPI lives at `http://localhost:8000/docs`. Without a trained artifact every
scoring route answers `503 model_not_ready` rather than guessing.

## The eight endpoints

All of them take `date` as **the day being recorded**. Only `/predict` answers
about the day after, and its response carries that `t+1` date.

| Method | Route | Answers |
|---|---|---|
| POST | `/api/v1/ingest` | store one `DailyLog` or a list, idempotent per `(child_id, date, source)` |
| GET | `/api/v1/predict` | risk, band, 80% interval, confidence, ICD — or a documented abstention |
| GET | `/api/v1/voi` | the adaptive form: highlighted questions, filter question, tail |
| GET | `/api/v1/explain` | drivers, narrative, candidate strategies |
| POST | `/api/v1/counterfactual` | risk before and after changing today's answers |
| GET | `/api/v1/quality` | ICD and its three components |
| POST | `/api/v1/feedback` | what actually happened, and whether a strategy helped |
| GET | `/api/v1/eval` | the full SPEC 13 report, computed at training time |

## Where Bluba's own data fits

`ml/adapters/bluba.py` is the single place where the platform's categorical
vocabulary becomes canonical values — `Reparador` becomes `sleep_quality = 5`,
`No Aplica` becomes `medication_adherence = "not_applicable"`. The four
anonymised cases load into the demo database next to the synthetic cohort.

The model still trains on synthetic data: four children over one month is not a
training set, and the export carries no crisis label. Only a severe event
becomes `crisis_occurred = true`; every other day stays `null`, because the
absence of a logged event is not evidence that nothing happened.

## Verification

```bash
ruff check .
ruff format --check .
pytest tests -q
lint-imports
```

## Architecture

Dependencies flow one way:

```text
apps/api -> ml/engine -> ml/features -> ml/synth
                     -> ml/voi, ml/narrative, ml/strategies, ml/eval
                     -> ml/adapters
                     -> ml/spec_constants, packages/shared
```

`ml/` never imports application, HTTP, or SQLite concerns; `import-linter`
enforces it. Generated datasets and trained models stay out of version control.
