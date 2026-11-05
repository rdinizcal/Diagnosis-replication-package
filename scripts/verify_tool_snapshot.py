#!/usr/bin/env python3
"""Check tool/ against the Diagnosis source base it was taken from.

Needs the snapshot unpacked by scripts/fetch_archive.py (Diagnosis/ at 05d0750).
"""
from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = "05d0750395972662e9be0a1083b09a6dce7e3e65"
DOCUMENTED_PATCHES = {
    "diagnosis/mutation/api.py": "0c1cb011565e78e966d7dd489219c1e6bc7b5b7e4177a62326d9e92ab8af3151",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    upstream = ROOT / "Diagnosis"
    if not (upstream / "diagnosis").is_dir():
        raise SystemExit("Diagnosis/ not found; run scripts/fetch_archive.py first")
    mismatches, compared = [], 0
    for bundled in (ROOT / "tool").rglob("*"):
        if not bundled.is_file() or "__pycache__" in bundled.parts:
            continue
        relative = bundled.relative_to(ROOT / "tool")
        source = upstream / relative
        if source.is_file():
            compared += 1
            if sha256(bundled) != sha256(source) and DOCUMENTED_PATCHES.get(relative.as_posix()) != sha256(bundled):
                mismatches.append(relative.as_posix())
    if mismatches:
        raise SystemExit("tool/ differs from Diagnosis@" + EXPECTED[:7] + ": " + ", ".join(mismatches))
    print(f"tool/ PASS: {compared} files identical to Diagnosis@{EXPECTED[:7]} "
          f"except {len(DOCUMENTED_PATCHES)} documented patch")


if __name__ == "__main__":
    main()
