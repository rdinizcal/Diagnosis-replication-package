#!/usr/bin/env python3
"""Verify packaged auxiliary evidence and its declared scope."""
from __future__ import annotations

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
    rq3 = rows(ROOT / "analysis/rq3_per_run.csv")
    catalogue = rows(ROOT / "analysis/rq3_configuration_catalogue.csv")
    rq3_validation = json.loads((ROOT / "analysis/rq3_configuration_validation.json").read_text())
    require(len(rq3) == 140 and len(catalogue) == 28, "RQ3 coverage")
    require(rq3_validation["status"] == "pass" and rq3_validation["configurations"] == 140,
            "RQ3 executable configurations")
    require(all(int(row["n_runs"]) == 5 for row in rows(ROOT / "analysis/table9_authoritative.csv")), "RQ3 five seeds")
    require(all((ROOT / row["launch_template"]).is_file() for row in catalogue), "RQ3 launch templates")
    print("OK RQ3: 140 raw runs, 28 configurations, generated Table 9")

    op = ROOT / "experiments/operator_coverage"
    require(json.loads((op / "actual_results.json").read_text()) ==
            json.loads((op / "expected_results.json").read_text()), "operator oracle")
    require(len(rows(op / "coverage_matrix.csv")) == 16, "operator matrix")
    print("OK operators: OP1-OP15 + OP4a fixtures and four-way matrix")

    paired = rows(ROOT / "analysis/rtamt_paired_verdicts.csv")
    require(len(paired) == 4350 and all(row["classification"] == "match" for row in paired), "RTAMT differential")
    for row in rows(ROOT / "analysis/rtamt_speedups.csv"):
        expected = float(row["z3_seconds_per_call"]) / float(row["rtamt_seconds_per_call"])
        require(abs(expected - float(row["computed_speedup"])) < 0.01, "computed speedup")
    hardware = json.loads((ROOT / "experiments/checker_swap_rtamt/hardware.json").read_text())
    require(hardware["archived_run_hardware"]["chip"] == "Apple M3", "RTAMT hardware metadata")
    print("OK RTAMT: two raw runs and 4,350 paired verdicts; speedups computed")

    fix = rows(ROOT / "experiments/implementation_fix/raw/verdicts.csv")
    require(len(fix) == 32, "implementation-fix verdict matrix")
    require(all(row["satisfied"] == "True" for row in fix if row["version"] == "post_fix"), "post-fix verdicts")
    require(any(row["scenario"] == "retry" and row["version"] == "pre_fix" and
                row["requirement"] == "ϕ3" and row["satisfied"] == "False" for row in fix), "flag witness")
    print("OK implementation fix: 8 traces, 32 verdicts, executed retry witness")

    baseline = rows(ROOT / "raw_results/baseline_td_sb_tempsy/outcomes.csv")
    inputs = ROOT / "inputs/baseline_td_sb_tempsy"
    require(len(baseline) == 17, "baseline outcomes")
    require(all((inputs / "CsvLogs" / row["trace_csv"]).is_file() for row in baseline), "baseline traces")
    require(all((inputs / "XmiProperties" / row["specification_xmi"]).is_file()
                for row in baseline if row["specification_xmi"]), "baseline specifications")
    counts = rows(ROOT / "analysis/baseline_outcome_counts.csv")
    require([int(row["count"]) for row in counts] == [5, 4, 8], "baseline outcome counts")
    print("OK baseline: 17 outcomes, inputs present, 5 diagnoses / 4 no output / 8 unsupported")

    forbidden = ("example" + ".com", "zenodo.org/record/" + "XXXX",
                 "INSERT" + "_URL", "TODO" + "_URL", "<" + "URL>")
    roots = [ROOT]
    hits = []
    for root in roots:
        for path in root.rglob("*"):
            if path.is_file() and ".git" not in path.parts and "_build" not in path.parts and path.suffix.lower() in {".tex", ".md", ".json", ".csv", ".yaml", ".yml"}:
                text = path.read_text(errors="ignore")
                if any(token in text for token in forbidden): hits.append(str(path))
    require(not hits, f"placeholder URLs: {hits}")
    print("OK URLs: no placeholder URL tokens")

    print("auxiliary verification PASS")


if __name__ == "__main__":
    main()
