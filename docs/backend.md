# Blubathon — backend v0.4.0

Referencia técnica del backend: formulario inteligente → modelo predictivo →
recomendación RAG. Mono-tenant, sin autenticación/autorización/auditoría. Para
qué es y qué permite hacer, ver el [README](../README.md).

Cubre `apps/api`, `ml`, `rag`, `packages/shared`, `tools`. UI en
`apps/mobile`, conectada a esta API y tipada contra el mismo
contrato generado: `packages/shared/generated` se publica como el paquete
`@blubathon/contract` y la interfaz lo importa, así que un cambio de contrato rompe
su compilación.

---

## 1. Piezas

| Paquete | Contiene |
|---|---|
| `packages/shared/` | Contrato: modelos Pydantic, enums, catálogo de campos, textos ES. No importa a nadie. |
| `ml/` | Dominio puro. `ml/prediction` (modelo), `ml/form` + `ml/defaults` (formulario). Funciones sobre filas ya cargadas, sin I/O. |
| `rag/` | `rag/authoring`: BM25, fusión, recuperación, redacción, verificación de citas. `rag/domain`: documentos, chunking, normalización. |
| `apps/api/` | FastAPI. Rutas en `routes/v1.py`, servicios en `services/`, store SQLite + migraciones. |
| `tools/` | `contracts` (genera el contrato publicado), `seed` (datos ficticios), `rag_authoring` (build offline del índice). |

`lint-imports`: `apps` depende de `ml`/`rag`, nadie depende de `apps`, el
store no calcula, y solo `apps/api/services/recommendations.py` importa
`rag.authoring` (única puerta al LLM).

`apps/api/ports/` define 3 protocolos (`defaults`, `form`, `prediction`).
`BLUBATHON_P1_ADAPTERS` elige la implementación:

| Adaptador | Env | Comportamiento |
|---|---|---|
| `apps/api/adapters/p1` | `real` | llama a `ml/**` sobre filas de la base |
| `apps/api/adapters/mock` | `mock` (default) | fixtures fijas, sin fórmulas |

Un solo tenant fijo (`apps/api/context.py::RequestContext`). Sin
`Authorization`, `Idempotency-Key`, `ETag`.

---

## 2. Modelo predictivo — `ml/prediction/`

Dos tracks, significados no intercambiables.

**`real_personal_baseline_v1`** (único track visible) — tasa observada del
objetivo entre episodios primarios previos del mismo sujeto, mismo
`care_mode`, misma definición de objetivo.

```text
p | D ~ Beta(1+e, 1+n-e)
p_mean = (1+e) / (2+n)
intervalo = [BetaPPF(0.05), BetaPPF(0.95)]
```

- `e`/`n` = outcomes positivos/totales verificados, ventana móvil 60 días (`BASELINE_WINDOW_DAYS`).
- Abstiene si `n < 5` (`BASELINE_MIN_OUTCOMES`), conflicto sin resolver en ventana, o falta `care_mode`.
- `ml/prediction/baseline.py::build_personal_baseline`.

**`real_logit_challenger_v1`** (siempre en sombra, `exposed=False` fijo):

```text
logit(p_t) = logit(p_base_t) + b0 + b1·sleep_deviation_t + b2·regulation_deviation_t
```

Offset = baseline (coef. fijo 1), 2 predictores preregistrados (desviación
sueño/regulación, ventana 30 días), `lambda` por
`LeaveOneGroupOut(subject_id)` + Brier out-of-fold
(`ml/prediction/challenger.py`). Con los datos actuales:
`not_trainable_single_class`.

**`risk_band`** (consumido por formulario y RAG, no por el track):

```text
None → unknown | ≥0.5 → high | 0.2–0.5 → medium | <0.2 → low
```

---

## 3. Formulario inteligente — `ml/form/`, `ml/defaults/`

19 campos (`FieldCode`): sueño, despertares, apoyo matutino, GI, medicación,
alimentación/rutina, alerta, desregulación, actividad, social, asistencia,
notas, etc.

**Orden de preguntas** (`ml/form/plan.py::build_form_plan`), 5 bloques:

1. Vencidas por antigüedad (≥7 días sin presentarse, `STALENESS_CEILING_DAYS`, o nunca presentadas).
2. Exploración: 1 día ISO/semana vía `HMAC(secreto, tenant, sujeto, semana, política) mod 7`, campo menos presentado en 60 días.
3. VoI: mayor información de valor disponible, descendente.
4. Orden canónico: llena cupos restantes.
5. Cola: resto de campos aplicables, sin destacar — todo campo sigue accesible.

Cupos destacados: 3 si cobertura < 0.5 (`LOW_COVERAGE_THRESHOLD`), si no 2.

**VoI implementado, no conectado**: `ml/form/voi.py` calcula información
mutua, pero `POST /v1/children/{id}/form-plan` siempre devuelve
`voi_status: "unavailable_model"`, `voi_nats: null` — no hay modelo
condicional que lo alimente. Razón `"voi"` nunca sale en la API; se usa
`"canonical_order"`.

**Defaults** (`ml/defaults/estimator.py`) — 5 campos elegibles
(`DEFAULT_ALLOWLIST_V1`): `food_changes`, `activity_participation`,
`social_interactions`, `eating_status`, `attendance_status`.

- Binario: `Beta(1+k, 1+N-k)`, ventana 60 días.
- Categórico/ordinal: `Dirichlet(1+n_j)` sobre soporte cerrado, candidato = `argmax`, empate = sin sugerencia.
- Umbral: límite inferior del posterior (q=0.05) > `0.70` (`DEFAULT_LOWER_THRESHOLD`).

**`POST /v1/children/{id}/forms`**: `interaction: "unknown"` nunca genera
observación. Al guardar: crea/enlaza episodio, corre baseline, abre
`outcome_request`, deja recomendación en `pending` (RAG corre después, en
background).

---

## 4. Sistema RAG — `rag/`, `apps/api/services/recommendations.py`

**Autoría** (offline, `tools/rag_authoring/cli.py`): documentos versionados →
chunking → normalización → hash → manifiesto reproducible. Solo CLI, nunca
HTTP. Ese comando **no escribe en la base**; para cargar un documento al
índice que consulta el runtime, usá `tools.rag_authoring.load_local` (§6).

**Runtime** (online, tras cada envío de formulario):

1. `query_for()` construye consulta ES desde las respuestas (sin texto libre), prefijo = `risk_band`: `"Riesgo alto. Calidad del sueño : Interrumpido. ..."`.
2. Recuperación: BM25 puro, modo `lexical_only` (sin recuperador denso configurado). Sin match → `abstained` / `no_indexed_match`.
3. Redacción (`request_draft`): único punto con acceso a LLM, solo recibe chunks recuperados (sin identidad/notas/texto libre). Sin `draft_transport` configurado → `abstained` / `draft_unavailable`. `rag/authoring/transports.py` da dos: `anthropic` (`claude-opus-5`) y `ollama` (local, cualquier modelo servido por Ollama) — ambos con el `output_schema` del prompt versionado forzando la forma de salida.
4. Verificación de citas (`verify_citation`): cada cita debe ser literal de un chunk recuperado. Si no → `abstained` / `draft_not_grounded`. Ninguna fila `matched` tiene cita no verificada.
5. Todo verificado → `matched`, se persiste `action_text_es`, `purpose_es`, citas.

**Feedback** (`POST /v1/recommendations/{id}/feedback`, `rating: "bad"`):
regenera en background excluyendo chunks usados, incrementa `attempt`.

Eventos (`recommendation.ready`, `recommendation.redrafted`,
`feedback.recorded`) publicados por `WS /v1/ws` post-commit.

---

## 5. API

Prefijo `/v1`. Sin auth. Ejemplos generados por `tools.contracts.examples`
(`packages/shared/examples/valid/`).

### `GET /v1/children`

```json
{
  "children": [
    {"child_id": "371c1a87-95e0-5025-9dad-ab57fc9a0b91", "display_label": "Niño demo"}
  ]
}
```

### `GET /v1/children/{child_id}`

