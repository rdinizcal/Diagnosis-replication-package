# Replication package: Search-based Trace Diagnostic for Cyber-Physical Systems

This repository holds the tool, inputs, raw results and analysis behind the paper's
three research questions: effectiveness (RQ1), efficiency (RQ2) and sensitivity to the
mutation space (RQ3), plus the studies in its Discussion. One command derives the
paper's tables, figures and numbers from the files here.

## Three commands

```sh
./run smoke         # about 10 s: parser, mutation, Z3 check, verdict cache, J48
./run results       # about 1 min: regenerate every paper result into analysis/, then verify it
./run experiments   # list the 480 run configurations; add --profile at1 --execute to run one
```

The simplest environment is the container, which pins every dependency:

```sh
docker build -t diagnosis-replication -f environment/Dockerfile .
docker run --rm diagnosis-replication ./run results
```

Without Docker you need Python 3.13, Java 17, Graphviz, the packages in
`environment/requirements-lock.txt` and `environment/rtamt-compat-lock.txt`, and
`pip install -e tool`. The smoke test and experiment runs also need Weka; set `WEKA_JAR` to
`weka.jar:bounce.jar`.

A full RQ1/RQ2 run of one configuration and seed can take up to five days of checker
time; the paper's campaign ran 340 of them on a cluster. `./run experiments --profile`
offers three representative single runs: `at1` (exp1), `multi-token` (exp2) and
`discrete-operator` (exp30).

## Where each result comes from

`./run results` runs the scripts below. Outputs are in `analysis/` unless noted.

| Paper | Script | Output | Evidence |
|---|---|---|---|
| RQ1 precision and recall per experiment (Appendix table) and their averages in Sec. V-C | `rq1_effectiveness.py` | `appendix_precision_recall_authoritative.csv`, `rq1_aggregate.json`, `rq1_per_seed_confusion.csv` | `raw_results/rq1_rq2/exp*/seed*/regen/`, `inputs/expert_trees/` |
| Fig. 12, precision/recall boxplot | `fig_boxplot.py` | `rq1_boxplot.pdf` | as above |
| Appendix decision trees | `modal_trees.py` | `modal_trees/`, `tool_trees/` | `raw_results/rq1_rq2/` |
| Table VIII, runtimes | `rq2_efficiency.py` | `table8_authoritative.csv`, `rq2_per_run.csv` | `raw_results/rq1_rq2/` |
| Table IX, sensitivity | `rq3_auxiliary.py` | `table9_authoritative.csv`, `rq3_per_run.csv` | `raw_results/rq3_sensitivity/` |
| Table X, checker swap; six-seed RTAMT spread; 4,350-candidate verdict check | `rtamt_auxiliary.py`; `rtamt_differential.py` re-runs the check | `rtamt_checker_authoritative.csv`, `rtamt_at1_seed_sweep.csv`, `rtamt_paired_verdicts.csv` | `raw_results/checker_swap_rtamt/` |
| Table VII, Sec. V-B and V-C, TD-SB-TemPsy baseline | `baseline_outcomes.py` | `baseline_outcome_counts.csv`, `baseline_diagnoses.csv` | `raw_results/baseline_td_sb_tempsy/`, `inputs/baseline_td_sb_tempsy/` |
| Sec. VI-A, operator coverage | `experiments/operator_coverage/run_coverage.py` | `experiments/operator_coverage/operator_coverage.csv` | the fixtures in that folder |
| Sec. VI-A, running-example fix | `experiments/implementation_fix/reproduce.py` | `experiments/implementation_fix/raw/` | the controllers and traces in that folder |
| Sec. V-A, trace sizes | `trace_stats.py` | `trace_statistics.csv` | `inputs/traces/` |

The `*_rows.tex` files next to the CSVs are the corresponding LaTeX table bodies.
`tests/expected/` holds the paper-facing CSVs that `./run results` compares against.

## Layout

`tool/` is the diagnosis tool. `inputs/` holds the requirements, traces, expert
reference trees, the running example and the baseline's converted inputs.
`experiments/` holds the run configurations of every study. `raw_results/` holds what
the runs produced, and `analysis/` what the scripts in `scripts/` derive from it.
`environment/` builds the container, and `docs/METHODS.md` explains how runs were
selected, scored and timed.

## Bulk data on Zenodo

Per-generation candidates, verdict caches and intermediate files of the RQ1/RQ2 runs
(635 MB), and the full Diagnosis repository that `tool/` was taken from, are archived on
Zenodo with this package ([10.5281/zenodo.23979522](https://doi.org/10.5281/zenodo.23979522)). None of it is needed for the commands above. `python3 scripts/fetch_archive.py`
downloads it, checks it against `raw_results/ARCHIVE.json` and unpacks it in place.

## Citation and licence

Cite the paper and this package (DOI [10.5281/zenodo.23979522](https://doi.org/10.5281/zenodo.23979522)); `CITATION.cff` has the details. The first three authors
contributed equally. Package material is under the MIT licence (`LICENSE`); third-party
terms are in `LICENSES/`.
