"""Backend registry and candidate source checks."""

from __future__ import annotations

import ast

METHODS = {
    "z3": {"package": "z3", "api": "Use z3.Solver or equivalent Z3 API calls."},
    "clingo": {"package": "clingo", "api": "Use clingo.Control and ground a logic program."},
    "isabelle": {"package": None, "api": "Later integration: Isabelle/HOL theories with chosen deontic semantics."},
    "nuxmv": {"package": None, "api": "Later integration: temporal transition models and nuXmv checks."},
}


def candidate_source_issue(code: str, method: str) -> str | None:
    if method not in {"z3", "clingo"}:
        return f"Method {method} is not yet executable"
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return f"Syntax error: {exc}"
    functions = [node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
    if not any(node.name == "evaluate" for node in functions):
        return "No evaluate(case) function"
    imported = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported.update(
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    )
    if method not in imported:
        return f"Source does not import {method}"
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
    names = {node.func.id for node in calls if isinstance(node.func, ast.Name)}
    names.update(node.func.attr for node in calls if isinstance(node.func, ast.Attribute))
    required = "Solver" if method == "z3" else "Control"
    if required not in names:
        return f"Source does not call {required}; solver use is unverified"
    return None
