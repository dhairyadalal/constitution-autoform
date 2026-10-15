"""Command line interface for the preliminary experiment."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from .backends import METHODS
from .codex import (
    FORMALIZATION_SCHEMA, JUDGMENT_SCHEMA, call_codex, prompt_file,
)
from .dataset import ROOT, expanded_bundle, file_hashes, load_benchmark, read_json
from .evaluation.execute import execute_candidate
from .evaluation.score import aggregate_votes, score_candidate
from .reporting import build_report


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def version_of(command: list[str]) -> str:
    try:
        result = subprocess.run(command, text=True, capture_output=True, timeout=10, check=False)
        return (result.stdout or result.stderr).strip().splitlines()[-1]
    except (OSError, subprocess.TimeoutExpired, IndexError):
        return "unavailable"


def candidate_prompt(bundle: dict, method: str, mode: str, environment: str) -> str:
    base = prompt_file("formalize.md")
    if mode == "decompose":
        base += "\n\n" + prompt_file("decompose.md")
    else:
        base += "\n\nSet `decomposition` to an empty array."
    return (
        base + "\n\nMETHOD:\n" + method + ": " + METHODS[method]["api"]
        + "\n\nENVIRONMENT:\n" + environment
        + "\n\nREQUIREMENT BUNDLE:\n" + json.dumps(bundle, indent=2)
    )


def judge_prompt(bundle: dict, cases: list[dict], environment: str) -> str:
    return (
        prompt_file("judge.md") + "\n\nENVIRONMENT:\n" + environment
        + "\n\nREQUIREMENT BUNDLE:\n" + json.dumps(bundle, indent=2)
        + "\n\nCASES:\n" + json.dumps(cases, indent=2)
    )


def run_experiment(config_path: Path, run_dir: Path | None, agent_writeup: bool) -> Path:
    benchmark = load_benchmark()
    config = read_json(config_path)
    unknown_bundles = set(config["bundle_ids"]) - set(benchmark["by_bundle"])
    unknown_methods = set(config["methods"]) - set(METHODS)
    if unknown_bundles or unknown_methods:
        raise ValueError(f"Unknown bundles {unknown_bundles}; unknown methods {unknown_methods}")
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + config["name"]
    run_dir = run_dir or ROOT / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    current_hashes = file_hashes(config_path)
    manifest_path = run_dir / "manifest.json"
    if manifest_path.exists():
        manifest = read_json(manifest_path)
        if manifest["file_hashes"] != current_hashes:
            raise RuntimeError("Frozen benchmark/config hash changed; create a new run")
    else:
        manifest = {
            "run_id": run_dir.name,
            "started_at_utc": datetime.now(timezone.utc).isoformat(),
            "config": config,
            "bundle_ids": config["bundle_ids"],
            "methods": config["methods"],
            "prompt_modes": config["prompt_modes"],
            "repetitions": config["repetitions"],
            "judge_votes": config["judge_votes"],
            "file_hashes": current_hashes,
            "python": sys.version,
            "codex_cli": version_of(["codex", "--version"]),
            "z3": version_of(["z3", "--version"]),
            "clingo": version_of(["clingo", "--version"]),
        }
        write_json(manifest_path, manifest)
    environment = (ROOT / "docs/environment.md").read_text(encoding="utf-8")
    cases = [case for case in benchmark["heldout"] if case["bundle_id"] in config["bundle_ids"]]
    runnable = [method for method in config["methods"] if METHODS[method]["package"]]
    unavailable = [method for method in config["methods"] if not METHODS[method]["package"]]
    write_json(run_dir / "availability.json", {"runnable": runnable, "not_run": unavailable})

    # Generate all candidate formalizations before asking agents to judge any held-out case.
    generation_jobs = []
    for bundle_id in config["bundle_ids"]:
        for method in runnable:
            for mode in config["prompt_modes"]:
                for repeat in range(1, config["repetitions"] + 1):
                    generation_jobs.append((bundle_id, method, mode, repeat))

    def generate_one(job: tuple[str, str, str, int]) -> dict:
        bundle_id, method, mode, repeat = job
        candidate_id = f"{bundle_id}__{method}__{mode}__{repeat:02d}"
        candidate_dir = run_dir / "candidates" / candidate_id
        artifact_path = candidate_dir / "candidate.json"
        if artifact_path.exists():
            artifact = read_json(artifact_path)
        else:
            print(f"Generate {candidate_id}", flush=True)
            prompt = candidate_prompt(expanded_bundle(benchmark, bundle_id), method, mode, environment)
            try:
                artifact = call_codex(
                    prompt, FORMALIZATION_SCHEMA, candidate_dir / "codex_call",
                    config["codex_timeout_seconds"],
                )
            except RuntimeError as exc:
                artifact = {
                    "code": "", "assumptions": [], "unsupported_requirements": [],
                    "decomposition": [], "error": str(exc),
                }
            write_json(artifact_path, artifact)
            (candidate_dir / "candidate.py").write_text(artifact.get("code", ""), encoding="utf-8")
        return {
            "candidate_id": candidate_id, "bundle_id": bundle_id,
            "method": method, "prompt_mode": mode,
            "repetition": repeat, "artifact": artifact,
        }

    candidate_specs = []
    workers = max(1, int(config.get("max_parallel_codex_calls", 1)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(generate_one, job) for job in generation_jobs]
        for future in as_completed(futures):
            candidate_specs.append(future.result())
    candidate_specs.sort(key=lambda item: item["candidate_id"])

    # Fresh calls judge the cases without seeing candidate source or method names.
    reference = {}
    for bundle_id in config["bundle_ids"]:
        bundle_cases = [case for case in cases if case["bundle_id"] == bundle_id]
        if not bundle_cases:
            continue
        bundle = expanded_bundle(benchmark, bundle_id)
        votes = []
        for vote_index in range(1, config["judge_votes"] + 1):
            vote_dir = run_dir / "reference_votes" / bundle_id / f"vote_{vote_index:02d}"
            vote_path = vote_dir / "vote.json"
            if vote_path.exists():
                vote = read_json(vote_path)
            else:
                print(f"Judge {bundle_id} vote {vote_index}", flush=True)
                try:
                    vote = call_codex(
                        judge_prompt(bundle, bundle_cases, environment),
                        JUDGMENT_SCHEMA, vote_dir / "codex_call",
                        config["codex_timeout_seconds"],
                    )
                except RuntimeError as exc:
                    vote = {"judgments": [], "error": str(exc)}
                write_json(vote_path, vote)
            votes.append(vote)
        reference.update(aggregate_votes(votes, [case["id"] for case in bundle_cases]))
    write_json(run_dir / "reference.json", reference)

    results = {"case_ids": [case["id"] for case in cases], "not_run_methods": unavailable, "candidates": []}
    for spec in candidate_specs:
        bundle_cases = [case for case in cases if case["bundle_id"] == spec["bundle_id"]]
        case_results = [
            {
                "case_id": case["id"],
                "result": execute_candidate(
                    spec["artifact"].get("code", ""), spec["method"], case,
                    config["candidate_timeout_seconds"],
                ),
            }
            for case in bundle_cases
        ]
        candidate = {key: value for key, value in spec.items() if key != "artifact"}
        candidate["assumptions"] = spec["artifact"].get("assumptions", [])
        candidate["unsupported_requirements"] = spec["artifact"].get("unsupported_requirements", [])
        candidate["generation_error"] = spec["artifact"].get("error")
        candidate["case_results"] = case_results
        candidate["score"] = score_candidate(case_results, reference)
        results["candidates"].append(candidate)
    write_json(run_dir / "results.json", results)
    report_path = build_report(run_dir, agent_writeup=agent_writeup, timeout=config["codex_timeout_seconds"])
    public_report = run_dir / "findings.md" if (run_dir / "findings.md").exists() else report_path
    (ROOT / "reports").mkdir(exist_ok=True)
    (ROOT / "reports" / f"{run_dir.name}-findings.md").write_text(
        public_report.read_text(encoding="utf-8"), encoding="utf-8"
    )
    print(f"Run saved to {run_dir}", flush=True)
    return run_dir


def main() -> None:
    parser = argparse.ArgumentParser(prog="autoform", description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("inventory", help="Show shared dataset and registered methods")
    run_parser = subparsers.add_parser("run", help="Generate, judge, evaluate, and report")
    run_parser.add_argument("--config", type=Path, default=ROOT / "configs/pilot.json")
    run_parser.add_argument("--run-dir", type=Path, default=None, help="Resume an existing run directory")
    run_parser.add_argument("--no-agent-writeup", action="store_true")
    report_parser = subparsers.add_parser("report", help="Regenerate a report from saved results")
    report_parser.add_argument("--run", type=Path, required=True)
    report_parser.add_argument("--agent-writeup", action="store_true")
    args = parser.parse_args()
    if args.command == "inventory":
        benchmark = load_benchmark()
        print(f"Requirements: {len(benchmark['requirements'])}")
        print(f"Categories: {len({r['category'] for r in benchmark['requirements']})}")
        print(f"Bundles: {len(benchmark['bundles'])}")
        print(f"Development cases: {len(benchmark['development'])}")
        print(f"Held-out cases: {len(benchmark['heldout'])}")
        print("Methods: " + ", ".join(METHODS))
    elif args.command == "run":
        run_experiment(args.config.resolve(), args.run_dir.resolve() if args.run_dir else None, not args.no_agent_writeup)
    elif args.command == "report":
        print(build_report(args.run.resolve(), agent_writeup=args.agent_writeup))


if __name__ == "__main__":
    main()
