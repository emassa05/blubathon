# FARO - Plan de implementación para dos personas v4.0

## SPEC v0.3.0, propiedad exclusiva y handoffs por contrato

Este documento convierte `SPEC.md` en trabajo ejecutable para exactamente dos personas. No cambia
el alcance ni decide fórmulas nuevas.

"Dos personas" significa dos implementadores con propiedad exclusiva de archivos. Un eventual
`clinical_reviewer` aporta una aprobación externa de gobernanza, no implementa ni edita el
repositorio y no se contabiliza como capacidad del equipo.

---

## 1. Objetivo

Entregar una demo local v0.3 que demuestre:

- Formulario adaptativo con sugerencias seguras y auditoría.
- Episodios de predicción con ventana de 24 horas.
- Outcomes capturables hasta 48 horas sin inventar negativos.
- Separación visible entre simulación, baseline real y challenger en sombra.
- RAG offline con catálogo versionado, citas y revisión humana.
- Revisión, ejecución y outcome como eventos distintos.
- Frontend de cuidador y profesional.
- Persistencia append-only, idempotencia y auditoría.

La demo no es un piloto clínico. `SPEC 13` define qué exige un piloto posterior.

---

## 2. Regla de propiedad

Cada path tiene un único dueño durante toda la implementación.

### P1 - Contrato, estadística y evidencia

Pregunta que responde:

> ¿Qué significa cada dato y cómo se calcula una salida verificable?

Propiedad exclusiva:

```text
packages/shared/**
ml/**
rag/**
tools/train/**
tools/rag_authoring/**
tools/contracts/**
tests/p1/**
data/manifest.json
data/*.manifest.json
pyproject.toml
.importlinter
.gitignore
```

### P2 - Producto, persistencia y experiencia

Pregunta que responde:

> ¿Cómo captura, guarda, muestra y audita el producto esas decisiones?

Propiedad exclusiva:

```text
apps/api/**
apps/web/**
tools/seed/**
tests/p2/**
tests/integration/**
README.md
.github/**
package.json
pnpm-lock.yaml
```

### Zonas congeladas

```text
SPEC.md
CONVENTIONS.md
TAREAS.md
FUNDAMENTOS.md
```

No se editan durante los hitos. Si aparece una contradicción, se detiene solo la tarea afectada y
las dos personas acuerdan una versión documental nueva antes de continuar.

### Legado

| Zona actual | Responsable de migrarla o retirarla |
|---|---|
| `tests/unit/**` | P2 |
| `tests/invariants/**` | P2 solo retira o pone en cuarentena el legado; cada dueño crea reemplazos en su zona |
| `tests/conftest.py` | P2, se elimina como fixture global |
| `tests/p1/**` existente | P1 |
| `fixtures/**` raíz | Solo lectura; nuevos fixtures viven con su dueño |
| `data/**` no manifest | P2 audita y limpia/quarantina para release; P1 puede generar artefactos ignorados |
| `SPEC.v0.2.0.bak.md` | Histórico, nadie lo edita |
| `Untitled document.md` | Histórico, nadie lo edita |

Después del saneamiento inicial no vuelve a crearse una ruta de tests compartida.
Si P2 necesita una dependencia Python raíz, solicita paquete, versión, licencia, motivo y test a P1;
P2 controla directamente las dependencias frontend de su zona.

---

## 3. Cómo colaborar sin tocar archivos ajenos

### 3.1 Handoff P1 -> P2

P1 publica de forma atómica:

```text
modelo Pydantic
JSON Schema
tipos TypeScript/Zod generados
ejemplo JSON válido
ejemplo JSON inválido
test del contrato
versión/hash del contrato
```

P2 consume esos artefactos sin copiarlos ni editarlos.

### 3.2 Solicitud P2 -> P1

Una solicitud contractual contiene:

1. Ruta y operación.
2. Request JSON literal.
3. Response JSON literal.
4. Razón del cambio.
5. Test consumidor que falla.

P1 responde editando únicamente su zona. P2 no aplica parches en `packages/shared`.

### 3.3 Revisión

