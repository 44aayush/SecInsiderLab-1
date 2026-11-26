"""Stdlib-only modules must not import numpy, pandas, sklearn or xgboost (IDS image lacks them)."""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

TESTS = Path(__file__).resolve().parent
SCRIPT = TESTS.parent / "script"
NAMES = ("common", "kmodel", "bpf_ctl", "flowview", "agent", "webui", "pktbuild", "replay")
MODULES = [SCRIPT / f"{m}.py" for m in NAMES]
MODULES.append(TESTS / "conftest.py")
FORBIDDEN = {"numpy", "pandas", "sklearn", "xgboost"}


def _imported_roots(path: Path) -> set[str]:
    """Collect the top-level package names a module imports.

    Args:
        path: Python source file.

    Returns:
        Set of root module names.
    """
    roots: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            roots.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            roots.add(node.module.split(".")[0])
    return roots


@pytest.mark.parametrize("path", [m for m in MODULES if m.exists()], ids=lambda p: p.name)
def test_stdlib_only(path: Path) -> None:
    """No forbidden third-party import in a stdlib-only module."""
    assert not _imported_roots(path) & FORBIDDEN
