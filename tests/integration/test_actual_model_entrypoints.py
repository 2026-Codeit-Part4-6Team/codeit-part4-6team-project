from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _function_names(path: Path) -> set[str]:
    module = ast.parse(path.read_text(encoding="utf-8"))
    return {node.name for node in module.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}


def test_basic_and_consultant_expose_run_entrypoints() -> None:
    basic_main = ROOT / "models" / "basic" / "main.py"
    consult_main = ROOT / "models" / "consult" / "main.py"

    assert basic_main.exists()
    assert consult_main.exists()
    assert "run" in _function_names(basic_main)
    assert "run" in _function_names(consult_main)
