"""B6: the task worker starts during import, so every module-level name it calls
must already be defined when its thread starts."""
import ast
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "server" / "app.py"


def _worker_start_line(tree: ast.Module) -> int:
    for node in tree.body:
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            call = node.value
            target = call.func.value if isinstance(call.func, ast.Attribute) else None
            if isinstance(target, ast.Call) and any(
                    kw.arg == "target" and isinstance(kw.value, ast.Name) and kw.value.id == "_worker"
                    for kw in target.keywords):
                return node.lineno
    raise AssertionError("worker thread start not found")


def test_worker_starts_after_every_function_it_calls():
    tree = ast.parse(APP.read_text(encoding="utf-8-sig"))
    defs = {node.name: node.lineno for node in tree.body if isinstance(node, ast.FunctionDef)}
    worker = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "_worker")
    called = {n.func.id for n in ast.walk(worker) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    start = _worker_start_line(tree)
    late = sorted(name for name in called if name in defs and defs[name] > start)
    assert not late, f"_worker starts at line {start} before these are defined: {late}"
