"""Deterministic evidence report for a completed candidate run."""

from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path

from autoform.paths import ROOT

from .runner import BASE, design_model, document_path, read_json, public_world, design_rules

CLAUSE_NUMBERS = {
    "character": {"D01": 4, "D02": 3, "D03": 1, "D04": 2, "D05": 5, "D06": 5, "D07": 8, "D08": 5, "D09": 9, "M_CHAR": 5},
    "authority": {"D01": 6, "D02": 7, "D03": 4, "D04": 5, "D05": 8, "D06": 8, "D07": 10, "D08": 8, "D09": 6, "M_AUTH": 7},
}


def _source_excerpt(document: str, rule_id: str) -> str:
    family = document.split("-", 1)[0]
    number = CLAUSE_NUMBERS[family].get(rule_id)
    if number is None:
        return "Source span unavailable"
    source = document_path(document).read_text(encoding="utf-8")
    match = re.search(rf"\*\*{number}\. [^*]+\*\*\s*([^\n]+)", source)
    return (match.group(1)[:260] + ("..." if len(match.group(1)) > 260 else "")) if match else "Source span unavailable"


def _candidate_records(run_dir: Path) -> list[dict]:
    records = []
    for path in sorted((run_dir / "candidates").glob("*/assessment.json")):
        label = path.parent.name
        pieces = label.split("__")
        if len(pieces) != 4:
            continue
        document, method, mode, repetition = pieces
        records.append({
            "label": label, "document": document, "method": method, "mode": mode,
            "repetition": repetition, "path": path.parent,
            "assessment": read_json(path), "candidate": read_json(path.parent / "candidate.json"),
        })
    return records


def _case_concordance(record: dict, reference: dict) -> tuple[int, int]:
    diagnostics_path = record["path"] / "case-diagnostics.json"
    if not diagnostics_path.exists():
        return 0, 0
    actual = read_json(diagnostics_path)
    match = total = 0
    for case_id, phases in reference.items():
        for phase, queries in phases.items():
            for action, expected in queries.items():
                got = actual.get(case_id, {}).get(phase, {}).get(action, {})
                if got.get("status"):
                    total += 1
                    match += got["status"] == expected["status"]
    return match, total


def _case_consequence(record: dict, reference: dict, action: str, require_difference: bool) -> str:
    path = record["path"] / "case-diagnostics.json"
    if not path.exists():
        return "Case consequence unavailable because diagnostics did not execute."
    actual = read_json(path)
    for case_id, phases in reference.items():
        for phase, queries in phases.items():
            if action not in queries:
                continue
            expected = queries[action]["status"]
            got = actual.get(case_id, {}).get(phase, {}).get(action, {}).get("status")
            if got is not None and ((got != expected) == require_difference) and (require_difference or expected != "unknown"):
                return f"Case {case_id}, {phase}: generated status `{got}`; designed status `{expected}`."
    return "No matching diagnostic consequence among the five cases."


