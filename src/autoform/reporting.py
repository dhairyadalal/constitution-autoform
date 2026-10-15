"""Create a reproducible numeric report and evidence packet for prose synthesis."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from .codex import WRITEUP_SCHEMA, call_codex, prompt_file


def build_report(run_dir: Path, agent_writeup: bool = False, timeout: int = 180) -> Path:
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    reference = json.loads((run_dir / "reference.json").read_text(encoding="utf-8"))
    results = json.loads((run_dir / "results.json").read_text(encoding="utf-8"))
    by_condition = defaultdict(list)
    examples = []
    per_candidate_examples = defaultdict(int)
    for candidate in results["candidates"]:
        key = (candidate["method"], candidate["prompt_mode"])
        by_condition[key].append(candidate)
        for entry in candidate["case_results"]:
            expected = reference[entry["case_id"]]["answer"]
            actual = entry["result"].get("answer")
            if (expected != "unresolved" and actual != expected and len(examples) < 24
                    and per_candidate_examples[candidate["candidate_id"]] < 2):
                per_candidate_examples[candidate["candidate_id"]] += 1
                examples.append({
                    "bundle": candidate["bundle_id"], "case_id": entry["case_id"],
                    "method": candidate["method"], "prompt_mode": candidate["prompt_mode"],
                    "expected": expected, "actual": actual,
                    "execution_status": entry["result"]["status"],
                    "reason": entry["result"].get("reason", "")[:240].replace("\n", " "),
                })
    lines = [
        "# Preliminary findings: synthetic constitution autoformalization",
        "",
        "## Research question",
        "Which distinctions in one shared synthetic constitution benchmark survive formalization across methods?",
        "",
        "## Procedure",
        f"Run `{manifest['run_id']}` used {manifest.get('artifact_mode', 'python')} artifacts, {len(manifest['bundle_ids'])} bundles, "
        f"{len(results['case_ids'])} held-out cases, {manifest['repetitions']} repetitions, "
        f"and {manifest['judge_votes']} independent agent reference votes per bundle.",
        "The reference is an agent-constructed interpretation. Solver execution checks the generated artifact's behavior against that interpretation.",
        "",
        "## Results",
        "| Method | Prompt | Candidates | Executable | Correct / determinate | False acceptance | False rejection | Unresolved outputs | Invalid case outputs |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for (method, mode), group in sorted(by_condition.items()):
        count = len(group)
        executable = sum(item["score"]["executable"] for item in group)
        correct = sum(item["score"]["correct"] for item in group)
        determinate = sum(item["score"]["determinate_reference"] for item in group)
        false_acceptance = sum(item["score"]["false_acceptance"] for item in group)
        false_rejection = sum(item["score"]["false_rejection"] for item in group)
        unresolved = sum(item["score"]["unresolved_output"] for item in group)
        invalid = sum(item["score"]["invalid_output"] for item in group)
        lines.append(f"| {method} | {mode} | {count} | {executable} | {correct}/{determinate} | {false_acceptance} | {false_rejection} | {unresolved} | {invalid} |")
    for method in results.get("not_run_methods", []):
        lines.append(f"| {method} | all | 0 | not run | n/a | n/a | n/a | n/a | n/a |")
    unresolved_refs = sum(item["answer"] == "unresolved" for item in reference.values())
    disagreements = sum(item["disagreement"] for item in reference.values())
    lines.extend([
        "", "## Reference uncertainty",
        f"{unresolved_refs} of {len(reference)} cases have unresolved reference judgments; "
        f"{disagreements} have vote disagreement or a missing vote.",
        "", "## Illustrative mismatches",
    ])
    for example in examples[:12]:
        lines.append(
            f"- `{example['bundle']}/{example['case_id']}`: {example['method']} "
            f"{example['prompt_mode']} gave `{example['actual']}` "
            f"({example['execution_status']}); agent reference `{example['expected']}`. "
            f"Candidate reason: {example['reason']}"
        )
    if not examples:
        lines.append("No determinate mismatches in the saved run.")
    lines.extend([
        "", "## Limits",
        "The benchmark is small and synthetic. Reference judgments come from agents, so shared model assumptions may affect both generation and evaluation. Candidate source requires qualitative inspection to confirm that the named solver carries the normative reasoning. Prompt-level separation does not prevent a local Codex process from reading other host files. Unintegrated methods are recorded as not run.",
        "", "## Reproduction",
        "See `manifest.json`, `reference.json`, `results.json`, and each candidate's saved prompt, response, source, and command trace in this run directory.",
        "",
    ])
    report_path = run_dir / "report.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    (run_dir / "evidence_packet.json").write_text(
        json.dumps({"manifest": manifest, "reference": reference, "condition_summary": lines[10:], "examples": examples}, indent=2),
        encoding="utf-8",
    )
    if agent_writeup:
        prompt = prompt_file("writeup.md") + "\n\nRUN REPORT:\n" + report_path.read_text(encoding="utf-8")
        prompt += "\n\nEVIDENCE EXAMPLES:\n" + json.dumps(examples[:16], indent=2)
        try:
            output = call_codex(prompt, WRITEUP_SCHEMA, run_dir / "writeup_call", timeout)
            markdown = output.get("markdown", "").strip()
            if markdown:
                (run_dir / "findings.md").write_text(markdown + "\n", encoding="utf-8")
        except RuntimeError as exc:
            (run_dir / "writeup_error.txt").write_text(str(exc), encoding="utf-8")
    return report_path
