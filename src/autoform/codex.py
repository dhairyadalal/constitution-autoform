"""Isolated Codex CLI calls with structured responses and saved traces."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path



def call_codex(prompt: str, schema: dict, trace_dir: Path, timeout: int) -> dict:
    trace_dir.mkdir(parents=True, exist_ok=True)
    (trace_dir / "prompt.txt").write_text(prompt, encoding="utf-8")
    if shutil.which("codex") is None:
        raise RuntimeError("Codex CLI is unavailable on PATH")
    with tempfile.TemporaryDirectory(prefix="spar-autoform-") as temp:
        temp_path = Path(temp)
        schema_path = temp_path / "schema.json"
        output_path = temp_path / "response.json"
        schema_path.write_text(json.dumps(schema), encoding="utf-8")
        command = [
            "codex", "-a", "never", "exec", "--ephemeral", "--skip-git-repo-check",
            "-s", "read-only", "-C", str(temp_path),
            "--output-schema", str(schema_path), "-o", str(output_path), "-",
        ]
        (trace_dir / "command.json").write_text(json.dumps(command, indent=2), encoding="utf-8")
        try:
            result = subprocess.run(
                command,
                input="Answer using only the content of this prompt. Do not inspect local files or use external tools.\n\n" + prompt,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            (trace_dir / "error.txt").write_text(f"Codex timed out after {timeout}s\n{exc}", encoding="utf-8")
            raise RuntimeError(f"Codex timed out after {timeout}s") from exc
        (trace_dir / "stdout.log").write_text(result.stdout, encoding="utf-8")
        (trace_dir / "stderr.log").write_text(result.stderr, encoding="utf-8")
        metadata = {}
        for key in ("model", "provider", "reasoning effort", "sandbox", "approval"):
            match = re.search(rf"^{re.escape(key)}: (.+)$", result.stderr, re.MULTILINE)
            if match:
                metadata[key.replace(" ", "_")] = match.group(1)
        (trace_dir / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
        if result.returncode != 0:
            raise RuntimeError(f"Codex exited {result.returncode}; see {trace_dir / 'stderr.log'}")
        if not output_path.exists():
            raise RuntimeError(f"Codex returned no structured output; see {trace_dir}")
        raw = output_path.read_text(encoding="utf-8")
        (trace_dir / "response.json").write_text(raw, encoding="utf-8")
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Invalid Codex JSON; see {trace_dir / 'response.json'}") from exc
