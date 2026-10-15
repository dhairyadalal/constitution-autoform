"""Model selection and NVIDIA hosted inference for experiment agents."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from urllib import error, parse, request

from autoform.codex import call_codex
from autoform.paths import ROOT

NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"


def nvidia_api_key() -> str:
    """Read the key from the process environment or the repo's ignored .env file."""
    value = os.environ.get("NVIDIA_API_KEY", "").strip()
    if value:
        return value
    env_path = ROOT / ".env"
    if env_path.is_file():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            name, raw = stripped.split("=", 1)
            if name.strip() == "NVIDIA_API_KEY":
                value = raw.strip().strip('"\'').strip()
                if value:
                    return value
    raise RuntimeError(f"NVIDIA_API_KEY is missing. Add it to {env_path} or set it in the environment.")


def agent_spec(config: dict, role: str, vote_index: int = 0) -> dict:
    """Select one fixed generation model or the designated review model."""
    agents = config.get("agents", {"provider": "codex"})
    provider = agents.get("provider", "codex")
    if provider == "codex":
        return {"provider": "codex"}
    if provider != "nvidia":
        raise ValueError(f"Unknown agent provider: {provider}")
    if role == "generation":
        selected = agents.get("generation")
    elif role == "review":
        reviewers = agents.get("review_models", [])
        if vote_index < 1 or vote_index > len(reviewers):
            raise ValueError(f"Review vote {vote_index} has no configured model")
        selected = reviewers[vote_index - 1]
    else:
        raise ValueError(f"Unknown agent role: {role}")
    if not isinstance(selected, dict) or not selected.get("model"):
        raise ValueError(f"No NVIDIA model configured for {role}")
    return {
        "provider": "nvidia",
        "model": selected["model"],
        "temperature": selected.get("temperature", 0.2),
        "max_tokens": selected.get("max_tokens", 4096),
        "base_url": agents.get("base_url", NVIDIA_BASE_URL).rstrip("/"),
    }


def configured_models(config: dict) -> list[dict]:
    agents = config.get("agents", {"provider": "codex"})
    if agents.get("provider", "codex") != "nvidia":
        return []
    result = [{"role": "generation", **agent_spec(config, "generation")}]
    result.extend({"role": f"review-{index}", **agent_spec(config, "review", index)} for index in range(1, len(agents.get("review_models", [])) + 1))
    return result


def _validate(value: object, schema: dict, path: str = "response") -> None:
    kind = schema.get("type")
    if kind == "object":
        if not isinstance(value, dict):
            raise ValueError(f"{path} must be an object")
        fields = schema.get("properties", {})
        missing = set(schema.get("required", [])) - set(value)
        if missing:
            raise ValueError(f"{path} missing: {', '.join(sorted(missing))}")
        if schema.get("additionalProperties") is False and set(value) - set(fields):
            raise ValueError(f"{path} has unexpected fields")
        for name, item in value.items():
            if name in fields:
                _validate(item, fields[name], f"{path}.{name}")
    elif kind == "array":
        if not isinstance(value, list):
            raise ValueError(f"{path} must be an array")
        for index, item in enumerate(value):
            _validate(item, schema.get("items", {}), f"{path}[{index}]")
    elif kind == "string" and not isinstance(value, str):
        raise ValueError(f"{path} must be a string")
    if "enum" in schema and value not in schema["enum"]:
        raise ValueError(f"{path} is outside its allowed values")


