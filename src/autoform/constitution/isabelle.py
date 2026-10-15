"""Compile finite norm models to Isabelle/HOL and batch-check their claims."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import hashlib
import tempfile
from pathlib import Path

from .model import analyze, validate


def isabelle_binary() -> str | None:
    configured = os.environ.get("ISABELLE_BIN")
    if configured:
        return configured if Path(configured).is_file() else None
    found = shutil.which("isabelle")
    if found:
        return found
    for path in ("/Applications/Isabelle2025-2.app/bin/isabelle", "/Applications/Isabelle.app/bin/isabelle"):
        if Path(path).is_file():
            return path
    return None


def _constructor(name: str) -> str:
    result = "".join(part.capitalize() for part in name.split("_"))
    if not re.fullmatch(r"[A-Z][A-Za-z0-9]*", result):
        raise ValueError(f"Unsafe Isabelle identifier: {name}")
    return result


def _and(parts: list[str]) -> str:
    return " & ".join(parts) if parts else "True"


def _or(parts: list[str]) -> str:
    return " | ".join(f"({part})" for part in parts) if parts else "False"


def render_theory(model: dict, rules: list[dict], expected_conflict: bool, witness: dict | None = None) -> str:
    validate(model, rules)
    facts = {name: _constructor(name) for name in model["facts"]}
    actions = {name: _constructor(name) for name in model["actions"]}
    if len(set(facts.values())) != len(facts) or len(set(actions.values())) != len(actions):
        raise ValueError("Isabelle constructors collide")
    lines = [
        "theory Candidate", "imports Main", "begin", "",
        "datatype fact = " + " | ".join(facts.values()),
        "datatype action = " + " | ".join(actions.values()),
        'type_synonym state = "fact => bool"', "",
    ]
    active_names = []
    for index, rule in enumerate(rules, 1):
        name = f"active_{index}"
        active_names.append(name)
        terms = [f"s {facts[f]}" for f in rule.get("all", [])]
        terms += [f"~ s {facts[f]}" for f in rule.get("not", [])]
        lines.extend([f"definition {name} :: \"state => bool\" where", f'  "{name} s = ({_and(terms)})"', ""])
    for force, name in (("O", "obliged"), ("F", "forbidden"), ("P", "permitted")):
        terms = []
        for i, rule in enumerate(rules):
            if rule["force"] != force:
                continue
            overriding = [f"~ {active_names[j]} s" for j, other in enumerate(rules) if rule["id"] in other.get("overrides", [])]
            terms.append(f"a = {actions[rule['action']]} & {active_names[i]} s" + (" & " + " & ".join(overriding) if overriding else ""))
        lines.extend([f"definition {name} :: \"state => action => bool\" where", f'  "{name} s a = ({_or(terms)})"', ""])
    reach = [f"(~ s {facts[c['if']]} | s {facts[c['then']]})" for c in model.get("state_constraints", [])]
    lines.extend(['definition reachable :: "state => bool" where', f'  "reachable s = ({_and(reach)})"', ""])
    cases = []
    for action in model["actions"]:
        pre = [f"s {facts[f]}" for f in model.get("action_preconditions", {}).get(action, [])]
        cases.append(f"a = {actions[action]} & ({_and(pre)})")
    lines.extend(['definition feasible :: "state => action => bool" where', f'  "feasible s a = ({_or(cases)})"', ""])
    simp = " ".join(["obliged_def", "forbidden_def", "reachable_def", "feasible_def"] + [f"{name}_def" for name in active_names])
    if expected_conflict:
        if witness is None:
            raise ValueError("Conflict proof requires a concrete witness")
        true_facts = [facts[f] for f in model["facts"] if witness["witness"][f]]
        set_expr = "{" + ", ".join(true_facts) + "}"
        action = actions[witness["action"]]
        lines.extend([
            'definition witness_state :: "state" where',
            f'  "witness_state = (%f. f \\<in> {set_expr})"', "",
            'lemma conflict_witness: "reachable witness_state & feasible witness_state ' + action + ' & obliged witness_state ' + action + ' & forbidden witness_state ' + action + '"',
            f"  by (simp add: witness_state_def {simp})", "",
        ])
    else:
        lines.extend([
            'lemma no_reachable_conflict: "~ (EX s a. reachable s & feasible s a & obliged s a & forbidden s a)"',
            f"  by (auto simp: {simp})", "",
        ])
    lines.extend(["end", ""])
    return "\n".join(lines)


def check_theory(model: dict, rules: list[dict], output_dir: Path, timeout: int = 300) -> dict:
    """Write a reproducible session, then ask Isabelle to check its generated proof."""
    analysis = analyze(model, rules)
    conflicts = analysis["conflicts"]
    output_dir.mkdir(parents=True, exist_ok=True)
    theory = render_theory(model, rules, bool(conflicts), conflicts[0] if conflicts else None)
    (output_dir / "Candidate.thy").write_text(theory, encoding="utf-8")
    session = "Autoform_" + hashlib.sha256(str(output_dir.resolve()).encode()).hexdigest()[:12]
    (output_dir / "ROOT").write_text(f'session {session} = HOL +\n  theories Candidate\n', encoding="utf-8")
    executable = isabelle_binary()
    if executable is None:
        return {"status": "not_run", "reason": "Isabelle executable unavailable; set ISABELLE_BIN", "theory": str(output_dir / "Candidate.thy"), "expected_claim": "conflict_witness" if conflicts else "no_reachable_conflict"}
    environment = os.environ.copy()
    environment["USER_HOME"] = os.environ.get("AUTOFORM_ISABELLE_USER_HOME", str(Path(tempfile.gettempdir()) / "autoform-isabelle-user"))
    try:
        version = subprocess.run([executable, "version"], text=True, capture_output=True, timeout=15, check=False, env=environment)
        process = subprocess.run([executable, "build", "-D", str(output_dir), session], text=True, capture_output=True, timeout=timeout, check=False, env=environment)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"status": "timeout" if isinstance(exc, subprocess.TimeoutExpired) else "runtime_error", "reason": str(exc), "theory": str(output_dir / "Candidate.thy")}
    (output_dir / "isabelle-stdout.log").write_text(process.stdout, encoding="utf-8")
    (output_dir / "isabelle-stderr.log").write_text(process.stderr, encoding="utf-8")
    return {
        "status": "checked" if process.returncode == 0 else "proof_or_build_error",
        "returncode": process.returncode, "version": (version.stdout or version.stderr).strip(),
        "theory": str(output_dir / "Candidate.thy"),
        "expected_claim": "conflict_witness" if conflicts else "no_reachable_conflict", "session": session,
    }