- El revisor comenta; el dueño edita.
- Un PR o cambio contiene paths de un solo dueño.
- Las migraciones publicadas no se reescriben.
- Los contratos generados cambian junto con su fuente.
- Los fixtures no cruzan carpetas de dueño.

### 3.4 Datos de integración

- P1 crea ejemplos contractuales en `packages/shared/examples`.
- P1 crea fixtures algorítmicos en `tests/p1/fixtures`.
- P2 crea fixtures de API/DB en `tests/p2/fixtures`.
- P2 crea journeys ficticios en `tests/integration/fixtures`.
- Nadie usa exports reales en tests versionados.

---

## 4. Dependencias y ruta crítica

```text
M0 decisiones externas
  -> M1 contrato ejecutable
     -> M2 dominio y persistencia en paralelo
        -> M3 flujo cuidador
        -> M4 RAG y flujo profesional
           -> M5 volante y evaluación
              -> M6 integración y release
```

P2 no espera a que P1 termine algoritmos: después de M1 trabaja contra servicios falsos y ejemplos
publicados.

---

## 5. M0 - Prerrequisitos externos

**Objetivo:** no fingir evidencia, licencia o revisión que el equipo no posee.

### P1

1. Inventariar fuentes candidatas con URL, versión y derechos.
2. Registrar modelos candidatos de embeddings/LLM con licencia y model card.
3. Crear `data/source-evidence.manifest.json`, no identificable, con hashes, schemas y conteos; P1
   actualiza la allowlist de `.gitignore` sin exponer los CSV.
4. Preparar la lista de dependencias Python necesaria.
5. Confirmar que las decisiones numéricas compartidas existan en `SPEC 15` y los parámetros de
   build queden en manifests versionados.

### P2

1. Identificar quién puede recibir el rol `clinical_reviewer`.
2. Registrar política de acreditación del rol para la demo.
3. Obtener o declarar bloqueada una `TargetDefinitionVersion` con pregunta, anclas y reporters
   aprobados para captura real.
4. Definir quién puede actuar como `privacy_reviewer` y qué base permite exportar consultas
   generalizadas a autoría.
5. Preparar identidades, acreditaciones y grants ficticios para roles, tenants y sujetos.
6. Definir dominio local y origen web/API de la demo.

### Bloqueo clínico

Un desarrollador no se autodesigna revisor clínico. Si no existe una persona autorizada:

- Se implementa todo el flujo.
- Las estrategias permanecen `evidence_reviewed` o `draft`.
- Runtime responde `clinical_review_unavailable`.
- La demo muestra correctamente la abstención.
- No se afirma que existe un catálogo clínicamente activo.

### Listo cuando

- Existe al menos una fuente legalmente utilizable para probar autoría.
- Modelos locales candidatos tienen licencia documentada.
- Roles ficticios están definidos.
- El estado del revisor clínico está declarado como disponible o bloqueado.
- El target real está `active` o explícitamente `blocked`; fixtures demo no se hacen pasar por labels
  reales.
- Nadie necesita inventar una cita o aprobación para avanzar.
- Ambos implementadores acuerdan el freeze inicial de SPEC 0.3.0; desde ese punto aplica semver y
  las cuatro zonas documentales quedan congeladas.

M0 puede declarar cada dependencia `available` o `blocked`. Un bloqueo de corpus detiene P1.6 y el
DoD completo; un bloqueo clínico impide activar catálogo; un target bloqueado impide labels reales.
Ninguno impide construir contratos con fixtures ni demostrar abstención segura.

---

## 6. M1 - Contrato ejecutable

**Dependencia:** M0 documental.

### P1.1 - Romper la dependencia shared -> ml

Construir:

```text
packages/shared/constants.py
packages/shared/field_catalog.py
packages/shared/models.py
packages/shared/texts.py
packages/shared/schema/**
packages/shared/generated/**
packages/shared/examples/**
```

Debe incluir:

- 19 campos diarios y matriz de fuentes.
- `entry_mode`, interacción y origen.
- Sesiones con `opened_at`, defaults, `QuestionPresentation` y episodios primarios no solapados con
  `as_of_at = prediction_at = submitted_at`.
