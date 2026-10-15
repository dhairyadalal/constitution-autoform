# Autoformalization of synthetic AI constitutions

This repository compares how four method-conditioned formalizers represent the same natural-language specifications. The benchmark has two original Meridian document families, a consistent and inconsistent version of each, five shared diagnostic cases, and a hidden authoring model. The documents are provisional. The [protocol](docs/protocol.md) defines the claims and limits of the experiment.

The active workflow is under `src/autoform/constitution/`, `data/benchmark/`, `configs/`, and `prompts/`. The CLI command is `autoform`. The earlier pilot data and code have been removed from this checkout. Git history retains them.

Install with `uv sync` or `pip install -e .`. Put your NVIDIA API key in the ignored `.env` file as `NVIDIA_API_KEY=...`. The tracked `.env.example` shows the format. The default configuration uses [Nemotron 3 Super](https://docs.api.nvidia.com/nim/reference/nvidia-nemotron-3-super-120b-a12b-infer) for generation and GLM-5.3, Gemma 4 31B, and GPT OSS 20B for three review votes. All four IDs were listed for the configured key and returned schema-valid JSON in a minimal live probe on 2026-10-15. This checks basic endpoint access, not performance on the benchmark. Edit `configs/preliminary.json` to change them. The key is never written to run traces.

Set `ISABELLE_BIN` or put `isabelle` on `PATH` to run the Isabelle checker. Then:

```sh
autoform models --config configs/preliminary.json
autoform check-design
autoform review-benchmark --config configs/preliminary.json --output runs/benchmark-review
autoform freeze --config configs/preliminary.json --review-record runs/benchmark-review/review-record.json
autoform run --config configs/preliminary.json --output runs/preliminary-<date> --reviews
```

`autoform models` checks whether the configured IDs appear in NVIDIA's current catalog. Catalog presence does not establish inference access. Run a small provisional slice before the full experiment to inspect JSON validity, source fidelity, latency, and any API errors. The model calls are single-turn structured requests; no tool-using agent loop is involved. To retain the local Codex CLI path, set `agents.provider` to `codex` in a separate configuration file.

Review the independent agent readings before freezing. The default run makes 64 candidate calls across four documents, four backends, two prompt modes, and two repetitions, plus three agent reviews per valid candidate. `autoform report --run runs/<run>` generates a deterministic Markdown analysis for a run whose source hashes match the current checkout. For a repeatable end-to-end check, run `uv run python -m unittest discover -s tests -v`. The tests use a small toy constitution with local Codex and HTTP stand-ins, so they make no hosted model calls. SMT, FOL, and ASP run normally. Isabelle runs if its executable is available; otherwise the test checks the recorded `not_run` status and generated theory.

The [interactive preliminary analysis](reports/preliminary-results.html) examines eight candidates from the pre-repair character documents at commit `8c26cc8`. The saved run is `runs/v2-smoke-20261015`. Clause 11 has since been repaired in both character documents. Those results do not evaluate the current drafts. No frozen comparison has been run.
