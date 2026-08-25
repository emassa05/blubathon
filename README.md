# Faro - backend v0.3.0

Faro organiza registros diarios, calcula estadísticas personales, presenta
estimaciones experimentales y ofrece apoyos previamente curados para revisión
profesional.

Faro **no** diagnostica, **no** prescribe, **no** reemplaza el criterio
profesional y **no** ejecuta intervenciones de forma autónoma. Tampoco
monitorea emergencias (`SPEC 2.27`).

Los documentos normativos son `SPEC.md`, `CONVENTIONS.md`, `TAREAS.md` y
`FUNDAMENTOS.md`. Ante contradicción manda `SPEC.md`. Este README documenta
solo el backend (`apps/api`, `ml`, `rag`, `packages/shared`, `tools`); el
frontend (`apps/web`) tiene su propia documentación.

---

## 1. Las piezas y quién manda sobre quién

```text
packages/shared/   el contrato: modelos, enums, constantes, catálogo de
                    campos, textos y bytes canónicos. No importa a nadie.
ml/                 dominio puro: defaults, formulario, predicción, evaluación.
                    Funciones sobre filas ya cargadas; no abre la base, no lee
                    el reloj.
rag/                autoría del corpus (offline) y runtime determinista de
                    recomendación (online, sin LLM).
apps/api/           FastAPI: rutas, servicios de aplicación, store (SQLite) y
                    migraciones. Es quien carga filas y llama al dominio.
tools/              contracts (genera el contrato), seed (datos ficticios),
                    train (entrena y evalúa ml/prediction).
```

`lint-imports` hace cumplir la capa: `apps` puede depender de `ml` y `rag`,
nadie depende de `apps`, y **el store no calcula** — cuando un servicio
necesita un número se lo pide a un puerto, nunca lo deriva él mismo.

`apps/api/ports/` declara cuatro protocolos (`defaults`, `form`, `prediction`,
`rag`) que solo describen la forma del resultado. `FARO_P1_ADAPTERS` elige
quién los implementa:

| Adaptador | Cuándo | Qué hace |
|---|---|---|
| `apps/api/adapters/p1` (`FARO_P1_ADAPTERS=real`) | dominio real | llama a `ml/**` y `rag/runtime` sobre filas de la base |
| `apps/api/adapters/mock` (por defecto) | tests de P2 y demo | responde con fixtures fijas, sin fórmulas del SPEC |

---

## 2. Cómo se resuelve cada caso

Once rutas de producto (`SPEC 11.1`). Esto es qué calcula cada una y con qué
regla, no solo qué devuelve.

### Abrir sesión — `POST /form-sessions`

1. **`audit_mode`** se fija una sola vez, con
   `HMAC_SHA256(secret, tenant_id | subject_id | local_date | policy_version) mod 1000 < 100`.
   Es decir: ~10% de las sesiones no ve sugerencias, de forma estable e
   impredecible desde el cliente. Nunca se recalcula (`INV-05`).
2. **El plan** (`ml/form/plan.py::build_form_plan`) ordena los campos así:
   outcome pendiente → vencidos por antigüedad (≥7 días sin preguntarse) →
   cuota de exploración (día ISO elegido también por HMAC semanal) → mayor VoI
   disponible → orden canónico para llenar cupos → el resto en cola. Todos los
   campos quedan accesibles siempre; "destacado" es solo prioridad de
   atención (`INV-10`).
3. Si `audit_mode=false`, cada campo de la allowlist recibe una sugerencia de
   default si `compute_default_decision` (`ml/defaults/estimator.py`) supera
   el umbral — ver §3.

### Responder — `POST /form-sessions/{id}/answers`

El cliente manda una **interacción** (`manual | accept_default | edit_default
| unknown`); el servidor deriva el **`entry_mode`** real, con esta
precedencia fija (nunca por "lo que dijo el cliente"):

1. Canal de importación con mapping aprobado → `imported_observed`.
2. Sesión de observación profesional → `professional_observed`.
3. Interacción `unknown` → `explicit_unknown`, **sin valor** (no es `0`, no es
   `false`, no es vacío).
4. Sesión auditada, respuesta manual → `audit_manual`.
5. `accept_default` sobre una sugerencia vigente, con el valor aceptado
   igual al presentado → `default_accepted`.
6. Cualquier valor manual sobre un campo con sugerencia vigente, aunque el
   cliente diga `manual` → `default_edited`. No se puede pisar una sugerencia
   sin que quede registrado.
7. Si el campo nunca tuvo sugerencia → `manual_no_default`.

Una sugerencia que nadie toca no crea observación (`INV-01`).

### Cerrar — `POST /form-sessions/{id}/submit`

Serializado por `(tenant_id, subject_id)` (evita dos episodios a la vez sobre
el mismo sujeto). La regla es fail-closed:

