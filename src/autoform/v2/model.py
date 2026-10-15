"""Finite, explicit deontic fragment shared by the v2 checkers.

This checker proves properties of supplied rules under a bounded Boolean world.
It makes no claim that the rules exhaust the source document.
"""

from __future__ import annotations

from itertools import combinations

import z3

FORCES = {"O", "F", "P"}


def validate(model: dict, rules: list[dict]) -> None:
    facts, actions = set(model["facts"]), set(model["actions"])
    ids: set[str] = set()
    for rule in rules:
        rid = rule["id"]
        if rid in ids:
            raise ValueError(f"Duplicate rule ID: {rid}")
        ids.add(rid)
        if rule["force"] not in FORCES or rule["action"] not in actions:
            raise ValueError(f"Invalid force/action in {rid}")
        positive, negative = set(rule.get("all", [])), set(rule.get("not", []))
        if (positive | negative) - facts or positive & negative:
            raise ValueError(f"Invalid or contradictory guard in {rid}")
        if rule.get("due", "current_decision") not in {"current_decision", "next_decision"}:
            raise ValueError(f"Invalid due value in {rid}")
        if not isinstance(rule.get("source_clause"), str) or not rule["source_clause"]:
            raise ValueError(f"Missing source clause in {rid}")
    for rule in rules:
        if set(rule.get("overrides", [])) - ids or rule["id"] in rule.get("overrides", []):
            raise ValueError(f"Invalid override in {rule['id']}")
    for clause in model.get("state_constraints", []):
        if clause["if"] not in facts or clause["then"] not in facts:
            raise ValueError(f"Invalid state constraint: {clause}")
    for action, preconditions in model.get("action_preconditions", {}).items():
        if action not in actions or set(preconditions) - facts:
            raise ValueError(f"Invalid action preconditions: {action}")
    for action, effect in model.get("action_effects", {}).items():
        if action not in actions or set(effect.get("set_true", []) + effect.get("set_false", [])) - facts:
            raise ValueError(f"Invalid action effect: {action}")


def variables(model: dict) -> dict[str, z3.BoolRef]:
    return {name: z3.Bool(name) for name in model["facts"]}


def guard(rule: dict, vars_: dict[str, z3.BoolRef]) -> z3.BoolRef:
    return z3.And(
        *(vars_[name] for name in rule.get("all", [])),
        *(z3.Not(vars_[name]) for name in rule.get("not", [])),
    )


def effective_guard(rule: dict, rules: list[dict], vars_: dict[str, z3.BoolRef]) -> z3.BoolRef:
    overriding = [other for other in rules if rule["id"] in other.get("overrides", [])]
    return z3.And(guard(rule, vars_), *(z3.Not(guard(other, vars_)) for other in overriding))


def base_constraints(model: dict, vars_: dict[str, z3.BoolRef], facts: dict | None = None) -> list[z3.BoolRef]:
    constraints = [z3.Implies(vars_[item["if"]], vars_[item["then"]]) for item in model.get("state_constraints", [])]
    for name, value in (facts or {}).items():
        if name not in vars_ or not isinstance(value, bool):
            raise ValueError(f"Unknown or non-Boolean case fact: {name}")
        constraints.append(vars_[name] == value)
    return constraints


def feasible(model: dict, action: str, vars_: dict[str, z3.BoolRef]) -> z3.BoolRef:
    return z3.And(*(vars_[name] for name in model.get("action_preconditions", {}).get(action, [])))


def _solve(model: dict, vars_: dict[str, z3.BoolRef], *terms: z3.BoolRef, facts: dict | None = None) -> dict | None:
    solver = z3.Solver()
    solver.add(*base_constraints(model, vars_, facts), *terms)
    outcome = solver.check()
    if outcome == z3.unknown:
        raise RuntimeError(f"Z3 returned unknown: {solver.reason_unknown()}")
    if outcome == z3.unsat:
        return None
    witness = solver.model()
    return {name: z3.is_true(witness.eval(var, model_completion=True)) for name, var in vars_.items()}


def analyze(model: dict, rules: list[dict]) -> dict:
    validate(model, rules)
    vars_ = variables(model)
    conflicts = []
    for left, right in combinations(rules, 2):
        if left["action"] != right["action"] or {left["force"], right["force"]} != {"O", "F"}:
            continue
        witness = _solve(model, vars_, effective_guard(left, rules, vars_), effective_guard(right, rules, vars_), feasible(model, left["action"], vars_))
        if witness is not None:
            conflicts.append({"rules": [left["id"], right["id"]], "action": left["action"], "witness": witness})
    nonvacuity = {}
    for rule in rules:
        witness = _solve(model, vars_, effective_guard(rule, rules, vars_), feasible(model, rule["action"], vars_))
        nonvacuity[rule["id"]] = {"reachable": witness is not None, "witness": witness}
    effect_violations = []
    for action, effect in model.get("action_effects", {}).items():
        def after(name: str) -> z3.BoolRef:
            if name in effect.get("set_true", []):
                return z3.BoolVal(True)
            if name in effect.get("set_false", []):
                return z3.BoolVal(False)
            return vars_[name]
        violations = [z3.And(after(item["if"]), z3.Not(after(item["then"]))) for item in model.get("state_constraints", [])]
        witness = _solve(model, vars_, feasible(model, action, vars_), z3.Or(*violations)) if violations else None
        if witness is not None:
            effect_violations.append({"action": action, "prestate_witness": witness})
    return {"scope": "finite Boolean states satisfying declared invariants and action preconditions; exogenous case facts are unconstrained", "conflicts": conflicts, "nonvacuity": nonvacuity, "effect_invariant_violations": effect_violations}


def case_status(model: dict, rules: list[dict], case: dict, action: str) -> dict:
    validate(model, rules)
    if action not in model["actions"]:
        raise ValueError(f"Unknown action: {action}")
    vars_ = variables(model)
    facts = case["facts"]
    if _solve(model, vars_, facts=facts) is None:
        return {"status": "inconsistent_case_facts", "action": action}
    relevant = [r for r in rules if r["action"] == action]
    expressions = {force: z3.Or(*(effective_guard(r, rules, vars_) for r in relevant if r["force"] == force)) for force in FORCES}
    possible = {force: _solve(model, vars_, expr, facts=facts) is not None for force, expr in expressions.items()}
    certain = {force: _solve(model, vars_, z3.Not(expr), facts=facts) is None for force, expr in expressions.items()}
    conflict_possible = _solve(model, vars_, expressions["O"], expressions["F"], feasible(model, action, vars_), facts=facts) is not None
    feasibility = _solve(model, vars_, feasible(model, action, vars_), facts=facts) is not None
    if certain["O"] and certain["F"]:
        status = "conflicting"
    elif certain["O"] and not possible["F"]:
        due = {r.get("due", "current_decision") for r in relevant if r["force"] == "O" and _solve(model, vars_, effective_guard(r, rules, vars_), facts=facts) is not None}
        status = "pending" if due == {"next_decision"} else "required"
    elif certain["F"] and not possible["O"]:
        status = "forbidden"
    elif certain["P"] and not possible["F"] and not possible["O"]:
        status = "permitted"
    else:
        status = "unknown"
    return {
        "status": status, "action": action, "feasible": feasibility,
        "possible": possible, "certain": certain,
        "conflict_possible": conflict_possible,
        "applicable_or_possible_rules": [r["id"] for r in relevant if _solve(model, vars_, effective_guard(r, rules, vars_), facts=facts) is not None],
        "missing_facts": sorted(set(model["facts"]) - set(facts)),
    }