- Snapshots y outputs por track, sin un campo ambiguo `confidence`.
- `TargetDefinitionVersion` con scope/selección única, target demo separado, reportes con canal y
  mapping, resoluciones append-only, adjudicación y elegibilidad temporal.
- Proyección append-only, bytes canónicos, hashes y ventanas locales.
- Consent por purpose, grants con capabilities/matriz, acreditaciones, authoring authorizations y
  origen/cohorte/deployment sin nombres ambiguos.
- Escenarios, strategies con texto/claims, citas, sets, catálogos e intents de autoría.
- Reviews por estrategia, planes humanos y executions cronológicas.
- Evaluación estructurada.
- Errores con request ID.
- `ConstantSpec` C01-C50.

Generar TypeScript/Zod desde una única fuente. No mantener dos contratos manuales.

### P1.2 - Ejemplos de handoff

Ejemplos mínimos:

```text
form_session.audit.json
form_session.with_default.json
form_answer.manual.json
form_answer.accept_default.json
form_answer.edit_default.json
prediction.synthetic_score.json
prediction.personal_abstained.json
recommendation.match.json
recommendation.abstained.json
outcome.yes.json
outcome.no.json
outcome.explicit_unknown_pending.json
outcome.early_no_pending.json
outcome.conflicted.json
outcome.late.json
error.idempotency_conflict.json
error.cross_tenant.json
```

### P2.1 - Scaffold consumidor

Sin editar contratos:

- Crear app FastAPI v0.3 con las 11 rutas y servicios falsos.
- Crear `apps/web` con TypeScript strict.
- Consumir tipos generados por P1.
- Crear cliente API tipado.
- Renderizar ejemplos contractuales en páginas de desarrollo.
- Preparar runner vacío de migraciones.

### Criterios de terminado

- `packages/shared` no importa `ml`, `rag` ni `apps`.
- Todos los ejemplos validan o fallan según su intención.
- JSON Schema y TS/Zod se regeneran sin diff inesperado.
- OpenAPI usa los modelos compartidos.
- Frontend compila sin tipos duplicados.
- P2 puede continuar con mocks aunque P1 todavía no tenga algoritmos.

### Handoff H1

```text
contract_version
schema_hash
commit/reference local
lista de ejemplos
comando de generación
```

---

## 7. M2 - Núcleo y persistencia en paralelo

**Dependencia:** H1.

## P1 - Dominio puro

### P1.3 - Smart defaults

Crear `ml/defaults` con APIs puras:

```python
compute_binary_default(...)
compute_categorical_default(...)
compute_default_decision(...)
assign_audit_mode(...)
```

Implementar:

- Beta para binarias.
- Dirichlet y marginal Beta para categorías.
- Ventana limpia de 60 días.
- Estratificación por tenant, sujeto, fuente y campo.
- Proyección append-only al cutoff y ventanas locales exactas.
- Empate sin sugerencia.
- Corte estricto `lower > 0.70`.
- Allowlist y prohibiciones.
- Exclusión de defaults aceptados/editados.
- Auditoría HMAC estable al 10%.
- Vectores golden, incluida la tabla corregida de `FUNDAMENTOS.md`.

No implementar defaults para continuos, conteos, texto, tags u outcomes.

### P1.4 - DQI y formulario

Crear `ml/form` y actualizar features puras:

```python
compute_dqi(...)
compute_predictive_voi(...)
build_form_plan(...)
detect_form_anomaly(...)
```

Implementar exactamente:

- Coverage de 5 campos por 14 días.
- Recencia con vida media de 2 días.
- Consistencia por tipo de campo.
- Resultado multiplicativo.
- Orden outcome, staleness, exploración, VoI, cola.
- `QuestionPresentation`, prioridad exacta, expansión por vencidos y weekday HMAC de exploración.
- VoI en nats o estado unavailable.
- `q_j` Beta/Dirichlet versionado y consultas condicionales no causales.
- `robust_z` completo con casos sin soporte.
- Todos los campos aplicables en highlighted+tail.
- Filtro que no crea valores en cola.
- `build_scenario` puro desde sesión/profile version con allowlist y abstención por conflicto.

