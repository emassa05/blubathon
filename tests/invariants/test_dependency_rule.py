"""CONVENTIONS §2 — la regla de dependencias: `ml/*` nunca importa de
`apps/*`. Sustituye a `import-linter` (no instalado) con una verificación
estática equivalente sobre el árbol de imports."""

import ast
from pathlib import Path

ML_DIR = Path(__file__).resolve().parents[2] / "ml"


def _imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
    return names


def test_ml_nunca_importa_de_apps():
    offenders = []
    for path in ML_DIR.rglob("*.py"):
        for name in _imports(path):
            if name == "apps" or name.startswith("apps."):
                offenders.append((str(path), name))
    assert offenders == [], f"ml/ importa de apps/: {offenders}"
