"""ASP representation of the same finite norm vocabulary, checked by clingo."""

from __future__ import annotations

import json
from pathlib import Path

import clingo

from .model import analyze, validate


def _quote(value: str) -> str:
    return json.dumps(value)


def render_program(model: dict, rules: list[dict]) -> str:
    validate(model, rules)
    lines = [f'{{ true({_quote(fact)}) }}.' for fact in model["facts"]]
    for clause in model.get("state_constraints", []):
        lines.append(f':- true({_quote(clause["if"])}), not true({_quote(clause["then"])}).')
    for rule in rules:
        body = [f'true({_quote(fact)})' for fact in rule.get("all", [])]
        body += [f'not true({_quote(fact)})' for fact in rule.get("not", [])]
        lines.append(f'active({_quote(rule["id"])}).' if not body else f'active({_quote(rule["id"])}) :- {", ".join(body)}.')
        for target in rule.get("overrides", []):
            lines.append(f'overridden({_quote(target)}) :- active({_quote(rule["id"])}).')
        name = {"O": "obliged", "F": "forbidden", "P": "permitted"}[rule["force"]]
        lines.append(f'{name}({_quote(rule["action"])}) :- active({_quote(rule["id"])}), not overridden({_quote(rule["id"])}).')
    for action in model["actions"]:
        pre = [f'true({_quote(fact)})' for fact in model.get("action_preconditions", {}).get(action, [])]
        lines.append(f'feasible({_quote(action)}).' if not pre else f'feasible({_quote(action)}) :- {", ".join(pre)}.')
    lines.extend([
        'conflict(A) :- obliged(A), forbidden(A), feasible(A).',
        'some_conflict :- conflict(A).',
        ':- not some_conflict.',
        '#show conflict/1.',
        '#show true/1.',
    ])
    return "\n".join(lines) + "\n"


def check_asp(model: dict, rules: list[dict], output_dir: Path) -> dict:
    program = render_program(model, rules)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "theory.lp").write_text(program, encoding="utf-8")
    control = clingo.Control(["--models=1", "--warn=none"])
    try:
        control.add("base", [], program)
        control.ground([("base", [])])
        models = []
        with control.solve(yield_=True) as handle:
            for answer in handle:
                models.append([str(atom) for atom in answer.symbols(shown=True)])
            outcome = handle.get()
    except RuntimeError as exc:
        return {"status": "parse_or_ground_error", "reason": str(exc), "source": str(output_dir / "theory.lp")}
    finite = analyze(model, rules)
    exists = bool(outcome.satisfiable)
    return {
        "status": "checked", "checker": "clingo", "conflict_query": "sat" if exists else "unsat",
        "agrees_with_finite_checker": exists == bool(finite["conflicts"]),
        "witness_atoms": models[0] if models else [], "source": str(output_dir / "theory.lp"),
    }
