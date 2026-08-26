# Qué se puede podar de Faro sin tocar el núcleo

Análisis del repositorio en `develop` (`f52c66b`, v0.3.0) contra cuatro
capacidades que se declaran núcleo:

1. **Modelo predictorio** — el doble track de `GET /prediction-episodes/{id}`.
2. **RAG** — el runtime determinista de recomendación.
3. **Mejora del RAG con feedback del terapeuta** — revisión profesional,
   sustitución por plan humano, y la solicitud de autoría que abre una
   abstención.
4. **Formulario inteligente** — plan adaptativo, VoI, defaults sugeridos y
   modos de entrada derivados.

Todo lo demás es candidato. El documento va de lo que se borra sin pensar a lo
que parece borrable y no lo es.

Un aviso antes de empezar: **la autenticación no es el mejor primer corte.** Es
el ejemplo que motivó este análisis, y la sección 3 explica por qué es un
refactor de ~25 sitios y no un `rm -rf`, mientras que las secciones 1 y 2
liberan más superficie con riesgo mucho menor.

---

## 0. El mapa de lo que no se toca

Antes de borrar conviene saber exactamente qué archivos sostienen las cuatro
capacidades. Esta es la lista completa; cualquier cosa fuera de ella es, en
principio, negociable.

| Capacidad | Dominio | Cableado en la app |
|---|---|---|
| Modelo predictorio | `ml/prediction/**` (baseline, challenger, landmarks, synthetic_reference), `ml/spec_constants.py`, `ml/errors.py` | `apps/api/ports/prediction.py`, `apps/api/adapters/p1/prediction.py`, `apps/api/services/episodes.py`, `apps/api/store/episodes.py` |
| RAG (runtime) | `rag/runtime/decide.py`, `rag/domain/**` | `apps/api/ports/rag.py`, `apps/api/adapters/p1/rag.py`, `apps/api/services/recommendations.py`, `apps/api/store/recommendations.py`, `apps/api/store/catalog.py` |
| Feedback del terapeuta → RAG | `rag/domain/reviews.py`, `rag/domain/activation.py`, `rag/authoring/**` | `POST /recommendation-instances/{id}/reviews`, `POST .../executions`, `GET /recommendation-instances`, tabla `authoring_requests`, `tools/rag_authoring/` |
| Formulario inteligente | `ml/form/plan.py`, `ml/form/quality.py`, `ml/form/scenario.py`, `ml/form/voi.py`, `ml/defaults/**` | `apps/api/ports/{form,defaults}.py`, `apps/api/adapters/p1/{form,defaults}.py`, `apps/api/services/{form_sessions,form_plan,entry_mode}.py`, `apps/api/store/{form_sessions,history,projection}.py` |

Transversal e intocable en los cuatro casos: `packages/shared/**` (el contrato),
`apps/api/store/db.py`, `apps/api/store/migrations/**`, `apps/api/canonical.py`,
`apps/api/clock.py`, `apps/api/errors.py`, `apps/api/main.py`,
`tools/contracts/{generate,examples}.py` y `tools/seed/**`.

---

## 1. Nivel 0 — borrado libre, riesgo cero

Nada de esto está referenciado por código. Se puede borrar hoy y la suite pasa
igual.

### 1.1 Cinco directorios de `ml/` que están vacíos

```
ml/voi/  ml/strategies/  ml/narrative/  ml/features/  ml/engine/
```

No contienen un solo `.py`: solo `__pycache__` sobreviviente de la v0.2. Git no
rastrea ninguno de sus archivos. Son fantasmas de un layout anterior.

> Ojo con uno de ellos: `.importlinter` nombra `ml.engine`, `ml.features` y
> `ml.voi` en el contrato `store-does-not-compute`. Prohibir un módulo
> inexistente no falla, pero conviene limpiar esas tres líneas en el mismo
> commit para que la regla siga diciendo la verdad.

### 1.2 `fixtures/` en la raíz — 6 archivos, 52 KB

```
fixtures/abstention_child.json   fixtures/child_abstain.json
fixtures/calm_child.json         fixtures/child_calm.json
fixtures/high_risk_child.json    fixtures/child_high_risk.json
```

Están rastreados por Git y **ninguno se menciona en una sola línea de código**.
Las únicas referencias en todo el repo son al directorio, en prosa:
`CONVENTIONS.md:87` (un árbol de layout) y `TAREAS.md:98`, que además ya los
declara legado: *"`fixtures/**` raíz | Solo lectura; nuevos fixtures viven con
su dueño"*.

