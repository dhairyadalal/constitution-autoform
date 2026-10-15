"""NVIDIA provider integration with a local OpenAI-compatible HTTP stand-in."""

import io
import json
import os
import tempfile
import threading
import unittest
from contextlib import redirect_stdout
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import mock

from autoform import agents
from autoform.constitution import report, runner

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "toy-benchmark"
MODELS = [
    "nvidia/nemotron-3-super-120b-a12b",
    "nvidia/nemotron-3-ultra-550b-a55b",
    "google/gemma-4-31b-it",
    "openai/gpt-oss-20b",
]


class Handler(BaseHTTPRequestHandler):
    calls = []

    def log_message(self, *_args):
        pass

    def _send(self, status, data):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _authorized(self):
        return self.headers.get("Authorization") == "Bearer local-test-key"

    def do_GET(self):
        if not self._authorized():
            return self._send(401, {})
        if self.path == "/v1/models":
            return self._send(200, {"data": [{"id": model} for model in MODELS]})
        self._send(404, {})

    def do_POST(self):
        if not self._authorized():
            return self._send(401, {})
        payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        self.calls.append(payload["model"])
        prompt = payload["messages"][-1]["content"]
        schema = json.loads(prompt.split("OUTPUT JSON SCHEMA:\n", 1)[1])
        if payload["model"] == "bad-json":
            content = "{}"
        elif "rule_reviews" in schema["properties"]:
            rules = json.loads(prompt.split("PROPOSED RULES:\n", 1)[1].split("\n\nOUTPUT JSON SCHEMA:", 1)[0])
            content = json.dumps({"rule_reviews": [
                {"rule_id": rule["id"], "assessment": "supported", "reason": "Toy source matches.", "alternative_reading": ""}
                for rule in rules
            ], "material_omissions": []})
        else:
            rules = [{
                "id": "D01", "force": "O", "action": "send_alert",
                "all": ["incident", "channel_ready"], "not": [],
                "due": "current_decision", "source_clause": "4",
                "source_quote": "send a short alert", "overrides": [],
            }]
            if "Do not send a short alert without consent." in prompt:
                rules.append({
                    "id": "M_CHAR", "force": "F", "action": "send_alert",
                    "all": [], "not": ["consent"],
                    "due": "current_decision", "source_clause": "5",
                    "source_quote": "Do not send a short alert without consent.", "overrides": [],
                })
            content = json.dumps({"rules": rules, "assumptions": [], "unsupported_clauses": [], "decomposition": []})
        if payload["model"] == "fenced-json":
            content = "```json\n" + content + "\n```"
        self._send(200, {
            "id": "local-response", "model": payload["model"],
            "choices": [{"message": {"content": content}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 10},
        })


class NvidiaProviderIntegrationTest(unittest.TestCase):
    def test_key_from_env_file_model_listing_and_pipeline(self):
        Handler.calls = []
        try:
            server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        except PermissionError:
            self.skipTest("Loopback sockets are unavailable in this sandbox")
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory(prefix="autoform-nvidia-") as temporary:
                temp = Path(temporary)
                (temp / ".env").write_text("NVIDIA_API_KEY=local-test-key\n")
                base_url = f"http://127.0.0.1:{server.server_port}/v1"
                config = json.loads((ROOT / "tests" / "fixtures" / "toy-config.json").read_text())
                config["methods"] = ["smt"]
                config["agents"] = {
                    "provider": "nvidia", "base_url": base_url,
                    "generation": {"model": MODELS[0], "temperature": 1.0, "max_tokens": 2048},
                    "review_models": [
                        {"model": name, "temperature": 0.2, "max_tokens": 1024}
                        for name in MODELS[1:]
                    ],
                }
                config_path = temp / "config.json"
                config_path.write_text(json.dumps(config))
                run_dir = temp / "run"
                with mock.patch.object(agents, "ROOT", temp), mock.patch.object(runner, "BASE", FIXTURE), mock.patch.object(report, "BASE", FIXTURE), mock.patch.dict(os.environ, {"NVIDIA_API_KEY": ""}):
                    self.assertEqual(agents.list_nvidia_models(base_url), sorted(MODELS))
                    buffer = io.StringIO()
                    with redirect_stdout(buffer), mock.patch("sys.argv", ["autoform", "models", "--config", str(config_path)]):
                        runner.main()
                    self.assertIn("review-3", buffer.getvalue())
                    self.assertNotIn("not_listed", buffer.getvalue())
                    with redirect_stdout(io.StringIO()):
                        runner.run(config_path, run_dir, with_reviews=True, allow_provisional=True)
                    self.assertEqual(len(Handler.calls), 8)
                    manifest = (run_dir / "manifest.json").read_text()
                    self.assertNotIn("local-test-key", manifest)
                    for document in config["documents"]:
                        candidate_dir = run_dir / "candidates" / f"{document}__smt__direct__01"
                        assessment = json.loads((candidate_dir / "assessment.json").read_text())
                        self.assertEqual(assessment["validity"]["schema"], "valid")
                        self.assertEqual(assessment["validity"]["backend"]["status"], "checked")
                        self.assertEqual(
                            [entry["model"] for entry in assessment["natural_language_defensibility"]["model_assignments"]],
                            MODELS[1:],
                        )
                        trace = candidate_dir / "generation_call"
                        self.assertEqual(json.loads((trace / "metadata.json").read_text())["returned_model"], MODELS[0])
                        for name in ("request.json", "model.json", "api-response.json", "metadata.json"):
                            self.assertNotIn("local-test-key", (trace / name).read_text())
                    bad_spec = {"provider": "nvidia", "base_url": base_url, "model": "bad-json", "temperature": 0.2, "max_tokens": 64}
                    with self.assertRaisesRegex(RuntimeError, "failed"):
                        agents.call_nvidia("Toy prompt", runner.CANDIDATE_SCHEMA, temp / "bad-call", 10, bad_spec)
                    self.assertIn("missing", (temp / "bad-call" / "error.txt").read_text())
                    fenced_spec = {**bad_spec, "model": "fenced-json"}
                    fenced = agents.call_nvidia("Toy prompt", runner.CANDIDATE_SCHEMA, temp / "fenced-call", 10, fenced_spec)
                    self.assertTrue(fenced["rules"])
        finally:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()

    def test_missing_key_fails_before_a_request(self):
        with tempfile.TemporaryDirectory(prefix="autoform-empty-key-") as temporary:
            with mock.patch.object(agents, "ROOT", Path(temporary)), mock.patch.dict(os.environ, {"NVIDIA_API_KEY": ""}):
                with self.assertRaisesRegex(RuntimeError, "NVIDIA_API_KEY is missing"):
                    agents.nvidia_api_key()


if __name__ == "__main__":
    unittest.main()
