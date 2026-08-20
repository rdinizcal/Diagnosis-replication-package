#!/usr/bin/env python3
"""Extract and aggregate RQ2 efficiency evidence for all 340 run slots."""
from __future__ import annotations

import csv
import json
import re
import statistics
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw_results" / "rq1_rq2"
OUT = ROOT / "derived_results"


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def load(path: Path) -> dict:
    return json.loads(path.read_text()) if path.exists() else {}


def write(path: Path, data: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(data[0])); writer.writeheader(); writer.writerows(data)


def number(value):
    return None if value in (None, "") else float(value)


def fmt(value):
    if value in (None, ""): return ""
    return f"{float(value):.6f}".rstrip("0").rstrip(".")


def percentile(values: list[float], p: float) -> float:
    values = sorted(values); point = (len(values) - 1) * p
    lo, hi = int(point), min(int(point) + 1, len(values) - 1)
    return values[lo] + (values[hi] - values[lo]) * (point - lo)


def stats(values) -> dict[str, str]:
    values = [float(value) for value in values if value not in (None, "")]
    if not values: return {"median": "", "mean": "", "iqr": ""}
    return {"median": fmt(statistics.median(values)), "mean": fmt(statistics.mean(values)),
            "iqr": fmt(percentile(values, .75) - percentile(values, .25))}


def node_metadata(path: Path) -> dict[str, str]:
    text = path.read_text(errors="replace") if path.exists() else ""
    def value(label):
        match = re.search(rf"^{re.escape(label)}:\s*(.*)$", text, re.M)
        return match.group(1).strip() if match else "UNRECORDED"
    model = re.search(r"^model name\s*:\s*(.*)$", text, re.M)
    cpus = re.search(r"^cpus:\s*(\d+)\s+mem:\s*(\d+)", text, re.M)
    return {"scheduler_node": value("node"), "cpu_model": model.group(1).strip() if model else "UNRECORDED",
            "scheduler_constraint": value("constraint"), "allocated_cpus": cpus.group(1) if cpus else "UNRECORDED",
            "allocated_memory_mb": cpus.group(2) if cpus else "UNRECORDED",
            "scheduler_started": value("started"), "scheduler_finished": value("finished")}


def extract() -> list[dict]:
    reconciled = rows(ROOT / "raw_results" / "normalized" / "experiment_seed_reconciliation.csv")
    output = []
    for row in reconciled:
        exp, seed = row["canonical_experiment_id"], row["seed"]
        archive = RAW / exp / f"seed{seed}" / "archive"
        summary, report, timing = load(archive / "summary.json"), load(archive / "report.json"), load(archive / "timespan.json")
        total = summary.get("runtime_sec", number(row["total_sec"]))
        mutation = timing.get("mutation_timestamp", number(row["mutation_sec"]))
        checker = timing.get("tracheck_timestamp", number(row["trace_check_sec"]))
        tree = timing.get("diagnosi_timestamp", number(row["decision_tree_sec"]))
        calls = report.get("real_solves", report.get("cache_misses", number(row["checker_calls"])))
        unique = report.get("cache_distinct", report.get("cache_misses", calls))
        hits = report.get("cache_hits", "")
        escalations = (report.get("tier2_decided", 0) + report.get("tier2_undecided", 0)) if report else ""
        undecided = report.get("tier2_undecided", number(row["undecided_count"]))
        share = 100 * checker / total if checker is not None and total else None
        if row["status"] == "timeout": classification = "censored_120h"
        elif row["status"] == "completed_degenerate": classification = "degenerate_one_class"
        elif calls and undecided not in (None, "") and float(undecided) / float(calls) >= .5: classification = "undecided_heavy"
        elif escalations not in (None, "") and calls and float(escalations) / float(calls) >= .5: classification = "timeout_escalation_heavy"
        else: classification = "completed_informative"
        output.append({"experiment_id": exp, "requirement": row["requirement"], "seed": seed,
                       "status": row["status"], "classification": classification,
                       "censored_at_120h": str(row["status"] == "timeout").lower(),
                       "total_wall_sec": fmt(total), "mutation_sec": fmt(mutation),
                       "checker_sec": fmt(checker), "decision_tree_sec": fmt(tree),
                       "checker_share_pct": fmt(share), "checker_calls": fmt(calls),
                       "unique_calls": fmt(unique), "cache_hits": fmt(hits),
                       "timeout_escalations": fmt(escalations), "undecided_calls": fmt(undecided),
                       "candidate_evaluations": report.get("TOTAL", row["candidate_evaluations"]),
                       "stop_reason": row["stop_reason"], **node_metadata(archive / "node_info.txt")})
    return output


def aggregate(per_run: list[dict]) -> tuple[list[dict], list[dict]]:
    grouped = defaultdict(list)
    for row in per_run: grouped[row["experiment_id"]].append(row)
    wide, table8 = [], []
    metrics = ("total_wall_sec", "mutation_sec", "checker_sec", "decision_tree_sec", "checker_share_pct",
               "checker_calls", "unique_calls", "cache_hits", "timeout_escalations", "undecided_calls")
    for i in range(1, 35):
        exp = f"exp{i}"; group = grouped[exp]; summary = {}
        for metric in metrics:
            for stat, value in stats(row[metric] for row in group).items(): summary[f"{metric}_{stat}"] = value
        base = {"experiment_id": exp, "requirement": group[0]["requirement"], "n_expected": 10,
                "n_completed": sum(row["status"].startswith("completed") for row in group),
                "n_informative": sum(row["status"] == "completed_informative" for row in group),
                "n_degenerate": sum(row["classification"] == "degenerate_one_class" for row in group),
                "n_timeout_censored_120h": sum(row["classification"] == "censored_120h" for row in group),
                "n_undecided_heavy": sum(row["classification"] == "undecided_heavy" for row in group), **summary}
        wide.append(base)
        status = "informative_all_seeds" if base["n_informative"] == 10 else "degenerate_all_seeds" if base["n_degenerate"] == 10 else "timeout_or_incomplete"
        table8.append({"canonical_experiment_id": exp, "requirement": group[0]["requirement"],
                       "reporting_statistic": "median across all 10 seeds; 120h censored elapsed times included",
                       "n_expected": 10, "n_completed": base["n_completed"], "n_informative": base["n_informative"],
                       "n_timeout": base["n_timeout_censored_120h"], "total_sec_median": summary["total_wall_sec_median"],
                       "mutation_sec_median": summary["mutation_sec_median"], "trace_check_sec_median": summary["checker_sec_median"],
                       "decision_tree_sec_median": summary["decision_tree_sec_median"],
                       "checker_calls_median": summary["checker_calls_median"], "status": status})
    return wide, table8


