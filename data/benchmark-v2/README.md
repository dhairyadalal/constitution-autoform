# Synthetic specification benchmark v2: authoring draft

This is a new, provisional benchmark. The earlier workspace benchmark and its pilot results remain frozen. These files are for review before formalizer prompts, reference judgments, or experimental runs are created.

The setting is a fictional incident-analysis assistant called Meridian. All names, incidents, tools, and messages are synthetic. The two document families are original writing inspired by the *structure* of the [Claude Constitution](https://www.anthropic.com/constitution) and the [OpenAI Model Spec](https://model-spec.openai.com/2026-08-18.html); neither draft represents either organization's policy.

## Files and separation

- `environment.md` defines one shared world and action vocabulary.
- `authoring/design-model.json` is the withheld, machine-readable design model. It specifies the rules, the controlled contradiction, and provenance. It is an authoring oracle, not a formalizer input.
- `constitutions/` contains two consistent documents and their minimally changed inconsistent versions.
- `cases/` contains five shared use cases. The case author sees the natural-language drafts and environment but no generated formalization. Cases and documents are provisional until reviewed and frozen.

The formalizer should eventually receive the natural-language constitution and environment only. Cases are held out. The design model and mutation record are withheld. Prompt separation alone is not a hard filesystem boundary for a local agent, so a later run must enforce or explicitly disclose that limitation.

## Intended claims

The design model permits four distinct assessments: artifact validity, formal coherence, fidelity to the intended rule design, and defensibility as an interpretation of the prose. A proof of coherence applies to the encoded rules and stated finite world. It cannot prove that the natural-language document has only one reading.

The consistent versions have no direct obligation/prohibition pair on the same action under a jointly satisfiable guard in the design model. In the inconsistent versions, a single changed provision creates `O(send_redacted_alert)` and `F(send_redacted_alert)` when a verified severe incident has an authorized oversight channel but the user has not confirmed an alert. The `C05` case witnesses that conjunction. This is a normative contradiction; ordinary ambiguity and priority questions are recorded separately.

Do not treat five cases as a statistical compliance benchmark. They are diagnostic probes. Before a run, obtain independent agent reviews of the prose, the conflict witness, and the case facts, preserve disagreements, and record document hashes.