```text
si no hay TargetDefinitionVersion activa y única para el instante:
    cerrar con target_definition_unavailable (o _ambiguous si hay > 1)
    no se crea episodio ni outcome request
si hay definición y no hay episodio primario abierto:
    crear PredictionEpisode + OutcomeRequest inmutable
    snapshot = IDs de observaciones proyectadas al cutoff (no una copia de
    valores: una corrección después no cambia lo que el episodio vio)
si hay definición y ya hay un episodio primario abierto:
    enlazar la sesión a ese episodio, no crear otro
```

### Ver estimaciones — `GET /prediction-episodes/{id}`

Tres tracks que nunca comparten significado (`SPEC 8.1`), y cada uno se
abstiene por su propia regla:

| Track | Cómo se calcula | Se abstiene si |
|---|---|---|
| `synthetic_reference_v021` | LightGBM sobre datos sintéticos, solo cohorte `demo_fixture` | falta el artefacto del modelo (`model_artifact_unavailable`) |
| `real_personal_baseline_v1` | `Beta(1+e, 1+n-e)` sobre outcomes reales previos del mismo sujeto/`care_mode`/target, ventana 60 días; `p_mean=(1+e)/(2+n)`, intervalo `[BetaPPF(0.05), BetaPPF(0.95)]` | `verified_outcomes < 5`, conflicto sin resolver, o falta historial de `care_mode` |
| `real_logit_challenger_v1` | regresión logística preentrenada con offset del baseline + desviaciones de sueño y regulación | siempre en sombra: nunca se expone, el modelo del contrato lo rechaza si se intenta |

Sin política de decisión validada, no hay bandas verde/ámbar/rojo
(`decision_policy_version`, `risk_band` quedan `null`, `SPEC 8.6`).

### Recomendación — `GET .../recommendations`

`rag/runtime/decide.py::decide(RuntimeInputs)` es puro y determinista: cero
llamadas a LLM en runtime. Recibe el escenario mínimo (campos con valor real,
sin identidad ni notas) y el catálogo activo, evalúa el *predicate* del set y
el de cada estrategia por separado, fail-closed, y devuelve como máximo tres
estrategias ya revisadas con sus citas exactas. `medication_adherence` no
entra al escenario si se respondió `unknown`: un `unknown` no asigna valor.

Mientras las estrategias siguen sin revisar, la familia ve
`{"status": "awaiting_professional_review", "items": []}`. El filtro por
actor y grants se aplica en el servidor, nunca solo en el cliente.

### Revisión profesional — `POST .../reviews`

Decisiones posibles: `approved`, `rejected`, `human_plan_substituted`,
`not_applicable`, `deferred`. Usa concurrencia optimista con `If-Match`: sin
cabecera → 428; revisión vigente → 201; revisión obsoleta → 409. Una
sustitución crea un plan del equipo que **no hereda citas** del original
(`INV-29`) y no puede ampliar los roles de ejecución de la estrategia
sustituida.

### Ejecución — `POST .../executions`

Registra que alguien aplicó una estrategia o un plan. `exposure_eligible` es
`false` si la aplicación llegó después del cierre de la ventana target o
antes de la revisión que la autorizó — se conserva el registro, pero no
cuenta como exposición válida (`SPEC 10.3`).

### Resultado — `POST .../outcome-reports`

El servidor deriva actor, rol, tenant e instante del contexto autorizado, y
resuelve así (`OutcomeService`, sobre la proyección al cutoff):

```text
1. yes elegible: timing_status in {early, on_time} y occurred_at en la ventana.
2. no elegible: solo timing_status = on_time.
3. hay yes y no elegibles a la vez -> conflicted, ever_conflicted=true.
4. solo yes -> yes; solo no -> no.
5. sin reporte concluyente antes del deadline -> pending; al vencer -> unknown.
```

Ni `no` ni `unknown` cierran la ventana antes de tiempo (`INV-14`). Una
resolución que alguna vez fue `conflicted` nunca vuelve a presentarse limpia:
`ever_conflicted` es monotónico.

---

## 3. Las fórmulas detrás de "sugerir" y "priorizar"

- **Default binario**: `k` ocurrencias en `N` observaciones elegibles (ventana
  limpia de 60 días, mismo tenant/sujeto/fuente/campo) →
  `Beta(1+k, 1+N-k)`, se sugiere si `BetaPPF(0.05) > 0.70` y el campo está en
  la allowlist (`food_changes`, `activity_participation`,
  `social_interactions`, `eating_status`, `attendance_status`).
- **Default categórico/ordinal**: Dirichlet con `alpha_j = 1+n_j`; candidato es
  el `argmax`; sin sugerencia si hay empate.
