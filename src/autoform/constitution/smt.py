"""Quantifier-free SMT-LIB representation of direct norm conflicts."""

from __future__ import annotations

from itertools import combinations
from pathlib import Path

import z3

from .model import analyze, base_constraints, effective_guard, feasible, validate, variables


def check_smt(model: dict, rules: list[dict], output_dir: Path) -> dict:
    validate(model, rules)
    output_dir.mkdir(parents=True, exist_ok=True)
    vars_ = variables(model)
    pairs = []
    for left, right in combinations(rules, 2):
        if left["action"] == right["action"] and {left["force"], right["force"]} == {"O", "F"}:
            pairs.append(z3.And(effective_guard(left, rules, vars_), effective_guard(right, rules, vars_), feasible(model, left["action"], vars_)))
    solver = z3.Solver()
    solver.add(*base_constraints(model, vars_), z3.Or(*pairs))
    (output_dir / "theory.smt2").write_text(solver.to_smt2(), encoding="utf-8")
    outcome = solver.check()
    finite = analyze(model, rules)
    return {
        "status": "checked" if outcome != z3.unknown else "unknown",
        "checker": "Z3", "conflict_query": str(outcome),
        "agrees_with_finite_checker": (outcome == z3.sat) == bool(finite["conflicts"]) if outcome != z3.unknown else None,
        "source": str(output_dir / "theory.smt2"),
    }
