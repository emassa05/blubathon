# FARO — SPEC · Contratos e invariantes congelados
### Fuente única de verdad · NeuroHack 2026 · v0.2.0

> **Qué es este documento.** Todo lo marcado **🔒 FIJO** es ley. Ninguna persona ni ninguna IA inventa, reinterpreta ni "mejora" un valor fijo sin pasar por el **Control de cambios (§14)**. El [`PLAN.md`](PLAN.md) dice *qué* y *por qué*; este SPEC dice *con exactamente qué números, nombres, fórmulas y formas*. Ante cualquier contradicción entre documentos, **manda el SPEC**.
>
> Regla operativa: antes de generar código, la IA lee este archivo. Si algo que necesita no está aquí, **no lo inventa**: lo agrega primero al SPEC (§14) y recién entonces lo implementa.
>
> Relacionados: [`CONTEXTO.md`](../CONTEXTO.md) · [`EVIDENCIA.md`](EVIDENCIA.md) · [`IDEAS.md`](IDEAS.md).

> **⚠️ Cambios v0.1.0 → v0.2.0 (detalle en §14.1).**
> **Fuera de alcance:** entrada por **voz** (STT, extracción LLM de transcripción, endpoint `/voice`) y canal **Telegram**.
> **Dentro:** **pregunta filtro** (§7.4) · **sugerencias no vinculantes** (§7.6) · **procedencia por campo** (§2.5) · **VoI con degradación por antigüedad y recálculo secuencial** (§7.2–7.3) · **salvaguardas contra el punto ciego** (§7.5) · **anclas verbales** (§12.5) · **SQLite** (§1, §15) · **LLM local de 3B** (§10).
> `PLAN.md` quedó desactualizado en esos puntos (menciona voz, Telegram, Supabase y un LLM de 8B). Manda este archivo.

---

## 0. Las 13 reglas no-negociables (la constitución)

Si un cambio viola una de estas, es un bug, no una decisión.

1. 🔒 **El LLM nunca calcula el riesgo.** El número sale del motor determinista. El LLM **solo redacta** la narrativa a partir de un payload que arma el backend (§10). Nada más.
2. 🔒 **Sin fuga temporal (leakage).** Para predecir el día `t+1` solo se usan datos hasta el día `t` inclusive. Ningún valor del día `t+1` es feature. Jamás.
3. 🔒 **Nombres en inglés `snake_case` en código/DB/API. Textos de UI en español.** Sin excepción.
4. 🔒 **El riesgo canónico es una probabilidad `p ∈ [0,1]`.** La UI muestra `round(p*100)` como entero. Nunca se guarda el porcentaje como fuente.
5. 🔒 **Nunca se imputa para el modelo.** LightGBM recibe `NaN` nativo. La imputación existe **solo** dentro del cálculo de VoI (§7.1–7.2) y como **sugerencia visual no vinculante** (§7.6).
6. 🔒 **El missingness es una feature, nunca un cero silencioso.** Cada variable tiene su indicador `*_missing`.
7. 🔒 **Si no hay datos suficientes, se abstiene (§6).** Nunca se fabrica un número para rellenar. "No sé todavía" es una salida válida y deseada.
8. 🔒 **Toda predicción viaja con `confidence` + `icd`.** Un riesgo sin confianza no se muestra.
9. 🔒 **`RANDOM_SEED = 42`** en todo proceso aleatorio (generador, bootstrap, splits, VoI). Reproducibilidad total.
10. 🔒 **Los splits de datos se hacen por niño (`child_id`), nunca por día.** Un niño está entero en train, o en val, o en test.
11. 🔒 **Lenguaje afirmativo y no diagnóstico.** Se habla de *desregulación* y *apoyos*, nunca de "conducta problema", nunca "diagnóstico", nunca alarmismo. Faro no diagnostica.
12. 🔒 **El sistema sugiere, nunca autocompleta.** Ningún campo adquiere valor sin que una persona lo haya tocado. Una sugerencia se muestra en gris y solo se convierte en dato al confirmarse (§7.6). **Un valor sugerido y no tocado no existe.**
13. 🔒 **El VoI ordena y destaca; nunca esconde.** Las 15 variables están **siempre accesibles** en el formulario. La priorización reduce fricción, jamás disponibilidad (§7.4).

---

## 1. Convenciones globales 🔒 FIJO

| Concepto | Valor fijo |
|---|---|
| Idioma de código/DB/API | inglés, `snake_case` |
| Idioma de UI y textos al usuario | español (Chile) |
| IDs | UUID v4, string |
| Fecha (día del registro) | `YYYY-MM-DD` (fecha local, sin hora) |
| Timestamps | ISO-8601 UTC, sufijo `Z` |
| Zona horaria de referencia | `America/Santiago` |
| Riesgo interno | `float` en `[0,1]`, 4 decimales en API |
| Riesgo en UI | entero `0–100` (`round(p*100)`) |
| Escala ordinal estándar | entero `1–5` |
| Ausencia de dato | `null` (JSON) / `NaN` (Python) — **nunca** `0` |
| Versión del modelo | string semver, ej. `"faro-0.2.0"` |
| Encoding de archivos | UTF-8 |
| Unidad de horas de sueño | horas decimales (ej. `8.5`) |
| **Almacén de datos** | **SQLite**, archivo único `data/faro.db` — cero dependencia de red |

**Convención de dirección ordinal 🔒:** en las variables de "estado", **`5` = mejor / más regulado**. Las **excepciones** (donde más alto = peor o no es monótono) están marcadas explícitamente en la tabla §2.1. El modelo no depende de la dirección; la UI, las anclas (§12.5) y la narrativa sí.

---

## 2. Contrato de datos — el registro diario 🔒 FIJO

La entidad central es `DailyLog`: un registro por `(child_id, date, source)`. Estas son **las 15 variables de las bases** mapeadas 1:1 a campos canónicos, más `night_awakenings` (sub-feature de sueño respaldada por evidencia).

### 2.1 Campos

| # (base) | Campo canónico | Tipo | Rango / enum | Dirección | Nullable |
|---|---|---|---|---|---|
| 1a | `sleep_hours` | float | `0.0–16.0` | más alto = mejor (hasta la necesidad personal) | sí |
| 1b | `sleep_quality` | int | `1–5` | 5 = mejor | sí |
| 1c* | `night_awakenings` | int | `0–15` | **más alto = peor** | sí |
| 2 | `wake_state` | int | `1–5` | 5 = despierta tranquilo | sí |
| 3 | `morning_support_need` | int | `1–5` | **más alto = peor** (más apoyo) | sí |
| 4 | `gi_status` | int | `1–5` | 5 = sin molestias | sí |
| 5 | `food_changes` | bool | `true/false` | `true` = hubo cambio | sí |
| 6 | `routine_changes` | bool | `true/false` | `true` = hubo cambio | sí |
| 7a | `observed_behavior_tags` | array\<enum\> | ver §2.2 | cualitativo | sí (default `[]`) |
| 7b | `observed_behavior_note` | text | libre, ≤500 | — | sí |
| 8 | `alertness` | int | `1–5` | **no monótono** (nivel de activación; 3≈óptimo) | sí |
| 9 | `dysregulation_events` | int | `0–20` | **más alto = peor** (episodios menores del día) | sí |
| 10 | `activity_participation` | int | `1–5` | 5 = participación plena | sí (null si no hubo actividad) |
| 11 | `social_interactions` | int | `1–5` | 5 = muy positivas | sí |
| 12 | `eating_status` | int | `1–5` | 5 = comió bien | sí |
| 13a | `relevant_event_flag` | bool | `true/false` | `true` = evento excepcional | sí |
| 13b | `relevant_events_note` | text | libre, ≤500 | — | sí |
| 14 | `crisis_occurred` | bool | `true/false` | **TARGET** (§3) | **no** (obligatorio) |
| 15 | `other_notes` | text | libre, ≤500 | — | sí |

