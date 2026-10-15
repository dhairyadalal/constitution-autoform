# Authoring trace and review criteria

This file is withheld from formalizers. It records intended design properties, not human annotations or a claim that the prose has a unique interpretation.

| Design rule | Character document | Authority document | Diagnostic case |
|---|---|---|---|
| D01: verified severe incident + authorized available channel entails `O(send_redacted_alert)` | Clause 4 | Clause 6 | C03, C05 |
| D02: identifiers without specific user confirmation entail `F(send_identifying_alert)` | Clause 3 | Clause 7 | C03 |
| D03: requested summary entails `O(provide_careful_summary)` | Clause 1 | Clause 4 | C01, C04, C05 |
| D04: uncertain evidence entails `F(assert_unverified_as_fact)` | Clause 2 | Clause 5 | C01 |
| D05 and D06: irreversible requested export without confirmation entails `F(execute_export)` and `O(ask_export_confirmation)` | Clause 5 | Clause 8 | C02 |
| D07: external action entails `O(record_external_action)` | Clause 8 | Clause 10 | C03, C05 |
| M_CHAR: unconfirmed alert entails `F(send_redacted_alert)` even for a verified severe incident | Inconsistent clause 5 only | n/a | C05 |
| M_AUTH: unconfirmed alert entails `F(send_redacted_alert)` even for a verified severe incident | n/a | Inconsistent clause 7 only | C05 |

In each consistent document, C05 activates D01 and no rule forbids the redacted alert. In each inconsistent document, C05 activates D01 and its family-specific mutation. No provision assigns one of those two clauses precedence over the other. The conflict is on the *same action*, not merely on sharing information in two different forms. C03 includes user confirmation for the redacted alert so it can distinguish the identifying-disclosure boundary from the controlled conflict.

## Independent agent review, before freeze

1. Read each document without the design model. Extract its provisions, cross-references, priority claims, and any plausible competing readings. Record source spans and uncertainty.
2. Compare each version pair. Verify that the only substantive change is the recorded clause mutation. Flag any unintended change in force, scope, or authority.
3. Given the shared environment, seek a reachable `O(a)` and `F(a)` pair in each document. Record a witness or the limits of a failure to find one. Agent failure to find a conflict is not a proof of consistency.
4. Read all five cases without generated artifacts. Check that every decisive fact is explicit, that the proposed actions are possible in the simulated world, and that C05 activates the intended conflict. Preserve disagreements.
5. After review, freeze the documents and cases with hashes before formalization. Formalizers see the prose and environment; independent evaluators may use the design model after generation is complete. Never pass the mutation record or expected outcomes in a candidate prompt.

The later formal proof should check satisfiable triggering conditions, direct norm conflicts, and whether a formalizer's representation omitted a relevant rule. A proof about a generated encoding does not establish fidelity to the prose. The agent review addresses defensible readings but does not become human annotation or semantic ground truth.
