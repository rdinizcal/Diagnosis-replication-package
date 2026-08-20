# RTAMT checker-swap study

`configs/` contains the executable AT1 and CCx configurations. The frozen
adapter is also preserved at `raw_results/checker_swap_rtamt/rtamt_engine.py`;
the dependency lock is RTAMT 0.3.5. `stl_translations.json` records the two
translations.

Run `archive_evidence.py` only while preparing the package from the sibling
Diagnosis checkout. Run `../../scripts/rtamt_auxiliary.py` to rebuild the
per-call timing, computed speedups, 4,350-row paired-verdict table, mismatch
classification, final-tree metrics, and agreement summary.

The RTAMT durations are raw measurements. The Z3 values (8.6 hours for AT1 and
4.4 days for CCx) survive only as contemporaneous author records; the original
timing logs were not retained. Accordingly, generated speedups are explicitly
classified as estimates. The authors confirmed that both runs used the current
computer; `hardware.json` records its specifications and that they were captured
after execution rather than embedded in the raw reports.
