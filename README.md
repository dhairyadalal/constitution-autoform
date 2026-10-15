# Autoformalizing synthetic AI constitutions

This repository asks whether an agent can translate a natural-language AI constitution into rules that preserve its requirements and expose its internal conflicts. The preliminary study uses two synthetic document families. Each has a coherent version and a version with one designed contradiction. The same five diagnostic cases are applied to every candidate formalization. See the [experiment protocol](docs/protocol.md) for the evaluation claims and their limits.

The formalizer produces a shared, source-traced rule representation under four target conditions: SMT, FOL, ASP, and Isabelle/HOL. Each candidate is compiled to its target backend for checking. This compares method-conditioned extraction and verification, not four independently authored native theories.

## Get the repository and benchmark

```sh
git clone https://github.com/dhairyadalal/constitution-autoform.git
cd constitution-autoform
```

The synthetic requirements are tracked in Git, so cloning the repository downloads them. There is no separate benchmark download. Start with [the benchmark guide](data/benchmark/README.md), then read the four natural-language documents in [`data/benchmark/constitutions/`](data/benchmark/constitutions/):

| Family | Coherent version | Designed-conflict version |
| --- | --- | --- |
| Character-oriented | [`character-consistent.md`](data/benchmark/constitutions/character-consistent.md) | [`character-inconsistent.md`](data/benchmark/constitutions/character-inconsistent.md) |
| Authority-oriented | [`authority-consistent.md`](data/benchmark/constitutions/authority-consistent.md) | [`authority-inconsistent.md`](data/benchmark/constitutions/authority-inconsistent.md) |

Here **character-oriented** means that requirements are framed as Meridian's standing commitments in the situations that motivate them. For example, “Support legitimate oversight” states the redacted-alert duty, while “Protect people named in records” and “Take the user's control seriously” explain related privacy and confirmation constraints. **Authority-oriented** means that the text first defines the user and operator roles and the scope of their instructions, then gives action-specific rules. Its “Severe-incident notification” and “Identifying disclosure” clauses separate the alert duty from disclosure restrictions. These labels describe how the rules are presented. Both families use the same designed rule core and the same fictional assistant.

The documents are original synthetic specifications, not copies of the public constitutions that inspired their styles. [`environment.md`](data/benchmark/environment.md) explains Meridian's setting, and [`world.json`](data/benchmark/world.json) defines the public facts, actions, and constraints available to the formalizer. [`shared-cases.md`](data/benchmark/cases/shared-cases.md) presents the five use cases in prose; [`cases.json`](data/benchmark/cases/cases.json) provides their machine-readable facts and queries.

[`authoring/design-model.json`](data/benchmark/authoring/design-model.json) records the intended rules and mutations. It is used for evaluation, not included in the formalizer prompt. The cases are also withheld from that prompt. The local Codex CLI can read files, so this prompt boundary is not hard isolation. The [freeze record](data/benchmark/freeze.json) pins the reviewed benchmark, prompts, and experiment configuration by hash. Do not edit those inputs in place for a new study.

## Set up the software

