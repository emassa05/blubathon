# Faro - demo local v0.3.0

Faro organiza registros diarios, calcula estadísticas personales, presenta
estimaciones experimentales y ofrece apoyos previamente curados para revisión
profesional.

Faro **no** diagnostica, **no** prescribe, **no** reemplaza el criterio
profesional y **no** ejecuta intervenciones de forma autónoma. Tampoco monitorea
emergencias: ante peligro inmediato hay que seguir los protocolos locales sin
esperar una alerta de esta aplicación (`SPEC 2.27`).

Los documentos normativos son `SPEC.md`, `CONVENTIONS.md`, `TAREAS.md` y
`FUNDAMENTOS.md`. Ante contradicción manda `SPEC.md`.

---

## Qué contiene esta parte del repositorio

Este README documenta la zona de P2: producto, persistencia y experiencia, ya
integrada sobre el dominio de P1.

```text
apps/api/       FastAPI, servicios de aplicación, store y migraciones
apps/web/       Next.js 15 con TypeScript strict
tools/seed/     siembra de la demo con datos completamente ficticios
tests/p2/       API, store, seguridad e invariantes de persistencia
tests/integration/  journeys extremo a extremo, en los dos conjuntos de adaptadores
```

Las zonas de P1 (`packages/shared`, `ml`, `rag`, `tools/contracts`,
`tools/train`, `tools/rag_authoring`, `tests/p1`) siguen siendo suyas: desde aquí
se consumen, no se editan. La única excepción es `packages/shared/package.json`,
que declara el contrato generado como paquete del workspace de pnpm para que el
frontend pueda importarlo.

---

## Estado del release

El manifest de release distingue cuatro estados independientes:

| Estado | Valor actual | Por qué |
|---|---|---|
| `implementation_status` | `p2_integrated_against_p1` | API, store, seguridad y UI corren contra el dominio de P1; `mock` queda como camino seleccionable de test y demo |
| `corpus_status` | `fixture_only` | No hay corpus legalmente utilizable; el fixture es de demostración |
| `target_definition_status` | `demo_fixture_only` | Hay target `demo_fixture` activo; no hay target real aprobado |
| `catalog_status` | `blocked_clinical_review` | No hay revisor clínico autorizado; ninguna estrategia llega a `active` |

Con `catalog_status=blocked_clinical_review` el runtime responde
`clinical_review_unavailable` y la demo muestra la abstención correctamente. No
se afirma que exista un catálogo clínicamente activo.

`implementation_status=p2_integrated_against_p1` dice que el producto corre
sobre el dominio publicado, no que produzca estimaciones clínicas. Con la demo
sembrada, el estimador real de defaults no sugiere nada (la cohorte es
`demo_fixture` y sus filas son sintéticas, `SPEC 6.2`), el baseline personal se
abstiene por `insufficient_verified_outcomes` y el track de simulación responde
`unavailable` porque el binario v0.2 no está en Git. Eso es exactamente lo que
el SPEC exige que se vea con estos datos.

---

## Cómo correr la demo

Requisitos: Python 3.12+ con las dependencias del proyecto instaladas, Node 20+
y pnpm 9.

```bash
# 1. Sembrar la base local con datos ficticios (estado honesto de release).
python -m tools.seed --catalog blocked

#    Para recorrer el flujo profesional completo con un catálogo fixture:
#    python -m tools.seed --catalog fixture-active

# 2. Levantar la API en 127.0.0.1.
uvicorn "apps.api.main:create_app" --factory --host 127.0.0.1 --port 8000

# 3. Levantar el frontend.
pnpm --dir apps/web dev
```

La aplicación queda en `http://127.0.0.1:3000`. La documentación OpenAPI está en
`http://127.0.0.1:8000/docs` y se deshabilita automáticamente en modo piloto.

### Cuentas de demostración

La demo usa sesiones locales ficticias preseeded (`SPEC 12.3`). El token no es un
secreto de producción y el modo piloto rechaza este mecanismo.

| Token | Persona ficticia | Rol |
|---|---|---|
| `demo-cuidadora-ana` | Ana Ríos | `caregiver` |
| `demo-profesional-a` | Pilar Soto | `professional` acreditada |
| `demo-evaluador-a` | Evaluador Demo A | `model_evaluator` |
| `demo-profesional-sin-acreditacion` | Profesional sin acreditación | `professional` sin acreditación vigente |
| `demo-cuidador-b` | Cuidador Demo B | `caregiver` de otra organización |

