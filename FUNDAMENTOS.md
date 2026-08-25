# FARO - Cómo funciona y por qué v1.0

## Explicación simple, cálculos reproducibles, evidencia y límites

Este documento explica `SPEC.md` sin convertir decisiones de producto en afirmaciones científicas.
No reemplaza al SPEC: ayuda a entenderlo y a defenderlo honestamente.

---

## 1. La idea completa en una página

Faro busca reducir cuatro problemas conectados:

1. Registrar todos los días es cansador.
2. Los días más difíciles suelen producir registros incompletos.
3. Con pocos outcomes reales no se puede prometer un predictor clínico confiable.
4. Una recomendación sin fuente, revisión o resultado posterior no permite aprender de forma segura.

La solución combina cuatro mecanismos:

```text
Formulario inteligente
  sugiere solo hábitos con evidencia suficiente
  y pregunta primero lo más importante

Predicción
  separa simulación, estadística personal y modelo real en sombra
  y se abstiene cuando faltan datos

RAG
  recupera literatura durante la construcción
  y producción sirve solo texto citado y revisado

Volante de datos
  separa lo que el profesional opinó,
  lo que realmente se aplicó y lo que ocurrió después
```

Ninguno de estos mecanismos autoriza diagnóstico, prescripción o acción autónoma.

---

## 2. De dónde sale cada decisión

Usamos cuatro etiquetas:

| Etiqueta | Ejemplo | Qué significa |
|---|---|---|
| Matemática `[M]` | La media de `Beta(a,b)` es `a/(a+b)` | Se deriva de la distribución |
| Evidencia `[E]` | El export local contiene 4 casos y 7 eventos | Se observa en una fuente verificable |
| Política `[P]` | Mostrar default solo si el límite supera 0.70 | Decisión conservadora del producto |
| Ingeniería `[I]` | SHA-256 para hashes | Elección técnica reproducible |

Esto importa porque expresiones como “sin umbrales inventados” son engañosas. La distribución Beta
penaliza automáticamente una muestra pequeña, pero elegir 0.70, 60 días y 10% de auditoría sigue
siendo una decisión de política.

Una política puede ser razonable sin ser una ley natural. Debe medirse y versionarse.

---

## 3. Qué sabemos hoy

El repositorio contiene, en la instantánea usada para crear el SPEC:

```text
4 casos reales
102 seguimientos diarios
37 sesiones profesionales
7 eventos registrados
2 eventos severos explícitos
0 conjunto completo de negativos explícitos
```

La cifra de 8 eventos del documento exploratorio no coincide con el CSV disponible; se adopta el
conteo verificable del archivo `[E]`.

Instantánea local verificada el 2026-08-25:

| Archivo | SHA-256 |
|---|---|
| `Datos base/1_casos_anonimizados.csv` | `F2BFC92053754C5A704A9300656A1670B99B03960FCC206AB1D2460083A404BC` |
| `Datos base/2_programas_y_objetivos.csv` | `FD3FAE8675D21E0A8E52C7F5BB5E30D613AA52513AD33F9E68D2735B77239B9D` |
| `Datos base/3_sesiones_profesionales.csv` | `972AF63D64D01F7572B4FFEDE9B1E3B09A4258A40A5FF8F7215F83CF1CA85739` |
| `Datos base/4_seguimiento_diario_tutor.csv` | `440A9AC4162C581F1C29FDDC1039ECB678BCD18B8D93144D97613F8E81D546A8` |
| `Datos base/5_eventos_desregulacion_tutor.csv` | `4892876526EEBDA3B98A464D8F7672E56B3576C06F6926A9A79ACAEA24971E79` |

Los conteos son filas de datos no vacías, excluyendo header: casos en archivo 1, sesiones en archivo
3, seguimientos en archivo 4 y eventos en archivo 5. Los dos severos son las filas cuyo campo
`intensidad` coincide exactamente con `Severa (8-10)`. Los CSV permanecen fuera de Git; la
implementación conserva este manifest no identificable y un comando de verificación, nunca los
exports.

Consecuencia:

- Podemos demostrar captura, fórmulas, abstención, RAG y auditoría.
- Podemos calcular estadísticas personales cuando existan yes/no explícitos.
- No podemos afirmar AUC, calibración o generalización clínica real.
- No podemos entrenar una regresión binaria si solo existe una clase confirmada.

El modelo LightGBM actual usa datos sintéticos. Sirve para comprobar ingeniería, no para afirmar
qué ocurrirá con niños reales.

---

## 4. Por qué no convertimos ausencia en cero

Supongamos tres días:

```text
Día 1: ocurrió una crisis -> yes
Día 2: alguien confirmó que no ocurrió -> no
Día 3: nadie respondió al llegar el deadline -> unknown
```

El día 3 no puede convertirse en `no`. Hacerlo cambiaría:

```text
tasa correcta sobre outcomes conocidos = 1 yes / 2 conocidos = 50%
tasa inventada contando silencio = 1 / 3 = 33%
```

El segundo número parece más preciso, pero contiene información inventada. Faro separa lo que una
persona reporta de la resolución derivada:

```text
reporte: yes | no | unknown
resolución: pending | yes | no | unknown | conflicted
```

La misma regla aplica a campos diarios: `false`, `0`, `unknown` y ausencia no son equivalentes.

El tiempo también importa. Si un evento severo ya ocurrió dentro de la ventana, un `yes` temprano
es concluyente. En cambio, responder `no` antes de que terminen las 24 horas solo describe lo
ocurrido hasta ese instante: se conserva como reporte provisional, pero no puede convertirse en un
negativo de entrenamiento.

Un `unknown` explícito significa "no puedo responder" y deja la resolución pending. Solo al llegar
el deadline sin una respuesta concluyente pasa a unknown. Si aparecen un yes y un no elegibles, queda
conflicted y v0.3 lo excluye del dataset incluso si después se adjudica.

Cada reporte o corrección crea otra resolución append-only derivada de la proyección vigente. Una
corrección puede cambiar el status actual, pero `ever_conflicted` nunca vuelve a false y una
corrección futura no reescribe snapshots pasados.
El inbox no mantiene otro status mutable: deriva pending/reportado/conflicto/missing desde esa
resolución y el reloj, por lo que una corrección vuelve a aparecer si corresponde.

La etiqueta `Severa (8-10)` solo documenta el valor del export. Para pedir nuevas respuestas reales
se necesita una `TargetDefinitionVersion` aprobada con pregunta, anclas y reporters elegibles; Faro
no inventa esos criterios a partir del nombre de una columna.

Cada tenant puede tener una sola definición activa efectiva. Sin ella, una sesión real puede guardar
observaciones, pero no crea episodio ni outcome request. La demo usa otra definición versionada y
outcomes sintéticos; no los mezcla con labels reales.

---

## 5. Smart defaults binarios

### 5.1 La pregunta

Para una respuesta binaria queremos estimar:

> ¿Qué tan probable es que el valor habitual vuelva a aparecer?

Ejemplos:

```text
food_changes = false
attendance_status = present frente a otra categoría no aplica por ser categórica
```

### 5.2 Prior y posterior

Con prior uniforme:

```text
p ~ Beta(1,1)
```

Después de `k` apariciones del candidato en `N` observaciones limpias:

```text
p | datos ~ Beta(1+k, 1+N-k)
```

El candidato es el valor con mayor conteo dentro del mismo tenant, sujeto, contexto
`home|therapy|school` y campo. Un empate no produce candidato.

La media es:

```text
E[p | datos] = (1+k)/(2+N)
```

El prior evita extremos inmediatos. Con 2 de 2:

```text
posterior = Beta(3,1)
media = 3/(3+1) = 75%
```

No decimos que la probabilidad verdadera “es una Beta”. Decimos que una distribución Beta
representa nuestra incertidumbre sobre el parámetro desconocido.

### 5.3 Límite inferior

Faro usa el percentil 5:

```text
lower = BetaPPF(0.05, alpha, beta)
```

Interpretación informal:

> Bajo este modelo y prior, queda 5% de masa posterior por debajo del límite.

No es lo mismo que un intervalo frecuentista de confianza.

### 5.4 Tabla corregida

| Historial | Posterior | Media | Percentil 5 | ¿Supera 0.70? |
|---|---|---:|---:|---|
| 2 de 2 | `Beta(3,1)` | 75.00% | 36.84% | No |
| 8 de 10 | `Beta(9,3)` | 75.00% | 52.99% | No |
| 32 de 40 | `Beta(33,9)` | 78.57% | 67.54% | No |
| 80 de 100 | `Beta(81,21)` | 79.41% | 72.54% | Sí |

Los cuantiles se calculan con `scipy.stats.beta.ppf`, no mediante una aproximación escrita a mano.

El 22% atribuido anteriormente a 2 de 2 no pertenece a `Beta(3,1)`. Aproximadamente 22.36% es el
límite exacto Clopper-Pearson unilateral de 95% para 2 éxitos de 2, que resuelve una pregunta
frecuentista distinta [R1, R2]. Mezclar ambos métodos vuelve inconsistente la tabla.

### 5.5 Por qué usamos el límite y no solo la media

Los cuatro ejemplos tienen medias parecidas. La diferencia está en la evidencia acumulada.

La media responde:

> ¿Cuál es la estimación central?

El límite responde:

> ¿Qué tan alto sigue siendo el valor incluso bajo una lectura conservadora del posterior?

La regla de producto es:

```text
mostrar sugerencia si lower > 0.70
```

El 0.70 es una política `[P]` motivada por el costo asimétrico de aceptar un default incorrecto. No
es un umbral clínico demostrado. Debe evaluarse con auditorías y puede cambiar en una versión futura.

---

## 6. Defaults categóricos y ordinales

Beta modela dos resultados. Para `K` categorías usamos Dirichlet.

### 6.1 Posterior Dirichlet

Con un conteo `n_j` por categoría:

```text
alpha_j = 1 + n_j
A = sum(alpha_j)
P(siguiente categoría = j | datos) = alpha_j / A
```

Ejemplo de escala con conteos:

```text
categorías = [1, 2, 3, 4, 5]
conteos    = [1, 2, 3, 32, 2]
posterior  = Dirichlet(2, 3, 4, 33, 3)
```

La categoría 4 es candidata porque tiene el mayor parámetro posterior. Para medir su incertidumbre,
su marginal es:

```text
p_4 ~ Beta(33, 2+3+4+3)
p_4 ~ Beta(33,12)
```

Se calcula `BetaPPF(0.05,33,12)` y se aplica la misma política `lower > 0.70`.

Si dos categorías empatan, Faro no sugiere ninguna.

### 6.2 Qué conserva y qué no

Dirichlet conserva que las probabilidades de todas las categorías suman 1. En una escala ordinal,
Faro conserva las anclas, pero no inventa que la distancia entre 1 y 2 sea exactamente la misma que
entre 4 y 5.

Por eso no se promedian categorías nominales ni se las codifica como un número ordenado para
facilitar un árbol.

### 6.3 Continuos y conteos

La probabilidad de observar exactamente `8.2` horas en una variable continua es cero bajo un modelo
continuo. Para crear un default habría que definir una tolerancia, por ejemplo `8.2 +/- 0.5`, pero
esa tolerancia sería otra política que hoy no está validada.

v0.3 se abstiene de sugerir:

- Horas de sueño.
- Número de despertares.
- Número de episodios.
- Texto.
- Tags.
- Outcomes.

Abstenerse evita introducir bins y tolerancias arbitrarias.

---

## 7. Cómo evitamos que el default se enseñe a sí mismo

Un ciclo peligroso sería:

```text
el sistema sugiere 4
-> la persona acepta sin revisar
-> el sistema cuenta otro 4
-> se vuelve más seguro
-> sugiere 4 todavía más
```

Por eso se distingue el modo de entrada:

| Modo | Default futuro | Modelo real primario |
|---|---:|---:|
| Manual sin default | Sí | Sí |
| Día de auditoría | Sí | Sí |
| Profesional observado | Sí | Sí |
| Importado con mapping aprobado | Sí | Sí |
| Default aceptado | No | No |
| Default editado | No | Sí |

Un valor editado sí puede describir el día, pero no entrena el sistema que decidió mostrar el
default porque estuvo expuesto a anclaje.

El control permanece vacío. La sugerencia solo se vuelve dato mediante una acción explícita.
Si el campo mostró una sugerencia y la persona escribe otro valor, el servidor siempre lo clasifica
como editado aunque el cliente intente llamarlo manual; así no vuelve a entrenar el mismo default.

Todas las fórmulas ven una proyección append-only al cutoff: de cada cadena original/correcciones se
usa solo la hoja vigente que ya se conocía. Una corrección ingresada mañana no modifica el snapshot
emitido hoy, y una rama conflictiva no se cuenta dos veces.

---

## 8. Auditoría del 10%

Para medir cuánto cambia una respuesta al mostrar sugerencias necesitamos días comparables sin
default. La tasa inicial es 10% `[P]`.

No se elige de nuevo al refrescar. Se usa:

```text
bucket = HMAC_SHA256(secret, tenant|subject|date|policy) mod 1000
audit = bucket < 100
```

Esto produce una asignación:

- Estable.
- No manipulable por refrescar.
- Aproximadamente 10% a largo plazo.
- Reproducible por el servidor con la misma política.

La tasa 10% no proviene de una ley estadística universal. Debe revisarse según volumen, carga y
precisión necesaria para medir sesgo.

---

## 9. VoI: qué preguntar primero

El default pregunta cuál valor es habitual. VoI pregunta cuál respuesta puede cambiar más la
predicción.

Para valores posibles `x_j`:

```text
q_j = probabilidad de la respuesta x_j
p_j = riesgo predicho si la respuesta fuera x_j
p_bar = sum(q_j * p_j)
```

La entropía binaria es:

```text
h(p) = -p ln(p) - (1-p) ln(1-p)
```

El VoI definido por el SPEC es:

```text
VoI(X) = h(p_bar) - sum(q_j * h(p_j))
```

Es una aproximación a información mutua, medida en nats `[M]`.

### Ejemplo calculable

Supongamos dos respuestas igualmente plausibles:

```text
q = [0.5, 0.5]
p = [0.1, 0.5]
p_bar = 0.3
```

Entonces:

```text
h(0.3) = 0.610864
h(0.1) = 0.325083
h(0.5) = 0.693147
promedio condicional = 0.5*0.325083 + 0.5*0.693147 = 0.509115
VoI = 0.610864 - 0.509115 = 0.101749 nats
```

Si ambas respuestas produjeran el mismo riesgo, VoI sería cero.

En v0.3, `q` no queda a criterio de cada implementación: es la media posterior Beta/Dirichlet de la
misma historia limpia de 60 días, fuente y campo. `p_j` es una consulta condicional que mantiene el
resto del snapshot; no representa una intervención causal. Campo o categoría no soportada, conflicto
o modelo incapaz de responder produce `voi=null`.

Cuando no existe un modelo condicional real apto, Faro devuelve `voi=null`. Cero significaría que
se calculó y no aporta información; `null` significa que no se puede calcular honestamente.