You need Python 3.10 or later, [uv](https://docs.astral.sh/uv/getting-started/installation/) or pip, and an installed, authenticated `codex` CLI for the default agent configuration. [`pyproject.toml`](pyproject.toml) and [`uv.lock`](uv.lock) specify the Python dependencies, including Z3 and clingo. For all four native checks, install [Isabelle](https://isabelle.in.tum.de/) and put `isabelle` on `PATH`, or set `ISABELLE_BIN` to its executable. Without Isabelle, its adapter still saves a theory but records the native check as `not_run`.

```sh
uv sync --locked
uv run autoform --help
```

If you use pip instead of uv:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
autoform --help
```

The default [`configs/preliminary.json`](configs/preliminary.json) pins the Codex model and reasoning setting, four documents, four backends, two prompt modes, two repetitions, and three separate agent reviews per valid candidate. An optional NVIDIA provider is configured in [`configs/nvidia.json`](configs/nvidia.json). It reads `NVIDIA_API_KEY` from the environment or the ignored repository `.env` file. That configuration is separate from the frozen preliminary experiment and cannot be substituted into it without a new freeze.

## Find the code, evidence, and reports

| Path | What it contains |
| --- | --- |
| [`docs/protocol.md`](docs/protocol.md) | Experimental claims, checker semantics, and interpretation limits |
| [`data/benchmark/`](data/benchmark/) | Natural-language requirements, public world, use cases, hidden design model, and freeze record |
| [`configs/`](configs/) and [`prompts/`](prompts/) | Agent settings and generation/review instructions |
| [`src/autoform/constitution/`](src/autoform/constitution/) | Runner, assessment, four backend adapters, and deterministic report generator |
| [`tests/`](tests/) | Toy pipeline integration tests that use local model stand-ins |
| [`reports/`](reports/) | Shareable HTML analyses, templates, and builders for the completed preliminary run |
| `runs/` | Local run artifacts: manifests, prompts, responses, candidate rules, native theories, checks, and review votes |

The main result is the [paper-style interactive report](reports/constitution-study-paper.html). The [preliminary evidence explorer](reports/preliminary-results.html) provides another view of the same run. Both HTML files embed the data needed for their charts and interactive comparisons. The completed preliminary run generated 64 candidates, of which 63 completed valid native checks. The paper explains the substantive finding: valid checks can miss a designed conflict when translation drops the requirement that creates it.

`runs/` is ignored by Git because the raw traces are large. **A clone includes the benchmark and HTML reports, but not the raw preliminary run directory.** The report's links to individual local trace files work only when that run directory is present. This repository does not provide a download for the raw preliminary run artifacts. The HTML builders in `reports/` are tied to that saved run and cannot reconstruct its traces from the HTML alone.

## Run the frozen experiment

From the repository root, first check that the designed rules behave as intended in the available backends. This command makes no agent calls:

```sh
uv run autoform check-design --output runs/design-check
```

Then generate and assess the candidates with the pinned configuration. This makes hosted model calls through the authenticated Codex CLI. `--reviews` requests three separate agent readings of each valid candidate; those readings are not human annotation or semantic ground truth.

```sh
uv run autoform run \
  --config configs/preliminary.json \
  --output runs/my-preliminary-run \
  --reviews \
  --workers 4
```

The run writes `manifest.json`, one directory per candidate under `candidates/`, and a deterministic `findings.md`. Each candidate directory saves its rule JSON, assessment, native backend output, case diagnostics, and model traces. The manifest records input hashes and configuration. To regenerate the text report from a saved run whose source files still match the checkout:

```sh
uv run autoform report --run runs/my-preliminary-run
```

Reusing the same output directory resumes saved candidates; use a new directory for an independent repetition. The full default matrix contains 4 documents × 4 target methods × 2 prompt modes × 2 repetitions = 64 candidate calls, plus reviews. Read the [protocol](docs/protocol.md) before interpreting case matches or backend checks as evidence of semantic fidelity.

## Extend the study

To repeat the **same frozen protocol**, keep the inputs and `configs/preliminary.json` unchanged and choose a fresh run directory. To vary the documents, prompts, model, methods, or other configuration, create a new benchmark version first. The current runner fixes the benchmark location and the four document identifiers in [`runner.py`](src/autoform/constitution/runner.py); it does not yet accept an arbitrary benchmark path from the CLI. A new document set therefore requires updating those bindings and any report logic that assumes the current families.

For a new version, copy the benchmark into a new versioned directory, change the runner's benchmark path, update the documents and public world, and record the intended rules and controlled mutations in the new authoring model. Keep the five-case design or replace it explicitly for that version. Give the formalizer only the document, environment, and public vocabulary. Review the new benchmark with independent agent calls, inspect disagreements, and then freeze its source hashes before running candidates. The relevant commands are `autoform review-benchmark`, `autoform freeze`, and `autoform run`; use `uv run autoform <command> --help` for their options. Preserve each version's configuration, prompts, model metadata, responses, and errors with its run. Do not feed hidden design rules or case labels into generation.

For a local pipeline check without hosted model calls, run the toy integration tests:

```sh
uv run python -m unittest discover -s tests -v
```
