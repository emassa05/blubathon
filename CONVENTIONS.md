# FARO - Convenciones de implementación v2.0

## Cómo construir SPEC v0.3.0 sin mezclar responsabilidades

Este documento define cómo escribir y organizar el código. `SPEC.md` define qué debe hacer el
producto. Si ambos difieren, manda `SPEC.md`.

---

## 1. Lectura obligatoria

Antes de editar código o generar artefactos se leen, en este orden:

1. `SPEC.md`.
2. `CONVENTIONS.md`.
3. `TAREAS.md`.
4. `FUNDAMENTOS.md` para comprender fórmulas y evidencia.

Los archivos históricos y `Untitled document.md` no son normativos.

---

## 2. Principios

1. La solución más pequeña que cumple el SPEC es la correcta.
2. Una capa nueva necesita una responsabilidad que no pueda vivir en una capa existente.
3. No se crea abstracción para una única implementación hipotética.
4. Contratos, estados y fórmulas se hacen explícitos antes de crear UI.
5. Un valor ausente permanece ausente.
6. La abstención se diseña y prueba como salida normal.
7. La historia clínica, de recomendaciones y de consentimiento es append-only.
8. Un número de política se etiqueta como política; no se vende como evidencia.
9. Ningún LLM ocupa una posición donde pueda alterar riesgo o recomendaciones activas.
10. Dos personas nunca editan el mismo archivo durante el mismo hito.

---

## 3. Forma objetivo del repositorio

```text
faro/
├── SPEC.md
├── CONVENTIONS.md
├── TAREAS.md
├── FUNDAMENTOS.md
├── apps/
│   ├── api/
│   │   ├── main.py
│   │   ├── routes/
│   │   ├── services/
│   │   ├── store/
│   │   └── migrations/
│   └── web/
│       ├── app/
│       ├── components/
│       ├── lib/
│       └── styles/
├── packages/
│   └── shared/
│       ├── models.py
│       ├── texts.py
│       ├── schema/
│       └── generated/
├── ml/
│   ├── defaults/
│   ├── form/
│   ├── features/
│   ├── prediction/
│   ├── eval/
│   ├── adapters/
│   ├── spec_constants.py
│   └── errors.py
├── rag/
│   ├── domain/
│   ├── authoring/
│   └── runtime/
├── tools/
│   ├── rag_authoring/
│   ├── contracts/
│   ├── train/
│   └── seed/
├── tests/
│   ├── p1/
│   ├── p2/
│   └── integration/
├── data/
└── fixtures/
```

No se mueve código existente solo por estética. La migración a esta forma ocurre cuando una tarea
del `TAREAS.md` necesita modificar ese módulo.

---

## 4. Dependencias

Las dependencias válidas son:

```text
apps/web -> apps/api (HTTP solamente)

apps/api -> packages/shared
apps/api -> ml
apps/api -> rag/runtime
apps/api -> apps/api/store

ml -> packages/shared
rag -> packages/shared

tools/rag_authoring -> rag/authoring
tools/train -> ml
```

Prohibiciones:

- `ml` no importa `apps`, SQL, FastAPI ni React.
- `rag` no importa `apps` ni el store clínico.
- `packages/shared` no importa `ml`, `rag` ni `apps`.
- `apps/web` no abre SQLite ni carga artefactos Python.
- `rag/authoring` no consulta sujetos, observaciones o outcomes.
- `rag/runtime` no llama embeddings ni LLM.
- `apps/api/store` no calcula defaults, VoI o riesgo.

`import-linter` debe comprobar al menos estas reglas. Un comentario no sustituye el contrato.

---

## 5. Propiedad exclusiva

La propiedad detallada vive en `TAREAS.md`. La frontera permanente es:

| Zona | Dueño | El otro puede |
|---|---|---|
| `packages/shared/**` | P1 | leer y solicitar cambios |
| `ml/**` | P1 | leer |
| `rag/**` | P1 | leer |
| `tools/train/**`, `tools/rag_authoring/**` | P1 | ejecutar |
| `tools/contracts/**`, `data/manifest.json`, `data/*.manifest.json` | P1 | ejecutar/leer |
| `data/**` excepto manifests aprobados | P2 | limpieza final; P1 puede generar artefactos ignorados |
| `apps/api/**` | P2 | leer |
| `apps/web/**` | P2 | leer |
| `tools/seed/**` | P2 | ejecutar |
| `tests/p1/**` | P1 | leer |
| `tests/p2/**`, `tests/integration/**` | P2 | leer |
| `pyproject.toml`, `.importlinter`, `.gitignore` | P1 | solicitar cambio |
| `package.json`, `pnpm-lock.yaml`, `.github/**` | P2 | solicitar cambio |
| Los cuatro documentos normativos | congelados durante implementación | nadie sin acuerdo |