Los tres primeros están en el selector de cuenta del frontend; los otros dos
existen para probar 403 auditados.

### Variables de entorno

| Variable | Por defecto | Para qué |
|---|---|---|
| `FARO_MODE` | `demo` | `pilot` exige PostgreSQL y bloquea el arranque sobre SQLite |
| `FARO_DB_PATH` | `data/faro.db` | Base SQLite local |
| `FARO_CORS_ORIGINS` | `http://127.0.0.1:3000,http://localhost:3000` | Allowlist explícita |
| `FARO_AUDIT_SECRET` | valor de demo | Secreto HMAC de asignación de auditoría |
| `FARO_SCENARIO_SECRET` | valor de demo | Clave del escenario mínimo cifrado |
| `FARO_P1_ADAPTERS` | `mock` | `real` corre contra `ml/**` y `rag/runtime` |
| `NEXT_PUBLIC_FARO_API` | `http://127.0.0.1:8000/api/v1` | Origen de la API para el frontend |

---

## Rutas

Las 11 rutas de producto de `SPEC 11.1`, más tres de soporte del despliegue
(`/health`, `GET /api/v1/session` y `GET /api/v1/form-sessions/{id}`).

| Método | Ruta | Resultado |
|---|---|---|
| POST | `/api/v1/form-sessions` | Abre sesión y fija auditoría |
| POST | `/api/v1/form-sessions/{id}/answers` | Añade respuesta y recalcula orden |
| POST | `/api/v1/form-sessions/{id}/submit` | Cierra y crea o enlaza episodio primario |
| GET | `/api/v1/prediction-episodes/{id}` | Devuelve outputs autorizados |
| GET | `/api/v1/outcome-requests` | Lista outcomes pendientes del actor |
| POST | `/api/v1/prediction-episodes/{id}/outcome-reports` | Reporta yes/no/unknown |
| GET | `/api/v1/prediction-episodes/{id}/recommendations` | Devuelve catálogo precomputado |
| GET | `/api/v1/recommendation-instances?review_status=pending` | Inbox profesional autorizado |
| POST | `/api/v1/recommendation-instances/{id}/reviews` | Registra decisión por estrategia |
| POST | `/api/v1/recommendation-instances/{id}/executions` | Registra aplicación |
| GET | `/api/v1/evaluation/{model_version}` | Reporte versionado |

Todo POST exige `Idempotency-Key`. Las reviews y ejecuciones exigen `If-Match`.
Una abstención es HTTP 200 con estado explícito y nunca usa el sobre de error.

---

## Cómo depende P2 del dominio de P1

Toda dependencia pasa por un puerto, y el conjunto de adaptadores se elige con
`FARO_P1_ADAPTERS`:

```text
apps/api/ports/        protocolos: defaults, formulario, predicción, runtime RAG
apps/api/adapters/p1   adaptadores reales sobre `ml/**` y `rag/runtime`
apps/api/adapters/mock adaptadores fixture, camino seleccionable de test y demo
apps/api/store/history.py  lecturas que el dominio puro necesita como entrada
apps/api/contracts/    re-export de `packages/shared`
apps/web/lib/contracts.ts  re-export de `@faro/contract`
apps/web/lib/texts.ts      mapea `FARO_TEXTS_ES` a los nombres de la UI
```

El contrato ejecutable ya no se duplica: `apps/api/contracts/**`,
`apps/api/canonical.py` y `apps/web/lib/contracts.ts` reexportan
`packages/shared`, y los validadores de P1 son los que hacen cumplir SPEC 8.5,
10.2 y 11.5 en las respuestas.

### Qué quedó cableado contra P1

| Puerto | Lo que llama de P1 |
|---|---|
| `defaults` | `assign_audit_mode`, y `compute_default_decision` sobre `eligible_history` |
| `form` | `build_form_plan` con la cobertura de `compute_dqi`, y `build_scenario` |
| `prediction` | `score_simulation`, `build_personal_baseline`, y la versión en sombra del challenger |
| `rag` | `decide(RuntimeInputs)` con `RuntimeCatalog` |

`ml.prediction.predict` y `rag.runtime.recommend` no existen: P1 publica el doble
track por separado y `decide`. El adaptador arma ambas formas; los puertos, los
servicios y el store no cambiaron para acomodarlas.

### Qué sigue en mock, y por qué

`apps/api/adapters/mock` no se borró: es el camino de `tests/p2`, donde una
sugerencia de fixture permite comprobar INV-01 con datos que el estimador real
-correctamente- no produce sobre una cohorte sintética. Los mocks no calculan
ninguna fórmula del SPEC.

| Puerto | Hace | No hace |
|---|---|---|
| `defaults` | Lee sugerencias de fixture y asigna auditoría HMAC estable | No calcula Beta, Dirichlet ni ventanas limpias |
| `form` | Ordena por prioridad declarada y construye el escenario mínimo | No calcula DQI, VoI ni anomalías; `voi_nats` siempre `null` |
| `prediction` | Devuelve score de simulación de fixture y abstenciones | No entrena, no estima, no calibra |
| `rag` | Evalúa fail-closed el predicate del set y de cada estrategia | No indexa, no recupera, no usa BM25/RRF ni verifica citas |

---

## Solicitudes a P1

Estas son las divergencias que P2 necesita resolver con P1. Cada una lleva ruta,
request, response y el test consumidor que la fija. Las que H1 ya resolvió están
marcadas como cerradas, con lo que P1 decidió.

Las que siguen abiertas están declaradas en un solo lugar del código: cada
respuesta de producto que las necesita es una **subclase** del modelo publicado
en `packages/shared`, en `apps/api/contracts/models.py` y en
`apps/web/lib/contracts.ts`. Nada del contrato se redeclara; lo único declarado
es el campo que falta.

### R1 - `submit` no puede decir por qué no hubo target — **abierta**

`SPEC 4.3` distingue dos causas de fallo cerrado: cero versiones activas
(`target_definition_unavailable`) y más de una (`target_definition_ambiguous`).
`SubmitStatus` de P1 tiene tres valores y `FormSubmitResponse` no lleva razones,
así que la segunda causa no llega al cliente.

- Ruta: `POST /api/v1/form-sessions/{id}/submit`
- Request: sin cuerpo.
- Response propuesta: `FormSubmitResponse` más
  `"reasons": ["target_definition_ambiguous"]`.
- Razón: distinguir "no hay definición" de "hay más de una" sin inventar un
  cuarto valor de `status`.
- Test consumidor:
  `tests/p2/test_episodes_and_outcomes.py::test_two_effective_target_versions_fail_closed`.
- Mientras tanto: `SubmitFormSessionView` declara `reasons`, y P2 persiste
  `form_sessions.prediction_status = 'target_definition_ambiguous'`.

### R2 - precedencia de `entry_mode` para sesión profesional con `unknown` — **abierta**

`SPEC 5.5` ordena `professional_observed` (regla 2) antes de `explicit_unknown`
(regla 3). Una sesión `professional_observation` en la que el profesional
responde `unknown` cumple ambas, pero `professional_observed` asigna valor y
`unknown` es por definición una decisión sin valor (`SPEC 8.2`).

- Ruta: `POST /api/v1/form-sessions/{id}/answers`
- Request: `{"answer": {"field_code": "gi_status", "interaction": "unknown"}}` en
  una sesión `session_kind=professional_observation`.
- Response actual: `{"entry_mode": "explicit_unknown", ...}`.
- Razón: la alternativa literal persistiría una observación
  `professional_observed` sin valor, que la propia tabla prohíbe.
- Test consumidor:
  `tests/p2/test_form_sessions.py::test_explicit_unknown_persists_without_a_value`.
- Decisión pedida: confirmar la precedencia o declarar la combinación inválida.

### R3 - catálogo cerrado de `behavior_tags` — **abierta, y P2 dejó de inventarlo**

`SPEC 5.2` declara `behavior_tags` como catálogo versionado sin enumerarlo. P2
había propuesto seis valores; H1 publicó el campo como `tag_set` con forma de
token (`^[a-z][a-z0-9_]*$`) y sin catálogo, que es lo que `SPEC 19` manda: una
decisión ausente se registra como pregunta, no se inventa.

- Consecuencia visible: el control de `behavior_tags` ya no ofrece opciones y lo
  dice; la interfaz no completa vocabulario clínico por su cuenta.
- Decisión pedida: publicar el catálogo versionado, o declarar el campo fuera de
  alcance en v0.3.

### R4 - capability de acreditación para revisar una recomendación de caso — **abierta**

`SPEC 13.1` pide "`required_approver_role` acreditado" con capability de grant
`recommendation_review`, sin fijar qué capability de acreditación aplica. P2 usa
`subject_care`, reservando `strategy_review` para autoría. Confirmar.

### R5 - la sesión de formulario no publica su bloque de outcome pendiente — **abierta**

`SPEC 6.9` pone el outcome pendiente como paso 1 del plan, en un bloque aparte
que no consume cupos. `FormPlan` de P1 lo reduce a `outcome_pending: bool` y
`FormSessionResponse` no lo lleva, así que la pregunta, sus anclas y sus plazos
no llegan al cliente por el contrato.

- Ruta: `POST /api/v1/form-sessions` y `GET /api/v1/form-sessions/{id}`
- Response propuesta: `FormSessionResponse` más
  `"outcome_pending": {"prediction_episode_id", "question_es",
  "severity_anchors_es", "target_end_at", "capture_deadline_at", "state"}`, y
  además `status`, `submitted_at`, `answered_field_codes` y `plan_source`.
- Test consumidor: `tests/integration/test_caregiver_journey.py` paso 8.
- Mientras tanto: `FormSessionView` los declara.

### R6 - el inbox profesional no publica de quién es el registro — **abierta**

`RecommendationInstanceView` lleva `subject_id`, no una etiqueta visible. Sin
ella el profesional lee UUIDs.

- Ruta: `GET /api/v1/recommendation-instances?review_status=pending`
- Response propuesta: `RecommendationInstanceView` más `"subject_label"`.
- Test consumidor: `tests/p2/test_recommendations.py::test_inbox_only_lists_subjects_with_an_active_grant`.

### R7 - el inbox publica el hash del escenario, no el escenario — **abierta**

`RecommendationInstanceView` lleva `scenario_hash`, que identifica el escenario
pero no lo describe. Quien revisa necesita ver el escenario mínimo de
`SPEC 9.7` -sin identificadores directos- para juzgar aplicabilidad, y qué
estrategias siguen pendientes.

- Ruta: `GET /api/v1/recommendation-instances?review_status=pending`
- Response propuesta: más `"scenario": ScenarioV1`, `"runtime_status"` y
  `"pending_strategy_version_ids"`.
- Test consumidor: `tests/p2/test_recommendations.py::test_professional_sees_the_scenario_without_identifiers`.

### R8 - un item de recomendación no dice quién lo aprueba ni quién lo aplica — **abierta**

`StrategyItem` y `HumanPlanItem` publican texto y citas. Sin
`required_approver_role` y `allowed_executor_roles` el cliente no sabe quién
puede aprobar ni quién puede aplicar; sin `non_actionable` no puede mostrar que
una dependencia suspendida bloquea nuevas acciones (`SPEC 10.2`); sin
`execution_status` no sabe si ya se registró una aplicación (`SPEC 10.3`).

- Ruta: `GET /api/v1/prediction-episodes/{id}/recommendations`
- Test consumidor: `tests/p2/test_recommendations.py::test_suspended_dependency_makes_the_instance_non_actionable`.

### R9 - `POST .../answers` no tiene response publicada — **abierta**

El contrato publica `FormAnswerRequest` y no un modelo de respuesta. El cliente
necesita saber qué observación se creó y con qué `entry_mode` la derivó el
servidor (`SPEC 5.5`), además del plan recalculado.

- Ruta: `POST /api/v1/form-sessions/{id}/answers`
- Response propuesta: `{"field_observation_id", "field_code", "entry_mode",
  "session"}`.
- Test consumidor: `tests/p2/test_form_sessions.py::test_manual_answer_over_a_presented_default_is_default_edited`.

### R10 - el episodio no publica el estado de su outcome — **abierta**

`PredictionEpisodeResponse` no lleva el estado derivado de la solicitud ni el
instante de predicción, distinto del cutoff `as_of_at` (`SPEC 4.1`).

- Ruta: `GET /api/v1/prediction-episodes/{id}`
- Response propuesta: más `"prediction_at"`, `"outcome_state"` y
  `"resolution_status"`.
- Test consumidor:
  `tests/p2/test_episodes_and_outcomes.py::test_deadline_without_a_conclusive_report_becomes_unknown_and_missing`.

### R11 - el reporte de evaluación no dice qué fila es — **abierta**

`EvaluationResponse` no lleva `evaluation_report_id`, el estado del modelo
(`ModelState`, `SPEC 14.2`) ni cuándo se publicó.

- Ruta: `GET /api/v1/evaluation/{model_version}`
- Test consumidor: `tests/p2/test_evaluation.py::test_evaluator_reads_a_published_report`.

### R12 - una corrección de observación no se puede expresar — **abierta**

`SPEC 5.8` hace append-only la observación diaria y una corrección se enlaza con
`supersedes_id`; `SPEC 5.5` permite declarar el instante efectivo de lo
observado. `AnswerSubmission` no lleva ninguno de los dos.

- Ruta: `POST /api/v1/form-sessions/{id}/answers`
- Request propuesto: `AnswerSubmission` más `"effective_at"` y `"supersedes_id"`.
- Test consumidor: `tests/p2/test_form_sessions.py::test_correction_keeps_the_original_row`.

### R13 - el contrato no lleva token de concurrencia — **abierta**

`SPEC 11.2` exige `If-Match` sobre los recursos con revisión y ninguna respuesta
publicada lleva un token que el cliente pueda devolver.

- Ruta: `GET /api/v1/prediction-episodes/{id}/recommendations` y el inbox.
- Response propuesta: más `"revision"`. La lectura individual además lo manda en
  la cabecera `ETag`.
- Test consumidor: `tests/p2/test_recommendations.py::test_review_requires_if_match_and_rejects_a_stale_revision`.

### R14 - reportar un outcome no devuelve el estado de la solicitud — **abierta**

`SPEC 4.4` deriva el estado de la `OutcomeRequest` del reloj y de la resolución
activa. P1 publica la regla (`derive_request_state`) pero `OutcomeReportResponse`
no devuelve su resultado, y el cliente no puede derivarla sin reimplementar la
precedencia.

- Ruta: `POST /api/v1/prediction-episodes/{id}/outcome-reports`
- Response propuesta: más `"request_state"`.
- Test consumidor: `tests/p2/test_episodes_and_outcomes.py::test_incompatible_reports_produce_conflicted`.

### R15 - la ejecución no dice qué se aplicó ni si cuenta — **abierta**

`StrategyExecutionResponse` no dice qué estrategia o plan se aplicó, y
`SPEC 10.3` distingue una aplicación tardía, que se conserva pero no se atribuye.
P1 publica la regla (`exposure_is_eligible`) pero no un campo donde devolver su
resultado.

- Ruta: `POST /api/v1/recommendation-instances/{id}/executions`
- Response propuesta: más `"strategy_version_id"`, `"human_plan_version_id"` y
  `"exposure_eligible"`.
- Test consumidor: `tests/integration/test_professional_journey.py::test_a_late_application_is_kept_but_not_attributed`.

### Cerradas por H1

- **Nombres de enums.** `SessionKind`, `EpisodeStatus`, `OutcomeValue`,
  `ResolutionStatus`, `OutcomeRequestStatus`, `ItemType`, `CatalogAvailability` y
  `ReportEstimability` de P2 pasan a los nombres publicados. `PredictionStatus`
  nombra el estado de una salida y el cierre de sesión usa `SubmitStatus`.
  `VersionStatus` se separa en `StrategyStatus` y `CatalogStatus`.
- **Valores.** `estimate_kind` usa `simulation_score` y
  `shadow_challenger_score`; una métrica estimada es `estimated`, no
  `estimable`; `interval` es `{lower, upper}`.
- **Textos.** La copia visible es la de `packages/shared/texts.py` y llega
  generada al frontend; la API dejó de repetir el aviso de emergencia en cada
  respuesta.
- **`EpisodeRole`.** P1 publica solo `primary`; `secondary` era un valor que
  nada escribía.
- **`accept_default`.** `AnswerSubmission` exige declarar el valor aceptado, y
  el servidor lo compara con el presentado antes de guardarlo.
- **Bytes canónicos.** `apps/api/canonical.py` reexporta
  `packages/shared/canonical.py`: había dos implementaciones de `SPEC 5.9`.

## Verificación

```bash
# Contrato: nada de `generated/` ni de `examples/` se edita a mano.
python -m tools.contracts.generate
python -m tools.contracts.examples
git diff --exit-code packages/shared/generated packages/shared/examples

# Backend
ruff check . && ruff format --check .
lint-imports
pytest tests -q

# Frontend
pnpm -C apps/web typecheck && pnpm -C apps/web test && pnpm -C apps/web build

# El camino real existe de verdad.
FARO_P1_ADAPTERS=real pytest tests/integration -q
```

`tests/p2/test_openapi.py` compara el documento OpenAPI publicado con la tabla de
rutas de `SPEC 11.1` y comprueba que cada respuesta use un modelo explícito.
`lint-imports` comprueba que la integración no rompió las capas: `packages` no
depende de nadie, `ml` y `rag` no importan `apps`, y el store no importa ningún
módulo de cálculo.

### Invariantes cubiertos por P2

`tests/p2/test_invariants.py` nombra uno por uno los invariantes que `TAREAS 11`
asigna a P2: INV-01, INV-05, INV-08, INV-11 a INV-15, INV-27, INV-29, INV-30 e
INV-31. Los invariantes algorítmicos y de contrato viven en `tests/p1`.

Desde la integración, varios los hace cumplir el propio contrato y no una
comprobación de P2: `PredictionOutputView` rechaza una abstención con número, una
simulación presentada como probabilidad y cualquier exposición del challenger;
`FormSessionResponse` rechaza un default dentro de una sesión auditada;
`FormSubmitResponse` rechaza un episodio sin definición de target;
`OutcomeResolutionView` rechaza un conflicto presentado limpio; `HumanPlanItem`
rechaza un plan del equipo con citas; e `IdempotencyScope` rechaza un scope
armado con el template de la ruta. `packages/shared/examples/invalid/` tiene un
ejemplo por cada uno, y `tests/integration/test_adapter_sets.py` comprueba que se
sostienen en los dos conjuntos de adaptadores.

---

## Saneamiento v0.2 realizado

`TAREAS P2.2` pide retirar el legado. Se retiraron:

- `tests/conftest.py`: fixture global v0.2 que entrenaba un modelo por sesión.
- `tests/unit/**`: `test_api.py` y `test_store.py` probaban la API v0.2 que este
  trabajo reemplaza; `test_voi.py`, `test_narrative.py`, `test_eval.py`,
  `test_strategies.py` y `test_bluba_adapter.py` cubrían módulos de `ml/`, cuyo
  reemplazo corresponde a P1 en `tests/p1`.
- `tests/invariants/**`: `test_constitution.py` y `test_dependency_rule.py`; la
  regla de dependencias la comprueba `import-linter`.
- `apps/api/**` v0.2 completo, reemplazado por la implementación de este SPEC.
- El contrato provisional de P2: `apps/api/contracts/**`, `apps/api/canonical.py`
  y `apps/web/lib/contracts.ts` dejaron de declarar modelos, enums, constantes,
  textos y hashes propios, y pasaron a reexportar `packages/shared`.

No se tocó `tests/p1/**`, `ml/**`, `rag/**` ni el contenido de
`packages/shared/**`.

---

## Límites conocidos de esta entrega

- Con la demo sembrada, el dominio real no produce ningún número: la cohorte es
  `demo_fixture`, sus filas son sintéticas y `SPEC 6.2` no las deja informar una
  sugerencia; el baseline personal se abstiene por falta de outcomes
  verificados; y el track de simulación responde `unavailable` porque el binario
  v0.2 no está en Git. Los números que se ven en el camino `mock` son de
  fixture y están rotulados como tales.
- El catálogo fixture del seeder existe para recorrer el flujo profesional. Sus
  documentos llevan `publisher=FIXTURE_DEMO` y `rights_basis=fixture_demo_only`;
  no son literatura clínica.
- El cifrado del escenario mínimo es local y suficiente para que el payload no
  quede legible en el archivo SQLite. El piloto exige un gestor de claves
  institucional.
- La serialización por `(tenant_id, subject_id)` usa `BEGIN IMMEDIATE`, que en
  SQLite serializa a todos los escritores. En PostgreSQL el equivalente es
  `SELECT ... FOR UPDATE` sobre la fila del sujeto.
