#!/usr/bin/env python3
"""Apply the minimal ANTLR 4.7 import fix required by Python 3.13."""
from pathlib import Path

root = Path("/usr/local/lib/python3.13/site-packages/antlr4")
old = "from typing.io import TextIO"
new = "from typing import TextIO"
for name in ("Lexer.py", "Parser.py"):
    path = root / name
    text = path.read_text()
    if text.count(old) != 1:
        raise SystemExit(f"refusing unexpected {path}: expected one {old!r}")
    path.write_text(text.replace(old, new))
print("patched ANTLR 4.7 typing imports for Python 3.13")
