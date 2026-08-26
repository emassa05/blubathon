# Contrato del backend de Faro — v0.3.0

Estado del contrato, tal como está implementado hoy en el repositorio. No es una
propuesta: cada ruta, campo, enum, constante y código de error de este documento
sale del código que corre.

- **`spec_version`**: `0.3.0` (constante `C01`)
- **`contract_version`**: `faro-contract-0.3.0`
- **`schema_hash`**: `8c4c956037e952b0666b8f99722d07faaf09bb11528a1072f20b91c811cee526`
  (léelo siempre de `packages/shared/generated/contract.lock.json`, no de aquí:
  un hash copiado en prosa se pudre)
- **143 definiciones** en el bundle JSON Schema, **87 modelos publicados**

## Fuentes de verdad

| Qué | Dónde |
|---|---|
| Modelos Pydantic (fuente de verdad) | `packages/shared/domain/**`, reexportados por `packages/shared/models.py` |
| Extensiones de producto de P2 | `apps/api/contracts/models.py` (subclases, nunca copias) |
| Vocabularios cerrados | `packages/shared/enums.py` |
| Catálogo de campos y matriz de fuentes | `packages/shared/field_catalog.py` |
| Constantes C01–C50 | `packages/shared/constants.py` |
| Textos en español | `packages/shared/texts.py` |
| Rutas HTTP | `apps/api/routes/v1.py` |
| Traducción de errores a HTTP | `apps/api/errors.py`, `apps/api/main.py` |
| JSON Schema / TypeScript / Zod | `packages/shared/generated/` |
| Ejemplos válidos e inválidos | `packages/shared/examples/` |

Nada bajo `generated/` ni `examples/` se edita a mano:

```bash
python -m tools.contracts.generate
python -m tools.contracts.examples
git diff --exit-code packages/shared/generated packages/shared/examples
```

---

## 1. Convenciones transversales

### 1.1 Prefijo y documentación

- Todas las rutas de producto cuelgan de **`/api/v1`** (`C02`).
- `GET /health` y `/docs` viven fuera del prefijo.
- `/docs` y `/openapi.json` **solo existen en `FARO_MODE=demo`**; el modo piloto
  los deshabilita (`CONVENTIONS 15`).

### 1.2 Autenticación

```http
Authorization: Bearer <demo_session_token>
```

En modo demo el token busca un usuario sembrado en `users.demo_session_token`.
**El modo piloto rechaza este autenticador** (`invalid_credentials`, 401): el
piloto exige OIDC y todavía no está implementado.

Tokens de demostración sembrados por `python -m tools.seed`:

| Token | Persona ficticia | Rol |
|---|---|---|
| `demo-cuidadora-ana` | Ana Ríos | `caregiver` |
| `demo-profesional-a` | Pilar Soto | `professional` acreditada |
| `demo-evaluador-a` | Evaluador Demo A | `model_evaluator` |
| `demo-profesional-sin-acreditacion` | — | `professional` sin acreditación vigente |
| `demo-cuidador-b` | — | `caregiver` de otra organización |

### 1.3 Autorización

Tenant + rol **no bastan**. Toda operación clínica exige además un
`SubjectAccessGrant` activo con la capability literal de la operación
(`SPEC 2.26`). Matriz mínima (`OPERATION_MATRIX`, `packages/shared/domain/identity.py`):

| Operación | Roles permitidos | Grant capability | Acreditación | Nota |
|---|---|---|---|---|
| `read_subject_or_form` | caregiver, professional | `subject_read` | `subject_care` | |
| `write_daily_observation` | caregiver, professional | `daily_observation_write` | `subject_care` | |
| `submit_form` | caregiver, professional | `form_submit` | `subject_care` | |
| `report_outcome` | caregiver, professional | `outcome_report` | — | el rol debe estar en `eligible_reporter_roles` del target |
| `review_recommendation` | professional | `recommendation_review` | `subject_care` | el actor debe satisfacer `required_approver_role` |
| `record_execution` | caregiver, professional | `execution_record` | — | el rol debe estar en `allowed_executor_roles` del ítem |
| `read_clinical_evaluation` | model_evaluator, professional | `evaluation_read` | `model_evaluation` | |

La acreditación solo se exige a quien tiene rol `professional` **y no** rol
`caregiver`.

Precedencia de negación al autorizar un sujeto (`AuthorizationService.authorize_subject`),
todas **403** y todas auditadas:

1. sujeto inexistente o de otro tenant → `cross_tenant`
2. cohorte no permitida por el modo de despliegue → `cohort_not_allowed`
3. rol no permitido → `role_not_allowed`
4. professional sin acreditación vigente → `accreditation_required`
5. sin grant activo con la capability → `subject_access_denied`

Un recurso (episodio, instancia, sesión) de otro tenant se comporta como
**inexistente**: **404 `not_found`**, nunca 403. Un 403 confirmaría que existe.

Los listados se filtran **en SQL** por tenant y grant (`GRANT_FILTER_SQL`);
nunca se cargan filas prohibidas para descartarlas después.

### 1.4 Cabeceras

| Cabecera | Dirección | Obligatoria en | Efecto |
|---|---|---|---|
| `Authorization: Bearer …` | request | todas las rutas `/api/v1` | 401 si falta o no resuelve |
| `Idempotency-Key: <str>` | request | **todo POST** | 400 `idempotency_key_required` si falta o viene vacía |
| `If-Match: <revision>` | request | POST de `reviews` y `executions` | 428 `precondition_required` si falta |
| `ETag: "<revision>"` | response | `GET …/recommendations` | token a devolver en `If-Match` |
| `X-Request-Id: <uuid>` | response | **todas** | mismo valor que `error.request_id` |

CORS: allowlist explícita (`FARO_CORS_ORIGINS`), nunca comodín.
`allow_credentials=false`; métodos `GET, POST, OPTIONS`; headers permitidos
`Authorization, Content-Type, Idempotency-Key, If-Match`; se expone `ETag`.

### 1.5 Idempotencia (`SPEC 11.2`)

El scope es la tupla **`(tenant_id, actor_id, method, ruta concreta, idempotency_key)`**.
La ruta es la **concreta y normalizada**, con los IDs reales — nunca la plantilla
de ruta. Un scope con `{` o `}` es un error de contrato: la misma clave sobre dos
recursos distintos jamás puede reproducir la respuesta del otro.

La huella del request cubre además `path_params`, la query canónica y el body:

```
request_fingerprint = sha256(dominio, contract_version, {scope, path_params, query, body})
```

- Misma clave + misma huella → se devuelve la respuesta guardada (**replay**).
- Misma clave + huella distinta → **409 `idempotency_key_conflict`**.
- Un replay **vuelve a autorizar** rol, acreditación, grant y capability antes de
  devolver la respuesta guardada: si el grant se revocó, el replay ya no pasa.

### 1.6 Concurrencia optimista

`GET …/recommendations` devuelve `revision` en el cuerpo y en el `ETag`.
Los POST de `reviews` y `executions` exigen `If-Match`:

| Situación | Respuesta |
|---|---|
| sin cabecera `If-Match` | **428** `precondition_required` |
| revisión vigente | **201** |
| revisión obsoleta | **409** `revision_conflict` |

### 1.7 Sobre de error (`SPEC 11.7`)

```json
{
  "error": {
    "code": "forbidden",
    "message_es": "No tienes autorización para esta operación.",
    "request_id": "d26b9ac7-59e4-43be-bfcc-7b1daca98f10"
  }
}
```

El sobre **nunca lleva payload clínico**. Toda negativa queda en auditoría
append-only, sin payload, aunque la transacción del comando se revierta.

**La abstención no es un error.** Un track que no estima, un catálogo que no
recomienda y una métrica sin soporte responden **HTTP 200** con su propio estado
explícito (`abstained`, `unavailable`, `not_estimable`,
`awaiting_professional_review`). El sobre de error jamás se usa para eso.

### 1.8 Reglas del modelo base (`FaroModel`)

- `extra="forbid"`: un campo desconocido es **422**, no se ignora.
- `frozen=True`: los modelos son inmutables; una corrección es una fila nueva
  enlazada con `supersedes_id`, nunca una mutación.
- Identificadores: **UUID**.
- Instantes: **datetime con zona**, normalizados a UTC. Un naive es error de contrato.
- Enums cerrados; toda respuesta tiene modelo explícito (ninguna ruta devuelve un dict suelto).

Tipos escalares:

| Tipo | Regla |
|---|---|
| `UtcDatetime` | aware, convertido a UTC |
| `Probability` | float en `[0.0, 1.0]` |
| `NonNegativeFloat` | float `≥ 0.0` |
| `VersionLabel` | `^[a-z0-9][a-z0-9._-]{0,63}$` |
| `Sha256Hex` | `^[0-9a-f]{64}$` |
| `Tag` | `^[a-z][a-z0-9_]*$`, ≤64 |
| `NamespacedTag` | `^[a-z][a-z0-9_]*:[a-z][a-z0-9_]*$`, ≤96 |
| `SpanishText` | texto normalizado, longitud ≥1 |
| `NotesText` | texto normalizado, ≤500 |
| `Interval` | `{lower, upper}`, ambos o ninguno, `lower ≤ upper` |

---

## 2. Rutas

Once rutas de producto (`SPEC 11.1`), dos de soporte (`GET /api/v1/session`,
`GET /health`).

| # | Método | Ruta | Éxito | Idem-Key | If-Match |
|---|---|---|---|---|---|
| 0 | GET | `/api/v1/session` | 200 | — | — |
| 1 | POST | `/api/v1/form-sessions` | 201 | ✅ | — |
| 2 | GET | `/api/v1/form-sessions/{form_session_id}` | 200 | — | — |
| 3 | POST | `/api/v1/form-sessions/{form_session_id}/answers` | 201 | ✅ | — |
| 4 | POST | `/api/v1/form-sessions/{form_session_id}/submit` | 201 | ✅ | — |
| 5 | GET | `/api/v1/prediction-episodes/{prediction_episode_id}` | 200 | — | — |
| 6 | GET | `/api/v1/outcome-requests` | 200 | — | — |
| 7 | POST | `/api/v1/prediction-episodes/{prediction_episode_id}/outcome-reports` | 201 | ✅ | — |
| 8 | GET | `/api/v1/prediction-episodes/{prediction_episode_id}/recommendations` | 200 | — | — |
| 9 | GET | `/api/v1/recommendation-instances` | 200 | — | — |
| 10 | POST | `/api/v1/recommendation-instances/{recommendation_instance_id}/reviews` | 201 | ✅ | ✅ |
| 11 | POST | `/api/v1/recommendation-instances/{recommendation_instance_id}/executions` | 201 | ✅ | ✅ |
| 12 | GET | `/api/v1/evaluation/{model_version}` | 200 | — | — |
| — | GET | `/health` | 200 | — | — |

---

### 2.0 `GET /api/v1/session`

Quién soy y sobre qué sujetos tengo grant. **No devuelve ningún dato clínico.**
Ruta de soporte del frontend, fuera de `SPEC 11.1`.

**Respuesta 200** — `SessionContextView`

```json
{
  "actor_id": "uuid",
  "display_name": "Ana Ríos",
  "tenant_id": "uuid",
  "roles": ["caregiver"],
  "subjects": [
    { "subject_id": "uuid", "display_label": "Sujeto Demo 1", "cohort_kind": "demo_fixture" }
  ],
  "deployment_mode": "demo",
  "adapters_source": "mock"
}
```

Los sujetos son exactamente aquellos con grant activo de capability
`subject_read` en el instante de la llamada.

---

### 2.1 `POST /api/v1/form-sessions`

Abre una sesión de formulario. `audit_mode`, los instantes y la versión de
política los decide el servidor, nunca el cliente.

**Request** — `FormSessionCreateRequest`

```json
{ "subject_id": "uuid", "source": "home", "session_kind": "caregiver_daily" }
```

**Respuesta 201** — `FormSessionView`

```json
{
  "form_session_id": "uuid",
  "subject_id": "uuid",
  "source": "home",
  "session_kind": "caregiver_daily",
  "opened_at": "2026-08-25T19:55:00.000Z",
  "audit_mode": false,
  "form_policy_version": "form-0.3.0",
  "voi_status": "unavailable_model",
  "highlighted": [ { "field_code": "...", "reason": "...", "voi_nats": null, "default": null } ],
  "tail": [ { "field_code": "notes", "reason": "tail", "voi_nats": null } ],
  "data_quality": null,

  "status": "draft",
  "submitted_at": null,
  "plan_source": "p1",
  "outcome_pending": null,
  "answered_field_codes": []
}
```

Los cinco últimos campos son la extensión de producto de P2 (solicitud R5);
el resto es `FormSessionResponse` de P1. `plan_source` es `p1` o `mock` según el
adaptador que construyó el plan.

`outcome_pending`, cuando existe (`OutcomePendingBlock`):

```json
{
  "prediction_episode_id": "uuid",
  "question_es": "…",
  "severity_anchors_es": ["…"],
  "target_end_at": "…",
  "capture_deadline_at": "…",
  "state": "open"
}
```

**Reglas que el contrato hace cumplir**

- Un `field_code` aparece **una sola vez**: o en `highlighted` o en `tail`,
  nunca en ambos ni repetido.
- **Una sesión auditada no devuelve ningún `default`**, ni en `highlighted` ni
  en `tail`. Se rechaza en el propio modelo.
- El valor de un `default` debe ser legal para su campo según el catálogo.
- Todos los campos quedan accesibles siempre; «destacado» es prioridad de
  atención, no un filtro (`INV-10`).

`audit_mode` se fija **una sola vez** al abrir, con
`HMAC_SHA256(secret, tenant_id | subject_id | local_date | policy_version) mod 1000 < 100`
(≈10%, `C10`), y **nunca se recalcula** (`INV-05`).

Orden del plan: outcome pendiente → vencidos (≥7 días, `C14`) → cuota de
exploración (día ISO por HMAC semanal, `C15`) → mayor VoI → orden canónico →
resto en cola. Destacados: 2 por defecto (`C11`), 3 si la cobertura es baja
(`C12`, umbral `C13`).

---

### 2.2 `GET /api/v1/form-sessions/{form_session_id}`

Relee la sesión con el plan recalculado. Mismo modelo `FormSessionView` que 2.1.

---

### 2.3 `POST /api/v1/form-sessions/{form_session_id}/answers`

**Request** — `AnswerRequest` (`FormAnswerRequest` + solicitud R12)

```json
{
  "answer": {
    "field_code": "food_changes",
    "interaction": "accept_default",
    "value": false,
    "default_presentation_id": "uuid",
    "effective_at": null,
    "supersedes_id": null
  }
}
```

- `interaction` ∈ `manual | accept_default | edit_default | unknown`.
- `unknown` **no lleva valor**. No es `0`, no es `false`, no es cadena vacía.
- `accept_default` y `edit_default` **exigen** `default_presentation_id`.
- Cualquier otra interacción exige `value`, y el valor se valida contra el
  catálogo del campo.
- `effective_at` y `supersedes_id` expresan una corrección: `SPEC 5.8` hace la
  observación append-only.

**Respuesta 201** — `AnswerAcceptedView`

```json
{
  "field_observation_id": "uuid|null",
  "field_code": "food_changes",
  "entry_mode": "default_accepted",
  "session": { "…FormSessionView con el plan recalculado…" }
}
```

**El servidor deriva `entry_mode`**, nunca el cliente. Precedencia fija:

1. canal de importación con mapping aprobado → `imported_observed`
2. sesión de observación profesional → `professional_observed`
3. interacción `unknown` → `explicit_unknown`, **sin valor**
4. sesión auditada + respuesta manual → `audit_manual`
5. `accept_default` sobre sugerencia vigente **con el valor presentado** → `default_accepted`
6. cualquier valor manual sobre un campo con sugerencia vigente, **aunque el
   cliente diga `manual`** → `default_edited`
7. campo sin sugerencia → `manual_no_default`

Una sugerencia que nadie toca **no crea observación** (`INV-01`).

**Errores propios**: `default_presentation_not_current` (422) si la sugerencia
referida ya no está vigente; `field_not_allowed_for_source` (422) si el campo no
se registra desde esa fuente; `form_session_not_open` (422) si la sesión ya cerró.

---

### 2.4 `POST /api/v1/form-sessions/{form_session_id}/submit`

Sin cuerpo. Serializado por `(tenant_id, subject_id)`.

**Respuesta 201** — `SubmitFormSessionView`

```json
{
  "form_session_id": "uuid",
  "status": "episode_created",
  "submitted_at": "…",
  "prediction_episode_id": "uuid|null",
  "linked_prediction_episode_id": "uuid|null",

  "outcome_request_id": "uuid|null",
  "recommendation_instance_id": "uuid|null",
  "reasons": []
}
```

