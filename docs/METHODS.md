# Methods

How the runs behind each result were selected, scored and timed. `README.md` maps the
paper's tables and figures to scripts and files.

## RQ1 and RQ2 runs

`experiments/registry.csv` defines exp1 to exp34 (requirement, mutable positions,
operators, admissible domains); each has ten seeds, and
`experiments/rq1_effectiveness/configs/` holds the 340 configurations.
`raw_results/normalized/experiment_seed_reconciliation.csv` lists the one run behind
each slot: 260 from campaign 20260803171759, 70 from the re-runs of campaign
20260812103600, and the 10 exp30 runs of campaign 20260903113951. The selection is
a fixed list (`raw_results/rq1_rq2/SELECTION.csv`) and does not depend on any result.
Of the 340 runs, 283 ended with an informative tree, 20 decided only one class, and 37
reached the 120-hour wall guard.

Every run had an Intel Xeon 6972P cluster node with 8 CPUs and 16 GB, as its
`archive/node_info.txt` records. Each run's `tool_commit` names the tool tree it ran;
`tool/PATCHES.md` relates those trees to `tool/`. A checker call is limited to
3,600 s.

## RQ1 scoring

Each scored seed is represented by the J48 tree relearned on all of the run's decided
samples: `dataset_qty_*_all.arff` without undecided rows, the full dataset (cut 1.0) and
Weka's default J48 settings. The trees are stored in `raw_results/rq1_rq2/exp*/seed*/regen/`;
deleting a `regen/` folder makes `rq1_effectiveness.py` relearn that tree, which needs
`WEKA_JAR`.

The tool tree and the expert evaluator are compared on a Cartesian grid over the mutated
parameters. A numeric axis takes the values `lo + (hi - lo) * i / 100` for `i = 0..100`;
a categorical axis has one cell per operator the configuration admits.
`analysis/rq1_grid_specifications.json` lists every axis. With satisfied as the positive
class, precision is TP/(TP+FP) and recall TP/(TP+FN); `analysis/rq1_per_seed_confusion.csv`
has the counts per seed. Each experiment reports the median over its scored seeds, each
rounded to one decimal, with the interquartile range computed by linear interpolation.
The Sec. V-C averages are taken over the medians of the 29 scored experiments. exp30 has
nine scored seeds and exp32 four; exp25 and exp26 decided one class in every seed, and
exp27, exp28 and exp31 reached the wall guard in every seed.

For 27 experiments, the expert evaluator is the expert's satisfied region, transcribed
from the original grid evaluators in `inputs/expert_trees/original_accuracy_scripts/`.
For exp2, exp14, exp16, exp18, exp20, exp33 and exp34 it is a rule over the trace, with
witnesses in `inputs/trace_witnesses/`. For exp33 and exp34 the rule is applied on the
configured mutation axes; the original `AccuracyRR.py` boxes are kept in the JSON.

The Appendix trees are chosen per experiment by `modal_trees.py`. Trees are grouped by
their ordered rule structure: split features, branch operators and categories, and leaf
labels, ignoring threshold values. From the largest group it picks the tree closest (L1)
to the group's median thresholds, then the lowest seed. `analysis/modal_trees/SELECTION_POLICY.json`
records the policy.

## RQ2 timing

`rq2_efficiency.py` reads each run's `report.json`, `timespan.json` and `summary.json` for
total, mutation, trace-checking and decision-tree time, checker calls and cache hits.
Table VIII reports the median over all ten seeds, counting a run stopped by the wall
guard with its elapsed time. A dagger marks an experiment with at least one such run, and
a double dagger one in which no seed produced a discriminating tree.

## RQ3 sensitivity

Five requirements (phi2, phi3, phi4, AT53, RR) in 28 configurations with five seeds each
give 140 runs in `raw_results/rq3_sensitivity/`. Each configuration in
`experiments/rq3_sensitivity/configs/` is the variant's launch template in
`inputs/launch_templates/sensitivity/` with the seed and GA settings recorded in the
run's `summary.json`. Positions follow the bundled tool's numbering: phi3's last numeric
position is 38 there and 40 in the template. Table IX reports the mean and standard
deviation over the five runs. "Split?" means at least one internal node, and the root
split is the most frequent one.

## Checker swap (Table X)