`*` = sub-feature añadida (respaldo: `EVIDENCIA §2.1`, los despertares nocturnos son la sub-variable de sueño más predictiva).

**Nota 🔒:** `relevant_event_flag` cumple doble función: es una de las 15 variables **y** es la respuesta a la pregunta filtro del formulario (§7.4). Es el mismo dato, capturado una sola vez.

### 2.2 Enum `observed_behavior_tags` 🔒

```
calm | irritable | anxious | withdrawn | stereotypy |
aggression | self_injury | meltdown | elopement | other
```

### 2.3 Enum `source` 🔒

```
home | therapy | school
```

Qué fuente llena qué (en el generador y en validación): `home` puede llenar todo; `therapy` llena `{gi_status, dysregulation_events, activity_participation, social_interactions, observed_behavior_*, alertness}`; `school` llena `{activity_participation, social_interactions, eating_status, dysregulation_events, observed_behavior_*}`. `crisis_occurred` lo puede reportar cualquiera.

### 2.4 Objeto JSON canónico 🔒

```json
{
  "log_id": "uuid",
  "child_id": "uuid",
  "date": "2026-08-25",
  "source": "home",
  "sleep_hours": 6.5,
  "sleep_quality": 2,
  "night_awakenings": 3,
  "wake_state": 2,
  "morning_support_need": 4,
  "gi_status": null,
  "food_changes": false,
  "routine_changes": true,
  "observed_behavior_tags": ["irritable"],
  "observed_behavior_note": null,
  "alertness": 4,
  "dysregulation_events": 2,
  "activity_participation": 3,
  "social_interactions": 2,
  "eating_status": 2,
  "relevant_event_flag": false,
  "relevant_events_note": null,
  "crisis_occurred": false,
  "other_notes": null,
  "capture_method": "form",
  "field_provenance": {
    "sleep_hours": "confirmed",
    "sleep_quality": "observed",
    "night_awakenings": "observed",
    "routine_changes": "observed",
    "gi_status": "assumed_stable"
  },
  "created_at": "2026-08-25T07:12:00Z"
}
```

`capture_method` 🔒 ∈ `form | synthetic`. (`voice` queda **reservado** para una versión futura; **no** se implementa en v0.2.0.)

### 2.5 Procedencia por campo (`field_provenance`) 🔒 FIJO

Cada campo lleva registrado **cómo llegó ahí**. Es la pieza que impide que el sistema infle su propia confianza con datos que nadie miró (regla §0.12).

| Valor | Significado | ¿Asigna valor? | Peso en `coverage` (§5.1) |
|---|---|---|---|
| `observed` | la persona ingresó el valor | sí | **1.0** |
| `confirmed` | había una sugerencia (§7.6) y la persona la aceptó tocándola | sí | **1.0** |
| `assumed_stable` | la persona respondió **"No"** a la pregunta filtro (§7.4); no se le pidió el valor | **no** → `null` | **0.5** |
| `unknown` | nadie dijo nada | no → `null` | **0.0** |

**Reglas 🔒:**
- `assumed_stable` **nunca asigna valor**: el campo queda `null` para el modelo. Solo aporta a la cobertura, porque una persona **afirmó activamente** que no hubo novedad — eso vale más que el silencio y menos que una observación.
- Una sugerencia **no tocada** no produce valor ni procedencia: queda `unknown` (regla §0.12).
- Los campos ausentes del objeto `field_provenance` se interpretan como `unknown`.
- `field_provenance` **no es feature del modelo** (§9.1). Existe solo para el cálculo del ICD (§5.1) y para auditoría.
- El generador sintético (§8) emite `observed` para todo campo presente y `unknown` para todo campo ausente.

---

## 3. Definición del target y horizonte 🔒 FIJO

- **Objetivo de predicción:** `y = crisis_occurred(t+1)`, binario, dado todo lo registrado hasta el final del día `t`.
- **Horizonte:** exactamente **un día calendario** (`t+1`). Esto materializa las "próximas 24 horas" de las bases.
- **Qué es una "crisis conductual"** (definición operativa, usada idénticamente por generador, modelo y evaluación): un evento de desregulación **mayor** = manifestación de al menos uno de `{meltdown, aggression, self_injury, elopement}` con intensidad sobre el umbral personal del niño (§8). Se distingue de `dysregulation_events`, que cuenta episodios **menores** del día y **no** es el target.
- **Regla anti-leakage 🔒:** las features para predecir `t+1` usan solo días `≤ t`. `dysregulation_events(t)` es feature válida (es del día `t`); `crisis_occurred(t+1)` jamás lo es.
- **Días mínimos de historia:** con menos de **5 días** de registros para un niño, el sistema **se abstiene** (§6) — no hay base personal suficiente.

---

## 4. Escala de riesgo y bandas 🔒 FIJO

Riesgo = `p(crisis_occurred(t+1)=true) ∈ [0,1]`, calibrado (§9).

| Banda | Rango de `p` | Color UI | Etiqueta ES |
|---|---|---|---|
| `verde` | `p < 0.15` | verde | "riesgo bajo" |
| `ambar` | `0.15 ≤ p < 0.35` | ámbar | "riesgo medio" |
| `rojo` | `p ≥ 0.35` | rojo | "riesgo alto" |

Base rate objetivo del generador ≈ **0.10** (§8). Con eso, `rojo` (≥0.35) ≈ **3.5×** la tasa base → señal fuerte y accionable. Estos cortes son **fijos** para todo el build (no se re-tunean a mano en demo).

---

## 5. Calidad del dato (ICD) y confianza 🔒 FIJO

### 5.1 Índice de Calidad del Dato

`ICD ∈ [0,1] = coverage × recency × consistency`

**Coverage (ponderada por importancia y por procedencia, ventana 14 días):**
```
coverage = Σ_v ( w_v · presencia_v ) / Σ_v w_v

  presencia_v = ( Σ_{d ∈ últimos 14 días} peso_proc_v(d) ) / 14

  peso_proc = 1.0  si observed | confirmed
            = 0.5  si assumed_stable
            = 0.0  si unknown
```
> **Por qué el 0.5 🔒:** sin él, un día tranquilo en que la persona responde "no pasó nada" (§7.4) haría caer la cobertura, y el sistema se abstendría **justo en los días buenos**, que son la mayoría. Un "no hubo novedad" es información, no silencio — pero vale la mitad que haber mirado.

**Recency (recencia):**
```
recency = exp(-λ · días_desde_último_registro),  λ = ln(2)/2   (vida media 2 días)
```
(último registro = último día con al menos `sleep_*` o `crisis_occurred` presente).

