#!/usr/bin/env python3
"""Regenerate RQ3 per-run metrics, configuration catalogue, and Table 9."""
from __future__ import annotations

import csv
import hashlib
import json
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "derived_results"
RQ3_CONFIGS = ROOT / "experiments" / "rq3_sensitivity" / "configs"

# Historical position IDs belong to the 2025 encoder used by the launch templates in
# evaluation_inputs/sensitivity. Values below are the unmutated literals of the bundled
# original properties, as every archived ARFF header and data row confirms.
ORIGINALS = {
    "phi2": {12: -3.0, 15: 1.5},
    "phi3": {4: 0, 8: 9_900_000.0, 10: "And", 18: 3.5, 40: 1.0},
    "phi4": {8: 90, 12: 7.0, 15: 1.0},
    "AT53_AT119": {2: "And", 8: 30_000_000, 17: "ForAll", 18: "Implies"},
    "RR": {9: "And", 12: 50.0, 17: 20.0},
}


def read(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def write(name: str, rows: list[dict]) -> None:
    if not rows:
        raise ValueError(f"refusing to write empty {name}")
    OUT.mkdir(exist_ok=True)
    with (OUT / name).open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def number(value):
    return float(value) if value not in (None, "") else None


def fmt(value):
    return f"{value:.6f}".rstrip("0").rstrip(".") if isinstance(value, float) else value


def mean_sd(values: list[float]) -> tuple[str, str]:
    if not values:
        return "", ""
    return fmt(statistics.mean(values)), fmt(statistics.stdev(values)) if len(values) > 1 else "0"


def tree_metrics(text: str) -> tuple[int | None, int | None, int | None]:
    leaves_match = re.search(r"Number of Leaves\s*:\s*(\d+)", text)
    nodes_match = re.search(r"Size of the tree\s*:\s*(\d+)", text)
    body = text.split("J48 pruned tree", 1)[-1].split("Number of Leaves", 1)[0]
    rule_lines = [line for line in body.splitlines() if re.match(r"^(?:\|\s+)*\S+\s+(?:<=|>=|<|>|=|!=)\s+", line)]
    depth = max((line.count("|") + 1 for line in rule_lines), default=None)
    return (
        int(nodes_match.group(1)) if nodes_match else None,
        depth,
        int(leaves_match.group(1)) if leaves_match else None,
    )


def config_rationale(variant: str) -> str:
    if variant == "B":
        return "broad: widest archived admissible domains and alternatives"
    if variant == "G":
        return "guided: domain-plausible narrowed domains with one mutation at a time"
    if variant in {"G2", "G3"}:
        return f"interaction: guided domains with up to {variant[-1]} simultaneous mutations"
    return "omit: excludes one or more guided mutable positions to test under-specification"


def build_configuration_catalogue() -> list[dict]:
    rows = []
    for seed0 in sorted(RQ3_CONFIGS.glob("*/*/seed0.json")):
        requirement, variant = seed0.parent.parent.name, seed0.parent.name
        config = json.loads(seed0.read_text(encoding="utf-8"))
        mutation = config["mutation"]
        positions = mutation["allowed_positions"]
        enabled = [name.removeprefix("enable_") for name, value in mutation.items()
                   if name.startswith("enable_") and value]
        metadata = config["replication_metadata"]
        originals = mutation["original_values"]
        rows.append({
            "requirement": requirement,
            "configuration": variant,
            "seeds_json": json.dumps(list(range(5))),
            "mutable_positions_json": json.dumps(positions),
            "historical_mutable_positions_json": json.dumps(metadata["historical_allowed_positions"]),
            "original_values_json": json.dumps(originals, sort_keys=True),
            "admissible_domains_json": json.dumps(mutation["allowed_changes"], sort_keys=True),
            "enabled_operators_json": json.dumps(enabled),
            "max_simultaneous_mutations": mutation["max_mutations"],
            "effective_max_simultaneous_mutations": metadata["effective_max_simultaneous_mutations"],
            "label_rationale": metadata["label_rationale"],
            "configuration_provenance": metadata["configuration_provenance"],
            "launch_template": metadata["launch_template"],
            "config_pattern": str(seed0.relative_to(ROOT)).replace("seed0.json", "seed{seed}.json"),
            "seed0_sha256": hashlib.sha256(seed0.read_bytes()).hexdigest(),
        })
    return rows


def latex_rows(table: list[dict]) -> str:
    groups = ["phi2", "phi3", "phi4", "AT53", "RR"]
    output = []
    for group_index, requirement in enumerate(groups):
        for row in (item for item in table if item["requirement"] == requirement):
            req = f"$\\phi_{requirement[-1]}$" if requirement.startswith("phi") else requirement
            runtime = f"${float(row['runtime_sec_mean']):.1f}\\pm {float(row['runtime_sec_sd']):.1f}$"
            if row["split"] == "Yes":
                size = f"${float(row['nodes_mean']):.1f}\\pm{float(row['nodes_sd']):.1f}$"
                if row["root_value_mean"]:
                    root = (f"{row['root_feature_mode']} @ ${float(row['root_value_mean']):.3f}"
                            f"\\pm {float(row['root_value_sd']):.3f}$")
                else:
                    root = f"{row['root_feature_mode']} @ {row['root_category_mode']}"
            else:
                size = root = "--"
            output.append(f"{req} & {row['configuration']} & {row['split']} & {runtime} & {size} & {root} \\\\")
        if group_index != len(groups) - 1:
            output.append("\\midrule")
    return "\n".join(output) + "\n"


def main() -> None:
    reconciliation = read(ROOT / "raw_results" / "normalized" / "rq3_seed_reconciliation.csv")
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    per_run = []
    required_raw = ("summary.json", "report.json", "timespan.json", "dataset_all.arff", "J48-data-100.out")
    for source in reconciliation:
        run_dir = (ROOT / "raw_results" / "rq3_sensitivity" / source["requirement"] /
                   source["configuration"] / f"seed{source['seed']}")
        missing = [name for name in required_raw if not (run_dir / name).is_file()]
        if missing:
            raise FileNotFoundError(f"{run_dir}: missing {missing}")
        summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
        full = next((item for item in summary.get("j48_runs", []) if item.get("qty") == 1.0), {})
        root = full.get("root_split", "")
        nodes, depth, leaves = tree_metrics((run_dir / "J48-data-100.out").read_text(encoding="utf-8"))
        row = {
            "requirement": source["requirement"],
            "configuration": source["configuration"],
            "seed": source["seed"],
            "status": source["status"],
            "split": "Yes" if root else "No",
            "runtime_sec": fmt(float(summary.get("runtime_sec", source["total_sec"]))),
            "nodes": nodes if root else "",
            "depth": depth if root else "",
            "leaves": leaves if root else "",
            "root_split": root,
            "raw_directory": str(run_dir.relative_to(ROOT)),
        }
        per_run.append(row)
        groups[(row["requirement"], row["configuration"])].append(row)
    write("rq3_per_run.csv", per_run)
    write("rq3_configuration_catalogue.csv", build_configuration_catalogue())

    req_names = {"AT53_AT119": "AT53"}
    table = []
    for (requirement, variant), run_rows in sorted(groups.items()):
        runtimes = [float(row["runtime_sec"]) for row in run_rows]
        nodes = [float(row["nodes"]) for row in run_rows if row["nodes"] != ""]
        depths = [float(row["depth"]) for row in run_rows if row["depth"] != ""]
        leaves = [float(row["leaves"]) for row in run_rows if row["leaves"] != ""]
        roots = [row["root_split"] for row in run_rows if row["root_split"]]
        features = [root.split()[0] for root in roots]
        mode = Counter(features).most_common(1)[0][0] if features else ""
        values, categories = [], []
        for root in roots:
            if root.split()[0] != mode:
                continue
            match = re.search(r"(?:<=|>=|<|>)\s*(-?[0-9.]+)", root)
            if match:
                value = float(match.group(1))
                if requirement == "phi3" and mode == "NUM1":
                    value /= 1_000_000
                values.append(value)
            else:
                match = re.search(r"(?:=|@)\s*([A-Za-z]+)", root)
                if match:
                    categories.append(match.group(1))
        runtime_mean, runtime_sd = mean_sd(runtimes)
        node_mean, node_sd = mean_sd(nodes)
        depth_mean, depth_sd = mean_sd(depths)
        leaves_mean, leaves_sd = mean_sd(leaves)
        root_mean, root_sd = mean_sd(values)
        informative = bool(roots)
        table.append({
            "requirement": req_names.get(requirement, requirement),
            "configuration": variant,
            "n_runs": len(run_rows),
            "n_informative": sum(row["status"] == "completed_informative" for row in run_rows),
            "split": "Yes" if informative else "No",
            "runtime_sec_mean": runtime_mean,
            "runtime_sec_sd": runtime_sd,
            "nodes_mean": node_mean,
            "nodes_sd": node_sd,
            "depth_mean": depth_mean,
            "depth_sd": depth_sd,
            "leaves_mean": leaves_mean,
            "leaves_sd": leaves_sd,
            "root_feature_mode": mode,
            "root_value_mean": root_mean,
            "root_value_sd": root_sd,
            "root_category_mode": Counter(categories).most_common(1)[0][0] if categories else "",
            "status_interpretation": "informative tree" if informative else "no informative tree; not convergence",
        })
    write("table9_authoritative.csv", table)
    (OUT / "table9_rows.tex").write_text(latex_rows(table), encoding="utf-8")

    def svg(name, title, items):
        width, height = 900, 40 + 26 * len(items)
        maximum = max(value for _, value in items) or 1
        lines = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" role="img"><title>{title}</title>', '<style>text{font:12px sans-serif}.b{fill:#3f6f8f}</style>']
        for index, (label, value) in enumerate(items):
            y = 24 + index * 26
            lines += [f'<text x="5" y="{y + 12}">{label}</text>', f'<rect class="b" x="120" y="{y}" width="{700 * value / maximum:.2f}" height="16"/>', f'<text x="825" y="{y + 12}" text-anchor="end">{value:.2f}</text>']
        lines.append("</svg>")
        (OUT / name).write_text("\n".join(lines) + "\n", encoding="utf-8")

    svg("rq3_runtime.svg", "RQ3 mean runtime (seconds)",
        [(row["requirement"] + "/" + row["configuration"], float(row["runtime_sec_mean"])) for row in table])
    print(f"wrote {len(per_run)} RQ3 seed rows, {len(table)} Table 9 rows, and configuration catalogue")


if __name__ == "__main__":
    main()
