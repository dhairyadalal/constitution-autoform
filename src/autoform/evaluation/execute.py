"""Execute a saved solver-backed candidate on a single shared case."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from ..backends import candidate_source_issue

_WRAPPER = """
import json
import runpy
import sys
module = runpy.run_path(sys.argv[1])
case = json.load(sys.stdin)
result = module['evaluate'](case)
print(json.dumps(result))
"""
VALID_ANSWERS = {"yes", "no", "unresolved"}


def execute_candidate(code: str, method: str, case: dict, timeout: int) -> dict:
    issue = candidate_source_issue(code, method)
    if issue:
        return {"status": "invalid_source", "answer": None, "reason": issue}
    with tempfile.TemporaryDirectory(prefix="spar-candidate-") as temp:
        path = Path(temp) / "candidate.py"
        path.write_text(code, encoding="utf-8")
        try:
            process = subprocess.run(
                [sys.executable, "-I", "-c", _WRAPPER, str(path)],
                input=json.dumps(case),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=temp,
                env={"PATH": os.environ.get("PATH", ""), "PYTHONNOUSERSITE": "1"},
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return {"status": "timeout", "answer": None, "reason": f"Exceeded {timeout}s"}
        if process.returncode != 0:
            return {
                "status": "runtime_error",
                "answer": None,
                "reason": process.stderr[-2000:] or f"Exit code {process.returncode}",
            }
        try:
            output = json.loads(process.stdout)
        except json.JSONDecodeError:
            return {"status": "invalid_output", "answer": None, "reason": process.stdout[-1000:]}
        if not isinstance(output, dict) or output.get("answer") not in VALID_ANSWERS:
            return {"status": "invalid_output", "answer": None, "reason": repr(output)[:1000]}
        return {
            "status": "valid",
            "answer": output["answer"],
            "reason": str(output.get("reason", ""))[:1000],
        }
