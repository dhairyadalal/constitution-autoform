"""Load and validate the shared synthetic benchmark."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BENCHMARK_PATHS = [
    "data/requirements/requirements.json",
    "data/constitutions/bundles.json",
    "data/development/cases.json",
    "evaluation/heldout/cases.json",
    "data/exploratory/abstract.json",
    "docs/environment.md",
    "docs/protocol.md",
    "prompts/formalize.md",
    "prompts/decompose.md",
    "prompts/judge.md",
    "prompts/writeup.md",
]


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_benchmark() -> dict:
    requirements = read_json(ROOT / BENCHMARK_PATHS[0])
    bundles = read_json(ROOT / BENCHMARK_PATHS[1])
    development = read_json(ROOT / BENCHMARK_PATHS[2])
    heldout = read_json(ROOT / BENCHMARK_PATHS[3])
    by_requirement = {item["id"]: item for item in requirements}
    by_bundle = {item["id"]: item for item in bundles}
    if len(by_requirement) != len(requirements) or len(by_bundle) != len(bundles):
        raise ValueError("Duplicate requirement or bundle ID")
    for bundle in bundles:
        for requirement_id in bundle["requirement_ids"]:
            if requirement_id not in by_requirement:
                raise ValueError(f"Unknown requirement {requirement_id}")
    all_cases = development + heldout
    if len({case["id"] for case in all_cases}) != len(all_cases):
        raise ValueError("Duplicate case ID")
    for case in all_cases:
        bundle = by_bundle.get(case["bundle_id"])
        if bundle is None or case["target"] not in bundle["requirement_ids"]:
            raise ValueError(f"Invalid target or bundle in {case['id']}")
        if case.get("query_kind", "compliance") not in {"compliance", "explicit_permission"}:
            raise ValueError(f"Invalid query kind in {case['id']}")
        if not isinstance(case.get("events"), list):
            raise ValueError(f"Missing events in {case['id']}")
    return {
        "requirements": requirements,
        "bundles": bundles,
        "development": development,
        "heldout": heldout,
        "by_requirement": by_requirement,
        "by_bundle": by_bundle,
    }


def expanded_bundle(benchmark: dict, bundle_id: str) -> dict:
    bundle = benchmark["by_bundle"][bundle_id]
    return {
        "id": bundle_id,
        "title": bundle["title"],
        "requirements": [benchmark["by_requirement"][rid] for rid in bundle["requirement_ids"]],
    }


def file_hashes(config_path: Path) -> dict[str, str]:
    source_paths = sorted((ROOT / "src").rglob("*.py"))
    paths = [ROOT / relative for relative in BENCHMARK_PATHS] + [config_path, ROOT / "pyproject.toml", *source_paths]
    if (ROOT / "uv.lock").exists():
        paths.append(ROOT / "uv.lock")
    return {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
