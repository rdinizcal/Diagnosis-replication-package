"""Regression tests for all paper-facing RQ1/RQ2 counts and aggregates."""
from __future__ import annotations

import csv
import json
import statistics
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def rows(relative):
    with (ROOT / relative).open(newline="") as stream: return list(csv.DictReader(stream))


def test_registry_and_seed_accounting():
    registry = rows("experiments/registry.csv")
    reconciled = rows("raw_results/normalized/experiment_seed_reconciliation.csv")
    assert [row["paper_experiment_id"] for row in registry] == [f"exp{i}" for i in range(1, 35)]
    assert len(reconciled) == len({(row["canonical_experiment_id"], row["seed"]) for row in reconciled}) == 340
    assert Counter(row["status"] for row in reconciled) == Counter(completed_informative=284, completed_degenerate=20, timeout=36)


def test_rq1_confusions_and_undecided_exclusion():
    specs = {item["experiment_id"]: item for item in json.loads((ROOT / "derived_results/rq1_grid_specifications.json").read_text())}
    data = rows("derived_results/rq1_per_seed_confusion.csv")
    assert len(data) == 340
    assert sum(row["scored"] == "true" for row in data) == 284
    for row in data:
        assert row["checker_undecided_excluded_from_tree_evaluation"] == "true"
        if row["scored"] == "true":
            assert sum(int(row[key]) for key in ("tp", "tn", "fp", "fn")) == specs[row["experiment_id"]]["cartesian_size"]


def test_rq1_manuscript_aggregate():
    value = json.loads((ROOT / "derived_results/rq1_aggregate.json").read_text())
    assert value["n_experiments"] == 29
    assert value["precision_mean_of_experiment_medians"] == 98.8
    assert value["recall_mean_of_experiment_medians"] == 97.5


def test_rq2_counts_and_table8_medians():
    data = rows("derived_results/rq2_per_run.csv")
    table = {row["canonical_experiment_id"]: row for row in rows("derived_results/table8_authoritative.csv")}
    assert len(data) == 340
    assert sum(row["censored_at_120h"] == "true" for row in data) == 36
    assert sum(row["classification"] == "degenerate_one_class" for row in data) == 20
    for exp in table:
        values = [float(row["total_wall_sec"]) for row in data if row["experiment_id"] == exp]
        assert abs(statistics.median(values) - float(table[exp]["total_sec_median"])) <= 1e-6


def test_expert_tool_and_modal_tree_coverage():
    expert = rows("references/expert_trees/INDEX.csv")
    tool = rows("derived_results/tool_tree_inventory.csv")
    modal = rows("derived_results/modal_tree_selection.csv")
    assert len(expert) == 34 and len(tool) == 340 and len(modal) == 34
    assert sum(row["tree_status"] == "unavailable_run_censored_before_final_tree" for row in tool) == 36
    assert sum(row["status"].startswith("selected") for row in modal) == 31