```json
{
  "child_id": "371c1a87-95e0-5025-9dad-ab57fc9a0b91",
  "display_label": "Niño demo",
  "care_mode": "home",
  "profile_version": "1.0.0",
  "prediction_episode_id": "f26081f2-9dfe-57e7-ad1b-c2005526e2c3"
}
```

### `GET /v1/children/{child_id}/history?limit=30`

```json
{
  "child_id": "371c1a87-95e0-5025-9dad-ab57fc9a0b91",
  "days": [
    {
      "local_date": "2026-08-25",
      "submission_id": "c8d87770-b0c0-51a6-bdd5-f31fad4af9d5",
      "prediction_episode_id": "f26081f2-9dfe-57e7-ad1b-c2005526e2c3",
      "prediction": {"status": "ok", "probability": 0.34, "interval": [0.12, 0.61]},
      "recommendation": {
        "recommendation_instance_id": "364adb48-2a43-52d6-a324-9236a1ee9771",
        "status": "matched",
        "rating": "good"
      },
      "outcome": {"status": "yes", "reported_at": "2026-08-26T09:00:00Z"}
    }
  ]
}
```

### `POST /v1/children/{child_id}/form-plan` — sin escritura

```json
{"source": "caregiver_daily", "answers": {"sleep_quality": "interrupted"}}
```
→
```json
{
  "questions": [
    {"field_code": "routine_changes", "highlighted": true, "reason": "staleness", "voi_nats": null}
  ],
  "defaults": [],
  "voi_status": "unavailable_model",
  "coverage": 0.62
}
```

### `POST /v1/children/{child_id}/forms`

```json
{
  "source": "caregiver_daily",
  "local_date": "2026-08-25",
  "answers": [
    {"field_code": "sleep_quality", "value": "interrupted", "interaction": "manual"}
  ]
}
```
→ `201`, `recommendation_instance_id` en `pending` en el instante de la
respuesta (RAG corre async):
```json
{
  "submission_id": "c8d87770-b0c0-51a6-bdd5-f31fad4af9d5",
  "status": "episode_created",
  "prediction_episode_id": "f26081f2-9dfe-57e7-ad1b-c2005526e2c3",
  "recommendation_instance_id": "364adb48-2a43-52d6-a324-9236a1ee9771",
  "outcome_request_id": "81ac1cb1-093d-5aa4-a301-1b573ee7e7f5"
}
```

`status` también: `episode_linked` (episodio primario ya abierto ese día),
`target_definition_unavailable` (fail-closed).

### `GET /v1/children/{child_id}/recommendations/today`

```json
{
  "status": "matched",
  "risk_band": "high",
  "recommendation_instance_id": "364adb48-2a43-52d6-a324-9236a1ee9771",
  "action_text_es": "Anticipa la siguiente actividad con una señal breve.",
  "purpose_es": "Facilitar una transición predecible.",
  "citations": [
    {
      "document_title_es": "Guía ficticia de apoyo",
      "locator": "p. 4",
      "quote_es": "Mantener una rutina predecible puede facilitar las transiciones."
    }
  ],
  "rating": null
}
```

Sin envío hoy → `{"status": "no_submission_today"}`.

### `GET /v1/recommendations?status=matched&child_id=...&limit=50`

Resuelto:
```json
{
  "recommendation_instance_id": "364adb48-2a43-52d6-a324-9236a1ee9771",
  "child_id": "371c1a87-95e0-5025-9dad-ab57fc9a0b91",
  "prediction_episode_id": "f26081f2-9dfe-57e7-ad1b-c2005526e2c3",
  "created_at": "2026-08-25T19:55:00.000Z",
  "risk_band": "high",
  "query_es": "Riesgo alto. Calidad del sueño : Interrumpido",
  "status": "matched",
  "action_text_es": "Anticipa la siguiente actividad con una señal breve.",
  "purpose_es": "Facilitar una transición predecible.",
  "citations": [
    {
      "document_title_es": "Guía ficticia de apoyo",
      "locator": "p. 4",
      "quote_es": "Mantener una rutina predecible puede facilitar las transiciones."
    }
  ],
  "attempt": 1
}
```

