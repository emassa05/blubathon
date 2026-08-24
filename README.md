# blubathon

## FARO — Sección de P2 (decisión y salida)

Cubre `ml/voi`, `ml/narrative`, `ml/strategies`, `ml/eval`, `apps/api/store`
y `tests/invariants` (ver `TAREAS.md` §P2). Como el Hito 0 de P1
(`ml/spec_constants`, `packages/shared`, `ml/errors`, `ml/engine/baseline.py`,
`fixtures/`) es el desbloqueo formal y aún no existía, esta implementación
también incluye una versión mínima de esas piezas y de `ml/engine/` (C0-C3)
para poder probar el flujo de punta a punta — quedan documentadas en cada
módulo como "implementación mínima, zona formal de P1" y se reemplazan sin
tocar la superficie pública de `ml/voi`, `ml/narrative`, etc.

### Setup (1 comando, con matices por versión de Python)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

> Nota: el SPEC pide Python 3.12; este entorno se probó también en 3.14.
> Si usas 3.12/3.13, `pip install -r requirements.txt` debería resolver
> versiones estables sin cambios.

### Sembrar la base y levantar la API

```bash
python -m apps.api.store.seed          # siembra data/faro.db desde fixtures/
uvicorn apps.api.main:app --reload     # http://127.0.0.1:8000/api/v1/...
```

`GET /docs` sirve el OpenAPI de los 8 endpoints (§11).

### Verificar antes de subir (CONVENTIONS §8)

```bash
ruff check . && ruff format --check . && pytest tests/invariants -q
```

O la suite completa (invariantes + unitarios de P2):

```bash
pytest tests -q
```
