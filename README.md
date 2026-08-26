# Blubathon — backend v0.4.0

Blubathon acompaña el seguimiento diario de un niño o niña: registra
observaciones (formulario inteligente), estima con qué probabilidad ocurre un
evento objetivo en la ventana siguiente (modelo predictivo) y, cuando el
riesgo lo amerita, redacta una recomendación breve apoyada en literatura
indexada (sistema RAG).

Blubathon **no** diagnostica, **no** prescribe y **no** reemplaza el criterio
profesional. Es una demo mono-tenant: no hay autenticación, autorización,
sesiones de usuario ni auditoría — todo corre bajo un único tenant fijo.

Este documento describe el backend (`apps/api`, `ml`, `rag`,
`packages/shared`, `tools`). La interfaz visual vive en `apps/mobile` y tiene
su propia documentación.

---

## 1. Las piezas

```text
packages/shared/   el contrato: modelos Pydantic, enums, catálogo de campos,
                    textos en español y utilidades canónicas. No importa a
                    nadie.
ml/                 dominio puro: ml/prediction (modelo), ml/form y
                    ml/defaults (formulario inteligente). Funciones sobre
                    filas ya cargadas; no abren la base ni leen el reloj.
rag/                rag/authoring: BM25, fusión, recuperación, redacción y
                    verificación de citas. rag/domain: documentos, chunking,
                    normalización, guardas de texto.
apps/api/           FastAPI: rutas (apps/api/routes/v1.py), servicios de
                    aplicación (apps/api/services), store SQLite y
                    migraciones. Es quien carga filas y llama al dominio.
tools/               contracts (genera el contrato publicado), seed (datos
                    ficticios), rag_authoring (construye el índice del
                    corpus offline).
```

`lint-imports` hace cumplir la capa: `apps` puede depender de `ml` y `rag`,
nadie depende de `apps`, el store no calcula, y solo
`apps/api/services/recommendations.py` puede alcanzar `rag.authoring` (el
único lugar del sistema con acceso al LLM).

`apps/api/ports/` declara tres protocolos (`defaults`, `form`, `prediction`)
que solo describen la forma del resultado. `FARO_P1_ADAPTERS` elige quién los
implementa (el nombre de la variable es una herencia de nombre interno, no
afecta al producto):

| Adaptador | Cuándo | Qué hace |
|---|---|---|
| `apps/api/adapters/p1` (`FARO_P1_ADAPTERS=real`) | dominio real | llama a `ml/**` sobre filas de la base |
| `apps/api/adapters/mock` (por defecto) | tests y demo rápida | responde con fixtures fijas |

Todo el sistema corre para un solo tenant fijo (`RequestContext`,
`apps/api/context.py`); no hay `Authorization`, `Idempotency-Key` ni `ETag` en
ningún endpoint.

---

## 2. El modelo predictivo (`ml/prediction/`)

Dos tracks, y nunca comparten significado:

### `real_personal_baseline_v1` — el único track visible

Estima la tasa observada del objetivo entre los episodios primarios previos
del **mismo** sujeto, bajo el mismo `care_mode` y la misma definición de
objetivo. No es incidencia diaria, no es riesgo poblacional y no depende de
las respuestas de hoy.

```text
p | D ~ Beta(1 + e, 1 + n - e)
p_mean = (1 + e) / (2 + n)
intervalo = [BetaPPF(0.05), BetaPPF(0.95)]
```

- `e` = resultados positivos verificados, `n` = resultados verificados totales,
  sobre una ventana móvil de **60 días** (`BASELINE_WINDOW_DAYS`).
- Se abstiene (`status=abstained`) si hay **menos de 5** resultados
  verificados (`BASELINE_MIN_OUTCOMES`), si hay un conflicto sin resolver en
  la ventana, o si falta el historial de `care_mode`.
- Código: `ml/prediction/baseline.py::build_personal_baseline`.

### `real_logit_challenger_v1` — siempre en sombra

```text
logit(p_t) = logit(p_base_t) + b0 + b1·sleep_deviation_t + b2·regulation_deviation_t
```

Regresión logística preentrenada, con el baseline como offset de coeficiente
fijo 1, dos predictores preregistrados (desviación de calidad de sueño y de
regulación diaria sobre los últimos 30 días) y `lambda` elegido por
`LeaveOneGroupOut(subject_id)` con Brier fuera de muestra
(`ml/prediction/challenger.py`). **Nunca se expone**: `exposed=False` está
fijo en el adaptador, sin condición, así que ninguna corrida de
entrenamiento cambia ese hecho. Con los datos actuales, además, no hay ambas
clases en las salidas (`not_trainable_single_class`).

### De la probabilidad a la respuesta

`risk_band` (usado por el formulario y por RAG, no por el track en sí):

```text
probability is None       → "unknown"
probability >= 0.5        → "high"
0.2 <= probability < 0.5  → "medium"
probability < 0.2         → "low"
```

---

## 3. El formulario inteligente (`ml/form/`, `ml/defaults/`)

