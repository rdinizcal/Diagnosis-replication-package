#!/usr/bin/env python3
"""Compare the evaluated manuscript's explicit claims with packaged evidence."""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = json.loads((ROOT / "expected" / "manuscript_claims.json").read_text())


def rows(relative: str) -> list[dict[str, str]]:
    with (ROOT / relative).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def main() -> None:
    aggregate = json.loads((ROOT / "derived_results" / "rq1_aggregate.json").read_text())
    rq1_n = int(aggregate["n_experiments"])
    completed = sum(row["status"] != "timeout_or_incomplete" for row in rows("derived_results/table8_authoritative.csv"))
    baseline_verified = sum(row["release_status"] == "verified" for row in rows("experiments/baseline_td_sb_tempsy/evidence_status.csv"))
    actual = {
        "abstract_expert_aligned_experiments": rq1_n,
        "rq1_answer_expert_aligned_experiments": rq1_n,
        "rq2_completed_experiments": completed,
        "baseline_cases_with_retained_raw_evidence": baseline_verified,
    }
    failed = False
    print(f"manuscript SHA-256: {SPEC['sha256']}")
    for name, item in SPEC["claims"].items():
        expected, observed = int(item["paper_value"]), actual[name]
        status = "PASS" if expected == observed else "FAIL"
        failed |= status == "FAIL"
        print(f"{status} {name}: paper={expected}, packaged_evidence={observed}")
    if failed:
        raise SystemExit("manuscript-value consistency FAIL")
    print("manuscript-value consistency PASS")


if __name__ == "__main__":
    main()