`status` ∈ `episode_created | episode_linked | target_definition_unavailable`,
y el contrato lo amarra a sus referencias:

| status | `prediction_episode_id` | `linked_prediction_episode_id` |
|---|---|---|
| `episode_created` | **obligatorio** | debe ser `null` |
| `episode_linked` | debe ser `null` | **obligatorio** |
| `target_definition_unavailable` | debe ser `null` | debe ser `null` |

Regla fail-closed del cierre:

```text
si no hay TargetDefinitionVersion activa y única para el instante:
    cerrar con target_definition_unavailable (reasons lleva
    target_definition_unavailable o target_definition_ambiguous)
    NO se crea episodio ni outcome request
si hay definición y no hay episodio primario abierto:
    crear PredictionEpisode + OutcomeRequest inmutable
    snapshot = IDs de observaciones proyectadas al cutoff
si hay definición y ya hay un episodio primario abierto:
    enlazar la sesión a ese episodio, no crear otro
```

El snapshot guarda **IDs**, no una copia de valores: una corrección posterior no
cambia lo que el episodio vio.

Ventana del target: horizonte de 24 h (`C04`), captura hasta 48 h (`C05`).

---

### 2.5 `GET /api/v1/prediction-episodes/{prediction_episode_id}`

**Respuesta 200** — `PredictionEpisodeView`

```json
{
  "prediction_episode_id": "uuid",
  "subject_id": "uuid",
  "as_of_at": "…",
  "target_start_at": "…",
  "target_end_at": "…",
  "capture_deadline_at": "…",
  "target_definition_version": "target-demo-1",
  "outputs": [ "…PredictionOutputView…" ],
  "data_quality": null,
  "decision_policy_version": null,
  "risk_band": null,

  "prediction_at": "…",
  "outcome_state": "open",
  "resolution_status": "pending"
}
```

`decision_policy_version` y `risk_band` son **siempre `null`** por contrato
(tipo `None`): sin política de decisión validada no hay bandas verde/ámbar/rojo
(`C37`, `SPEC 8.6`).

`as_of_at` es el cutoff de los datos; `prediction_at` es cuándo se calcularon las
salidas. No son lo mismo.

**`PredictionOutputView`** — un track:

```json
{
  "track_id": "real_personal_baseline_v1",
  "intended_use": "operational_support",
  "status": "abstained",
  "estimate_kind": "personal_observed_episode_rate",
  "probability": null,
  "simulation_score": null,
  "interval": null,
  "interval_method": null,
  "abstention_reasons": ["insufficient_verified_outcomes"],
  "model_version": "real-personal-baseline-0.3.0",
  "input_data_origin": "real"
}
```

No existe campo `confidence`. Es deliberado.

**Los tres tracks y lo que jamás comparten**

| Track | `intended_use` | `estimate_kind` | Se abstiene si |
|---|---|---|---|
| `synthetic_reference_v021` | `simulation_only` | `simulation_score` | falta el artefacto (`model_artifact_unavailable`) |
| `real_personal_baseline_v1` | `operational_support` | `personal_observed_episode_rate` | `verified_outcomes < 5` (`C19`), conflicto sin resolver, o falta historial de `care_mode` |
| `real_logit_challenger_v1` | `shadow_evaluation` | `shadow_challenger_score` | **nunca se expone**: el modelo lanza error si se intenta serializar |

Validadores del contrato, en el propio modelo:

- Exponer `real_logit_challenger_v1` es un error de contrato.
- `intended_use` y `estimate_kind` deben ser exactamente los de su track.
- El track sintético **nunca** corre sobre `input_data_origin: real`.
- Si `status != ok`: al menos una `abstention_reason`, y `probability`,
  `simulation_score`, `interval` e `interval_method` **todos `null`**.
  Una abstención con número es rechazada.
- Si `status == ok` y es el track sintético: lleva `simulation_score`, y
  `probability`, `interval`, `interval_method` **deben ser `null`**.
  Una simulación nunca se presenta como probabilidad clínica.
- Si `status == ok` y es un baseline real: lleva `probability`, `interval` e
  `interval_method`, y `simulation_score` **debe ser `null`**.

Baseline personal: `Beta(1+e, 1+n−e)` sobre outcomes reales previos del mismo
sujeto/`care_mode`/target, ventana 60 días (`C18`);
`p_mean = (1+e)/(2+n)`; intervalo `[BetaPPF(0.05), BetaPPF(0.95)]`
(`C42`, `C43`), método `beta_posterior_quantile`.

---

### 2.6 `GET /api/v1/outcome-requests`

Bandeja de outcomes pendientes del actor.

**Respuesta 200** — `OutcomeRequestListResponse`

```json
{
  "items": [
    {
      "outcome_request_id": "uuid",
      "prediction_episode_id": "uuid",
      "subject_id": "uuid",
      "target_definition_version": "target-demo-1",
      "question_es": "…",
      "severity_anchors_es": ["…"],
      "target_start_at": "…",
      "target_end_at": "…",
      "capture_deadline_at": "…",
      "state": "open",
      "resolution_status": "pending"
    }
  ]
}
```

Es un GET, pero corre en transacción de **escritura**: al pasar el deadline,
`SPEC 4.4` exige materializar la resolución `unknown` antes de derivar `missing`.
No crea episodios ni requests.

---

### 2.7 `POST /api/v1/prediction-episodes/{id}/outcome-reports`

**Request** — `OutcomeReportRequest`

```json
{ "value": "yes", "occurred_at": "2026-08-26T00:55:00.000Z", "supersedes_id": null }
```

- `value` ∈ `yes | no | unknown`.
- **Solo `yes` lleva `occurred_at`**, y `yes` lo exige. Ambas direcciones se
  rechazan en el modelo.
- El servidor deriva actor, rol, tenant, `timing_status` e `intake_channel` del
  contexto autorizado. El cliente no los manda.

**Respuesta 201** — `OutcomeReportResponseView`

```json
{
  "report": {
    "outcome_report_id": "uuid",
    "prediction_episode_id": "uuid",
    "value": "yes",
    "occurred_at": "…",
    "reported_at": "…",
    "timing_status": "early",
    "reporter_role": "caregiver",
    "intake_channel": "form",
    "target_definition_version": "target-demo-1"
  },
  "resolution": {
    "status": "yes",
    "resolved_at": "…",
    "qualifying_report_id": "uuid",
    "ever_conflicted": false,
    "resolution_version": 1
  },
  "request_state": "reported"
}
```

Reporte y resolución van **separados**: son hechos distintos.

**Adjudicación** (`OutcomeService`, sobre la proyección al cutoff):

```text
1. yes elegible: timing_status ∈ {early, on_time} y occurred_at dentro de la ventana
2. no elegible:  solo timing_status = on_time
3. hay yes y no elegibles a la vez -> conflicted, ever_conflicted = true
4. solo yes -> yes;  solo no -> no
5. sin reporte concluyente antes del deadline -> pending; al vencer -> unknown
```

- Ni `no` ni `unknown` cierran la ventana antes de tiempo (`INV-14`).
- `ever_conflicted` es **monotónico**: lo que alguna vez fue `conflicted` nunca
  vuelve a presentarse limpio. Un `conflicted` con `ever_conflicted: false` es
  rechazado por el contrato.
- Una resolución concluyente (`yes`/`no`) **nombra** su `qualifying_report_id` y
  su `resolved_at`; una no concluyente no puede llevarlos.
- `timing_status: missing` describe un reporte ausente: nunca aparece en uno
  almacenado.
- Un evento no puede haber ocurrido después de haber sido reportado.

---

### 2.8 `GET /api/v1/prediction-episodes/{id}/recommendations`

Este GET **no crea filas** (`SPEC 11.6`). Devuelve `ETag: "<revision>"`.

**Respuesta 200** — `RecommendationsView`

```json
{
  "status": "matched",
  "recommendation_instance_id": "uuid",
  "catalog_version": "catalog-demo-1",
  "corpus_version": "corpus-demo-1",
  "items": [ "…StrategyItemView | HumanPlanItemView…" ],
  "reasons": [],
  "revision": "…"
}
```

`status` ∈ `matched | abstained | awaiting_professional_review`, amarrado a su
contenido:

| status | items | reasons |
|---|---|---|
| `matched` | **al menos uno** | — |
| `abstained` | **vacío** | **al menos una** |
| `awaiting_professional_review` | **vacío** | — |

Mientras las estrategias siguen sin revisar, la familia ve
`{"status": "awaiting_professional_review", "items": []}`. El filtro por actor y
grants se aplica **en el servidor**, nunca solo en el cliente.

