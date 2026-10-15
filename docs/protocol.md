# Pilot protocol

## Research question

On one shared set of synthetic requirements and histories, which semantic distinctions do the tested formalization methods preserve, lose, or add? We compare the resulting representations, including explicit unsupported cases and mismatches. A compiler success or solver result establishes behavior of the artifact, not fidelity to the prose.

## Data

The candidate categories in the requirements analysis are coverage targets, not settled ontology primitives. The preliminary set has one or two synthetic examples for every category and six small bundles with observable interactions. The exact same bundles and cases are offered to every method. Requirements and case histories contain no evaluator labels. Agent authorship and version hashes are recorded.

## Agent roles and separation

The formalizer receives a bundle, environment semantics, the target method, and two unlabeled development histories from that same bundle to demonstrate the fixed JSON interface. The judge receives the bundle, environment semantics, and held-out cases, but no candidate code or method name. Three independent judge calls vote on each bundle. Majority agreement is the preliminary reference; disagreement or a majority `unresolved` result remains `unresolved` in scoring. Stage ordering means reference votes are generated after candidate formalizations. Prompt-level separation is not a hard host filesystem boundary.

## Methods

Z3 and clingo are the first executable integrations. Both must return `compliant`, `violation`, or `unresolved` for a case. The generated source must actually use its named solver to decide, and the report retains source for inspection. Isabelle/HOL and nuXmv use the same benchmark when integrated; their absence in a run is `not_run`, not failure. The direct and decomposition prompts each use the same input. A later feedback condition must be analyzed separately because it uses additional computation.

## Evaluation

Save every generated artifact, parse error, execution error, timeout, solver result, agent vote, and declared assumption. For each candidate, report executable validity, number of determinate reference cases, correct judgments, false acceptance, false rejection, unresolved output, and unsupported cases. Invalid candidates score zero on all determinate cases in the overall metric; conditional accuracy is also reported. Histories within a bundle are related observations, so compare methods by bundle and run, not by treating every case as an independent sample. Include concrete error traces and alternative plausible readings in the final write-up.

## Freeze and completion

The runner hashes dataset files, prompts, config, and environment documentation into the run manifest. A completed pilot has saved candidate source, three reference votes per bundle, executable results for installed methods, a discrepancy analysis, and a clean report with research question, procedure, findings, and limitations.