Abstenido:
```json
{
  "recommendation_instance_id": "364adb48-2a43-52d6-a324-9236a1ee9771",
  "child_id": "371c1a87-95e0-5025-9dad-ab57fc9a0b91",
  "prediction_episode_id": "f26081f2-9dfe-57e7-ad1b-c2005526e2c3",
  "created_at": "2026-08-25T19:55:00.000Z",
  "risk_band": "unknown",
  "query_es": "Calidad del sueño : Interrumpido",
  "status": "abstained",
  "citations": [],
  "abstention_reason": "no_indexed_match",
  "attempt": 1
}
```

`abstention_reason`: `no_indexed_match` | `draft_unavailable` |
`draft_not_grounded` (§4).

### `POST /v1/recommendations/{recommendation_instance_id}/feedback`

```json
{"rating": "good", "note_es": null}
```
→ `201`, `rating: "bad"` dispara regeneración async; `attempt` es el valor
previo a esa regeneración:
```json
{"feedback_id": "8f1e2b7a-2b8e-5c3f-9e1a-4d6f8a2b1c3d", "rating": "good", "attempt": 1}
```

### `GET /v1/prediction-episodes/{prediction_episode_id}`

```json
{
  "prediction_episode_id": "f26081f2-9dfe-57e7-ad1b-c2005526e2c3",
  "subject_id": "371c1a87-95e0-5025-9dad-ab57fc9a0b91",
  "as_of_at": "2026-08-25T19:55:00.000Z",
  "prediction_at": "2026-08-25T19:55:00.000Z",
  "target_start_at": "2026-08-25T19:55:00.000Z",
  "target_end_at": "2026-08-26T19:55:00.000Z",
  "capture_deadline_at": "2026-08-27T19:55:00.000Z",
  "target_definition_version": "1.0.0",
  "outputs": [
    {
      "track_id": "real_personal_baseline_v1",
      "intended_use": "operational_support",
      "status": "ok",
      "estimate_kind": "personal_observed_episode_rate",
      "probability": 0.34,
      "interval": {"lower": 0.12, "upper": 0.61},
      "interval_method": "beta_posterior_quantile",
      "abstention_reasons": [],
      "model_version": "real-personal-baseline-0.3.0",
      "input_data_origin": "real"
    }
  ],
  "decision_policy_version": null,
  "risk_band": null
}
```

### `POST /v1/prediction-episodes/{prediction_episode_id}/outcome-reports`

`occurred_at` solo en reporte `yes`:
```json
{"value": "yes", "occurred_at": "2026-08-26T09:00:00Z"}
```
→ `201`:
```json
{
  "report": {
    "outcome_report_id": "b3f0e6d1-4a2c-5f8e-9b1a-2c3d4e5f6a7b",
    "prediction_episode_id": "f26081f2-9dfe-57e7-ad1b-c2005526e2c3",
    "value": "yes",
    "occurred_at": "2026-08-26T09:00:00Z",
    "reported_at": "2026-08-26T09:00:05Z",
    "timing_status": "on_time",
    "reporter_role": "caregiver",
    "intake_channel": "form",
    "target_definition_version": "1.0.0"
  },
  "resolution": {
    "status": "yes",
    "resolved_at": "2026-08-26T09:00:05Z",
    "qualifying_report_id": "b3f0e6d1-4a2c-5f8e-9b1a-2c3d4e5f6a7b",
    "ever_conflicted": false,
    "resolution_version": 1
  },
  "request_state": "reported"
}
```

### `GET /v1/outcome-requests`

```json
{
  "items": [
    {
      "outcome_request_id": "81ac1cb1-093d-5aa4-a301-1b573ee7e7f5",
      "prediction_episode_id": "f26081f2-9dfe-57e7-ad1b-c2005526e2c3",
      "subject_id": "371c1a87-95e0-5025-9dad-ab57fc9a0b91",
      "target_definition_version": "1.0.0",
      "question_es": "¿Ocurrió el evento objetivo en la ventana declarada?",
      "target_start_at": "2026-08-25T19:55:00.000Z",
      "target_end_at": "2026-08-26T19:55:00.000Z",
      "capture_deadline_at": "2026-08-27T19:55:00.000Z",
      "state": "open",
      "resolution_status": "pending"
    }
  ]
}
```

