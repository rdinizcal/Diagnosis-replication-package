# RQ1 effectiveness and RQ2 efficiency

## Authoritative population

`experiments/registry.csv` declares exp1--exp34 and seeds 0--9.
`raw_results/normalized/experiment_seed_reconciliation.csv` selects exactly one
source run for each of the 340 slots. The outcome population is 284 completed
informative runs, 20 completed one-class/degenerate runs, and 36 runs censored at
the 120-hour wall guard. Selection never depends on the measured result.

## RQ1

`rq1_effectiveness.py` evaluates each available informative tool tree and expert
tree on the same Cartesian product. Every numeric axis is
`lo + (hi-lo)*i/100`, `i=0..100` (101 values including endpoints). Every
categorical axis has one cell for every operator admitted by the configuration.
`rq1_grid_specifications.json` stores all generated values and per-axis SHA-256.
The output records TP/TN/FP/FN and seed-level precision/recall. Checker-level
undecided candidates are missing training labels and are explicitly excluded;
they are not a third prediction class.

The manuscript statistic first rounds each seed precision/recall to one decimal,
takes the per-experiment median, and then reports mean/minimum/maximum/sample SD
across the 29 scored configurations. Twenty-eight use ten seeds; exp32 uses its
four completed informative seeds and is provisional.

Tool trees are grouped for modal selection by the complete ordered normalized
rule topology: split features, branch operators/categories, and leaf labels are
retained; numeric threshold values and training counts are abstracted. This is
neither a root-only mode nor an exact-numeric-tree mode. Tied modal signatures
use lexicographic order. The representative minimizes normalized L1 distance to
the modal group's component-wise median thresholds, then uses the lowest seed.
The executable policy is also written to `modal_trees/SELECTION_POLICY.json`.

## RQ2

`rq2_efficiency.py` extracts total, mutation, checker, and decision-tree time;
checker/unique calls; cache hits; timeout escalations; undecided calls; stop
reason; and scheduler resources for every slot. It emits per-run values plus
median, mean, and interpolation-based IQR per experiment. Table 8 uses the
median across all ten declared slots and retains observed elapsed values for
censored runs. It never treats a timeout as convergence.

Statuses, formulas, verdicts, counts, trees, and confusion matrices are logical
reproduction targets. Wall-clock values are hardware/scheduler sensitive. The
original Xeon node/allocation metadata is retained per run. A performance rerun
is considered consistent within ±20% for experiment-level median phase/total
times only when CPU model, allocation, tool/checker versions, and exclusive
scheduling match; larger deviation triggers investigation but does not alter a
logical reproduction.

## Generated results

`appendix_precision_recall_rows.tex` and `table8_rows.tex` are generated from
the packaged data. Expert and modal tool tree manifests contain exact DOT-to-SVG/PDF
commands. `./verify` validates all counts, formulas, file coverage, medians, and
frozen paper-facing CSV oracles.
