# Cómo funciona Faro v0.3.0

Guía de lectura del repositorio ya integrado: qué hace el sistema, por dónde
pasa una petición, y qué impide el contrato. Los documentos normativos siguen
siendo `SPEC.md`, `CONVENTIONS.md`, `TAREAS.md` y `FUNDAMENTOS.md`; ante
contradicción manda `SPEC.md`. Esto es el mapa, no la norma.

---

## 1. Qué es, y sobre todo qué no es

Faro organiza registros diarios de una persona acompañada, calcula estadística
personal sobre sus propios resultados, presenta estimaciones experimentales y
ofrece apoyos previamente curados para revisión profesional.

No diagnostica, no prescribe, no reemplaza el criterio profesional y no ejecuta
intervenciones por su cuenta. **No monitorea emergencias**: ante peligro
inmediato hay que seguir los protocolos locales sin esperar una alerta de esta
aplicación (`SPEC 2.27`).

Eso último no es un descargo legal pegado al final. Es un texto del contrato
(`packages/shared/texts.py`), se genera hacia el frontend y el componente que lo
muestra no puede escribir otro.

---

## 2. Dos mitades y un contrato en medio

El repositorio tiene dos zonas de trabajo y una frontera dura entre ellas.

```text
packages/shared/     el contrato ejecutable: modelos, enums, constantes,
                     catálogo de campos, textos, bytes canónicos
   └── generated/    lo mismo para el frontend: tipos, Zod, constantes,
                     catálogo y textos, generados, nunca escritos a mano

ml/                  dominio puro: defaults, formulario, predicción, evaluación
rag/                 autoría del corpus y runtime determinista de recomendación
tools/               contracts, train, rag_authoring, seed

apps/api/            FastAPI: rutas, servicios, store y migraciones
apps/web/            Next.js 15 con TypeScript strict
```

**Nada del contrato se declara dos veces.** `apps/api/contracts/**`,
`apps/api/canonical.py` y `apps/web/lib/contracts.ts` son re-exports de
`packages/shared`. Si un modelo, un enum, una constante o un texto visible
aparece en `apps/`, es un error: su lugar es `packages/shared`.

Cuatro contratos de import lo sostienen, y `lint-imports` los verifica:

| Contrato | Qué prohíbe |
|---|---|
| `shared-is-independent` | que `packages` importe `apps`, `ml`, `rag`, FastAPI o sqlite3 |
| `ml-does-not-import-apps` | que el dominio conozca la aplicación |
| `store-does-not-compute` | que el store importe `ml.defaults`, `ml.form`, `ml.prediction`, `ml.voi`… |
| `rag-does-not-touch-the-clinic` | que `rag` lea el store clínico |
| `runtime-has-no-model-index-or-network` | que el runtime llame a un LLM, a un índice o a la red |
| `layers` | `apps` sobre (`ml`, `rag`) sobre `packages` |

La regla que más se nota en el día a día es la tercera: **el store persiste, no
calcula**. Cuando un servicio necesita un número, no lo computa: se lo pide a un
puerto.

---

## 3. Puertos y adaptadores

`apps/api/ports/` declara cuatro protocolos —`defaults`, `form`, `prediction`,
`rag`— y nada más. No calculan: describen la forma del resultado.

`FARO_P1_ADAPTERS` elige quién los implementa:

```text
apps/api/adapters/p1/     el dominio real de P1  (FARO_P1_ADAPTERS=real)
apps/api/adapters/mock/   respuestas de fixture  (por defecto)
```

El dominio de P1 son funciones puras sobre filas ya cargadas: no abren la base,
no leen el reloj. Quien carga las filas es el adaptador, a través de
`apps/api/store/history.py`, que sólo lee. Por eso el conjunto real necesita la
base y falla explícito sin ella, en vez de devolver un resultado inventado.

### Qué llama cada adaptador real

| Puerto | Función de P1 |
|---|---|
| `defaults` | `assign_audit_mode`; `compute_default_decision` sobre `eligible_history` |
| `form` | `build_form_plan` con la cobertura de `compute_dqi`; `build_scenario(ScenarioInputs)` |
| `prediction` | `score_simulation`, `build_personal_baseline`, versión en sombra del challenger |
| `rag` | `decide(RuntimeInputs)` con `RuntimeCatalog` |

