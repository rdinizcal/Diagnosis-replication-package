#!/usr/bin/env python3
"""Validate coverage, provenance, RQ1/RQ2 arithmetic, and paper-facing oracles."""
from __future__ import annotations

import csv
import json
import math
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def rows(path: Path):
    with path.open(newline="") as stream: return list(csv.DictReader(stream))


def require(condition, message):
    if not condition: raise AssertionError(message)


def same_csv(name):
    expected, actual = rows(ROOT / "tests" / "expected" / name), rows(ROOT / "analysis" / name)
    require(expected == actual, f"oracle mismatch: {name} ({len(expected)} vs {len(actual)} rows)")
    print(f"OK oracle {name} ({len(actual)} rows)")


def main() -> None:
    registry = rows(ROOT / "experiments" / "registry.csv")
    require([row["paper_experiment_id"] for row in registry] == [f"exp{i}" for i in range(1, 35)], "registry IDs")
    require(all(json.loads(row["seed_set_json"]) == list(range(10)) for row in registry), "declared seed sets")
    reconciliation = rows(ROOT / "raw_results" / "normalized" / "experiment_seed_reconciliation.csv")
    require(len(reconciliation) == 340 and len({(r["canonical_experiment_id"], r["seed"]) for r in reconciliation}) == 340, "340 unique slots")
    require(Counter(r["status"] for r in reconciliation) == Counter(completed_informative=283, completed_degenerate=20, timeout=37), "reconciled outcomes")

    evidence = rows(ROOT / "raw_results" / "rq1_rq2" / "EVIDENCE_MATRIX.csv")
    require(len(evidence) == 340, "evidence matrix coverage")
    always = ("effective_configuration", "generated_candidates_generation_fitness", "unique_formulas_verdict_duration",
              "cache_hit_miss_timeout_tiers", "j48_training_data", "run_log", "scheduler_metadata")
    require(all(row[key] == "True" for row in evidence for key in always), "mandatory raw evidence")
    require(sum(row["stopping_history"] == "False" for row in evidence) == 37, "stopping histories unavailable only for censored runs")

    expert = rows(ROOT / "inputs" / "expert_trees" / "INDEX.csv")
    require(len(expert) == 34, "34 expert trees")
    require(Counter(row["derivation_status"] for row in expert) == Counter(trace_rule_with_witness=7, expert_region=27), "expert evaluator kinds")
    for row in expert:
        for key in ("machine_readable_tree", "dot", "svg", "pdf"): require((ROOT / row[key]).is_file(), f"missing expert {key}: {row['experiment_id']}")
        spec = json.loads((ROOT / row["machine_readable_tree"]).read_text())
        require(spec["original_reference"]["role"] and spec["canonicalization"]["role"], "expert role separation")
        if row["derivation_status"] == "expert_region":
            require(spec["evaluator"]["satisfied_boxes"], f"expert region: {row['experiment_id']}")
    for exp in (33, 34):
        spec = json.loads((ROOT / f"inputs/expert_trees/machine_readable/exp{exp}.json").read_text())
        require("known_issue" in spec["original_reference"] and spec["canonicalization"]["original_vs_corrected"].startswith("corrected"), f"exp{exp} corrected provenance")

    specs = {item["experiment_id"]: item for item in json.loads((ROOT / "analysis" / "rq1_grid_specifications.json").read_text())}
    pr = rows(ROOT / "analysis" / "rq1_per_seed_confusion.csv")
    require(len(pr) == 340 and sum(row["scored"] == "true" for row in pr) == 283, "RQ1 slot/scored counts")
    for row in pr:
        require(row["checker_undecided_excluded_from_tree_evaluation"] == "true", "undecided policy")
        if row["scored"] != "true": continue
        counts = [int(row[key]) for key in ("tp", "tn", "fp", "fn")]
        require(sum(counts) == specs[row["experiment_id"]]["cartesian_size"] == int(row["grid_points"]), f"grid size {row['experiment_id']}/{row['seed']}")
        tp, _, fp, fn = counts
        require(round(100*tp/(tp+fp), 1) == float(row["precision_pct"]), "precision arithmetic")
        require(round(100*tp/(tp+fn), 1) == float(row["recall_pct"]), "recall arithmetic")
    aggregate = json.loads((ROOT / "analysis" / "rq1_aggregate.json").read_text())
    require(aggregate["n_experiments"] == 29 and aggregate["precision_mean_of_experiment_medians"] == 98.8 and aggregate["recall_mean_of_experiment_medians"] == 97.4, "manuscript RQ1 aggregate")

    inventory = rows(ROOT / "analysis" / "tool_tree_inventory.csv")
    require(len(inventory) == 340, "tool-tree slot inventory")
    require(Counter(row["tree_status"] for row in inventory) == Counter(available=283, degenerate_one_class_reconstructed_from_arff=20, unavailable_run_censored_before_final_tree=37), "tool-tree statuses")
    for row in inventory:
        require((ROOT / row["json"]).is_file(), "tool-tree JSON")
        if row["tree_status"].startswith(("available", "degenerate")):
            for key in ("dot", "svg", "pdf"): require((ROOT / row[key]).is_file(), f"tool-tree {key}")
    modal = rows(ROOT / "analysis" / "modal_tree_selection.csv")
    require(len(modal) == 34 and sum(row["status"].startswith("selected") for row in modal) == 31, "modal selections")
    policy = json.loads((ROOT / "analysis" / "modal_trees" / "SELECTION_POLICY.json").read_text())
    require(policy["grouping_basis"] == "full normalized rule topology" and policy["mode_tie_break"], "modal policy")

    runs = rows(ROOT / "analysis" / "rq2_per_run.csv")
    require(len(runs) == 340, "RQ2 per-run coverage")
    require(sum(row["censored_at_120h"] == "true" for row in runs) == 37, "120-hour censoring")
    require(sum(row["classification"] == "degenerate_one_class" for row in runs) == 20, "degenerate classification")
    required = ("total_wall_sec", "mutation_sec", "checker_sec", "decision_tree_sec", "checker_calls", "unique_calls", "cache_hits",
                "timeout_escalations", "undecided_calls", "stop_reason", "scheduler_node", "cpu_model", "allocated_cpus", "allocated_memory_mb")
    require(all(row[key] != "" for row in runs for key in required), "RQ2 required per-run fields")
    grouped = defaultdict(list)
    for row in runs: grouped[row["experiment_id"]].append(row)
    table8 = {row["canonical_experiment_id"]: row for row in rows(ROOT / "analysis" / "table8_authoritative.csv")}
    for exp, group in grouped.items():
        require(math.isclose(statistics.median(float(row["total_wall_sec"]) for row in group), float(table8[exp]["total_sec_median"]), abs_tol=1e-6), f"Table 8 median {exp}")
    for name in ("table8_authoritative.csv", "table9_authoritative.csv", "appendix_precision_recall_authoritative.csv",
                 "rtamt_checker_authoritative.csv", "rtamt_checker_agreement.csv"):
        same_csv(name)
    print("verification PASS: 34 experiments, 340 RQ1/RQ2 slots, all counts and aggregates")


if __name__ == "__main__":
    try: main()
    except Exception as error:
        print(f"verification FAIL: {error}", file=sys.stderr); raise