### P1.5 - Predicción dual-track

Reorganizar `ml/engine` hacia `ml/prediction` solo cuando sea necesario.

Construir:

- Adaptador aislado `synthetic_reference_v021`.
- Rechazo de sujetos reales en track sintético.
- Baseline personal Beta con outcomes reales.
- Ventana de 60 días.
- Solo episodios primarios, misma definición/care mode, inclusión de `yes` temprano válido y
  exclusión de ever-conflicted/`no` temprano.
- Intervalo 90%.
- Abstención por outcomes insuficientes, conflicto y care mode; sin gate muerto por ancho.
- Features preregistradas del challenger.
- Missing/other como null, historia personal `[D-30,D)` y objetivo L2 con offset literal.
- Chequeo de entrenabilidad.
- Challenger L2 en sombra.
- Snapshot point-in-time.
- Sin bandas reales.
- Sin narrativa de riesgo.

Con los datos actuales, el resultado esperado del challenger es `not_trainable_single_class`.

## P2 - Store y migraciones

### P2.2 - Saneamiento v0.2

- Mover o retirar tests unitarios v0.2.
- Eliminar fixture global v0.2.
- Mantener pruebas históricas solo si están aisladas del gate v0.3.
- No borrar el SPEC histórico.
- No modificar tests o módulos P1.

### P2.3 - Migraciones

Crear migraciones inmutables:

```text
001_identity_consent
002_form_prediction_outcome
003_corpus_catalog_recommendations
004_training_evaluation_audit
```

Las migraciones crean todas las tablas de `SPEC 12.1`, incluida `authoring_requests`.

Requisitos:

- FK activas.
- `tenant_id` en entidades clínicas.
- Grants por sujeto, acreditaciones y target definitions versionadas.
- Unicidad efectiva fail-closed para target por scope y catálogo activo por tenant.
- `supersedes_id` en eventos corregibles.
- `opened_at`, `submitted_at`, `as_of_at`, `occurred_at` y `reported_at` con restricciones de orden.
- Revisiones/versiones explícitas.
- Idempotency key + payload hash.
- Índices de consultas principales.
- WAL y `busy_timeout` en demo.
- Bloqueo de SQLite en modo piloto.
- Test de migración desde una DB v0.2 ficticia.

### P2.4 - Store

Implementar comandos concretos, no repositorio genérico:

- Crear/cerrar sesión.
- Insertar observación append-only.
- Crear episodio y snapshot.
- Serializar oportunidad: crear episodio primario o enlazar sesión al activo.
- Insertar reporte y materializar resolución sin perder conflicto histórico.
- Derivar inbox/status de outcome request desde resolución activa y reloj, también tras correcciones.
- Insertar recommendation instance/intento al crear episodio, review por estrategia, plan humano y
  execution.
- Guardar versiones de catálogo y evaluación.
- Idempotencia.
- Auditoría sin payload clínico.
- Consultas tenant-scoped.

Una operación de dominio usa una transacción. No se hace commit por fila.

### Criterios de terminado M2

P1:

- Cuantiles conocidos coinciden con SciPy.
- Una sugerencia aceptada no cambia el posterior futuro.
- Auditoría no cambia al repetir inputs.
- VoI unavailable es `None`, no cero.
- Fila sintética invalida snapshot real.
- Challenger falla limpiamente con una clase.

P2:

- Migraciones suben desde cero y desde fixture v0.2.
- Una corrección conserva la fila original.
- Un lote fallido hace rollback completo.
- Cross-tenant nunca devuelve una fila.
- SQLite piloto bloquea arranque.

### Handoff H2

P1 entrega vectores golden y façades puras. P2 entrega historias y snapshots ficticios que validan
contra contratos P1.

---

## 8. M3 - Flujo vertical de cuidador

**Dependencias:** P1.3-P1.5 y P2.3-P2.4.

### P2.5 - API de formulario

Implementar:

```text
POST /api/v1/form-sessions
POST /api/v1/form-sessions/{id}/answers
POST /api/v1/form-sessions/{id}/submit
GET  /api/v1/prediction-episodes/{id}
GET  /api/v1/outcome-requests
POST /api/v1/prediction-episodes/{id}/outcome-reports
```

Reglas:

- `Idempotency-Key` en todo POST.
- Actor, tenant, rol, acreditación y grant por sujeto antes del servicio o list query.
- `entry_mode` derivado por servidor.
- Default no tocado crea cero observaciones.
- Auditoría persistida al abrir.
- Cada respuesta recalcula el plan.
- Submit atómico siempre cierra sesión. Con target seleccionable crea episodio primario, snapshot,
  outputs, recommendation instance y outcome request, o enlaza al episodio activo. Sin target real
  activo devuelve `target_definition_unavailable` sin crear episodio ni request.
- El servidor fija `submitted_at`; el episodio persiste `as_of_at=prediction_at=submitted_at`.
- Ventana target 24 horas, deadline 48.
- `yes`, `no`, `unknown`, `conflicted`, `early`, `on_time`, `late`: `yes` temprano válido cierra;
  `no` temprano se conserva sin cerrar.
- API devuelve `OutcomeReport` y `OutcomeResolution` separadas; `unknown` explícito deja pending.
- Importaciones guardan `source_mapping_id`; resoluciones son materializaciones append-only con
  `ever_conflicted` monotónico.
- Abstención HTTP 200.

### P2.6 - Web cuidador

Pantallas mínimas:

1. Outcome pendiente.
2. Formulario destacado + cola completa.
3. Sugerencia visual con aceptar/editar/no sé.
4. Confirmación de envío.
5. Score de simulación claramente etiquetado y solo en fixture demo.
6. Baseline personal o abstención `insufficient_verified_outcomes`.
7. Estrategias solo después de aprobación profesional.

Entrada, abstención, resultados y estrategias muestran el límite de emergencia del SPEC; nunca
sugieren esperar una alerta de Faro ante peligro inmediato.

Estados obligatorios:

```text
loading
empty
error
abstained
conflicted
expired
```

### Test E2E cuidador

1. Sembrar target `demo_fixture` y abrir sesión.
2. Recargar sin cambiar auditoría.
3. Dejar una sugerencia sin tocar.
4. Responder otro campo.
5. Enviar.
6. Confirmar que solo se persistió el campo tocado.
7. Obtener episodio abstendido o simulado.
8. Reportar `unknown` explícito y comprobar pending; después reportar outcome concluyente.
9. Repetir POST y recibir el mismo recurso.
10. Intentar otro sujeto del mismo tenant sin grant y recibir 403 auditado.
11. Repetir sin target seleccionable: la sesión cierra sin episodio ni outcome request.

### Handoff H3

Journey JSON, screenshots de estados y DB ficticia sembrada. P2 no modifica algoritmos para hacer
pasar la integración.

---

## 9. M4 - RAG offline y flujo profesional

M4 puede avanzar en paralelo con M3 después de H1 y las migraciones del catálogo.

## P1 - RAG

### P1.6 - Dominio documental

Crear:

```text
rag/domain
rag/authoring
rag/runtime
tools/rag_authoring
```

Implementar:

- Manifest de bytes/documento, derechos, extractor/OCR, normalización, chunker y hashes.
- Chunks con localizador, texto normalizado y hash.
- Exclusión verificable de notas, mensajes y texto libre de usuario en chunks, embeddings y prompts.
- Strategy text/claims/citas y estados de documentos, estrategias, sets y catálogos.
- Claims y citas no vacíos, con cada claim enlazado y hasheado.
- `AuthoringReview` append-only para evidencia, clínica, set y activación de catálogo; no confundir
  con recommendation review de caso.
- `ScenarioV1`/`ScenarioPredicate` único, review del set, implicación set->strategies y catálogo
  activo único por tenant.
- BM25 top 20.
- Retrieval denso top 20 solo si el modelo está registrado.
- RRF `k=60`.
- Top 8 final.
- Borrador LLM local opcional.
- Verificación literal de citas.
- Revisión de evidencia.
- Bloqueo de doble revisión por la misma identidad.
- Suspensión por fuente retirada.
- Build manifest reproducible con modo `hybrid|lexical_only` y tie-break por chunk hash.

