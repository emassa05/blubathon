# FARO — Convenciones de código
### Cómo escribimos, cómo nos dividimos, cómo no nos pisamos · v1.0

> **Relación con el [`SPEC.md`](SPEC.md).** El SPEC dice **qué** hace el sistema (contratos, números, invariantes) y está congelado. Este documento dice **cómo escribimos el código**. Son documentos distintos a propósito: el SPEC cambia solo con acuerdo de los dos; esto puede evolucionar mientras programamos.
>
> **Toda IA que genere código para este proyecto lee este archivo primero.** Sin esto, cada archivo sale con un estilo distinto y el repo termina siendo un collage.

---

## 1. Forma del repositorio

**Un repositorio. Dos procesos que se hablan por HTTP.**

```
faro/
├── apps/
│   ├── web/          Next.js 15 · TypeScript · Tailwind · shadcn/ui
│   │                 corre en Node, puerto 3000
│   └── api/          FastAPI · Python 3.12 · Pydantic v2
│       ├── routes/   los 8 endpoints (SPEC §11)      · P1
│       └── store/    persistencia SQLite             · P2
│                     corre en Python, puerto 8000, prefijo /api/v1
├── packages/
│   └── shared/       EL CONTRATO. Tipos zod (TS) ↔ pydantic (PY), SPEC §2 y §11
├── ml/               Librería Python PURA. No sabe qué es HTTP.
│   ├── spec_constants.py   ← todos los números 🔒 del SPEC, una sola vez
│   ├── errors.py           ← las 4 excepciones (§6 de este doc)
│   ├── synth/        generador causal            SPEC §8
│   ├── features/     C0 calidad + C1 baseline    SPEC §5, §9.1
│   ├── engine/       C2 modelo + C3 decisión     SPEC §9, §6
│   │                 + baseline.py (logística de §8.2, desbloquea a P2)
│   ├── voi/          VoI, filtro, salvaguardas   SPEC §7
│   ├── narrative/    payload → plantilla/LLM     SPEC §10
│   ├── strategies/   catálogo (datos)            SPEC §12
│   └── eval/         métricas y ablaciones       SPEC §13
├── data/             faro.db (SQLite) + parquet — generado, en .gitignore
├── tests/            suite de invariantes (§7 de este doc)
└── README.md         setup en 1 comando
```

**Arranque local:** `pnpm dev` (web) y `uvicorn app:app --reload` (api), en dos terminales. Nada de Docker: es una dependencia más que se puede caer el día del pitch.

---

## 2. La regla de dependencias 🔒

**Las flechas van en un solo sentido. Sin excepciones.**

```
apps/web  →  apps/api  →  ml/engine  →  ml/features  →  ml/synth
                              ↓              ↓
                        ml/spec_constants · packages/shared
```

- `ml/*` **NUNCA** importa de `apps/*`.
- `ml/*` no sabe qué es HTTP, ni SQLite, ni React, ni un request.
- `apps/api` es una capa delgada: recibe, valida, llama a `ml/`, serializa. **Cero lógica de negocio.**
- Si un módulo de `ml/` necesita leer algo del disco, no lo lee: **lo recibe como parámetro**.

**Por qué esto importa más de lo que parece:** a Bluba le estamos prometiendo *"tomen el motor y pónganle su propia interfaz"*. Si el motor sabe de HTTP, esa promesa es mentira. **La regla arquitectónica y el argumento del pitch son lo mismo.**

Se verifica en CI con `import-linter` (~10 líneas de config).

---

## 3. Mapa de propiedad — quién toca qué 🔒

**La regla anti-enredo: cada archivo tiene un dueño. Si necesitas tocar algo del otro, se avisa por chat antes, no después.**

