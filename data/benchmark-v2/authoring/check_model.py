"""Check direct normative conflicts in the withheld finite design model.

This establishes properties of the design model, not semantic fidelity of prose.
"""

from __future__ import annotations

import json
from pathlib import Path

import z3


ROOT = Path(__file__).resolve().parent


def guard(rule: dict, variables: dict[str, z3.BoolRef]) -> z3.BoolRef:
    return z3.And(
        *(variables[name] for name in rule.get("all", [])),
        *(z3.Not(variables[name]) for name in rule.get("not", [])),
    )


def main() -> None:
    model = json.loads((ROOT / "design-model.json").read_text(encoding="utf-8"))
    variables = {name: z3.Bool(name) for name in model["facts"]}
    output = {}
    for family, family_info in model["families"].items():
        for variant in ("consistent", "inconsistent"):
            rules = model["shared_rules"][:]
            if variant == "inconsistent":
                rules += [next(item for item in model["mutations"] if item["id"] == family_info["mutation_id"])]
            conflicts = []
            for obligation in (r for r in rules if r["force"] == "O"):
                for prohibition in (r for r in rules if r["force"] == "F" and r["action"] == obligation["action"]):
                    solver = z3.Solver()
                    solver.add(guard(obligation, variables), guard(prohibition, variables))
                    if solver.check() == z3.sat:
                        witness = solver.model()
                        conflicts.append({
                            "obligation": obligation["id"],
                            "prohibition": prohibition["id"],
                            "action": obligation["action"],
                            "witness": {name: z3.is_true(witness.eval(var, model_completion=True)) for name, var in variables.items()},
                        })
            output[f"{family}-{variant}"] = conflicts
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
