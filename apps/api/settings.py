"""Configuración de despliegue (SPEC 12.3).

`FARO_MODE=demo` usa SQLite local, cohorte `demo_fixture` y sesión ficticia
preseeded. `FARO_MODE=pilot` exige PostgreSQL: SQLite bloquea el arranque.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from apps.api.contracts.constants import PILOT_DATABASE
from apps.api.contracts.enums import CohortKind, DeploymentMode
from apps.api.errors import FaroApiError

_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_CORS_ORIGINS = ("http://127.0.0.1:3000", "http://localhost:3000")


@dataclass(frozen=True, slots=True)
class Settings:
    mode: DeploymentMode = DeploymentMode.DEMO
    database_url: str = ""
    db_path: Path = field(default_factory=lambda: _REPOSITORY_ROOT / "data" / "faro.db")
    bind_host: str = "127.0.0.1"
    bind_port: int = 8000
    cors_origins: tuple[str, ...] = DEFAULT_CORS_ORIGINS
    audit_secret: bytes = b"faro-demo-audit-secret"
    scenario_secret: bytes = b"faro-demo-scenario-secret"

    @property
    def expose_openapi(self) -> bool:
        """CONVENTIONS 15: la documentación OpenAPI se deshabilita en piloto."""
        return self.deployment_mode is DeploymentMode.DEMO

    @property
    def deployment_mode(self) -> DeploymentMode:
        """Normaliza el modo aunque llegue como string desde el entorno."""
        return DeploymentMode(self.mode)

    @property
    def allowed_cohort(self) -> CohortKind:
        """SPEC 12.3: la demo solo acepta `demo_fixture`."""
        if self.deployment_mode is DeploymentMode.DEMO:
            return CohortKind.DEMO_FIXTURE
        return CohortKind.REAL_SUBJECT

    def validate(self) -> None:
        """SPEC 12.3 / INV-30. SQLite en modo piloto bloquea el arranque."""
        if self.deployment_mode is DeploymentMode.PILOT and not self.database_url.startswith(
            PILOT_DATABASE
        ):
            raise FaroApiError("pilot_requires_postgresql", 500)


def _origins(raw: str | None) -> tuple[str, ...]:
    if not raw:
        return DEFAULT_CORS_ORIGINS
    return tuple(origin.strip() for origin in raw.split(",") if origin.strip())


def load_settings(environ: dict[str, str] | None = None) -> Settings:
    env = dict(os.environ if environ is None else environ)
    mode = DeploymentMode(env.get("FARO_MODE", DeploymentMode.DEMO.value))
    data_dir = Path(env.get("FARO_DATA_DIR", _REPOSITORY_ROOT / "data"))
    settings = Settings(
        mode=mode,
        database_url=env.get("FARO_DATABASE_URL", ""),
        db_path=Path(env.get("FARO_DB_PATH", data_dir / "faro.db")),
        bind_host=env.get("FARO_BIND_HOST", "127.0.0.1"),
        bind_port=int(env.get("FARO_BIND_PORT", "8000")),
        cors_origins=_origins(env.get("FARO_CORS_ORIGINS")),
        audit_secret=env.get("FARO_AUDIT_SECRET", "faro-demo-audit-secret").encode(),
        scenario_secret=env.get("FARO_SCENARIO_SECRET", "faro-demo-scenario-secret").encode(),
    )
    settings.validate()
    return settings