Y son duplicados renombrados entre sí, con contenidos distintos, lo que es peor
que tenerlos o no tenerlos:

| Par | Archivo A | Archivo B |
|---|---|---|
| abstención | `abstention_child.json` (2 filas) | `child_abstain.json` (2 filas, otro hash) |
| calma | `calm_child.json` (5 filas) | `child_calm.json` (14 filas) |
| riesgo alto | `high_risk_child.json` (5 filas) | `child_high_risk.json` (10 filas) |

Los fixtures vivos son `tests/p1/factories.py`, `tests/p1/rag_factories.py`,
`tests/integration/fixtures/*.json` y `apps/api/adapters/mock/fixtures/`.

### 1.3 Cachés y artefactos regenerables (no rastreados)

```
__pycache__/  .ruff_cache/  .pytest_cache/  .import_linter_cache/   ~272 KB
apps/web/.next/                                                      120 MB
node_modules/                                                        450 MB
.venv/                                                               480 MB
```

Todos están en `.gitignore`. No aportan nada al repositorio y los `__pycache__`
de `ml/voi`, `ml/engine`, etc. son justamente lo que hace parecer que esos
directorios existen.

**Total nivel 0: 6 archivos rastreados, 5 directorios fantasma, ~1 GB en disco.**

---

## 2. Nivel 1 — borrado real, con tests que hay que retirar

Aquí sí se borra código vivo. Cada bloque dice exactamente qué test se cae, para
que el borrado sea un commit completo y no una suite roja.

### 2.1 El adaptador Bluba y su manifiesto de evidencia — ~710 líneas

| Archivo | Líneas |
|---|---|
| `ml/adapters/bluba.py` + `__init__.py` | 190 |
| `tools/contracts/source_evidence.py` | 365 |
| `tests/p1/test_m0_evidence_manifests.py` | 156 |
| `data/source-evidence.manifest.json` | (manifiesto) |

`ml/adapters/bluba.py` traduce el vocabulario del export de Bluba a valores
canónicos. **La API no lo importa nunca.** Sus únicos consumidores son
`tests/p1/test_prediction.py` y `tests/p1/test_invariants_p1.py:557` (INV-35).
El export que mapea no está en Git y sus derechos están sin declarar, así que el
módulo no tiene entrada de datos real.

Cuidado con una confusión frecuente: el `entry_mode` `imported_observed` **no
depende de este módulo**. Lo deriva `apps/api/services/entry_mode.py` desde la
tabla `source_mappings`. El formulario inteligente sigue intacto.

Al borrar hay que quitar también el import y el test `test_inv_35_*` de
`tests/p1/test_invariants_p1.py`, y el bloque de imports de Bluba al inicio de
`tests/p1/test_prediction.py` (el resto del archivo es predicción pura y se
queda).

**Si en algún momento se piensa ingerir el export real de Bluba, este es el
único archivo del repo que sabe hacerlo. Conservarlo cuesta 190 líneas
aisladas.** Es la decisión de producto, no técnica, de este bloque.

### 2.2 `ml/form/anomaly.py` — 255 líneas

Exportado por `ml/form/__init__.py`, consumido **solo** por
`tests/p1/test_form.py`. Ni el plan del formulario, ni los defaults, ni el
adaptador P1, ni ninguna ruta llaman a `detect_form_anomaly`,
`compute_categorical_surprise` ni `compute_robust_deviation`.

Es detección de anomalías construida y nunca cableada. Borrar el módulo, sus 3
entradas en `__all__` y su bloque de tests.

### 2.3 El aparato de entrenamiento y evaluación offline — ~2.970 líneas

**Este es el corte grande, y es condicional.** Léase la advertencia antes del
comando.

| Bloque | Líneas |
|---|---|
| `ml/eval/**` (bootstrap, metrics, protocol, report) | 907 |
| `tools/train/**` (cli, consent, evaluate, run, snapshot) | 926 |
| `tests/p1/test_eval.py` + `test_train.py` + `train_factories.py` | 1.135 |

**Qué NO se rompe:** el modelo predictorio en línea. `ml/prediction/**` es
independiente de `ml/eval`; el adaptador P1 llama a `score_simulation` y
`build_personal_baseline` directamente. `GET /prediction-episodes/{id}` no toca
una sola línea de `ml/eval` ni de `tools/train`.

**Qué sí se pierde:** la capacidad de reentrenar el challenger y de producir un
reporte de evaluación nuevo. El repositorio pasa a servir el modelo, no a
generarlo.