### `WS /v1/ws`

Sin auth ni filtro por `child_id`.

```json
{"type": "recommendation.ready", "child_id": "371c1a87-95e0-5025-9dad-ab57fc9a0b91",
 "prediction_episode_id": "f26081f2-9dfe-57e7-ad1b-c2005526e2c3",
 "recommendation_instance_id": "364adb48-2a43-52d6-a324-9236a1ee9771", "status": "abstained",
 "abstention_reason": "draft_unavailable", "at": "2026-08-25T19:55:03.000Z"}
```
```json
{"type": "recommendation.redrafted",
 "recommendation_instance_id": "364adb48-2a43-52d6-a324-9236a1ee9771",
 "attempt": 2, "status": "matched", "at": "2026-08-25T20:10:00.000Z"}
```
```json
{"type": "feedback.recorded",
 "recommendation_instance_id": "364adb48-2a43-52d6-a324-9236a1ee9771",
 "rating": "bad", "at": "2026-08-25T20:09:00.000Z"}
```

---

## 6. Correr el backend

```bash
python -m tools.seed
uvicorn "apps.api.main:create_app" --factory --host 127.0.0.1 --port 8000

# dominio real + RAG con redacción vía API de Claude:
export ANTHROPIC_API_KEY=sk-ant-...
BLUBATHON_P1_ADAPTERS=real BLUBATHON_DRAFT_LLM=anthropic \
  uvicorn "apps.api.main:create_app" --factory --port 8000

# o local, con Ollama corriendo (ollama pull qwen2.5:7b-instruct):
BLUBATHON_P1_ADAPTERS=real BLUBATHON_DRAFT_LLM=ollama \
  uvicorn "apps.api.main:create_app" --factory --port 8000
```

`GET /health` → `{"status": "ok", "spec_version": "0.4.0", "mode": "demo",
"adapters": "p1"}`. OpenAPI en `/docs`, deshabilitado en modo piloto
(`BLUBATHON_MODE=pilot`).

### Cargar documentos al corpus

`tools.rag_authoring build` escribe manifiestos offline, no toca la base. Para
que el runtime pueda recuperar de un documento, cargalo con:

```bash
python -m tools.rag_authoring.load_local --db data/blubathon.db \
    --title "Guía de apoyos" --file guia.pdf
```

Acepta PDF (vía `pypdf`), `.txt` y `.md`. Un PDF escaneado sin capa de texto
falla explícito en vez de cargar un documento vacío — eso necesita OCR, que no
está en el repo. El chunking es el real (`rag/domain/chunking.py`), así que lo
cargado es indistinguible de lo que produciría el pipeline de autoría.

| Variable | Default | Efecto |
|---|---|---|
| `BLUBATHON_MODE` | `demo` | `pilot` exige PostgreSQL, bloquea arranque sobre SQLite |
| `BLUBATHON_DB_PATH` | `data/blubathon.db` | Ruta SQLite |
| `BLUBATHON_CORS_ORIGINS` | `http://127.0.0.1:3000,http://localhost:3000` | Allowlist CORS. En desarrollo no hace falta: `apps/mobile` sale por su propio proxy |
| `BLUBATHON_P1_ADAPTERS` | `mock` | `real` → `ml/**` + `rag/authoring` |
| `BLUBATHON_DRAFT_LLM` | — | `anthropic` (necesita `ANTHROPIC_API_KEY`) o `ollama` (local) |
| `BLUBATHON_OLLAMA_MODEL` | `qwen2.5:7b-instruct` | Modelo servido por Ollama |
| `BLUBATHON_OLLAMA_URL` | `http://127.0.0.1:11434` | Daemon de Ollama |

---

## 7. Verificación

```bash
python -m tools.contracts.generate
python -m tools.contracts.examples
git diff --exit-code packages/shared/generated packages/shared/examples

ruff check . && ruff format --check .
lint-imports
pytest tests -q

BLUBATHON_P1_ADAPTERS=real pytest tests/integration -q
```

`lint-imports` verifica, entre otras cosas, que solo
`apps/api/services/recommendations.py` alcanza `rag.authoring`.