**Consistency (consistencia entre fuentes):**
```
1 fuente ese día          → consistency = 1.0
≥2 fuentes con solape     → consistency = clip(1 − desacuerdo_norm_medio, 0.5, 1.0)
                            desacuerdo_norm = |a−b| / rango_de_la_variable
sin solape                → consistency = 1.0
```

### 5.2 Pesos de importancia `w_v` 🔒

Derivados de `EVIDENCIA §2.4` (no arbitrarios):

| Variable | `w_v` |
|---|---|
| `sleep_hours`, `sleep_quality` | 1.0 |
| `night_awakenings` | 0.8 |
| `gi_status` | 0.7 |
| `routine_changes` | 0.7 |
| `wake_state` | 0.6 |
| `dysregulation_events` | 0.6 |
| `morning_support_need` | 0.5 |
| `alertness` | 0.5 |
| `social_interactions` | 0.4 |
| `activity_participation` | 0.4 |
| `eating_status`, `food_changes` | 0.3 |
| `relevant_event_flag` | 0.3 |

(`observed_behavior_*`, `other_notes` no pesan en cobertura por ser texto libre opcional.)

**Conjunto de alto peso 🔒:** `HIGH_WEIGHT = { v : w_v ≥ 0.5 }` =
`{sleep_hours, sleep_quality, night_awakenings, gi_status, routine_changes, wake_state, dysregulation_events, morning_support_need, alertness}` — **9 variables**.
Es el conjunto al que aplican el techo de antigüedad y la cuota de exploración (§7.5).

### 5.3 Etiqueta de confianza 🔒

Se combina `ICD` con el ancho del intervalo de predicción `width` (§9.3):

| `confidence` | Condición |
|---|---|
| `alta` | `ICD ≥ 0.70` **y** `width ≤ 0.25` |
| `media` | (no `alta`) **y** `ICD ≥ 0.45` **y** `width ≤ 0.45` |
| `baja` | no cumple `alta`/`media` **pero** por encima del piso de abstención (§6) |
| `null` | se abstiene (§6) |

---

## 6. Regla de abstención 🔒 FIJO

El sistema **NO entrega número** (`status="insufficient_data"`, `risk=null`, `risk_band=null`, `confidence=null`) cuando se cumple **al menos una**:

```
ICD < 0.35                         (datos demasiado pobres)
  OR  width > 0.60                 (el modelo está demasiado incierto)
  OR  días_de_historia < 5         (sin base personal)
```

Al abstenerse, devuelve `requested_variables` = las 1–3 variables faltantes de mayor VoI (§7), con su `prompt_es`, para pedir el dato que más reduciría la incertidumbre. Mensaje de UI fijo (plantilla):
> *"Todavía no tengo información suficiente para darte una estimación confiable. Me ayudaría saber: {variables}."*

---

## 7. Valor de la Información (VoI) y formulario adaptativo 🔒 FIJO

> **Qué es.** El VoI responde: *¿cuál pregunta, si me la respondieran, más cambiaría mi estimación de hoy?* Formalmente es un criterio de **reducción esperada de varianza** (diseño experimental bayesiano / aprendizaje activo).
> **Qué NO es.** No es una compuerta. Ordena y destaca; **nunca esconde** (regla §0.13).

### 7.1 Cálculo base 🔒

Para cada variable `v` **faltante** el día `t`:

```
1. Muestrear K = 20 valores plausibles de v  (distribución de §7.2).
2. Para cada muestra k: fijar v = valor_k, recomputar el riesgo p_k con el modelo.
3. VoI(v) = Var_k(p_k)              (varianza del riesgo sobre las 20 imputaciones)
```

- `K = 20` 🔒. Con `RANDOM_SEED = 42` la imputación es reproducible.
- La imputación de este paso vive **solo** aquí. El modelo de riesgo (§9) nunca ve valores imputados (regla §0.5).
- Costo: ~14 variables × 20 muestras = 280 predicciones, ejecutadas en lote sobre el ensemble. Milisegundos.

### 7.2 Muestreo con degradación por antigüedad 🔒

Los `K` valores salen de la distribución personal empírica del niño, **ensanchada según los días sin observar la variable**.

```
d_v = días desde la última observación de v con provenance ∈ {observed, confirmed}

μ_muestreo(v) = mediana personal de v        (ventana 30 días)
σ_muestreo(v) = MAD_personal(v) · (1 + κ · d_v)

κ = 0.15   🔒     → a los 7 días la dispersión se duplica (1 + 0.15·7 = 2.05)

Muestras clipeadas al rango legal de la variable (§2.1) y redondeadas al tipo
(entero para escalas 1–5, float para sleep_hours).

Si el niño tiene < 10 días de historia, o < 5 observaciones de v:
    usar el prior poblacional (§8.4) en vez de la distribución personal.
```

**Por qué 🔒:** la certeza sobre una variable **no observada se degrada con el tiempo**. Si `gi_status` se vio ayer, es improbable que hoy sea distinto y el VoI será bajo, correctamente. Si se vio hace 8 días, podría ser cualquier cosa: la dispersión crece, los `p_k` se separan, y el VoI **sube solo**. Esto elimina el punto ciego auto-confirmado sin ninguna regla ad-hoc.

### 7.3 Recálculo secuencial 🔒

El VoI se **recalcula después de cada respuesta** dentro de la misma sesión, no una sola vez al abrir el formulario. La segunda pregunta se elige con la primera **ya respondida**.

```
abre formulario → VoI → pregunta #1
responde        → RECALCULAR → VoI → pregunta #2
responde        → RECALCULAR → (filtro §7.4)
```

### 7.4 Estructura del formulario 🔒

```
BLOQUE 1 · DESTACADAS
  top-2 por VoI  (top-3 si ICD < 0.5).  Siempre visibles, nunca filtradas.

BLOQUE 2 · PREGUNTA FILTRO
  "¿Hoy pasó algo distinto o fuera de lo común?"   [No] [Sí]
  → la respuesta se persiste en `relevant_event_flag` (§2.1, campo 13a)
  → "No": el bloque 3 no se despliega. Cada variable de la cola recibe
          provenance = "assumed_stable" (§2.5). NO se les asigna valor.
  → "Sí": se despliega el bloque 3.

BLOQUE 3 · COLA
  variables restantes, ordenadas por VoI descendente.

BLOQUE 4 · SIEMPRE VISIBLE
  "Quiero contar algo más" → abre el formulario completo (las 15 variables).
```

**Regla 🔒:** el bloque 4 está disponible en todo momento, en todos los estados. La persona siempre puede registrar cualquier variable sin que el sistema se la pida (regla §0.13).

### 7.5 Salvaguardas contra el punto ciego 🔒

El VoI puro es explotación pura: podría dejar de preguntar una variable estable y no enterarse nunca de que cambió. Estas tres salvaguardas lo impiden, y **la pregunta filtro (§7.4) no las anula jamás**.