**`StrategyItemView`**

```json
{
  "item_type": "strategy",
  "strategy_version_id": "uuid",
  "review_status": "approved",
  "action_text_es": "Texto exacto revisado…",
  "citations": [
    {
      "citation_id": "uuid",
      "claim_id": "uuid",
      "locator": "section 2, paragraph 3",
      "quoted_text": "Fragmento literal verificado.",
      "canonical_url": "https://example.org/versioned-source"
    }
  ],
  "required_approver_role": "professional",
  "allowed_executor_roles": ["caregiver"],
  "non_actionable": null,
  "execution_status": null
}
```

**`HumanPlanItemView`**

```json
{
  "item_type": "human_plan",
  "human_plan_version_id": "uuid",
  "action_text_es": "…",
  "citations": [],
  "strategy_version_id": "uuid|null",
  "required_approver_role": "…",
  "allowed_executor_roles": ["…"],
  "non_actionable": null,
  "execution_status": null
}
```

**Un plan humano nunca hereda citas del RAG** (`INV-29`): `citations` no vacío es
un error de contrato. `strategy_version_id` (la estrategia sustituida) viaja solo
hacia un profesional; la familia no lo necesita.

Runtime: `rag/runtime/decide.py::decide(RuntimeInputs)` es puro y determinista,
**cero llamadas a LLM** (`C29 = 0`). Recibe el escenario mínimo, evalúa el
predicate del set y el de cada estrategia por separado, fail-closed, y devuelve
**como máximo 3** estrategias ya revisadas (`C30`). `medication_adherence` no
entra al escenario si se respondió `unknown`.

Precedencia de la razón de abstención (`SPEC 9.6`, exactamente una):
`corpus_not_ready` → `clinical_review_unavailable` → `catalog_suspended` →
`catalog_ambiguous` → `catalog_not_ready` → `no_approved_match` →
`scenario_unavailable_conflict`.

---

### 2.9 `GET /api/v1/recommendation-instances`

Inbox profesional. Query param `review_status`, **solo `pending`** está soportado
(cualquier otro valor → 422 `validation_error`, razón `unsupported_review_status`).

Exige rol `professional` (403 `role_not_allowed`) y acreditación `subject_care`
vigente (403 `accreditation_required`). Filtra por grants de capability
`recommendation_review`.

**Respuesta 200** — `RecommendationInboxView`

```json
{
  "items": [
    {
      "recommendation_instance_id": "uuid",
      "prediction_episode_id": "uuid",
      "subject_id": "uuid",
      "scenario_hash": "…",
      "catalog_version": "catalog-demo-1",
      "corpus_version": "corpus-demo-1",
      "strategy_version_ids": ["uuid"],
      "review_status": "pending",
      "created_at": "…",

      "subject_label": "…",
      "runtime_status": "matched",
      "scenario": { "…ScenarioV1…" },
      "pending_strategy_version_ids": ["uuid"],
      "revision": "…"
    }
  ]
}
```

`ScenarioV1` es el escenario mínimo (`SPEC 9.7`): **sin identidad, sin notas, sin
IDs externos, sin historial**.

```json
{
  "schema_version": "scenario-1",
  "field_values": { "sleep_quality": "interrupted" },
  "context_tags": [],
  "profile_tags": [],
  "contraindication_tags": []
}
```

`field_values` solo admite los **5 campos** de `SCENARIO_ALLOWLIST_V1`:
`sleep_quality`, `alertness`, `gi_status`, `medication_adherence`,
`daily_regulation_state`. Cualquier otro campo es error de contrato. Los tags se
deduplican y ordenan.

---

### 2.10 `POST /api/v1/recommendation-instances/{id}/reviews`

Exige `Idempotency-Key` **y** `If-Match`.

**Request** — `RecommendationReviewRequest`

```json
{
  "strategy_version_id": "uuid",
  "decision": "human_plan_substituted",
  "human_plan_action_text_es": "Texto del plan del equipo.",
  "human_plan_allowed_executor_roles": ["caregiver"]
}
```

`decision` ∈ `approved | rejected | human_plan_substituted | not_applicable | deferred`.

- **Solo** `human_plan_substituted` lleva `human_plan_action_text_es` y
  `human_plan_allowed_executor_roles`, y los **exige a ambos**. Cualquier otra
  decisión con ellos es rechazada.
- Una sustitución **no puede ampliar** los roles de ejecución de la estrategia
  sustituida (422 `human_plan_roles_not_subset`).
- El plan creado **no hereda citas** (`INV-29`).

**Respuesta 201** — `RecommendationReviewResponse`

```json
{
  "review_id": "uuid",
  "recommendation_instance_id": "uuid",
  "strategy_version_id": "uuid",
  "decision": "human_plan_substituted",
  "reviewed_at": "…",
  "human_plan_version_id": "uuid|null"
}
```

**Errores propios**: 428 `precondition_required` sin `If-Match`;
409 `revision_conflict` con revisión obsoleta; 403 `review_role_not_permitted`
si el rol no satisface `required_approver_role`;
409 `recommendation_dependency_suspended` si una dependencia está suspendida.

---

### 2.11 `POST /api/v1/recommendation-instances/{id}/executions`

Exige `Idempotency-Key` **y** `If-Match`.

**Request** — `StrategyExecutionRequest`

```json
{
  "strategy_version_id": "uuid",
  "human_plan_version_id": null,
  "status": "applied",
  "applied_at": "2026-08-26T10:00:00.000Z"
}
```

- Referencia **exactamente uno**: estrategia **o** plan humano, nunca ambos ni
  ninguno (422 `execution_target_ambiguous`).
- `status` ∈ `applied | not_applied | unknown`.
- **Solo `applied` lleva `applied_at`**, y lo exige.

**Respuesta 201** — `ExecutionView`

```json
{
  "strategy_execution_id": "uuid",
  "recommendation_instance_id": "uuid",
  "status": "applied",
  "recorded_at": "…",
  "applied_at": "…",
  "strategy_version_id": "uuid|null",
  "human_plan_version_id": "uuid|null",
  "exposure_eligible": true
}
```

`exposure_eligible` es **`false`** si la aplicación llegó después del cierre de
la ventana target o antes de la revisión que la autorizó: el registro se
conserva, pero no cuenta como exposición válida (`SPEC 10.3`). La aprobación
nunca prueba la aplicación.

**Errores propios**: 403 `execution_role_not_permitted` si el rol no está en
`allowed_executor_roles` del ítem referido.

---

### 2.12 `GET /api/v1/evaluation/{model_version}`

Exige rol `model_evaluator` o `professional` (403 `role_not_allowed`) y
acreditación `model_evaluation` vigente (403 `accreditation_required`).
Sin reporte publicado para esa versión → **404 `evaluation_not_found`**.

**Respuesta 200** — `EvaluationReportView`

```json
{
  "model_version": "…",
  "track_id": "synthetic_reference_v021",
  "status": "published",
  "data_origin": "synthetic",
  "intended_use": "simulation_only",
  "dataset_sha256": "…",
  "target_definition_version": "target-demo-1",
  "protocol_version": "…",
  "metrics": [ "…MetricValue…" ],
  "group_metrics": [ "…GroupMetric…" ],
  "source_metrics": [ "…SourceMetric…" ],
  "decision_coverage": null,
  "abstentions": [ { "reason": "…", "count": 0, "rate": 0.0 } ],
  "limitations_es": ["…"],

  "evaluation_report_id": "uuid",
  "model_state": "shadow",
  "published_at": "…"
}
```

- `limitations_es` tiene **mínimo un elemento**: todo reporte dice qué no puede mostrar.
- **`INV-34`**: un reporte con `data_origin: synthetic` debe declarar
  `intended_use: simulation_only`. Se rechaza lo contrario.
- Un reporte es de **una** versión exacta de definición de target. No hay pooling en v0.3.

**`MetricValue`** — una métrica sin soporte es `not_estimable`, **nunca cero**:

```json
{ "name": "auc", "status": "not_estimable", "value": null, "interval": null,
  "not_estimable_reason": "…", "denominator": null }
```

Si `status: estimated` → hay `value` y no hay `not_estimable_reason`.
Si `status: not_estimable` → no hay `value` ni `interval`, y **sí** hay razón.

**`GroupMetric`** — un grupo suprimido **no publica métricas, ni indirectamente**:

```json
{ "group_kind": "…", "group_value": "…", "subject_count": 0,
  "positive_count": 0, "negative_count": 0, "suppressed": true, "metrics": [] }
```

