"""Audit the withheld intended rules under the public finite-world semantics."""

from __future__ import annotations

import json
from pathlib import Path

from autoform.v2.model import analyze


ROOT = Path(__file__).resolve().parent


def main() -> None:
    design = json.loads((ROOT / "design-model.json").read_text(encoding="utf-8"))
    world = json.loads((ROOT.parent / "world.json").read_text(encoding="utf-8"))
    results = {}
    for family, info in design["families"].items():
        for variant in ("consistent", "inconsistent"):
            rules = list(design["shared_rules"])
            if variant == "inconsistent":
                rules.append(next(rule for rule in design["mutations"] if rule["id"] == info["mutation_id"]))
            name = f"{family}-{variant}"
            full = analyze(world, rules)
            results[name] = {
                "scope": full["scope"],
                "conflicts": full["conflicts"],
                "nonvacuity": {rid: item["reachable"] for rid, item in full["nonvacuity"].items()},
                "effect_invariant_violations": full["effect_invariant_violations"],
            }
            expected = design["intended_consistency"][name]
            if bool(results[name]["conflicts"]) == expected:
                raise RuntimeError(f"Unexpected conflict classification for {name}")
            if not all(results[name]["nonvacuity"].values()):
                raise RuntimeError(f"Vacuous intended rule in {name}")
            if results[name]["effect_invariant_violations"]:
                raise RuntimeError(f"Action effect breaks an invariant in {name}")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
