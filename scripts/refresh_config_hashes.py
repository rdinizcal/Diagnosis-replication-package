#!/usr/bin/env python3
"""Refresh hashes after an intentional, reviewed configuration migration."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(path: Path) -> str:
    data = json.loads(path.read_text())
    return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def refresh(name: str, canonical_column: bool = False) -> None:
    path = ROOT / "experiments" / name
    with path.open(newline="") as stream: rows = list(csv.DictReader(stream))
    for row in rows:
        config = ROOT / row["path"]
        row["sha256"] = digest(config)
        if canonical_column:
            row["canonical_json_sha256"] = canonical(config)
            if row["study_id"] == "rq3_sensitivity":
                row["provenance"] = "reconstructed_current_snapshot_from_archived_rq3_evidence"
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)


refresh("configuration_hashes.csv", canonical_column=True)
refresh("auxiliary_configuration_hashes.csv")
print("refreshed primary and auxiliary configuration hashes")
