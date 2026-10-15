"""Prepare, generate, and assess whole-document constitution formalizations."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from autoform.codex import call_codex
from autoform.paths import ROOT

from .asp import check_asp
from .fol import check_fol
from .isabelle import check_theory
from .model import analyze, case_status, validate
from .smt import check_smt

BASE = ROOT / "data" / "benchmark"
METHODS = {"smt", "fol", "asp", "isabelle"}
METHOD_GUIDANCE = {
    "smt": "The rules will be compiled to a quantifier-free Boolean SMT query over possible states.",
    "fol": "The rules will be compiled to quantified first-order predicates over states and actions.",
    "asp": "The rules will be compiled to a stable-model program with explicit choices for unknown facts.",
    "isabelle": "The rules will be compiled to Isabelle/HOL definitions and a checked theorem about conflict or a concrete witness.",
}
RULE_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "id": {"type": "string"}, "force": {"type": "string", "enum": ["O", "F", "P"]},
        "action": {"type": "string"},
        "all": {"type": "array", "items": {"type": "string"}},
        "not": {"type": "array", "items": {"type": "string"}},
        "due": {"type": "string", "enum": ["current_decision", "next_decision"]},
        "source_clause": {"type": "string"}, "source_quote": {"type": "string"},
        "overrides": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["id", "force", "action", "all", "not", "due", "source_clause", "source_quote", "overrides"],
}
CANDIDATE_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "rules": {"type": "array", "items": RULE_SCHEMA},
        "assumptions": {"type": "array", "items": {"type": "string"}},
        "unsupported_clauses": {"type": "array", "items": {"type": "string"}},
        "decomposition": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["rules", "assumptions", "unsupported_clauses", "decomposition"],
}
REVIEW_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "rule_reviews": {"type": "array", "items": {
            "type": "object", "additionalProperties": False,
            "properties": {
                "rule_id": {"type": "string"},
                "assessment": {"type": "string", "enum": ["supported", "unsupported", "uncertain"]},
                "reason": {"type": "string"}, "alternative_reading": {"type": "string"},
            },
            "required": ["rule_id", "assessment", "reason", "alternative_reading"],
        }},
        "material_omissions": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["rule_reviews", "material_omissions"],
}
BENCHMARK_REVIEW_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "consistent_conflict": {"type": "string", "enum": ["found", "not_found", "uncertain"]},
        "inconsistent_conflict": {"type": "string", "enum": ["found", "not_found", "uncertain"]},
        "conflict_witness": {"type": "string"},
        "unintended_pair_changes": {"type": "array", "items": {"type": "string"}},
        "ambiguous_readings": {"type": "array", "items": {"type": "string"}},
        "case_issues": {"type": "array", "items": {"type": "string"}},
        "reasoning": {"type": "string"},
    },
    "required": ["consistent_conflict", "inconsistent_conflict", "conflict_witness", "unintended_pair_changes", "ambiguous_readings", "case_issues", "reasoning"],
}


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def public_world() -> dict:
    return read_json(BASE / "world.json")


def design_model() -> dict:
    return read_json(BASE / "authoring" / "design-model.json")


def document_path(document: str) -> Path:
    if document not in {"character-consistent", "character-inconsistent", "authority-consistent", "authority-inconsistent"}:
        raise ValueError(f"Unknown document: {document}")
    return BASE / "constitutions" / f"{document}.md"


def design_rules(model: dict, document: str) -> list[dict]:
    family, variant = document.split("-", 1)
    rules = list(model["shared_rules"])
    if variant == "inconsistent":
        mutation_id = model["families"][family]["mutation_id"]
        rules.append(next(item for item in model["mutations"] if item["id"] == mutation_id))
    return rules


def _signature(rule: dict) -> tuple:
    return (
        rule["force"], rule["action"], tuple(sorted(rule.get("all", []))),
        tuple(sorted(rule.get("not", []))), rule.get("due", "current_decision"),
        tuple(sorted(rule.get("overrides", []))),
    )


def design_fidelity(candidate: list[dict], intended: list[dict]) -> dict:
    remaining = list(candidate)
    matched, missing = [], []
    for expected in intended:
        match = next((r for r in remaining if _signature(r) == _signature(expected)), None)
        if match is None:
            missing.append(expected["id"])
        else:
            matched.append({"design_id": expected["id"], "candidate_id": match["id"]})
            remaining.remove(match)
    return {"matched": matched, "missing_design_rules": missing, "extra_candidate_rules": [r["id"] for r in remaining], "scope": "exact match of the encoded core; broader prose and near matches require separate review"}


def backend_check(world: dict, rules: list[dict], method: str, path: Path, timeout: int) -> dict:
    if method == "smt":
        return check_smt(world, rules, path)
    if method == "fol":
        return check_fol(world, rules, path)
    if method == "asp":
        return check_asp(world, rules, path)
    if method == "isabelle":
        return check_theory(world, rules, path, timeout)
    raise ValueError(f"Unknown method: {method}")


def case_diagnostics(world: dict, rules: list[dict], cases: list[dict]) -> dict:
    diagnostics = {}
    for case in cases:
        entry = {"initial": {action: case_status(world, rules, case, action) for action in case["queries"]}}
        for followup in case.get("followups", []):
            phase_case = {"facts": {**case["facts"], **followup["facts"]}}
            entry[followup["label"]] = {action: case_status(world, rules, phase_case, action) for action in followup["queries"]}
        diagnostics[case["id"]] = entry
    return diagnostics


def assess_candidate(candidate: dict, document: str, method: str, path: Path, timeout: int) -> dict:
    if candidate.get("generation_error"):
        return {
            "validity": {"schema": "generation_failed", "source_trace": "not_checked", "reason": candidate["generation_error"]},
            "coherence": {"status": "not_checked"},
            "design_fidelity": {"status": "not_checked"},
            "natural_language_defensibility": {"status": "not_run"},
        }
    world = public_world()
    rules = candidate.get("rules", [])
    source = document_path(document).read_text(encoding="utf-8")
    try:
        validate(world, rules)
        quote_issues = [r["id"] for r in rules if not r.get("source_quote") or r["source_quote"] not in source]
        finite = analyze(world, rules)
        backend = backend_check(world, rules, method, path / "backend", timeout)
        cases = read_json(BASE / "cases" / "cases.json")["cases"]
        diagnostics = case_diagnostics(world, rules, cases)
        write_json(path / "case-diagnostics.json", diagnostics)
        return {
            "validity": {"schema": "valid", "source_trace": "valid" if not quote_issues else "quote_mismatch", "quote_issues": quote_issues, "backend": backend},
            "coherence": finite,
            "design_fidelity": design_fidelity(rules, design_rules(design_model(), document)),
            "natural_language_defensibility": {"status": "not_run", "reason": "Independent agent review must be requested separately"},
            "case_diagnostics": "case-diagnostics.json",
            "unsupported_clauses": candidate.get("unsupported_clauses", []),
        }
    except (KeyError, TypeError, ValueError, RuntimeError) as exc:
        return {
            "validity": {"schema": "invalid", "reason": str(exc)},
            "coherence": {"status": "not_checked"},
            "design_fidelity": {"status": "not_checked"},
            "natural_language_defensibility": {"status": "not_run"},
        }


def _files_for_manifest(config_path: Path) -> list[Path]:
    files = [config_path.resolve(), BASE / "environment.md", BASE / "world.json", BASE / "cases" / "shared-cases.md", BASE / "cases" / "cases.json", BASE / "authoring" / "design-model.json", ROOT / "prompts" / "formalize.md", ROOT / "prompts" / "review.md", ROOT / "prompts" / "benchmark_review.md"]
    files += sorted((BASE / "constitutions").glob("*.md"))
    return files


def _hashes(files: list[Path]) -> dict[str, str]:
    return {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in files}


def generation_prompt(document: str, method: str, mode: str) -> str:
    if method not in METHODS or mode not in {"direct", "structured"}:
        raise ValueError("Unknown method or prompt mode")
    instruction = ("List candidate provisions and their relationships in `decomposition` before encoding rules." if mode == "structured" else "Set `decomposition` to an empty array and formalize directly.")
    return "\n\n".join([
        (ROOT / "prompts" / "formalize.md").read_text(encoding="utf-8"),
        f"Target checker: {method}. {METHOD_GUIDANCE[method]} {instruction}",
        "PUBLIC WORLD VOCABULARY AND SEMANTICS:\n" + json.dumps(public_world(), indent=2),
        "COMMON ENVIRONMENT:\n" + (BASE / "environment.md").read_text(encoding="utf-8"),
        "NATURAL-LANGUAGE SPECIFICATION:\n" + document_path(document).read_text(encoding="utf-8"),
    ])


def review_candidate(candidate: dict, document: str, path: Path, votes: int, timeout: int) -> dict:
    source = document_path(document).read_text(encoding="utf-8")
    prompt = "\n\n".join([(ROOT / "prompts" / "review.md").read_text(encoding="utf-8"), "SPECIFICATION:\n" + source, "PROPOSED RULES:\n" + json.dumps(candidate.get("rules", []), indent=2)])
    batches = []
    for index in range(1, votes + 1):
        vote_path = path / f"vote-{index:02d}.json"
        if vote_path.exists():
            vote = read_json(vote_path)
        else:
            try:
                vote = call_codex(prompt, REVIEW_SCHEMA, path / f"call-{index:02d}", timeout)
            except RuntimeError as exc:
                vote = {"rule_reviews": [], "material_omissions": [], "error": str(exc)}
            write_json(vote_path, vote)
        batches.append(vote)
    verdicts = {}
    complete = all("error" not in batch for batch in batches)
    for rule in candidate.get("rules", []):
        choices = []
        for batch in batches:
            matching = [r for r in batch.get("rule_reviews", []) if r.get("rule_id") == rule["id"]]
            if len(matching) == 1:
                choices.append(matching[0]["assessment"])
            else:
                complete = False
        verdicts[rule["id"]] = {"verdict": choices[0] if len(choices) == votes and len(set(choices)) == 1 else "disputed_or_incomplete", "votes": choices}
    return {"status": "agent_reviewed" if complete else "partial_review", "reviewer_count": votes, "rule_verdicts": verdicts, "material_omissions_by_vote": [batch.get("material_omissions", []) for batch in batches], "votes_preserved_at": str(path), "qualification": "Independent agent readings, not human annotation or semantic ground truth"}


def review_benchmark(output_dir: Path, votes: int, timeout: int) -> Path:
    if votes < 3:
        raise ValueError("At least three independent review calls are required")
    instruction = (ROOT / "prompts" / "benchmark_review.md").read_text(encoding="utf-8")
    environment = (BASE / "environment.md").read_text(encoding="utf-8")
    cases = (BASE / "cases" / "shared-cases.md").read_text(encoding="utf-8")
    reviews = {}
    for family in ("character", "authority"):
        prompt = "\n\n".join([instruction, "ENVIRONMENT:\n" + environment, "CONSISTENT VERSION:\n" + document_path(family + "-consistent").read_text(encoding="utf-8"), "MUTATED VERSION:\n" + document_path(family + "-inconsistent").read_text(encoding="utf-8"), "SHARED CASES:\n" + cases])
        reviews[family] = []
        for index in range(1, votes + 1):
            path = output_dir / family / f"vote-{index:02d}.json"
            if path.exists():
                vote = read_json(path)
            else:
                try:
                    vote = call_codex(prompt, BENCHMARK_REVIEW_SCHEMA, output_dir / family / f"call-{index:02d}", timeout)
                except RuntimeError as exc:
                    vote = {"error": str(exc)}
                write_json(path, vote)
            reviews[family].append(vote)
    record = {"status": "agent_reviewed", "votes_per_family": votes, "families": reviews, "qualification": "Independent agent readings, not human annotation or semantic ground truth"}
    write_json(output_dir / "review-record.json", record)
    return output_dir / "review-record.json"


def run(config_path: Path, output_dir: Path, with_reviews: bool = False, allow_provisional: bool = False) -> None:
    config = read_json(config_path)
    if set(config["methods"]) - METHODS:
        raise ValueError("Unknown method in config")
    hashes = _hashes(_files_for_manifest(config_path))
    freeze_path = BASE / "freeze.json"
    if freeze_path.exists():
        frozen = read_json(freeze_path)
        if frozen.get("file_hashes") != hashes:
            raise RuntimeError("Frozen benchmark or prompt changed; create a new benchmark version")
    elif not allow_provisional:
        raise RuntimeError("Benchmark is provisional; review and freeze it before a main run, or use --allow-provisional for a development smoke run")
    manifest_path = output_dir / "manifest.json"
    if manifest_path.exists():
        if read_json(manifest_path)["file_hashes"] != hashes:
            raise RuntimeError("Benchmark or prompt changed; create a new run directory")
    else:
        write_json(manifest_path, {"created_at_utc": datetime.now(timezone.utc).isoformat(), "config": config, "file_hashes": hashes, "benchmark_status": "frozen" if freeze_path.exists() else "provisional_development", "isolation": "Formalizer invoked in a separate temporary working directory; prompt contains public inputs only. Host filesystem access is not blocked."})
    for document in config["documents"]:
        for method in config["methods"]:
            for mode in config["prompt_modes"]:
                for repetition in range(1, config["repetitions"] + 1):
                    label = f"{document}__{method}__{mode}__{repetition:02d}"
                    path = output_dir / "candidates" / label
                    candidate_path = path / "candidate.json"
                    if candidate_path.exists():
                        candidate = read_json(candidate_path)
                    else:
                        try:
                            candidate = call_codex(generation_prompt(document, method, mode), CANDIDATE_SCHEMA, path / "codex_call", config["codex_timeout_seconds"])
                        except RuntimeError as exc:
                            candidate = {"rules": [], "assumptions": [], "unsupported_clauses": [], "decomposition": [], "generation_error": str(exc)}
                        write_json(candidate_path, candidate)
                    result = assess_candidate(candidate, document, method, path, config["isabelle_timeout_seconds"])
                    if with_reviews and result["validity"].get("schema") == "valid":
                        result["natural_language_defensibility"] = review_candidate(candidate, document, path / "reviews", config["review_votes"], config["codex_timeout_seconds"])
                    write_json(path / "assessment.json", result)
                    print(f"{label}: {result['validity']['schema']}, {result['validity'].get('backend', {}).get('status', 'not_checked')}", flush=True)
    from .report import build_report
    print(f"Report: {build_report(output_dir)}", flush=True)


def check_design(output_dir: Path, timeout: int) -> dict:
    world, hidden = public_world(), design_model()
    for key in ("facts", "actions", "state_constraints", "action_preconditions", "action_effects"):
        if world[key] != hidden[key]:
            raise ValueError(f"Public world and authoring model diverge: {key}")
    results = {}
    cases = read_json(BASE / "cases" / "cases.json")["cases"]
    for document in ("character-consistent", "character-inconsistent", "authority-consistent", "authority-inconsistent"):
        rules = design_rules(hidden, document)
        path = output_dir / document
        results[document] = {
            "coherence": analyze(world, rules),
            "cases": case_diagnostics(world, rules, cases),
            "backends": {method: backend_check(world, rules, method, path / method, timeout) for method in sorted(METHODS)},
        }
    write_json(output_dir / "design-check.json", results)
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    design = sub.add_parser("check-design", help="Check withheld authoring rules in all four backends")
    design.add_argument("--output", type=Path, default=ROOT / "runs" / "design-check")
    design.add_argument("--isabelle-timeout", type=int, default=300)
    experiment = sub.add_parser("run", help="Generate and assess method-conditioned candidates")
    experiment.add_argument("--config", type=Path, default=ROOT / "configs" / "preliminary.json")
    experiment.add_argument("--output", type=Path, required=True)
    experiment.add_argument("--reviews", action="store_true")
    experiment.add_argument("--allow-provisional", action="store_true", help="Only for development smoke runs")
    freeze = sub.add_parser("freeze", help="Record reviewed source and prompt hashes")
    freeze.add_argument("--config", type=Path, default=ROOT / "configs" / "preliminary.json")
    freeze.add_argument("--review-record", type=Path, required=True)
    benchmark_review = sub.add_parser("review-benchmark", help="Collect independent agent reviews before freezing")
    benchmark_review.add_argument("--output", type=Path, required=True)
    benchmark_review.add_argument("--votes", type=int, default=3)
    benchmark_review.add_argument("--timeout", type=int, default=300)
    report = sub.add_parser("report", help="Write an evidence report from saved candidate assessments")
    report.add_argument("--run", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "check-design":
        results = check_design(args.output, args.isabelle_timeout)
        for name, result in results.items():
            print(f"{name}: {len(result['coherence']['conflicts'])} conflicts; " + ", ".join(f"{method}={value['status']}" for method, value in result["backends"].items()))
    elif args.command == "freeze":
        if not args.review_record.is_file():
            raise ValueError("Independent review record is missing")
        review = read_json(args.review_record)
        if review.get("status") != "agent_reviewed" or review.get("votes_per_family", 0) < 3:
            raise ValueError("Independent benchmark review is incomplete")
        if any(len(review.get("families", {}).get(family, [])) != review["votes_per_family"] or any("error" in vote for vote in review["families"][family]) for family in ("character", "authority")):
            raise ValueError("Independent benchmark review has missing or failed votes")
        hashes = _hashes(_files_for_manifest(args.config))
        write_json(BASE / "freeze.json", {"frozen_at_utc": datetime.now(timezone.utc).isoformat(), "review_record": str(args.review_record), "review_record_sha256": hashlib.sha256(args.review_record.read_bytes()).hexdigest(), "file_hashes": hashes})
        print(f"Frozen {len(hashes)} source and prompt files")
    elif args.command == "report":
        from .report import build_report
        print(build_report(args.run))
    elif args.command == "review-benchmark":
        print(review_benchmark(args.output, args.votes, args.timeout))
    else:
        run(args.config, args.output, args.reviews, args.allow_provisional)


if __name__ == "__main__":
    main()