The RTAMT runs are in `raw_results/checker_swap_rtamt/runs/`: AT1 with seeds 1 to 6 and
CCx with seed 0, configured as in `experiments/checker_swap_rtamt/configs/` (AT1 with
the seed changed). Seed 1 is
the AT1 row of Table X, and all six give the 95.8 to 97.2% spread.
`experiments/checker_swap_rtamt/hardware.json` records the computer.

The Z3 rows are the original campaign's runs of the same requirement and search
configuration: AT1 is historical exp2 and CCx historical exp31. Their records are in
`z3_records/`, copied from `replication/results/raw/` of Diagnosis@05d0750. exp31 left
no tree, so its tree is relearned with J48 from that run's per-100 ARFF. Seconds per call
are trace-checking time over checker calls; diagnosis time is the sum of the three
phases.

DT accuracy is measured against the analytical ground truth. For AT1, the tree's satisfied
boxes are compared on the 101^3 grid over (lo, hi, threshold) with the rule "satisfied
iff threshold > v_speed(hi)". For CCx, the tree is a single threshold, compared with the
trace minimum of y5 - y4 (7.3894) as interval overlap on the mutation range [5, 10].

`scripts/rtamt_differential.py` rebuilds `at1_differential.json` in about four minutes.
It takes every distinct (lo, hi, threshold) AT1 candidate with a recorded Z3 verdict in
historical exp1 and exp2, 4,350 in all, and re-checks it with the RTAMT engine on the same
trace.

## TD-SB-TemPsy baseline

`inputs/baseline_td_sb_tempsy/` holds the 17 benchmark traces in the baseline's CSV log
format and the 13 requirements it can express as XMI specifications. AT6a, AT6b, AT6c
and AT6abc need Before/Between scopes; CC2 to CC5 need nested temporal operators and
have no XMI. `experiments/baseline_td_sb_tempsy/fetch_and_patch.sh TARGET` checks out the
tool (Apache-2.0) at `4107534` plus pull request 2 (`8efd304`). That pull request adds
the Complete-OCL import fix and a Docker environment with Eclipse Mars, Java 7, EMF 2.11
and OCL. Each pair is run with `TraceCheck` under a one-hour limit.
`raw_results/baseline_td_sb_tempsy/outcomes.csv` records the outcome and tool output of
every run, from which `baseline_outcomes.py` derives the counts and the diagnosis
witnesses of Table VII.

## Operator coverage

`experiments/operator_coverage/run_coverage.py` applies OP1 to OP15 and the
implies-operand swap OP4a as AST transformations to three small AT-derived requirements
in `requirements/`. It injects each mutant the way the search does and checks it with
the tool's trace checker. Every operator must yield a well-formed mutant with a SAT or
UNSAT verdict, and `expected_results.json` is the oracle. The search's own mutation
step implements numeric perturbation and relational, logical and quantifier flips, which
the benchmark exercises as OP2, OP4, OP5, OP11 and OP13. `build_matrix.py` cross-tabulates
implemented, fixture-covered, configured and sampled operators into `coverage_matrix.csv`.
It reads the archived generations, so it needs the Zenodo archive.

## Running-example fix

`experiments/implementation_fix/` holds the original controller (`sim_lc_faulty.py`), the
controller with the evasion flag reset (`sim_lc.py`) and the patch between them.
`reproduce.py` simulates four scenarios with each controller, keeps the eight traces in
`raw/`, and checks the four running-example requirements on each. Under the fix all 16
requirement/scenario pairs are satisfied, and phi3 in the retry scenario changes from
violated to satisfied. `test_verdict_matrix.py` and `test_fix_verification.py` check
both matrices.

## Re-running experiments

`./run experiments` lists the selected configurations without running them; filter with
`--study rq1_rq2|rq3_sensitivity`, `--ids exp1,exp2` and `--seeds 0`, or pick a
`--profile`, and add `--execute` to run. Runs are serial, seeds fix Python's and NumPy's
random generators, and outputs go to `raw_results/rerun/` without touching the archive.
Checker timeouts and wall-clock times depend on the hardware and its load.

## Environment

`environment/Dockerfile` (or `replication.def` for Apptainer) builds Python 3.13.5 with
the pins in `requirements-lock.txt`, Z3 4.15.4.0, OpenJDK 17, Weka 3.8.6 with Bounce 0.18,
RTAMT 0.3.5 and Graphviz. `environment/versions.json` records the tested image.