VoI tampoco puede desplazar preguntas vencidas. El formulario destaca primero antigüedad, después
una exploración determinista en un weekday HMAC semanal y recién entonces VoI. Se persiste cada
`QuestionPresentation`; aparecer solo en la cola no cuenta como haber preguntado. Si hay más campos
vencidos que los 2 o 3 cupos normales, la lista se amplía hasta incluirlos.

---

## 10. Calidad del dato

Faro separa calidad de riesgo:

```text
DQI = coverage * recency * consistency
```

### 10.1 Coverage

Se observan cinco campos durante 14 días:

```text
sleep_quality
wake_state
gi_status
medication_adherence
daily_regulation_state
```

Hay 70 oportunidades de observación:

```text
5 campos * 14 días = 70
```

Coverage suma los pesos de procedencia y divide por 70. Un sujeto nuevo no recibe calidad alta por
haber completado un solo día. La ventana son fechas locales `[D-13,D]` y usa la proyección vigente
al cutoff.

### 10.2 Recency

```text
recency = exp(-ln(2) * days / 2)
```

Ejemplos:

```text
0 días -> 1.00
2 días -> 0.50
4 días -> 0.25
```

La vida media de dos días es política del producto, no resultado clínico.
Si no existe ninguna observación válida en la ventana, la recencia es cero.

### 10.3 Consistency

Dos fuentes iguales producen desacuerdo cero. Para ordinales 1-5:

```text
disagreement = |a-b|/4
```

Para categorías:

```text
0 si iguales
1 si distintas
```

```text
consistency = max(0.5, 1 - mean_disagreement)
```

El piso 0.5 es política. El sistema no promedia categorías para resolver el conflicto; conserva las
dos observaciones.

### 10.4 Por qué multiplicar

La multiplicación hace que un componente muy pobre limite el total. Una coverage perfecta no
compensa un registro muy antiguo.

Ejemplo ilustrativo:

```text
coverage = 0.80
recency = 0.50
consistency = 0.90
DQI = 0.80 * 0.50 * 0.90 = 0.36
```

Los valores del ejemplo no describen un caso real.

v0.3 no convierte el DQI en una barrera numérica universal. Cada track se abstiene por condiciones
explícitas, como falta de outcomes o conflicto. Definir un corte de DQI exigiría otra política
versionada y evidencia de validación; mientras tanto, el índice resume calidad y orienta qué dato
falta, no decide riesgo.

---

## 11. Desviación personal robusta

La media y desviación clásica cambian mucho con outliers. Faro usa mediana y MAD:

```text
median = mediana(x)
MAD = mediana(|x - median|)
robust_scale = (1 / NormalPPF(0.75)) * MAD
robust_z = (x - median) / robust_scale
```

Como `1/NormalPPF(0.75) = 1.482602...`, el factor hace comparable el MAD con la desviación estándar
bajo una distribución normal `[M]`. No convierte el dato en normal; R17 documenta la definición y
robustez del MAD, no se usa como fuente del factor.

Ejemplo:

```text
historia = [1,2,2,3,4]
median = 2
MAD = 1
valor actual = 5
robust_z = (5-2)/(1.4826*1) = 2.023
```

El corte `|z| >= 2` es una política de apertura del formulario, no diagnóstico.

Si MAD es cero o hay menos de cinco observaciones, el sistema no fabrica un z-score.

---

## 12. Predicción a 24 horas

### 12.1 Ventana

Si el formulario cierra a las 20:00:

```text
target: después de hoy 20:00, hasta mañana 20:00 inclusive
deadline de reporte: pasado mañana 20:00
```

El target dura 24 horas. El inicio abierto evita usar el mismo hecho como predictor y label; las 48
horas solo dan tiempo adicional para reportarlo.

La sesión guarda dos tiempos distintos: `opened_at` cuando se abre y `submitted_at` cuando el
servidor acepta el envío. El episodio fija
`as_of_at = prediction_at = submitted_at`; ningún dato posterior puede entrar al snapshot ya
emitido.

Si otra sesión cierra antes de terminar ese target, guarda observaciones y se enlaza al episodio
abierto: no crea otra ventana solapada. Así un mismo evento no se cuenta varias veces por haber
enviado formularios desde distintos contextos.

### 12.2 Track sintético

El LightGBM actual se entrenó con un generador cuyos coeficientes fueron elegidos por diseño. Que el
modelo recupere esos patrones demuestra que el pipeline funciona dentro de la simulación, no que
prediga una población real.

Por eso solo usa `simulation_only`. La UI demo puede mostrar su `simulation_score`, pero mantiene
`probability=null`: no lo rotula como probabilidad clínica.

### 12.3 Baseline personal

Con `e` outcomes yes y `n-e` no explícitos:

```text
p | D ~ Beta(1+e, 1+n-e)
```

Si hubiera 2 yes y 24 no explícitos:

```text
n = 26
posterior = Beta(3,25)
media = 3/28 = 10.71%
```

El cálculo solo es válido si los 24 negativos fueron confirmados en episodios primarios con la misma
definición de target y care mode. Veinticuatro silencios no sirven, ni tampoco conflictos
adjudicados para conveniencia.

