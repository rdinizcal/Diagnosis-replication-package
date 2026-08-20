#!/usr/bin/env python3
"""Regenerate pre/post traces, verdict matrix, and the controller patch."""
from __future__ import annotations

import csv
import difflib
import json
from pathlib import Path

from requirements import RequirementsConfig, evaluate_requirements_for_dataframe
from sim_lc import simulate_scenario as fixed
from sim_lc_faulty import simulate_scenario as faulty

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
SCENARIOS = ("normal", "smooth", "cut-in", "retry")


def main() -> None:
    RAW.mkdir(exist_ok=True)
    verdict_rows = []
    for scenario in SCENARIOS:
        for version, simulator in (("pre_fix", faulty), ("post_fix", fixed)):
            trace = simulator(scenario)
            trace.to_csv(RAW / f"{version}_{scenario}.csv", index=False)
            verdicts, details = evaluate_requirements_for_dataframe(trace, RequirementsConfig())
            (RAW / f"{version}_{scenario}_details.json").write_text(
                json.dumps(details, indent=2, default=str) + "\n", encoding="utf-8")
            for phi in ("ϕ1", "ϕ2", "ϕ3", "ϕ4"):
                verdict_rows.append({"scenario": scenario, "version": version,
                                     "requirement": phi, "satisfied": verdicts[phi]})
    with (RAW / "verdicts.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(verdict_rows[0]))
        writer.writeheader(); writer.writerows(verdict_rows)
    before = (HERE / "sim_lc_faulty.py").read_text().splitlines(keepends=True)
    after = (HERE / "sim_lc.py").read_text().splitlines(keepends=True)
    (HERE / "flag_rearming_and_controller_fixes.patch").write_text("".join(
        difflib.unified_diff(before, after, "sim_lc_faulty.py", "sim_lc.py")))
    retry = {(row["version"], row["requirement"]): row["satisfied"]
             for row in verdict_rows if row["scenario"] == "retry"}
    if retry[("pre_fix", "ϕ3")] is not False or retry[("post_fix", "ϕ3")] is not True:
        raise AssertionError("retry scenario does not demonstrate flag re-arming")
    if not all(row["satisfied"] for row in verdict_rows if row["version"] == "post_fix"):
        raise AssertionError("post-fix requirement failure")
    print("generated 8 traces; retry phi3 changes violated->satisfied; all post-fix verdicts pass")


if __name__ == "__main__":
    main()
