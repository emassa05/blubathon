# FARO - SPEC v0.3.0

## Contrato de producto, datos, estadística y seguridad

**Estado:** borrador no publicado, previo al freeze inicial. `0.3.0` es la versión reservada para el
primer contrato aprobado; todavía no existen schemas o artefactos v0.3 publicados. Las ediciones de
esta fase no son cambios entre releases. Después del freeze, toda modificación sigue `SPEC 19` y
exige semver nuevo. El código actual sigue siendo transitorio hasta cumplir este documento.

**Autoridad:** este archivo reemplaza como fuente normativa a `SPEC.v0.2.0.bak.md` y corrige las
ideas exploratorias de `Untitled document.md`. Los documentos anteriores se conservan solo como
historia y contexto.

**Documentos relacionados:**

- `CONVENTIONS.md`: cómo se implementa este contrato.
- `TAREAS.md`: quién construye cada parte y en qué orden.
- `FUNDAMENTOS.md`: explicación simple de las fórmulas, evidencia y límites.

---

## 0. Cómo leer este SPEC

### 0.1 Clases de decisiones

Todo valor normativo pertenece a una clase. La clase evita presentar una decisión de producto como
si fuera una verdad científica.

| Marca | Clase | Significado |
|---|---|---|
| `[M]` | Matemática | Identidad o fórmula derivada matemáticamente |
| `[E]` | Evidencia | Hecho observado en datos o fuente externa verificable |
| `[P]` | Política | Decisión de producto, seguridad o tolerancia al riesgo |
| `[I]` | Ingeniería | Restricción de implementación, protocolo o reproducibilidad |

Reglas:

1. Un valor `[P]` puede cambiar por decisión del equipo, pero exige nueva versión del SPEC.
2. Un valor `[E]` siempre cita su origen en `FUNDAMENTOS.md`.
3. Un valor `[M]` debe tener fórmula y test numérico.
4. Un valor `[I]` debe tener una razón operativa verificable.
5. Ningún peso sintético se presenta como evidencia clínica.

### 0.2 Jerarquía

Ante contradicción manda, en este orden:

1. `SPEC.md`.
2. Contratos ejecutables de `packages/shared` que ya cumplan este SPEC.
3. `CONVENTIONS.md`.
4. `TAREAS.md`.
5. `FUNDAMENTOS.md`.
6. README, presentaciones y documentos históricos.

### 0.3 Alcance de v0.3.0

v0.3.0 construye una demo local completa y deja contratos listos para un piloto. Incluye:

- Formulario adaptativo con sugerencias estadísticas no vinculantes.
- Priorización por outcome pendiente, antigüedad, exploración y VoI cuando esté disponible.
- Predicción a 24 horas con tracks separados para simulación y datos reales.
- RAG de autoría offline y catálogo clínico precomputado con citas.
- Revisión profesional, ejecución y outcome como eventos separados.
- Volante de datos versionado, reversible y sin despliegue automático.
- Frontend para cuidador y profesional.

No incluye validación clínica ni despliegue automático de modelos.

---

## 1. Uso previsto

Faro organiza registros, calcula estadísticas personales, presenta estimaciones experimentales y
ofrece opciones de apoyo previamente curadas para revisión profesional.

Faro:

- No diagnostica.
- No prescribe tratamientos.
- No reemplaza el criterio profesional.
- No ejecuta intervenciones de forma autónoma.
- No afirma eficacia causal a partir de feedback observacional.
- No afirma rendimiento clínico usando datos sintéticos.

### 1.1 Modos de uso

| `intended_use` | Datos | Uso permitido |
|---|---|---|
| `simulation_only` | Sintéticos | Demo, pruebas y evaluación técnica |
| `operational_support` | Reales | Registro y estadísticas personales autorizadas |
| `shadow_evaluation` | Reales | Evaluación invisible de un modelo candidato |
| `authoring_only` | Literatura y escenarios mínimos potencialmente seudonimizados | Construcción del catálogo RAG |

Un modelo `simulation_only` nunca puede emitir una salida para un sujeto real.

### 1.2 Estado actual verificable

A fecha de este SPEC, el repositorio contiene 4 casos reales, 7 eventos registrados, 2 eventos
severos explícitos y ningún conjunto completo de negativos verificados `[E]`. Por tanto:

```text
synthetic_reference = disponible solo para simulación
real_personal_baseline = recolectando outcomes
real_logit_challenger = no entrenable con una sola clase confirmada
rag_catalog = no listo hasta incorporar corpus y revisiones reales
```

Estas condiciones se recalculan desde los datos; no se hardcodean como estado permanente.

---

## 2. Constitución no negociable

Un cambio que viole una regla de esta sección es un bug.

1. El LLM nunca calcula riesgo, intervalo, calidad, VoI ni outcome.
2. Datos sintéticos y reales nunca se mezclan en entrenamiento, calibración o evaluación.
3. Toda predicción usa una instantánea cerrada en `as_of_at`.
4. Un dato posterior a `as_of_at` no modifica una predicción ya emitida.
5. `null`, `unknown`, ausencia, `false` y `0` son estados distintos.
6. Una sugerencia no tocada no crea observación.
7. Una sugerencia aceptada no alimenta el estimador de sugerencias.
8. Responder "nada distinto" no asigna valores a otros campos.
9. La ausencia de un reporte nunca se convierte en outcome negativo.
10. Una probabilidad real visible siempre incluye track, versión, método de intervalo y uso
    previsto; si el intervalo requerido no es estimable, la salida se abstiene. La simulación puede
    mostrar un `simulation_score`, nunca rotularlo como probabilidad clínica.
11. La abstención es una salida válida con HTTP 200.
12. Una salida abstendida no lleva banda, narrativa de riesgo ni recomendación causal.
13. Sin política de decisión validada no existen bandas operativas verde, ámbar o roja.
14. El modelo sintético nunca se usa sobre niños reales.
15. El challenger real permanece en sombra durante v0.3.0.
16. El índice RAG nunca contiene nombres, IDs, notas o historiales de menores.
17. Producción solo sirve estrategias de una versión activa del catálogo cerrado.
18. Toda estrategia activa tiene citas verificables y dos revisores distintos.
19. Feedback nunca modifica automáticamente catálogo, retriever o modelos desplegados.
20. Correcciones crean versiones; nunca sobrescriben historia.
21. Aprobación profesional, aplicación y outcome son conceptos separados.
22. Una asociación observada nunca se presenta como eficacia causal.
23. Texto libre clínico o escrito por usuarios nunca es feature, embedding ni contenido de prompt.
    Solo literatura versionada y autorizada puede entrar al índice y a prompts de autoría.
24. Toda operación con datos reales está limitada por tenant y rol.
25. El sistema se abstiene antes de fabricar una respuesta faltante.
26. Tenant y rol no bastan: todo acceso clínico exige un grant activo sobre el sujeto.
27. Faro no es monitoreo de emergencias y nunca debe retrasar protocolos urgentes o de resguardo.

---

## 3. Arquitectura objetivo

```text
apps/web
   -> apps/api
      -> packages/shared
      -> apps/api/store
      -> ml/defaults
      -> ml/form
      -> ml/prediction
      -> ml/eval
      -> rag/runtime

tools/rag_authoring
   -> rag/authoring
      -> rag/domain
      -> literatura versionada

tools/train
   -> ml/prediction
   -> ml/eval
   -> snapshots inmutables
```

Restricciones:

- `ml/` no importa `apps/`, HTTP, SQLite ni componentes React.
- `rag/authoring` no consulta la base clínica.
- `rag/runtime` no llama al LLM ni al índice vectorial.
- `apps/web` solo consume contratos publicados por la API.
- `packages/shared` no importa de `apps`, `ml` ni `rag`.

---

## 4. Tiempo, episodio y target

### 4.1 Episodio de predicción

Una sesión siempre puede cerrar y persistir observaciones. El servidor crea un
`PredictionEpisode` inmutable únicamente cuando corresponde una oportunidad primaria:

```text
FormSession.opened_at      = instante en que el servidor abre la sesión
FormSession.submitted_at   = instante en que el servidor acepta el cierre
PredictionEpisode.as_of_at = FormSession.submitted_at
prediction_at              = PredictionEpisode.as_of_at
target_start_at            = prediction_at
target_end_at              = prediction_at + 24 horas
capture_deadline_at        = prediction_at + 48 horas
```

`opened_at` fija la identidad y la política de auditoría de la sesión, pero no es el corte de la
predicción. El snapshot incluye únicamente datos con `effective_at <= as_of_at` e
`ingested_at <= as_of_at`. Los timestamps operativos los asigna el servidor; el cliente puede
declarar un tiempo efectivo sujeto a validación, pero no decide el corte.

Constantes:

- `TARGET_HORIZON_HOURS = 24` `[P]`.
- `OUTCOME_CAPTURE_LIMIT_HOURS = 48` `[P]`.
- Ventana target: `(target_start_at, target_end_at]` `[M]`.
- La captura dispone de 24 horas adicionales `[M]`.

El extremo inicial abierto impide que un hecho usado en el snapshot sea también label; el extremo
final cerrado conserva exactamente 24 horas. Las 48 horas definen solo hasta cuándo se acepta el
reporte primario.

### 4.2 Oportunidad canónica

El servidor serializa por `tenant_id, subject_id` la siguiente decisión:

```text
si no existe TargetDefinitionVersion seleccionable para sujeto real:
    cerrar sesión con prediction_status=target_definition_unavailable
    no crear PredictionEpisode ni OutcomeRequest
si existe definición y no hay episodio primario con target_end_at > submitted_at:
    crear PredictionEpisode(role=primary) y OutcomeRequest inmutable
si existe definición y hay episodio primario abierto:
    cerrar la sesión con linked_prediction_episode_id
    no crear otro episodio ni otro OutcomeRequest
```

Una nueva oportunidad puede empezar exactamente en el `target_end_at` anterior. Baseline y
evaluación incluyen solo episodios `primary`; por ello estiman tasa por oportunidad de formulario
observada, no incidencia diaria poblacional. La posible selección por completar el formulario se
declara en todo reporte.

### 4.3 Definición versionada del target

`TargetDefinitionVersion` contiene:

```text
target_definition_version
scope = tenant | demo_fixture
tenant_id nullable
question_es
severity_anchors_es
eligible_reporter_roles
eligible_source_mappings
effective_from
evidence_basis
approval_status = draft | active | retired
clinical_review_id
content_sha256
```

La etiqueta importada `intensidad="Severa (8-10)"` demuestra que esa categoría existe en el export
Bluba `[E]`; no define por sí sola cómo debe responder una persona nueva. Captura real manual exige
una versión `active` con pregunta, anclas y roles aprobados por la organización. Sin ella, el sistema
acepta fixtures demo, pero se abstiene de crear labels reales con
`target_definition_unavailable`. Cada episodio y reporte guarda la versión usada.
Activación exige un `clinical_reviewer` acreditado distinto del implementador y hash del payload
revisado.

Para `scope=tenant`, `tenant_id` es obligatorio; para `demo_fixture`, es null y todo outcome lleva
`data_origin=synthetic`. En cada scope puede existir como máximo una versión activa efectiva para un
instante. El servidor selecciona la única con `effective_from <= submitted_at` y sin retiro efectivo;
cero devuelve unavailable y más de una falla cerrado con `target_definition_ambiguous`.