Este número es una tasa personal por oportunidades de formulario observadas. Puede estar sesgada por
quién y cuándo completa el formulario; no es incidencia diaria ni una probabilidad contextual
completa de mañana.

### 12.4 Challenger logístico

El challenger pregunta si desviaciones del día aportan información sobre la tasa personal:

```text
logit(p_t) = logit(p_base_t)
           + intercepto de calibración
           + beta_1 * desviación de sueño
           + beta_2 * desviación de regulación
```

Se usan dos predictores preregistrados para evitar selección oportunista. Eso no significa que ocho
eventos sean suficientes.

Cada indicador usa 1 solo para la categoría positiva y 0 para un complemento observado. Ausencia,
`unknown`, `other` o conflicto producen null y abstención, nunca cero. Las tasas personales usan 30
días previos del mismo sujeto, fuente y campo, con al menos cinco días observados.

El offset tiene coeficiente fijo 1. Se penalizan solo los dos coeficientes con L2; el intercepto no.
El SPEC fija la función objetivo, `LeaveOneGroupOut`, el significado de lambda y el optimizador para
que dos implementaciones no llamen "el mismo modelo" a resultados distintos.

La heurística histórica de diez eventos por predictor proviene de estudios de simulación y no es
una garantía universal [R5-R7]. Métodos modernos recomiendan calcular tamaño muestral considerando
prevalencia, parámetros, sobreajuste esperado y precisión [R8]. Con cuatro sujetos y una sola clase
confirmada, el modelo no es entrenable ni evaluable.

Repetir Random Forest con 200 semillas mide inestabilidad, pero no crea información. Por eso se
elimina como selector del modelo v0.3.

### 12.5 Sombra

Un modelo en sombra:

- Calcula resultados para evaluación interna.
- No cambia lo que ve una familia.
- No reemplaza al modelo desplegado.
- No se promociona automáticamente.

Promocionarlo exigiría otro SPEC y validación prospectiva.

---

## 13. Cómo evaluamos una probabilidad

### 13.1 Brier score

```text
Brier = mean((p_i - y_i)^2)
```

Ejemplo:

```text
y = [1,0]
p = [0.8,0.3]
Brier = ((0.8-1)^2 + (0.3-0)^2)/2
      = (0.04 + 0.09)/2
      = 0.065
```

Menor es mejor. Debe compararse contra una tasa base, no leerse aislado [R9].

### 13.2 Precision-Recall

Cuando los positivos son raros, una accuracy alta puede lograrse diciendo siempre “no”. Las curvas
Precision-Recall muestran mejor el compromiso sobre la clase positiva [R3, R4].

Faro usa `average_precision_score` de scikit-learn. No usa una implementación casera que dependa del
orden de empates.

### 13.3 Agrupación por sujeto

Los días de un mismo niño están correlacionados. Si días del mismo niño aparecen en train y test,
el modelo puede reconocer patrones personales y aparentar generalización.

Por eso:

- Splits completos por sujeto.
- Transformaciones dentro del fold.
- Bootstrap por sujeto.
- Evaluación temporal sin usar datos futuros.

La validación estructurada debe respetar la dependencia de los datos [R10].

### 13.4 Calibración

Un modelo calibrado que dice 20% debería observar aproximadamente 20 outcomes positivos entre
casos comparables con esa predicción. Se reportan intercepto y pendiente de calibración cuando los
datos permiten estimarlos [R18].

Con una sola clase no hay AUC ni calibración estimable. La salida correcta es `not_estimable`.

### 13.5 Transparencia

TRIPOD+AI pide reportar población, outcome, predictores, manejo de datos, evaluación y limitaciones
de modelos predictivos [R11]. Cada reporte Faro incluye origen, dataset hash, modelo y limitaciones.

### 13.6 Protocolo v1

Faro no deja la evaluación como una lista de métricas. La versión v1 usa outer
`LeaveOneGroupOut(subject_id)` y selecciona lambda solo con folds agrupados dentro de cada outer
train. Luego usa 2.000 remuestreos de sujetos con seed 42 e intervalo percentil 90%.
Si menos de 80% de réplicas son válidas, no publica intervalo. Métricas de grupo se suprimen por
debajo de 10 sujetos, 5 positivos o 5 negativos. `Alert-budget recall` queda `not_estimable` porque
v0.3 no tiene definición de alerta ni política de decisión.

Estas métricas de desarrollo no bastan para declarar `shadow_evaluated`: ese estado requiere un
periodo prospectivo temporal preregistrado y separado de los datos que eligieron lambda. Cada reporte
usa una única `target_definition_version`; v0.3 no agrupa preguntas o anclas distintas.

Para el sujeto outer, sus outcomes anteriores al cutoff de cada episodio sí pueden construir su
baseline personal, igual que en uso real; nunca ajustan coeficientes ni eligen lambda. El protocolo
guarda cuándo se reveló cada outcome y excluye landmarks sin historia mínima.

---

## 14. Cómo funciona el RAG

### 14.1 Qué es RAG