Reglas:

1. P2 nunca corrige directamente un contrato de `packages/shared`.
2. P2 solicita el cambio con ejemplo de request/response y motivo.
3. P1 actualiza contrato, schema generado y fixture en un único cambio.
4. P2 integra solo después de que el contrato publicado esté verde.
5. Si una tarea exige tocar una zona ajena, la tarea está mal dividida y se rediseña.
6. Una dependencia de zona ajena se solicita con paquete, versión, licencia, motivo y test; el dueño
   del manifest aplica el cambio.

---

## 6. Contratos compartidos

`packages/shared` es independiente y contiene:

- Modelos Pydantic.
- Enums y tipos cerrados.
- Textos normativos de UI.
- JSON Schema generado.
- Tipos TypeScript/Zod generados o verificados desde el mismo schema.

Reglas:

- `extra="forbid"` en fronteras de API.
- IDs UUID v4.
- Timestamps UTC conscientes de zona.
- `FormSession.opened_at` y `submitted_at` son distintos; el episodio usa
  `as_of_at = prediction_at = submitted_at`.
- El servidor genera `opened_at`, `submitted_at`, `ingested_at` y `reported_at`; un tiempo efectivo
  declarado por cliente es otro campo y nunca fija el cutoff.
- Enums cerrados, sin strings libres donde existe catálogo.
- Todo response tiene modelo explícito.
- Ningún `dict[str, object]` sustituye un contrato estable.
- Una pareja opcional se valida como pareja: ambos campos o ninguno.
- El schema generado no se edita a mano.
- Un cambio incompatible exige nueva versión de contrato.

El contrato no importa constantes desde `ml`. Las constantes contractuales viven en
`packages/shared/constants.py`; las fórmulas internas viven en `ml/spec_constants.py`.

---

## 7. Constantes y evidencia

Cada constante normativa incluye:

```python
ConstantSpec(
    value=0.70,
    decision_class="policy",
    spec_ref="SPEC 6.6 / C09",
)
```

Clases válidas:

```text
mathematical
evidence
policy
engineering
```

Prohibido:

- Duplicar un literal del registro de constantes.
- Marcar un parámetro de simulación como evidencia.
- Agregar un umbral porque "se ve bien".
- Cambiar un número sin actualizar SPEC, test y versión.
- Usar un comentario como única referencia.

Las fórmulas puras reciben sus parámetros. Las funciones no leen configuración global oculta.

---

## 8. Datos y procedencia

### 8.1 Append-only

Se crean nuevas filas para:

- Observaciones.
- Outcomes.
- Revisiones.
- Ejecuciones.
- Consentimientos.
- Versiones de documento, estrategia y modelo.

Una corrección usa `supersedes_id`. No se sobrescribe el valor anterior.

Toda lectura estadística usa `project_as_of` del SPEC: selecciona solo la hoja vigente de cada
cadena conocida al cutoff. Una corrección futura no cambia snapshots históricos; ramas y ciclos
fallan, no se resuelven por conveniencia.

### 8.2 Ausencia

Reglas:

- `None`/`null` significa sin valor.
- `false` es una respuesta observada.
- `0` es un conteo observado.
- `unknown` es una decisión explícita sin valor.
- Un campo omitido no es `unknown` automáticamente.
- Una ausencia de evento no es un outcome negativo.

### 8.3 Entry mode

El servidor deriva `entry_mode`; el cliente solo declara interacción.

Nunca se confía en un `entry_mode` enviado por navegador.

### 8.4 Adaptadores

Los adaptadores:

- Conservan valor fuente.
- Usan tablas de mapping versionadas.
- Fallan ante categorías desconocidas.
- No convierten categorías en conteos.
- No convierten asistencia en participación.
- No generan timestamps ficticios sin marcarlos como importación.
- Tienen fixtures literales de cada categoría fuente.

### 8.5 Contexto y corte temporal

- `source` en una observación significa `home`, `therapy` o `school`; no identifica al actor ni a
  una publicación.
- `source_id` se reserva para corpus; `actor_id` y `source_mapping_id` tienen responsabilidades
  separadas.
- El servidor asigna `opened_at` y `submitted_at`; el navegador no fija el cutoff.
- Un snapshot rechaza datos cuyo tiempo efectivo o de ingesta sea posterior a `as_of_at`.
- Un `yes` temprano es elegible si el evento ya ocurrió dentro del target; un `no` temprano no
  cierra la ventana.
