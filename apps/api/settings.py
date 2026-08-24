"""Where the API looks for its artifacts. Overridable for tests and deploys."""

from __future__ import annotations

import os
from pathlib import Path

_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.environ.get("FARO_DATA_DIR", _REPOSITORY_ROOT / "data"))
MODEL_PATH = Path(os.environ.get("FARO_MODEL_PATH", DATA_DIR / "model.joblib"))
DB_PATH = Path(os.environ.get("FARO_DB_PATH", DATA_DIR / "faro.db"))