RAG combina recuperación desde una memoria documental explícita con generación. Lewis et al.
describieron este enfoque para tareas intensivas en conocimiento [R12]. Recuperar fuentes puede
mejorar especificidad y procedencia, pero no garantiza corrección.

Faro separa autoría y runtime.

### 14.2 Autoría offline

```text
documento permitido y hasheado
-> extracción/chunking declarados en build manifest
-> fragmentos con localizador
-> BM25
-> retrieval denso opcional
-> fusión RRF
-> 8 fragmentos
-> borrador LLM opcional
-> verificación literal
-> revisión de evidencia
-> revisión clínica
-> versión activa
```

BM25 aporta coincidencia lexical. El retrieval denso aporta similitud semántica. RRF fusiona
rankings sin tratar sus scores como si estuvieran en la misma escala [R19, R20].

Cada build registra bytes originales, extractor/OCR, normalización, chunker, modelo, librerías y
tie-breaks. Si no hay embedding aprobado, `lexical_only` usa BM25 top 8 y lo declara; no finge un
pipeline híbrido. En modo híbrido, RRF suma `1/(60+rank)` con ranks desde 1.

Sets y estrategias usan el mismo `ScenarioPredicate` estructurado. Ambos se revisan, ambos se
evalúan fail-closed y el tenant tiene un solo catálogo activo efectivo; no hay conversión implícita
desde campos a tags ni selección silenciosa de "la versión más nueva".

El escenario se construye con una función única desde la sesión enviada y la profile version del
snapshot. Usa solo campos enum allowlisted, contexto, profile y contraindicaciones; omite unknown y
se abstiene ante conflicto. P2 nunca reconstruye esas precedencias por su cuenta.

### 14.3 Runtime

En producción:

```text
escenario categórico
-> match con RecommendationSet activo
-> filtro de tags/contraindicaciones
-> texto previamente aprobado
-> citas exactas
```

No se llama al LLM. El runtime devuelve texto `action_text_es` ya revisado y cada claim apunta a
citas literales verificadas. Una estrategia activa no puede tener claims o citas vacíos. Esto
garantiza consistencia por versión, no verdad clínica absoluta.

La excepción al veto de texto libre es estrictamente documental: solo literatura versionada, con
derechos y hash, puede fragmentarse o entrar a embeddings y prompts de autoría. Notas, mensajes y
texto escrito por cuidadores o profesionales nunca entran a ese pipeline.

Una solicitud nacida de un caso permanece cifrada en la frontera clínica. Para usarla en curaduría
se requiere consentimiento o base institucional separada, y un privacy reviewer certifica una
consulta generalizada. Solo esa consulta sin atributos de caso entra a BM25, embeddings o LLM;
tener grant de lectura no autoriza el uso secundario.

Las reviews de evidencia, clínica y activación guardan actor acreditado, decisión y hash exacto del
objeto. Son distintas de la review profesional de una recomendación para un caso.

### 14.4 Por qué no prometemos cero alucinación

Incluso con RAG pueden ocurrir:

- Fragmentos irrelevantes.
- Interpretaciones incorrectas.
- Fuentes desactualizadas.
- Aplicación fuera de contexto.
- Errores introducidos durante revisión.

La garantía real de Faro es trazabilidad:

```text
qué documento
qué versión
qué fragmento
qué texto
qué revisores
qué catálogo
```

NIST AI RMF y WHO recomiendan gobernanza, trazabilidad, responsabilidades y gestión continua del
riesgo en sistemas de IA [R13, R14].

### 14.5 Por qué revisar clínicamente

NICE CG170 enfatiza atención individualizada, equipos multidisciplinarios, consideración del
ambiente, sueño, condiciones físicas, cambios de rutina y preferencias [R15]. Esto respalda revisar
contexto y coordinación; no respalda automáticamente una estrategia específica generada por Faro.

Una cita general no autoriza copiar una intervención precisa. Cada acción necesita su fragmento y
revisión correspondiente.

---

## 15. Cómo mejora con feedback

Faro registra tres cosas distintas:

```text
Review: ¿el profesional considera aplicable la recomendación?
Execution: ¿se aplicó realmente?
Outcome: ¿qué ocurrió en la ventana de 24 horas?
```

Si llegan tres estrategias, cada una tiene su propia review y execution. Una sustitución crea un
`HumanPlanVersion` del caso sin heredar citas RAG; no edita la estrategia global.

Casos informativos:

| Review | Execution | Outcome | Qué permite decir |
|---|---|---|---|
| Aprobada | Aplicada | No event | Asociación observada, no eficacia |
| Aprobada | Aplicada | Event | Caso prioritario para revisión |
| Aprobada | No aplicada | Cualquiera | No evalúa exposición |
| Rechazada | No aplicada | Event | No prueba que la estrategia habría funcionado |
| Sustituida | Aplicada | No event | Describe el plan humano, no la estrategia RAG |

El feedback mejora así:

- Rechazos repetidos priorizan revisión.
- Ediciones de caso crean plan humano y propuesta de curaduría; solo autoría puede crear un draft.
- Escenarios sin cobertura guían curaduría.
- Outcomes permiten análisis descriptivo por versión.
- Ninguna señal cambia producción sin revisión y activación manual.