def latex_rows(table8: list[dict]) -> str:
    def duration(seconds, phase=False):
        value = float(seconds)
        if phase and value < 1: return "$<$1s"
        if value < 120: return f"{value:.0f}s"
        if value < 5400: return f"{value/60:.0f}min"
        return f"{value/3600:.1f}h"
    def cells(row):
        exp = int(row["canonical_experiment_id"][3:])
        mark = "$^{\\dagger\\ddagger}$" if exp in (27, 28, 31) else "$^{\\dagger}$" if exp == 32 else "$^{\\ddagger}$" if exp in (25, 26) else ""
        return (f"\\emph{{{row['canonical_experiment_id']}}} & {duration(row['total_sec_median'])}{mark} & "
                f"{duration(row['mutation_sec_median'], True)} & {duration(row['trace_check_sec_median'])} & "
                f"{duration(row['decision_tree_sec_median'], True)} & {float(row['checker_calls_median']):g}")
    lines = []
    for index in range(0, 34, 2):
        if index in (20, 32): lines.append("        \\midrule")
        lines.append(f"        {table8[index]['requirement']} & {cells(table8[index])} & {cells(table8[index+1])}\\\\")
    return "\n".join(lines) + "\n"


def runtime_svg(table8: list[dict]) -> str:
    width, height = 920, 40 + len(table8) * 24
    maximum = max(float(row["total_sec_median"]) for row in table8)
    lines = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" role="img">',
             '<title>RQ2 median total runtime by experiment</title>', '<style>text{font:12px sans-serif}.bar{fill:#3f6f8f}</style>']
    for index, row in enumerate(table8):
        y = 20 + index * 24; value = float(row["total_sec_median"]); bar = 700 * value / maximum
        lines += [f'<text x="5" y="{y+12}">{row["canonical_experiment_id"]}</text>',
                  f'<rect class="bar" x="90" y="{y}" width="{bar:.2f}" height="15"/>',
                  f'<text x="900" y="{y+12}" text-anchor="end">{value/3600:.2f} h</text>']
    return "\n".join(lines + ["</svg>"]) + "\n"


def main() -> None:
    OUT.mkdir(exist_ok=True)
    per_run = extract()
    if len(per_run) != 340: raise AssertionError(len(per_run))
    wide, table8 = aggregate(per_run)
    write(OUT / "rq2_per_run.csv", per_run); write(OUT / "rq2_statistics.csv", wide)
    write(OUT / "table8_authoritative.csv", table8)
    (OUT / "table8_rows.tex").write_text(latex_rows(table8))
    (OUT / "rq2_runtime.svg").write_text(runtime_svg(table8))
    methodology = {
        "logical_outputs": "status, verdicts, decided candidate sets, trees, confusion matrices, and counts are reproducible outputs",
        "hardware_sensitive_outputs": "wall, mutation, checker, and decision-tree durations",
        "original_scheduler_metadata": "raw_results/rq1_rq2/exp*/seed*/archive/node_info.txt and rq2_per_run.csv",
        "performance_rerun_tolerance": {"relative": 0.20, "applies_to": "experiment-level median phase and total times",
                                        "conditions": "same CPU model, allocation, checker/tool versions, and exclusive/uncontended scheduling",
                                        "interpretation": "outside tolerance requires investigation; it does not invalidate logical reproduction"},
        "censoring": {"limit_hours": 120, "runs": sum(row["censored_at_120h"] == "true" for row in per_run),
                      "policy": "retain observed elapsed time; never relabel as convergence"},
    }
    (OUT / "rq2_runtime_methodology.json").write_text(json.dumps(methodology, indent=2, sort_keys=True) + "\n")
    experiment_medians = [float(row["total_sec_median"]) for row in table8]
    q1, q3 = percentile(experiment_medians, .25), percentile(experiment_medians, .75)
    paper_values = {"n_run_slots": len(per_run), "n_completed_informative": sum(row["status"] == "completed_informative" for row in per_run),
                    "n_completed_degenerate": sum(row["status"] == "completed_degenerate" for row in per_run),
                    "n_censored_120h": sum(row["censored_at_120h"] == "true" for row in per_run),
                    "experiment_median_runtime_hours_median": round(statistics.median(experiment_medians)/3600, 1),
                    "experiment_median_runtime_iqr_minutes_hours": [round(q1/60), round(q3/3600, 1)],
                    "checker_share_pct_median_across_runs": round(statistics.median(float(row["checker_share_pct"]) for row in per_run if row["checker_share_pct"]), 1)}
    (OUT / "rq2_paper_values.json").write_text(json.dumps(paper_values, indent=2, sort_keys=True) + "\n")
    print(f"RQ2: {len(per_run)} runs, {len(table8)} Table 8 rows, {methodology['censoring']['runs']} censored")


if __name__ == "__main__":
    main()