**a) Techo de antigüedad 🔒**
```
Ninguna variable de HIGH_WEIGHT (§5.2) puede pasar más de 7 días sin ser
preguntada. Al alcanzar d_v = 7 entra al BLOQUE 1 aunque su VoI sea bajo
y aunque el filtro haya respondido "No".

Mecánica 🔒: DESPLAZA la posición de menor VoI del BLOQUE 1. El bloque
NO crece: mantiene 2 posiciones (3 si ICD < 0.5).

Desempate 🔒: si dos o más variables alcanzan d_v ≥ 7 el mismo día,
entra primero la de mayor w_v; si empatan en w_v, la de mayor d_v;
si aún empatan, orden alfabético del nombre canónico.
```

**b) Gatillo por anomalía 🔒**
```
Si alguna respuesta del día tiene |z-score personal| ≥ 2.0 (capa C1, §9.1),
el BLOQUE 3 se despliega automáticamente, aunque el filtro haya dicho "No".
```

**c) Cuota de exploración 🔒 (determinista, no aleatoria)**
```
Si   hash_estable(child_id + date) mod 7 == 0
     → UNA posición del BLOQUE 1 se asigna a la variable de HIGH_WEIGHT
       menos observada en los últimos 14 días, en vez de a la de mayor VoI.

hash_estable = SHA-256 del string concatenado, primeros 8 bytes como entero.
Frecuencia efectiva ≈ 1 de cada 7 días. Determinista y reproducible: la
misma demo da siempre el mismo resultado.
```

**Precedencia 🔒:** si en un mismo día coinciden techo de antigüedad y cuota de exploración, manda el **techo** (a > c). El gatillo por anomalía (b) es independiente y siempre se aplica.

### 7.6 Sugerencias — no autocompletado 🔒

```
Cada pregunta PUEDE mostrar un valor sugerido:

  sugerencia(v) = mediana personal de v en los últimos 14 días
  Solo si hay ≥ 5 observaciones de v en esa ventana; si no, sin sugerencia.
```

**Reglas 🔒 (materializan la regla §0.12):**
- La sugerencia se renderiza **en gris, como texto de ayuda**. El campo está **vacío**.
- Se muestra con su **ancla verbal** (§12.5) cuando la variable es ordinal: *"lo habitual: Buena (4)"*.
- Un toque la acepta → el valor se guarda con `provenance = "confirmed"`.
- La persona puede elegir cualquier otro valor → `provenance = "observed"`.
- **Sin toque → no hay valor y no hay procedencia.** El campo queda `null` / `unknown`.
- La sugerencia **nunca** viaja a `/ingest` por sí sola. El cliente envía solo campos tocados.

### 7.7 Textos

Cada variable tiene su `prompt_es` fijo en §12.4 y sus anclas verbales en §12.5.

---

## 8. Generador sintético causal — parámetros 🔒 FIJO

Reemplaza el dataset inexistente. Cada número sale de `EVIDENCIA §2` traducido a coeficientes. **Todos los valores de esta sección son fijos.**

### 8.1 Estructura

```
Población:  N_CHILDREN = 200,  DAYS = 180,  base_rate objetivo ≈ 0.10
Semilla:    RANDOM_SEED = 42

Carga alostática latente del día t (escala estandarizada):

L(t) = β0
     + β_sleep    · sleep_debt(t)
     + β_awak     · z(night_awakenings(t))
     + β_gi       · gi_burden(t)
     + β_routine  · routine_load(t)
     + β_sensory  · sensory_load(t)
     + β_sr       · sleep_debt(t) · routine_load(t)        // interacción ABA
     + β_gs       · gi_burden(t)  · sensory_load(t)        // interacción
     + ρ          · L(t−1)                                  // arrastre
     + θ_i                                                  // susceptibilidad personal
     + ε(t)

p_crisis(t+1) = sigmoid( L(t) )
crisis_occurred(t+1) = 1 con probabilidad p_crisis(t+1)
```

### 8.2 Coeficientes 🔒

| Símbolo | Valor | Justificación (EVIDENCIA) |
|---|---|---|
| `β0` (intercepto) | `-2.20` | fija base rate ≈ sigmoid(−2.2) ≈ 0.10 |
| `β_sleep` | `0.90` | sueño = predictor top (22–32% varianza) §2.1 |
| `β_awak` | `0.50` | despertares nocturnos, sub-feature fuerte §2.1 |
| `β_gi` | `0.60` | GI medio-alto, proxy dolor no comunicado §2.2 |
| `β_routine` | `0.60` | cambio de rutina = setting event §2.3 |
| `β_sensory` | `0.40` | carga sensorial |
| `β_sr` (sueño×rutina) | `0.50` | mecanismo ABA: el setting event baja el umbral §2.3 |
| `β_gs` (GI×sensorial) | `0.35` | interacción secundaria |
| `ρ` (arrastre) | `0.30` | autocorrelación día a día |
| `σ` (ruido `ε`) | `0.70` | variabilidad irreductible |
| `θ_i` | `~ Normal(0, 0.60)` | susceptibilidad personal (define umbral) |

### 8.3 Ventanas de arrastre 🔒

```
sleep_debt(t)   = 0.5·d(t) + 0.3·d(t−1) + 0.2·d(t−2)
                  d(τ) = max(0, need_i − sleep_hours(τ)) / need_i   (déficit relativo)
gi_burden(t)    = 0.6·g(t) + 0.4·g(t−1)     g(τ)=(5 − gi_status(τ))/4
routine_load(t) = 1.0·r(t) + 0.5·r(t−1) + 0.25·r(t−2)   r=1 si routine_changes else 0
sensory_load(t) = derivada de alertness extremo + relevant_event_flag
```

### 8.4 Perfiles de niño 🔒

| Rasgo | Distribución |
|---|---|
| `support_level` | 60% low, 40% high (high → mayor `σ` personal y θ más alto) |
| `verbal` | 70% verbal, 30% no-verbal (no-verbal → `β_gi` ×1.3: dolor no comunicado) |
| `chronic_gi` | 30% con comorbilidad GI (gi_status basal peor) |
| `sex` | 50% F / 50% M |
| `need_i` (horas de sueño necesarias) | `~ Normal(9.0, 1.0)`, clip `[7,11]` |
| `base_rate_i` | derivada de θ_i, esperada ≈ 0.10, rango efectivo `0.05–0.20` |

**Prior poblacional 🔒 (usado por §7.2 en cold-start):** para cada variable, la distribución marginal empírica calculada sobre **el conjunto de train** (§9.4), no sobre toda la población — para no filtrar información de test.

**Camuflaje femenino (para el test de equidad) 🔒:** en niñas, las señales *observadas* (`dysregulation_events`, `observed_behavior_tags`) se atenúan por factor `0.70` mientras la carga latente `L` es la misma. Esto simula el infra-registro real y permite medir si el modelo rinde peor con ellas (`EVIDENCIA` / rúbrica InES).

### 8.5 Modelo de observación (latente → registro) 🔒

- `sleep_hours(t) = need_i − 2·max(0, L(t)/3) + N(0, 0.8)`, clip `[3,12]` → peores días duermen menos.
- `sleep_quality` = binning de `sleep_hours` y `night_awakenings` a `1–5`.
- `night_awakenings ~ Poisson(0.5 + 1.5·relu(L(t)))`, clip `[0,15]`.
- `gi_status`: peor si `chronic_gi`; empeora con `L`.
- `wake_state`, `morning_support_need`, `alertness`, `dysregulation_events`, `social_interactions`, `activity_participation`, `eating_status`: funciones ruidosas de `L(t)` y del rasgo, discretizadas a su rango (§2.1). Direcciones según §2.1.
- `routine_changes`, `food_changes`, `relevant_event_flag`: Bernoulli con prob base baja (0.10–0.15), elevada en días de evento.