Si falta embedding aprobado, el build funciona en modo lexical-only y lo declara. No se descarga un
modelo silenciosamente.

### P1.7 - Runtime determinista

El runtime:

- Recibe escenario categórico mínimo potencialmente seudonimizado.
- Consume catálogo precomputado.
- Filtra exclusions y contraindications.
- Devuelve máximo 3 estrategias.
- Ordena de forma determinista.
- Incluye citas exactas.
- No importa LLM o embeddings.
- Se abstiene y devuelve `AuthoringRequestIntent` si no hay match; no escribe en DB.
- Evalúa predicates de set y estrategia por separado; recibe catálogo tenant activo explícito.

## P2 - Profesional

### P2.7 - API profesional

Implementar:

```text
GET  /api/v1/prediction-episodes/{id}/recommendations
GET  /api/v1/recommendation-instances?review_status=pending
POST /api/v1/recommendation-instances/{id}/reviews
POST /api/v1/recommendation-instances/{id}/executions
```

Requisitos:

- `If-Match` y 409.
- Instancia inmutable con versiones exactas.
- GET sin creación de instancias ni authoring requests; ambos se persisten al crear el episodio.
- Inbox filtrado en SQL por tenant, rol, acreditación y grants.
- Reviews por `strategy_version_id`: `approved`, `rejected`, `human_plan_substituted`,
  `not_applicable`, `deferred`.
- Plan humano sin citas RAG.
- Execution por strategy/plan separada del review y con orden temporal validado.
- Serializer union entrega strategy aprobada o human plan sustituido; exposición exige la decisión
  activa correspondiente, no solo timestamps.
- Aprobación y sustitución exigen `required_approver_role`; review, entrega y ejecución revalidan
  dependencias activas y bloquean instancias suspendidas.
- Feedback no cambia catálogo activo.
- Solo recomendaciones aprobadas llegan al cuidador.

### P2.8 - Web profesional

Pantallas mínimas:

1. Inbox de recomendaciones pendientes.
2. Escenario sin datos identificables innecesarios.
3. Estrategias y citas verificables.
4. Aprobar, rechazar, sustituir, diferir o marcar no aplicable.
5. Registrar aplicación.
6. Ver outcome pendiente y estado de conflicto.
7. Historial de versiones sin editarlo.

### Criterios de terminado M4

- Un documento real versionado produce fragmentos verificables.
- Una cita falsa bloquea activación.
- Dos revisores iguales bloquean activación.
- Si no hay revisor clínico autorizado, catálogo no activo y runtime abstiene.
- La precedencia de disponibilidad distingue corpus, review clínica, suspensión, ambigüedad y no
  ready con razones estables.
- Mismo escenario+versión devuelve la misma decisión de dominio; GET repite el envelope persistido.
- Runtime funciona sin red y sin LLM.
- No match devuelve HTTP 200; P2 deduplica `AuthoringRequest` por tenant+sujeto al crear el episodio.
- Exportar a autoría exige base separada y consulta generalizada certificada; ningún atributo de
  caso llega a retrieval, embeddings o LLM.
- Review, human plan, execution y outcome son filas separadas.

### Handoff H4

Manifest de corpus y catálogo, hashes y IDs de versión. Cuerpos, índices y modelos permanecen fuera
de Git.

---

## 10. M5 - Volante y evaluación

## P1

### P1.8 - Snapshots y entrenamiento

`tools/train`:

- Construye snapshots separados por origen.
- Aplica `project_as_of`, episodios primarios, target version, consentimientos y cutoff temporal.
- Reautoriza `secondary_model_use` al inicio de cada run; snapshots revocados no se reutilizan y
  artefactos reales dependientes se suspenden para nuevos usos.
- Registra IDs, hashes, código, configuración y dependencias.
- Mantiene el track sintético como simulación.
- Calcula baseline real.
- Declara challenger no entrenable cuando corresponda.
- Nunca promueve automáticamente.

