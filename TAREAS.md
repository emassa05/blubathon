# FARO — División del trabajo entre 2 personas
### Dominios separados · quién hace qué · criterios de terminación · v3.0

> Lee primero [`CONVENTIONS.md`](CONVENTIONS.md) §3 (mapa de propiedad). Este documento es el **reparto y el orden**; aquel es **las reglas**.
>
> **Secuencia:** primero el backend completo y funcional. El frontend arranca después, cuando el diseño esté hecho.
>
> **Cada tarea tiene un "✅ Listo cuando".** Una tarea no está terminada hasta que cumple todos sus puntos. Nada se entrega a medias.

---

## FASE 1 · BACKEND

### Los dos dominios

| | **P1 · DATOS Y MODELO** | **P2 · DECISIÓN Y SALIDA** |
|---|---|---|
| Pregunta que responde | *¿de dónde salen los datos y cómo se calcula el número?* | *¿qué se pregunta, qué se responde y cómo se mide?* |
| Dueño de | `packages/shared`, `ml/spec_constants`, `ml/errors`, `ml/synth`, `ml/features`, `ml/engine`, `apps/api/main.py`, `apps/api/routes/` | `ml/voi`, `ml/narrative`, `ml/strategies`, `ml/eval`, `apps/api/store/`, `tests/invariants` |
| Peso relativo | ~24 h | ~22 h |

**Quién es P1:** quien esté más cómodo con pandas y scikit-learn. La cadena generador → features → modelo es la de mayor riesgo técnico.

---

### 🚦 HITO 0 · P1 — lo único que bloquea al otro

Es lo primero que se hace, antes que cualquier otra cosa. No es el motor: es **el contrato en código**, para que P2 no dependa nunca de P1.

**Entrega:**
1. `ml/spec_constants.py` — todos los números 🔒 del SPEC (CONVENTIONS §4).
2. `packages/shared/` — `DailyLog`, `RiskResponse`, `VoIResponse`, `ExplainResponse` en pydantic.
3. `ml/errors.py` — las 4 excepciones (CONVENTIONS §6).
4. `ml/engine/baseline.py` — ver abajo.
5. `fixtures/` — 3 niños: uno tranquilo, uno de riesgo alto, uno que fuerza abstención.

**✅ Listo cuando:**
- Un test verifica que cada constante coincide con su valor en el SPEC.
- Los modelos pydantic validan **los ejemplos literales** del SPEC §2.4, §11.1, §11.2 y §11.3 sin modificarlos.
- `predict_baseline` devuelve una `p` **distinta** al variar `sleep_hours` (si no, el VoI de P2 daría varianza cero).
- Los 3 fixtures se cargan y validan contra el schema.
- Está en `main`.

### El desbloqueo: `ml/engine/baseline.py`

Todo el trabajo de P2 necesita **una función que prediga** — pero no necesita la buena.

```python
def predict_baseline(features: dict) -> float:
    """Regresión logística a mano con los coeficientes de SPEC §8.2.
    Determinista, sin entrenar, microsegundos."""
```

P2 construye el VoI completo desde el primer momento, con varianza real y testeable.

**No es código desechable:** el SPEC §13 exige baselines de comparación obligatorios. Cuando P1 termine el LightGBM se cambia un import, y este se queda como término de comparación en la lámina de evaluación.

---

## P1 · DATOS Y MODELO

### 1.1 · Generador causal sintético — §8 · ~5 h

DAG, coeficientes, ventanas de arrastre, perfiles de niño, modelo de observación, missingness NMAR.

**✅ Listo cuando:**
- Genera 200 niños × 180 días con `RANDOM_SEED=42`.
- La base rate observada de `crisis_occurred` cae en `[0.08, 0.12]` (objetivo 0.10, §8.1).
- Las 9 variables con `w_v ≥ 0.5` tienen distribuciones dentro de sus rangos legales (§2.1).
- El missingness es **mayor en días de `L(t)` alto** — verificado con un test, no a ojo (§8.6).
- Los perfiles se cumplen: 60/40 support_level, 70/30 verbal, 30% chronic_gi, 50/50 sexo (§8.4).
- El camuflaje femenino atenúa las señales observadas ×0.70 con `L` idéntica.
- **Dos corridas seguidas producen archivos idénticos byte a byte.**
- Emite `logs.parquet`, `ground_truth.parquet` y `manifest.json` con semilla y parámetros.
- Todo campo presente lleva `field_provenance = "observed"`; todo ausente, `unknown`.