### 8.6 Missingness NMAR (el arma) 🔒

```
p_miss_base = 0.25
p_miss(t)   = clip( p_miss_base + 0.40·sigmoid(L(t) − 0.5), 0, 0.85 )
```
→ los días de mayor carga se registran **menos** (hasta ~85% de campos ausentes).

Ajustes por campo 🔒:
```
gi_status, social_interactions, night_awakenings : p_miss × 1.4  (se olvidan más)
sleep_hours, sleep_quality                        : p_miss × 0.6  (se registran más)
```
Estructural (no NMAR): fines de semana → campos de `school` = `null`; `therapy` solo ~2 días/semana; `home` todos los días.

**Separación de conceptos 🔒:** este missingness modela **si la persona responde**. Es independiente de la política de elicitación (§7), que modela **qué se le pregunta**. Su composición se define en §13.1.

### 8.7 Salidas del generador 🔒

- `data/logs.parquet` — registros `DailyLog` con missingness aplicado (lo que "ve" el sistema), con `capture_method="synthetic"` y `field_provenance` = `observed` para todo campo presente.
- `data/ground_truth.parquet` — `L(t)`, `p_crisis(t+1)`, `crisis_occurred(t+1)`, perfil del niño (solo para evaluación; **el modelo no lo ve**).
- `data/manifest.json` — semilla, parámetros usados, versión del generador.
- `data/faro.db` — SQLite sembrado desde `logs.parquet` para que la app arranque con datos.

---

## 9. Modelo de riesgo y confianza 🔒 FIJO

### 9.1 Features (derivadas en C0/C1, todas con historia ≤ t)

```
Por cada variable ordinal/continua v:
  - valor crudo v(t)                       (NaN si falta → LightGBM lo maneja)
  - z-score personal robusto (mediana/MAD, ventana 14–30 d)   [C1]
  - v_missing (bool)                        [regla §0.6]
  - lags: v(t−1), v(t−2)  (para sleep, gi, routine)
  - media móvil 3d y 7d; tendencia (pendiente 7d)
Globales:
  - base_rate personal (frecuencia histórica de crisis del niño)
  - day_of_week
  - dysregulation_events(t), su media 3d
  - relevant_event_flag(t)                  (= respuesta a la pregunta filtro §7.4)

Prohibido como feature 🔒:
  - cualquier valor del día t+1
  - el ICD (es gate, no feature)
  - field_provenance (§2.5) — vive solo para el ICD
```

> **Nota 🔒:** no se agregan indicadores `*_assumed_stable` por variable. La información de "hoy no pasó nada" ya entra al modelo una sola vez, vía `relevant_event_flag`. Duplicarla por campo introduciría colinealidad con `*_missing` sin aportar señal.

### 9.2 Modelo 🔒

- **Estimador:** `LightGBM` (clasificación binaria), **sin imputar** (NaN nativo).
- **Config fija (punto de partida):**
  ```
  objective=binary, n_estimators=400, learning_rate=0.03,
  num_leaves=31, max_depth=6, min_child_samples=40,
  subsample=0.8, colsample_bytree=0.8, reg_lambda=1.0,
  class_weight=balanced, random_state=42, early_stopping (val, patience=40)
  ```
- **Calibración:** `isotonic regression` ajustada en el fold de validación → `p` calibrada.

### 9.3 Confianza / intervalo 🔒

- **Primario:** ensemble bootstrap de `B=20` LightGBM (resamples por niño, semillas 42..61).
  ```
  p        = media de las 20 predicciones (calibradas)
  σ        = desviación estándar de las 20
  interval = [ clip(p − 1.2816·σ, 0, 1), clip(p + 1.2816·σ, 0, 1) ]   (80%)
  width    = interval[1] − interval[0]
  ```
- **Secundario (para la página de evaluación y el pitch):** conjunto conforme `MAPIE` a `α=0.10` (cobertura 90% garantizada, distribution-free). Se **reporta**, no gobierna la UI.
- `width` alimenta la etiqueta de confianza (§5.3) y la abstención (§6).

### 9.4 Splits 🔒

```
Por child_id (regla §0.10), con RANDOM_SEED=42:
  train 60%  |  calib/val 20%  (calibración isotónica + conformal)  |  test 20%
Secundario: holdout temporal (últimos 30 días de cada niño de test) para robustez.
```

---

## 10. Contrato del LLM 🔒 FIJO

**El LLM corre local (Ollama), en un modelo de ~3B parámetros cuantizado** (`qwen2.5:3b-instruct` o `llama3.2:3b`, Q4_K_M). **Único uso: redactar la narrativa.** Nunca calcula riesgo (regla §0.1), nunca ve datos crudos, nunca extrae de texto libre en v0.2.0.

**Por qué 3B y no 8B 🔒:** el equipo dispone de 8 GB de VRAM. Un modelo de 8B Q4 más el navegador deja el margen en ~0 y, en Windows, el driver hace *fallback* silencioso a RAM del sistema — no falla, se vuelve 5–10× más lento. Con la tarea reducida a redactar ≤60 palabras desde un payload cerrado, un 3B es suficiente y deja margen de sobra.

### 10.1 Uso único — narrativa accionable

- **Entrada:** `NarrativePayload` **construido por el backend**:
  ```json
  {
    "child_name": "Lucas",
    "risk_band": "rojo",
    "confidence": "media",
    "horizon": "mañana",
    "drivers": [
      {"label": "sueño", "direction": "empeora", "detail": "3 noches bajo su normal"},
      {"label": "rutina", "direction": "empeora", "detail": "cambio ayer"}
    ],
    "candidate_strategies": ["visual_support", "reduce_stimuli", "advance_sleep"]
  }
  ```
- **Salida (schema estricto):**
  ```json
  { "headline_es": "…", "explanation_es": "…", "actions_es": ["…","…","…"] }
  ```
- **Reglas 🔒:** `temperature=0.2`; salida forzada contra el schema (Outlines/Instructor o gramática GBNF); `actions_es` ≤ 3 y **solo** derivadas de `candidate_strategies` provistas; puede nombrar **solo** los `drivers` del payload (no inventa causas); sin diagnóstico, sin alarmismo, lenguaje afirmativo (regla §0.11); `explanation_es` ≤ 60 palabras.

### 10.2 Fallback determinista 🔒 (obligatorio, se construye ANTES que el LLM)

```
Si la salida no valida contra el schema → 1 reintento.
Si vuelve a fallar, o si Ollama no está disponible
   → plantilla determinista en español, poblada desde el mismo NarrativePayload.
```
El modo determinista **no es un parche de emergencia**: es la ruta por defecto que debe existir y estar probada. El LLM es una mejora de fluidez sobre él, nunca una dependencia.

### 10.3 Prompts

Viven en `ml/narrative/prompts/` versionados. Cambiarlos = cambio de SPEC (§14). No se editan ad-hoc en código.

---

## 11. Contrato de la API 🔒 FIJO

Base: FastAPI, JSON, prefijo `/api/v1`. Errores: `{ "error": {"code": string, "message_es": string} }`.

