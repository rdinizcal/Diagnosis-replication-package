#!/usr/bin/env python3
"""Verify auxiliary evidence and identify release-blocking missing campaigns."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-incomplete", action="store_true")
    args = parser.parse_args()
    blockers = []

    rq3 = rows(ROOT / "derived_results/rq3_per_run.csv")
    catalogue = rows(ROOT / "derived_results/rq3_configuration_catalogue.csv")
    rq3_validation = json.loads((ROOT / "derived_results/rq3_configuration_validation.json").read_text())
    require(len(rq3) == 140 and len(catalogue) == 28, "RQ3 coverage")
    require(rq3_validation["status"] == "pass" and rq3_validation["configurations"] == 140,
            "RQ3 executable configurations")
    require(all(int(row["n_runs"]) == 5 for row in rows(ROOT / "derived_results/table9_authoritative.csv")), "RQ3 five seeds")
    require(all(row["archive_byte_identical"] == "False" for row in catalogue), "RQ3 reconstruction disclosure")
    print("OK RQ3: 140 raw runs, 28 configurations, generated Table 9")

    op = ROOT / "experiments/operator_coverage"
    require(json.loads((op / "actual_results.json").read_text()) ==
            json.loads((op / "expected_results.json").read_text()), "operator oracle")
    require(len(rows(op / "coverage_matrix.csv")) == 16, "operator matrix")
    print("OK operators: OP1-OP15 + OP4a fixtures and four-way matrix")

    paired = rows(ROOT / "derived_results/rtamt_paired_verdicts.csv")
    require(len(paired) == 4350 and all(row["classification"] == "match" for row in paired), "RTAMT differential")
    for row in rows(ROOT / "derived_results/rtamt_speedups.csv"):
        expected = float(row["z3_seconds_per_call"]) / float(row["rtamt_seconds_per_call"])
        require(abs(expected - float(row["computed_speedup"])) < 0.01, "computed speedup")
    hardware = json.loads((ROOT / "experiments/checker_swap_rtamt/hardware.json").read_text())
    require(hardware["archived_run_hardware"]["chip"] == "Apple M3", "RTAMT hardware metadata")
    print("OK RTAMT: two raw runs and 4,350 paired verdicts; speedups computed")
    blockers.append("RTAMT: raw Z3 timing logs were not retained")

    fix = rows(ROOT / "experiments/implementation_fix/raw/verdicts.csv")
    require(len(fix) == 32, "implementation-fix verdict matrix")
    require(all(row["satisfied"] == "True" for row in fix if row["version"] == "post_fix"), "post-fix verdicts")
    require(any(row["scenario"] == "retry" and row["version"] == "pre_fix" and
                row["requirement"] == "ϕ3" and row["satisfied"] == "False" for row in fix), "flag witness")
    print("OK implementation fix: 8 traces, 32 verdicts, executed retry witness")

    baseline = rows(ROOT / "experiments/baseline_td_sb_tempsy/evidence_status.csv")
    require(len(baseline) == 17, "baseline inventory")
    if any(row["release_status"] != "verified" for row in baseline):
        blockers.append("TD-SB-TemPsy: 17 converted inputs and raw run records were not retained")
    ms = rows(ROOT / "derived_results/ms_sensitivity_comparison.csv")
    require(len(ms) == 4, "MS matrix")
    ms_configs = sorted((ROOT / "experiments/ms_sensitivity/configs").rglob("seed*.json"))
    require(len(ms_configs) == 40, "40 MS configurations")
    require(all(json.loads(path.read_text())["replication_metadata"]["tool_snapshot_for_rerun"] ==
                "05d0750395972662e9be0a1083b09a6dce7e3e65" for path in ms_configs),
            "MS pipeline snapshot")
    if sum(int(row["completed_seeds"]) for row in ms) != 40:
        blockers.append("MS sensitivity: current-pipeline 40-run campaign has not been executed")

    forbidden = ("example" + ".com", "zenodo.org/record/" + "XXXX",
                 "INSERT" + "_URL", "TODO" + "_URL", "<" + "URL>")
    roots = [ROOT, ROOT.parents[1] / "paper/latex"]
    hits = []
    for root in roots:
        for path in root.rglob("*"):
            if path.is_file() and ".git" not in path.parts and "_build" not in path.parts and path.suffix.lower() in {".tex", ".md", ".json", ".csv", ".yaml", ".yml"}:
                text = path.read_text(errors="ignore")
                if any(token in text for token in forbidden): hits.append(str(path))
    require(not hits, f"placeholder URLs: {hits}")
    print("OK URLs: no placeholder URL tokens")

    if blockers:
        print("RELEASE BLOCKERS:")
        for blocker in blockers: print(f"- {blocker}")
        if not args.allow_incomplete:
            raise SystemExit(2)
    print("auxiliary verification PASS" if not blockers else "auxiliary evidence verification PASS; release completeness FAIL")


if __name__ == "__main__":
    main()