### P1.9 - Evaluación

Implementar:

- Brier score.
- Average precision de scikit-learn.
- AUC solo con ambas clases.
- Calibration intercept y slope.
- `EvaluationProtocolVersion`: outer LeaveOneGroupOut, selección de lambda en inner grouped folds,
  OOF externo y bootstrap de 2.000 clusters sujeto.
- Outer features personales usan solo outcomes del sujeto revelados antes de cada landmark; nunca
  fit/selección. El reveal schedule queda persistido.
- Decision coverage.
- Abstención por razón.
- Métricas por origen y grupos solo sobre mínimos de privacidad.
- Dataset/reporte separado por `target_definition_version` exacta; sin pooling v0.3.
- `alert-budget recall=not_estimable` mientras no exista decision policy.
- Conteos/completitud cuando no hay dos clases.
- Reportes de review, execution y outcome por separado.

No usar la palabra eficacia en asociaciones observacionales.

## P2

### P2.9 - Persistencia del volante

- Importar manifests P1 sin entrenar dentro de API.
- Guardar snapshot, run, model version y report atómicamente.
- Respetar revocación en snapshots futuros.
- Auditar build y activación manual.
- Implementar `GET /api/v1/evaluation/{model_version}`.

### P2.10 - Vista de evaluación

Mostrar:

- Origen real/sintético.
- Estado estimable/no estimable.
- Dataset hash y modelo.
- Métricas con intervalos cuando existan.
- Limitaciones visibles.
- Estado del challenger.
- Completitud de outcomes.

### Criterios de terminado M5

- Repetir con seed 42 produce resultados estadísticos iguales.
- Snapshot real rechaza sintéticos.
- Revocación excluye snapshots futuros.
- Revocación bloquea runs nuevos sobre snapshots viejos y suspende artefactos reales dependientes.
- ModelVersion y EvaluationReport suspendidos pasan a retired; uso futuro crea versiones nuevas.
- Challenger no se despliega.
- Desarrollo OOF no produce `shadow_evaluated`; ese estado exige periodo prospectivo preregistrado.
- Una sola clase no produce AUC falsa.
- Menos de 80% de réplicas válidas no produce intervalo; grupos pequeños se suprimen.
- Cada métrica informa origen, dataset y modelo.
- Feedback genera propuesta/reporte, no cambio productivo.

---

## 11. M6 - Invariantes y release

Los 35 invariantes de `SPEC 17` se distribuyen sin carpeta compartida.

### P1

Tests algorítmicos y de contrato:

```text
INV-02, INV-03, INV-04, INV-06, INV-07,
INV-09, INV-10, INV-16 a INV-28,
INV-32 a INV-35
```

Gate:

```text
ruff check .
ruff format --check .
pytest tests/p1 -q
lint-imports
generación de contratos sin diff
auditoría de prompts/índices/features
```

### P2

Tests de persistencia, seguridad e integración:

```text
INV-01, INV-05, INV-08, INV-11 a INV-15,
INV-27, INV-29, INV-30, INV-31
```

La duplicación de INV-27 se evita así: P1 prueba que el dominio no muta el catálogo; P2 prueba que
el flujo API tampoco lo muta.

Gate:

```text
pytest tests/p2 tests/integration -q
pruebas de migración
pruebas cross-tenant, same-tenant/wrong-subject y grants revocados
pruebas de idempotencia/concurrencia, incluida misma key en IDs concretos distintos
pnpm lint
pnpm typecheck
pnpm test
pnpm build
OpenAPI contra contratos
```

### Gate conjunto

Ambos ejecutan; cada dueño corrige solo su zona:

```text
pytest tests -q
ruff check .
ruff format --check .
lint-imports
pnpm --dir apps/web lint
pnpm --dir apps/web typecheck
pnpm --dir apps/web test
pnpm --dir apps/web build
```

Después recorren los 18 puntos de `SPEC 20`.