| Método | Ruta | Entrada | Salida |
|---|---|---|---|
| POST | `/ingest` | `DailyLog` (§2.4) o `DailyLog[]` | `{ ok, child_id, date }` |
| GET | `/predict` | `?child_id&date` | `RiskResponse` (§11.1) |
| GET | `/voi` | `?child_id&date` | `VoIResponse` (§11.2) |
| GET | `/explain` | `?child_id&date` | `ExplainResponse` (§11.3) |
| POST | `/counterfactual` | `{ child_id, date, overrides:{field:value} }` | `{ risk_before, risk_after, band_before, band_after }` |
| GET | `/quality` | `?child_id&date` | `{ icd, coverage, recency, consistency }` |
| POST | `/feedback` | `{ child_id, date, dysregulation_occurred:bool, strategy_used?:string, helped?:bool }` | `{ ok }` |
| GET | `/eval` | — | métricas (§13) |

**`/ingest` 🔒:** acepta `field_provenance` (§2.5). El cliente envía **solo campos tocados** (regla §0.12). Si un campo llega con valor pero sin procedencia, se asume `observed`. Si llega `assumed_stable` con valor no nulo → **error de validación** (`code="provenance_conflict"`).

### 11.1 `RiskResponse` (contrato central) 🔒

```json
{
  "child_id": "uuid",
  "date": "2026-08-25",
  "status": "ok",
  "risk": 0.62,
  "risk_band": "rojo",
  "interval": [0.48, 0.76],
  "confidence": "media",
  "icd": 0.71,
  "requested_variables": [
    { "variable": "gi_status", "prompt_es": "¿Tuvo molestias digestivas hoy?", "voi": 0.12 }
  ],
  "model_version": "faro-0.2.0",
  "generated_at": "2026-08-25T07:00:00Z"
}
```
- `date` = el día **para el cual** se predice (`t+1`).
- Cuando `status="insufficient_data"`: `risk`, `risk_band`, `interval`, `confidence` = `null`; `requested_variables` obligatorio (§6).
- Cuando `status="ok"`: `requested_variables` = la micro-pregunta adaptativa (top-2/3 de VoI) o `[]`.

**Coherencia verificable del ejemplo:** `risk=0.62 ≥ 0.35 → rojo` ✓ · `width=0.76−0.48=0.28`; `ICD=0.71≥0.70` pero `width 0.28 > 0.25` → no `alta`; `ICD≥0.45` y `0.28≤0.45` → `media` ✓ · no abstiene (`ICD 0.71≥0.35`, `width 0.28≤0.60`) ✓.

### 11.2 `VoIResponse` 🔒

```json
{
  "child_id": "uuid",
  "date": "2026-08-25",
  "highlighted": [
    { "variable": "sleep_hours", "prompt_es": "¿Cuántas horas durmió anoche?",
      "voi": 0.1421, "reason": "voi", "suggestion": 8.2, "suggestion_label_es": null },
    { "variable": "gi_status", "prompt_es": "¿Tuvo molestias digestivas hoy?",
      "voi": 0.0089, "reason": "staleness", "days_since_observed": 7,
      "suggestion": 4, "suggestion_label_es": "Bien" }
  ],
  "filter_question_es": "¿Hoy pasó algo distinto o fuera de lo común?",
  "tail": [
    { "variable": "social_interactions", "prompt_es": "¿Cómo fueron sus interacciones sociales?",
      "voi": 0.0031, "reason": "voi", "suggestion": 3, "suggestion_label_es": "Neutras" }
  ]
}
```
- `reason` 🔒 ∈ `voi | staleness | exploration` — hace visibles las salvaguardas de §7.5 en la UI (*"lleva 7 días sin registrarse"*).
- `suggestion` = `null` si no hay ≥5 observaciones en 14 días (§7.6). `suggestion_label_es` = ancla verbal (§12.5), `null` para variables no ordinales.
- `highlighted` tiene 2 elementos (3 si `ICD < 0.5`).

### 11.3 `ExplainResponse` 🔒
```json
{
  "drivers": [ { "variable": "sleep_hours", "shap": -0.31, "direction": "empeora", "detail_es": "3 noches bajo su normal" } ],
  "narrative": { "headline_es": "…", "explanation_es": "…", "actions_es": ["…"] },
  "narrative_source": "llm",
  "strategies": [ { "id": "visual_support", "label_es": "Apoyos visuales anticipados" } ]
}
```
`narrative_source` 🔒 ∈ `llm | template` — refleja si se usó el fallback determinista (§10.2).

---

## 12. Catálogo de estrategias y textos 🔒 FIJO

### 12.1 Estrategias (lista cerrada — el LLM solo elige de aquí)

| `id` | `label_es` | Disparador (driver) | Base (EVIDENCIA §2.3) |
|---|---|---|---|
| `visual_support` | Apoyos visuales / agenda anticipada | rutina, transiciones | antecedent strategy validada |
| `reduce_stimuli` | Reducir estímulos sensoriales | sensorial, alerta alta | antecedent strategy |
| `advance_sleep` | Proteger / adelantar la rutina de sueño | sueño | sueño = predictor top |
| `anticipate_transition` | Anticipar verbalmente las transiciones | rutina, colegio | predictibilidad |
| `regulation_space` | Ofrecer un espacio de regulación | desregulación | apoyo de regulación |
| `sensory_tools` | Herramientas sensoriales (audífonos, presión) | sensorial | ajuste sensorial |
| `routine_predictability` | Reforzar la predictibilidad de la rutina | rutina | setting event |
| `gi_comfort` | Atender molestias físicas / GI | GI | dolor no comunicado |
| `proactive_breaks` | Pausas proactivas estructuradas | colegio, actividad | antecedent strategy |
| `co_regulation` | Co-regulación y presencia calmada | genérico / alta carga | apoyo relacional |

### 12.2 Mapeo driver → estrategias candidatas 🔒

```
sueño           → [advance_sleep, co_regulation]
rutina          → [visual_support, anticipate_transition, routine_predictability]
GI              → [gi_comfort, reduce_stimuli]
sensorial/alerta→ [reduce_stimuli, sensory_tools]
desregulación   → [regulation_space, co_regulation]
colegio         → [anticipate_transition, proactive_breaks]
```
El backend arma `candidate_strategies` uniendo los mapeos de los drivers activos (top-3 SHAP), dedup, máx 4. El LLM elige ≤3 para `actions_es`.

### 12.3 Etiquetas ES de variables (para UI y drivers) 🔒

```
sleep_hours→"horas de sueño"  sleep_quality→"calidad del sueño"
night_awakenings→"despertares nocturnos"  wake_state→"estado al despertar"
morning_support_need→"apoyo matinal"  gi_status→"salud digestiva"
food_changes→"cambios en alimentación"  routine_changes→"cambios de rutina"
alertness→"estado de alerta"  dysregulation_events→"desregulaciones del día"
activity_participation→"participación en actividades"
social_interactions→"interacciones sociales"  eating_status→"alimentación"
relevant_event_flag→"evento relevante"
```

### 12.4 `prompt_es` de micro-pregunta por variable 🔒

