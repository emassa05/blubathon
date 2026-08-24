"""FastAPI app — SPEC §11. Capa delgada: recibe, valida, llama a `ml/`,
serializa. Cero lógica de negocio (CONVENTIONS §2)."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from apps.api.errors import error_body
from apps.api.routes import counterfactual, explain, feedback, ingest, predict, quality, voi
from apps.api.routes import eval as eval_route
from ml.errors import FaroError

app = FastAPI(title="FARO API", version="0.2.0")

API_PREFIX = "/api/v1"
app.include_router(ingest.router, prefix=API_PREFIX, tags=["ingest"])
app.include_router(predict.router, prefix=API_PREFIX, tags=["predict"])
app.include_router(voi.router, prefix=API_PREFIX, tags=["voi"])
app.include_router(explain.router, prefix=API_PREFIX, tags=["explain"])
app.include_router(counterfactual.router, prefix=API_PREFIX, tags=["counterfactual"])
app.include_router(quality.router, prefix=API_PREFIX, tags=["quality"])
app.include_router(feedback.router, prefix=API_PREFIX, tags=["feedback"])
app.include_router(eval_route.router, prefix=API_PREFIX, tags=["eval"])


@app.exception_handler(FaroError)
def handle_faro_error(request: Request, exc: FaroError) -> JSONResponse:
    """CONVENTIONS §6 — único lugar donde una excepción de `ml/` se
    traduce a HTTP. La abstención de `/predict` NO pasa por aquí: se
    maneja dentro de la ruta y devuelve 200 (§0.7)."""
    body, status = error_body(exc)
    return JSONResponse(status_code=status, content=body)
