# Design decisions

1. One synthetic benchmark and the same cases are used for every method. A representation mismatch is reported, not removed from the comparison.
2. The preliminary benchmark and reference judgments are agent-generated. No human annotation is assumed.
3. The final findings write-up is a required deliverable.
4. Z3 and clingo are the initial executable methods. Isabelle/HOL and nuXmv remain registered for the shared benchmark, with availability reported explicitly.
5. Abstract values and dispositions can be included as `unresolved` where no operationalization follows from the case. The report must name the interpretation that a binary judgment would require.
6. The first full run showed that a broad environment description leaves the action vocabulary and JSON structure underspecified for generated candidates. The revised interface states exact fields and event names and provides two unlabeled development histories per bundle. The earlier run remains saved with its file hashes as a diagnostic version.
7. Source inspection of the revised Python run found candidates that decide normative conditions in Python and use Z3 only to check the resulting Boolean. A declarative artifact mode now supplies case facts through fixed adapters and requires SMT expressions or ASP rules. The Python run remains a workflow baseline, not a clean comparison of representation methods.