```
sleep_hours            "¿Cuántas horas durmió anoche?"
sleep_quality          "¿Cómo durmió anoche?"
night_awakenings       "¿Cuántas veces se despertó en la noche?"
wake_state             "¿Cómo despertó hoy?"
morning_support_need   "¿Cuánto apoyo necesitó para iniciar el día?"
gi_status              "¿Tuvo molestias digestivas hoy?"
routine_changes        "¿Hubo algún cambio en su rutina?"
alertness              "¿Cómo estuvo su estado de alerta hoy?"
social_interactions    "¿Cómo fueron sus interacciones sociales?"
activity_participation "¿Cómo participó en sus actividades?"
eating_status          "¿Cómo estuvo su alimentación hoy?"
food_changes           "¿Hubo cambios en lo que comió?"
dysregulation_events   "¿Tuvo episodios de desregulación hoy? ¿Cuántos?"
relevant_event_flag    "¿Hoy pasó algo distinto o fuera de lo común?"
```

> Cobertura verificada: las 14 variables con peso `w_v` (§5.2) tienen aquí su `prompt_es`.
> `relevant_event_flag` usa el mismo texto que la pregunta filtro (§7.4) — es el mismo dato.

### 12.5 Anclas verbales de las escalas ordinales 🔒 FIJO

**Una sola tabla para toda la aplicación.** El formulario, las sugerencias (§7.6) y la narrativa (§10) usan **estas** palabras y no otras. Sin esto, el mismo número significaría cosas distintas según por dónde se capturó, y la columna quedaría contaminada.

Aplica a las **8 variables ordinales `1–5`**. `sleep_hours`, `night_awakenings` y `dysregulation_events` son numéricas y no llevan anclas; los `bool` tampoco.

| `sleep_quality` | (5 = mejor) |
|---|---|
| 1 | Pésima — casi no durmió, muchos despertares |
| 2 | Mala — durmió poco o muy inquieto |
| 3 | Regular — durmió, pero con interrupciones |
| 4 | Buena — durmió bien, alguna interrupción menor |
| 5 | Excelente — durmió de corrido y despertó descansado |

| `wake_state` | (5 = despierta tranquilo) |
|---|---|
| 1 | Muy desregulado — despertó llorando o muy alterado |
| 2 | Desregulado — despertó irritable o muy sensible |
| 3 | Neutro — ni bien ni mal |
| 4 | Tranquilo — despertó bien, con buena disposición |
| 5 | Muy tranquilo — despertó descansado y regulado |

| `morning_support_need` | (**más alto = más apoyo = peor**) |
|---|---|
| 1 | Autónomo — hizo su rutina solo |
| 2 | Poco apoyo — recordatorios puntuales |
| 3 | Apoyo moderado — acompañamiento en varias partes |
| 4 | Mucho apoyo — hubo que guiar casi todo |
| 5 | Apoyo total — no logró iniciar el día sin ayuda constante |

| `gi_status` | (5 = sin molestias) |
|---|---|
| 1 | Muy mal — dolor evidente, vómitos o diarrea |
| 2 | Mal — molestias claras (dolor, estitiquez, náuseas) |
| 3 | Regular — algo de molestia, poco clara |
| 4 | Bien — sin molestias notorias |
| 5 | Muy bien — digestión normal, sin señales |

| `alertness` | (**no monótono — 3 ≈ óptimo**) |
|---|---|
| 1 | Muy apagado — somnoliento, sin energía |
| 2 | Bajo — más lento o desconectado de lo habitual |
| 3 | Adecuado — alerta y disponible |
| 4 | Acelerado — más inquieto o activado de lo habitual |
| 5 | Muy acelerado — muy activado, difícil de calmar |

| `activity_participation` | (5 = participación plena) |
|---|---|
| 1 | No participó |
| 2 | Participó muy poco, con mucha resistencia |
| 3 | Participó a ratos |
| 4 | Participó bien la mayor parte del tiempo |
| 5 | Participó plenamente |

| `social_interactions` | (5 = muy positivas) |
|---|---|
| 1 | Muy difíciles — conflictos o retraimiento marcado |
| 2 | Difíciles — le costó relacionarse |
| 3 | Neutras — sin nada destacable |
| 4 | Buenas — interactuó bien |
| 5 | Muy buenas — disfrutó el contacto con otros |

| `eating_status` | (5 = comió bien) |
|---|---|
| 1 | Casi no comió |
| 2 | Comió poco o rechazó comidas |
| 3 | Comió algo menos de lo habitual |
| 4 | Comió bien |
| 5 | Comió muy bien, sin dificultad |

**Regla de UI 🔒:** en escalas ordinales el formulario muestra **las cinco anclas como opciones**, más una opción **"No sé"** que persiste el campo como `null` con procedencia `unknown` (nunca como `3`).

---

## 13. Métricas de evaluación 🔒 FIJO

Reportadas en `/eval` y en la página pública. Todas sobre el **test set (20% por niño)**.

| Métrica | Definición fija | Meta |
|---|---|---|
| `auc_pr` | average precision (área PR) | > baseline (frecuencia base) |
| `auc_roc` | referencia comparativa (no principal) | ~0.78–0.84 (rango Goodwin) |
| `brier` | Brier score de la `p` calibrada | menor mejor |
| `ece` | Expected Calibration Error, 10 bins | < 0.05 objetivo |
| `alert_budget_recall` | recall de crisis con presupuesto de 1 alerta/niño/semana | curva reportada |
| `lead_time` | horizonte efectivo (fijo 24 h por diseño) | — |
| `decision_coverage` | % de días-niño donde `status="ok"` (no abstiene) | reportar |
| `ablations` | Δ AUC-PR al quitar {sueño}, {baseline personal C1}, y al forzar `p_miss=0.50` | tabla |
| `fairness_sex` | AUC-PR y recall por sexo (F vs M) | diferencia pequeña; se reporta honestamente |
| **`elicitation_ablation`** | **comparación de políticas de pregunta (§13.1)** | **tabla** |
| **`misspecification`** | **§13.2** | **tabla** |

Baselines de comparación obligatorios: (1) predecir siempre la base rate, (2) "ayer hubo desregulación → mañana crisis". Faro debe superarlos.

### 13.1 Ablación de política de elicitación 🔒

Responde de frente la objeción *"¿y si el VoI deja de preguntar algo que importaba?"*, con evidencia en vez de argumentos.

**Composición de máscaras 🔒:** un campo se observa si **(a) la política lo preguntó** Y **(b) la persona respondió**. (b) es el NMAR del generador (§8.6); (a) es la política. Se aplica (a) sobre los logs ya generados — el generador **no** cambia.

**Adherencia 🔒 (modelo de fatiga):** la probabilidad de responder decae con el número de preguntas mostradas ese día.
```
p_responde(n_preguntas) = clip( 0.95 − 0.045 · n_preguntas , 0.30, 0.95 )
   n=2  → 0.860     n=5  → 0.725     n=15 → 0.275 → clip 0.300
```

| Política | Preguntas/día | Adherencia efectiva | Se reporta |
|---|---|---|---|
| **A** · preguntar las 15 | 15 | ~0.30 | `auc_pr`, `decision_coverage` |
| **B** · Faro: top-VoI + filtro + salvaguardas (§7) | 2–3 (6 si abre la cola) | ~0.86 | `auc_pr`, `decision_coverage` |
| **C** · formulario fijo de 5 campos | 5 | ~0.725 | `auc_pr`, `decision_coverage` |
| **D** · VoI **sin** salvaguardas (§7.5 desactivadas) | 2 | ~0.86 | `auc_pr` + `stale_variable_miss_rate` |

