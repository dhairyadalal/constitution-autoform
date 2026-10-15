"""Build the frozen preliminary results explorer from saved evidence."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

from autoform.constitution.runner import BASE, case_diagnostics, design_model, design_rules, public_world
from autoform.paths import ROOT


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def source_clauses(path: Path) -> dict[str, dict[str, str]]:
    text = path.read_text(encoding="utf-8")
    pattern = r"(?ms)^\*\*(\d+)\. ([^*]+)\*\*\s*(.*?)(?=^\*\*\d+\. |\Z)"
    result = {}
    for match in re.finditer(pattern, text):
        result[match.group(1)] = {"title": match.group(2).strip(), "text": match.group(3).strip()}
    if not result:
        raise ValueError(f"No numbered clauses found in {path}")
    return result


def case_narratives(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    pattern = r"(?ms)^## (C\d\d) · [^\n]+\n(.*?)(?=^## C\d\d · |\Z)"
    return {match.group(1): match.group(2).strip() for match in re.finditer(pattern, text)}


def compact_diagnostics(raw: dict) -> dict:
    return {
        case_id: {
            phase: {
                action: {
                    "status": item.get("status"),
                    "active": item.get("applicable_or_possible_rules", []),
                    "possible": item.get("possible", {}),
                    "certain": item.get("certain", {}),
                }
                for action, item in actions.items()
            }
            for phase, actions in phases.items()
        }
        for case_id, phases in raw.items()
    }


def build(run_dir: Path, output_path: Path, template_path: Path) -> None:
    manifest = read_json(run_dir / "manifest.json")
    for name, expected in manifest["file_hashes"].items():
        path = ROOT / name
        if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f"Saved run does not match checkout: {name}")
    if manifest.get("benchmark_status") != "frozen":
        raise ValueError("This report requires a frozen benchmark run")
    config = manifest["config"]
    world, hidden = public_world(), design_model()
    cases = read_json(BASE / "cases" / "cases.json")["cases"]
    narratives = case_narratives(BASE / "cases" / "shared-cases.md")
    documents = {
        document: source_clauses(BASE / "constitutions" / f"{document}.md")
        for document in config["documents"]
    }
    references = {
        document: compact_diagnostics(case_diagnostics(world, design_rules(hidden, document), cases))
        for document in config["documents"]
    }
    records = {}
    verdicts = Counter()
    for path in sorted((run_dir / "candidates").glob("*/assessment.json")):
        label = path.parent.name
        document, method, mode, repetition = label.split("__")
        assessment = read_json(path)
        candidate = read_json(path.parent / "candidate.json")
        review = assessment.get("natural_language_defensibility", {})
        verdicts.update(item["verdict"] for item in review.get("rule_verdicts", {}).values())
        diagnostics_path = path.parent / "case-diagnostics.json"
        records[label] = {
            "label": label,
            "document": document,
            "method": method,
            "mode": mode,
            "repetition": repetition,
            "rules": candidate.get("rules", []),
            "validity": assessment["validity"],
            "coherence": {
                "conflicts": assessment.get("coherence", {}).get("conflicts", []),
                "unreachable_rules": assessment.get("coherence", {}).get("unreachable_rules", []),
            },
            "fidelity": assessment.get("design_fidelity", {}),
            "diagnostics": compact_diagnostics(read_json(diagnostics_path)) if diagnostics_path.exists() else {},
            "review": {
                "status": review.get("status"),
                "rule_verdicts": review.get("rule_verdicts", {}),
                "omissions": review.get("material_omissions_by_vote", []),
            },
        }
    if len(records) != 64:
        raise ValueError(f"Expected 64 candidates, found {len(records)}")
    valid = [r for r in records.values() if r["validity"].get("schema") == "valid"]
    consistent = [r for r in valid if r["document"].endswith("-consistent")]
    inconsistent = [r for r in valid if r["document"].endswith("-inconsistent")]
    detected = sum(bool(r["coherence"]["conflicts"]) for r in inconsistent)
    if len(valid) != 63 or len(consistent) != 32 or len(inconsistent) != 31 or detected != 16:
        raise ValueError("Observed run counts differ from the analysis written for this report")
    call_logs = list((run_dir / "candidates").glob("**/stderr.log"))
    cli_tokens = []
    for log in call_logs:
        matches = re.findall(r"tokens used\s*\n([\d,]+)", log.read_text(encoding="utf-8", errors="replace"))
        if matches:
            cli_tokens.append(int(matches[-1].replace(",", "")))
    if len(call_logs) != 253 or len(cli_tokens) != 253:
        raise ValueError("Expected token usage from all 253 Codex calls")
    first_call = datetime.fromisoformat(manifest["created_at_utc"]).timestamp()
    last_assessment = max(path.stat().st_mtime for path in (run_dir / "candidates").glob("*/assessment.json"))
    elapsed_seconds = round(last_assessment - first_call)
    method_stats = []
    for method in config["methods"]:
        group = [r for r in records.values() if r["method"] == method]
        inc = [r for r in group if r["document"].endswith("-inconsistent") and r["validity"].get("schema") == "valid"]
        con = [r for r in group if r["document"].endswith("-consistent") and r["validity"].get("schema") == "valid"]
        method_stats.append({
            "method": method,
            "consistent_clear": sum(not r["coherence"]["conflicts"] for r in con),
            "consistent_valid": len(con),
            "inconsistent_detected": sum(bool(r["coherence"]["conflicts"]) for r in inc),
            "inconsistent_valid": len(inc),
            "invalid": sum(r["validity"].get("schema") != "valid" for r in group),
        })
    payload = {
        "run": {"path": str(run_dir.relative_to(ROOT)), "commit": "3f10fb9", "config": config, "created_at_utc": manifest["created_at_utc"]},
        "stats": {
            "total": len(records), "valid": len(valid), "checked": sum(r["validity"].get("backend", {}).get("status") == "checked" for r in valid),
            "source_exact": sum(r["validity"].get("source_trace") == "valid" for r in valid),
            "consistent_clear": sum(not r["coherence"]["conflicts"] for r in consistent),
            "consistent_valid": len(consistent), "inconsistent_detected": detected,
            "inconsistent_valid": len(inconsistent),
            "complete_core": sum(not r["fidelity"].get("missing_design_rules") and not r["fidelity"].get("extra_candidate_rules") for r in valid),
            "review_verdicts": dict(verdicts), "method": method_stats,
            "model_calls": len(call_logs), "cli_reported_tokens": sum(cli_tokens), "elapsed_seconds": elapsed_seconds,
        },
        "cases": {case["id"]: {**case, "narrative": narratives[case["id"]]} for case in cases},
        "documents": documents,
        "references": references,
        "candidates": records,
    }
    template = template_path.read_text(encoding="utf-8")
    replacements = {
        "{{VALID}}": str(len(valid)),
        "{{DETECTED}}": str(detected),
        "{{SOURCE_EXACT}}": str(payload["stats"]["source_exact"]),
        "{{REVIEW_SUPPORTED}}": str(verdicts["supported"]),
        "{{REVIEW_TOTAL}}": str(sum(verdicts.values())),
        "{{RUN_PATH}}": payload["run"]["path"],
        "{{RUN_COMMIT}}": payload["run"]["commit"],
        "{{MODEL_CALLS}}": str(len(call_logs)),
        "{{CLI_TOKENS}}": f"{sum(cli_tokens):,}",
        "{{ELAPSED}}": f"{elapsed_seconds // 60}m {elapsed_seconds % 60:02d}s",
    }
    for key, value in replacements.items():
        template = template.replace(key, value)
    evidence = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    if "<!--EVIDENCE_JSON-->" not in template:
        raise ValueError("Template has no evidence placeholder")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(template.replace("<!--EVIDENCE_JSON-->", evidence), encoding="utf-8")
    print(f"Wrote {output_path} ({output_path.stat().st_size:,} bytes)")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python reports/build_preliminary.py runs/<frozen-run>")
    build((ROOT / sys.argv[1]).resolve(), ROOT / "reports" / "preliminary-results.html", ROOT / "reports" / "preliminary-template.html")