### 4.4 Reporte y resolución del outcome

`OutcomeReport.value` admite `yes | no | unknown`. `OutcomeResolution.status` es distinto:

```text
pending | yes | no | unknown | conflicted
```

- Un reporte `yes` declara explícitamente un evento dentro de la ventana.
- Un reporte `no` declara explícitamente que no ocurrió el evento target durante toda la ventana.
- Un reporte `unknown` declara que la persona no puede responder; no resuelve el outcome.
- Resolución `unknown` significa que llegó el deadline sin reporte concluyente.
- Resolución `conflicted` significa que existen reportes `yes` y `no` elegibles incompatibles.
- `yes` exige `occurred_at` dentro de la ventana y `occurred_at <= reported_at`.
- `no` y `unknown` prohíben `occurred_at`.
- Un `yes` válido puede resolver antes de `target_end_at`; un `no` temprano queda provisional.
- Un reporte posterior al deadline se conserva como `late`, pero no entra al dataset primario.

Campos mínimos de `OutcomeReport`:

```text
outcome_report_id, tenant_id, prediction_episode_id
target_definition_version, reporter_actor_id, reporter_role
value, occurred_at nullable, reported_at, timing_status, data_origin
intake_channel = form | import, source_mapping_id nullable
supersedes_id nullable, ingested_at
```

`intake_channel=import` exige `source_mapping_id` incluido en `eligible_source_mappings`; formulario
lo deja null y exige un reporter role elegible.

Algoritmo de resolución sobre la proyección vigente al cutoff:

1. `yes` elegible: `timing_status in {early,on_time}` y `occurred_at` dentro del target.
2. `no` elegible: únicamente `timing_status=on_time`.
3. Si hay al menos un `yes` y un `no` elegibles, estado `conflicted` y `ever_conflicted=true`.
4. Si solo hay `yes`, estado `yes`; si solo hay `no`, estado `no`.
5. `qualifying_report_id` usa el primero por `reported_at, outcome_report_id`.
6. Sin reporte concluyente antes del deadline, estado `pending`; al llegar el deadline, `unknown`.

Cada cambio de reportes activos crea otra materialización append-only:

```text
outcome_resolution_id, tenant_id, prediction_episode_id
status, resolved_at nullable, qualifying_report_id nullable
ever_conflicted, resolution_version, ingested_at, supersedes_id nullable
```

`resolved_at=null` mientras está pending. `ever_conflicted` es monotónico entre versiones. Una
adjudicación conserva actor, decisión, razón y tiempo para operación, pero todo episodio alguna vez
conflictivo queda excluido del dataset primario v0.3.

`OutcomeRequest` es un registro inmutable de scheduling, no una máquina mutable. Su estado se deriva
de la resolución activa: pending y `now <= deadline` -> `open`; yes/no -> `reported`; conflicted ->
`conflicted`; pending cuando `now > deadline` materializa primero resolución unknown y deriva
`missing`. Una corrección recalcula resolución y estado. El inbox selecciona resolución pending,
deadline aún abierto, reporter role/capability y grant activos.

### 4.5 Estados de captura

| Momento | `timing_status` | Efecto |
|---|---|---|
| Antes de `target_end_at` | `early` | `yes` válido es elegible; `no` queda provisional |
| Entre fin y deadline, ambos inclusive | `on_time` | `yes` o `no` válido es elegible |
| Después del deadline | `late` | Auditoría, no dataset primario |
| Sin reporte concluyente al deadline | `missing` | Resolución `unknown` |

Los límites exactos son: `early` si `reported_at < target_end_at`, `on_time` si
`target_end_at <= reported_at <= capture_deadline_at`, y `late` si
`reported_at > capture_deadline_at`.

---

## 5. Contrato de datos

### 5.1 Convenciones globales

| Concepto | Valor |
|---|---|
| IDs | UUID v4 `[I]` |
| Fechas | `YYYY-MM-DD` |
| Timestamps | ISO-8601 UTC con `Z` |
| Zona de referencia | `America/Santiago` `[I]` |
| Código/API/DB | inglés `snake_case` |
| Texto visible | español de Chile |
| Ausencia | `null`/`NaN`, nunca cero implícito |
| Encoding | UTF-8 |
| Hash de contenido | SHA-256 `[I]` |

### 5.2 Observación diaria

La unidad de registro es una observación de campo, no una fila mutable con todos los campos. Una
sesión puede crear varias `FieldObservation`, cada una append-only.

Campos estructurales mínimos:

```text
field_observation_id, tenant_id, subject_id, form_session_id nullable
field_code, value nullable, source, actor_id
entry_mode, data_origin, cohort_kind
effective_at, ingested_at, local_date
source_mapping_id nullable, supersedes_id nullable
```

`effective_at` indica cuándo aplica la observación; `ingested_at` es el tiempo de servidor en que se
acepta. `local_date` se deriva de `effective_at` en `America/Santiago` y se persiste para reproducir
ventanas incluso si cambian librerías de zona horaria.

Campos diarios iniciales:

| Campo | Tipo | Valores/rango | Default v0.3 |
|---|---|---|---|
| `sleep_hours` | float | 0.0-16.0 | No |
| `sleep_quality` | enum | `restorative`, `interrupted`, `sleep_onset_difficulty`, `other` | No |
| `night_awakenings` | int | 0-15 | No |
| `wake_state` | enum | `calm_happy`, `tired_sleepy`, `irritable_crying`, `other` | No |
| `morning_support_need` | ordinal | 1-5 con anclas | No |
| `gi_status` | enum | `normal`, `constipation`, `diarrhea`, `other` | No |
| `medication_adherence` | enum | `taken`, `missed`, `not_applicable` | No |
| `food_changes` | bool | `true`, `false` | Sí |
| `routine_changes` | bool | `true`, `false` | No |
| `alertness` | enum | `low`, `calm`, `optimal`, `high`, `other` | No |
| `dysregulation_event_count` | int | 0-20, conteo observado | No |
| `daily_regulation_state` | enum | `excellent`, `stable_with_support`, `frequent_dysregulation`, `other` | No |
| `activity_participation` | ordinal | 1-5 con anclas | Sí |
| `social_interactions` | ordinal | 1-5 con anclas | Sí |
| `eating_status` | ordinal | 1-5 con anclas | Sí |
| `attendance_status` | enum | `present`, `absent`, `not_applicable` | Sí |
| `relevant_event_flag` | bool | `true`, `false` | No |
| `behavior_tags` | enum[] | catálogo versionado | No |
| `notes` | texto | máximo 500 caracteres | No |

`major_dysregulation_24h` no pertenece a la observación diaria: vive en `OutcomeReport`.

### 5.3 Categorías sin falsa precisión

Reglas de adaptación:

- `stable_with_support` no se convierte en un conteo inventado.
- `frequent_dysregulation` no se convierte en un conteo inventado.
- `attendance_status=present` no se convierte en participación `4`.
- Las categorías nominales no se convierten en una escala ordenada.
- Un modelo puede usar one-hot encoding versionado, nunca un orden ficticio.
- Toda importación conserva `raw_value`, `mapping_version` y valor canónico.
- Una categoría desconocida falla con `unmapped_source_value`; no se transforma a `null`.

### 5.4 Fuente

```text
home | therapy | school
```

En observaciones, `source` identifica el contexto de observación, no la identidad del actor, el
canal de ingesta ni una fuente bibliográfica. Es parte de `FieldObservation` y de la clave de
estimación. `source_id` queda reservado para documentos del corpus; `actor_id` y
`source_mapping_id` registran por separado quién reportó y qué adaptador se usó.

Cada campo declara sus fuentes permitidas en `packages/shared`. Una fuente no permitida no puede
elevar cobertura mediante procedencia sin valor.

Matriz inicial `[P]`:

| Campo | `home` | `therapy` | `school` |
|---|:---:|:---:|:---:|
| `sleep_hours` | Sí | No | No |
| `sleep_quality` | Sí | No | No |
| `night_awakenings` | Sí | No | No |
| `wake_state` | Sí | No | No |
| `morning_support_need` | Sí | No | No |
| `gi_status` | Sí | Sí | No |
| `medication_adherence` | Sí | Sí | No |
| `food_changes` | Sí | No | No |
| `routine_changes` | Sí | No | No |
| `alertness` | Sí | Sí | Sí |
| `dysregulation_event_count` | Sí | Sí | Sí |
| `daily_regulation_state` | Sí | Sí | Sí |
| `activity_participation` | Sí | Sí | Sí |
| `social_interactions` | Sí | Sí | Sí |
| `eating_status` | Sí | No | Sí |
| `attendance_status` | No | Sí | Sí |
| `relevant_event_flag` | Sí | Sí | Sí |
| `behavior_tags` | Sí | Sí | Sí |
| `notes` | Sí | Sí | Sí |

Cambiar esta matriz exige versión de contrato. El frontend solo muestra campos habilitados para la
fuente de la sesión.

### 5.5 Modo de entrada

```text
manual_no_default
audit_manual
default_accepted
default_edited
professional_observed
imported_observed
explicit_unknown
```

| `entry_mode` | Asigna valor | Entrena defaults | Modelo real primario |
|---|---:|---:|---:|
| `manual_no_default` | Sí | Sí | Sí |
| `audit_manual` | Sí | Sí | Sí |
| `professional_observed` | Sí | Sí, separado por fuente | Sí |
| `imported_observed` | Sí | Sí si mapping aprobado | Sí |
| `default_accepted` | Sí | No | No |
| `default_edited` | Sí | No | Sí |
| `explicit_unknown` | No | No | No |

El cliente no elige `entry_mode`. Envía la interacción y el servidor deriva el modo usando la
sesión y el `default_presentation_id`.

Precedencia de derivación:

1. Canal de importación: exige mapping aprobado y produce `imported_observed`; si no, rechaza.
2. Sesión `professional_observation`: exige rol y grant activos, no muestra defaults y produce
   `professional_observed`.
3. Interacción `unknown`: produce `explicit_unknown` sin valor.
4. Sesión auditada: una respuesta manual produce `audit_manual`.
5. `accept_default` exige presentación vigente y produce `default_accepted`.
6. `edit_default` exige presentación vigente y produce `default_edited`.
7. Cualquier valor ingresado en un campo que tuvo presentación vigente y no fue aceptado produce
   `default_edited`, aunque el cliente lo llame `manual`.
8. `manual_no_default` solo existe si ese campo/sesión nunca tuvo presentación vigente.

Combinaciones no contempladas fallan; nunca se elige el modo por prioridad implícita.

### 5.6 Origen

Los nombres no se intercambian:

```text
FieldObservation.data_origin = real | synthetic
Subject.cohort_kind = real_subject | demo_fixture
PredictionOutput.input_data_origin = real | synthetic
ModelVersion.training_data_origin = real | synthetic
deployment_mode = demo | pilot
```

Un snapshot real rechaza cualquier observación sintética. Un modelo de simulación rechaza sujetos
reales. `deployment_mode=demo` solo acepta `demo_fixture`; los exports reales se analizan offline y
no se sirven por la aplicación demo. En piloto, simulación solo existe en un sandbox administrativo
aislado y nunca comparte episodios con sujetos reales.

### 5.7 Perfil estable

`SubjectProfile` contiene únicamente atributos requeridos por matching y autorizados:

```text
sensory_profile_tags
communication_support_tags
contraindication_tags
care_mode
profile_version
effective_from
recorded_at
supersedes_id nullable
```

Los tags vienen de catálogos cerrados. No se infieren desde notas libres. Cada episodio guarda
`profile_version` y `care_mode` en su snapshot; comparaciones históricas usan el modo capturado en
cada episodio, no el perfil actual.

### 5.8 Proyección append-only al cutoff

Toda fórmula usa la misma vista `project_as_of(rows, cutoff)`:

1. Conserva filas con `ingested_at <= cutoff` y, cuando aplica, `effective_at <= cutoff`.
2. Resuelve `supersedes_id` solo con correcciones conocidas al cutoff.
3. Una cadena aporta únicamente su hoja vigente; una corrección futura no reescribe el pasado.
4. Ramas, ciclos, referencias cross-tenant o tipos incompatibles invalidan la cadena.
5. Empates de ingesta se ordenan por UUID solo para reproducir diagnóstico; dos hojas activas son
   conflicto y no se agregan silenciosamente.
6. Todo snapshot persiste los IDs exactos proyectados y nunca se recalcula.

Para un campo, fuente y `local_date`, debe quedar como máximo una observación activa. Si varias
fuentes permitidas informan el mismo campo-día, DQI puede comparar sus valores; un modelo solo usa el
campo si todos coinciden o su regla declara cómo resolverlo.

Ventanas de días calendario con cutoff de fecha `D=local_date(as_of_at)`:

```text
últimos W días, inclusivo = [D-(W-1), D]
W días previos, exclusivo = [D-W, D)
```

En ambos casos también se aplica el cutoff instantáneo y la proyección anterior.

### 5.9 Bytes canónicos y hashes

Objetos JSON se normalizan a Unicode NFC y timestamps UTC `YYYY-MM-DDTHH:mm:ss.sssZ`, luego se
serializan con RFC 8785 (JCS). Arrays que representan sets se ordenan por valor canónico; arrays con
semántica de ranking conservan orden. Filas de snapshots/datasets se ordenan por tipo de entidad y
UUID. Cada hash usa separación de dominio:

```text
SHA256("faro:<artifact>:<schema_version>\0" || canonical_bytes)
```

Esto aplica a snapshots, datasets, documentos, chunks, estrategias y payloads idempotentes. Un
`scenario_hash` clínico usa HMAC-SHA256 con secreto tenant porque el espacio de escenarios es de baja
entropía; el hash sin clave no sale de la frontera clínica.

---

## 6. Formulario inteligente

### 6.1 Dos preguntas distintas

El formulario separa:

1. **Default:** qué valor es suficientemente habitual para sugerirlo.
2. **VoI:** qué pregunta puede aportar más información a la predicción.

Una variable puede tener default confiable y, al mismo tiempo, ser importante de preguntar para
detectar una excepción.

### 6.2 Ventana limpia

Para defaults se usa la proyección al cutoff de los últimos 60 días calendario inclusivos
`[D-59,D]` `[P]`, estratificada por:

```text
tenant_id
subject_id
source
field_code
```

No se combinan contextos ni tenants. El posterior de cada candidato se calcula únicamente dentro
de ese estrato y con corte temporal en el instante que solicita la decisión.

Solo cuentan:

```text
manual_no_default
audit_manual
professional_observed
imported_observed con mapping aprobado
```

No cuentan sugerencias aceptadas o editadas, datos sintéticos, unknown ni días ausentes.

`N` es número de observaciones elegibles, no número de días de calendario.

### 6.3 Variables binarias

Para `k` ocurrencias del valor candidato en `N` observaciones:

```text
p | D ~ Beta(1 + k, 1 + N - k)
posterior_mean = (1 + k) / (2 + N)
lower = BetaPPF(0.05, 1 + k, 1 + N - k)
```

- El candidato binario es el valor con mayor conteo elegible; si `k_true=k_false`, no hay candidato.
- Prior `Beta(1,1)` `[P]`.
- Cuantil unilateral `0.05` `[P]`.
- El prior es uniforme; no se llama "máxima ignorancia".

### 6.4 Variables categóricas y ordinales

Para soporte cerrado `S={s1,...,sK}` y conteos `n1,...,nK`:

```text
alpha_j = 1 + n_j
A = sum(alpha_j)
posterior_mean_j = alpha_j / A
candidate = argmax(alpha_j)
```

Si hay empate, no hay sugerencia.

La marginal del candidato es:

```text
p_candidate | D ~ Beta(alpha_candidate, A - alpha_candidate)
lower = BetaPPF(0.05, alpha_candidate, A - alpha_candidate)
```

Aunque una escala sea ordinal, el estimador no promedia categorías ni inventa distancias. Las
anclas se conservan en la UI.

### 6.5 Continuos, conteos, texto y outcomes

En v0.3 no tienen default:

- Continuos.
- Conteos.
- Texto libre.
- Tags múltiples.
- Outcomes.

Definir tolerancias o bins sin validación introduciría decisiones no justificadas.

### 6.6 Regla de presentación

Una sugerencia se presenta solo si:

```text
lower > 0.70
AND field_code in DEFAULT_ALLOWLIST_V1
AND audit_mode = false
AND no posterior tie
```

- `DEFAULT_LOWER_THRESHOLD = 0.70` `[P]`.
- El corte es estricto: `0.70` exacto no alcanza.
- El campo permanece vacío.
- Un toque en la sugerencia crea `default_accepted`.
- Escribir otro valor crea `default_edited`.
- No tocar no crea observación.

### 6.7 Allowlist v1

```text
food_changes
activity_participation
social_interactions
eating_status
attendance_status
```

Todo campo ausente de la allowlist tiene defaults deshabilitados `[P]`.

Variables de alta señal sin default:

```text
sleep_quality
wake_state
gi_status
medication_adherence
routine_changes
alertness
daily_regulation_state
dysregulation_event_count
relevant_event_flag
```

### 6.8 Auditoría de defaults

El 10% de sesiones no muestra defaults `[P]`.

Asignación estable:

```text
bucket = HMAC_SHA256(secret, tenant_id | subject_id | local_date | policy_version) mod 1000
audit_mode = bucket < 100
```

La asignación:

- Se persiste al abrir la sesión.
- No cambia al refrescar o reabrir.
- No es predecible por el cliente.
- Produce `audit_manual`.
- Nunca se recalcula retroactivamente.

### 6.9 Bloques del formulario

El outcome pendiente es un bloque separado y no consume cupos de campos diarios. Para estos campos,
`base_slots=3` si `coverage < 0.50`; en otro caso `base_slots=2` `[P]`.

Orden exacto del plan:

1. Outcome pendiente.
2. Preguntas obligatorias por antigüedad.
3. Cuota de exploración.
4. Preguntas por VoI disponible.
5. Orden canónico para completar cupos.
6. Cola completa.

Reglas:

- Normalmente se destacan `base_slots`; si hay más campos vencidos, se amplía hasta incluirlos, con
  máximo 5 monitoreados. El límite 2/3 no rompe la garantía de antigüedad.
- Todos los campos aplicables permanecen accesibles.
- La pregunta filtro no oculta campos.
- Responder "No" solo guarda `relevant_event_flag=false`.
- Cada campo destacado crea `QuestionPresentation`; la cola no cuenta como pregunta destacada.
- Recalcular conserva preguntas ya respondidas y no vuelve a presentar la misma en la sesión.

### 6.10 Antigüedad y exploración

Campos monitoreados:

```text
sleep_quality
wake_state
gi_status
medication_adherence
daily_regulation_state
```

Prioridad de desempate `[P]`:

| Prioridad | Campo |
|---:|---|
| 1 | `sleep_quality` |
| 2 | `wake_state` |
| 3 | `gi_status` |
| 4 | `medication_adherence` |
| 5 | `daily_regulation_state` |

- "Preguntado" significa que existió `QuestionPresentation(highlighted=true)` en una sesión cuya
  fuente permitía el campo. La mera presencia en la cola no reinicia el reloj.
- En la primera sesión, campos nunca preguntados siguen la prioridad declarada. Después se ordenan
  por más días desde la última presentación, menor número de prioridad y `field_code`.
- Todo campo con al menos 7 días desde su última presentación se incluye, aunque amplíe los cupos.
- La exploración ocupa como máximo un cupo restante y nunca desplaza un vencido.
- Para cada semana ISO local:

```text
exploration_weekday = HMAC_SHA256(
  secret, tenant_id | subject_id | iso_week | policy_version
) mod 7
```

- Si existe sesión ese día, se elige entre campos aplicables no seleccionados el menos destacado en
  los 60 días inclusivos; empate por prioridad y `field_code`. Si no existe sesión o no queda cupo,
  no se compensa retroactivamente. Por eso la frecuencia es aproximadamente 1/7.
- VoI descendente llena cupos restantes; empate por prioridad y `field_code`. El resto usa orden
  canónico del catálogo.

### 6.11 Anomalía del formulario

La cola se abre si ocurre cualquiera:

```text
relevant_event_flag = true
medication_adherence = missed
daily_regulation_state = frequent_dysregulation
alertness in {low, high}
categoría actual con probabilidad predictiva personal < 0.05
valor numérico con |robust_z| >= 2.0
```

Los cortes `0.05` y `2.0` son políticas `[P]`, no umbrales clínicos universales.

La probabilidad categórica usa el posterior predictivo Dirichlet de la ventana limpia del mismo
estrato y requiere al menos `PERSONAL_MIN_OBSERVATIONS=5`. Si la categoría es `other`, hay conflicto
o falta historia, la regla queda unavailable.

Para numéricos se usa la proyección de los `PERSONAL_DEVIATION_WINDOW_DAYS=30` días previos
`[D-30,D)`, mismo sujeto, fuente y campo, con modos elegibles para modelo real:

```text
median = median(history)
MAD = median(abs(history - median))
robust_scale = (1 / NormalPPF(0.75)) * MAD
robust_z = (current - median) / robust_scale
```

`1/NormalPPF(0.75) ~= 1.4826` `[M]`. Con menos de 5 valores, `MAD=0`, conflicto o valor no
observable, `robust_z=null` y la regla no abre la cola.

---

## 7. Calidad del dato y VoI

### 7.1 Índice de calidad

```text
DQI = coverage * recency * consistency
```

`coverage` usa únicamente campos aplicables y modos de entrada:

| Modo | Peso de cobertura `[P]` |
|---|---:|
| Observación manual/auditada/profesional/importada aprobada | 1.0 |
| Default editado | 1.0 |
| Default aceptado | 0.5 |
| Unknown/ausente | 0.0 |

La ventana exacta es `[D-13,D]` después de `project_as_of`; los campos son `[P]`:

```text
DQI_WINDOW_DAYS = 14
DQI_REQUIRED_FIELDS = {
  sleep_quality,
  wake_state,
  gi_status,
  medication_adherence,
  daily_regulation_state
}
```

Todos los campos tienen el mismo peso. `medication_adherence=not_applicable` es una respuesta
presente. Para un campo `v` y día `d`:

```text
presence(v,d) = max(entry_mode_weight de observaciones válidas y fuentes permitidas ese día)
coverage = sum_v sum_d presence(v,d) / (5 * 14)
```

Los 14 días del denominador son fijos. Un sujeto nuevo no obtiene cobertura artificialmente alta
por tener un solo día de historia.

`recency`:

```text
recency = exp(-ln(2) * days_since_last_observation / 2)
```

`days_since_last_observation` es la diferencia entera entre `D` y el `local_date` más reciente de
una observación válida de los cinco campos. La vida media de 2 días es política `[P]`.
Si no existe ninguna observación válida de los cinco campos en la ventana, `recency=0`.

`consistency` compara fuentes solo cuando dos o más fuentes permitidas tienen una observación activa
del mismo campo-día. La proyección garantiza como máximo un valor por fuente. Desacuerdo normalizado:

```text
nominal/bool: 0 si valores iguales, 1 si son distintos
ordinal 1-5: abs(a-b) / 4
continuo/conteo: abs(a-b) / rango_legal
```

Para cada campo-día con solape se promedian todos los pares de fuentes. Luego:

```text
mean_disagreement = media de desacuerdos de campo-día con solape
consistency = max(0.5, 1 - mean_disagreement)
```

Sin solape, `consistency=1.0`. El DQI no resuelve el conflicto ni promedia categorías nominales;
solo mide su existencia.

El DQI describe calidad y nunca es feature predictiva. v0.3 no define un corte universal de DQI:
las abstenciones usan las condiciones explícitas de cada track. Adoptar un umbral de DQI exigiría
registrarlo como nueva política y validarlo.

### 7.2 VoI predictivo

Cuando existe un modelo condicional autorizado, el VoI es información mutua aproximada entre la
respuesta `X` y el outcome `Y`.

Para valores posibles `x_j`:

```text
q_j = P(X=x_j | historia limpia)
p_j = P(Y=1 | X=x_j, contexto)
p_bar = sum(q_j * p_j)
h(p) = -p*ln(p) - (1-p)*ln(1-p)
VoI(X) = h(p_bar) - sum(q_j * h(p_j))
```

- Unidad: nats `[M]`.
- Se define `0*ln(0)=0` `[M]`.
- Error numérico negativo se clipea a cero `[I]`.
- VoI ordena; nunca esconde.
- `q_j` es la media posterior Beta/Dirichlet sobre soporte completo usando la misma ventana limpia
  `[D-59,D]`, estrato y modos de defaults; se calcula aunque el campo no esté en la allowlist.
- Se valida `q_j >= 0`, `sum(q)=1` dentro de tolerancia numérica y `p_j in [0,1]`.
- `p_j` es una consulta condicional del modelo fijando `X=x_j` y manteniendo el resto del snapshot;
  no se describe como intervención causal.
- El output registra `q_estimator_version`, `conditional_model_version` y cutoff.
- Campo continuo, categoría no soportada, conflicto o modelo que no admite la consulta devuelve VoI
  unavailable; no se imputa.

### 7.3 Estado del VoI

```text
available
unavailable_model
unavailable_field_type
unavailable_prediction
```

Cuando no está disponible, el API devuelve `voi=null`, no cero. El formulario sigue funcionando
con outcome pendiente, antigüedad, exploración y orden canónico.

---

## 8. Predicción dual-track

### 8.1 Tracks

| Track | Datos | Uso v0.3 |
|---|---|---|
| `synthetic_reference_v021` | Sintéticos | Simulación y regresión técnica |
| `real_personal_baseline_v1` | Outcomes reales verificados | Estadística personal, no riesgo contextual |
| `real_logit_challenger_v1` | Outcomes reales verificados | Sombra únicamente |

### 8.2 Referencia sintética

El LightGBM existente se conserva para:

- Pruebas de integración.
- Demostración de abstención y VoI.
- Tests de leakage, missingness y determinismo.
- Stress tests.

Toda salida lleva `intended_use=simulation_only`. Sus bandas legacy no aparecen en sujetos reales.
La API la expone únicamente en cohortes `demo_fixture` como `simulation_score` en `[0,1]`, con
`probability=null` e `interval=null`. La UI dice que es un score de una simulación diseñada, no una
probabilidad para una persona.

### 8.3 Baseline personal real

Para outcomes de episodios primarios previos del mismo sujeto, `care_mode` y
`target_definition_version`, cuya fecha de inicio cae en `[D-59,D]` y cuya resolución era conocida
en `as_of_at` `[P]`:

```text
e = outcomes yes
n = outcomes yes + outcomes no
p | D ~ Beta(1 + e, 1 + n - e)
p_mean = (1 + e) / (2 + n)
interval = [BetaPPF(0.05), BetaPPF(0.95)]
```

Solo entran resoluciones:

- `status in {yes,no}` con `qualifying_report_id` elegible.
- `ever_conflicted=false`.
- Reales.
- Con `resolved_at <=` nuevo `as_of_at` e `ingested_at <= as_of_at`.
- Autorizados por consentimiento aplicable.

La salida declara `estimate_kind=personal_observed_episode_rate`. No se presenta como incidencia
diaria, riesgo poblacional ni efecto de las respuestas del día.

### 8.4 Challenger real

Modelo preregistrado:

```text
logit(p_t) =
    logit(p_base_t)
    + calibration_intercept
    + beta_1 * sleep_deviation_t
    + beta_2 * regulation_deviation_t
```

Predictores:

```text
sleep_disrupted_t = 1 si sleep_quality in {interrupted, sleep_onset_difficulty}
                    0 si sleep_quality = restorative
                    null si missing, unknown, other o conflicted
sleep_deviation_t = sleep_disrupted_t - tasa personal previa de sleep_disrupted

regulation_frequent_t = 1 si daily_regulation_state=frequent_dysregulation
                        0 si daily_regulation_state in {excellent, stable_with_support}
                        null si missing, unknown, other o conflicted
regulation_deviation_t = regulation_frequent_t - tasa personal previa equivalente
```

Cada tasa personal usa la proyección del mismo `subject_id`, `source` y campo en los 30 días
previos `[D-30,D)`, solo modos elegibles para el modelo real y un valor canónico por día. Requiere
al menos 5 días observados; C21 y C22 gobiernan ventana y mínimo. No combina fuentes ni convierte
conflicto en cero.

Reglas:

- Regresión logística con offset y penalización L2 definida por:

```text
eta_i = logit(p_base_i) + b0 + b1*x1_i + b2*x2_i
p_i = sigmoid(eta_i)
loss = -mean(y_i*ln(p_i) + (1-y_i)*ln(1-p_i))
       + lambda/2 * (b1^2 + b2^2)
```

- Dos predictores preregistrados; no se seleccionan con Random Forest.
- `p_base_t` entra con coeficiente fijo 1; el intercepto no se penaliza y no hay class weights ni
  estandarización adicional.
- El grid es `lambda in {0.01, 0.1, 1, 10, 100}` `[I]`; mayor `lambda` es más regularización.
- Se optimiza en `float64` con SciPy `L-BFGS-B`; versión, tolerancia, máximo de iteraciones y estado
  de convergencia se fijan antes del run en `ChallengerTrainingProtocolVersion`, cuyo hash queda en
  `TrainingRun`; no son flags libres por ejecución.
- Selección por menor Brier OOF con `LeaveOneGroupOut(subject_id)`; cada transformación, incluida la
  tasa personal, se calcula solo con historia disponible dentro del fold y al cutoff de cada fila.
- Cada partición de entrenamiento exige ambas clases. Una validación de un solo sujeto puede tener
  una clase porque Brier por fila sigue definido; el conjunto OOF agregado exige ambas.
- Empates dentro de `1e-12` eligen mayor `lambda` `[P]`.
- Elegido `lambda`, se reajusta una vez sobre todos los datos elegibles con el mismo protocolo; ese
  artefacto es el único candidato a `ModelVersion`.
- Entrenabilidad exige un plan de tamaño muestral versionado basado en Riley et al.; no se fija un
  número universal de eventos.
- Fallo de convergencia produce `TrainingRun.status=not_trainable` con razón; no crea `ModelVersion`.
- No hay promoción automática.

### 8.5 Abstención

El baseline personal se abstiene si:

```text
verified_outcomes < 5
OR unresolved_conflict = true
OR care_mode_history unavailable
```

El mínimo `5` es una política conservadora inicial `[P]`. No existe gate adicional por ancho en
v0.3: con este prior y mínimo, el antiguo corte `0.60` era inalcanzable y se retira.

`verified_outcomes` es exactamente `n` después de todos los filtros de `SPEC 8.3`.
`unresolved_conflict=true` si, en esa misma ventana `[D-59,D]`, sujeto, care mode y target version,
existe un episodio primario real con resolución activa `conflicted`. `care_mode_history unavailable`
significa que el episodio actual no tiene care mode capturado o que un outcome candidato carece del
care mode histórico de su snapshot. Conflictos o perfiles fuera de ese scope no bloquean.

El challenger se abstiene si:

```text
model_state not in {shadow, shadow_evaluated}
OR predictor missing
OR personal predictor history < 5
OR feature conflict
OR unsupported mapping
OR calibration failure
```

Aunque no abstenga internamente, el challenger permanece oculto a cuidadores en v0.3.
Estado `shadow` permite generar scores internos; `shadow_evaluated` solo se alcanza tras evaluación
prospectiva versionada y tampoco habilita exposición a familias.

### 8.6 Bandas

```text
decision_policy_version = null
risk_band = null
autonomous_action = null
```

Los cortes verde/ámbar/rojo actuales provienen de la simulación y no se trasladan a datos reales.

---

## 9. RAG clínico híbrido

### 9.1 Principio

El RAG trabaja en autoría, no en cada consulta clínica.

```text
literatura versionada
-> retrieval híbrido
-> borrador opcional del LLM local
-> verificación de citas
-> revisión de evidencia
-> revisión clínica
-> catálogo precomputado
-> runtime determinista
```

En runtime hay cero llamadas LLM `[P]`.

### 9.2 Corpus

Allowlist inicial de publicadores `[P]`:

```text
MINSAL
MINEDUC
NICE
PubMed Central
SciELO
Cochrane
```

La allowlist no implica que todo documento respalde una estrategia.

Cada documento exige:

```text
source_id
publisher
title
document_version
publication_date
retrieved_at
canonical_url
rights_basis
original_bytes_sha256
extracted_text_sha256
extraction_manifest_id
language
status
```

Sin versión, derechos y hash, el documento no se indexa.

### 9.3 Fragmentos

Cada fragmento conserva:

```text
document_version_id
locator
text
chunk_sha256
chunker_version
```

El localizador puede ser página, sección o párrafo. Una cita sin localizador verificable no puede
publicarse.

### 9.4 Recuperación de autoría

Cada `AuthoringBuildManifest` fija y hashea extractor/OCR, versiones, normalización, chunk size,
overlap, tokenizer, BM25, modelo denso, prompt, librerías y plataforma. El texto extraído se
normaliza a Unicode NFC y LF; la cita literal se verifica contra ese texto y el localizador, mientras
el hash de bytes originales conserva la procedencia.

Modos permitidos:

```text
hybrid | lexical_only
```

Pipeline inicial `hybrid`:

1. BM25 top 20 `[I]`.
2. Retrieval denso local top 20 `[I]`.
3. Reciprocal Rank Fusion con `k=60` `[I]`.
4. Top 8 fragmentos finales `[I]`.
5. Borrador opcional por LLM local.
6. Verificación automática de que cada cita es literal.
7. Revisión humana de evidencia.
8. Revisión clínica independiente.

Ranks empiezan en 1 y RRF usa:

```text
rrf_score(chunk) = sum_retrievers(1 / (60 + rank_retriever(chunk)))
```

Empates de cada retriever y del score final se resuelven por `chunk_sha256`. En
`lexical_only` se omiten pasos densos y RRF: BM25 entrega directamente top 8. El modo queda visible
en el manifest y en la revisión; nunca se descarga un modelo faltante ni se simula retrieval híbrido.

El modelo de embeddings y el LLM no se fijan hasta registrar licencia, model card, hash y pruebas
locales. Ninguno recibe datos personales.

El texto que se fragmenta, indexa o incluye en prompts procede exclusivamente de estas versiones
documentales autorizadas. Notas, mensajes y cualquier otro texto libre clínico o de usuario quedan
fuera de `document_chunks`, embeddings y prompts.

### 9.5 Estrategia versionada

`StrategyVersion` contiene:

```text
strategy_id estable
strategy_version_id
purpose_es
action_text_es
claims[{claim_id, start, end, claim_text_es, citation_ids}]
applicability_predicate
required_approver_role
allowed_executor_roles
corpus_version
evidence_review_id
clinical_review_id
effective_from
supersedes_version_id
status
content_sha256
```

Estados:

```text
draft -> evidence_reviewed -> clinical_reviewed -> active -> suspended | retired
```

Activación exige:

- `claims` no vacío, al menos una cita total y al menos una cita verificable por cada claim clínico
  o factual.
- Dos revisores distintos.
- Ninguna fuente retirada.
- Tags de contraindicación revisados; la aplicabilidad al escenario se evalúa después.
- `content_sha256` del payload canónico completo idéntico al contenido revisado.

`StrategyCitation` enlaza `claim_id`, `document_chunk_id`, `locator`, `quoted_text` y hash. La
verificación automática comprueba que `quoted_text` existe literalmente en el chunk normalizado; el
`evidence_reviewer` decide si respalda el claim. Runtime sirve exactamente `action_text_es` de la
versión activa, nunca texto recompuesto. Cada `claim_text_es` debe coincidir con
`action_text_es[start:end]`; cambios de offsets o texto invalidan el hash y las revisiones.

Toda revisión de autoría usa una entidad distinta de la review de caso:

```text
AuthoringReview:
  authoring_review_id
  object_type = target_definition | document | strategy | recommendation_set | catalog
  object_version_id
  review_kind = evidence | clinical | privacy | catalog_activation
  actor_id, accreditation_id
  decision = approved | changes_requested | rejected
  reviewed_content_sha256, reviewed_at, supersedes_id nullable
```

Es append-only. Un ID de review solo es válido si actor/accreditation tenían capability correcta al
`reviewed_at`, el hash coincide exactamente y la decisión activa es approved.

Los revisores tienen responsabilidades diferentes:

- `evidence_reviewer`: verifica fuente, fragmento, licencia, versión y correspondencia del claim.
- `clinical_reviewer`: profesional autorizado por la organización para evaluar aplicabilidad y
  seguridad contextual.

Un desarrollador no obtiene el rol `clinical_reviewer` por implementar o probar el sistema. La
organización debe registrar la política de acreditación y asignar el rol. Si no existe una persona
autorizada, ninguna `StrategyVersion` llega a `active`; el runtime se abstiene con
`clinical_review_unavailable`.

### 9.6 Catálogo y sets versionados

```text
CatalogVersion:
  catalog_version, tenant_id, corpus_version, recommendation_set_version_ids
  catalog_activation_review_id
  status, effective_from, suspended_at nullable, content_sha256

RecommendationSetVersion:
  recommendation_set_id, recommendation_set_version
  applicability_predicate
  ordered_strategy_version_ids, reviewed_priority
  clinical_review_id, status, effective_from, content_sha256
```

Ambos usan `draft -> reviewed -> active -> suspended | retired`. Un catálogo solo activa si todos
sus sets están activos; un set solo activa si todas sus estrategias están activas, su predicate y
prioridad fueron revisados y no depende de fuentes retiradas. Suspender una dependencia suspende el
set y catálogo para nuevas instancias; las instancias históricas conservan versiones.
Activar catálogo exige además `catalog_activation_review_id` aprobado sobre su hash por tenant admin
acreditado para esa capacidad.

Existe como máximo un `CatalogVersion` activo y efectivo por tenant en cada instante. P2 selecciona
la única versión con `effective_from <= as_of_at` y sin suspensión/retiro; cero produce
`catalog_not_ready`, más de una `catalog_ambiguous`. Runtime recibe esa versión explícita y vuelve a
validar scope/estado; nunca elige "la más nueva" implícitamente.

Antes del runtime, P2 deriva una razón única con esta precedencia:

```text
corpus ausente/no autorizado                         -> corpus_not_ready
versiones revisables bloqueadas solo por review clínica -> clinical_review_unavailable
dependencia antes activa ahora suspendida            -> catalog_suspended
más de un catálogo activo efectivo                   -> catalog_ambiguous
ningún catálogo activo por otra causa                -> catalog_not_ready
catálogo activo                                      -> ready
```

La razón se persiste en la instancia. `clinical_review_unavailable` no se reduce a
`catalog_not_ready`, y un estado ambiguous o suspended falla cerrado.

`ScenarioV1` tiene una única representación, sin conversión implícita:

```text
schema_version
field_values: map<field_code, enum_value>
context_tags: set<context_tag>
profile_tags: set<namespaced_profile_tag>
contraindication_tags: set<contraindication_tag>
```

`ScenarioPredicate` se usa sin variantes en sets y estrategias:

```text
required_field_values: map<field_code, allowed_values>
excluded_field_values: map<field_code, forbidden_values>
required_context_tags, excluded_context_tags
required_profile_tags, contraindication_tags
```

Matching fail-closed exige que todos los valores requeridos coincidan, ningún valor excluido
coincida, los tags requeridos sean subconjunto y los excluidos/contraindicados sean disjuntos de su
set correspondiente.

Activar un set exige `clinical_review_id` acreditado, hash de predicate/orden y comprobar sobre los
catálogos cerrados finitos que su predicate implica el predicate de cada estrategia incluida. En
runtime se evalúan de nuevo, de forma independiente, set y cada estrategia; cualquier campo, tag o
versión desconocida falla cerrado.

Sets elegibles se ordenan por `reviewed_priority`, luego
`recommendation_set_version`; estrategias conservan `ordered_strategy_version_ids`. No hay match
parcial, fuzzy ni ranking por aceptación en v0.3.

### 9.7 Escenario mínimo sin identificadores directos

Payload de matching:

```json
{
  "schema_version": "scenario-1",
  "field_values": {
    "sleep_quality": "interrupted",
    "alertness": "high"
  },
  "profile_tags": ["sensory:auditory_hypersensitive"],
  "context_tags": ["therapy"],
  "contraindication_tags": []
}
```

No contiene identidad, notas, IDs externos ni historial. Se trata como dato potencialmente
seudonimizado mientras una combinación de atributos pueda ser vinculable; no se presume anónimo.

Tags se deduplican y ordenan antes de JCS. El hash clínico sigue `SPEC 5.9`; acceso y exportación de
escenarios o solicitudes de autoría exigen los mismos grants y auditoría que otros datos clínicos.

`build_scenario(snapshot, submitted_form_session_id, scenario_schema_version)` es dominio puro de
P1 y usa esta allowlist v1 `[P]`:

```text
sleep_quality
alertness
gi_status
medication_adherence
daily_regulation_state
```

Algoritmo fail-closed:

1. Verifica snapshot cutoff, sesión enviada y `SubjectProfile.profile_version` capturado.
2. Para `field_values`, toma solo la observación activa de esa sesión y campo. Missing/unknown se
   omite; un conflicto o más de una hoja activa devuelve `scenario_unavailable_conflict`.
3. `context_tags` contiene el `source` de la sesión y solo tags cerrados explícitos de esa sesión.
4. `profile_tags` namespacea los tags sensoriales/comunicación de la profile version capturada.
5. `contraindication_tags` copia el catálogo cerrado de esa misma profile version.
6. Rechaza campos/tags desconocidos y nunca usa notes, texto, outcomes, IDs ni datos posteriores.
7. Deduplica, ordena y serializa como `ScenarioV1`; devuelve scenario, hash y builder version.

P2 no reimplementa estas reglas: llama la façade P1 y persiste su resultado o abstención.

### 9.8 Runtime

El runtime:

- Busca sets activos dentro de un `CatalogVersion` activo usando el predicate exacto.
- Evalúa fail-closed el predicate del set y de cada estrategia, incluidos valores, tags y
  contraindicaciones.
- Ordena sets por prioridad revisada y conserva el orden revisado de estrategias.
- Devuelve máximo 3 estrategias `[P]`.
- Incluye citas de las versiones exactas.
- Se abstiene si no existe match aprobado.
- Devuelve un `AuthoringRequestIntent` para escenarios no cubiertos.

No redacta texto nuevo ni escribe en DB. P2 persiste la decisión al crear el episodio y deduplica la
solicitud por `tenant_id, subject_id, scenario_hash, catalog_version, status=open`.

`AuthoringRequest` contiene ID, tenant, subject, prediction episode, hash, versión y payload canónico
cifrado del escenario mínimo, motivo, catálogo consultado, timestamps y estado; vive en la DB
clínica. Solo una
exportación humana autorizada y auditada puede convertirla en input seudonimizado del entorno de
autoría.

Acceder con grant no autoriza uso secundario. Exportar exige consentimiento separado o base legal
institucional documentada en `AuthoringUseAuthorization`. El curador redacta dentro de la frontera
clínica una consulta generalizada; un privacy reviewer certifica que no conserva atributos de caso.
Solo esa consulta y un ID de curaduría aleatorio llegan a BM25, embeddings o LLM. El escenario
original, su HMAC, tenant, sujeto e instancia nunca salen ni entran a modelos. Revocación cierra
requests pendientes; si una exportación no puede certificarse como general e irreversible, suspende
los builds dependientes.

### 9.9 Feedback y mejora

El feedback produce métricas y propuestas de revisión. No cambia producción directamente.

```text
rechazo repetido -> cola de curaduría
edición profesional de caso -> HumanPlanVersion + propuesta de curaduría
fuente faltante -> solicitud de corpus
outcomes -> evaluación descriptiva por versión
```

Solo el workflow de autoría puede convertir una propuesta de curaduría en `StrategyVersion draft`;
una edición de caso nunca modifica ni crea directamente catálogo productivo.

`acceptance_rate` no modifica el ranking productivo en v0.3 `[P]`. Puede aparecer en reportes y
priorizar revisión humana.

---

## 10. Revisión humana y volante

### 10.1 Instancia de recomendación

Al crear un episodio, P2 llama al runtime puro y persiste una `RecommendationInstance` inmutable en
la misma transacción. Los GET posteriores solo leen esa instancia:

```text
recommendation_instance_id
prediction_episode_id
scenario_hash
catalog_version nullable
corpus_version nullable
strategy_version_ids
created_at
runtime_status = matched | abstained
abstention_reasons
```

La ausencia de una review activa significa `pending`; `review_status` no se guarda ni muta en la
instancia. Una instancia abstendida puede no contener estrategias y mantiene su razón. Repetir el GET
devuelve el mismo envelope persistido; el determinismo de dominio se verifica sobre escenario,
versiones, estrategias y texto, no sobre IDs generados entre episodios distintos.