La fórmula `similitud + lambda*aceptación` no se usa en producción v0.3. La aceptación mide
preferencia profesional y puede contener sesgos. Se reporta, pero no reemplaza relevancia documental
ni outcome.

### 15.1 Human-in-the-loop correcto

Si un profesional revisa después de que la familia ya aplicó una recomendación, es supervisión
posterior, no control humano previo.

Faro exige:

```text
recomendación pendiente -> profesional -> aprobada -> visible/aplicable
```

Un borrador puede mostrarse al profesional, nunca como recomendación aprobada a la familia.

Para asociar una execution con el outcome, la aprobación debe preceder la aplicación, y la aplicación
debe ocurrir antes del fin del target y, si hubo evento, antes del evento. Reportes retrospectivos se
conservan, pero no se convierten en exposición válida de esa ventana.
Una estrategia requiere review activa `approved`; un plan humano requiere
`human_plan_substituted`. Rechazada, deferred o not applicable nunca se vuelve exposición por tener
timestamps plausibles.

Antes de aprobar, mostrar o aplicar, Faro vuelve a verificar que fuente, estrategia, set y catálogo
sigan activos. Una suspensión conserva la instancia para auditoría, pero la vuelve no accionable.

---

## 16. Privacidad y anonimización

Quitar nombre y RUT no vuelve automáticamente anónimo un registro. Un conjunto de atributos puede
seguir siendo vinculable a una persona; en ese caso es seudonimizado.

Faro reduce exposición mediante:

- Corpus separado de datos clínicos.
- Cero historiales en el índice RAG.
- Cero notas o texto libre de usuarios en prompts; solo fragmentos documentales autorizados.
- Escenarios categóricos mínimos.
- Procesamiento local en autoría.
- Tenant, rol, acreditación y grant específico del sujeto en cada acceso.
- Auditoría sin payload clínico.

Estas medidas reducen riesgo; no sustituyen una evaluación jurídica, consentimiento, retención,
cifrado y control de acceso.

Consentimiento también tiene purpose y tiempo. Cada run de training/evaluation reautoriza a sus
sujetos; una revocación impide reutilizar un snapshot viejo para trabajo nuevo y suspende artefactos
reales dependientes hasta revisión o retraining. Un grant de atención no autoriza modelado ni
curaduría.

Faro tampoco es monitoreo de emergencias. La interfaz debe indicar que nadie espere una alerta de la
app y que, ante peligro inmediato, se sigan sin demora los protocolos locales de emergencia o
resguardo. Esta regla no depende del score ni de una abstención.

WHO establece que ética, derechos humanos y responsabilidad deben formar parte del diseño y uso de
IA en salud [R14].

---

## 17. Qué podemos afirmar

| Afirmación permitida | Afirmación no permitida todavía |
|---|---|
| El posterior Beta distingue poca de mucha evidencia | “2 de 2 tiene límite bayesiano 22%” |
| El formulario puede abstenerse de sugerir | “No usamos umbrales elegidos” |
| VoI ordena preguntas cuando existe modelo apto | “VoI demuestra utilidad clínica” |
| La simulación prueba integración y leakage implementado | “El modelo está validado en niños reales” |
| El baseline resume tasa por oportunidades observadas | “Es incidencia diaria o el riesgo contextual completo de mañana” |
| El challenger está preregistrado y en sombra | “Dos predictores funcionan con ocho eventos” |
| RAG aporta fragmentos y trazabilidad | “RAG elimina las alucinaciones” |
| Un catálogo cerrado mejora consistencia | “Elimina toda contraindicación” |
| El profesional revisa antes de mostrar a familia | “La IA decide la intervención” |
| Outcomes permiten análisis observacional | “Sabemos que la sugerencia causó el resultado” |
| Procesamiento local reduce transferencias | “El payload es legalmente anónimo” |
| El coste marginal de runtime es bajo | “El coste total es cero” |

---

## 18. Cómo se verifica que nada fue inventado

Para cada salida se puede reconstruir:

### Default

```text
observaciones elegibles
conteos
prior
posterior
cuantil
policy version
presentation ID
```

### Predicción

```text
episodio
as_of_at
episode role y target definition version
IDs de observación
proyección de correcciones conocida al cutoff
feature version
track/model version
input data origin
intervalo
razón de abstención
```

### Recomendación

```text
scenario hash
catalog version
strategy version
action text hash y claims
fragment IDs
document hashes
evidence reviewer
clinical reviewer
review/execution/outcome
```

### Evaluación

```text
dataset hash
subject split
model version
evaluation protocol version
metric implementation
interval method
limitations
```

Si falta una pieza, la salida se abstiene o queda como draft.

---

## 19. Referencias

Fuentes consultadas y claims usados:

### Estadística y evaluación

- `[R1]` Clopper, C. J., & Pearson, E. S. (1934). The Use of Confidence or
  Fiducial Limits Illustrated in the Case of the Binomial.
  https://doi.org/10.1093/biomet/26.4.404