Mínimos de privacidad: `C48` ≥10 sujetos, `C49` ≥5 positivos, `C50` ≥5 negativos.

---

### 2.13 `GET /health`

Sin autenticación.

```json
{ "status": "ok", "spec_version": "0.3.0", "mode": "demo", "adapters": "p1" }
```

`adapters` ∈ `mock | p1`, según `FARO_P1_ADAPTERS`.

---

## 3. Vocabularios cerrados

Todo enum es cerrado. Un valor fuera de la lista es **422**, jamás se coacciona a
`null` ni se convierte en número.

### Contexto y actor

| Enum | Valores |
|---|---|
| `Source` | `home`, `therapy`, `school` |
| `Role` | `caregiver`, `professional`, `clinical_reviewer`, `evidence_reviewer`, `privacy_reviewer`, `model_evaluator`, `tenant_admin`, `auditor` |
| `CohortKind` | `real_subject`, `demo_fixture` |
| `DeploymentMode` | `demo`, `pilot` |
| `IntakeChannel` | `form`, `import` |
| `DataOrigin` | `real`, `synthetic` |
| `IntendedUse` | `simulation_only`, `operational_support`, `shadow_evaluation`, `authoring_only` |

### Formulario y observación

| Enum | Valores |
|---|---|
| `FormSessionKind` | `caregiver_daily`, `professional_observation` |
| `FormSessionStatus` | `draft`, `submitted`, `abandoned`, `expired` |
| `SubmitStatus` | `episode_created`, `episode_linked`, `target_definition_unavailable` |
| `AnswerInteraction` (lo declara el cliente) | `manual`, `accept_default`, `edit_default`, `unknown` |
| `EntryMode` (lo deriva el servidor) | `manual_no_default`, `audit_manual`, `default_accepted`, `default_edited`, `professional_observed`, `imported_observed`, `explicit_unknown` |
| `QuestionReason` | `outcome_pending`, `staleness`, `exploration`, `voi`, `canonical_order`, `tail` |
| `VoiStatus` | `available`, `unavailable_model`, `unavailable_field_type`, `unavailable_prediction` |
| `FormAnomalyTrigger` | `relevant_event_flag`, `medication_missed`, `frequent_dysregulation`, `alertness_extreme`, `categorical_anomaly`, `robust_z_anomaly` |
| `FieldKind` | `continuous`, `count`, `boolean`, `nominal`, `ordinal`, `tag_set`, `text` |

### Predicción

| Enum | Valores |
|---|---|
| `TrackId` | `synthetic_reference_v021`, `real_personal_baseline_v1`, `real_logit_challenger_v1` |
| `PredictionStatus` | `ok`, `abstained`, `unavailable` |
| `EstimateKind` | `personal_observed_episode_rate`, `simulation_score`, `shadow_challenger_score` |
| `IntervalMethod` | `beta_posterior_quantile` |
| `EpisodeRole` | `primary` (v0.3 crea exactamente uno) |
| `PredictionEpisodeStatus` | `pending`, `completed`, `failed` |
| `PredictionAbstentionReason` | `collecting_data`, `insufficient_verified_outcomes`, `unresolved_conflict`, `care_mode_history_unavailable`, `target_definition_unavailable`, `target_definition_ambiguous`, `model_state_not_shadow`, `predictor_missing`, `personal_predictor_history_insufficient`, `feature_conflict`, `unsupported_mapping`, `calibration_failure`, `cohort_not_eligible`, `model_artifact_unavailable` |

### Outcome

| Enum | Valores |
|---|---|
| `OutcomeReportValue` | `yes`, `no`, `unknown` |
| `OutcomeResolutionStatus` | `pending`, `yes`, `no`, `unknown`, `conflicted` |
| `OutcomeRequestState` | `open`, `reported`, `conflicted`, `missing` |
| `TimingStatus` | `early`, `on_time`, `late`, `missing` |

### Recomendación y revisión

| Enum | Valores |
|---|---|
| `RuntimeStatus` | `matched`, `abstained` |
| `RecommendationResponseStatus` | `matched`, `abstained`, `awaiting_professional_review` |
| `RecommendationItemType` | `strategy`, `human_plan` |
| `RecommendationAbstentionReason` | `corpus_not_ready`, `clinical_review_unavailable`, `catalog_suspended`, `catalog_ambiguous`, `catalog_not_ready`, `no_approved_match`, `scenario_unavailable_conflict` |
| `CatalogReadiness` | igual que arriba menos `no_approved_match`/`scenario_…`, más `ready` |
| `ReviewDecision` | `approved`, `rejected`, `human_plan_substituted`, `not_applicable`, `deferred` |
| `ReviewStatus` | `pending` + los cinco anteriores (`pending` es la **ausencia** de revisión activa; nunca se persiste) |
| `ExecutionStatus` | `applied`, `not_applied`, `unknown` |
| `NonActionableReason` | `dependency_suspended` |
| `RetrievalMode` | `hybrid`, `lexical_only` |

### Ciclo de vida de artefactos

| Enum | Valores |
|---|---|
| `ApprovalStatus` | `draft`, `active`, `retired` |
| `DocumentStatus` | `draft`, `verified`, `indexed`, `active`, `superseded`, `withdrawn` |
| `StrategyStatus` | `draft`, `evidence_reviewed`, `clinical_reviewed`, `active`, `suspended`, `retired` |
| `CatalogStatus` | `draft`, `reviewed`, `active`, `suspended`, `retired` |
| `TargetScope` | `tenant`, `demo_fixture` |
| `ModelState` | `candidate`, `validated_offline`, `shadow`, `shadow_evaluated`, `rejected`, `suspended_for_consent_review`, `retired` |
| `EvaluationReportStatus` | `draft`, `published`, `suspended_for_consent_review`, `retired` |
| `MetricStatus` | `estimated`, `not_estimable` |
| `TrainingRunStatus` | `created`, `running`, `completed`, `not_trainable`, `failed` |
| `NotTrainableReason` | `not_trainable_single_class`, `not_trainable_insufficient_sample_plan`, `not_trainable_convergence_failure`, `not_trainable_consent_not_reauthorized` |

### Gobernanza y consentimiento

| Enum | Valores |
|---|---|
| `ConsentPurpose` | `operational_support`, `secondary_model_use`, `authoring_generalization` (nunca se sustituyen entre sí) |
| `AccreditationCapability` | `subject_care`, `target_review`, `strategy_review`, `evidence_review`, `privacy_review`, `catalog_activation`, `model_evaluation` |
| `GrantCapability` | `subject_read`, `daily_observation_write`, `form_submit`, `outcome_report`, `recommendation_review`, `execution_record`, `evaluation_read` |
| `AuthorizationStatus` | `active`, `revoked`, `expired` |
| `AuthoringBasisType` | `consent`, `institutional_legal_basis` |
| `AuthoringScope` | `generalize_query_only` |
| `AuthoringReviewObjectType` | `target_definition`, `document`, `strategy`, `recommendation_set`, `catalog` |
| `AuthoringReviewKind` | `evidence`, `clinical`, `privacy`, `catalog_activation` |
| `AuthoringReviewDecision` | `approved`, `changes_requested`, `rejected` |
| `AuthoringRequestStatus` | `open`, `exported`, `closed` |

### Valores de campo

| Enum | Valores |
|---|---|
| `SleepQuality` | `restorative`, `interrupted`, `sleep_onset_difficulty`, `other` |
| `WakeState` | `calm_happy`, `tired_sleepy`, `irritable_crying`, `other` |
| `GiStatus` | `normal`, `constipation`, `diarrhea`, `other` |
| `MedicationAdherence` | `taken`, `missed`, `not_applicable` (`not_applicable` es una respuesta presente, no una ausencia) |
| `Alertness` | `low`, `calm`, `optimal`, `high`, `other` |
| `DailyRegulationState` | `excellent`, `stable_with_support`, `frequent_dysregulation`, `other` |
| `AttendanceStatus` | `present`, `absent`, `not_applicable` |

---

## 4. Catálogo de campos (`SPEC 5.2`, `SPEC 5.4`)

19 campos diarios, en **orden canónico** (el orden de declaración es el orden que
usa el plan para llenar cupos). `major_dysregulation_24h` **no está**: es un
outcome, no una observación diaria.