def _fetch_json(url: str, key: str, timeout: int, body: dict | None = None) -> tuple[int, dict]:
    headers = {"Authorization": f"Bearer {key}", "Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    payload = json.dumps(body).encode("utf-8") if body is not None else None
    http_request = request.Request(url, data=payload, headers=headers, method="POST" if body is not None else "GET")
    with request.urlopen(http_request, timeout=timeout) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def _completion(base_url: str, key: str, payload: dict, timeout: int) -> dict:
    deadline = time.monotonic() + timeout
    for attempt in range(3):
        try:
            status, result = _fetch_json(base_url + "/chat/completions", key, max(1, int(deadline - time.monotonic())), payload)
            if status == 202:
                request_id = result.get("requestId") or result.get("request_id")
                if not isinstance(request_id, str) or not request_id:
                    raise RuntimeError("NVIDIA returned 202 without a request ID")
                status_url = base_url + "/status/" + parse.quote(request_id, safe="")
                while time.monotonic() < deadline:
                    time.sleep(1)
                    status, result = _fetch_json(status_url, key, max(1, int(deadline - time.monotonic())))
                    if status != 202:
                        break
            if status != 200:
                raise RuntimeError(f"NVIDIA returned HTTP {status}")
            return result
        except error.HTTPError as exc:
            if exc.code not in {429, 500, 502, 503, 504} or attempt == 2:
                raise RuntimeError(f"NVIDIA returned HTTP {exc.code}") from exc
            time.sleep(min(2 ** attempt, max(0, deadline - time.monotonic())))
        except (error.URLError, TimeoutError) as exc:
            if attempt == 2:
                raise RuntimeError(f"NVIDIA transport failed: {type(exc).__name__}") from exc
            time.sleep(min(2 ** attempt, max(0, deadline - time.monotonic())))
    raise RuntimeError("NVIDIA request did not complete")


def call_nvidia(prompt: str, schema: dict, trace_dir: Path, timeout: int, spec: dict) -> dict:
    key = nvidia_api_key()
    trace_dir.mkdir(parents=True, exist_ok=True)
    (trace_dir / "prompt.txt").write_text(prompt, encoding="utf-8")
    (trace_dir / "schema.json").write_text(json.dumps(schema, indent=2) + "\n", encoding="utf-8")
    payload = {
        "model": spec["model"],
        "messages": [
            {"role": "system", "content": "Return one JSON object that matches the supplied schema. Do not include Markdown or commentary."},
            {"role": "user", "content": prompt + "\n\nOUTPUT JSON SCHEMA:\n" + json.dumps(schema)},
        ],
        "temperature": spec["temperature"],
        "max_tokens": spec["max_tokens"],
        "stream": False,
    }
    (trace_dir / "request.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    (trace_dir / "model.json").write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
    try:
        response = _completion(spec["base_url"], key, payload, timeout)
        (trace_dir / "api-response.json").write_text(json.dumps(response, indent=2) + "\n", encoding="utf-8")
        choice = response["choices"][0]
        if choice.get("finish_reason") == "length":
            raise RuntimeError("NVIDIA response was truncated")
        content = choice["message"]["content"]
        if not isinstance(content, str):
            raise RuntimeError("NVIDIA returned no text content")
        result = json.loads(content)
        _validate(result, schema)
        (trace_dir / "response.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        metadata = {"provider": "nvidia", "requested_model": spec["model"], "returned_model": response.get("model"), "response_id": response.get("id"), "finish_reason": choice.get("finish_reason"), "usage": response.get("usage")}
        (trace_dir / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
        return result
    except (KeyError, IndexError, TypeError, json.JSONDecodeError, ValueError, RuntimeError) as exc:
        (trace_dir / "error.txt").write_text(f"{type(exc).__name__}: {exc}\n", encoding="utf-8")
        raise RuntimeError(f"NVIDIA model {spec['model']} failed; see {trace_dir}") from exc


def call_agent(prompt: str, schema: dict, trace_dir: Path, timeout: int, spec: dict) -> dict:
    if spec["provider"] == "codex":
        return call_codex(prompt, schema, trace_dir, timeout)
    return call_nvidia(prompt, schema, trace_dir, timeout, spec)


def list_nvidia_models(base_url: str) -> list[str]:
    key = nvidia_api_key()
    try:
        _, data = _fetch_json(base_url.rstrip("/") + "/models", key, 30)
    except error.HTTPError as exc:
        raise RuntimeError(f"NVIDIA model listing returned HTTP {exc.code}") from exc
    return sorted(item["id"] for item in data.get("data", []) if isinstance(item, dict) and isinstance(item.get("id"), str))