Si el proyecto se queda con el baseline personal (que es estadística cerrada,
`Beta(1+e, 1+n−e)`, y no necesita entrenamiento) y con el track sintético
congelado, esto se va entero. Si se planea reentrenar, se queda.

Una advertencia menor: `tools/contracts/examples.py` importa de
`ml.prediction.challenger`, no de `ml.eval`, así que la generación de ejemplos
del contrato sobrevive al corte.

### 2.4 La superficie de reporte de evaluación — ~490 líneas

Va con la anterior o por separado; es la mitad de lectura de lo mismo.

| Archivo | Líneas |
|---|---|
| `apps/api/services/evaluation.py` | 115 |
| `apps/api/store/evaluation.py` | 30 |
| `apps/web/app/evaluacion/page.tsx` | 167 |
| `tests/p2/test_evaluation.py` | 100 |
| ruta `GET /evaluation/{model_version}` en `routes/v1.py` | ~10 |

Es una ruta de lectura que sirve reportes ya persistidos por `tools/train`. No
participa en ninguna de las cuatro capacidades núcleo. Al retirarla se cae
también el rol `model_evaluator` y su cuenta demo `demo-evaluador-a`, y hay que
quitar la tarjeta "Evaluación" de `apps/web/app/page.tsx`.

Las tablas `evaluation_reports`, `model_versions`, `dataset_snapshots` y
`training_runs` (migración `004`) se pueden dejar en el esquema sin costo, o
retirar con una migración `006`. Ver sección 4.6 antes de tocar migraciones.

**Total nivel 1: ~4.400 líneas, con 5 archivos de test retirados enteros.**

---

## 3. Nivel 2 — la autenticación: qué se va de verdad y qué no

El planteo era "la autenticación no la necesitamos". Es cierto a medias, y la
mitad que no es cierta importa.

### 3.1 Lo que sí es autenticación, y sí sobra

`apps/api/auth/demo.py` (55 líneas) es un `Bearer <token>` que busca una fila en
`users`. Es ficticio por diseño (`SPEC 12.3`) y el modo piloto lo rechaza. Junto
con `apps/web/lib/session.ts` (51 líneas) y el selector de cuenta en
`AppShell.tsx`, esto es **~130 líneas** que se reemplazan por un actor fijo.

Ese corte es barato y sin consecuencias.

### 3.2 Lo que la gente llama "autenticación" y en realidad es autorización

`apps/api/auth/authorization.py` son 290 líneas, pero el costo no está ahí: está
en **25 sitios de llamada** repartidos así:

| Archivo | Llamadas |
|---|---|
| `apps/api/services/form_sessions.py` | 6 |
| `apps/api/services/recommendations.py` | 6 |
| `apps/api/services/outcomes.py` | 3 |
| `apps/api/services/episodes.py` | 1 |
| `apps/api/services/evaluation.py` | 1 |
| `apps/api/routes/v1.py` | 1 |
| interno de `authorization.py` | 7 |

Más 5 tablas (`users`, `user_roles`, `professional_accreditations`,
`subject_access_grants`, `consents`), su siembra en `tools/seed/seeder.py`, y
`tests/p2/test_authorization.py`.

Y hay tres acoplamientos que hacen que borrar esto **no sea neutral para el
núcleo**:

**a) La revisión del terapeuta está construida sobre la acreditación.**
`services/recommendations.py:221-230` exige `Role.PROFESSIONAL` **y** una
acreditación vigente con capability `subject_care` antes de abrir el inbox.
`rag/domain/reviews.py` va más lejos: una revisión de autoría solo es usable si
la acreditación otorgaba la capability exacta en el instante `reviewed_at`.
Borrar el concepto de acreditación no simplifica el sistema de feedback: le
quita la noción de *quién está autorizado a dar feedback*, que es de lo que
trata el sistema.

**b) El consentimiento entra en el modelo predictorio.**
`apps/api/adapters/p1/prediction.py:146-165` lee los sujetos con consentimiento
`operational_support` activo y pasa `consent_authorized` a cada
`BaselineCandidate`. En `ml/prediction/baseline.py:124` ese flag decide si el
candidato cuenta. **Si se borra la tabla `consents` sin más, el baseline personal
deja de acumular evidencia y se abstiene siempre** — silenciosamente, sin error.
Si se retira, hay que fijar `consent_authorized=True` de forma explícita.

