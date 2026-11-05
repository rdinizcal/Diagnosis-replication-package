#!/usr/bin/env python3
"""Materialize every tool tree and select one deterministic modal tree per experiment."""
from __future__ import annotations

import csv
import hashlib
import json
import os
import statistics
import subprocess
from collections import Counter, defaultdict
from pathlib import Path

from j48_tree import normalized_signature, numeric_thresholds, parse, to_dot

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw_results" / "rq1_rq2"
OUT = ROOT / "analysis" / "tool_trees"
MODAL = ROOT / "analysis" / "modal_trees"


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as stream: return list(csv.DictReader(stream))


def final_tree(archive: Path) -> Path | None:
    evaluation = archive / "evaluation_tree" / "J48-data-100.out"
    if evaluation.exists(): return evaluation
    candidate = archive / "J48-data-100.out"
    return candidate if candidate.exists() else None


def arff_label(archive: Path) -> str:
    labels = set()
    for path in archive.glob("dataset_qty_*_all.arff"):
        in_data = False
        for line in path.read_text(errors="replace").splitlines():
            if line.strip().lower() == "@data": in_data = True; continue
            if in_data and line.strip() and not line.lstrip().startswith("%"):
                labels.add(line.rsplit(",", 1)[-1].strip().upper())
    decided = sorted(labels & {"TRUE", "FALSE", "SAT", "UNSAT", "SATISFIED", "VIOLATED"})
    return decided[0] if len(decided) == 1 else "UNAVAILABLE"


# A fixed timestamp keeps the PDFs byte-identical across regenerations.
REPRODUCIBLE = {**os.environ, "SOURCE_DATE_EPOCH": "0"}


def render(dot_path: Path) -> tuple[Path, Path]:
    svg, pdf = dot_path.with_suffix(".svg"), dot_path.with_suffix(".pdf")
    subprocess.run(["dot", "-Tsvg", str(dot_path), "-o", str(svg)], check=True)
    subprocess.run(["dot", "-Tpdf", str(dot_path), "-o", str(pdf)], check=True, env=REPRODUCIBLE)
    return svg, pdf