Dos façades que el puerto pedía no existen en P1, y el adaptador las arma:

- **`ml.prediction.predict`** no existe. P1 publica el doble track por separado,
  que es lo correcto: los tres tracks no comparten significado. El adaptador
  llama a cada uno y arma la tupla de salidas.
- **`rag.runtime.recommend`** no existe. P1 publica `decide(RuntimeInputs)`. El
  adaptador construye esas entradas desde el catálogo que la aplicación ya
  seleccionó.

Esa traducción vive entera en `apps/api/adapters/p1`. Los puertos, los servicios
y el store no cambiaron de forma para acomodarla.

---

## 4. El recorrido de un día

Once rutas de producto (`SPEC 11.1`) más tres de soporte. Este es el camino
completo, en el orden en que ocurre.

### 4.1 Abrir la sesión — `POST /api/v1/form-sessions`

El servidor fija **`audit_mode` al abrir y no lo recalcula jamás** (`INV-05`).
La asignación es un HMAC sobre tenant, sujeto, fecha local y versión de política:
estable entre recargas, imprevisible desde el cliente. Un 10% de las sesiones no
muestra sugerencias, para poder comparar respuestas con y sin ayuda.

Después construye el plan (`SPEC 6.9`), en este orden exacto: outcome pendiente,
preguntas vencidas por antigüedad, cuota de exploración, VoI disponible, orden
canónico para llenar cupos, y la cola completa.

**Todos los campos aplicables quedan accesibles.** Destacar es atención, no
acceso (`INV-10`).

En la corrida real, con la demo recién sembrada:

```text
plan_source: p1 | voi_status: unavailable_model | audit_mode: false
destacadas: sleep_quality, wake_state, gi_status,
            medication_adherence, daily_regulation_state   (todas por staleness)
cola:       sleep_hours, night_awakenings, morning_support_need, food_changes,
            routine_changes, alertness, dysregulation_event_count,
            activity_participation, social_interactions, eating_status,
            relevant_event_flag, behavior_tags, notes
```

Los cinco campos monitoreados salen destacados porque nunca se preguntaron: a
partir de los 7 días desde la última presentación un campo entra aunque amplíe
los cupos. `voi_nats` es `null`, nunca cero: sin modelo condicional no hay valor
de información, y cero sería una afirmación distinta (`INV-09`).

### 4.2 Responder — `POST /api/v1/form-sessions/{id}/answers`

El cliente declara una **interacción**; el servidor deriva el **modo de entrada**.
El cliente nunca envía `entry_mode`.

```text
interacción     manual | accept_default | edit_default | unknown
modo derivado   manual_no_default | audit_manual | default_accepted |
                default_edited | professional_observed | imported_observed |
                explicit_unknown
```

Tres reglas que se ven en la corrida:

- Responder a mano sobre un campo que tenía sugerencia vigente es
  `default_edited`, aunque el cliente diga `manual`. No se puede mentir sobre
  esto.
- Aceptar una sugerencia exige **declarar el valor aceptado**, y el servidor lo
  compara con el presentado antes de guardarlo. Si no coincide, la interacción
  declarada es falsa y falla.
- `unknown` persiste **sin valor**. No es un cero, no es un no, y no es lo mismo
  que dejar el campo vacío.

```text
sleep_quality=interrupted        -> entry_mode: manual_no_default
medication_adherence (unknown)   -> entry_mode: explicit_unknown, value NULL
```

Una sugerencia que nadie toca **no crea ninguna observación** (`INV-01`).

### 4.3 Cerrar — `POST /api/v1/form-sessions/{id}/submit`

Aquí está la decisión más delicada del sistema, y está serializada por
`(tenant_id, subject_id)` (`SPEC 4.2`):

