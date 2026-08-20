# Raw results

This directory is immutable archival evidence selected by the reconciliation
allow-list. `rq1_rq2/expN/seedS/archive/` retains the effective configuration,
all generation dumps (candidate/formula/fitness/verdict), all ARFF training data,
raw J48 output/models, cache database, stopping checks, inference state, reports,
run log, and scheduler metadata that exist for the selected run. The 340-row
`EVIDENCE_MATRIX.csv` makes absence explicit. In particular, a run censored
before stopping/final-tree generation is not given a fabricated artifact.

`ARCHIVE_MANIFEST.csv` binds every archived file to its selected source path and
SHA-256. Generated checker `temp.py` files and per-run copies of immutable
requirements are excluded as duplicates; the formulas/verdicts remain in the
generation dumps, ARFFs, and SQLite cache, while requirements remain in `data/`.
New executions must write below `rerun/`.