19 campos de observación diaria (`packages/shared/enums.py::FieldCode`):
sueño, despertares nocturnos, apoyo matutino, estado gastrointestinal,
adherencia a medicación, cambios de alimentación/rutina, alerta, eventos de
desregulación, participación en actividades, interacciones sociales,
asistencia, notas libres, etc.

### El orden de las preguntas (`ml/form/plan.py::build_form_plan`)

Seis bloques, en este orden exacto:

1. **Vencidas por antigüedad** — todo campo monitoreado sin presentarse hace
   ≥7 días (`STALENESS_CEILING_DAYS`), o nunca presentado.
2. **Cupo de exploración** — un día ISO por semana, elegido de forma estable
   por `HMAC(secreto, tenant, sujeto, semana, versión_política) mod 7`; toma
   el campo aplicable menos presentado en los últimos 60 días.
3. **VoI** — mayor información de valor disponible, descendente (ver abajo).
4. **Orden canónico** — llena los cupos que falten con el orden fijo del
   catálogo.
5. **Cola** — el resto de los campos aplicables, sin destacar. Ningún campo
   queda inaccesible: "destacado" es solo prioridad de atención.

El número de cupos destacados es 3 si la cobertura de datos del sujeto está
por debajo de 0.5 (`LOW_COVERAGE_THRESHOLD`), si no 2
(`FORM_HIGHLIGHTED_DEFAULT`/`FORM_HIGHLIGHTED_LOW_COVERAGE`).

**VoI está definido pero no conectado**: `ml/form/voi.py` implementa
información mutua aproximada, pero `POST /v1/children/{id}/form-plan`
siempre responde `voi_status: "unavailable_model"` y `voi_nats: null` — no
existe todavía un modelo condicional de outcome que lo alimente. El motivo de
pregunta `"voi"` nunca aparece en la respuesta pública; se usa
`"canonical_order"` en su lugar.

### Los defaults sugeridos (`ml/defaults/estimator.py`)

Solo 5 campos pueden sugerir un valor (`DEFAULT_ALLOWLIST_V1`):
`food_changes`, `activity_participation`, `social_interactions`,
`eating_status`, `attendance_status`.

- **Binario**: `Beta(1+k, 1+N-k)` sobre `N` observaciones elegibles en 60
  días del mismo tenant/sujeto/fuente/campo.
- **Categórico/ordinal**: `Dirichlet(1 + n_j)` sobre el soporte cerrado; el
  candidato es el `argmax`; un empate no sugiere nada.
- Se sugiere solo si el **límite inferior** del 5% del posterior supera
  **0.70** (`DEFAULT_LOWER_THRESHOLD`) — se muestra el límite conservador, no
  la media, porque dos historiales con la misma media pueden tener evidencia
  muy distinta.

### Enviar el formulario (`POST /v1/children/{id}/forms`)

Una respuesta con `interaction: "unknown"` nunca genera una observación (no
es `null`, no es `false`, no cuenta). Al guardarse: crea o enlaza un episodio
de predicción, dispara la predicción del baseline, abre un `outcome_request`
y deja una recomendación en `status="pending"` — el RAG corre después, en
segundo plano.

---

## 4. El sistema RAG (`rag/`, `apps/api/services/recommendations.py`)

Dos mitades con roles distintos.

### Autoría (offline, `rag/authoring/`, `tools/rag_authoring/cli.py`)

Construye el índice a partir de documentos versionados en texto plano
(`.txt`/`.md`, sin extracción de PDF): los divide en chunks
(`rag/domain/chunking.py`), normaliza el texto, calcula hashes y arma un
manifiesto reproducible (`rag-build.manifest.json`). Este paso corre por CLI,
nunca por HTTP.

### Runtime (online, disparado tras cada envío del formulario)

1. **`query_es`** (`apps/api/services/recommendation_query.py::query_for`) —
   arma una consulta en español a partir de las respuestas (excluyendo texto
   libre), con el `risk_band` como prefijo:
   `"Riesgo alto. Calidad del sueño : Interrumpido. ..."`.
2. **Recuperación** — BM25 léxico puro (`Bm25Index` +
   `rag/authoring/retrieval.py::retrieve`, modo `lexical_only` en este
   despliegue: no hay recuperador denso configurado). Sin coincidencias →
   `status="abstained"`, `abstention_reason="no_indexed_match"`.
3. **Redacción** (`rag/authoring/drafting.py::request_draft`) — el único
   punto del sistema donde puede intervenir un LLM, y solo recibe los chunks
   recuperados: nunca identidad, notas ni texto libre del cuidador. Sin un
   `draft_transport` configurado (el caso por defecto en esta demo, ver §6),
   → `abstention_reason="draft_unavailable"`.
4. **Verificación de citas** (`rag/domain/citations.py::verify_citation`) —
   cada cita del borrador debe ser una cita **literal** de un chunk
   recuperado. Si alguna no lo es → `abstention_reason="draft_not_grounded"`.
   Ninguna fila `status="matched"` existe con una cita no verificada.