def build_report(run_dir: Path) -> Path:
    manifest = read_json(run_dir / "manifest.json")
    for name, expected in manifest.get("file_hashes", {}).items():
        path = ROOT / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f"Run source differs from current checkout: {name}. Use the saved report or restore the run's source commit.")
    records = _candidate_records(run_dir)
    if not records:
        raise ValueError("No candidate assessments in this run")
    config = manifest["config"]
    hidden, world = design_model(), public_world()
    from .runner import case_diagnostics
    cases = read_json(BASE / "cases" / "cases.json")["cases"]
    references = {doc: case_diagnostics(world, design_rules(hidden, doc), cases) for doc in config["documents"]}
    grouped = defaultdict(list)
    for record in records:
        grouped[(record["document"], record["method"])].append(record)
    lines = [
        "# Preliminary findings", "",
        "## Experimental setup and run", "",
        f"This run used {len(config['documents'])} whole natural-language document{'s' if len(config['documents']) != 1 else ''}, {len(cases)} shared diagnostic cases, {len(config['methods'])} target backend{'s' if len(config['methods']) != 1 else ''}, {len(config['prompt_modes'])} prompt mode{'s' if len(config['prompt_modes']) != 1 else ''}, and {config['repetitions']} repetition{'s' if config['repetitions'] != 1 else ''}. The saved run contains {len(records)} candidate assessment{'s' if len(records) != 1 else ''}. Benchmark status: `{manifest.get('benchmark_status', 'unknown')}`. Formalizers received only the source document, public environment, and public world vocabulary. The hidden design model and cases were used after candidate generation. Generation provider: `{config.get('agents', {}).get('provider', 'codex')}`.",
        "",
        "The unit of analysis is a candidate constitution. Each target backend compiles from a candidate's common finite rule representation. Differences between target conditions concern method-conditioned extraction and checking, not independently generated native syntax. The source documents and cases are synthetic. Independent review votes are agent interpretations, not human annotations or semantic ground truth.",
        "",
        "Generation model: `" + config.get("agents", {}).get("generation", {}).get("model", "local Codex CLI") + "`. Review models: " + ", ".join("`" + item["model"] + "`" for item in config.get("agents", {}).get("review_models", [])) + ("." if config.get("agents", {}).get("review_models") else "local Codex CLI."),
        "",
        "## Key results", "",
        "| Document | Backend | Candidates | Schema-valid | Source quotes exact | Backend checked | Correct conflict finding | Complete exact core | Case status matches |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for document in config["documents"]:
        expected_conflict = not hidden["intended_consistency"][document]
        for method in config["methods"]:
            group = grouped.get((document, method), [])
            valid = [r for r in group if r["assessment"]["validity"].get("schema") == "valid"]
            source_valid = [r for r in valid if r["assessment"]["validity"].get("source_trace") == "valid"]
            checked = [r for r in valid if r["assessment"]["validity"].get("backend", {}).get("status") == "checked"]
            correct = sum(bool(r["assessment"]["coherence"].get("conflicts")) == expected_conflict for r in valid)
            complete = sum(not r["assessment"]["design_fidelity"].get("missing_design_rules") and not r["assessment"]["design_fidelity"].get("extra_candidate_rules") for r in valid)
            matched, total = 0, 0
            for record in valid:
                m, t = _case_concordance(record, references[document])
                matched += m
                total += t
            lines.append(f"| {document} | {method} | {len(group)} | {len(valid)} | {len(source_valid)} | {len(checked)} | {correct}/{len(valid)} | {complete}/{len(valid)} | {matched}/{total} |")
    lines += [
        "", "The conflict column compares each candidate's bounded result with the withheld design expectation. It cannot establish that the natural-language document has a unique interpretation. Case counts are diagnostic query matches across five scenarios and any stated follow-up phase; they are not independent accuracy samples.",
        "", "### Independent agent readings", "",
        "| Document | Backend | Complete candidate reviews | Unanimously supported rules | Unsupported rules | Disputed or uncertain rules |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for document in config["documents"]:
        for method in config["methods"]:
            group = grouped.get((document, method), [])
            complete = [r for r in group if r["assessment"].get("natural_language_defensibility", {}).get("status") == "agent_reviewed"]
            verdicts = [item["verdict"] for r in complete for item in r["assessment"]["natural_language_defensibility"].get("rule_verdicts", {}).values()]
            lines.append(f"| {document} | {method} | {len(complete)}/{len(group)} | {verdicts.count('supported')}/{len(verdicts)} | {verdicts.count('unsupported')} | {sum(v in {'uncertain', 'disputed_or_incomplete'} for v in verdicts)} |")
    lines += ["", "A determinate rule verdict requires all independent votes to agree. Agent-identified omissions and explanations are preserved in each candidate's review files.", "", "## Error analysis", ""]
    categories = defaultdict(list)
    for record in records:
        assessment = record["assessment"]
        validity = assessment["validity"]
        if validity.get("schema") != "valid":
            categories["Generation or schema failure"].append(record)
            continue
        if validity.get("source_trace") != "valid":
            categories["Source quote mismatch"].append(record)
        if validity.get("backend", {}).get("status") != "checked":
            categories["Native checker unavailable or failed"].append(record)
        expected = not hidden["intended_consistency"][record["document"]]
        if bool(assessment["coherence"].get("conflicts")) != expected:
            categories["Missed or spurious conflict"].append(record)
        if assessment["design_fidelity"].get("missing_design_rules"):
            categories["Omitted intended core rule"].append(record)
        if assessment["design_fidelity"].get("extra_candidate_rules"):
            categories["Added unmatched rule"].append(record)
        reviews = assessment.get("natural_language_defensibility", {})
        if reviews.get("status") == "partial_review":
            categories["Partial agent review"].append(record)
        if reviews.get("status") == "agent_reviewed":
            if any(v["verdict"] in {"unsupported", "disputed_or_incomplete"} for v in reviews.get("rule_verdicts", {}).values()):
                categories["Unsupported or disputed source reading"].append(record)
            if any(vote for vote in reviews.get("material_omissions_by_vote", [])):
                categories["Agent-noted prose omission"].append(record)
    reviewed = sum(r["assessment"].get("natural_language_defensibility", {}).get("status") == "agent_reviewed" for r in records)
    for name in ("Generation or schema failure", "Source quote mismatch", "Native checker unavailable or failed", "Missed or spurious conflict", "Omitted intended core rule", "Added unmatched rule", "Partial agent review", "Unsupported or disputed source reading", "Agent-noted prose omission"):
        examples = categories[name]
        denominator = reviewed if name in {"Unsupported or disputed source reading", "Agent-noted prose omission"} else len(records)
        if denominator == 0:
            lines.append(f"- {name}: not evaluated because independent agent review was not run.")
        else:
            lines.append(f"- {name}: {len(examples)}/{denominator} candidates" + (f". Example: `{examples[0]['label']}`." if examples else "."))
    lines += ["", "These categories overlap. A solver proof for an incomplete encoding is a valid proof of the wrong object. Exact core-rule matching is intentionally strict; a paraphrase with different guards may be a partial semantic match and needs source review.", "", "## Illustrative formalizations", ""]
    successes = [r for r in records if r["assessment"].get("design_fidelity", {}).get("matched")]
    failures = [r for r in records if r["assessment"].get("design_fidelity", {}).get("missing_design_rules") or r["assessment"].get("design_fidelity", {}).get("extra_candidate_rules")]
    if successes:
        record = successes[0]
        match = record["assessment"]["design_fidelity"]["matched"][0]
        rule = next(r for r in record["candidate"]["rules"] if r["id"] == match["candidate_id"])
        consequence = _case_consequence(record, references[record["document"]], rule["action"], False)
        backend = record["assessment"]["validity"]["backend"]
        formal_result = backend.get("expected_claim") or backend.get("conflict_query", "see saved finite check")
        lines += [f"### Preserved provision: `{record['label']}`", "", f"Source: “{rule['source_quote']}”", "", "Generated rule:", "", "```json", json.dumps(rule, indent=2), "```", "", f"The encoded rule exactly matches intended core rule `{match['design_id']}`. Native check: `{backend['status']}` ({formal_result}). {consequence} This supports fidelity for this provision under the finite vocabulary; independent source review remains separate.", ""]
    if failures:
        record = failures[0]
        fidelity = record["assessment"]["design_fidelity"]
        if fidelity.get("missing_design_rules"):
            rid = fidelity["missing_design_rules"][0]
            expected = next(r for r in design_rules(hidden, record["document"]) if r["id"] == rid)
            consequence = _case_consequence(record, references[record["document"]], expected["action"], True)
            backend = record["assessment"]["validity"]["backend"]
            formal_result = backend.get("expected_claim") or backend.get("conflict_query", "see saved finite check")
            lines += [f"### Missing or changed provision: `{record['label']}`", "", f"Source clause excerpt: “{_source_excerpt(record['document'], rid)}”", "", "Intended core rule:", "", "```json", json.dumps(expected, indent=2), "```", "", f"No generated rule exactly matched `{rid}`. Native check: `{backend['status']}` ({formal_result}). {consequence} Inspect the saved candidate and independent source-review votes before attributing the cause to the formalism.", ""]
        else:
            rid = fidelity["extra_candidate_rules"][0]
            extra = next(r for r in record["candidate"]["rules"] if r["id"] == rid)
            lines += [f"### Added rule: `{record['label']}`", "", f"Source quote: “{extra['source_quote']}”", "", "Generated rule:", "", "```json", json.dumps(extra, indent=2), "```", "", "This rule has no exact match in the designed core. The source may nevertheless support it; the agent review votes determine whether the addition is defensible.", ""]
    if not successes:
        lines += ["No candidate preserved an intended core rule exactly; there is no observed success example.", ""]
    if not failures:
        lines += ["No exact core-rule mismatch was observed; there is no observed failure example.", ""]
    lines += ["## Interpretation limits", "", "The current bounded model checks simultaneous norms under freely set exogenous facts. It does not prove eventual compliance with pending duties, coverage of every prose commitment, or absence of all ambiguity. Source defensibility is based on saved independent agent votes when review was enabled. A substantive final analysis should inspect the listed examples, disagreement records, native theory files, and compiler logs before drawing a comparative conclusion.", ""]
    output = run_dir / "findings.md"
    output.write_text("\n".join(lines), encoding="utf-8")
    return output
