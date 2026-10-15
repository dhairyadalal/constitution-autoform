# Reports

[Preliminary results](preliminary-results.html) is an interactive analysis of the frozen 64-candidate Codex run at `runs/preliminary-codex-parallel-20261015`. It includes source clauses, generated rules, native checker outputs, diagnostic case statuses, and agent review verdicts. The run used source commit `3f10fb9`.

Rebuild it from the saved evidence with `python reports/build_preliminary.py runs/preliminary-codex-parallel-20261015`. The builder checks source hashes and refuses an incomplete or non-frozen run. `preliminary-template.html` contains the presentation and analysis; `build_preliminary.py` supplies the saved data. `findings.md` in the run directory is the deterministic table report.

[Paper-style research report](constitution-study-paper.html) presents the same saved evidence as an introduction, methods, results, and discussion, with a pipeline diagram, interactive candidate comparisons, worked examples, and the full synthetic documents. It introduces the autoformalization question, states this preliminary study’s goals, and distinguishes observed translation failures from questions for later experiments. The existing preliminary explorer is retained.

Rebuild the paper with `python reports/build_paper.py runs/preliminary-codex-parallel-20261015`. `paper-template.html` holds its narrative and interaction code. `build_paper.py` reuses the original evidence builder and checks the additional reported case and review counts. The report explicitly records that due-phase labels affect case diagnosis but are ignored by the global conflict query.