### 1.2 · C0 · Calidad del dato (ICD) — §5, §2.5 · ~4 h

**✅ Listo cuando:**
- `compute_icd(history, date)` devuelve `{icd, coverage, recency, consistency}`, los cuatro en `[0,1]`.
- `coverage` usa `PROVENANCE_WEIGHTS` — un día entero en `assumed_stable` da la mitad de cobertura que uno `observed`.
- `recency` decae con vida media de 2 días (`λ = ln(2)/2`).
- `consistency` devuelve 1.0 con una sola fuente y penaliza el desacuerdo entre fuentes con solape.
- Test de cada componente por separado + un historial perfecto que da `ICD ≈ 1.0` y uno vacío que da `≈ 0`.

### 1.3 · C1 · Baseline personal (n-of-1) — §9.1 · ~4 h

**✅ Listo cuando:**
- Calcula z-score robusto (mediana / MAD) por variable, ventana 14–30 días, ajustado por día de semana.
- Devuelve `NaN` — nunca `0` — cuando hay menos de 5 observaciones de esa variable.
- Anomalía multivariante por Mahalanobis robusto.
- Test: una serie constante da `z = 0`; un valor a 3 desviaciones da `|z| > 2`.
- Genera las features del §9.1: valor crudo, z-score, `*_missing`, lags, medias móviles 3d/7d, tendencia 7d.

### 1.4 · C2 · Modelo y confianza — §9.2, §9.3 · ~5 h

**✅ Listo cuando:**
- LightGBM entrena con la config fija del §9.2, **sin imputar** (NaN nativo).
- Splits **por `child_id`** 60/20/20 con semilla 42 — ningún niño aparece en dos particiones (test).
- Calibración isotónica ajustada en el fold de validación.
- Ensemble bootstrap `B=20`, semillas 42–61 → `p`, `σ`, `interval` al 80%, `width`.
- **Test: la matriz que recibe LightGBM todavía contiene `NaN`** (regla §0.5).
- `auc_pr` en test supera la frecuencia base y los dos baselines obligatorios del §13.
- MAPIE conforme a `α=0.10` calculado y reportado (no gobierna la UI).

### 1.5 · C3 · Decisión y abstención — §4, §5.3, §6 · ~2 h

**✅ Listo cuando:**
- Mapea `p` → banda con los cortes exactos del §4.
- Etiqueta de confianza según la tabla §5.3, combinando `ICD` y `width`.
- Abstención por las **tres** condiciones del §6, cada una probada por separado.
- Al abstenerse devuelve `requested_variables` no vacío.
- Devuelve un `RiskResponse` que valida contra `packages/shared`.
- **Test de bordes: `0.1499`→verde · `0.15`→ámbar · `0.3499`→ámbar · `0.35`→rojo.**

### 1.6 · Rutas de la API — §11 · ~2 h + ~2 h

Los 8 endpoints conectados al motor real.

**✅ Listo cuando:**
- Los 8 responden y validan entrada con pydantic.
- Las 4 excepciones se traducen a `{"error": {"code", "message_es"}}` — y **solo aquí** (CONVENTIONS §6).
- **La abstención devuelve HTTP 200**, no un error.
- `/ingest` rechaza `assumed_stable` con valor no nulo → `provenance_conflict`.
- OpenAPI se genera en `/docs` y describe los 8 endpoints.
- `import-linter` confirma que `ml/` no importa nada de `apps/`.

---

## P2 · DECISIÓN Y SALIDA

### 2.1 · Persistencia SQLite — §1, §2.5 · ~3 h

**✅ Listo cuando:**
- El esquema refleja `DailyLog` (§2.1) con `field_provenance` como tabla o JSON.
- `/ingest` acepta un log o una lista, y es idempotente por `(child_id, date, source)`.
- Rechaza `assumed_stable` con valor no nulo lanzando `ContractViolationError`.
- `crisis_occurred` acepta `null` y **nunca** lo convierte a `false` por omisión (§3). Test explícito.
- Siembra `faro.db` desde `logs.parquet`.
- Consultar el historial de un niño devuelve orden cronológico y campos ausentes como `None`, nunca `0`.
- Vive en `apps/api/store/` — `ml/` no toca disco (CONVENTIONS §2).

### 2.2 · VoI base — §7.1 · ~3 h

**✅ Listo cuando:**
- `compute_voi(history, date)` devuelve la lista de variables **faltantes** ordenada por VoI descendente.
- `K = 20` muestras, reproducible con semilla 42.
- Las variables ya presentes ese día no aparecen en el ranking.
- Test: una variable que no mueve la `p` da `VoI ≈ 0`; una que la mueve mucho da `VoI` alto.
- **Las imputaciones no salen de este módulo** (regla §0.5): el modelo nunca las ve.