- Reporte (`yes|no|unknown`) y resolución (`pending|yes|no|unknown|conflicted`) usan tipos distintos.
- Resoluciones son materializaciones append-only recalculadas tras cada corrección; su
  `ever_conflicted` es monotónico.
- Un episodio alguna vez conflictivo no entra al dataset primario v0.3, aunque tenga adjudicación.

---

## 9. Estadística

### 9.1 Funciones puras

Las funciones estadísticas reciben datos y devuelven resultados sin I/O:

```python
posterior_default(counts, prior, quantile) -> PosteriorDefault
compute_dqi(history, as_of_at, policy) -> DataQuality
compute_predictive_voi(values, probabilities) -> float
build_personal_baseline(outcomes, policy) -> Estimate
```

El DQI se reporta sin convertirlo en gate global. Mientras `SPEC 15` no registre un umbral, cada
track se abstiene solo por sus reglas explícitas.

El challenger implementa la función objetivo, folds y offset literales del SPEC. No se sustituye
por `LogisticRegression` si la librería no soporta el offset fijado. Toda evaluación consume una
`EvaluationProtocolVersion`, no flags ad hoc de notebook.

### 9.2 Precisión

- Cálculos internos en `float64`.
- Redondeo solo en serialización.
- Banda o estado se calcula con el mismo valor serializado que valida el contrato.
- Cuantiles usan SciPy; no se aproximan manualmente.
- Empates y NaN tienen comportamiento explícito.

### 9.3 Reproducibilidad

- Semilla offline `42` donde exista aleatoriedad controlada.
- Splits y bootstrap agrupados por `subject_id`.
- Snapshots de dataset inmutables y hasheados.
- Un training run registra código, configuración, dependencias y dataset hash.
- Timestamps operativos no participan en igualdad de resultados estadísticos.

### 9.4 Métricas

- Average precision viene de scikit-learn.
- Brier usa su definición estándar.
- AUC no se calcula con una sola clase.
- Bootstrap agrupa por sujeto.
- Toda selección vive dentro del fold.
- Hyperparameters se eligen en inner grouped folds de cada outer train; el outer outcome nunca
  participa en selección.
- Cada reporte real usa una sola `target_definition_version` exacta.
- Una métrica sin soporte devuelve `not_estimable`, no cero.

---

## 10. Formulario

- Un default se renderiza como ayuda, no como valor del control.
- `accept_default` exige acción explícita.
- Si el campo tuvo una presentación, cualquier otro valor deriva `default_edited`; el cliente no
  puede enviarlo como `manual_no_default`.
- `unknown` persiste sin valor.
- Todos los campos aplicables permanecen accesibles.
- Recálculo secuencial ocurre tras cada respuesta confirmada.
- `audit_mode` se fija al crear la sesión y no cambia.
- El outcome pendiente no consume un slot diario; `QuestionPresentation` define qué fue realmente
  destacado y permite reproducir antigüedad/exploración.
- Si una sesión cae dentro de un target primario abierto, se enlaza al episodio: no crea ventanas
  solapadas.
- Sin target definition seleccionable, la sesión cierra sin episodio ni outcome request real.
- El estado de outcome request se deriva de resolución/reloj; no se muta una segunda máquina que
  pueda quedar desincronizada.
- La UI nunca inventa defaults localmente.
- El navegador envía solo campos tocados.
- Estados loading, error, vacío, abstención y conflicto son obligatorios.

Los textos visibles salen de `packages/shared/texts.py` o del catálogo versionado.

---

## 11. RAG y LLM

### 11.1 Separación

`rag/authoring` puede:

- Indexar literatura permitida.
- Recuperar fragmentos.
- Pedir un borrador a un LLM local.
- Verificar citas.
- Crear una versión draft.
- Operar en `hybrid` o `lexical_only` declarado por un build manifest completo.
- Usar un solo `ScenarioV1`/`ScenarioPredicate` y comprobar set y estrategia fail-closed.
- Construir ScenarioV1 solo mediante `build_scenario` P1; P2 persiste, no replica precedencias.

`rag/runtime` solo puede:

- Recibir un escenario categórico.
- Buscar un set precomputado.
- Filtrar incompatibilidades.
- Devolver texto aprobado y citas.

### 11.2 Prompts

- Viven versionados como package data.
- Declaran input y output schema.
- No incluyen datos personales.
- Solo reciben fragmentos de literatura versionada con derechos registrados.
- Nunca reciben notas, mensajes ni otro texto libre clínico o escrito por usuarios.
- Un cambio de prompt crea nueva versión de build.
- El output del LLM nunca se activa sin revisión.
- Extractor, chunker, BM25, embeddings, RRF, prompts y normalización quedan hasheados en el manifest.
- Reviews de autoría son eventos con actor, accreditation, hash y decisión; nunca se reutiliza la
  recommendation review de un caso.
