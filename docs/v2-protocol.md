# V2 executable protocol and current status

The v2 code path formalizes whole Meridian documents using one public finite vocabulary. The two consistent and two minimally mutated documents and five case narratives remain provisional. The authoring model is withheld from generation and used only after candidate creation. A provisional development smoke has now generated eight candidates for the character pair. Its reviewed findings are in `reports/v2-smoke-findings.md`; no frozen-run or final comparative finding is claimed.

## What the executable fragment means

A candidate is a list of source-traced norms. Each norm has force `O`, `F`, or explicit `P`, an action, a conjunction of positive and negative Boolean facts, a due phase, and optional explicit overrides. The candidate must quote an exact span from its source document. An omitted case fact is unknown, so a case status is determinate only if it holds in every completion that satisfies the public state constraints. An action can be required, forbidden, permitted, pending, conflicting, or unknown. `unknown` includes absence of a norm and variation across possible completions; the saved trace shows which rules may apply.

The coherence checker seeks a state satisfying the public invariant, an action's preconditions, and effective `O(a)` and `F(a)` together. It also checks whether each rule can activate, whether action effects preserve the invariant, and whether an explicit override suppresses a lower-priority rule. “Reachable” here means satisfiable in this finite state space. The environment can set exogenous case facts freely. There is no full transition system, real clock, or proof of natural-language consistency. The `next_decision` field exposes a pending duty but does not prove that the assistant eventually performs it.

The two document families are analyzed separately. The paired mutation tests whether a method preserves the redacted alert duty, the scoped identifying-disclosure restriction, and the added same-action prohibition. The five cases are diagnostic traces, not a sample for a compliance percentage. C03 has a follow-up phase for audit logging after a redacted alert.

## Method integrations

All methods receive the same whole document, environment, and public vocabulary. Their prompts differ only in target checker and direct versus structured extraction instructions. The generated output is a common rule representation. This is a controlled comparison of method-conditioned extraction and backend verification. It is not yet a comparison of independently written native SMT, FOL, ASP, and Isabelle theories. Native theories are compiled from each candidate's rules, and the common finite checker is retained as a parity reference.

| Method | Native artifact | Check performed |
|---|---|---|
| SMT | Finite Boolean Z3 model and witness | Conflict, nonvacuity, invariant-preserving effects, cases |
| FOL | Quantified predicates over states and enumerated actions in `theory.smt2` | Z3 asks whether a state and action jointly satisfy obligation and prohibition; compared with finite result |
| ASP | `theory.lp` with optional facts and derived norms | clingo searches for one conflict answer set; compared with finite result |
| Isabelle/HOL | `Candidate.thy` and `ROOT` | `isabelle build` checks a generated `no_reachable_conflict` theorem or a concrete `conflict_witness` theorem. Proof failure is recorded separately from a semantic conflict. |

The [Isabelle System Manual](https://isabelle.in.tum.de/library/Doc/System/Sessions.html) defines the session `ROOT` and batch `build` interface used here. The [PIDE MCP server](https://github.com/kappelmann/isabelle-pide-mcp) is useful for interactive proof-state exploration, but it manages a separate PIDE session and requires a matching Isabelle install. The batch interface gives saved theories, a repeatable exit status, and compiler logs for each experiment candidate. Set `ISABELLE_BIN` to a supported Isabelle executable, or put `isabelle` on `PATH`. If absent, the adapter writes the theory and reports `not_run`.

## Four outcomes

1. **Formal validity:** schema, exact source quote, and native checker status. An unavailable backend is `not_run`, not a failed formalization.
2. **Coherence:** bounded conflict witnesses, rule nonvacuity, and action-effect invariant checks for the candidate's own rules.
3. **Design fidelity:** exact matches, omitted intended core rules, and extra rules against the hidden authoring model. This is a strict structural diagnostic, not a graded semantic score.
4. **Natural-language defensibility:** three independent agent readings of each generated rule when `--reviews` is requested. Only unanimous complete votes produce a determinate verdict. Every vote, reason, alternative reading, and alleged omission is saved. These are agent interpretations, not human annotation or ground truth.

Case diagnostics are saved separately. They do not replace any of the four outcomes. The final report must state the actual run configuration and denominators, give results by document and method, then analyze omissions, wrong scopes, proof failures, and ambiguity with source text, generated rule or theory, checker result, case consequence, and interpretation limit. Include successful and failed examples. Do not claim a method comparison if Isabelle is `not_run` or if no candidates were generated.

## Commands and freeze gate

Install the Python package with `uv sync` or `pip install -e .`. Run `autoform-v2 check-design` to check the withheld authoring model in the four backends. It does not call an agent. Run `autoform-v2 review-benchmark --output runs/<review-dir>` to collect three independent agent readings of each document pair and the five cases without showing them the hidden model. Inspect the saved disagreements and repair any benchmark defects. Then run `autoform-v2 freeze --review-record runs/<review-dir>/review-record.json`. This records hashes for the four documents, five cases, public and hidden models, prompts, and configuration. Any change after freezing requires a new benchmark version. Then run `autoform-v2 run --output runs/<new-v2-run> --reviews`. The default configuration creates 4 documents × 4 target methods × 2 prompt modes × 2 repetitions, or 64 candidate calls, plus three review calls per valid candidate. The runner writes `findings.md` with setup, denominators, error categories, and source-to-rule examples; `autoform-v2 report --run runs/<new-v2-run>` regenerates it from saved evidence. Costs and elapsed time should be recorded from the saved call traces. `--allow-provisional` is reserved for a development smoke run and labels the manifest accordingly.

The Codex formalizer runs in a separate temporary working directory. Its prompt contains the source document and public world, with no cases or hidden model. Host filesystem read access is not a hard security boundary. This limitation is recorded in every run manifest. The v1 pilot and its results remain unchanged.
