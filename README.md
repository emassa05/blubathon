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

Este README documenta la zona de P2: producto, persistencia y experiencia.

```text
apps/api/       FastAPI, servicios de aplicación, store y migraciones
apps/web/       Next.js 15 con TypeScript strict
tools/seed/     siembra de la demo con datos completamente ficticios
tests/p2/       API, store, seguridad e invariantes de persistencia
tests/integration/  journeys extremo a extremo
```

Las zonas de P1 (`packages/shared`, `ml`, `rag`, `tools/contracts`,
`tools/train`, `tools/rag_authoring`, `tests/p1`) no se editan desde aquí.

---

## Estado del release

El manifest de release distingue cuatro estados independientes:

| Estado | Valor actual | Por qué |
|---|---|---|
| `implementation_status` | `p2_complete_against_mocks` | API, store, seguridad y UI funcionan contra adaptadores fixture |
| `corpus_status` | `fixture_only` | No hay corpus legalmente utilizable; el fixture es de demostración |
| `target_definition_status` | `demo_fixture_only` | Hay target `demo_fixture` activo; no hay target real aprobado |
| `catalog_status` | `blocked_clinical_review` | No hay revisor clínico autorizado; ninguna estrategia llega a `active` |

Con `catalog_status=blocked_clinical_review` el runtime responde
`clinical_review_unavailable` y la demo muestra la abstención correctamente. No
se afirma que exista un catálogo clínicamente activo.

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
| `FARO_P1_ADAPTERS` | `mock` | `real` exige las façades de P1 |
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

## Cómo está aislada la dependencia de P1

P2 no espera a P1 y tampoco duplica sus contratos. Toda dependencia del dominio
de P1 pasa por un puerto:

```text
apps/api/ports/        protocolos: defaults, formulario, predicción, runtime RAG
apps/api/adapters/mock adaptadores fixture, activos hoy
apps/api/adapters/p1   punto exacto de integración cuando P1 publique H1
apps/api/contracts/    modelos de request/response provisionales
apps/web/lib/contracts.ts  tipos TypeScript provisionales
apps/web/lib/texts.ts      textos visibles provisionales
```

Los mocks viven únicamente en zonas P2, no calculan ninguna fórmula del SPEC y
devuelven `unavailable`/abstención donde el SPEC lo exige. Sustituir un mock es
implementar la clase equivalente en `apps/api/adapters/p1` y cambiar
`FARO_P1_ADAPTERS`; servicios, store y UI no cambian.

Los cuatro archivos marcados `PROVISIONAL - PUERTO HACIA P1` se convierten en
re-exports de `packages/shared` cuando exista H1.

### Qué hace y qué no hace cada mock

| Puerto | Hace | No hace |
|---|---|---|
| `defaults` | Lee sugerencias de fixture y asigna auditoría HMAC estable | No calcula Beta, Dirichlet ni ventanas limpias |
| `form` | Ordena por prioridad declarada y construye el escenario mínimo | No calcula DQI, VoI ni anomalías; `voi_nats` siempre `null` |
| `prediction` | Devuelve score de simulación de fixture y abstenciones | No entrena, no estima, no calibra |
| `rag` | Evalúa fail-closed el predicate del set y de cada estrategia | No indexa, no recupera, no usa BM25/RRF ni verifica citas |

---

## Solicitudes a P1

Estas son las divergencias que P2 necesita resolver con P1. Cada una lleva ruta,
request, response y el test consumidor que la fija.

### R1 - `submit` necesita exponer la razón de la selección de target

`SPEC 11.3` define `status` en `{episode_created, episode_linked,
target_definition_unavailable}`, pero `SPEC 4.3` distingue dos causas de fallo
cerrado: cero versiones activas (`target_definition_unavailable`) y más de una
(`target_definition_ambiguous`). Con solo tres estados, la segunda causa queda
invisible para el cliente.

- Ruta: `POST /api/v1/form-sessions/{id}/submit`
- Request: sin cuerpo.
- Response propuesta:

```json
{
  "form_session_id": "uuid",
  "status": "target_definition_unavailable",
  "submitted_at": "2026-08-25T19:55:00.000Z",
  "prediction_episode_id": null,
  "linked_prediction_episode_id": null,
  "outcome_request_id": null,
  "recommendation_instance_id": null,
  "reasons": ["target_definition_ambiguous"],
  "emergency_notice_es": "…"
}
```

- Razón: distinguir "no hay definición" de "hay más de una" sin inventar un
  cuarto valor de `status`.
- Test consumidor:
  `tests/p2/test_episodes_and_outcomes.py::test_two_effective_target_versions_fail_closed`.
- Mientras tanto: P2 persiste `form_sessions.prediction_status =
  'target_definition_ambiguous'` y devuelve la razón en `reasons`.

### R2 - precedencia de `entry_mode` para sesión profesional con `unknown`

`SPEC 5.5` ordena la derivación con `professional_observed` (regla 2) antes de
`explicit_unknown` (regla 3). Una sesión `professional_observation` en la que el
profesional responde `unknown` cumple ambas, pero `professional_observed` asigna
valor y `unknown` es por definición una decisión sin valor (`SPEC 8.2`).

- Ruta: `POST /api/v1/form-sessions/{id}/answers`
- Request: `{"field_code": "gi_status", "interaction": "unknown"}` en una sesión
  `session_kind=professional_observation`.
- Response actual: `{"entry_mode": "explicit_unknown", ...}`.
- Razón: la alternativa literal persistiría una observación
  `professional_observed` sin valor, que la propia tabla prohíbe.
- Test consumidor: `tests/p2/test_form_sessions.py::test_explicit_unknown_persists_without_a_value`.
- Decisión pedida: confirmar la precedencia o declarar la combinación inválida.

### R3 - catálogo cerrado de `behavior_tags`

`SPEC 5.2` declara `behavior_tags` como `enum[]` de un "catálogo versionado" sin
enumerar sus valores. P2 propone provisionalmente
`behavior-tags-0.3.0` con seis valores en
`apps/api/contracts/field_catalog.py`; el catálogo normativo es de P1.

### R4 - capability de acreditación para revisar una recomendación de caso

`SPEC 13.1` pide "`required_approver_role` acreditado" con capability de grant
`recommendation_review`, sin fijar qué capability de acreditación aplica. P2 usa
`subject_care`, reservando `strategy_review` para autoría. Confirmar.

---

## Verificación

```bash
# Backend
ruff check .
ruff format --check .
pytest tests/p2 tests/integration -q

# Frontend
pnpm --dir apps/web lint
pnpm --dir apps/web typecheck
pnpm --dir apps/web test
pnpm --dir apps/web build
```

`tests/p2/test_openapi.py` compara el documento OpenAPI publicado con la tabla de
rutas de `SPEC 11.1` y comprueba que cada respuesta use un modelo explícito.
Cuando P1 publique los contratos ejecutables, ese mismo test pasa a comparar
contra el JSON Schema generado.

### Invariantes cubiertos por P2

`tests/p2/test_invariants.py` nombra uno por uno los invariantes que `TAREAS 11`
asigna a P2: INV-01, INV-05, INV-08, INV-11 a INV-15, INV-27, INV-29, INV-30 e
INV-31. Los invariantes algorítmicos y de contrato viven en `tests/p1`.

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

No se tocó `tests/p1/**`, `ml/**`, `rag/**` ni `packages/shared/**`.

---

## Límites conocidos de esta entrega

- Todos los números que produce el backend vienen de adaptadores fixture. No hay
  ninguna estimación estadística real hasta que P1 publique `ml/`.
- El catálogo fixture del seeder existe para recorrer el flujo profesional. Sus
  documentos llevan `publisher=FIXTURE_DEMO` y `rights_basis=fixture_demo_only`;
  no son literatura clínica.
- El cifrado del escenario mínimo es local y suficiente para que el payload no
  quede legible en el archivo SQLite. El piloto exige un gestor de claves
  institucional.
- La serialización por `(tenant_id, subject_id)` usa `BEGIN IMMEDIATE`, que en
  SQLite serializa a todos los escritores. En PostgreSQL el equivalente es
  `SELECT ... FOR UPDATE` sobre la fila del sujeto.