- Ningún escenario de caso entra a retrieval: export exige base separada, consulta generalizada y
  certificación de privacidad.

### 11.3 Citas

- Cada claim apunta a un fragmento literal.
- El fragmento se verifica contra hash y localizador.
- DOI es opcional; URL, versión y localizador son obligatorios.
- Una fuente retirada invalida versiones dependientes.
- No se usa la frase "cero alucinación".

---

## 12. API

### 12.1 Servicios

Las rutas:

- Validan request.
- Autorizan actor y tenant.
- Llaman un servicio de aplicación.
- Serializan response.

No contienen SQL ni fórmulas.

Los servicios:

- Abren una transacción por comando.
- Cargan estado requerido.
- Llaman dominio puro.
- Persisten eventos.
- Devuelven contrato compartido.

GET no crea instancias ni solicitudes de autoría. La instancia de recomendación y cualquier intent
deduplicado se persisten atómicamente al crear el episodio; el GET posterior es lectura estable.
El response de recomendaciones es union de strategy aprobada o human plan sustituido y se filtra en
servidor. Aprobación/sustitución exige el approver role; una exposición exige la review activa
compatible y dependencias todavía activas. Suspensión deja historia no accionable.

### 12.2 Errores

Formato:

```json
{
  "error": {
    "code": "stable_code",
    "message_es": "Mensaje sanitizado.",
    "request_id": "uuid"
  }
}
```

Reglas:

- Abstención es HTTP 200.
- Validación es 422.
- Conflicto de revisión/idempotencia es 409.
- No autenticado es 401.
- No autorizado/cross-tenant es 403.
- Same-tenant sin `SubjectAccessGrant` también es 403.
- Modelo o catálogo no listo usa salida de estado si es esperable, no 500.
- Excepción inesperada se registra con stack y request ID, sin payload clínico.

### 12.3 Idempotencia

- Todo POST exige `Idempotency-Key`.
- El scope incluye tenant, actor, método y path concreto normalizado; path params, query y body se
  hashean con JCS/separación de dominio. Dos IDs distintos nunca comparten replay.
- Clave y hash de payload se guardan juntos.
- Mismo payload devuelve respuesta original.
- Payload distinto con misma clave devuelve 409.
- Un replay vuelve a autorizar rol, accreditation, grant, consent y capability antes de devolver la
  respuesta guardada.
- Una lista se inserta en una transacción.

---

## 13. Persistencia y migraciones

- SQL vive solo en `apps/api/store`.
- No se ejecuta DDL por request.
- Las migraciones tienen número, nombre y checksum.
- Toda FK tiene test.
- SQLite demo usa WAL y `busy_timeout`.
- El modo piloto rechaza SQLite.
- JSON almacenado valida schema y versión antes de insertarse.
- Toda consulta clínica incluye `tenant_id`.
- Toda consulta de sujeto incluye el grant activo en SQL; no filtra después de cargar filas.
- Las queries usan parámetros, nunca interpolación de usuario.
- Los repositorios no hacen commit por fila.

Una migración no se modifica después de compartirse; se crea otra.

---

## 14. Frontend

Stack objetivo:

```text
Next.js 15+
TypeScript strict
Tailwind
componentes accesibles basados en Radix/shadcn cuando aporten valor
```

Reglas:

- Mobile-first y usable en desktop.
- Sin animaciones automáticas intensas.
- Respeta `prefers-reduced-motion`.
- No depende solo del color para estados.
- Botones y controles con área táctil mínima de 44 px.
- Focus visible y navegación por teclado.
- Lenguaje afirmativo, no diagnóstico.
- En entrada, abstención, resultado y recomendaciones se muestra que Faro no monitorea emergencias
  ni debe retrasar protocolos urgentes o de resguardo.
- La abstención no se presenta como error.
- Una sugerencia tiene estilo distinto de un valor confirmado.
- Las citas se pueden abrir y verificar.
- Un borrador no revisado nunca aparece como recomendación aprobada.

No se agrega PWA, offline sync ni notificaciones push en v0.3.

---

## 15. Seguridad y privacidad

- No se loguean cuerpos de requests clínicos.
- No se usan IDs externos como UUID derivables sin secreto.
- Secrets solo en variables de entorno o secret store.
- `.env` nunca entra a Git.
- CORS usa allowlist explícita.
- Documentación OpenAPI se deshabilita en piloto salvo rol administrador.
- Toda lectura o escritura real genera evento de auditoría.
- Roles se combinan con grants por sujeto; professionals además requieren acreditación institucional
  vigente. Tenant y rol por sí solos no autorizan.
