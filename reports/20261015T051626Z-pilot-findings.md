# Diagnostic run: underspecified environment interface

The formalizers did not receive the exact event vocabulary or development examples. Several generated programs guessed field names, so the aggregate results below measure interface inference as well as formalization. Use the subsequent run with the revised interface for the preliminary method comparison.

## Research question
Which distinctions in one shared synthetic constitution benchmark survive formalization across methods?

## Method
The `20261015T051626Z-pilot` run evaluated 30 held-out cases across 6 bundles, with 3 repetitions and 3 independent agent reference votes per bundle. The reference judgments are independent agent votes, not human labels or ground truth. The results report executable validity separately from semantic agreement with those judgments.

## Findings
Executable coverage varied by method and prompt: clingo produced 9 executable candidates in both prompt modes; z3 produced 15 with decomposition and 14 with direct prompting, out of 18 candidates per condition. Among determinate outputs, agreement was 0/78 for clingo with decomposition, 6/78 for clingo direct, 28/78 for z3 with decomposition, and 30/78 for z3 direct. These pilot results do not establish that one formalism is generally superior.

Unresolved outputs remained common: 41 for clingo decomposition, 32 for clingo direct, 28 for z3 decomposition, and 24 for z3 direct. The reference itself was unresolved on 4 of 30 cases; 1 case had vote disagreement or a missing vote. The report also records unsupported requirements and malformed case facts among reasons for valid but unresolved outputs.

## Illustrative mismatches
For bundle `deletion`, case `deletion-1`, clingo with decomposition returned a runtime error caused by a syntax error in one candidate; another valid candidate returned unresolved because it formalized only R15. Both differ from the agent reference vote of `no` in different ways: the first is an execution failure, while the second executes but does not settle the case.

For bundle `deletion`, case `deletion-1`, z3 with decomposition returned `yes` despite the agent reference vote of `no`, with the stated reason that no breach was established. Another z3 decomposition candidate for the same bundle and case failed at runtime while accessing object data. These examples show that executable validity and semantic agreement are distinct outcomes.

## Limitations
The benchmark is small and synthetic, and shared model assumptions may affect both candidate generation and agent reference judgments. Candidate source needs qualitative inspection to confirm that the named solver carries the normative reasoning. Prompt-level separation does not prevent a local Codex process from reading other host files. Unintegrated methods were not run. The report does not specify which unsupported requirements account for each aggregate result.

## Next experiment
Expand the held-out cases and bundles, adjudicate unresolved and disagreeing agent votes, and record unsupported requirements per candidate. Then inspect candidate source to verify solver involvement before comparing semantic agreement across methods.