`stale_variable_miss_rate` 🔒 = % de días en que una variable de `HIGH_WEIGHT` cambió ≥2 puntos respecto de su última observación **y** la política no la preguntó ese día. **B vs D cuantifica exactamente cuánto compran las salvaguardas.**

### 13.2 Test de mala especificación 🔒

La evaluación sobre datos del propio generador es circular: el modelo redescubre los coeficientes que nosotros pusimos. Para acotar eso:

```
Entrenar con los parámetros de §8.2.
Evaluar sobre un segundo dataset generado con parámetros PERTURBADOS:
   todos los β  ×  U(0.7, 1.3)     ·  ρ = 0.15 y 0.45     ·  base_rate = 0.06 y 0.16
   (semillas 142, 143, 144 — distintas de la de train)
Reportar la caída de auc_pr.
```

**Se declara explícitamente en el pitch:** estas métricas validan que el pipeline funciona y que resiste supuestos distintos; **no** son una afirmación sobre el rendimiento con niños reales. Para eso hace falta validación con datos de Bluba, y el protocolo se propone como siguiente paso.

---

## 14. Control de cambios 🔒

- Este SPEC es versionado (`v0.2.0`). Cualquier cambio de un valor **🔒 FIJO** requiere: (a) editar aquí, (b) subir la versión (`patch` para números/textos, `minor` para nuevos campos/endpoints), (c) acuerdo explícito de los 2 integrantes.
- Las IAs **no** cambian valores fijos por iniciativa propia. Si una IA necesita algo no especificado: lo agrega al SPEC primero, con nota, y recién codifica.
- **Reconciliación con la "documentación de soporte" del 24 ago:** si el lanzamiento aclara formatos/variables, se actualiza **este** archivo (§2/§3/§8) y sube versión. Gracias al aislamiento del contrato de datos, eso cambia el adaptador y los parámetros del generador — **no** la app.

### 14.1 Historial

**v0.2.0** — 23 ago 2026

*Eliminado:*
- Entrada por **voz**: endpoint `POST /voice`, uso "extracción" del LLM (ex §10.1), `confidence_per_field`, `faster-whisper`. `capture_method="voice"` queda reservado, no implementado.
- Canal **Telegram**: `capture_method="telegram"`.
- **Supabase** como almacén → reemplazado por SQLite.

*Añadido:*
- §0.12 y §0.13 — reglas de sugerencia-no-autocompletado y de VoI-no-esconde (11 → 13 reglas).
- §1 — SQLite como almacén.
- §2.5 — `field_provenance` (`observed | confirmed | assumed_stable | unknown`).
- §5.1 — `coverage` ponderada por procedencia (peso 0.5 para `assumed_stable`).
- §5.2 — conjunto `HIGH_WEIGHT`.
- §7.2 — muestreo con degradación por antigüedad (`κ = 0.15`), reemplaza el bono ad-hoc.
- §7.3 — recálculo secuencial del VoI.
- §7.4 — estructura del formulario en 4 bloques + **pregunta filtro**.
- §7.5 — salvaguardas: techo de 7 días, gatillo por anomalía, cuota de exploración determinista.
- §7.6 — sugerencias no vinculantes.
- §8.4 — prior poblacional calculado solo sobre train.
- §9.1 — `relevant_event_flag` como feature; `field_provenance` prohibida como feature.
- §10 — LLM local de **3B**; §10.2 fallback determinista obligatorio.
- §11.2 — `VoIResponse` con `reason`, `suggestion`, bloques.
- §11.3 — `narrative_source`.
- §12.5 — **anclas verbales** de las 8 escalas ordinales + opción "No sé".
- §13.1 — ablación de política de elicitación con modelo de adherencia.
- §13.2 — test de mala especificación.

**v0.1.0** — 21 ago 2026. Versión inicial.

---

## 15. Estructura de repositorio 🔒 FIJO

```
faro/
├── SPEC.md                      # este archivo — fuente de verdad
├── README.md                    # setup en 1 comando
├── apps/
│   ├── web/                     # Next.js 15 + TS + Tailwind + shadcn
│   └── api/                     # FastAPI (/api/v1, §11)
├── packages/
│   └── shared/                  # tipos: zod (TS) ↔ pydantic (PY), un solo contrato §2/§11
├── ml/
│   ├── spec_constants.py        # espejo en código de TODO número 🔒 (CONVENTIONS §4)
│   ├── errors.py                # las 4 excepciones (CONVENTIONS §6)
│   ├── synth/                   # generador §8  → data/*.parquet + data/faro.db
│   ├── features/                # C0 calidad + C1 baseline personal §9.1
│   ├── engine/                  # C2 LightGBM+ensemble+conformal, C3 decisión §9,§6
│   ├── voi/                     # §7 (VoI, filtro, salvaguardas, sugerencias)
│   ├── narrative/               # SHAP→payload→plantilla/LLM §10, prompts/ versionados
│   ├── strategies/              # catálogo §12 (data)
│   └── eval/                    # métricas §13 + página pública
├── tests/
│   └── invariants/              # un test por regla de §0 (CONVENTIONS §7)
├── data/                        # faro.db (SQLite), logs.parquet, ground_truth.parquet, manifest.json
└── .github/workflows/           # CI (ruff + tests de invariantes)
```

Versionado semver; `model_version` string en cada `RiskResponse`. Licencia compatible (PI → UFRO, `CONTEXTO §8`).

**Entorno 🔒:** Python **3.12** (no 3.13 — algunas dependencias del stack van atrasadas). Node 20+.

> **Cómo se escribe el código** (regla de dependencias, propiedad de archivos, constantes, errores, tests, git) vive en [`CONVENTIONS.md`](CONVENTIONS.md). **Quién hace qué y en qué orden**, en [`TAREAS.md`](TAREAS.md). Este SPEC define *qué* hace el sistema; esos definen *cómo lo construimos*.

---

## 16. Trazabilidad — cada requisito de las bases, dónde vive

| Requisito de las bases | Sección del SPEC |
|---|---|
| Indicador de probabilidad para 24 h | §3, §4, §9 |
| Explicación comprensible y accionable | §10.1, §12 |
| Gestionar datos incompletos o faltantes | §0.5–0.6, §8.6, §9.2 (NaN nativo) |
| Datos **inconsistentes** entre fuentes | §5.1 (`consistency`) |
| Nivel de confianza según calidad de datos | §5, §9.3 |
| Incentivar / facilitar registro oportuno | §7.4 (3 toques en un día tranquilo), §7.6 (sugerencias) |
| Identificar variables de mayor valor predictivo | §7 (VoI, prospectivo), §11.3 (SHAP, retrospectivo) |
| Reducir la carga de registro | §7.4, §7.6 |
| Alertar cuando la info no es suficiente | §6 (abstención) |
| (Equidad de género — jurado InES) | §8.4, §13 `fairness_sex` |
| (Honestidad metodológica — jurado académico) | §13.1, §13.2 |
