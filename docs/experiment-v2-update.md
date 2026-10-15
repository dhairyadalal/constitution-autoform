# Experiment v2: audit and required update

Status: v2 infrastructure implemented and authoring-model check passed in SMT, quantified FOL, ASP, and Isabelle/HOL. The benchmark still needs independent pre-freeze review, and no v2 candidate-generation experiment has run. The executable scope and commands are in `docs/v2-protocol.md`. This plan uses the four provisional Meridian documents and five cases in `data/benchmark-v2/`. The previous 72-artifact pilot remains a separate engineering pilot.

## Research question

Can an automated formalization of a natural-language constitution preserve its requirements and relationships well enough to establish useful, source-traceable properties? The controlled test is whether a method distinguishes a consistent document from a minimally edited document with a reachable, unresolved obligation/prohibition conflict, while preserving the safeguards that make the consistent document useful.

The unit of analysis is the complete document and its generated representation. The five cases are diagnostic probes, not independent samples for a compliance-rate estimate. The Anthropic-inspired and OpenAI-inspired families differ in writing and authority structure, but both use the same simulated environment and conflict pattern. Results must be reported within each family before making any cross-family comparison.

## What the previous audit changes

| Prior failure or current draft limitation | Required v2 change |
|---|---|
| Sparse, isolated requirements made semantic interpretation trivial or arbitrary. | Formalize each 840–950-word document as a whole. Require source links for every represented provision and relationship. Preserve the version-pair diff. |
| A worked prompt example copied the evaluated R05 rule. | Use syntax examples from an unrelated toy domain and no benchmark clause or case wording. Inspect prompts for leakage before freezing. |
| The old adapter reduced obligations to `violation` and treated absence of a violation as compliance. | Define explicit states for required, forbidden, permitted, pending, conflicting, and unknown. Preserve temporal and missing-fact assumptions in the artifact. |
| A 2:1 agent vote became a determinate reference despite the written policy. | Keep every vote. Use only unanimous determinate judgments for primary case comparison; analyze disputed readings separately. Do not call agent consensus semantic ground truth. |
| Unsupported requirements were counted as valid unresolved outputs. | Report parse/check validity, requirement coverage, and case abstention separately. An artifact can be executable but incomplete. |
| Z3 and clingo fact encoders gave missing facts different meanings. | Fix one environment interpretation for all methods and state each adapter's realization of it. Record any unsupported feature as a method limitation. |
| Isabelle and a distinct FOL representation were absent. | Implement and verify those adapters before the main comparison or explicitly narrow the registered study. FOL may use Z3 as a checker, but its representation fragment must be specified separately from SMT. Isabelle must compile and check generated theories. |
| The old write-up lacked source-to-formalization examples. | For each substantive finding, show source provision, generated expression/rule, formal witness or proof result, case consequence, and interpretation limit. Include both success and failure. |
| Current v2 checker finds only direct `O(a)`/`F(a)` pairs with jointly satisfiable Boolean guards. | Define reachable states, action effects, deadlines, priorities, and an explicit conflict policy. Check non-vacuity and intended safeguard coverage. Describe any remaining checks by their exact scope. |
| Current case C05 is titled “Conflict witness” and asks whether the provisions conflict. | Replace that title and leading question in formalizer-facing or judge-facing material with neutral wording. Keep the witness designation only in withheld authoring metadata. |

## Benchmark preparation before freeze

1. Review the two document families for naturalness, scope, and whether the single changed clause really introduces the only *intended* contradiction. Treat competing plausible readings as data. The authoring design model is an intended interpretation, not a proof of unique prose meaning.
2. Complete the hidden executable design model. Define the state and action vocabulary, feasibility constraints, rule activation, norm force, authority, priorities, and how an action satisfies or breaches a duty. Check the consistent versions for reachable direct conflicts and the inconsistent versions for a concrete witness. Check that baseline safeguards are satisfiable rather than proved only by dropping a rule.
3. Review all five scenarios independently of generated artifacts. Give each a neutral title, a fixed fact record, and an action query. Keep an easy case, two medium cases, and two hard cases. Preserve missing facts as unknown. Include permitted actions so a blanket prohibition is visible.
4. Freeze source documents, design model, cases, environment, prompts, and review records with hashes. Generation receives only the natural-language document, common environment, and unrelated interface examples. Held-out cases and the hidden model remain unavailable in the prompt. Host-level isolation should be enforced if possible; otherwise disclose prompt-level separation only.

## Experimental conditions

Use the same four documents and five cases for every method. Generate multiple independent candidates for each document, method, and prompt condition. Keep a direct translation condition and a structured extraction condition. Add solver-feedback repair only as a separately costed condition, with feedback limited to compilation and proof diagnostics and no held-out answers.

At minimum, compare a constraint/SMT representation, an explicitly restricted first-order representation, ASP, and Isabelle/HOL once each has a working adapter. Record each formalism's semantics and unsupported constructs. Hold model, prompts apart from syntax instructions, generation budget, and checker time budget as comparable as practical. Do not rank formalisms from five cases or conflate solver choice with representation quality.

## Four outcomes, reported separately

1. **Formal validity:** Does the artifact parse, type-check or ground, and execute the intended checks? Record errors and repair cost.
2. **Coherence:** Does the artifact have reachable incompatible obligations or prohibitions, or violate stated priorities? Report a minimal witness, a proof under bounded assumptions, or `unknown`. Also test non-vacuity and whether a permitted route remains available.
3. **Design fidelity:** Does the artifact preserve the hidden model's provisions, guards, exceptions, authority relations, and engineered mutation? Count omissions, additions, and weakened safeguards separately. Detecting “no conflict” by dropping the alert duty is a failure.
4. **Natural-language defensibility:** Independent agents judge whether each formal commitment is supported by source spans and whether a plausible alternative reading changes the result. Preserve disagreement and confidence reasons. No human annotation is claimed for this preliminary run.

Case outcomes explain mechanisms. A case record should identify the applicable clauses, proposed action, predicted status, checker trace, and agent interpretation. It should not collapse a conflict into a yes/no compliance label. Report per-document outcomes and a qualitative cross-method comparison; five cases do not warrant broad accuracy percentages.

## Report structure and completion gate

The final report must give the experimental setup and actual run, quantitative results with denominators, then error analysis grounded in illustrative formalizations that succeeded and failed. It must distinguish malformed artifacts, missing requirements, wrong semantics, spurious conflicts, missed conflicts, and genuine source ambiguity. It must state what each formal guarantee assumes and which conclusions remain agent interpretations.

Do not start the main run until the v2 benchmark is frozen, the checker semantics are documented, all claimed method integrations execute a small neutral example, and the scoring/reporting pipeline keeps the four outcomes separate. If a method is unavailable, report `not run` and narrow the comparison rather than imputing failure.
