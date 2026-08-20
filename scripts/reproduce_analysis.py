#!/usr/bin/env python3
"""Analysis-only regeneration of every packaged RQ1/RQ2 table and figure."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def main() -> None:
    for script in ("build_expert_references.py", "rq1_effectiveness.py", "rq2_efficiency.py",
                   "modal_trees.py", "validate_rq3_configs.py", "rq3_auxiliary.py",
                   "rtamt_auxiliary.py"):
        subprocess.run([sys.executable, str(SCRIPTS / script)], cwd=ROOT, check=True)
    subprocess.run(
        [sys.executable, str(ROOT / "experiments" / "ms_sensitivity" / "generate_table.py")],
        cwd=ROOT,
        check=True,
    )
    print("analysis regeneration PASS")


if __name__ == "__main__": main()