| # | `field_code` | Tipo | Dominio | Fuentes | Default estimable |
|---|---|---|---|---|---|
| 1 | `sleep_hours` | continuous | 0.0..16.0 | home | no |
| 2 | `sleep_quality` | nominal | restorative \| interrupted \| sleep_onset_difficulty \| other | home | no |
| 3 | `night_awakenings` | count | 0..15 | home | no |
| 4 | `wake_state` | nominal | calm_happy \| tired_sleepy \| irritable_crying \| other | home | no |
| 5 | `morning_support_need` | ordinal | 1..5 | home | no |
| 6 | `gi_status` | nominal | normal \| constipation \| diarrhea \| other | home, therapy | no |
| 7 | `medication_adherence` | nominal | taken \| missed \| not_applicable | home, therapy | no |
| 8 | `food_changes` | boolean | false \| true | home | **sí** |
| 9 | `routine_changes` | boolean | false \| true | home | no |
| 10 | `alertness` | nominal | low \| calm \| optimal \| high \| other | home, therapy, school | no |
| 11 | `dysregulation_event_count` | count | 0..20 | home, therapy, school | no |
| 12 | `daily_regulation_state` | nominal | excellent \| stable_with_support \| frequent_dysregulation \| other | home, therapy, school | no |
| 13 | `activity_participation` | ordinal | 1..5 | home, therapy, school | **sí** |
| 14 | `social_interactions` | ordinal | 1..5 | home, therapy, school | **sí** |
| 15 | `eating_status` | ordinal | 1..5 | home, school | **sí** |
| 16 | `attendance_status` | nominal | present \| absent \| not_applicable | therapy, school | **sí** |
| 17 | `relevant_event_flag` | boolean | false \| true | home, therapy, school | no |
| 18 | `behavior_tags` | tag_set | tokens `^[a-z][a-z0-9_]*$` | home, therapy, school | no |
| 19 | `notes` | text | ≤500 caracteres | home, therapy, school | no |

**Nada convierte una categoría en un número.** `stable_with_support` no es un
conteo, `present` no es un puntaje de participación, y un valor nominal nunca se
vuelve escala ordenada (`INV-35`).

El frontend **solo muestra los campos habilitados para la fuente de la sesión**.
Cambiar la matriz de fuentes exige una versión nueva de contrato.

### Subconjuntos con nombre

| Conjunto | Campos |
|---|---|
| `DEFAULT_ALLOWLIST_V1` (`SPEC 6.7`) | `food_changes`, `activity_participation`, `social_interactions`, `eating_status`, `attendance_status` |
| `HIGH_SIGNAL_NO_DEFAULT` | `sleep_quality`, `wake_state`, `gi_status`, `medication_adherence`, `routine_changes`, `alertness`, `daily_regulation_state`, `dysregulation_event_count`, `relevant_event_flag` |
| `MONITORED_FIELDS` (orden = prioridad de desempate) | `sleep_quality`, `wake_state`, `gi_status`, `medication_adherence`, `daily_regulation_state` |
| `DQI_REQUIRED_FIELDS` | los mismos cinco monitoreados, con peso igual, ventana fija de 14 días (`C38`) |
| `SCENARIO_ALLOWLIST_V1` (`SPEC 9.7`) | `sleep_quality`, `alertness`, `gi_status`, `medication_adherence`, `daily_regulation_state` |
| `KINDS_WITHOUT_DEFAULTS` (`SPEC 6.5`) | tipos `continuous`, `count`, `text`, `tag_set` |

Un valor fuera del soporte declarado lanza `UnknownFieldValueError` y **falla
ruidosamente**: nunca se convierte en silencio en un `null` (`SPEC 5.3`).

---

## 5. Las fórmulas del contrato

Ninguna vive en `apps/api`: el store solo lee filas, el adaptador solo las pasa,
el cálculo entero está en `ml/`.

- **Default binario** — `k` ocurrencias en `N` observaciones elegibles (ventana
  limpia de 60 días, mismo tenant/sujeto/fuente/campo) → `Beta(1+k, 1+N−k)`. Se
  sugiere si `BetaPPF(0.05) > 0.70` (**estricto**: exactamente 0.70 no sugiere) y
  el campo está en la allowlist.
- **Default categórico/ordinal** — Dirichlet con `alpha_j = 1+n_j`; candidato es
  el `argmax`; **sin sugerencia si hay empate**.
- **VoI** — información mutua aproximada entre respuesta y outcome:
  `VoI(X) = h(p̄) − Σ q_j · h(p_j)` en nats. Si no hay modelo condicional es
  **`null`, nunca `0`**.
- **DQI** — `dqi = coverage · recency · consistency`, verificado en el propio
  modelo con tolerancia `1e-12`. Describe calidad; **nunca es feature predictiva
  ni compuerta** (`SPEC 7.1`).
- **Anomalía / cola completa** — se abre si `relevant_event_flag = true`,
  `medication_adherence = missed`, `daily_regulation_state = frequent_dysregulation`,
  `alertness` extremo, probabilidad categórica personal `< 0.05` (`C16`), o
  `|robust_z| ≥ 2.0` (`C17`) sobre los últimos 30 días (mediana + MAD, `C21`).

---

## 6. Constantes normativas C01–C50

Un literal de esta tabla **no se duplica** en ningún módulo (`CONVENTIONS 7`):
cada nombre lee su valor del registro.

| ID | Nombre | Valor | Clase | SPEC | Nota |
|---|---|---|---|---|---|
| C01 | `SPEC_VERSION` | `0.3.0` | engineering | SPEC 15 | |
| C02 | `API_PREFIX` | `/api/v1` | engineering | SPEC 11 | |
| C03 | `REFERENCE_TIMEZONE` | `America/Santiago` | engineering | SPEC 5.1 | |
| C04 | `TARGET_HORIZON_HOURS` | `24` | policy | SPEC 4.1 | |
| C05 | `OUTCOME_CAPTURE_LIMIT_HOURS` | `48` | policy | SPEC 4.1 | |
| C06 | `DEFAULT_WINDOW_DAYS` | `60` | policy | SPEC 6.2 | |
| C07 | `DEFAULT_PRIOR_PER_CATEGORY` | `1` | policy | SPEC 6.3 | |
| C08 | `DEFAULT_LOWER_QUANTILE` | `0.05` | policy | SPEC 6.3 | |
| C09 | `DEFAULT_LOWER_THRESHOLD` | `0.70` | policy | SPEC 6.6 | estricto: un límite inferior de exactamente 0.70 no presenta sugerencia |
| C10 | `DEFAULT_AUDIT_RATE` | `0.10` | policy | SPEC 6.8 | |
| C11 | `FORM_HIGHLIGHTED_DEFAULT` | `2` | policy | SPEC 6.9 | |
| C12 | `FORM_HIGHLIGHTED_LOW_COVERAGE` | `3` | policy | SPEC 6.9 | |
| C13 | `LOW_COVERAGE_THRESHOLD` | `0.50` | policy | SPEC 6.9 | |
| C14 | `STALENESS_CEILING_DAYS` | `7` | policy | SPEC 6.10 | |
| C15 | `EXPLORATION_PERIOD` | `one_hmac_weekday_per_iso_week` | policy | SPEC 6.10 | frecuencia ≈1/7; un día perdido nunca se compensa |
| C16 | `CATEGORICAL_ANOMALY_PROBABILITY` | `0.05` | policy | SPEC 6.11 | |
| C17 | `ROBUST_Z_ANOMALY` | `2.0` | policy | SPEC 6.11 | |
| C18 | `BASELINE_WINDOW_DAYS` | `60` | policy | SPEC 8.3 | |
| C19 | `BASELINE_MIN_OUTCOMES` | `5` | policy | SPEC 8.5 | |
| C20 | `BASELINE_MAX_INTERVAL_WIDTH` | `null` | policy | SPEC 8.5 | compuerta retirada: con este prior y mínimo, el corte 0.60 era inalcanzable |
| C21 | `PERSONAL_DEVIATION_WINDOW_DAYS` | `30` | policy | SPEC 6.11 | |
| C22 | `PERSONAL_MIN_OBSERVATIONS` | `5` | policy | SPEC 6.11 | |
| C23 | `CHALLENGER_MAX_PREDICTORS` | `2` | policy | SPEC 8.4 | preregistrados: desviación de sueño y de regulación |
| C24 | `CHALLENGER_L2_GRID` | `(0.01, 0.1, 1.0, 10.0, 100.0)` | engineering | SPEC 8.4 | |
| C25 | `RAG_LEXICAL_TOP_K` | `20` | engineering | SPEC 9.4 | |
| C26 | `RAG_DENSE_TOP_K` | `20` | engineering | SPEC 9.4 | |
| C27 | `RAG_RRF_K` | `60` | engineering | SPEC 9.4 | |
| C28 | `RAG_FINAL_CHUNKS` | `8` | engineering | SPEC 9.4 | |
| C29 | `RUNTIME_LLM_CALLS` | `0` | policy | SPEC 9.1 | |
| C30 | `MAX_RUNTIME_STRATEGIES` | `3` | policy | SPEC 9.8 | |
| C31 | `STRATEGY_REQUIRED_DISTINCT_REVIEWERS` | `2` | policy | SPEC 9.5 | un revisor de evidencia y uno clínico, nunca la misma identidad |
| C32 | `PRODUCTION_ACCEPTANCE_RERANK_WEIGHT` | `0` | policy | SPEC 9.9 | |
| C33 | `HASH_ALGORITHM` | `sha256` | engineering | SPEC 5.9 | |
| C34 | `OFFLINE_RANDOM_SEED` | `42` | engineering | SPEC 14.4 | |
| C35 | `PILOT_DATABASE` | `postgresql>=16` | engineering | SPEC 12.3 | |
| C36 | `MIN_TLS_VERSION` | `1.2` | engineering | SPEC 12.3 | |
| C37 | `DECISION_POLICY_VERSION` | `null` | policy | SPEC 8.6 | no existe política de decisión validada, así que no hay bandas de riesgo operativas |
| C38 | `DQI_WINDOW_DAYS` | `14` | policy | SPEC 7.1 | |
| C39 | `DQI_RECENCY_HALF_LIFE_DAYS` | `2` | policy | SPEC 7.1 | |
| C40 | `DQI_ACCEPTED_DEFAULT_WEIGHT` | `0.5` | policy | SPEC 7.1 | |
| C41 | `DQI_CONSISTENCY_FLOOR` | `0.5` | policy | SPEC 7.1 | |
| C42 | `BASELINE_LOWER_QUANTILE` | `0.05` | policy | SPEC 8.3 | |
| C43 | `BASELINE_UPPER_QUANTILE` | `0.95` | policy | SPEC 8.3 | |
| C44 | `CHALLENGER_TIE_TOLERANCE` | `1e-12` | engineering | SPEC 8.4 | |
| C45 | `EVAL_BOOTSTRAP_REPLICATES` | `2000` | engineering | SPEC 14.4 | |
| C46 | `EVAL_INTERVAL_LEVEL` | `0.90` | policy | SPEC 14.4 | |
| C47 | `EVAL_MIN_VALID_BOOTSTRAP_FRACTION` | `0.80` | policy | SPEC 14.4 | |
| C48 | `GROUP_METRIC_MIN_SUBJECTS` | `10` | policy | SPEC 14.4 | |
| C49 | `GROUP_METRIC_MIN_POSITIVES` | `5` | policy | SPEC 14.4 | |
| C50 | `GROUP_METRIC_MIN_NEGATIVES` | `5` | policy | SPEC 14.4 | |