def main() -> None:
    registry = read_rows(ROOT / "raw_results" / "normalized" / "experiment_seed_reconciliation.csv")
    grouped, inventory = defaultdict(list), []
    OUT.mkdir(parents=True, exist_ok=True); MODAL.mkdir(parents=True, exist_ok=True)
    for row in registry:
        exp, seed, status = row["canonical_experiment_id"], int(row["seed"]), row["status"]
        archive = RAW / exp / f"seed{seed}" / "archive"
        destination = OUT / exp / f"seed{seed}"; destination.mkdir(parents=True, exist_ok=True)
        source = final_tree(archive); tree = parse(source.read_text(errors="replace")) if source else None
        tree_status = "available"
        if tree is None and status == "completed_degenerate":
            tree = {"root": 0, "nodes": [{"id": 0, "kind": "leaf", "label": arff_label(archive)}], "edges": []}
            tree_status = "degenerate_one_class_reconstructed_from_arff"
        elif tree is None:
            tree_status = "unavailable_run_censored_before_final_tree"
        payload = {"schema_version": 1, "experiment_id": exp, "seed": seed, "run_status": status,
                   "tree_status": tree_status, "source_j48_output": str(source.relative_to(ROOT)) if source else None,
                   "tree": tree}
        json_path = destination / "tool_tree.json"
        dot_path = destination / "tool_tree.dot"
        svg_path = pdf_path = None
        if tree:
            signature = normalized_signature(tree)
            payload["normalized_rule_signature"] = signature
            payload["normalized_rule_signature_sha256"] = hashlib.sha256(signature.encode()).hexdigest()
            payload["numeric_thresholds"] = numeric_thresholds(tree)
            dot_path.write_text(to_dot(tree, f"{exp} seed {seed} tool tree"))
            svg_path, pdf_path = render(dot_path)
            grouped[exp].append({"seed": seed, "tree": tree, "signature": signature,
                                 "thresholds": numeric_thresholds(tree), "json": json_path,
                                 "dot": dot_path, "svg": svg_path, "pdf": pdf_path})
        json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        inventory.append({"experiment_id": exp, "seed": seed, "run_status": status,
                          "tree_status": tree_status, "json": str(json_path.relative_to(ROOT)),
                          "dot": str(dot_path.relative_to(ROOT)) if tree else "",
                          "svg": str(svg_path.relative_to(ROOT)) if svg_path else "",
                          "pdf": str(pdf_path.relative_to(ROOT)) if pdf_path else ""})

    selections, appendix = [], []
    policy = {
        "grouping_basis": "full normalized rule topology",
        "normalization": "ordered split/branch/leaf structure and feature/operator/category are retained; training counts and numeric threshold values are abstracted",
        "not_used_as_mode": ["root feature alone", "unnormalized full numeric tree"],
        "mode_tie_break": "lexicographically smallest normalized signature",
        "representative": "minimum normalized L1 distance of thresholds to component-wise modal-group medians; then lowest seed",
        "missing_policy": "censored runs without a final tree are inventoried but excluded; degenerate one-class trees participate as a leaf topology",
    }
    (MODAL / "SELECTION_POLICY.json").write_text(json.dumps(policy, indent=2, sort_keys=True) + "\n")
    for index in range(1, 35):
        exp, candidates = f"exp{index}", grouped[f"exp{index}"]
        counts = Counter(item["signature"] for item in candidates)
        if not counts:
            selections.append({"experiment_id": exp, "trees_available": 0, "modal_count": 0,
                               "representative_seed": "", "signature_sha256": "", "status": "no_final_tree",
                               "json": "", "dot": "", "svg": "", "pdf": ""})
            continue
        maximum = max(counts.values())
        signature = min(sig for sig, count in counts.items() if count == maximum)
        modal = [item for item in candidates if item["signature"] == signature]
        lengths = {len(item["thresholds"]) for item in modal}
        if len(lengths) == 1 and next(iter(lengths)):
            medians = [statistics.median(values) for values in zip(*(item["thresholds"] for item in modal))]
            def distance(item):
                return sum(abs(value-med) / max(1.0, abs(med)) for value, med in zip(item["thresholds"], medians))
        else:
            def distance(item): return 0.0
        representative = min(modal, key=lambda item: (distance(item), item["seed"]))
        stem = MODAL / f"{exp}_tool"
        stem.with_suffix(".json").write_text(representative["json"].read_text())
        stem.with_suffix(".dot").write_text(to_dot(representative["tree"], f"{exp} modal tool tree (seed {representative['seed']})"))
        svg, pdf = render(stem.with_suffix(".dot"))
        digest = hashlib.sha256(signature.encode()).hexdigest()
        selections.append({"experiment_id": exp, "trees_available": len(candidates), "modal_count": maximum,
                           "representative_seed": representative["seed"], "signature_sha256": digest,
                           "status": "selected_degenerate" if not representative["tree"]["edges"] else "selected_informative",
                           "json": str(stem.with_suffix('.json').relative_to(ROOT)),
                           "dot": str(stem.with_suffix('.dot').relative_to(ROOT)),
                           "svg": str(svg.relative_to(ROOT)), "pdf": str(pdf.relative_to(ROOT))})
        appendix.append({"experiment_id": exp, "kind": "tool_modal", "seed": representative["seed"],
                         "dot": str(stem.with_suffix('.dot').relative_to(ROOT)), "svg": str(svg.relative_to(ROOT)),
                         "pdf": str(pdf.relative_to(ROOT)),
                         "svg_command": f"dot -Tsvg {stem.with_suffix('.dot').relative_to(ROOT)} -o {svg.relative_to(ROOT)}",
                         "pdf_command": f"dot -Tpdf {stem.with_suffix('.dot').relative_to(ROOT)} -o {pdf.relative_to(ROOT)}"})
    for name, data in (("tool_tree_inventory.csv", inventory), ("modal_tree_selection.csv", selections),
                       ("appendix_tool_tree_manifest.csv", appendix)):
        with (ROOT / "analysis" / name).open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(data[0])); writer.writeheader(); writer.writerows(data)
    print(f"tool trees: {len(inventory)} run slots; {sum(bool(r['representative_seed'] != '') for r in selections)} modal selections")


if __name__ == "__main__": main()
