#!/usr/bin/env python3
"""Re-check every recorded Z3 AT1 candidate with RTAMT and compare the verdicts.

The AT1 Z3 runs (historical exp1 and exp2) log each candidate's window bounds,
speed threshold and Z3 verdict per generation. Every distinct (lo, hi, thr) is
rendered with the tool's RTAMT template and evaluated on the same trace.
"""
from __future__ import annotations

import json
import logging
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw_results" / "checker_swap_rtamt"
sys.path.insert(0, str(ROOT / "tool"))

from diagnosis.engines.rtamt_engine import RtamtEngine  # noqa: E402

LINE = re.compile(r"^\d+: ForAll,(\d+),<=,t,And,t,<=,(\d+),v_speed\[.*\],<,([-\d.]+)\t\S+\t(True|False)$")


def recorded_z3() -> dict[tuple[int, int, float], set[str]]:
    verdicts: dict[tuple[int, int, float], set[str]] = {}
    for log in sorted((RAW / "z3_records").glob("AT1_exp*/[0-9]*.txt")):
        for line in log.read_text().splitlines():
            match = LINE.match(line)
            if match:
                key = (int(match[1]), int(match[2]), float(match[3]))
                verdicts.setdefault(key, set()).add("SATISFIED" if match[4] == "True" else "VIOLATED")
    return verdicts


def main() -> None:
    logging.disable(logging.WARNING)  # RTAMT warns once per spec about the implicit output variable
    engine = RtamtEngine(RAW / "runs" / "AT1_seed1" / "AT1_AT001.py")
    rows, conflicts = [], 0
    for (lo, hi, thr), z3 in sorted(recorded_z3().items()):
        conflicts += len(z3) > 1
        spec = engine.subject.build({4: lo, 8: hi, 11: thr}, engine._us_to_sample)
        rho = float("inf") if spec is None else engine._robustness(spec)
        verdict = "SATISFIED" if rho > 0 else "VIOLATED"
        rows.append({"lo": lo, "hi": hi, "thr": thr, "rho": rho, "rtamt": verdict,
                     "z3": "/".join(sorted(z3)), "match": z3 == {verdict}, "rho_zero": rho == 0})
    mismatches = [row for row in rows if not row["match"]]
    summary = {"distinct_triples": len(rows), "z3_source_conflicts": conflicts,
               "mismatches": len(mismatches), "rho_zero": sum(row["rho_zero"] for row in rows),
               "unexplained_mismatches": sum(not row["rho_zero"] for row in mismatches),
               "sat": sum(row["rtamt"] == "SATISFIED" for row in rows),
               "viol": sum(row["rtamt"] == "VIOLATED" for row in rows)}
    out = RAW / "at1_differential.json"
    out.write_text(json.dumps({"summary": summary, "rows": rows}, indent=2))
    print(f"AT1 differential: {summary['distinct_triples']} candidates, "
          f"{summary['mismatches']} mismatches, {summary['z3_source_conflicts']} Z3 conflicts")


if __name__ == "__main__":
    main()
