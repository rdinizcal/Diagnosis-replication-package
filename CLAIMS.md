# Claim-to-evidence map

This map identifies the empirical results supported by the package and connects
each result to a generating command, archived evidence, regenerated output, and
an executable verification. It describes the artifact's evidence chain; it is
not a version audit of the manuscript.

| ID | Supported result | Generating command | Raw evidence | Derived output | Verification |
|---|---|---|---|---|---|
| C-RQ1 | The archived campaign accounts for 340 seed slots. Of these, 284 are scored and 29 experiments have scored medians; aggregate precision and recall are 98.8% and 97.5%. | `./reproduce-analysis` | `raw_results/rq1_rq2/`; `inputs/expert_trees/`; `experiments/registry.csv` | `rq1_per_seed_confusion.csv`; `rq1_aggregate.json`; `appendix_precision_recall_authoritative.csv`; `rq1_grid_specifications.json` | `python3 scripts/verify.py`; `python3 -m pytest -q tests/test_rq1_rq2.py` |
| C-MODE | All 340 tree slots are accounted for and 31 modal tree selections are generated. Censored or one-class outcomes retain an explicit status. | `./reproduce-analysis` (`scripts/modal_trees.py`) | Per-seed J48 and ARFF records under `raw_results/rq1_rq2/` | `modal_tree_selection.csv`; `modal_trees/`; `tool_tree_inventory.csv` | `python3 scripts/verify.py` |
| C-RQ2 | The efficiency analysis regenerates 340 per-run rows, including 36 censored slots, and the authoritative summary table. | `./reproduce-analysis` | Run reports, timespans, logs, caches, and scheduler records under `raw_results/rq1_rq2/`; `EVIDENCE_MATRIX.csv` | `rq2_per_run.csv`; `rq2_statistics.csv`; `table8_authoritative.csv`; `rq2_runtime.svg` | `python3 scripts/verify.py`; `python3 -m pytest -q tests/test_rq1_rq2.py` |
| C-RQ3 | The sensitivity analysis regenerates 140 archived rows, 28 configurations in the summary, and the authoritative table. | `./reproduce-analysis` (`validate_rq3_configs.py`, `rq3_auxiliary.py`) | `raw_results/rq3_sensitivity/`; `raw_results/normalized/rq3_seed_reconciliation.csv` | `rq3_per_run.csv`; `rq3_configuration_catalogue.csv`; `table9_authoritative.csv`; `rq3_runtime.svg` | `python3 scripts/verify_auxiliaries.py` |
| C-RTAMT | The checker-swap auxiliary analysis accounts for 4,350 paired verdicts with matching classifications and two packaged RTAMT timing measurements. | `python3 scripts/rtamt_auxiliary.py` | `raw_results/checker_swap_rtamt/` | `rtamt_checker_authoritative.csv`; `rtamt_paired_verdicts.csv`; `rtamt_speedups.csv` | `python3 scripts/verify_auxiliaries.py` |
| C-OP | OP1--OP15 and OP4a each produce at least one parser-valid, injected, solver-evaluable mutant in the coverage fixtures. | `python3 experiments/operator_coverage/run_coverage.py` | `experiments/operator_coverage/requirements/`; expected source, AST, and verdict fixtures | `actual_results.json`; `operator_coverage.csv`; `coverage_matrix.csv` | The command compares actual results with `expected_results.json`; CI also runs `tests/test_operator_coverage.py`. |
| C-FIX | The implementation-fix regression reproduces its 32-verdict matrix and satisfies all post-fix checks. | `cd experiments/implementation_fix && python3 reproduce.py` | Faulty and fixed controllers, patch, eight traces, and `raw/verdicts.csv` | Reproduced verdict matrix | `python3 -m pytest -q experiments/implementation_fix/test_fix_verification.py experiments/implementation_fix/test_verdict_matrix.py` |

Precision is `TP/(TP+FP)` and recall is `TP/(TP+FN)` on the deterministic
Cartesian grid, with satisfied as the positive class. Numeric dimensions have
101 values; discrete dimensions enumerate their configured domain. Undecided
checker calls do not enter tree-to-tree classification. `exp32` has four scored
seeds, and timeouts remain classified as censored rather than convergence.

The external-baseline and MS-sensitivity directories are supporting inventories
and executable configuration material. They are outside the core RQ1--RQ3
results asserted above, and no derived empirical claim is made for an entry
whose status indicates that a measurement is unavailable.