Versiones adicionales fuera del registro numerado: `CONTRACT_VERSION`
(`faro-contract-0.3.0`), `FORM_POLICY_VERSION` (`form-0.3.0`),
`DEFAULTS_ESTIMATOR_VERSION` (`defaults-0.3.0`), `SCENARIO_SCHEMA_VERSION`
(`scenario-1`), `SCENARIO_BUILDER_VERSION` (`scenario-builder-0.3.0`).

---

## 7. Errores

Cada código es estable y **no revela payload clínico**. El mensaje en español es
el que el cliente puede mostrar tal cual.

### Códigos que la API emite hoy

| HTTP | `code` | `message_es` |
|---|---|---|
| 400 | `idempotency_key_required` | Falta la cabecera Idempotency-Key. |
| 401 | `authentication_required` | Necesitas iniciar sesión para continuar. |
| 401 | `invalid_credentials` | La sesión local no es válida. |
| 403 | `forbidden` | No tienes autorización para esta operación. |
| 403 | `cross_tenant` | No tienes autorización para esta organización. |
| 403 | `cohort_not_allowed` | Este modo de despliegue solo acepta la cohorte de demostración. |
| 403 | `role_not_allowed` | Tu rol no permite esta operación. |
| 403 | `accreditation_required` | Necesitas una acreditación vigente para esta operación. |
| 403 | `subject_access_denied` | No tienes una autorización vigente sobre esta persona. |
| 403 | `review_role_not_permitted` | Tu rol no puede aprobar ni sustituir esta estrategia. |
| 403 | `execution_role_not_permitted` | Tu rol no puede registrar esta aplicación. |
| 404 | `not_found` | No encontramos el recurso solicitado. |
| 404 | `evaluation_not_found` | No hay reporte de evaluación para esa versión de modelo. |
| 405 | `method_not_allowed` | Operación no permitida en esta ruta. |
| 409 | `idempotency_key_conflict` | Esa clave de idempotencia ya se usó con otro contenido. |
| 409 | `revision_conflict` | El recurso cambió desde tu última lectura. |
| 409 | `recommendation_dependency_suspended` | Una dependencia de esta recomendación está suspendida. |
| 422 | `validation_error` | Los datos enviados no cumplen el contrato. |
| 422 | `field_not_allowed_for_source` | Ese campo no se registra desde esta fuente. |
| 422 | `default_presentation_not_current` | La sugerencia mostrada ya no está vigente. |
| 422 | `form_session_not_open` | Esta sesión de formulario ya está cerrada. |
| 422 | `outcome_report_invalid_timing` | El momento declarado no cae en la ventana del objetivo. |
| 422 | `outcome_occurred_at_required` | Un reporte afirmativo necesita cuándo ocurrió. |
| 422 | `outcome_occurred_at_forbidden` | Solo un reporte afirmativo declara cuándo ocurrió. |
| 422 | `execution_target_ambiguous` | Una aplicación referencia una estrategia o un plan, no ambos. |
| 422 | `human_plan_roles_not_subset` | El plan humano no puede ampliar los roles de ejecución. |
| 428 | `precondition_required` | Falta la cabecera If-Match para un recurso con revisión. |
| 500 | `pilot_requires_postgresql` | El modo piloto no arranca sobre SQLite. |
| 500 | `internal_error` | Ocurrió un error inesperado. El equipo quedó notificado. |

### Códigos declarados en `ERROR_MESSAGES_ES` sin sitio de emisión hoy

`capability_required`, `unmapped_source_value`, `outcome_request_closed`,
`target_definition_ambiguous`. Están en el diccionario de mensajes y son estables,
pero ninguna ruta los levanta en el código actual: `target_definition_ambiguous`
viaja como `reasons` del `submit`, no como error.

### `ErrorCode` del contrato publicado

El enum `ErrorCode` de `packages/shared/enums.py` es un conjunto **más chico** que
el diccionario de la API: `validation_error`, `unauthenticated`, `forbidden`,
`not_found`, `idempotency_conflict`, `revision_conflict`,
`recommendation_dependency_suspended`, `unmapped_source_value`,
`target_definition_ambiguous`, `entry_mode_not_derivable`,
`synthetic_row_in_real_snapshot`, `real_subject_not_allowed_in_demo`,
`internal_error`.

> **Diferencia real, no cosmética.** `ErrorDetail.code` está tipado como
> `ErrorCode`, pero el sobre lo emite `apps/api/main.py::_envelope` construyendo el
> JSON a mano, sin pasar por el modelo. Por eso la API responde códigos más
> específicos (`cross_tenant`, `accreditation_required`, `idempotency_key_conflict`
> en vez de `idempotency_conflict`, …) que no están en el enum publicado. Un
> cliente que valide el sobre con el Zod generado va a rechazar respuestas de error
> legítimas: trata `code` como string estable y compara contra la tabla de arriba.

---

## 8. Lo que el contrato no deja construir

Cada punto tiene su ejemplo inválido en `packages/shared/examples/invalid/`,
nombrando la regla del SPEC que rompe.