- `[R2]` Brown, L. D., Cai, T. T., & DasGupta, A. (2001). Interval Estimation for a
  Binomial Proportion. https://doi.org/10.1214/ss/1009213286
- `[R3]` Davis, J., & Goadrich, M. (2006). The Relationship Between Precision-Recall
  and ROC Curves. https://doi.org/10.1145/1143844.1143874
- `[R4]` Saito, T., & Rehmsmeier, M. (2015). The Precision-Recall Plot Is More
  Informative than the ROC Plot When Evaluating Binary Classifiers on Imbalanced
  Datasets. https://doi.org/10.1371/journal.pone.0118432
- `[R5]` Peduzzi, P. et al. (1996). A simulation study of the number of events per
  variable in logistic regression analysis. https://doi.org/10.1016/S0895-4356(96)00236-3
- `[R6]` Vittinghoff, E., & McCulloch, C. E. (2007). Relaxing the Rule of Ten Events
  per Variable in Logistic and Cox Regression. https://doi.org/10.1093/aje/kwk052
- `[R7]` van Smeden, M. et al. (2016). No rationale for 1 variable per 10 events
  criterion for binary logistic regression analysis. https://doi.org/10.1186/s12874-016-0267-3
- `[R8]` Riley, R. D. et al. (2019). Minimum sample size for developing a
  multivariable prediction model: Part II. https://doi.org/10.1002/sim.7992
- `[R9]` Brier, G. W. (1950). Verification of forecasts expressed in terms of
  probability. https://doi.org/10.1175/1520-0493(1950)078%3C0001:VOFEIT%3E2.0.CO;2
- `[R10]` Roberts, D. R. et al. (2017). Cross-validation strategies for data with
  temporal, spatial, hierarchical, or phylogenetic structure.
  https://doi.org/10.1111/ecog.02881
- `[R11]` Collins, G. S. et al. (2024). TRIPOD+AI statement.
  https://doi.org/10.1136/bmj-2023-078378
- `[R17]` NIST/SEMATECH e-Handbook, Measures of Scale: MAD.
  https://www.itl.nist.gov/div898/handbook/eda/section3/eda356.htm
- `[R18]` Van Calster, B. et al. (2019). Calibration: the Achilles heel of predictive
  analytics. https://doi.org/10.1186/s12916-019-1466-7

### RAG, gobernanza y práctica clínica

- `[R12]` Lewis, P. et al. (2020). Retrieval-Augmented Generation for
  Knowledge-Intensive NLP Tasks.
  https://proceedings.neurips.cc/paper/2020/hash/6b493230205f780e1bc26945df7481e5-Abstract.html
- `[R13]` NIST (2023). Artificial Intelligence Risk Management Framework 1.0.
  https://doi.org/10.6028/NIST.AI.100-1
- `[R14]` World Health Organization (2021). Ethics and governance of artificial
  intelligence for health. https://www.who.int/publications/i/item/9789240029200
- `[R15]` NICE CG170. Autism spectrum disorder in under 19s: support and management.
  https://www.nice.org.uk/guidance/cg170/chapter/recommendations
- `[R16]` MINSAL/DIPRECE. Orientaciones técnicas para la atención integral de
  personas con diagnóstico de trastorno del espectro autista.
  https://diprece.minsal.cl/orientaciones-tecnicas-atencion-integral-de-personas-con-diagnostico-de-trastorno-del-especto-autista-a-lo-largo-del-curso-de-vida/
- `[R19]` Robertson, S., & Zaragoza, H. (2009). The Probabilistic Relevance
  Framework: BM25 and Beyond. https://doi.org/10.1561/1500000019
- `[R20]` Cormack, G. V., Clarke, C. L. A., & Büttcher, S. (2009). Reciprocal Rank
  Fusion outperforms Condorcet and individual rank learning methods.
  https://doi.org/10.1145/1571941.1572114
- `[R21]` Mitchell, M. et al. (2019). Model Cards for Model Reporting.
  https://doi.org/10.1145/3287560.3287596

### Notas de uso de las referencias

- Las guías NICE y MINSAL justifican consultar factores individuales, ambiente, condiciones
  coexistentes y coordinación profesional. No validan el predictor Faro.
- La literatura de RAG justifica retrieval+generación, no garantiza ausencia de errores.
- La literatura de sample size impide defender un modelo con cuatro sujetos; no fija un número
  mágico universal para el futuro.
- NIST y WHO sustentan gobernanza y trazabilidad; no certifican la implementación.

---

## 20. Resumen final

La mejor combinación no reemplaza una técnica por otra:

```text
Beta/Dirichlet decide si una sugerencia habitual es suficientemente confiable.
VoI decide qué pregunta puede ser más informativa.
DQI resume cobertura, recencia y consistencia; no impone un corte no registrado.
El track predictivo declara qué puede estimar y se abstiene si no puede.
RAG recupera evidencia durante autoría.
El catálogo revisado controla lo que se sirve.
Review, execution y outcome permiten aprender sin confundir preferencia con efecto.
```

Cuando la evidencia no alcanza, la respuesta correcta de Faro es “todavía no se puede saber”.
