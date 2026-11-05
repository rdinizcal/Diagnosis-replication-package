#!/usr/bin/env python3
"""Generate checker-swap evidence tables from preserved machine outputs."""
from __future__ import annotations

import csv
import json
from pathlib import Path

from checker_swap_accuracy import at1_accuracy, ccx_accuracy

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw_results" / "checker_swap_rtamt"
OUT = ROOT / "analysis"

RUNS = {"AT1": "AT1_seed1", "CCx": "CCX_seed0"}
# The Z3 side is the original campaign's run of the same requirement and configuration.
Z3_RUNS = {"AT1": "AT1_exp2", "CCx": "CCX_exp31"}
PHASES = ("mutation_timestamp", "tracheck_timestamp", "diagnosi_timestamp")


def accuracy(requirement: str, tree: Path) -> float:
    measure = at1_accuracy if requirement == "AT1" else ccx_accuracy
    return round(measure(tree)[2] * 100, 2)


def duration(seconds: float) -> str:
    if seconds < 1000: return f"{seconds:.0f}\\,s"
    if seconds < 2 * 86400: return f"{seconds / 3600:.1f}\\,h"
    return f"{seconds / 86400:.1f}\\,d"


def per_call(seconds: float) -> str:
    return f"{seconds:.1f}" if seconds >= 10 else f"{seconds:.3g}"


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)


def main() -> None:
    metrics = []
    speedups = []
    for requirement, run_name in RUNS.items():
        run = RAW / "runs" / run_name
        z3_run = RAW / "z3_records" / Z3_RUNS[requirement]
        report = json.loads((run / "report.json").read_text())
        timing = json.loads((run / "timespan.json").read_text())
        summary = json.loads((run / "summary.json").read_text())
        z3_report = json.loads((z3_run / "report.json").read_text())
        z3_timing = json.loads((z3_run / "timespan.json").read_text())
        rows = []
        for engine, path, calls, times in (
                ("Z3", z3_run, int(z3_report["TOTAL"]), z3_timing),
                ("RTAMT", run, int(report["rtamt_evaluations"]), timing)):
            checker = float(times["tracheck_timestamp"])
            rows.append({"requirement": requirement, "engine": engine, "checker_calls": calls,
                         "checker_sec": f"{checker:.6f}", "seconds_per_call": f"{checker / calls:.6f}",
                         "accuracy_pct": accuracy(requirement, path / "J48-data-100.out"),
                         "diagnosis_sec": f"{sum(float(times[key]) for key in PHASES):.6f}",
                         "source": str((path / "timespan.json").relative_to(ROOT))})
        metrics.extend(rows)
        z3_per_call, rtamt_per_call = (float(row["seconds_per_call"]) for row in rows)
        final_tree = next(item for item in summary["j48_runs"] if item["qty"] == 1.0)
        speedups.append({
            "requirement": requirement,
            "z3_seconds_per_call": f"{z3_per_call:.6f}",
            "rtamt_seconds_per_call": f"{rtamt_per_call:.6f}",
            "computed_speedup": f"{z3_per_call / rtamt_per_call:.3f}",
            "rtamt_phase_sum_sec": rows[1]["diagnosis_sec"],
            "rtamt_end_to_end_sec": f"{float(summary['ga_sec']):.6f}",
            "tree_accuracy_pct": rows[1]["accuracy_pct"],
            "tree_nodes": final_tree.get("tree_nodes", ""),
            "tree_depth": final_tree.get("tree_depth", ""),
            "tree_leaves": final_tree.get("tree_leaves", ""),
            "root_split": final_tree.get("root_split", ""),
        })
    write_csv(OUT / "rtamt_checker_authoritative.csv", metrics)
    write_csv(OUT / "rtamt_speedups.csv", speedups)
    tex_rows = []
    for row in metrics:
        tex_rows.append(
            f"{row['requirement']} & {row['engine']} & {row['checker_calls']} & "
            f"{duration(float(row['checker_sec']))} & {per_call(float(row['seconds_per_call']))} & "
            f"{duration(float(row['diagnosis_sec']))} & {float(row['accuracy_pct']):.2f}\\% \\\\"
        )
    (OUT / "rtamt_checker_rows.tex").write_text("\n".join(tex_rows) + "\n")
    by_req = {row["requirement"]: row for row in speedups}
    (OUT / "rtamt_macros.tex").write_text(
        f"\\newcommand{{\\ATspeedup}}{{{float(by_req['AT1']['computed_speedup']):.0f}}}\n"
        f"\\newcommand{{\\CCXspeedup}}{{{float(by_req['CCx']['computed_speedup']):.0f}}}\n"
    )

    sweep = []
    for run in sorted((RAW / "runs").glob("AT1_seed*"), key=lambda path: int(path.name[8:])):
        report = json.loads((run / "report.json").read_text())
        sweep.append({"seed": run.name[8:], "checker_calls": report["rtamt_evaluations"],
                      "accuracy_pct": accuracy("AT1", run / "J48-data-100.out")})
    write_csv(OUT / "rtamt_at1_seed_sweep.csv", sweep)

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
