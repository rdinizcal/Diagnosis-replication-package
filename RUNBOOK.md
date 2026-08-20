# Runbook

## 1. Obtain and inspect

Preserve the package directory unchanged. Verify the release checksum/signature
outside this package if supplied, then run:

```sh
python3 scripts/preflight.py
python3 scripts/validate_configs.py
```

Preflight needs at least Python 3.13, Java 17, Graphviz, Z3, RTAMT, the analysis
libraries, and `WEKA_JAR`. Full campaigns can require five days per
configuration and substantial output space; do not infer a cluster allocation
from the quick preflight.

## 2. Recommended container

```sh
docker build -t diagnosis-replication -f environment/Dockerfile .
docker run --rm diagnosis-replication
docker run --rm -v "$PWD/derived_results:/opt/replication/derived_results" \
  diagnosis-replication ./reproduce-analysis
```

For Apptainer:

```sh
apptainer build diagnosis-replication.sif environment/replication.def
apptainer run diagnosis-replication.sif
```

## 3. Smoke

`./smoke` uses the canonical AT1 exp1/seed0 identity and numeric domain, parses
and mutates an AT1-shaped formula, checks a satisfiable Z3 constraint, exercises
the verdict cache, and trains/evaluates a tiny J48 tree. Failure of any component is a package or
environment failure, not an experimental result.

## 4. Computational reproduction

```sh
./reproduce-analysis
./verify
python3 -m pytest -q tests/test_rq1_rq2.py
```

The first command uses no checker: it reads the packaged archive, rebuilds the
expert references, confusion matrices, modal trees, Tables 8/9, LaTeX rows, and
figures. The second validates every run slot and all reported counts and
aggregates, then compares paper-facing CSVs exactly with `expected`.

## 5. Full rerun

Always inventory first:

```sh
./reproduce-full
./reproduce-full --study rq1_rq2 --ids exp1,exp2 --seeds 0
./reproduce-full --profile at1
./reproduce-full --profile multi-token
./reproduce-full --profile discrete-operator
```

Execute only after provisioning the declared budgets:

```sh
./reproduce-full --study rq1_rq2 --ids exp1 --seeds 0 --execute
./reproduce-full --profile multi-token --execute
./reproduce-full --profile discrete-operator --execute
./reproduce-full --study rq3_sensitivity --execute
```

Each process is serial (`parallel_workers=1`). Seeds propagate to Python's
`random` and NumPy. Do not share a writable cache between independent seeds.
Outputs go below `raw_results/rerun/`; archived material is never overwritten.
The `at1` profile is the single-token exp1/seed0 run; `multi-token` is
exp2/seed0; `discrete-operator` is exp30/seed0. The smoke is intentionally
seconds-long, while these three full profiles retain their original budgets and
may be long. RQ3 reruns are method replications from reconstructed configs, not byte-exact
reproductions. Compare new distributions and statuses, not wall-clock equality.

## 6. Auxiliary studies

- Operator coverage: `python3 experiments/operator_coverage/run_coverage.py`.
- RTAMT swap: run the two configs in `checker_swap_rtamt/configs` with the
  bundled RTAMT-capable tool.
- TD-SB-TemPsy baseline: the configuration and limitations are documented, but
  raw baseline logs/tool version were not recoverable; this study cannot be
  exactly rerun from this archive.
- Implementation fix: run from that directory so imports resolve:
  `cd experiments/implementation_fix && python3 test_fix_verification.py`.

## 7. Release refresh

After intentional changes, run `python3 scripts/archive_rq1_rq2.py` only against
the unchanged reconciliation allow-list, then rerun all validation, analysis,
and verification commands, build the image, record its
digest, and run `python3 scripts/build_manifest.py`. Never point the builder at
an unlisted campaign or replace `UNRECORDED` with a repository HEAD.