### 10.2 Decisión profesional

```text
approved
rejected
human_plan_substituted
not_applicable
deferred
```

Reglas:

- Cada `RecommendationReview` identifica `recommendation_instance_id` y exactamente un
  `strategy_version_id`; la review se hace por estrategia, no por set completo.
- Guarda `review_id`, decisión, `reviewed_by`, `reviewed_at`, `supersedes_id` y
  `human_plan_version_id nullable`.
- Una recomendación sin review activa está pending y solo la ve un profesional con grant.
- La familia solo ve estrategias con review activa `approved` y cuyo
  `required_approver_role` cumplía el actor.
- Crear `approved` o `human_plan_substituted` exige que el reviewer cumpla
  `required_approver_role` de la estrategia; el serializer vuelve a verificarlo para ambos tipos.
- `deferred` puede ser superseded por una decisión posterior; no cuenta como aceptación.
- Una edición crea `human_plan_substituted` y una `HumanPlanVersion` inmutable, nunca modifica el
  catálogo.
- Un plan humano no hereda las citas RAG.
- `HumanPlanVersion` guarda texto, autor, tiempo, hash, versión y `allowed_executor_roles`, y queda
  enlazado a la review. Sus roles solo pueden ser un subconjunto de los de la estrategia sustituida.
- Antes de aceptar una review favorable o serializar un item a caregiver, el servidor revalida que
  strategy, set, catalog y fuentes exactas sigan activos. Si alguna dependencia está suspendida, la
  instancia deriva `non_actionable=dependency_suspended`; conserva historia, pero no admite nueva
  aprobación ni exposición.

### 10.3 Ejecución

La aprobación no prueba que se aplicó. Se registra por separado:

```text
applied | not_applied | unknown
```

Si se aplicó, se guarda actor y `applied_at`.

`StrategyExecution` identifica instancia y exactamente uno entre `strategy_version_id` y
`human_plan_version_id`; además guarda estado, actor, `recorded_at`, `applied_at nullable` y
`supersedes_id`. El actor debe cumplir `allowed_executor_roles` del objeto referenciado y tener grant
sobre el sujeto.
`recorded_at` es de servidor; `applied_at` puede declararse retrospectivamente, nunca ser futuro
respecto de `recorded_at`, y no altera timestamps de review u outcome.
Antes de registrar una nueva aplicación se revalida la cadena activa. Una suspensión devuelve 409
`recommendation_dependency_suspended`; ejecuciones ya ocurridas se conservan solo como historia.

Para análisis de exposición, una ejecución `applied` es elegible solo si:

```text
recommendation.created_at <= review.reviewed_at <= execution.applied_at
execution.applied_at <= target_end_at
si outcome=yes: execution.applied_at < outcome.occurred_at
si execution referencia estrategia: review activa decision=approved
si execution referencia plan humano: review activa decision=human_plan_substituted
```

Aplicaciones tardías o reportadas retrospectivamente se conservan, pero no se atribuyen al outcome
de esa ventana.

### 10.4 Outcome

Se mantienen separados:

| Concepto | Entidad |
|---|---|
| Preferencia profesional | `RecommendationReview` |
| Exposición a estrategia | `StrategyExecution` |
| Resultado observado | `OutcomeReport` |

`approved + no event` no demuestra eficacia. Los reportes de v0.3 son asociativos y descriptivos.

### 10.5 Volante

```text
observación real
-> snapshot de predicción
-> recomendación versionada
-> revisión profesional
-> ejecución
-> outcome
-> snapshot de dataset
-> training run candidato
-> evaluación
-> aprobación manual futura
```

Reglas:

- Snapshots son inmutables y hasheados.
- Cada snapshot registra observaciones, outcomes y consentimientos incluidos.
- Revocación excluye al sujeto de snapshots futuros.
- Datos sintéticos y reales usan snapshots separados.
- No hay fine-tuning del redactor en v0.3.
- Un nuevo evento puede crear un candidato, nunca desplegarlo.

---

## 11. API v0.3

Base:

```text
/api/v1
application/json
```

### 11.1 Rutas de producto

| Método | Ruta | Resultado |
|---|---|---|
| POST | `/form-sessions` | Abre sesión y fija auditoría |
| POST | `/form-sessions/{id}/answers` | Añade respuesta y recalcula orden |
| POST | `/form-sessions/{id}/submit` | Cierra y crea o enlaza episodio primario |
| GET | `/prediction-episodes/{id}` | Devuelve outputs autorizados |
| GET | `/outcome-requests` | Lista outcomes pendientes del actor |
| POST | `/prediction-episodes/{id}/outcome-reports` | Reporta yes/no/unknown |
| GET | `/prediction-episodes/{id}/recommendations` | Devuelve catálogo precomputado |
| GET | `/recommendation-instances?review_status=pending` | Inbox profesional autorizado |
| POST | `/recommendation-instances/{id}/reviews` | Registra decisión por estrategia |
| POST | `/recommendation-instances/{id}/executions` | Registra aplicación por estrategia/plan |
| GET | `/evaluation/{model_version}` | Reporte versionado |

La autoría de corpus, catálogo y entrenamiento usa CLI local en v0.3, no endpoints públicos.

### 11.2 Idempotencia y concurrencia

- Todo POST exige `Idempotency-Key` `[I]` con scope
  `(tenant_id, actor_id, method, normalized_concrete_path, key)`. El path concreto incluye todos los
  IDs normalizados; no se usa solo el route template.
- La misma clave y payload devuelve la misma respuesta.
- La misma clave con payload distinto devuelve HTTP 409.
- El hash del request usa `SPEC 5.9` sobre path params, query canónica y body. Un replay vuelve a
  autorizar rol, accreditation, grant, consent y capacidad de operación. Si ya no son válidos
  responde 403, no revela la respuesta histórica.
- Recursos con revisión usan `If-Match`.
- Conflicto de revisión devuelve HTTP 409.
- Lotes se confirman en una sola transacción.

### 11.3 Sesión de formulario

```json
{
  "form_session_id": "uuid",
  "subject_id": "uuid",
  "source": "home",
  "session_kind": "caregiver_daily",
  "opened_at": "2026-08-25T19:55:00Z",
  "audit_mode": false,
  "form_policy_version": "form-0.3.0",
  "voi_status": "unavailable_model",
  "highlighted": [],
  "tail": []
}
```

Una pregunta puede incluir:

```json
{
  "field_code": "food_changes",
  "reason": "staleness",
  "voi_nats": null,
  "default": {
    "presentation_id": "uuid",
    "value": false,
    "candidate_count": 36,
    "posterior_mean": 0.8409,
    "lower_bound": 0.7431,
    "n_observations": 42,
    "estimator_version": "defaults-0.3.0"
  }
}
```

Interacciones válidas:

```text
manual | accept_default | edit_default | unknown
```

Submit devuelve `status=episode_created|episode_linked|target_definition_unavailable`,
`prediction_episode_id nullable` y `linked_prediction_episode_id nullable`. Solo el primer estado
crea snapshot, outputs, recomendación y outcome request; el segundo referencia los ya persistidos y
el tercero no fabrica un target.

### 11.4 Outcome

El cliente envía `value` y, solo para `yes`, `occurred_at`. El servidor toma actor, rol, tenant,
`reported_at`, target y definición desde contexto autorizado; deriva `timing_status` y devuelve por
separado el reporte creado y la resolución actual. El rol debe estar permitido por la definición y
tener grant activo. `unknown` explícito y `no` temprano dejan
`resolution.status=pending`. Correcciones usan un nuevo POST con `supersedes_id` y la misma
autorización.

### 11.5 Predicción

Toda salida contiene:

```text
track_id
intended_use
status = ok | abstained | unavailable
estimate_kind
probability nullable
simulation_score nullable
interval nullable
abstention_reasons
model_version
input_data_origin
interval_method nullable
```

`confidence` no forma parte del contrato porque no tiene una semántica única entre tracks. Una
abstención exige `probability=null`, `simulation_score=null`, `interval=null` e
`interval_method=null`; `collecting_data` se representa como razón de abstención. Un baseline real
visible con `status=ok` exige probabilidad, intervalo y método no nulos. Una simulación `ok` exige
`simulation_score`, mantiene probabilidad/intervalo nulos y solo se muestra en demo. Los outputs
internos del challenger en sombra pueden guardar score sin intervalo, pero nunca se exponen.

### 11.6 Recomendación

Una respuesta exitosa incluye `recommendation_instance_id`, versiones y una lista union `items`.
El JSON siguiente ilustra la forma con una cita de fixture demo, no afirma una fuente clínica real:

```json
{
  "status": "matched",
  "recommendation_instance_id": "uuid",
  "catalog_version": "catalog-0.3.0",
  "corpus_version": "corpus-sha256",
  "items": [
    {
      "item_type": "strategy",
      "strategy_version_id": "uuid",
      "review_status": "pending",
      "action_text_es": "Texto exacto revisado.",
      "citations": [
        {
          "citation_id": "uuid",
          "claim_id": "uuid",
          "locator": "section 2, paragraph 3",
          "quoted_text": "Fragmento literal verificado.",
          "canonical_url": "https://example.org/versioned-source"
        }
      ]
    }
  ]
}
```

El ejemplo corresponde a un profesional autorizado. El serializer aplica actor y grants: un
caregiver recibe strategies con review activa `approved` y, para `human_plan_substituted`, un item
`{item_type:"human_plan", human_plan_version_id, action_text_es, citations:[]}`. Mientras todo esté
pending devuelve `status=awaiting_professional_review` e `items=[]`. Nunca filtra solo en frontend.

Si no existe corpus o match aprobado:

```json
{
  "status": "abstained",
  "recommendation_instance_id": "uuid",
  "catalog_version": null,
  "corpus_version": null,
  "reasons": ["corpus_not_ready"],
  "items": []
}
```

### 11.7 Errores

```json
{
  "error": {
    "code": "stable_machine_code",
    "message_es": "Mensaje sanitizado.",
    "request_id": "uuid"
  }
}
```

La abstención no usa el envelope de error.

---

## 12. Persistencia

### 12.1 Tablas mínimas de demo

```text
tenants
users
user_roles
professional_accreditations
subjects
subject_profiles
subject_access_grants
consents
form_sessions
default_presentations
question_presentations
field_observations
source_mappings
prediction_episodes
feature_snapshots
prediction_outputs
target_definition_versions
outcome_requests
outcome_reports
outcome_resolutions
outcome_adjudications
document_versions
document_chunks
authoring_build_manifests
authoring_reviews
corpus_versions
strategies
strategy_versions
strategy_citations
recommendation_sets
catalog_versions
recommendation_instances
recommendation_reviews
human_plan_versions
strategy_executions
authoring_requests
authoring_use_authorizations
dataset_snapshots
training_runs
model_versions
evaluation_reports
audit_events
idempotency_keys
```

### 12.2 Reglas de persistencia

- Observaciones, outcomes, revisiones, ejecuciones, planes humanos, grants, acreditaciones,
  consentimientos, authoring authorizations y auditoría son append-only.
- Una corrección usa `supersedes_id`.
- No se borra historia con `UPDATE` destructivo.
- Foreign keys activas.
- JSON solo para payloads validados y versionados.
- Cada migración tiene `up` y prueba sobre una base anterior.
- Una transacción cubre cada comando de dominio completo.