- **VoI**: información mutua aproximada entre la respuesta y el outcome,
  `VoI(X) = h(p_bar) - sum(q_j * h(p_j))` en nats; `null` (nunca `0`) si no
  hay modelo condicional.
- **Anomalía / cola completa**: se abre si `relevant_event_flag=true`,
  `medication_adherence=missed`, `daily_regulation_state=frequent_dysregulation`,
  `alertness` extremo, probabilidad categórica personal `< 0.05`, o
  `|robust_z| >= 2.0` sobre los últimos 30 días (mediana + MAD).

Ninguna de estas fórmulas vive en `apps/api`: el store solo lee filas y el
adaptador solo las pasa; el cálculo entero está en `ml/`.

---

## 4. Autorización

Todo acceso a datos clínicos exige tenant + rol + **grant activo sobre el
sujeto**, no solo rol (`SPEC 2.26`). Comprobado en la demo:

```text
cuidadora  -> GET /evaluation              403 role_not_allowed
cuidador B -> GET /prediction-episodes/…   404 not_found   (no 403: no revela existencia)
profesional sin acreditación -> GET inbox  403 accreditation_required
```

Cross-tenant siempre es 404, nunca 403: un 403 confirmaría que el recurso
existe. Cada negativa queda en auditoría append-only, sin payload clínico.

---

## 5. Cómo correr el backend

```bash
# 1. Sembrar la base local (datos completamente ficticios).
python -m tools.seed --catalog blocked          # estado honesto de release
python -m tools.seed --catalog fixture-active   # para recorrer el flujo profesional

# 2. Levantar la API.
uvicorn "apps.api.main:create_app" --factory --host 127.0.0.1 --port 8000

#    Contra el dominio real de P1 en vez de los mocks:
FARO_P1_ADAPTERS=real uvicorn "apps.api.main:create_app" --factory --port 8000
```

`GET /health` dice contra qué está corriendo:
`{"status": "ok", "spec_version": "0.3.0", "mode": "demo", "adapters": "p1"}`.
La documentación OpenAPI vive en `/docs` y se deshabilita sola en modo
piloto (`FARO_MODE=pilot`).

### Variables de entorno

| Variable | Por defecto | Para qué |
|---|---|---|
| `FARO_MODE` | `demo` | `pilot` exige PostgreSQL y bloquea el arranque sobre SQLite |
| `FARO_DB_PATH` | `data/faro.db` | Base SQLite local |
| `FARO_CORS_ORIGINS` | `http://127.0.0.1:3000,http://localhost:3000` | Allowlist explícita |
| `FARO_AUDIT_SECRET` | valor de demo | Secreto HMAC de asignación de auditoría |
| `FARO_SCENARIO_SECRET` | valor de demo | Clave del escenario mínimo cifrado |
| `FARO_P1_ADAPTERS` | `mock` | `real` corre contra `ml/**` y `rag/runtime` |

### Cuentas de demostración

| Token | Persona ficticia | Rol |
|---|---|---|
| `demo-cuidadora-ana` | Ana Ríos | `caregiver` |
| `demo-profesional-a` | Pilar Soto | `professional` acreditada |
| `demo-evaluador-a` | Evaluador Demo A | `model_evaluator` |
| `demo-profesional-sin-acreditacion` | — | `professional` sin acreditación vigente (para 403) |
| `demo-cuidador-b` | — | `caregiver` de otra organización (para 404 cross-tenant) |

---

## 6. Verificación

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

`tests/p2/test_openapi.py` compara el OpenAPI publicado contra `SPEC 11.1`.
`tests/p2/test_invariants.py` cubre los invariantes que le tocan a P2
(INV-01, 05, 08, 11-15, 27, 29-31); los algorítmicos y de contrato viven en
`tests/p1`. `lint-imports` verifica que las capas no se rompieron.

---

## 7. Estado real del release

Cuatro estados independientes, y ninguno implica al otro:

| Estado | Valor | Por qué |
|---|---|---|
| `implementation_status` | `p2_integrated_against_p1` | el backend corre sobre el dominio real; `mock` sigue como camino de test/demo |
| `corpus_status` | `fixture_only` | no hay corpus clínico legalmente utilizable |
| `target_definition_status` | `demo_fixture_only` | no hay target real aprobado |
| `catalog_status` | `blocked_clinical_review` | no hay revisor clínico autorizado; ninguna estrategia llega a `active` |

Con la demo sembrada, el dominio real no inventa nada: el estimador de
defaults no sugiere sobre la cohorte sintética `demo_fixture` (`SPEC 6.2`), el
baseline personal se abstiene por falta de outcomes verificados, el track
sintético responde `unavailable` porque el binario v0.2 no está en Git, y el
catálogo de recomendaciones responde `clinical_review_unavailable`. Eso es lo
correcto de ver con estos datos, no una falla.
