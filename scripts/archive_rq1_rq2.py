#!/usr/bin/env python3
"""Archive every retained artifact for the reconciled RQ1/RQ2 run selection.

This is a release-construction command.  It follows the 340-row reconciliation
allow-list and never chooses a run by recency, outcome, or file-system order.
Large generated checker programs and duplicate requirement sources are omitted:
their immutable inputs are in ``data/`` and every generated candidate is retained
in the generation dumps, ARFFs, and verdict cache.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
from pathlib import Path


PKG = Path(__file__).resolve().parents[1]
REPO = PKG.parent
WORKSPACE = REPO.parent
RECON = REPO / "reconciliation" / "generated" / "experiment_seed_reconciliation.csv"

TOP_LEVEL = {
    "hypot.txt", "inference_state.json", "inferred_labels.csv", "pr_growth.png",
    "report.json", "summary.json", "timespan.json", "worker.log",
    "verdict_cache.sqlite", "verdict_cache.sqlite-shm", "verdict_cache.sqlite-wal",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def copy_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def selected_run(row: dict[str, str]) -> Path:
    paths = [WORKSPACE / item for item in row["source_artifact_paths"].split(";") if item]
    runs = {path.parent for path in paths if path.name in {"summary.json", "report.json"}}
    if len(runs) != 1:
        raise RuntimeError(f"{row['canonical_experiment_id']}/seed{row['seed']}: run={runs}")
    run = runs.pop()
    if not run.is_dir():
        raise FileNotFoundError(run)
    return run


def result_mirror(row: dict[str, str], run: Path) -> Path | None:
    pattern = f"{row['canonical_experiment_id']}_*_s{row['seed']}"
    matches = [path / run.name for path in REPO.glob(f"results/{pattern}") if (path / run.name).is_dir()]
    if len(matches) > 1:
        raise RuntimeError(f"ambiguous result mirror for {pattern}/{run.name}: {matches}")
    return matches[0] if matches else None


def include(path: Path, run: Path) -> bool:
    relative = path.relative_to(run)
    if len(relative.parts) > 1:
        return relative.parts[0] in {"generations", "stopping_checks"}
    name = path.name
    return (
        name in TOP_LEVEL
        or name.startswith("J48-data-")
        or (name.startswith("dataset_qty_") and name.endswith(".arff"))
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="validate source inventory only")
    args = parser.parse_args()
    rows = read_rows(RECON)
    if len(rows) != 340:
        raise RuntimeError(f"expected 340 reconciled slots, found {len(rows)}")

    inventory: list[dict[str, object]] = []
    run_index: list[dict[str, object]] = []
    for row in rows:
        exp, seed = row["canonical_experiment_id"], row["seed"]
        run = selected_run(row)
        mirror = result_mirror(row, run)
        destination = PKG / "raw_results" / "rq1_rq2" / exp / f"seed{seed}" / "archive"
        sources = [path for path in run.rglob("*") if path.is_file() and include(path, run)]
        outer = run.parent
        for name in ("config.json", "node_info.txt"):
            path = outer / name
            if path.exists():
                sources.append(path)
        if mirror and (mirror / "regen").is_dir():
            sources.extend(path for path in (mirror / "regen").rglob("*") if path.is_file())

        evidence = {
            "effective_configuration": (outer / "config.json").exists(),
            "generated_candidates_generation_fitness": (run / "generations").is_dir(),
            "unique_formulas_verdict_duration": (run / "verdict_cache.sqlite").exists(),
            "cache_hit_miss_timeout_tiers": (run / "report.json").exists(),
            "stopping_history": (run / "summary.json").exists(),
            "j48_training_data": any(path.name.endswith(".arff") for path in sources),
            "raw_j48_output": any(path.name.endswith(".out") for path in sources),
            "evaluation_tree": bool(mirror and (mirror / "regen" / "J48-data-100.out").exists()),
            "run_log": (run / "worker.log").exists(),
            "scheduler_metadata": (outer / "node_info.txt").exists(),
        }
        metadata = {
            "canonical_experiment_id": exp,
            "seed": int(seed),
            "authoritative_campaign": row["source_batch"],
            "selection_policy": "reconciliation allow-list; independent of result quality/runtime",
            "archived_source_run": str(run.relative_to(WORKSPACE)),
            "status": row["status"],
            "stop_reason": row["stop_reason"],
            "censored": row["status"] == "timeout",
            "censoring_limit_sec": 432000 if row["status"] == "timeout" else None,
            "tool_commit_at_run": row["tool_commit"],
            "repository_head_at_reconciliation_not_run_commit": row["repository_head_at_reconciliation"],
            "evidence": evidence,
            "unavailable_evidence": {
                key: ("not present in the reconciliation-selected source run; preserve as unavailable, do not reconstruct from another campaign")
                for key, available in evidence.items() if not available
            },
            "omissions": {
                "temp.py": "duplicate generated checker program; formulas and verdicts retained in generations/cache",
                "run_requirement_copy": "duplicate of immutable requirement under data/requirements",
            },
        }

        if not args.check:
            for source in sorted(set(sources)):
                if source.parent == outer:
                    relative = Path(source.name)
                elif mirror and source.is_relative_to(mirror / "regen"):
                    relative = Path("evaluation_tree") / source.relative_to(mirror / "regen")
                else:
                    relative = source.relative_to(run)
                target = destination / relative
                copy_file(source, target)
                inventory.append({
                    "experiment_id": exp, "seed": seed,
                    "role": "evaluation_tree" if relative.parts[0] == "evaluation_tree" else "raw_run_evidence",
                    "path": str(target.relative_to(PKG)), "bytes": target.stat().st_size,
                    "sha256": sha256(target),
                    "source_path": str(source.relative_to(WORKSPACE)),
                })
            (destination / "metadata.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
            target = destination / "metadata.json"
            inventory.append({
                "experiment_id": exp, "seed": seed, "role": "archive_metadata",
                "path": str(target.relative_to(PKG)), "bytes": target.stat().st_size,
                "sha256": sha256(target), "source_path": "generated by archive_rq1_rq2.py",
            })
        run_index.append({"experiment_id": exp, "seed": seed, "status": row["status"], **evidence})

    missing = [item for item in run_index if not all(item[key] for key in (
        "effective_configuration", "generated_candidates_generation_fitness",
        "cache_hit_miss_timeout_tiers", "j48_training_data", "run_log", "scheduler_metadata"
    )) and item["status"] != "timeout"]
    if missing:
        raise RuntimeError(f"completed runs missing mandatory evidence: {missing[:3]}")
    if not args.check:
        for name, data in (("ARCHIVE_MANIFEST.csv", inventory), ("EVIDENCE_MATRIX.csv", run_index)):
            path = PKG / "raw_results" / "rq1_rq2" / name
            with path.open("w", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=list(data[0]))
                writer.writeheader(); writer.writerows(data)
    print(f"validated {len(rows)} authoritative RQ1/RQ2 slots; archived files={len(inventory)}")


if __name__ == "__main__":
    main()