### 12.3 Demo y piloto

Demo:

```text
FARO_MODE=demo
database=SQLite
bind=127.0.0.1
WAL=true
real_network_access=false
authentication=preseeded_fictional_local_session
allowed_cohort=demo_fixture
```

Piloto:

```text
FARO_MODE=pilot
database=PostgreSQL 16+
authentication=OIDC
authorization=tenant-scoped RBAC + subject grants
transport=TLS 1.2+
audit=append-only
```

SQLite en modo piloto bloquea el arranque.
Un sujeto `real_subject` en modo demo también bloquea la operación.

---

## 13. Seguridad, privacidad y consentimiento

Roles mínimos:

```text
caregiver
professional
clinical_reviewer
evidence_reviewer
privacy_reviewer
model_evaluator
tenant_admin
auditor
```

### 13.1 Contratos de autorización

```text
Consent:
  consent_id, tenant_id, subject_id, grantor_actor_id
  purpose = operational_support | secondary_model_use | authoring_generalization
  policy_version, granted_at, valid_from, valid_until nullable
  revoked_at nullable, status, supersedes_id nullable

ProfessionalAccreditation:
  accreditation_id, tenant_id, actor_id
  capabilities: set<subject_care | target_review | strategy_review |
                    evidence_review | privacy_review | catalog_activation | model_evaluation>
  credential_policy_version, issuer_actor_id
  valid_from, valid_until nullable, revoked_at nullable, status, supersedes_id nullable

SubjectAccessGrant:
  subject_access_grant_id, tenant_id, subject_id, actor_id
  capabilities: set<subject_read | daily_observation_write | form_submit |
                    outcome_report | recommendation_review | execution_record | evaluation_read>
  issuer_actor_id, valid_from, valid_until nullable
  revoked_at nullable, status, supersedes_id nullable

AuthoringUseAuthorization:
  authorization_id, tenant_id, subject_id, authoring_request_id
  basis_type = consent | institutional_legal_basis
  consent_id nullable, legal_basis_version nullable
  scope = generalize_query_only
  approved_by_privacy_reviewer, approved_at, valid_from
  valid_until nullable, revoked_at nullable, status, supersedes_id nullable
```

Estos contratos son append-only. En un cutoff son activos solo si la hoja proyectada tiene
`status=active`, `valid_from <= cutoff < valid_until` cuando existe límite y no hay revocación
efectiva. El purpose/capability/scope debe coincidir literalmente con la operación. Target exige
`target_review`, estrategia/set `strategy_review`, evidencia `evidence_review`, export
`privacy_review`. Consentimientos y bases no se sustituyen entre purposes.

Matriz mínima de operación:

| Operación | Rol además del grant | Capability |
|---|---|---|
| Leer sujeto/formulario | caregiver o professional acreditado | `subject_read` |
| Escribir observación diaria | caregiver o professional acreditado | `daily_observation_write` |
| Cerrar formulario | caregiver o professional acreditado | `form_submit` |
| Reportar outcome | rol permitido por target definition | `outcome_report` |
| Revisar recomendación | `required_approver_role` acreditado | `recommendation_review` |
| Registrar ejecución | rol permitido por item | `execution_record` |
| Leer evaluación clínica | model_evaluator o professional acreditado | `evaluation_read` |

`tenant_admin` puede emitir/revocar grants, pero no obtiene lectura clínica sin su propio grant.

### 13.2 Reglas

- `tenant_id` es obligatorio en toda entidad clínica.
- Toda consulta o lista de sujeto verifica tenant, rol, acreditación aplicable y
  `SubjectAccessGrant` activo; pertenecer al tenant no concede acceso a todos sus sujetos.
- Un caregiver requiere vínculo vigente con el sujeto. Un professional requiere acreditación
  organizacional versionada y asignación vigente al care team del sujeto.
- Grants guardan sujeto, actor, capacidad, `valid_from`, `valid_until`, emisor y revocación. Listas se
  filtran en DB por grants; no se cargan filas prohibidas para filtrarlas en aplicación.
- Cross-tenant o same-tenant/wrong-subject responde 403 y registra auditoría.
- Logs técnicos no contienen payload clínico ni notas.
- Referencias externas se cifran en piloto.
- El corpus vive separado del almacenamiento clínico.
- No se envían datos personales a servicios LLM externos.
- Uso secundario para modelos exige consentimiento separado, explícito y revocable.
- Uso de escenarios para curaduría/autoría exige `AuthoringUseAuthorization` separado; grants no lo
  sustituyen y solo consultas generalizadas certificadas salen de la frontera clínica.
- Cada inicio de training/evaluation vuelve a comprobar `secondary_model_use` activo para todos los
  sujetos del snapshot. Un snapshot con revocación posterior sigue inmutable para auditoría, pero no
  puede alimentar un run nuevo: se deriva otro snapshot o el run se bloquea.
- Una revocación pone modelos/evaluaciones reales dependientes en `suspended_for_consent_review` para
  nuevos usos. Se retienen cifrados solo según política legal/auditoría; reactivación exige decisión
  institucional documentada o retraining sobre snapshot elegible. No afecta artefactos sintéticos.
- Sin política institucional de retención, el modo piloto no arranca.
- Un payload sin nombre puede seguir siendo dato seudonimizado; no se llama anónimo por defecto.
- La UI muestra permanentemente que Faro no monitorea emergencias. En entrada, abstención,
  estimaciones y recomendaciones indica no esperar una alerta y seguir de inmediato protocolos
  locales de emergencia o resguardo ante peligro.

---

## 14. Evaluación

### 14.1 Simulación

Puede demostrar:

- Determinismo.
- Ausencia de leakage implementado.
- Contratos.
- Missingness.
- Stress tests.
- Integración.

No demuestra eficacia clínica.

### 14.2 Dataset real primario

Incluye solo:

```text
episode_role=primary
input_data_origin=real
resolution.status in {yes,no}
resolution.ever_conflicted=false
qualifying report elegible según SPEC 4.4
consent compatible
una única target_definition_version exacta por dataset/reporte
snapshot cutoff=target_start_at y label estrictamente posterior
```

### 14.3 Métricas

```text
Brier score
average precision
AUC-ROC secundaria
calibration intercept
calibration slope
decision coverage
abstention rate por razón
métricas por fuente y grupos disponibles
```

Reglas:

- Se usa `sklearn.metrics.average_precision_score`; no implementación casera.
- Bootstrap agrupado por niño, nunca por fila.
- Preprocesamiento y selección viven dentro del fold.
- Un fold sin ambas clases no produce AUC.
- Cada métrica informa dataset hash, origen, modelo y limitaciones.
- Con una sola clase solo se reportan conteos y completitud.
- Las métricas sintéticas llevan `simulation_only` visible.
- `alert-budget recall` no se calcula en v0.3 porque no existe política de decisión ni definición de
  alerta; añadirlo exige versionar ambas.

### 14.4 Protocolo reproducible v1

- Evaluación de desarrollo anidada: outer `LeaveOneGroupOut(subject_id)` predice exactamente una vez
  por episodio. Dentro de cada outer train, un inner `LeaveOneGroupOut` selecciona `lambda` por Brier
  OOF; luego se reajusta en todo el outer train y predice el sujeto outer. Ningún outcome outer
  actual o futuro participa en fit o selección. Para construir `p_base_i` y tasas personales de un
  episodio outer se permite únicamente historia del mismo sujeto con `resolved_at <= as_of_at_i`;
  esos labels revelados derivan features/offset de ese landmark, pero nunca entrenan coeficientes ni
  eligen lambda. El protocolo persiste el reveal schedule y evalúa solo landmarks que cumplen mínimos
  históricos. Si un outer train o su inner protocol no es entrenable, queda `not_estimable`.
- La agregación outer OOF calcula métricas solo para una `target_definition_version` exacta. Versiones
  distintas producen datasets y reportes separados; v0.3 no define compatibilidad para pooling.
- Brier se compara con el baseline OOF correspondiente; average precision y AUC usan scikit-learn.
- Calibración ajusta `y ~ intercept + slope*logit(p_oof)` por máxima verosimilitud sin penalización;
  no convergencia, una clase o probabilidades no válidas produce `not_estimable`.
- Intervalos: 2.000 bootstraps por clusters de sujeto, seed 42, percentiles 5 y 95. Cada réplica
  remuestrea sujetos con reemplazo e incluye todas sus filas. Réplicas sin soporte se omiten; si
  menos de 80% son válidas, no se publica intervalo.
- `decision_coverage = outputs status=ok / episodios primarios elegibles`; se reporta también cada
  razón de abstención sobre el mismo denominador.
- Métricas de grupo se suprimen salvo que el grupo tenga al menos 10 sujetos, 5 outcomes `yes` y 5
  `no`; los conteos pequeños tampoco se muestran indirectamente.
- `EvaluationProtocolVersion` registra splits, hashes, versiones de librería, seed, método de
  intervalo, reglas de estimabilidad y cualquier tolerancia. Cambiar una regla crea otra versión.
- Estas métricas de desarrollo no cambian el modelo a `shadow_evaluated`. Esa transición exige un
  periodo prospectivo temporal, preregistrado antes de observar outcomes, con dataset separado del
  usado para selección de lambda.

### 14.5 Recomendaciones

Se reportan por separado:

```text
review acceptance
execution rate
outcome completeness
outcome association by strategy version
corpus gaps
rejection reasons
```

Ninguna tabla usa la palabra "eficacia" sin diseño causal aprobado.
Las asociaciones de outcome incluyen solo exposiciones cronológicamente elegibles según `SPEC 10.3`
y declaran confusión por indicación y selección profesional.

---

## 15. Registro de constantes

