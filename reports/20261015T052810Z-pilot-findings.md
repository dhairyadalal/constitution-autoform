## Research question
Which distinctions in one shared synthetic constitution benchmark survive formalization across methods?

## Method
The pilot used 30 held-out cases across 6 bundles, with 3 repetitions and 3 independent agent reference votes per bundle. The reference is an agent-constructed interpretation, not human labels or ground truth. Solver execution checks whether generated artifacts run and whether their outputs agree with that reference. The report therefore separates executable validity from semantic agreement. Across 18 candidates per method and prompt setting, valid execution ranged from 5/18 (clingo direct) to 18/18 (Z3 decompose). Correct determinate outputs ranged from 9/78 to 69/78, with denominators reflecting case-repetition evaluations.

## Findings
Executable validity did not ensure semantic agreement: valid artifacts could still return unresolved or disagree with agent votes. Z3 decompose had the highest reported correct/determinate count (69/78), while clingo outputs included many invalid case outputs (58 for decompose, 65 for direct). This pilot does not establish that one formalism is generally superior. Four of 30 cases had unresolved reference judgments; two involved vote disagreement or a missing vote. Some requirements were unsupported by an independent action or breach condition, leaving their outcomes unresolved.

## Illustrative mismatches
For `deletion/deletion-1`, clingo decompose produced a runtime error from unsafe variables; another valid clingo decompose candidate returned unresolved because the bundle lacked an independent action condition. For `deletion/deletion-2`, a valid clingo decompose candidate returned yes against the agent reference no, reasoning that each recorded deletion had active owner approval and no legal hold. For `deletion/deletion-1`, Z3 decompose returned unresolved because the cited requirement defined or prioritized deletion rules without itself supplying a prohibition or permission condition.

## Limitations
The benchmark is small and synthetic. Agent reference judgments may share assumptions with candidate generation and evaluation. Candidate source needs qualitative inspection to establish that the named solver carries the normative reasoning. Prompt-level separation does not prevent a local Codex process from reading other host files. Unintegrated methods were not run.

## Next experiment
Expand the benchmark with more bundles and cases, resolve or explicitly adjudicate the uncertain agent votes, and add independent action or breach conditions where requirements currently lack them. Then inspect candidate source and rerun execution and semantic-agreement evaluation, reporting the two separately.