```text
si no hay TargetDefinitionVersion seleccionable:
    cerrar con target_definition_unavailable
    NO crear episodio ni outcome request
si hay definición y no hay episodio primario abierto:
    crear PredictionEpisode(role=primary) y OutcomeRequest inmutable
si hay definición y hay episodio primario abierto:
    enlazar la sesión, no crear otra ventana
```

Es **fail-closed**: sin definición aprobada no se fabrica un objetivo. Con dos
definiciones vigentes tampoco, porque ninguna es "la" seleccionable.

```json
{
  "status": "episode_created",
  "prediction_episode_id": "a9394d30-…",
  "outcome_request_id": "504fea4f-…",
  "recommendation_instance_id": "c77c4ee5-…",
  "reasons": []
}
```

Sólo el primer estado crea snapshot, salidas, recomendación y solicitud de
outcome. El snapshot guarda los **IDs proyectados al cutoff**, no una copia de
los valores: una corrección posterior no altera lo que el episodio vio.

### 4.4 Ver las estimaciones — `GET /api/v1/prediction-episodes/{id}`

Tres tracks que nunca se prestan significado (`SPEC 8.1`):

| Track | Qué mide | Uso previsto |
|---|---|---|
| `synthetic_reference_v021` | score de simulación diseñada | `simulation_only` |
| `real_personal_baseline_v1` | tasa observada de la propia persona | `operational_support` |
| `real_logit_challenger_v1` | score en sombra | `shadow_evaluation` |

El tercero **nunca se expone**. No aparece en la respuesta, y el modelo del
contrato lo rechaza si alguien lo intenta.

Salida real con la demo sembrada:

```text
real_personal_baseline_v1   abstained    razones: insufficient_verified_outcomes,
                                                  collecting_data
synthetic_reference_v021    unavailable  razones: model_artifact_unavailable
challenger expuesto: False
decision_policy_version: null | risk_band: null
```

Las dos abstenciones son la respuesta correcta, no una falla. El baseline necesita
cinco resultados verificados de esta persona y no los hay. El track sintético
necesita el binario v0.2, que no está en Git a propósito, y lo dice en vez de
devolver un número.

**No hay bandas de riesgo.** Sin política de decisión validada, verde, ámbar y
rojo no existen (`SPEC 8.6`).

### 4.5 Recomendación — `GET .../recommendations`

El runtime es determinista y puro: **cero llamadas a un LLM** (`C29`). Recibe el
escenario mínimo y el catálogo activo que la aplicación ya seleccionó, evalúa el
predicado del set y de cada estrategia por separado y fail-closed, y devuelve
como máximo tres estrategias ya revisadas con las citas de sus versiones exactas.

El escenario mínimo (`SPEC 9.7`) no lleva identidad, notas, IDs externos ni
historial:

```json
{
  "schema_version": "scenario-1",
  "field_values": { "gi_status": "constipation", "sleep_quality": "interrupted" },
  "context_tags": ["home"],
  "profile_tags": ["communication:visual_schedule", "sensory:auditory_hypersensitive"],
  "contraindication_tags": []
}
```

`medication_adherence` no aparece: se respondió `unknown`, y un `unknown` no
asigna valor, así que no entra al match.

El serializer aplica actor y grants **en el servidor**. Nunca se filtra sólo en
el frontend. Mientras todo esté pendiente, la familia ve:

```json
{ "status": "awaiting_professional_review", "items": [] }
```

### 4.6 Revisión profesional — `POST .../reviews`

El inbox lista las instancias con estrategias sin revisar, con el escenario para
poder juzgar aplicabilidad. Decisiones posibles: `approved`, `rejected`,
`human_plan_substituted`, `not_applicable`, `deferred`.

Los recursos con revisión usan `If-Match` (`SPEC 11.2`):

```text
sin If-Match                    -> HTTP 428
con la revisión vigente          -> HTTP 201
con una revisión obsoleta        -> HTTP 409
```

Una sustitución crea un **plan del equipo**, que reemplaza a la estrategia y
**no hereda sus citas** (`INV-29`). Sus roles de ejecución no pueden ser más
amplios que los de la estrategia sustituida.

Después de revisar, la familia ve:

```text
strategy   | approved     | citas: 1 | ejecutores: caregiver, professional
human_plan | (sustituida) | citas: 0 | ejecutores: caregiver
```

### 4.7 Ejecución — `POST .../executions`

Registra que alguien aplicó una estrategia o un plan. `SPEC 10.3` distingue una
aplicación tardía: se conserva, pero no se atribuye.

```json
{
  "status": "applied",
  "human_plan_version_id": "803af0c5-…",
  "exposure_eligible": true
}
```

`exposure_eligible` es falso si la aplicación llegó después del cierre de la
ventana, o antes de la revisión que la autorizó.

### 4.8 Resultado — `POST .../outcome-reports`

El cliente envía `value` y, sólo para `yes`, `occurred_at`. El servidor toma
actor, rol, tenant, instante y definición desde el contexto autorizado, y deriva
el `timing_status`.

**Ni `no` ni `unknown` cierran la ventana antes de tiempo** (`INV-14`):

```text
reporte: unknown | timing: early
resolución: pending | ever_conflicted: false
estado de la solicitud: open
```

Y una resolución que alguna vez estuvo en conflicto **nunca vuelve a
presentarse limpia**: `ever_conflicted` no vuelve a `false`.

---

## 5. Lo que el contrato no deja construir

Estas nueve reglas ya no dependen de que alguien se acuerde. Las hacen cumplir
los validadores de `packages/shared`, y cada una tiene un ejemplo inválido en
`packages/shared/examples/invalid/` que nombra la regla del SPEC que rompe.

| Regla | Quién la impide |
|---|---|
| Abstención con probabilidad, intervalo, banda o narrativa | `PredictionOutputView` |
| Simulación presentada como probabilidad clínica | `PredictionOutputView` |
| Cualquier exposición del challenger en sombra | `PredictionOutputView` |
| Un default dentro de una sesión auditada | `FormSessionResponse` |
| Un episodio sin definición de target seleccionable | `FormSubmitResponse` |
| Un `no` o `unknown` que cierra la ventana antes de tiempo | `OutcomeResolutionView` |
| Una resolución alguna vez en conflicto presentada limpia | `OutcomeResolutionView` |
| Un plan humano con citas del RAG | `HumanPlanItem` |
| Idempotencia por template de ruta en vez de path concreto | `IdempotencyScope` |

`tests/integration/test_adapter_sets.py` comprueba que se sostienen en los dos
conjuntos de adaptadores.

---

## 6. Los dos conjuntos, y qué cambia de verdad

Esta es la diferencia que más confunde, así que conviene verla lado a lado. Misma
demo, mismo sujeto, misma sesión:

| | `FARO_P1_ADAPTERS=real` | `mock` (por defecto) |
|---|---|---|
| `plan_source` | `p1` | `mock` |
| Sugerencia de default | ninguna | `food_changes=false`, media 0.8409, cota 0.7431, n=42 |
| Baseline personal | `abstained` | `abstained` |
| Track sintético | `unavailable` (`model_artifact_unavailable`) | `ok`, score 0.42 |
| Runtime de recomendación | `decide` sobre el catálogo real | evaluación fail-closed del predicado |

**El camino real no sugiere nada, y eso es correcto.** `SPEC 6.2` sólo deja que
una observación **real** informe una sugerencia. En la demo la cohorte es
`demo_fixture` y sus filas son sintéticas, así que el estimador no tiene nada
elegible que contar. El mock sugiere porque lee un fixture declarado, y lo dice
en su propio docstring.

Por eso `mock` no se borró: es el camino de `tests/p2`, donde una sugerencia de
fixture permite comprobar `INV-01` con datos que el estimador real —correctamente—
no produce.

---

## 7. Autorización

Cinco cuentas ficticias, cada una para probar un borde distinto:

| Token | Persona | Prueba |
|---|---|---|
| `demo-cuidadora-ana` | Ana Ríos | flujo del cuidador |
| `demo-profesional-a` | Pilar Soto | revisión acreditada |
| `demo-evaluador-a` | Evaluador Demo A | lectura de evaluación |
| `demo-profesional-sin-acreditacion` | — | 403 por acreditación vencida |
| `demo-cuidador-b` | — | 404 cross-tenant |

