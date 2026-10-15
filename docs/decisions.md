# Design decisions

1. One synthetic benchmark and the same cases are used for every method. A representation mismatch is reported, not removed from the comparison.
2. The preliminary benchmark and reference judgments are agent-generated. No human annotation is assumed.
3. The final findings write-up is a required deliverable.
4. Z3 and clingo are the initial executable methods. Isabelle/HOL and nuXmv remain registered for the shared benchmark, with availability reported explicitly.
5. Abstract values and dispositions can be included as `unresolved` where no operationalization follows from the case. The report must name the interpretation that a binary judgment would require.
