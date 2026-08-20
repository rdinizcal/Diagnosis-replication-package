#!/usr/bin/env python3
"""Verify that MANIFEST.csv exactly covers the release payload and its hashes."""
from __future__ import annotations

import csv
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "MANIFEST.csv"
EXCLUDED_TOP_LEVEL = {".git", "Diagnosis", "ci-derived"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def payload_files() -> set[str]:
    result = set()
    for path in ROOT.rglob("*"):
        if not path.is_file() or path == MANIFEST:
            continue
        relative = path.relative_to(ROOT)
        if relative.parts and relative.parts[0] in EXCLUDED_TOP_LEVEL:
            continue
        if any(part in {"__pycache__", ".pytest_cache", ".venv"} for part in path.parts):
            continue
        result.add(relative.as_posix())
    return result


def main() -> None:
    with MANIFEST.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    paths = [row["artifact_path"] for row in rows]
    if len(paths) != len(set(paths)):
        raise SystemExit("manifest verification FAIL: duplicate artifact paths")
    listed, actual = set(paths), payload_files()
    missing = sorted(listed - actual)
    unlisted = sorted(actual - listed)
    mismatches = []
    for row in rows:
        path = ROOT / row["artifact_path"]
        if path.is_file() and sha256(path) != row["checksum_sha256"]:
            mismatches.append(row["artifact_path"])
    if missing or unlisted or mismatches:
        print("manifest verification FAIL")
        if missing:
            print("missing files:", *missing, sep="\n- ")
        if unlisted:
            print("unlisted files:", *unlisted, sep="\n- ")
        if mismatches:
            print("checksum mismatches:", *mismatches, sep="\n- ")
        raise SystemExit(1)
    print(f"manifest verification PASS: {len(rows)} files, SHA-256 exact")


if __name__ == "__main__":
    main()
