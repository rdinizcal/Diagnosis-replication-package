#!/usr/bin/env python3
"""Portable, offline release checks that complement empirical verification."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_TOP_LEVEL = {".git", "Diagnosis", "ci-derived"}
TEXT_SUFFIXES = {".cfg", ".csv", ".json", ".md", ".py", ".sh", ".tex", ".toml", ".txt", ".yaml", ".yml"}
DEVELOPER_PATH = re.compile(r"(?:/Users/[^/]+/|/home/[^/]+/|[A-Za-z]:\\\\Users\\\\[^\\\\]+\\\\)")
# Run summaries record the output directory of the machine that produced them.
ARCHIVED_PATH_EXCEPTIONS = {
    f"raw_results/checker_swap_rtamt/runs/{run}/summary.json"
    for run in ("CCX_seed0", *(f"AT1_seed{seed}" for seed in range(1, 7)))
}
SECRET_PATTERNS = {
    "AWS access key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "GitHub token": re.compile(r"gh[opurs]_[A-Za-z0-9_]{30,}"),
}


def main() -> None:
    errors: list[str] = []
    for path in ROOT.rglob("*"):
        relative_path = path.relative_to(ROOT)
        if relative_path.parts and relative_path.parts[0] in EXCLUDED_TOP_LEVEL:
            continue
        if path.is_symlink():
            errors.append(f"symlink not allowed in archive: {relative_path}")
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        relative = relative_path.as_posix()
        if DEVELOPER_PATH.search(text) and relative not in ARCHIVED_PATH_EXCEPTIONS and path.name != "release_audit.py":
            errors.append(f"active absolute developer path: {relative}")
        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(text):
                errors.append(f"possible {label}: {path.relative_to(ROOT)}")
    registry = ROOT / "experiments" / "registry.csv"
    ids = re.findall(r"(?:^|\n)(exp\d+),", registry.read_text(encoding="utf-8"))
    if ids != [f"exp{i}" for i in range(1, 35)]:
        errors.append("canonical registry is not exactly exp1..exp34")
    versions = json.loads((ROOT / "environment" / "versions.json").read_text())
    if not versions.get("container_base", "").startswith("python:3.13.5-slim-bookworm@sha256:"):
        errors.append("container base is not digest-pinned")
    for required in ("README.md", "CITATION.cff", "LICENSE", ".zenodo.json"):
        if not (ROOT / required).is_file():
            errors.append(f"missing release metadata: {required}")
    if errors:
        print("release audit FAIL")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print("release audit PASS: active paths, secrets, IDs, environment pin, and publication files")
    print(f"exempt: {len(ARCHIVED_PATH_EXCEPTIONS)} archived RTAMT run summaries that record their output directory")


if __name__ == "__main__":
    main()