**c) `authorize_subject` es lo único que resuelve el sujeto.**
Además de negar, devuelve `subject_id`, `tenant_id`, `cohort_kind` y
`display_label`, y esos valores se usan aguas abajo. Y `granted_subject_ids`
produce el filtro SQL de dos listas (`GET /session`, `GET /recommendation-instances`).
Sin sustituto, esas dos rutas se quedan sin criterio de selección.

### 3.3 El corte recomendado: aplanar, no borrar

Si el objetivo es dejar de mantener autenticación real sin desarmar el dominio:

1. **Sustituir `demo.py` por un actor fijo.** `current_actor` en
   `routes/dependencies.py` devuelve un `ActorContext` constante con ambos roles
   y el tenant de la demo. Borrar `demo.py`, `session.ts` y el selector de
   cuenta. *(−130 líneas, 0 sitios rotos)*

2. **Convertir `AuthorizationService` en permisivo, sin cambiar su firma.**
   `authorize_subject` deja de negar y sigue devolviendo el
   `SubjectAuthorization` con los datos del sujeto; `granted_subject_ids` pasa a
   `SELECT subject_id FROM subjects WHERE tenant_id = ?`;
   `active_accreditation` devuelve un ID fijo; `active_consents` devuelve la
   lista real o una constante — pero **nunca vacía**, por el punto (b).
   *(−~200 líneas dentro del archivo, 0 sitios de llamada tocados)*

3. **Retirar `tests/p2/test_authorization.py`** (104 líneas) y las aserciones de
   403/404 en `tests/integration/*`.

4. **Dejar las 5 tablas en el esquema.** Sembradas con una fila cada una, no
   cuestan nada y evitan una migración destructiva.

Esto elimina ~450 líneas y toda la carga mental de la autorización, sin tocar un
solo `services/*.py` y sin cambiar el comportamiento del predictor.

**El borrado total** (quitar `ActorContext` de las firmas, las 5 tablas, la
auditoría) son ~1.100 líneas menos pero toca los 6 servicios, el store, las
migraciones y 4 archivos de test. Es un día de trabajo con riesgo real de
regresión silenciosa en el baseline. Solo vale la pena si el proyecto pasa a ser
mono-usuario de forma definitiva.

### 3.4 La auditoría, de paso

`apps/api/store/audit.py` (46 líneas) tiene 10 sitios de llamada, la mitad en
caminos de denegación que desaparecen con el paso 2. Si se aplana la
autorización, la auditoría queda registrando casi solo `allowed`. Se puede
convertir `audit.record` en un no-op de una línea y dejar los sitios de llamada
donde están: cuesta menos que borrarlos y es reversible.

---

## 4. Nivel 3 — parece borrable y no lo es

Seis trampas. Vale la pena leerlas antes de abrir el editor.

### 4.1 `apps/api/adapters/mock/**` (487 líneas)

Parece código de demo muerto. **Es el camino por defecto de `tests/p2`.** Y hay
una razón concreta que `COMO-FUNCIONA.md §6` documenta: el estimador real
correctamente no sugiere nada sobre la cohorte `demo_fixture` (las filas son
sintéticas y `SPEC 6.2` solo deja que una observación real informe una
sugerencia), así que **`INV-01` solo se puede comprobar contra el mock**.
Borrarlo deja el invariante del formulario inteligente sin test.

### 4.2 `packages/shared/examples/invalid/**` (17 archivos)

Parecen datos de prueba. Son los guardianes de las nueve reglas que el contrato
no deja construir: challenger expuesto, abstención con probabilidad, default en
sesión auditada, plan humano con citas del RAG, idempotencia por template. Cada
uno nombra la regla del SPEC que rompe y `tools/contracts/examples.py` los
valida contra el JSON Schema generado.

### 4.3 `packages/shared/generated/**` (8 archivos)

Es código generado, pero `apps/web/lib/contracts.ts` lo consume y el gate de
verificación es `git diff --exit-code packages/shared/generated`. Regenerarlo es
`python -m tools.contracts.generate`; borrarlo rompe el frontend y el gate.

### 4.4 `apps/api/contracts/**` (768 líneas)

Parece una duplicación del contrato. **No declara ningún modelo**: son
re-exports de `packages/shared`, más las subclases de las 15 divergencias
abiertas con P1 (`R1`–`R15`) en `models.py`, que sí son código propio y necesario
—el bloque de outcome pendiente, el escenario del inbox, los roles de un item—.
Colapsar esto fue el trabajo de dos commits recientes (`dff054d`, `6eb5cd0`); no
hay nada que ganar.

