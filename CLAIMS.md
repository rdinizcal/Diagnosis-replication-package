# Claims and evidence

The manuscript evaluated on 2026-08-20 was
`_TSE__Search_based_Trace_Diagnostic_for_Cyber_Physical_Systems.pdf`, 22 pages,
SHA-256 `6db3ee8b1e5116334e89396b7672f5462c791ba1b1d1e6b10d2cef03812f961e`.
It is not included in this artifact. Page references below refer to that exact
PDF; a different manuscript version requires a new audit.

| ID | Paper location | Generating command | Raw evidence | Derived output | Audit verdict |
|---|---|---|---|---|---|
| C-RQ1 | §5.4 “RQ1 – Effectiveness,” pp. 15–16; Fig. 9; experiment definitions in Table 6, p. 13 | `./reproduce-analysis`; `python3 scripts/verify.py` | `raw_results/rq1_rq2/`; `references/expert_trees/`; `experiments/registry.csv` | `rq1_per_seed_confusion.csv`; `rq1_aggregate.json`; `appendix_precision_recall_authoritative.csv`; `rq1_grid_specifications.json` | **PASS for archived/computational reproduction.** 340 slots are accounted for, 284 seeds are scored, 29 experiments have scored medians, and the reported 98.8%/97.5% aggregates regenerate. This does not rerun all checker calls. |
| C-MODE | Appendix A is referenced on p. 16 and citation [30] on p. 21; the external appendix itself is not bundled | `./reproduce-analysis` (`scripts/modal_trees.py`) | Per-seed J48/ARFF evidence under `raw_results/rq1_rq2/` | `modal_tree_selection.csv`; `modal_trees/`; `tool_tree_inventory.csv` | **PARTIAL.** 31 modal selections regenerate; three experiments have no selectable completed tree. Equality with the externally hosted paper appendix is unverifiable from this package. |
| C-RQ2 | §5.4 “RQ2 – Efficiency,” pp. 16–17; Table 8, p. 17 | `./reproduce-analysis`; `python3 scripts/verify.py` | 340 run reports, timespans, logs, caches, and scheduler records under `raw_results/rq1_rq2/`; `EVIDENCE_MATRIX.csv` | `rq2_per_run.csv`; `rq2_statistics.csv`; `table8_authoritative.csv`; `rq2_runtime.svg` | **PASS for archived/computational reproduction.** Table 8 and 36 censored runs regenerate. Timing is not independently rerun and the historical tool/image identity is unrecorded. |
| C-RQ3 | §5.4 “RQ3 – Cost–Effectiveness,” pp. 17–18; Table 9, p. 17 | `./reproduce-analysis` (`validate_rq3_configs.py`, `rq3_auxiliary.py`) | 140 directories under `raw_results/rq3_sensitivity/`; `raw_results/normalized/rq3_seed_reconciliation.csv` | `rq3_per_run.csv`; `rq3_configuration_catalogue.csv`; `table9_authoritative.csv`; `rq3_runtime.svg` | **PARTIAL.** All 140 archived rows and Table 9 regenerate, but the 140 executable configs are evidence-based reconstructions, not retained historical effective JSON; AT53 used legacy binder-only semantics. |
| C-RTAMT | No RTAMT result appears in the evaluated manuscript PDF | `python3 scripts/rtamt_auxiliary.py` | `raw_results/checker_swap_rtamt/`; two RTAMT reports and differential records | `rtamt_checker_authoritative.csv`; `rtamt_paired_verdicts.csv`; `rtamt_speedups.csv` | **UNVERIFIABLE AS A PAPER CLAIM.** The package reproduces 4,350 matching paired verdicts and two RTAMT measurements. Z3 speedups remain estimates because raw Z3 timing logs are absent. |
| C-OP | Mutation operators in Table 1, p. 7; coverage limitation discussion, p. 10; experiment operator use in Table 6, p. 13 | `python3 experiments/operator_coverage/run_coverage.py` | `experiments/operator_coverage/requirements/`; expected source/AST/verdict fixtures | `actual_results.json`; `operator_coverage.csv`; `coverage_matrix.csv` | **PASS for executable operator coverage.** OP1–OP15 plus OP4a each produced at least one parser-valid, injected, solver-evaluable mutant. This is coverage, not empirical effectiveness. |
| C-BASE | §5.2, pp. 11–14; Table 7, p. 14; RQ2 context, p. 16; discussion p. 18; conclusion p. 20 | No generating command exists for the reported values. `fetch_and_patch.sh` only retrieves the pinned upstream tool | `experiments/baseline_td_sb_tempsy/evidence_status.csv` records 17/17 cases as unverified; converted inputs, stdout/stderr, timeout/crash logs, and timings are absent | None | **FAIL.** The evaluated paper retains empirical baseline claims, directly contradicting the package statement that no such claim is retained. No supported baseline case can be reproduced. |
| C-MS | No current-pipeline MS100/MS1000 study appears in the evaluated manuscript PDF | `python3 experiments/ms_sensitivity/generate_table.py` | No run outputs; 40 materialized configs under `experiments/ms_sensitivity/configs/` | `ms_sensitivity_comparison.csv` with blank metrics and `not_executed` status | **UNVERIFIABLE / NOT EXECUTED.** Configuration materialization is checkable; no empirical result exists. |
| C-FIX | No flag re-arming experiment appears in the evaluated manuscript PDF | `cd experiments/implementation_fix && python3 reproduce.py`; associated pytest files | Exact faulty/fixed controllers, patch, eight traces, and `raw/verdicts.csv` | Reproduced verdict matrix | **UNVERIFIABLE AS A PAPER CLAIM; PASS AS PACKAGE-ONLY REGRESSION.** The 32 verdicts and post-fix checks execute, but there is no paper location to validate. |

Precision is `TP/(TP+FP)` and recall is `TP/(TP+FN)` on the common deterministic
Cartesian grid, with “satisfied” as the positive class. Numeric dimensions have
101 values; discrete dimensions enumerate their configured domain. Undecided
checker calls do not enter tree-to-tree classification. `exp32` is provisional
(four scored seeds); no timeout is relabeled as convergence.

The package does not establish bit-identical timing, the archived tool commit or
image, exact RQ3 historical configurations, measured Z3/RTAMT speedups, the
paper's baseline results, or a completed MS-sensitivity campaign. Strict
`./verify` must remain nonzero until the missing raw evidence is supplied and
the manuscript/package contradiction is resolved.