- Consent, accreditation y authoring authorization se proyectan al cutoff por purpose/capability;
  cada training/evaluation run reautoriza, aunque el snapshot sea anterior.
- El corpus RAG y la DB clínica usan almacenamientos separados.
- Ningún modelo externo recibe payload personal.
- Índices, embeddings y prompts se auditan para impedir texto libre clínico; la literatura
  autorizada no se clasifica como texto de usuario.
- Los tests usan datos ficticios, no exports reales.

---

## 16. Tests

Buscamos invariantes, no porcentaje artificial de cobertura.

Capas:

```text
tests/p1           contratos, estadística, ML, RAG e invariantes de P1
tests/p2           API, store, UI e invariantes de P2
tests/integration  extremo a extremo, dueño P2
```

Reglas:

- Cada regla de `SPEC 17` tiene un test nombrado.
- Tests de estadística comparan resultados numéricos conocidos.
- Tests de LLM usan transporte simulado; no dependen de Ollama real.
- Tests de tiempo usan reloj inyectado.
- Tests de auditoría usan secreto fijo de prueba.
- Tests de DB corren sobre migraciones reales.
- Tests de autorización incluyen cross-tenant.
- Tests de autorización incluyen same-tenant/wrong-subject, grant revocado y lista filtrada en DB.
- Tests de RAG verifican texto citado contra hash.
- Tests de outcome cubren `yes` temprano elegible y `no` temprano provisional.
- Tests de outcome separan reporte/resolución, cutoff abierto, conflicto permanente y ausencia al
  deadline; tests de episodios impiden targets primarios solapados.
- Tests de target cubren cero/múltiples definiciones activas, demo synthetic y mapping de import.
- Tests de GET prueban que recomendaciones no crean filas y retornan el envelope persistido.
- Tests de evaluación prueban que lambda se elige solo dentro del outer train.
- Tests idempotentes reutilizan una key/body sobre dos path IDs y exigen recursos distintos.
- Un test no se llama "mueve el riesgo" si no afirma desigualdad.
- Un test no acepta igualdad cuando el requisito exige aumento estricto.
- Los tests públicos no se saltan silenciosamente por ausencia de datos privados.

---

## 17. Herramientas

Python:

```text
ruff check .
ruff format --check .
pytest tests -q
lint-imports
```

Frontend:

```text
pnpm lint
pnpm typecheck
pnpm test
pnpm build
```

Contratos:

```text
python -m tools.contracts.generate
git diff --exit-code packages/shared/generated
```

No se introducen Docker, colas, microservicios o Kubernetes para la demo local. PostgreSQL y OIDC
pertenecen al perfil piloto posterior.

---

## 18. Git

- Commits pequeños y no interactivos.
- No se hace commit directo de datos, DB, modelos, índices o secrets.
- No se reescribe historia compartida.
- No se usa `git reset --hard` ni force push.
- Cada commit toca solo la zona del dueño.
- Los contratos se publican antes de que el consumidor los integre.
- Un archivo generado se actualiza junto a su fuente.
- `main` debe permanecer verde.

El trabajo documental solicitado en esta sesión no se commitea ni se pushea.

---

## 19. Definition of Done

Una tarea está terminada cuando:

1. Cumple el criterio literal de `TAREAS.md`.
2. Tiene tests relevantes y no nominales.
3. No rompe dependencias ni propiedad.
4. No introduce números normativos fuera del registro.
5. No mezcla real y sintético.
6. No inventa valores ausentes.
7. Mantiene historial append-only.
8. Pasa formato, lint, tests, contratos y build aplicables.
9. Documenta limitaciones visibles al usuario si corresponde.
10. No deja TODO silencioso en una ruta activa.

---

## 20. Lo que no hacemos

- Repository pattern genérico sobre cada tabla.
- Clases base abstractas sin dos implementaciones reales.
- Fine-tuning del LLM.
- LLM de producción redactando acciones nuevas.
- Autocomplete silencioso.
- Promoción automática de modelos o catálogo.
- Métricas caseras cuando existe implementación validada.
- Conversión de categorías a números para facilitar un modelo.
- Causalidad inferida desde feedback observacional.
- Compatibilidad hacia atrás sin consumidor o dato persistido que la requiera.
- Seguridad ficticia basada solo en CORS o UUID.
- Features derivadas de notas libres.
- Claims clínicos sin fuente, versión y revisión.

La regla final: si una persona no puede explicar de dónde salió un dato, un número o una
recomendación, esa salida no se publica.
