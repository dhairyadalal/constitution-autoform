# Reports

[Preliminary results](preliminary-results.html) is an interactive analysis of the frozen 64-candidate Codex run at `runs/preliminary-codex-parallel-20261015`. It includes source clauses, generated rules, native checker outputs, diagnostic case statuses, and agent review verdicts. The run used source commit `3f10fb9`.

Rebuild it from the saved evidence with `python reports/build_preliminary.py runs/preliminary-codex-parallel-20261015`. The builder checks source hashes and refuses an incomplete or non-frozen run. `preliminary-template.html` contains the presentation and analysis; `build_preliminary.py` supplies the saved data. `findings.md` in the run directory is the deterministic table report.
