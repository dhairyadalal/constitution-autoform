"""Restricted first-order representation over states and actions, checked by Z3."""

from __future__ import annotations

from pathlib import Path

import z3

from .model import analyze, validate


def check_fol(model: dict, rules: list[dict], output_dir: Path, timeout_ms: int = 30000) -> dict:
    """Use quantified biconditionals, not the finite propositional checker encoding."""
    validate(model, rules)
    output_dir.mkdir(parents=True, exist_ok=True)
    context = z3.Context()
    state = z3.DeclareSort("State", ctx=context)
    action, constructors = z3.EnumSort("Action", ["A_" + name for name in model["actions"]], ctx=context)
    action_terms = dict(zip(model["actions"], constructors))
    facts = {name: z3.Function("fact_" + name, state, z3.BoolSort(ctx=context)) for name in model["facts"]}
    obliged = z3.Function("obliged", state, action, z3.BoolSort(ctx=context))
    forbidden = z3.Function("forbidden", state, action, z3.BoolSort(ctx=context))
    permitted = z3.Function("permitted", state, action, z3.BoolSort(ctx=context))
    s, a = z3.Const("s", state), z3.Const("a", action)
    axioms = []
    for clause in model.get("state_constraints", []):
        axioms.append(z3.ForAll([s], z3.Implies(facts[clause["if"]](s), facts[clause["then"]](s))))
    for force, predicate in (("O", obliged), ("F", forbidden), ("P", permitted)):
        parts = []
        for rule in rules:
            if rule["force"] != force:
                continue
            guard = [facts[name](s) for name in rule.get("all", [])]
            guard += [z3.Not(facts[name](s)) for name in rule.get("not", [])]
            overriding = []
            for other in rules:
                if rule["id"] in other.get("overrides", []):
                    other_guard = [facts[name](s) for name in other.get("all", [])]
                    other_guard += [z3.Not(facts[name](s)) for name in other.get("not", [])]
                    overriding.append(z3.Not(z3.And(*other_guard)))
            parts.append(z3.And(a == action_terms[rule["action"]], *guard, *overriding))
        axioms.append(z3.ForAll([s, a], predicate(s, a) == (z3.Or(*parts) if parts else z3.BoolVal(False, ctx=context))))
    feasible_parts = []
    for name, term in action_terms.items():
        preconditions = [facts[f](s) for f in model.get("action_preconditions", {}).get(name, [])]
        feasible_parts.append(z3.And(a == term, *preconditions))
    conflict = z3.And(z3.Or(*feasible_parts), obliged(s, a), forbidden(s, a))
    solver = z3.Solver(ctx=context)
    solver.set(timeout=timeout_ms)
    solver.add(*axioms)
    solver.add(z3.Exists([s, a], conflict))
    (output_dir / "theory.smt2").write_text(solver.to_smt2(), encoding="utf-8")
    outcome = solver.check()
    finite = analyze(model, rules)
    result = {
        "status": "checked" if outcome != z3.unknown else "unknown",
        "fragment": "first-order predicates over states and finite enumerated actions; quantified closed definitions",
        "checker": "Z3", "conflict_query": str(outcome),
        "agrees_with_finite_checker": (outcome == z3.sat) == bool(finite["conflicts"]) if outcome != z3.unknown else None,
        "source": str(output_dir / "theory.smt2"),
    }
    if outcome == z3.unknown:
        result["reason"] = solver.reason_unknown()
    return result