### 4.5 `rag/authoring/**` + `tools/rag_authoring/` (~1.100 líneas)

Es offline y el runtime tiene prohibido importarlo por contrato
(`runtime-has-no-model-index-or-network`). Pero es **la otra mitad del sistema de
mejora del RAG**: cuando el runtime se abstiene crea un `authoring_request`
(`services/form_sessions.py:662`), y quien lo atiende es este pipeline — BM25,
RRF, el borrador con LLM local y el manifiesto reproducible. Sin él, el feedback
del terapeuta entra al sistema y no sale a ninguna parte.

`rag/authoring/drafting.py` es además el único punto del repositorio donde se
permite un modelo de lenguaje, y su prompt versionado
(`prompts/authoring_draft.v0_3_0.json`) entra por hash en el manifiesto de build.

### 4.6 Las migraciones

`apps/api/store/migrations/**` es acumulativo y `tests/p2/test_migrations.py`
afirma la lista exacta de tablas. **No se edita una migración ya aplicada.** Si
se retira una tabla, se hace con una migración nueva (`006_*.sql`) y se
actualiza la lista del test. En la práctica, para todo lo que este documento
propone, dejar las tablas huérfanas en el esquema es más barato y más seguro que
retirarlas.

---

## 5. Orden de ejecución

Cada paso termina en verde antes de empezar el siguiente. El gate completo es:

```bash
python -m tools.contracts.generate && python -m tools.contracts.examples
git diff --exit-code packages/shared/generated packages/shared/examples
ruff check . && ruff format --check . && lint-imports
pytest tests -q
pnpm -C apps/web typecheck && pnpm -C apps/web test && pnpm -C apps/web build
FARO_P1_ADAPTERS=real pytest tests/integration -q
```

**Paso 1 — nivel 0.** Borrar los 5 directorios fantasma de `ml/`, `fixtures/` de
la raíz y las cachés. Limpiar las 3 líneas muertas de `.importlinter` y la rama
`fixtures/` del árbol en `CONVENTIONS.md:87`. Gate completo.

**Paso 2 — anomalías del formulario.** `ml/form/anomaly.py`, sus exports y su
bloque en `tests/p1/test_form.py`. Gate completo.

**Paso 3 — Bluba.** `ml/adapters/`, `tools/contracts/source_evidence.py`,
`data/source-evidence.manifest.json`, `tests/p1/test_m0_evidence_manifests.py`,
y los dos consumidores de test. Decidir antes si el export real está en el
horizonte. Gate completo.

**Paso 4 — decisión sobre entrenamiento.** Si el modelo se congela: borrar
`ml/eval/`, `tools/train/` y sus 3 archivos de test, y luego la superficie de
reporte (§2.4) con la ruta, el servicio, el store, la página web y su test. Gate
completo, prestando atención a que `GET /prediction-episodes/{id}` siga
respondiendo igual.

**Paso 5 — aplanar la autorización.** Los cuatro sub-pasos de §3.3, en ese
orden, con gate entre el 1 y el 2. Verificar explícitamente el baseline personal
después del paso 2 (el fallo de `consent_authorized` no da error, solo abstiene).

---

## 6. Resumen

| Nivel | Qué | Líneas | Riesgo |
|---|---|---|---|
| 0 | 5 dirs fantasma de `ml/`, `fixtures/` raíz, cachés | 6 archivos + ~1 GB | ninguno |
| 1 | `ml/form/anomaly.py` | 255 | bajo |
| 1 | Bluba + manifiesto de evidencia | ~710 | bajo (decisión de producto) |
| 1 | `ml/eval` + `tools/train` | ~2.970 | medio: congela el modelo |
| 1 | superficie de reporte de evaluación | ~490 | bajo |
| 2 | autenticación demo + frontend de sesión | ~130 | ninguno |
| 2 | autorización aplanada (no borrada) | ~320 | medio: vigilar `consent_authorized` |
| — | **Total realista** | **~4.900 líneas** | |
| 3 | mock adapters, examples/invalid, generated, contracts, rag/authoring, migraciones | — | **no borrar** |

Las cuatro capacidades núcleo salen intactas de los tres niveles. Lo que se pierde
en el camino es la ingesta de Bluba, el reentrenamiento del challenger, el reporte
de evaluación y el multi-tenant — cuatro cosas que el proyecto puede no necesitar,
pero que conviene perder a propósito y no por sorpresa.
