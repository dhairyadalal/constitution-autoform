# Preliminary findings: declarative autoformalization of a synthetic constitution

## Research question and design

The pilot tests which distinctions in one synthetic constitution survive declarative autoformalization. Holding the requirements and cases fixed makes failures comparable across target methods and prompting procedures. Six bundles draw on a 16-statement inventory spanning the 14 provisional categories; two unlabeled development histories per bundle show the input interface, and 30 held-out histories test the generated artifacts. Broad goals, values, and dispositions remain exploratory because these histories do not establish their satisfaction conditions. This scope exposes failures in executable rules without treating the category inventory as a settled ontology. The [manifest](evidence/declarative-pilot/manifest.json) records the frozen inputs and run settings.

Codex produced 72 declarative artifacts: Z3 expressions or clingo rules, under direct and decomposition prompts, with three fresh generations per bundle and condition. The fixed adapters translated the same case JSON into solver facts and asked whether the target rule was violated or explicitly permitted the observed action. Three separate Codex judgments per bundle supplied the preliminary reference; their prompts contained no generated artifacts. All generation and judging calls used `gpt-6-luna` at medium reasoning effort. The [reference votes](evidence/declarative-pilot/reference.json), [case results](evidence/declarative-pilot/results.json), and [artifact archive](evidence/declarative-pilot/artifacts-and-votes.zip) preserve the evidence needed to inspect each judgment and encoding.

## Results

Executable validity is the dominant bottleneck. A candidate counts as fully executable only if it returns a valid judgment on every held-out case in its bundle. The table also shows correct judgments over all determinate case evaluations, counting invalid and unresolved candidate outputs as incorrect. Each condition has 18 candidates and 78 determinate case evaluations, because four of the 30 reference cases were unresolved and each bundle was generated three times.

| Method | Prompt | Fully executable | Correct / determinate | Valid determinate outputs |
|---|---|---:|---:|---:|
| Z3 | Direct | 4/18 | 21/78 | 28/78 |
| Z3 | Decomposition | 6/18 | 23/78 | 29/78 |
| clingo | Direct | 5/18 | 19/78 | 25/78 |
| clingo | Decomposition | 4/18 | 16/78 | 18/78 |

The main change occurs across requirement structures, not consistently between methods. All 12 sharing artifacts executed on every case, and 47 of their 48 determinate outputs matched the agent reference. Across the other five bundles, only 7 of 60 artifacts executed on every case. In `revocation-3`, 11 of 12 artifacts failed during execution; in `remedy-2`, all 12 failed. These counts support a narrower conclusion than a ranking of formalisms: this generation setup is brittle on interacting and temporally ordered rules. The current bundles vary in several ways at once, so the data do not isolate which source of complexity causes that drop.

Compilation failures and semantic failures are distinct. Many clingo artifacts contain unsafe variables in rules for active approval or intervening events. Many Z3 artifacts contain malformed quantified expressions, incorrect `not` arity, or unmatched parentheses. On `deletion-1`, which prohibits deletion under a legal hold, nine of 12 artifacts failed to execute, two returned the reference judgment `no`, and one returned `unresolved`. On `preservation-2`, which requires saving a version despite an owner's discard request under legal hold, seven failed, three abstained, one agreed, and one disagreed. The first repair experiment should therefore use compiler and grounding feedback without exposing held-out judgments; otherwise a change in semantic score will be dominated by artifacts that never reached semantic evaluation.

Decomposition did not yield a consistent gain. It increased fully executable Z3 artifacts from four to six and correct Z3 judgments from 21 to 23, while decreasing fully executable clingo artifacts from five to four and correct clingo judgments from 19 to 16. There are only three generations per bundle and prompt condition. A prompt effect cannot be separated from sampling variation or backend-specific syntax difficulty on this evidence.

## Interpretation limits

The reference is an agent interpretation, not semantic ground truth. Four cases received unresolved reference judgments. The judges split two to one on `deletion-3`, which asks whether a non-owner approval event itself breaches an authority rule; its majority answer was `yes` in this run and `no` in the [earlier run's votes](evidence/declarative-pilot/prior-python-run-reference.json). That flip shows the risk of treating a majority label as uniquely intended. Excluding contested cases or reporting alternative readings is necessary before making a semantic fidelity claim.

The methods share cases, yet their fact encoders have different underlying semantics for missing information. Z3 leaves omitted facts unconstrained, while clingo uses alternative answer sets for missing recipient status, sensitivity, and legal hold. The comparison therefore concerns these specified representation and verification workflows. Isabelle/HOL and nuXmv have no executable integration in this pilot, so this run contains no results for them. The candidate and judge calls used the same model family, which may also create correlated interpretation errors.

## Next experiment

Keep this benchmark fixed and give each failed artifact up to two rounds of syntax or grounding feedback from its own solver. Record whether repair makes it executable, then score the repaired artifact on the same held-out histories without revealing their agent judgments. Use only unanimous agent labels for the primary semantic score and report disputed cases separately. This tests whether the observed bottleneck is mainly generation of valid solver syntax or preservation of the constitutional distinctions once an artifact runs.