| No se puede | Ejemplo inválido |
|---|---|
| Una abstención con probabilidad, intervalo, banda o narrativa | `prediction.abstained_with_probability` |
| Un `simulation_score` presentado como probabilidad clínica | `prediction.simulation_as_probability` |
| Exponer el challenger en sombra | `prediction.challenger_exposed` |
| Un default dentro de una sesión auditada | `form_session.audited_with_default` |
| Un `accept_default` sin la presentación a la que responde | `form_answer.accept_default_without_presentation` |
| Un `unknown` con valor | `form_answer.unknown_with_value` |
| Un episodio creado sin definición de target seleccionable | `submit.target_unavailable_with_episode` |
| Una ventana de episodio desplazada | `episode.shifted_window` |
| Un `yes` sin `occurred_at`, o un `no` con `occurred_at` | `outcome.yes_without_occurred_at`, `outcome.no_with_occurred_at` |
| Una resolución `conflicted` que finge no haberlo estado | `outcome.conflicted_not_ever_conflicted` |
| Una abstención de recomendación con ítems | `recommendation.abstained_with_items` |
| Un plan humano con citas del RAG | `recommendation.human_plan_with_citations` |
| Un escenario con un campo fuera de la allowlist | `scenario.field_outside_allowlist` |
| Un reporte sintético sin `simulation_only` | `evaluation.synthetic_without_simulation_only` |
| Una observación desde una fuente que no la permite | `observation.source_not_allowed` |
| Un scope de idempotencia hecho con la plantilla de ruta | `idempotency.route_template_path` |

---

## 9. Textos en español (`packages/shared/texts.py`)

El texto visible vive aquí o en el catálogo versionado, **nunca inline en un
componente** (`CONVENTIONS 10`). Lenguaje afirmativo y no diagnóstico; una
abstención nunca se presenta como error.

**Avisos obligatorios**

- `EMERGENCY_LIMIT_ES` — se muestra en entrada, abstención, resultados y
  recomendaciones: *«Faro no vigila emergencias ni envía alertas. Ante peligro
  inmediato, sigue de inmediato los protocolos de emergencia o resguardo de tu
  localidad.»*
- `INTENDED_USE_ES` — *«Faro organiza registros, calcula estadísticas personales y
  muestra estimaciones experimentales. No diagnostica, no indica tratamientos y no
  reemplaza el criterio profesional.»*
- `SIMULATION_DISCLAIMER_ES` — obligatorio junto a cualquier `simulation_score`:
  *«Este número viene de una simulación diseñada por el equipo, no de datos de una
  persona real. No es una probabilidad clínica.»*

**Diccionarios exportados**

`FIELD_LABELS_ES`, `FIELD_PROMPTS_ES`, `ORDINAL_ANCHORS_ES`, `SOURCE_LABELS_ES`,
`SLEEP_QUALITY_LABELS_ES`, `WAKE_STATE_LABELS_ES`, `GI_STATUS_LABELS_ES`,
`MEDICATION_ADHERENCE_LABELS_ES`, `ALERTNESS_LABELS_ES`,
`DAILY_REGULATION_LABELS_ES`, `ATTENDANCE_LABELS_ES`, `OUTCOME_VALUE_LABELS_ES`,
`OUTCOME_RESOLUTION_LABELS_ES`, `PREDICTION_ABSTENTION_ES`,
`RECOMMENDATION_ABSTENTION_ES`, `ERROR_MESSAGES_ES`.

**Cadenas sueltas**

`DEFAULT_SUGGESTION_HINT_ES`, `AUDIT_SESSION_HINT_ES`, `UNKNOWN_ANSWER_ES`,
`UNKNOWN_ANSWER_HINT_ES`, `AWAITING_PROFESSIONAL_REVIEW_ES`,
`CONFLICTED_STATE_ES`, `EXPIRED_SESSION_ES`, `FILTER_QUESTION_ES`,
`FILTER_NEGATIVE_HINT_ES`, `LOADING_ES`, `EMPTY_ES`, `GENERIC_ERROR_ES`.

---

## 10. Cómo lo consume el frontend

`packages/shared/generated/index.ts` reexporta tipos, esquemas Zod, constantes,
catálogo de campos y textos. El frontend necesita `zod` como dependencia e importa
desde ese índice **en vez de** volver a declarar un tipo, un umbral, una fila de la
matriz de fuentes o un texto visible.

| Artefacto | Ruta |
|---|---|
| Bundle JSON Schema (143 definiciones) | `packages/shared/generated/faro.schema.json` |
| Tipos TypeScript | `packages/shared/generated/contract.ts` |
| Esquemas Zod | `packages/shared/generated/contract.zod.ts` |
| Constantes | `packages/shared/generated/constants.ts` |
| Catálogo de campos | `packages/shared/generated/field-catalog.ts` |
| Textos en español | `packages/shared/generated/texts.ts` |
| Índice | `packages/shared/generated/index.ts` |
| Manifiesto del handoff | `packages/shared/generated/contract.lock.json` |

**Cuidado con dos cosas al validar en el cliente**

1. El sobre de error trae códigos fuera del enum `ErrorCode` publicado (§7).
2. Las respuestas de las rutas 1–4, 5, 8–12 son **subclases** de los modelos
   publicados: llevan campos extra que los tipos de P1 no declaran
   (`apps/api/contracts/models.py`, solicitudes R1, R5, R7–R15). Los tipos
   generados describen la base, no la vista de producto.

Si P2 necesita un cambio de contrato, la solicitud vuelve a P1 con ruta,
operación, JSON literal de request, JSON literal de response, la razón y un test
consumidor que falle. P1 edita el modelo, los artefactos generados y los ejemplos
en un solo cambio.

---

## 11. Ejecución y entorno

```bash
# Sembrar la base local (datos completamente ficticios)
python -m tools.seed --catalog blocked          # estado honesto de release
python -m tools.seed --catalog fixture-active   # para recorrer el flujo profesional

# Levantar
uvicorn "apps.api.main:create_app" --factory --host 127.0.0.1 --port 8000

# Contra el dominio real de P1 en vez de los mocks
FARO_P1_ADAPTERS=real uvicorn "apps.api.main:create_app" --factory --port 8000
```

| Variable | Por defecto | Para qué |
|---|---|---|
| `FARO_MODE` | `demo` | `pilot` exige PostgreSQL y bloquea el arranque sobre SQLite |
| `FARO_DB_PATH` | `data/faro.db` | Base SQLite local |
| `FARO_DATA_DIR` | `data/` | Directorio de datos |
| `FARO_DATABASE_URL` | `""` | URL del motor; en piloto debe empezar con `postgresql` |
| `FARO_BIND_HOST` | `127.0.0.1` | |
| `FARO_BIND_PORT` | `8000` | |
| `FARO_CORS_ORIGINS` | `http://127.0.0.1:3000,http://localhost:3000` | Allowlist explícita |
| `FARO_AUDIT_SECRET` | valor de demo | Secreto HMAC de asignación de auditoría |
| `FARO_SCENARIO_SECRET` | valor de demo | Clave del escenario mínimo cifrado |
| `FARO_P1_ADAPTERS` | `mock` | `real` corre contra `ml/**` y `rag/runtime` |

`apps/api/ports/` declara cuatro protocolos (`defaults`, `form`, `prediction`,
`rag`) que solo describen la forma del resultado; `FARO_P1_ADAPTERS` elige quién
los implementa (`apps/api/adapters/p1` o `apps/api/adapters/mock`).

---

## 12. Qué devuelve hoy, con la demo sembrada

Cuatro estados independientes; ninguno implica al otro:

| Estado | Valor |
|---|---|
| `implementation_status` | `p2_integrated_against_p1` |
| `corpus_status` | `fixture_only` |
| `target_definition_status` | `demo_fixture_only` |
| `catalog_status` | `blocked_clinical_review` |

Con esos datos, el dominio real **no inventa nada**, y eso es lo correcto de ver:

- el estimador de defaults no sugiere sobre la cohorte sintética `demo_fixture`;
- el baseline personal se abstiene por falta de outcomes verificados
  (`insufficient_verified_outcomes`);
- el track sintético responde `unavailable` (`model_artifact_unavailable`): el
  binario v0.2 no está en Git;
- el catálogo de recomendaciones responde `clinical_review_unavailable`.

---

## 13. Verificación

```bash
# Contrato
python -m tools.contracts.generate
python -m tools.contracts.examples
git diff --exit-code packages/shared/generated packages/shared/examples

# Backend
ruff check . && ruff format --check .
lint-imports
pytest tests -q

# El camino real existe de verdad, no solo el mock
FARO_P1_ADAPTERS=real pytest tests/integration -q
```

`tests/p2/test_openapi.py` compara el OpenAPI publicado contra `SPEC 11.1`.
`tests/p2/test_invariants.py` cubre INV-01, 05, 08, 11–15, 27, 29–31; los
algorítmicos y de contrato viven en `tests/p1`. `lint-imports` verifica que las
capas no se rompieron: `apps` puede depender de `ml` y `rag`, nadie depende de
`apps`, y **el store no calcula**.