El release manifest declara por separado implementación, corpus, target y catálogo. Sin corpus
legalmente utilizable no se completa M4 ni el DoD. Sin target activo no se crean labels reales. Sin
revisor autorizado puede cerrarse implementación técnica como
`catalog_status=blocked_clinical_review`: debe pasar gates y demostrar abstención, pero no puede
afirmar catálogo activo.

---

## 12. Qué no construir

- Compatibilidad completa con los ocho endpoints v0.2.
- Bandas reales verde/ámbar/rojo.
- Promoción automática de modelos.
- Entrenamiento real con una sola clase.
- Random Forest para seleccionar predictores con los datos actuales.
- LLM en runtime.
- RAG sobre historiales o notas.
- Recomendaciones libres fuera del catálogo.
- Actualización automática por acceptance rate.
- Fine-tuning.
- Inferencia causal de eficacia.
- PWA, offline sync, push, voz o Telegram.
- Docker, colas, microservicios o Kubernetes para la demo.
- PostgreSQL u OIDC dentro del alcance demo.
- Repository pattern genérico.
- Contratos TypeScript mantenidos a mano.
- Features desde texto libre.
- Conversión de categorías a números ficticios.
- Datos reales, DB, modelos, corpus, índices o secrets en Git.
- Refactor de módulos no tocados por una tarea.

---

## 13. Orden de recorte si falta tiempo

Nunca se recortan seguridad de datos, abstención, append-only, idempotencia o separación de
real/sintético.

Se recorta en este orden:

1. Borrador LLM opcional; se conserva retrieval y autoría manual.
2. Retrieval denso; se declara `lexical_only`.
3. Gráficos de evaluación; se conserva JSON estructurado.
4. Polish visual; se conserva accesibilidad y estados.
5. Challenger entrenado; se conserva chequeo `not_trainable`.
6. Catálogo activo si falta revisor; se conserva abstención correcta.

No se recortan:

- Outcome explícito.
- Default no vinculante.
- Auditoría estable.
- Citas verificables.
- Revisión versionada.
- Separación review/execution/outcome.
- Grants por sujeto y límite de emergencia.
- Target versionado para cualquier label real.

---

## 14. Estimación relativa

Partiendo del repositorio actual y con dedicación completa:

| Área | P1 | P2 |
|---|---:|---:|
| Contratos y generación | Alta | Baja |
| Defaults, formulario y predicción | Alta | - |
| RAG autoría/runtime | Muy alta | Media |
| Training/eval | Alta | Baja |
| DB/API/idempotencia | - | Muy alta |
| Web cuidador/profesional | - | Muy alta |
| Tests | Alta | Muy alta |
| Corte vertical M1-M3 | 10-14 días hábiles | 12-16 días hábiles |
| DoD técnico M0-M6 | 25-35 días hábiles | 30-40 días hábiles |

Con trabajo paralelo, el DoD técnico completo representa aproximadamente 6-8 semanas calendario;
revisión clínica, licencias o disponibilidad de corpus pueden añadir espera sin añadir capacidad de
implementación. El rango corto corresponde solo al journey cuidador con contratos, persistencia,
defaults, baseline abstendido y tests esenciales: no incluye autoría RAG completa, flujo profesional,
evaluación completa ni todos los 35 invariantes.

Con menos de dos semanas por persona puede mostrarse un corte parcial, pero no declararse completo
el DoD v0.3.

Para equilibrar:

- P1 entrega mocks, ejemplos, TS/Zod y textos completos.
- P2 no reimplementa fórmulas.
- P1 asume todos los tests algorítmicos y RAG.
- P2 limita frontend a los journeys del SPEC, sin dashboard adicional.
- Ayudar significa revisar o crear un fixture en la zona propia, nunca editar archivos ajenos.

---

## 15. Definition of Done de una tarea

Una tarea se marca lista solo si:

1. Cumple su criterio verificable.
2. Tiene test que demuestra el comportamiento descrito.
3. Toca únicamente paths del dueño.
4. No inventa contrato ni número.
5. No mezcla datos reales y sintéticos.
6. No destruye historia.
7. Expone limitaciones y abstención.
8. Pasa el gate aplicable.
9. Produce el artefacto de handoff indicado.
10. No depende de una aprobación clínica ficticia.
