#!/usr/bin/env python3
"""Regenerate every table, figure and number of the paper from the packaged evidence."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def main() -> None:
    for script in ("build_expert_references.py", "rq1_effectiveness.py", "rq2_efficiency.py",
                   "modal_trees.py", "validate_rq3_configs.py", "rq3_auxiliary.py",
                   "rtamt_auxiliary.py",
                   "baseline_outcomes.py", "fig_boxplot.py", "trace_stats.py"):
        subprocess.run([sys.executable, str(SCRIPTS / script)], cwd=ROOT, check=True)
    fix = ROOT / "experiments" / "implementation_fix"
    subprocess.run([sys.executable, "reproduce.py"], cwd=fix, check=True)
    subprocess.run([sys.executable, str(ROOT / "experiments" / "operator_coverage" / "run_coverage.py")],
                   cwd=ROOT, check=True)
    print("analysis regeneration PASS")


if __name__ == "__main__": main()