| Zona | Dueño | El otro puede |
|---|---|---|
| `packages/shared/` | **P1** | leer, nunca editar sin avisar |
| `ml/spec_constants.py`, `ml/errors.py` | **P1** | leer, nunca editar |
| `ml/synth/`, `ml/features/`, `ml/engine/` | **P1** | leer |
| `apps/api/main.py`, `apps/api/routes/` | **P1** | leer |
| `ml/voi/`, `ml/narrative/`, `ml/strategies/`, `ml/eval/` | **P2** | leer |
| `apps/api/store/` | **P2** | leer |
| `tests/invariants/` | **P2** | agregar tests en archivos propios |
| `README.md` | **P1** | P2 agrega su sección al final |
| `apps/web/` **completo** | Fase 2 — de quien se bifurque | ver `TAREAS.md` |
| `SPEC.md`, `CONVENTIONS.md` | **los dos**, con acuerdo | — |

**Regla de oro:** dos personas nunca editan el mismo archivo el mismo día. Si eso pasa, el archivo estaba mal dividido — se parte, no se negocia.

---

## 4. Los números del SPEC tienen un solo dueño 🔒

Todo valor marcado 🔒 en el SPEC vive **una sola vez**, en `ml/spec_constants.py`, con su referencia:

```python
"""Espejo en código del SPEC.md. Un cambio aquí exige un cambio allá."""

RANDOM_SEED = 42  # SPEC §0.9
BAND_AMBER, BAND_RED = 0.15, 0.35  # SPEC §4
ABSTAIN_ICD, ABSTAIN_WIDTH = 0.35, 0.60  # SPEC §6
ABSTAIN_MIN_HISTORY_DAYS = 5  # SPEC §6
VOI_K, VOI_KAPPA = 20, 0.15  # SPEC §7.1, §7.2
STALENESS_CEILING_DAYS = 7  # SPEC §7.5a
EXPLORATION_MODULO = 7  # SPEC §7.5c
PROVENANCE_WEIGHTS = {  # SPEC §2.5
    "observed": 1.0,
    "confirmed": 1.0,
    "assumed_stable": 0.5,
    "unknown": 0.0,
}
```

**Prohibido 🔒:** escribir un literal numérico del SPEC en cualquier otro archivo. Si ves un `0.35` suelto en el código, es un bug.

*Razón:* el modo de falla clásico de un hackathon es el mismo umbral copiado en cuatro archivos y, para el domingo, con tres valores distintos.

---

## 5. Nombres

- **Código, DB y API: inglés `snake_case`** (SPEC §0.3). Componentes React en `PascalCase`, variables TS en `camelCase`.
- **Todo texto visible al usuario: español**, y sale de `packages/shared` o de las tablas del SPEC §12 — **nunca hardcodeado en un componente**.
- Los nombres canónicos del SPEC §2.1 se usan **tal cual**, de la DB a la URL. `sleep_hours` es `sleep_hours` en todas partes. Nada de `sleepHours` en un lado y `horas_sueno` en otro.
- Booleanos: `is_`, `has_`, `should_`. Funciones que calculan: verbo (`compute_icd`, `rank_by_voi`).

---

## 6. Errores

```python
# ml/errors.py — dueño: P1
class FaroError(Exception): ...


class InsufficientDataError(FaroError): ...  # SPEC §6


class ContractViolationError(FaroError): ...  # datos que rompen §2


class ModelNotReadyError(FaroError): ...  # modelo sin entrenar
```

Cuatro. No más. Nada de jerarquías de diez clases.

**Reglas:**
- `ml/` lanza excepciones. **`apps/api` es el único que las convierte a HTTP.**
- Formato de error de la API, fijo en SPEC §11: `{"error": {"code": str, "message_es": str}}`.
- **La abstención NO es un error.** Es un `RiskResponse` válido con `status="insufficient_data"` y HTTP 200. Confundir esto rompe el SPEC §0.7.
- Nunca un `except:` desnudo. Nunca un `except Exception: pass`.

---

## 7. Tests: la suite de invariantes 🔒

