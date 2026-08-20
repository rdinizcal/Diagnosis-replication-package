#!/usr/bin/env python3
"""Archive the adopted RTAMT runs and analysis sources from the sibling checkout."""
from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKSPACE = ROOT.parents[1]
SOURCE = WORKSPACE / "code" / "Diagnosis"
RAW = ROOT / "raw_results" / "checker_swap_rtamt"

RUNS = {
    "AT1_seed1": SOURCE / "outputs/rtamt/AT1_s1/2026-08-13_10_27_54.084490",
    "CCX_seed0": SOURCE / "outputs/rtamt/CCX/2026-07-25_11_18_40.699423",
}


def main() -> None:
    for label, source in RUNS.items():
        if not source.is_dir():
            raise FileNotFoundError(source)
        destination = RAW / "runs" / label
        shutil.copytree(source, destination, dirs_exist_ok=True)
    report = SOURCE / "reports" / "rtamt_effectiveness"
    for source in report.iterdir():
        if source.is_file():
            shutil.copy2(source, RAW / source.name)
    shutil.copy2(SOURCE / "diagnosis/engines/rtamt_engine.py", RAW / "rtamt_engine.py")
    print("archived two adopted RTAMT run directories and analysis sources")


if __name__ == "__main__":
    main()
