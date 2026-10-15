"""Evaluate declarative SMT and ASP artifacts against the fixed case encoder."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def execute_declarative(artifact: str, supported: list[str], method: str, case: dict, timeout: int) -> dict:
    target = case["target"]
    if target not in supported:
        return {"status": "valid", "answer": "unresolved", "reason": f"{target} declared unsupported"}
    if method not in {"z3", "clingo"}:
        return {"status": "not_run", "answer": None, "reason": f"No declarative adapter for {method}"}
    payload = {"artifact": artifact, "method": method, "case": case}
    try:
        process = subprocess.run(
            [sys.executable, "-I", str(Path(__file__).resolve()), "--worker"],
            input=json.dumps(payload), text=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env={"PATH": os.environ.get("PATH", ""), "PYTHONNOUSERSITE": "1"},
            timeout=timeout, check=False,
        )
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "answer": None, "reason": f"Exceeded {timeout}s"}
    if process.returncode != 0:
        return {"status": "runtime_error", "answer": None, "reason": process.stderr[-1800:]}
    try:
        result = json.loads(process.stdout)
    except json.JSONDecodeError:
        return {"status": "invalid_output", "answer": None, "reason": process.stdout[-1000:]}
    if result.get("answer") not in {"yes", "no", "unresolved"}:
        return {"status": "invalid_output", "answer": None, "reason": repr(result)[:1000]}
    return {"status": "valid", "answer": result["answer"], "reason": result.get("reason", "")}


def _quoted(value: object) -> str:
    return json.dumps("" if value is None else str(value), ensure_ascii=True)


def _smt_facts(case: dict) -> str:
    lines = [
        "(declare-const N Int)",
        "(declare-fun action (Int) String)",
        "(declare-fun actor (Int) String)",
        "(declare-fun obj (Int) String)",
        "(declare-fun recipient (Int) String)",
        "(declare-fun subject (Int) String)",
        "(declare-fun owner (String) String)",
        "(declare-fun sensitivity (String) String)",
        "(declare-fun external (String) Bool)",
        "(declare-fun hold (String) Bool)",
        f"(assert (= N {len(case['events'])}))",
    ]
    for i, event in enumerate(case["events"]):
        for field, function in (("action", "action"), ("actor", "actor"), ("object", "obj"), ("recipient", "recipient"), ("subject", "subject")):
            lines.append(f"(assert (= ({function} {i}) {_quoted(event.get(field))}))")
    for item in case.get("objects", []):
        item_id = _quoted(item["id"])
        if "owner" in item:
            lines.append(f"(assert (= (owner {item_id}) {_quoted(item['owner'])}))")
        if "sensitivity" in item:
            lines.append(f"(assert (= (sensitivity {item_id}) {_quoted(item['sensitivity'])}))")
        if "legal_hold" in item:
            lines.append(f"(assert (= (hold {item_id}) {'true' if item['legal_hold'] else 'false'}))")
    for person in case.get("people", []):
        if "external" in person:
            lines.append(f"(assert (= (external {_quoted(person['id'])}) {'true' if person['external'] else 'false'}))")
    return "\n".join(lines) + "\n"


def _run_z3(artifact: str, case: dict) -> dict:
    import z3

    rules = json.loads(artifact)
    if not isinstance(rules, dict) or case["target"] not in rules:
        raise ValueError("Artifact must map target IDs to violation and permission expressions")
    query_key = "violation" if case.get("query_kind", "compliance") == "compliance" else "permission"
    expression = rules[case["target"]][query_key]
    if not isinstance(expression, str) or not expression.strip():
        raise ValueError(f"Missing {query_key} expression")
    if any(token in expression.lower() for token in ("(assert", "(declare", "(set-", "(check-")):
        raise ValueError("Artifact must contain only a Boolean expression")
    facts = _smt_facts(case)

    def satisfiable(extra: str):
        solver = z3.Solver()
        solver.set(timeout=6000)
        solver.from_string(facts + "(assert " + extra + ")")
        return solver.check()

    true_check = satisfiable(expression)
    false_check = satisfiable(f"(not {expression})")
    if true_check == z3.unknown or false_check == z3.unknown:
        return {"answer": "unresolved", "reason": "Z3 returned unknown"}
    if true_check == z3.unsat and false_check == z3.unsat:
        raise ValueError("Inconsistent fact model or expression")
    if true_check == z3.sat and false_check == z3.sat:
        return {"answer": "unresolved", "reason": "Both truth values fit the known facts"}
    holds = true_check == z3.sat
    if query_key == "violation":
        return {"answer": "no" if holds else "yes", "reason": f"Z3 {'entails' if holds else 'rules out'} target violation"}
    return {"answer": "yes" if holds else "no", "reason": f"Z3 {'entails' if holds else 'rules out'} explicit permission"}


def _asp_facts(case: dict) -> str:
    lines = []
    for index, event in enumerate(case["events"]):
        values = [str(index)] + [
            _quoted(event.get(field))
            for field in ("action", "actor", "object", "recipient", "subject")
        ]
        lines.append(f"event({','.join(values)}).")
        lines.append(f"time({index}).")
    recipients = {person["id"]: person for person in case.get("people", [])}
    for event in case["events"]:
        recipient = event.get("recipient")
        if recipient is not None and recipient not in recipients:
            recipients[recipient] = {"id": recipient}
    for person_id, person in recipients.items():
        qid = _quoted(person_id)
        lines.append(f"person({qid}).")
        if person.get("external") is True:
            lines.append(f"external({qid}).")
        elif person.get("external") is False:
            lines.append(f"internal({qid}).")
        else:
            lines.append(f"1 {{ external({qid}); internal({qid}) }} 1.")
    for item in case.get("objects", []):
        qid = _quoted(item["id"])
        lines.append(f"object({qid}).")
        if "owner" in item:
            lines.append(f"owner({qid},{_quoted(item['owner'])}).")
        if "sensitivity" in item:
            lines.append(f"sensitivity({qid},{_quoted(item['sensitivity'])}).")
        else:
            lines.append(f"1 {{ sensitivity({qid},\"public\"); sensitivity({qid},\"internal\"); sensitivity({qid},\"restricted\") }} 1.")
        if item.get("legal_hold") is True:
            lines.append(f"hold({qid}).")
        elif item.get("legal_hold") is False:
            lines.append(f"not_hold({qid}).")
        else:
            lines.append(f"1 {{ hold({qid}); not_hold({qid}) }} 1.")
    return "\n".join(lines) + "\n"


def _run_clingo(artifact: str, case: dict) -> dict:
    import clingo

    if any(token in artifact for token in ("#const", "#include", "#script")):
        raise ValueError("Artifact contains a prohibited clingo directive")
    controller = clingo.Control(["--models=0", "--warn=none"])
    controller.add("base", [], _asp_facts(case) + "\n" + artifact)
    controller.ground([("base", [])])
    predicate = "violation" if case.get("query_kind", "compliance") == "compliance" else "permission"
    target_atom = clingo.Function(predicate, [clingo.String(case["target"])])
    outcomes = []
    with controller.solve(yield_=True) as handle:
        for model in handle:
            outcomes.append(model.contains(target_atom))
        result = handle.get()
    if not result.satisfiable or not outcomes:
        raise ValueError("No answer set; artifact or facts are inconsistent")
    if all(outcomes):
        answer = "no" if predicate == "violation" else "yes"
    elif not any(outcomes):
        answer = "yes" if predicate == "violation" else "no"
    else:
        answer = "unresolved"
    return {"answer": answer, "reason": f"clingo: {sum(outcomes)} of {len(outcomes)} answer sets contain {predicate}({case['target']})"}


if __name__ == "__main__":
    payload = json.load(sys.stdin)
    function = _run_z3 if payload["method"] == "z3" else _run_clingo
    print(json.dumps(function(payload["artifact"], payload["case"])))