**No buscamos cobertura. Buscamos que las 13 reglas del SPEC §0 sean imposibles de romper sin que CI lo grite.**

`tests/invariants/` — un test por regla, con el `§` en el nombre:

```python
def test_s0_2_sin_leakage():
    """Barajar los valores del día t+1 no debe cambiar ninguna predicción."""


def test_s0_5_nunca_imputa():
    """La matriz que recibe LightGBM todavía contiene NaN."""


def test_s0_7_abstiene_bajo_icd():
    """ICD=0.30 → status='insufficient_data', risk is None."""


def test_s0_9_determinismo():
    """Dos corridas con seed 42 → salida idéntica."""


def test_s0_12_sugerencia_no_tocada_no_existe():
    """Una sugerencia sin confirmar no llega a /ingest."""


def test_s2_5_assumed_stable_sin_valor():
    """provenance='assumed_stable' con valor no nulo → ContractViolationError."""


def test_s4_bordes_de_banda():
    """0.1499→verde · 0.15→ambar · 0.3499→ambar · 0.35→rojo"""
```

Ese último atrapa el clásico `<` vs `<=` — el bug que te hace quedar mal **en vivo**.

**Regla 🔒:** ningún merge a `main` con la suite de invariantes en rojo. Los tests de UI son opcionales; estos no.

---

## 8. Herramientas — mínimas

| | Herramienta | Config |
|---|---|---|
| Python: lint + formato | **ruff** | una sola herramienta, instantánea |
| Python: validación | **pydantic v2** | solo en las fronteras (API, ingesta) |
| TypeScript | **`strict: true`** | y nada más |
| Tests | **pytest** | |
| Dependencias JS | **pnpm** | |

**No usamos:** `mypy --strict` (te comes el domingo peleando con los tipos de LightGBM), Docker, Nx/Turborepo, husky.

Un solo comando para verificar antes de subir: `ruff check . && ruff format --check . && pytest tests/invariants -q`.

---

## 9. Git

- Rama `main`, siempre verde. Ramas cortas solo para lo riesgoso.
- **`git pull` antes de cada `push`.** Con el mapa de propiedad del §3, los conflictos deberían ser casi imposibles; si aparecen, es señal de que se rompió el mapa.
- Commits pequeños, en imperativo y en español: `agrega calculo de ICD`, `corrige borde de banda ambar`.
- `data/` en `.gitignore`, salvo `manifest.json`.
- **Nunca** se sube un `.env`, un modelo entrenado, ni un `node_modules`.

---

## 10. Definition of Done

Una tarea está lista cuando:

1. ✅ Corre localmente sin errores en consola.
2. ✅ `ruff` y la suite de invariantes pasan.
3. ✅ No introdujo ningún literal del SPEC fuera de `spec_constants.py`.
4. ✅ Respeta la regla de dependencias (§2).
5. ✅ Si tocó un contrato de `packages/shared`, **le avisó al otro**.
6. ✅ Está en `main`.

---

## 11. Lo que NO vamos a hacer 🔒

Con 2 personas y 60 horas, esto **resta**:

| No | Por qué |
|---|---|
| Repository pattern, inyección de dependencias, clases base abstractas | "Clean architecture" de manual **es otra forma de espagueti**: cuatro archivos para leer una fila |
| Cobertura del 100% | 15 tests de invariantes valen más que 200 triviales |
| Docstrings en todo | Solo donde el *por qué* no es obvio, con el `§` del SPEC |
| Microservicios, colas, cachés | No hay carga que lo justifique |
| Optimizar antes de medir | 36.000 filas. SQLite se ríe |
| Abstraer "por si acaso" | **Una capa de indirección solo se justifica con dos implementaciones reales.** No las tenemos |
| **PWA** (manifest, service worker, offline) | Fuera de alcance por decisión del 24 ago. La web corre en el navegador como cualquier sitio |

**La regla que resume todo:** el código debe poder leerse a las 3 AM del domingo por la persona que no lo escribió.
