#!/usr/bin/env python3
"""Archive the exact pre/post controller and verification tests."""
from __future__ import annotations

import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parents[3] / "running_example"
FILES = ("sim_lc_faulty.py", "sim_lc.py", "requirements.py", "sim_config.py",
         "test_verdict_matrix.py", "test_fix_verification.py")

for name in FILES:
    shutil.copy2(SOURCE / name, HERE / name)
print(f"archived {len(FILES)} exact running-example sources/tests")