### 2.3 · VoI avanzado — §7.2, §7.3, §7.6 · ~3 h

**✅ Listo cuando:**
- `σ_muestreo = MAD · (1 + κ·d_v)` con `κ = 0.15`; a `d_v = 7` la dispersión es ~2×.
- **Test: la misma variable con `d_v=0` da VoI menor que con `d_v=8`.**
- Con menos de 10 días de historia o menos de 5 observaciones de `v`, usa el prior poblacional (§8.4).
- Las muestras se clipean al rango legal y se redondean al tipo correcto.
- Recálculo secuencial: responder una pregunta **cambia el ranking** de las siguientes (test).
- Sugerencia = mediana personal de 14 días, y **solo si hay ≥5 observaciones**; si no, `null`.

### 2.4 · Formulario y salvaguardas — §7.4, §7.5 · ~3 h

**✅ Listo cuando:**
- `build_form(...)` devuelve el `VoIResponse` completo del §11.2, incluido el **BLOQUE 0** (`closing_question_es`, `closing_target_date`).
- `closing_question_es` va en `null` si el target del día anterior ya fue reportado, y presente si es `null` — test de ambos casos.
- `highlighted` tiene 2 elementos, o 3 si `ICD < 0.5`.
- **Techo de antigüedad:** una variable de `HIGH_WEIGHT` con `d_v ≥ 7` entra a `highlighted` desplazando la de menor VoI — el bloque **no crece**.
- Desempate del techo: `w_v` → `d_v` → alfabético (test con dos variables empatadas).
- **Cuota de exploración:** `hash(child_id+date) mod 7 == 0`, determinista y reproducible.
- **Precedencia:** con techo y exploración el mismo día, manda el techo.
- **Gatillo por anomalía:** `|z| ≥ 2.0` despliega la cola aunque el filtro diga "No".
- Con filtro en "No", las variables de la cola reciben `assumed_stable` **sin valor**.
- Cada salvaguarda tiene su propio test.

### 2.5 · Narrativa — §10.1, §10.2 · ~4 h

**La plantilla determinista se construye primero. El LLM va encima.**

**✅ Listo cuando:**
- La plantilla produce `headline_es`, `explanation_es`, `actions_es` válidos **sin LLM**.
- `explanation_es` ≤ 60 palabras; `actions_es` ≤ 3 y **subconjunto** de `candidate_strategies`.
- Solo nombra drivers presentes en el payload — no inventa causas (test).
- El LLM 3B se intenta, reintenta una vez si no valida el schema, y **cae a plantilla**.
- `narrative_source` refleja cuál se usó (`llm` | `template`).
- **Test: con Ollama apagado, `/explain` devuelve una narrativa válida.**
- Los prompts viven versionados en `ml/narrative/prompts/`.

### 2.6 · Catálogo de estrategias — §12.1, §12.2 · ~1 h

**✅ Listo cuando:**
- Las 10 estrategias con su `id` y `label_es` exactos del §12.1.
- El mapeo driver → estrategias del §12.2, completo.
- `build_candidates(drivers)` deduplica y devuelve máximo 4.
- Test: cada uno de los 6 drivers del §12.2 produce al menos una estrategia, y ninguna estrategia devuelta está fuera de la lista cerrada.

### 2.7 · Suite de invariantes — §0 · ~2 h

**✅ Listo cuando:**
- Existe **un test por cada una de las 13 reglas** del SPEC §0, nombrado con su `§`.
- Incluye los bordes de banda (§4) y el conflicto de procedencia (§2.5).
- `import-linter` verifica la regla de dependencias (CONVENTIONS §2).
- Todo corre en CI y `main` no acepta merge con la suite en rojo.

### 2.8 · Métricas y ablaciones — §13 · ~3 h + ~3 h

**✅ Listo cuando:**
- Calcula las 9 métricas del §13 sobre el test set.
- `ece` con 10 bins; `alert_budget_recall` como curva, no como número suelto.
- `fairness_sex` reporta AUC-PR y recall por sexo **honestamente**, salga lo que salga.
- **Ablación §13.1:** las 4 políticas (A/B/C/D) con el modelo de adherencia, más `stale_variable_miss_rate` para comparar B contra D.
- **Ablación §13.2:** entrenar con §8.2 y evaluar con parámetros perturbados (semillas 142–144), reportando la caída.
- Los dos baselines obligatorios del §13 aparecen en la tabla.
- Las funciones de métrica son **puras** (`y_true, y_pred → dict`) y testeadas con arreglos sintéticos.
- `/eval` devuelve el JSON completo.

