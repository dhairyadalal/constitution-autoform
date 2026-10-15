# Synthetic constitution benchmark

The benchmark contains two original Meridian specifications. Each has a consistent version and a version with one designed contradiction. The documents are provisional. A prior development smoke run used the character pair before a repair to clause 11. Its saved candidates remain at `runs/v2-smoke-20261015`; the interactive analysis is in `reports/preliminary-results.html`. The repaired documents have not been rerun. Independent agent review and freezing are pending.

The setting, names, incidents, tools, and messages are synthetic. The document families draw on the structure of the [Claude Constitution](https://www.anthropic.com/constitution) and [OpenAI Model Spec](https://model-spec.openai.com/2026-08-18.html). They do not represent either organization's policy.

`environment.md` and `world.json` define the shared prose environment and public finite vocabulary. `constitutions/` holds the four natural-language documents. `cases/` holds five shared diagnostic cases. `authoring/design-model.json` records the intended rules and controlled mutations; it is withheld during generation. The cases are also withheld from formalizers. Missing case facts remain unknown.

The intended claims are artifact validity, coherence under the finite model, fidelity to the authoring design, and defensibility as a reading of the prose. A coherence proof applies to the encoded rules and stated world. It cannot establish that the prose has a unique interpretation. The inconsistent versions create a feasible state where a redacted alert is both required and forbidden. The five cases probe consequences of the rules; they are not a statistical compliance benchmark.
