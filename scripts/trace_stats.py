#!/usr/bin/env python3
"""Records per benchmark trace, and their min/max/mean/standard deviation."""
import csv
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRACES = ROOT / "inputs" / "traces"
OUT = ROOT / "analysis" / "trace_statistics.csv"

csv.field_size_limit(sys.maxsize)
records = {}
for family in ("AT", "CC"):
    for row in list(csv.reader(open(TRACES / f"traces{family}.csv")))[1:]:
        records[row[0].strip()] = sum(1 for sample in row[1].strip().strip("[]").split(";") if sample.strip())
records["RR"] = sum(1 for _ in open(TRACES / "traceRR.csv"))
counts = list(records.values())
summary = {"traces": len(counts), "min": min(counts), "max": max(counts),
           "mean": round(statistics.mean(counts), 1), "sd": round(statistics.pstdev(counts), 1)}
with OUT.open("w", newline="") as stream:
    writer = csv.writer(stream); writer.writerow(["trace", "records"]); writer.writerows(records.items())
print("trace records: " + ", ".join(f"{key}={value}" for key, value in summary.items()))