---

## ✅ La Fase 1 está terminada cuando

1. `curl` a `/predict` de un niño de fixture devuelve un `RiskResponse` con riesgo, banda, intervalo, confianza e ICD.
2. `curl` a `/predict` de un niño con datos pobres devuelve `status="insufficient_data"` con `requested_variables`.
3. `curl` a `/voi` devuelve `highlighted` + `filter_question_es` + `tail`.
4. `curl` a `/explain` devuelve narrativa válida **con Ollama apagado**.
5. `curl` a `/eval` devuelve las métricas y las dos ablaciones.
6. La suite de invariantes está verde.
7. `import-linter` y `ruff` están verdes.
8. Dos corridas completas desde cero producen resultados idénticos.

Recién ahí se toca el frontend.

---

## FASE 2 · FRONTEND

**Prerrequisito: el `UI.md`** — inventario de pantallas, rutas por rol, tokens de diseño, estados (cargando, error, vacío, primer uso), reglas de accesibilidad y baja estimulación. Los textos ya están todos en el SPEC §12.3–§12.5; no hay que inventar copy.

| # | Pantalla | SPEC | Peso |
|---|---|---|---|
| F.1 | Scaffold Next.js + Tailwind + shadcn + conmutador de rol + cliente de API tipado (zod) | §11 | ~3 h |
| F.2 | **Formulario adaptativo**: 4 bloques, pregunta filtro, sugerencias en gris, "No sé", anclas verbales | §7.4, §7.6, §12.5 | ~5 h |
| F.3 | **Tarjeta del día**: anillo de riesgo, banda, confianza, y **el estado de abstención** | §4, §5.3, §6 | ~4 h |
| F.4 | **Ranking de VoI visible** con su `reason` (*"lleva 7 días sin registrarse"*) | §7.5, §11.2 | ~3 h |
| F.5 | Modo "¿por qué?" con drivers SHAP + slider contrafactual | §11.3 | ~4 h |
| F.6 | Panel profesional: timeline riesgo vs. eventos, calidad del registro | — | ~3 h |
| F.7 | Página pública de evaluación | §13 | ~3 h |

**Criterios transversales de la Fase 2:**
- Ningún texto en español está hardcodeado en un componente: sale de `packages/shared` o del SPEC §12.
- Los tres estados de banda y los cuatro de confianza (incluido `null` = abstención) tienen su representación visual.
- La abstención **no se ve como un error**: es una pantalla legítima que pide un dato.
- Una sugerencia sin tocar se ve claramente distinta de un valor confirmado.
- Todas las escalas ordinales muestran las 5 anclas del §12.5 **más "No sé"**.

---

## Hitos de sincronización

Por evento, no por reloj.

| Hito | Qué habilita |
|---|---|
| **M1** · Hito 0 en `main` | P2 arranca. **El contrato queda congelado.** |
| **M2** · Generador produciendo datos | P2 pasa de fixtures a datos reales |
| **M3** · LightGBM reemplaza a `baseline.py` | P2 recalcula métricas sobre el modelo real |
| **M4** · Fase 1 terminada (los 8 puntos de arriba) | Arranca el diseño y el `UI.md` |
| **M5** · `UI.md` listo | Arranca la Fase 2 |

**Regla:** si un contrato de `packages/shared` cambia después de M1, se avisa por chat **antes** de tocarlo. Cambiar el contrato en silencio es la única forma real de romperle el trabajo al otro.

---

## Entregables

| Entregable | Dueño |
|---|---|
| Repo público + README con setup en 1 comando | P1 |
| Diagrama de arquitectura | P1 |
| Deploy (API + web) | P1 |
| Láminas de rigor: calibración, AUC-PR, ablaciones, equidad por sexo | P2 |
| Video demo | quien haya hecho el frontend |
| Láminas de producto y problema | el otro |
| Envío del formulario de entrega | **los dos juntos, con margen** |

---

## Las tres reglas que evitan el enredo

1. **Nadie edita un archivo del otro.** Si lo necesitas, se avisa antes. (CONVENTIONS §3)
2. **El contrato se congela en M1.** Todo lo demás puede cambiar; eso no, sin aviso.
3. **`main` siempre verde.** `git pull` antes de cada `push`, y la suite de invariantes en verde antes de subir.