5. Con todo verificado: `status="matched"`, se persisten `action_text_es`,
   `purpose_es` y las citas.

**Retroalimentación** (`POST /v1/recommendations/{id}/feedback` con
`rating: "bad"`) dispara una regeneración en segundo plano que excluye los
chunks ya usados e incrementa `attempt`.

Todo evento (`recommendation.ready`, `recommendation.redrafted`,
`feedback.recorded`) se publica por `WS /v1/ws` después de que la transacción
que lo originó hizo commit.

---

## 5. API

Prefijo `/v1`. Sin autenticación. Los ejemplos son literales, generados por
`tools.contracts.examples` a partir del contrato publicado
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

Entrada:

```json
{"source": "caregiver_daily", "answers": {"sleep_quality": "interrupted"}}
```

Salida:

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

Entrada:

```json
{
  "source": "caregiver_daily",
  "local_date": "2026-08-25",
  "answers": [
    {"field_code": "sleep_quality", "value": "interrupted", "interaction": "manual"}
  ]
}
```

Salida (`201`) — `recommendation_instance_id` referencia una fila `pending`
en el instante de la respuesta; el RAG corre después, en segundo plano:

```json
{
  "submission_id": "c8d87770-b0c0-51a6-bdd5-f31fad4af9d5",
  "status": "episode_created",
  "prediction_episode_id": "f26081f2-9dfe-57e7-ad1b-c2005526e2c3",
  "recommendation_instance_id": "364adb48-2a43-52d6-a324-9236a1ee9771",
  "outcome_request_id": "81ac1cb1-093d-5aa4-a301-1b573ee7e7f5"
}
```

`status` también puede ser `episode_linked` (ya había un episodio primario
abierto ese día) o `target_definition_unavailable` (fail-closed: no hay una
única definición de objetivo activa).

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

Cada `item` tiene la forma completa de una recomendación; dos ejemplos, uno
resuelto y uno abstenido:

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

`abstention_reason` toma `no_indexed_match`, `draft_unavailable` o
`draft_not_grounded` — ver §4.

### `POST /v1/recommendations/{recommendation_instance_id}/feedback`

Entrada:

```json
{"rating": "good", "note_es": null}
```

Salida (`201`) — `rating: "bad"` dispara una regeneración en segundo plano;
`attempt` es el valor antes de que esa regeneración termine:

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

Entrada (un reporte afirmativo declara cuándo ocurrió; cualquier otro valor,
nunca):

```json
{"value": "yes", "occurred_at": "2026-08-26T09:00:00Z"}
```

Salida (`201`):

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

Sin autenticación ni filtro por `child_id`. Eventos:

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

## 6. Cómo correr el backend

```bash
# 1. Sembrar la base local (datos completamente ficticios).
python -m tools.seed

# 2. Levantar la API.
uvicorn "apps.api.main:create_app" --factory --host 127.0.0.1 --port 8000

#    Contra el dominio real de ml/ y rag/ en vez de los mocks:
FARO_P1_ADAPTERS=real uvicorn "apps.api.main:create_app" --factory --port 8000
```

`GET /health` dice contra qué está corriendo:
`{"status": "ok", "spec_version": "0.4.0", "mode": "demo", "adapters": "p1"}`.
La documentación OpenAPI vive en `/docs` y se deshabilita sola en modo piloto
(`FARO_MODE=pilot`).

Por defecto no hay ningún `draft_transport` conectado, así que toda
recomendación con chunks indexados abstiene con `draft_unavailable` — el LLM
de redacción se conecta pasando un `DraftTransport`
(`rag/authoring/drafting.py`) a `create_app(..., draft_transport=...)`.

### Variables de entorno

Conservan el prefijo interno `FARO_` (no es el nombre del producto, es un
identificador de configuración heredado):

| Variable | Por defecto | Para qué |
|---|---|---|
| `FARO_MODE` | `demo` | `pilot` exige PostgreSQL y bloquea el arranque sobre SQLite |
| `FARO_DB_PATH` | `data/faro.db` | Base SQLite local |
| `FARO_CORS_ORIGINS` | `http://127.0.0.1:3000,http://localhost:3000` | Allowlist explícita |
| `FARO_P1_ADAPTERS` | `mock` | `real` corre contra `ml/**` y `rag/authoring` |

---

## 7. Verificación

```bash
# Contrato: nada de generated/ ni examples/ se edita a mano.
python -m tools.contracts.generate
python -m tools.contracts.examples
git diff --exit-code packages/shared/generated packages/shared/examples

# Backend
ruff check . && ruff format --check .
lint-imports
pytest tests -q

# El camino real existe de verdad, no solo el mock.
FARO_P1_ADAPTERS=real pytest tests/integration -q
```

`lint-imports` verifica, entre otras cosas, que solo
`apps/api/services/recommendations.py` alcanza `rag.authoring` — es la única
puerta al LLM del sistema.
