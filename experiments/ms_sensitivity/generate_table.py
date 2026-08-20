#!/usr/bin/env python3
"""Generate an evidence-completeness comparison; never invent absent metrics."""
from __future__ import annotations

import csv
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[1] / "derived_results" / "ms_sensitivity_comparison.csv"
RAW = HERE.parents[1] / "raw_results" / "ms_sensitivity"
rows = []
for experiment in ("exp2", "exp4"):
    for ms in (100, 1000):
        found = list((RAW / experiment / f"MS{ms}").glob("seed*/summary.json"))
        rows.append({"experiment": experiment, "MS": ms, "expected_seeds": 10,
                     "completed_seeds": len(found), "runtime": "", "precision": "",
                     "recall": "", "status": "not_executed" if not found else "incomplete"})
with OUT.open("w", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
if any(row["completed_seeds"] for row in rows):
    raise SystemExit("partial raw MS evidence found; aggregation requires a complete 40-run campaign")
print("generated MS comparison status table: 0/40 runs; no metrics asserted")
