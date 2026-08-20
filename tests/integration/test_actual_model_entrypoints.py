from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _run_signature(path: Path) -> tuple[str, str]:
    module = ast.parse(path.read_text(encoding="utf-8"))
    run = next(
        node
        for node in module.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "run"
    )
    assert len(run.args.args) == 1
    argument = run.args.args[0]
    assert argument.arg == "request"
    assert isinstance(argument.annotation, ast.Name)
    assert isinstance(run.returns, ast.Name)
    return argument.annotation.id, run.returns.id


def test_basic_and_consultant_expose_plain_dict_run_entrypoints() -> None:
    basic_main = ROOT / "models" / "basic" / "main.py"
    consult_main = ROOT / "models" / "consult" / "main.py"

    assert basic_main.exists()
    assert consult_main.exists()
    assert _run_signature(basic_main) == ("dict", "dict")
    assert _run_signature(consult_main) == ("dict", "dict")
