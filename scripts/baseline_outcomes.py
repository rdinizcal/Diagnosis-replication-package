#!/usr/bin/env python3
"""Summarise the TD-SB-TemPsy runs: outcome counts and diagnosis witnesses."""
from __future__ import annotations

import csv
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw_results" / "baseline_td_sb_tempsy" / "outcomes.csv"
OUT = ROOT / "analysis"
OUTCOMES = ("diagnosis", "no_output", "unsupported")
WITNESS = re.compile(r"vSignal = '([^']+)', Records = Sequence\{Tuple\{timestamp = ([-\d.E]+), "
                     r"signalValue = ([-\d.E]+)\}\}")


def main() -> None:
    rows = list(csv.DictReader(RAW.open()))
    counts = Counter("unsupported" if row["outcome"].startswith("unsupported") else row["outcome"]
                     for row in rows)
    with (OUT / "baseline_outcome_counts.csv").open("w", newline="") as stream:
        writer = csv.writer(stream); writer.writerow(["outcome", "requirements", "count"])
        for key in OUTCOMES:
            names = [row["requirement"] for row in rows if row["outcome"].startswith(key)]
            writer.writerow([key, ";".join(names), counts[key]])
    with (OUT / "baseline_diagnoses.csv").open("w", newline="") as stream:
        writer = csv.writer(stream); writer.writerow(["requirement", "signal", "timestamp_us", "value"])
        for row in rows:
            match = WITNESS.search(row["tool_output"])
            if row["outcome"] == "diagnosis" and match:
                writer.writerow([row["requirement"], match[1], float(match[2]), match[3]])
    print(f"TD-SB-TemPsy: {counts['diagnosis']}/{len(rows)} diagnoses, {counts['no_output']} no output, "
          f"{counts['unsupported']} unsupported")


if __name__ == "__main__":
    main()
