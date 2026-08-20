#!/usr/bin/env python3
"""Generate checker-swap evidence tables from preserved machine outputs."""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw_results" / "checker_swap_rtamt"
OUT = ROOT / "derived_results"

RUNS = {
    "AT1": ("AT1_seed1", 97.24),
    "CCx": ("CCX_seed0", 99.88),
}
# These are contemporaneous author records, not raw timing logs. They are kept
# to make the historical estimate auditable, but are never promoted to raw data.
Z3_RECORDED = {
    "AT1": {"calls": 2300, "value": 8.6, "unit": "hours", "diagnosis_value": 8.8, "accuracy": 97.97},
    "CCx": {"calls": 200, "value": 4.4, "unit": "days", "diagnosis_value": 4.4, "accuracy": 99.54},
}


def seconds(value: float, unit: str) -> float:
    factors = {"seconds": 1, "minutes": 60, "hours": 3600, "days": 86400}
    return value * factors[unit]


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)


def main() -> None:
    metrics = []
    speedups = []
    for requirement, (run_name, accuracy) in RUNS.items():
        run = RAW / "runs" / run_name
        report = json.loads((run / "report.json").read_text())
        timing = json.loads((run / "timespan.json").read_text())
        summary = json.loads((run / "summary.json").read_text())
        calls = int(report["rtamt_evaluations"])
        checker = float(timing["tracheck_timestamp"])
        phases = sum(float(timing[key]) for key in
                     ("mutation_timestamp", "tracheck_timestamp", "diagnosi_timestamp"))
        rtamt_per_call = checker / calls
        z3 = Z3_RECORDED[requirement]
        z3_total = seconds(z3["value"], z3["unit"])
        z3_per_call = z3_total / z3["calls"]
        speedup = z3_per_call / rtamt_per_call
        metrics.extend([
            {"requirement": requirement, "engine": "Z3", "checker_calls": z3["calls"],
             "checker_sec": f"{z3_total:.6f}", "seconds_per_call": f"{z3_per_call:.6f}",
             "accuracy_pct": z3["accuracy"], "duration_evidence": "author_record_only_raw_log_absent",
             "diagnosis_sec": f"{seconds(z3['diagnosis_value'], z3['unit']):.6f}",
             "source": "raw_results/checker_swap_rtamt/RESULTS.md"},
            {"requirement": requirement, "engine": "RTAMT", "checker_calls": calls,
             "checker_sec": f"{checker:.6f}", "seconds_per_call": f"{rtamt_per_call:.6f}",
             "accuracy_pct": accuracy, "duration_evidence": "raw_timespan_json",
             "diagnosis_sec": f"{phases:.6f}",
             "source": f"raw_results/checker_swap_rtamt/runs/{run_name}/timespan.json"},
        ])
        final_tree = next(item for item in summary["j48_runs"] if item["qty"] == 1.0)
        speedups.append({
            "requirement": requirement,
            "z3_seconds_per_call": f"{z3_per_call:.6f}",
            "rtamt_seconds_per_call": f"{rtamt_per_call:.6f}",
            "computed_speedup": f"{speedup:.3f}",
            "speedup_evidence": "estimate_due_to_missing_raw_z3_timing_log",
            "rtamt_phase_sum_sec": f"{phases:.6f}",
            "rtamt_end_to_end_sec": f"{float(summary['ga_sec']):.6f}",
            "tree_accuracy_pct": accuracy,
            "tree_nodes": final_tree.get("tree_nodes", ""),
            "tree_depth": final_tree.get("tree_depth", ""),
            "tree_leaves": final_tree.get("tree_leaves", ""),
            "root_split": final_tree.get("root_split", ""),
        })
    write_csv(OUT / "rtamt_checker_authoritative.csv", metrics)
    write_csv(OUT / "rtamt_speedups.csv", speedups)
    tex_rows = []
    for row in metrics:
        if row["engine"] == "Z3":
            original = Z3_RECORDED[row["requirement"]]
            duration = f"{original['value']} {original['unit']}\\textsuperscript{{*}}"
        else:
            duration = f"{float(row['checker_sec']):.1f}s"
        tex_rows.append(
            f"{row['requirement']} & {row['engine']} & {row['checker_calls']} & {duration} & "
            f"{float(row['seconds_per_call']):.3f} & {float(row['diagnosis_sec']):.1f}s & "
            f"{float(row['accuracy_pct']):.2f}\\% \\\\"
        )
    (OUT / "rtamt_checker_rows.tex").write_text("\n".join(tex_rows) + "\n")
    by_req = {row["requirement"]: row for row in speedups}
    (OUT / "rtamt_macros.tex").write_text(
        f"\\newcommand{{\\ATspeedup}}{{{float(by_req['AT1']['computed_speedup']):.0f}}}\n"
        f"\\newcommand{{\\CCXspeedup}}{{{float(by_req['CCx']['computed_speedup']):.0f}}}\n"
    )

    differential = json.loads((RAW / "at1_differential.json").read_text())
    rows = differential["rows"]
    if len(rows) != 4350 or len({(r["lo"], r["hi"], r["thr"]) for r in rows}) != 4350:
        raise AssertionError("differential evidence is not 4,350 distinct candidates")
    write_csv(OUT / "rtamt_paired_verdicts.csv", [
        {"candidate_id": index, **row,
         "classification": "match" if row["match"] else ("boundary" if row["rho_zero"] else "mismatch")}
        for index, row in enumerate(rows, 1)
    ])
    agreement = [{**differential["summary"],
                  "source_artifact_path": "raw_results/checker_swap_rtamt/at1_differential.json"}]
    write_csv(OUT / "rtamt_checker_agreement.csv", agreement)
    print(f"generated paired verdicts for {len(rows)} candidates and computed {len(speedups)} speedups")


if __name__ == "__main__":
    main()