| ID | Constante | Valor | Clase |
|---|---|---:|---|
| C01 | `SPEC_VERSION` | `0.3.0` | `[I]` |
| C02 | `API_PREFIX` | `/api/v1` | `[I]` |
| C03 | `REFERENCE_TIMEZONE` | `America/Santiago` | `[I]` |
| C04 | `TARGET_HORIZON_HOURS` | 24 | `[P]` |
| C05 | `OUTCOME_CAPTURE_LIMIT_HOURS` | 48 | `[P]` |
| C06 | `DEFAULT_WINDOW_DAYS` | 60 | `[P]` |
| C07 | `DEFAULT_PRIOR_PER_CATEGORY` | 1 | `[P]` |
| C08 | `DEFAULT_LOWER_QUANTILE` | 0.05 | `[P]` |
| C09 | `DEFAULT_LOWER_THRESHOLD` | 0.70 estricto | `[P]` |
| C10 | `DEFAULT_AUDIT_RATE` | 0.10 | `[P]` |
| C11 | `FORM_HIGHLIGHTED_DEFAULT` | 2 | `[P]` |
| C12 | `FORM_HIGHLIGHTED_LOW_COVERAGE` | 3 | `[P]` |
| C13 | `LOW_COVERAGE_THRESHOLD` | 0.50 | `[P]` |
| C14 | `STALENESS_CEILING_DAYS` | 7 | `[P]` |
| C15 | `EXPLORATION_PERIOD` | 1 weekday HMAC por semana ISO | `[P]` |
| C16 | `CATEGORICAL_ANOMALY_PROBABILITY` | 0.05 | `[P]` |
| C17 | `ROBUST_Z_ANOMALY` | 2.0 | `[P]` |
| C18 | `BASELINE_WINDOW_DAYS` | 60 | `[P]` |
| C19 | `BASELINE_MIN_OUTCOMES` | 5 | `[P]` |
| C20 | `BASELINE_MAX_INTERVAL_WIDTH` | `null` (gate retirado) | `[P]` |
| C21 | `PERSONAL_DEVIATION_WINDOW_DAYS` | 30 | `[P]` |
| C22 | `PERSONAL_MIN_OBSERVATIONS` | 5 | `[P]` |
| C23 | `CHALLENGER_MAX_PREDICTORS` | 2 preregistrados | `[P]` |
| C24 | `CHALLENGER_L2_GRID` | `{0.01,0.1,1,10,100}` | `[I]` |
| C25 | `RAG_LEXICAL_TOP_K` | 20 | `[I]` |
| C26 | `RAG_DENSE_TOP_K` | 20 | `[I]` |
| C27 | `RAG_RRF_K` | 60 | `[I]` |
| C28 | `RAG_FINAL_CHUNKS` | 8 | `[I]` |
| C29 | `RUNTIME_LLM_CALLS` | 0 | `[P]` |
| C30 | `MAX_RUNTIME_STRATEGIES` | 3 | `[P]` |
| C31 | `STRATEGY_REQUIRED_DISTINCT_REVIEWERS` | 2: evidence + clinical | `[P]` |
| C32 | `PRODUCTION_ACCEPTANCE_RERANK_WEIGHT` | 0 | `[P]` |
| C33 | `HASH_ALGORITHM` | SHA-256 | `[I]` |
| C34 | `OFFLINE_RANDOM_SEED` | 42 | `[I]` |
| C35 | `PILOT_DATABASE` | PostgreSQL 16+ | `[I]` |
| C36 | `MIN_TLS_VERSION` | 1.2 | `[I]` |
| C37 | `DECISION_POLICY_VERSION` | `null` | `[P]` |
| C38 | `DQI_WINDOW_DAYS` | 14 | `[P]` |
| C39 | `DQI_RECENCY_HALF_LIFE_DAYS` | 2 | `[P]` |
| C40 | `DQI_ACCEPTED_DEFAULT_WEIGHT` | 0.5 | `[P]` |
| C41 | `DQI_CONSISTENCY_FLOOR` | 0.5 | `[P]` |
| C42 | `BASELINE_LOWER_QUANTILE` | 0.05 | `[P]` |
| C43 | `BASELINE_UPPER_QUANTILE` | 0.95 | `[P]` |
| C44 | `CHALLENGER_TIE_TOLERANCE` | `1e-12` | `[I]` |
| C45 | `EVAL_BOOTSTRAP_REPLICATES` | 2000 | `[I]` |
| C46 | `EVAL_INTERVAL_LEVEL` | 0.90 | `[P]` |
| C47 | `EVAL_MIN_VALID_BOOTSTRAP_FRACTION` | 0.80 | `[P]` |
| C48 | `GROUP_METRIC_MIN_SUBJECTS` | 10 | `[P]` |
| C49 | `GROUP_METRIC_MIN_POSITIVES` | 5 | `[P]` |
| C50 | `GROUP_METRIC_MIN_NEGATIVES` | 5 | `[P]` |

El registro cubre decisiones numéricas normativas compartidas. Bounds de schema, códigos HTTP y
parámetros internos de una librería fijados dentro de un manifest versionado no se duplican aquí;
sí deben registrarse en su contrato o manifest y quedar hasheados.

No son constantes clínicas:

- Pesos causales del generador sintético.
- Cortes legacy verde/ámbar/rojo.
- Tasas observadas de aceptación.
- Supuesta eficacia de estrategias.

---

## 16. Máquinas de estado

| Entidad | Transiciones válidas |
|---|---|
| `FormSession` | `draft -> submitted`, `draft -> abandoned`, `draft -> expired` |
| `PredictionEpisode` | `pending -> completed|failed`; estados por track viven en `PredictionOutput` |
| `TargetDefinitionVersion` | `draft -> active -> retired` |
| `OutcomeRequest` | scheduling inmutable; `open|reported|conflicted|missing` se deriva de resolución activa y reloj |
| `OutcomeResolution` | materialización append-only derivada: cualquier status puede seguir a otro tras corrección; `ever_conflicted` nunca vuelve a false |
| `DocumentVersion` | `draft -> verified -> indexed -> active`, `active -> superseded|withdrawn` |
| `StrategyVersion` | `draft -> evidence_reviewed -> clinical_reviewed -> active -> suspended|retired` |
| `RecommendationSetVersion` | `draft -> reviewed -> active -> suspended|retired` |
| `CatalogVersion` | `draft -> reviewed -> active -> suspended|retired` |
| `RecommendationInstance` | `created` terminal; review se deriva de eventos separados |
| `TrainingRun` | `created -> running -> completed|not_trainable|failed` |
| `ModelVersion` | `candidate -> validated_offline -> shadow -> shadow_evaluated|rejected`; si `training_data_origin=real`, cualquier estado no terminal -> `suspended_for_consent_review -> retired` |
| `EvaluationReport` | `draft -> published`; real `published -> suspended_for_consent_review -> retired` |
| `Consent` | `active -> revoked|expired` |
| `SubjectAccessGrant` | `active -> revoked|expired` |
| `ProfessionalAccreditation` | `active -> revoked|expired` |
| `AuthoringUseAuthorization` | `active -> revoked|expired` |

No existe transición automática a champion operativo en v0.3.
Una suspensión por consentimiento no reactiva la misma versión. Una decisión institucional conserva
el artefacto solo para auditoría; uso futuro exige nuevo snapshot/run y nueva ModelVersion/Report.

---

## 17. Invariantes verificables

1. Un default no tocado produce cero observaciones.
2. `default_accepted` no entra al estimador de defaults ni al modelo real primario.
3. `default_edited` no entra al estimador de defaults.
4. Una sesión auditada no devuelve defaults.
5. Reabrir una sesión no cambia `audit_mode`.
6. Un empate posterior devuelve `default=null`.
7. `lower=0.70` no muestra sugerencia.
8. Responder el filtro con "No" no crea observaciones para la cola.
9. VoI no disponible devuelve `null`, no cero.
10. `highlighted + tail` conserva todos los campos aplicables.
11. Datos o correcciones posteriores a `as_of_at` no alteran el snapshot ni su proyección.
12. Requests idempotentes reautorizados devuelven el mismo recurso.
13. Sin target activo no nace episodio/outcome real; con target no hay primarios solapados y un `yes` temprano válido resuelve.
14. Un `no`/`unknown` temprano mantiene `pending`; al deadline sin conclusión pasa a `unknown`, nunca a `no`.
15. Reportes incompatibles producen `conflicted`.
16. Un outcome `late` queda fuera del dataset primario.
17. Una fila sintética hace fallar un snapshot real.
18. El modelo sintético rechaza sujetos reales.
19. El challenger falla si una partición de entrenamiento o el OOF agregado tiene una sola clase.
20. Un baseline con menos de 5 outcomes abstiene.
21. Una abstención no produce banda ni narrativa verde.
22. Ningún prompt o índice contiene IDs o notas clínicas.
23. Una estrategia con claims/citas vacíos, texto no revisado o claim sin cita no puede activarse.
24. Una cita que no coincide con el fragmento hasheado bloquea activación.
25. Una persona no puede completar ambas revisiones.
26. Runtime no invoca LLM, embeddings ni store; devuelve una decisión pura.
27. Feedback no modifica el catálogo activo.
28. Una fuente retirada suspende dependencias; instancias históricas quedan visibles pero no accionables.
29. Un plan humano no muestra citas del RAG.
30. SQLite en modo piloto bloquea el arranque.
31. Una consulta cross-tenant o same-tenant sin grant responde 403 y genera auditoría.
32. Evaluación real separa target versions, reautoriza consentimiento al run y excluye sintéticos, unknown, ever-conflicted, tardíos y `no` tempranos.
33. Cada métrica informa origen, dataset hash y modelo.
34. Métricas sintéticas muestran `simulation_only`.
35. Ningún adaptador convierte categorías en conteos o escalas ficticias.

---

## 18. Fuera de alcance

v0.3 no implementa:

- Diagnóstico o prescripción.
- Promoción automática de modelos.
- Fine-tuning del LLM.
- LLM en runtime clínico.
- RAG sobre historiales personales.
- Generación libre de estrategias.
- Ranking productivo automático por aceptación.
- Inferencia causal de eficacia.
- Modelo individual por niño.
- Voz, Telegram o PWA.
- Bandas reales de riesgo sin política validada.
- Uso de notas libres como features.
- Piloto con datos identificables sobre SQLite.

---

## 19. Control de cambios

Un cambio normativo exige:

1. Propuesta con clase `[M]`, `[E]`, `[P]` o `[I]`.
2. Edición de este archivo y de los contratos afectados.
3. Actualización de tests de invariantes.
4. Incremento semver.
5. Acuerdo explícito de las dos personas responsables.

Semver:

- `patch`: aclaración o corrección sin cambio de contrato.
- `minor`: nuevos campos, estados, rutas o políticas compatibles.
- `major`: cambio de target, uso previsto o garantía de seguridad.

Las IAs no cambian constantes normativas por iniciativa propia. Si falta una decisión, la registran
como pregunta y se abstienen de inventarla.

---

## 20. Definition of Done de v0.3.0

v0.3.0 está terminada solo cuando:

1. Los 35 invariantes de la sección 17 tienen tests verdes.
2. Un cuidador completa el formulario con y sin defaults y ve el límite de uso urgente.
3. Una sugerencia no tocada no aparece en persistencia.
4. Una sesión auditada permanece estable al recargar.
5. Con target seleccionable, un episodio crea ventana de 24 horas y deadline de 48; sin target no
   fabrica episodio ni request.
6. Se capturan `pending`, `yes`, `no`, `unknown` y conflicto con target versionado, sin inventar
   outcomes.
7. El modelo sintético solo funciona sobre cohorte demo.
8. El baseline real abstiene con los datos actuales.
9. El challenger permanece en sombra y falla limpiamente si no es entrenable.
10. Un corpus real versionado produce al menos un catálogo con citas verificables: si existe revisor
    clínico autorizado puede activarse tras ambas revisiones; si no existe, permanece inactivo y el
    runtime demuestra `clinical_review_unavailable` sin aprobación ficticia.
11. Runtime devuelve la misma recomendación para el mismo escenario y versión.
12. Un escenario no cubierto se abstiene y crea solicitud de autoría.
13. Un profesional revisa, sustituye o rechaza sin sobrescribir historia.
14. Aprobación, aplicación y outcome quedan separados.
15. Los reportes distinguen simulación de datos reales.
16. Ruff, tests, import-linter, contratos y build de frontend pasan.
17. No existen secretos, datos personales ni artefactos no autorizados en Git.
18. La documentación y OpenAPI coinciden con este SPEC.

El release manifest distingue `implementation_status`, `corpus_status`, `target_definition_status`
y `catalog_status`. Sin corpus legalmente utilizable, M4 y este DoD quedan bloqueados. Sin target
activo se bloquean labels reales, aunque fixtures demo prueben el flujo. Sin revisor clínico puede
cerrarse implementación técnica con `catalog_status=blocked_clinical_review`, pero nunca
`catalog_enabled`.
