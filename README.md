# Autoformalization of synthetic AI constitutions

This repository compares how four method-conditioned formalizers represent the same natural-language specifications. The benchmark has two original Meridian document families, a consistent and inconsistent version of each, five shared diagnostic cases, and a hidden authoring model. The documents are provisional. The [protocol](docs/protocol.md) defines the claims and limits of the experiment.

The active workflow is under `src/autoform/constitution/`, `data/benchmark/`, `configs/`, and `prompts/`. The CLI command is `autoform`. The earlier pilot data and code have been removed from this checkout. Git history retains them.

Install with `uv sync` or `pip install -e .`. The default configuration pins authenticated Codex CLI calls to `gpt-6-luna` with medium reasoning for generation and three separate review calls. The NVIDIA adapter remains optional in `configs/nvidia.json`; it reads `NVIDIA_API_KEY` from the ignored `.env` file. Initial full-document NVIDIA reviews were slow or malformed, so that provider is not the current experiment default.

Set `ISABELLE_BIN` or put `isabelle` on `PATH` to run the Isabelle checker. Then:

```sh
autoform check-design
autoform review-benchmark --config configs/preliminary.json --output runs/benchmark-review
autoform freeze --config configs/preliminary.json --review-record runs/benchmark-review/review-record.json
autoform run --config configs/preliminary.json --output runs/preliminary-<date> --reviews
```

Run a small provisional slice before the full experiment to inspect JSON validity, source fidelity, latency, and any agent errors. The model calls are single-turn structured requests. To try the optional NVIDIA configuration, use `autoform models --config configs/nvidia.json` and pass that configuration explicitly to the other commands.

Review the independent agent readings before freezing. The default run makes 64 candidate calls across four documents, four backends, two prompt modes, and two repetitions, plus three agent reviews per valid candidate. `autoform report --run runs/<run>` generates a deterministic Markdown analysis for a run whose source hashes match the current checkout. For a repeatable end-to-end check, run `uv run python -m unittest discover -s tests -v`. The tests use a small toy constitution with local Codex and HTTP stand-ins, so they make no hosted model calls. SMT, FOL, and ASP run normally. Isabelle runs if its executable is available; otherwise the test checks the recorded `not_run` status and generated theory.

The [interactive preliminary analysis](reports/preliminary-results.html) examines eight candidates from the pre-repair character documents at commit `8c26cc8`. The saved run is `runs/v2-smoke-20261015`. Clause 11 has since been repaired in both character documents. Those results do not evaluate the current drafts. No frozen comparison has been run.
