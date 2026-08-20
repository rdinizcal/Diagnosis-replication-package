#!/usr/bin/env python3
"""Build the four-way operator status matrix from code, fixtures, and archives."""
from __future__ import annotations

import csv
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

OPS = ["OP1", "OP2", "OP3", "OP4", "OP4a", "OP5", "OP6", "OP7",
       "OP8", "OP9", "OP10", "OP11", "OP12", "OP13", "OP14", "OP15"]
IMPLEMENTED = {"OP2", "OP4", "OP5", "OP6", "OP7", "OP11", "OP12", "OP13"}


def archived_candidate_variation(experiment: str) -> bool:
    """Require an archived generation containing a candidate distinct from HC."""
    for path in (ROOT / "raw_results" / "rq1_rq2" / experiment).glob("seed*/archive/generations/*.txt"):
        formulas = []
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if "\t" not in line or line.startswith("Formula"):
                continue
            formulas.append(line.split("\t", 1)[0].split(": ", 1)[-1])
        if len(set(formulas)) > 1:
            return True
    return False


def main() -> None:
    with (ROOT / "experiments" / "registry.csv").open(newline="", encoding="utf-8") as stream:
        registry = list(csv.DictReader(stream))
    with (HERE / "operator_coverage.csv").open(newline="", encoding="utf-8") as stream:
        synthetic = {row["operator"]: row for row in csv.DictReader(stream)}

    configured = {op: [] for op in OPS}
    for row in registry:
        for op in json.loads(row["operators_json"]):
            configured[op].append(row["paper_experiment_id"])

    rows = []
    for op in OPS:
        configured_experiments = configured[op]
        sampled_experiments = [exp for exp in configured_experiments if archived_candidate_variation(exp)]
        rows.append({
            "operator": op,
            "implemented_in_active_sampler": "yes" if op in IMPLEMENTED else "no",
            "covered_by_synthetic_suite": "yes" if synthetic[op]["fired_count"] != "0" else "no",
            "configured_in_34_benchmark_experiments": "yes" if configured_experiments else "no",
            "configured_experiments": ";".join(configured_experiments),
            "actually_sampled_in_archived_runs": "yes" if sampled_experiments else "no",
            "sampled_evidence_experiments": ";".join(sampled_experiments),
            "sampling_evidence_rule": (
                "operator is declared by the canonical registry and an archived generation contains "
                "a candidate distinct from its generation HC; family-level evidence"
                if sampled_experiments else "no configured archived candidate evidence"
            ),
        })

    with (HERE / "coverage_matrix.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    lines = [
        "# Operator implementation and coverage matrix", "",
        "‘Sampled’ is family-level evidence: the canonical registry enables the operator and at least one archived generation contains a candidate distinct from its generation champion. It does not claim that every configured position was sampled.", "",
        "| Operator | Implemented | Synthetic suite | Configured in 34 | Sampled in archive | Experiments |",
        "|---|:---:|:---:|:---:|:---:|---|",
    ]
    for row in rows:
        lines.append(f"| {row['operator']} | {row['implemented_in_active_sampler']} | {row['covered_by_synthetic_suite']} | {row['configured_in_34_benchmark_experiments']} | {row['actually_sampled_in_archived_runs']} | {row['configured_experiments'] or '—'} |")
    (HERE / "coverage_matrix.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {len(rows)} operator-matrix rows")


if __name__ == "__main__":
    main()
