#!/usr/bin/env python3
"""Verify the pinned Diagnosis provenance submodule and bundled source subset."""
from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = "05d0750395972662e9be0a1083b09a6dce7e3e65"
DOCUMENTED_PATCHES = {
    "diagnosis/mutation/api.py": "0c1cb011565e78e966d7dd489219c1e6bc7b5b7e4177a62326d9e92ab8af3151",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    staged = subprocess.check_output(
        ["git", "ls-files", "--stage", "Diagnosis"], cwd=ROOT, text=True
    ).strip().split()
    if len(staged) < 2 or staged[0] != "160000" or staged[1] != EXPECTED:
        raise SystemExit(f"Diagnosis gitlink mismatch: expected {EXPECTED}")

    upstream = ROOT / "Diagnosis"
    if upstream.is_dir() and (upstream / "diagnosis").is_dir():
        head = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=upstream, text=True
        ).strip()
        if head != EXPECTED:
            raise SystemExit(f"initialized Diagnosis HEAD mismatch: {head}")
        mismatches = []
        for bundled in (ROOT / "tool").rglob("*"):
            if not bundled.is_file():
                continue
            relative = bundled.relative_to(ROOT / "tool")
            source = upstream / relative
            if source.is_file() and sha256(bundled) != sha256(source):
                expected_patch = DOCUMENTED_PATCHES.get(relative.as_posix())
                if expected_patch != sha256(bundled):
                    mismatches.append(relative.as_posix())
        if mismatches:
            raise SystemExit("bundled/upstream mismatches: " + ", ".join(mismatches))

    print(
        f"Diagnosis submodule PASS: {EXPECTED}; "
        f"{len(DOCUMENTED_PATCHES)} documented bundled patch"
    )


if __name__ == "__main__":
    main()