Comprobado en la corrida:

```text
cuidadora  -> GET /evaluation              403 role_not_allowed
cuidador B -> GET /prediction-episodes/…   404 not_found          (no 403: no revela existencia)
prof. sin acreditación -> GET inbox        403 accreditation_required
```

El cross-tenant devuelve **404, no 403**: un 403 confirmaría que el recurso
existe. Cada negativa queda en la auditoría, que es append-only y no contiene
payload clínico.

---

## 8. Cómo levantarlo

```bash
# 1. Sembrar la demo (datos completamente ficticios).
python -m tools.seed --catalog blocked          # estado honesto de release
python -m tools.seed --catalog fixture-active   # para recorrer el flujo profesional

# 2. API.
uvicorn "apps.api.main:create_app" --factory --host 127.0.0.1 --port 8000

#    Contra el dominio real de P1:
FARO_P1_ADAPTERS=real uvicorn "apps.api.main:create_app" --factory --port 8000

# 3. Frontend.
pnpm -C apps/web dev
```

La aplicación queda en `http://127.0.0.1:3000`, la API en `http://127.0.0.1:8000`
y su documentación OpenAPI en `/docs`, que se deshabilita sola en modo piloto.

`GET /health` dice contra qué está corriendo:

```json
{ "status": "ok", "spec_version": "0.3.0", "mode": "demo", "adapters": "p1" }
```

### Verificación completa

```bash
python -m tools.contracts.generate
python -m tools.contracts.examples
git diff --exit-code packages/shared/generated packages/shared/examples

ruff check . && ruff format --check .
lint-imports
pytest tests -q

pnpm -C apps/web typecheck && pnpm -C apps/web test && pnpm -C apps/web build

FARO_P1_ADAPTERS=real pytest tests/integration -q
```

El `git diff --exit-code` prueba que nadie editó a mano el contrato generado.
`lint-imports` prueba que las capas siguen en pie. La última línea prueba que el
camino real existe de verdad.

---

## 9. Estado real del release

Cuatro estados independientes, y ninguno implica al otro:

| Estado | Valor | Por qué |
|---|---|---|
| `implementation_status` | `p2_integrated_against_p1` | el producto corre sobre el dominio publicado |
| `corpus_status` | `fixture_only` | no hay corpus legalmente utilizable |
| `target_definition_status` | `demo_fixture_only` | no hay target real aprobado |
| `catalog_status` | `blocked_clinical_review` | no hay revisor clínico autorizado |

Que la implementación esté integrada **no significa que la demo produzca
estimaciones clínicas**. Con datos sintéticos el dominio real se abstiene en
todo, y decirlo es parte del estado honesto.

---

## 10. Lo que falta

Quince divergencias abiertas con P1, `R1` a `R15`, cada una con ruta, request,
response, razón y test consumidor en la sección "Solicitudes a P1" del
`README.md`. Todas son campos que el contrato publicado todavía no lleva y que el
producto necesita: el bloque de outcome pendiente, el escenario del inbox, los
roles de un item, la respuesta de `POST /answers`, la corrección append-only de
una observación, el token de concurrencia para `If-Match`.

Cada una está declarada **en un solo lugar**: como subclase del modelo de P1, en
`apps/api/contracts/models.py` y en `apps/web/lib/contracts.ts`. Nada del
contrato se redeclara; lo único declarado es el campo que falta. Cuando P1
publique el campo, se borra la subclase y no se toca nada más.

Tres cosas que el repositorio no contiene a propósito, y que no son deuda sino
decisiones:

- El binario de simulación v0.2 (`.gitignore`). Por eso el track sintético
  responde `unavailable` en un clon nuevo.
- El corpus clínico y sus índices. Sólo entran los manifests y los hashes.
- El catálogo cerrado de `behavior_tags`. `SPEC 5.2` lo declara versionado pero
  no lo enumera, y `SPEC 19` dice que una decisión ausente se registra como
  pregunta, no se inventa. La interfaz lo dice en vez de ofrecer categorías.
