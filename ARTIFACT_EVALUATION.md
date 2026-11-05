# Artifact validation report

## Status

The standalone replication repository passes its clean-checkout evidence-chain
workflow. The locked environment builds from the repository, smoke and analysis
workflows run without network access after setup, and generated outputs satisfy
the packaged analysis oracles.

Validation date: 2026-08-20. Evaluator timezone: Europe/Rome.

## Validated workflows

- The Diagnosis submodule resolves to
  `05d0750395972662e9be0a1083b09a6dce7e3e65`; the bundled executable subset is
  checked against that source plus the documented patch in `tool/PATCHES.md`.
- `MANIFEST.csv` covers the immutable package contents and verifies SHA-256
  checksums.
- The container build supplies the pinned analysis and solver environment.
- Schema validation covers 480 primary/RQ3 configurations and the auxiliary
  configurations registered by the package.
- Smoke covers configuration loading, parsing, mutation, checker integration,
  caching, and tree generation.
- Unit, quantifier, implementation-fix, and operator-coverage regressions pass.
- Analysis regeneration starts with an empty output directory and produces 34
  expert references, 340 RQ1 slots (284 scored), 340 RQ2 rows (36 censored),
  340 tool-tree slots, 31 modal selections, 140 RQ3 rows, 28 RQ3 summary rows,
  and 4,350 paired checker verdicts.
- The generated CSV and JSON values pass the packaged arithmetic and analysis
  oracles. Graphviz renderings are content-regenerable; byte identity of PDF and
  SVG rendering is not required across platforms.

The complete claim-to-command-to-evidence mapping is in `CLAIMS.md`.

## Provenance and scope

The selected historical RQ1/RQ2 outputs did not record their original tool
commit or image digest. This field is represented as `UNRECORDED`; the rerun
source is explicitly pinned to the Diagnosis commit above. RQ3 effective
configuration files are evidence-based reconstructions from the archived runs,
with both historical and current position namespaces retained.

The core computational reproduction covers RQ1--RQ3 from archived raw outputs.
Full solver reruns use the materialized configurations and require the
documented cluster-scale budget. Checker-swap, external-baseline, and
MS-sensitivity directories are optional supporting material with explicit
status fields; they do not create empirical claims for unavailable
measurements.

## Portability and integrity

- Active configuration and scripts use repository-relative paths; historical
  absolute paths may appear only as inert provenance fields in archived data.
- Clean-checkout execution does not depend on untracked sibling files.
- Runtime writes are confined to `analysis/` and
  `raw_results/rerun/`; archived inputs remain immutable.
- Runtime tests use `--network none` after the documented environment build.
- Canonical experiment IDs are `exp1` through `exp34`; historical aliases are
  metadata only.
- Primary and sensitivity seeds, worker counts, and tool-specific random seeds
  are materialized in configuration or validation code.
- Package, tool, input, and third-party licensing information is collected in
  `LICENSE`, `tool/LICENSE`, `LICENSES/`, and the provenance records.
- No package file exceeds GitHub's 100 MiB per-file limit. The unpacked payload
  is approximately 840 MiB and a measured compressed audit archive was about
  116 MiB.

## Exact validation commands

Run from the repository root:

```sh
python3 scripts/preflight.py
python3 scripts/verify_submodule.py
python3 scripts/verify_manifest.py
python3 scripts/release_audit.py
docker build --pull -t diagnosis-artifact -f environment/Dockerfile .
docker run --rm --network none diagnosis-artifact python3 scripts/validate_configs.py
docker run --rm --network none diagnosis-artifact ./smoke
mkdir -p clean-derived
docker run --rm --network none \
  -v "$PWD/clean-derived:/opt/replication/derived_results" \
  diagnosis-artifact ./reproduce-analysis
docker run --rm --network none \
  -v "$PWD/clean-derived:/opt/replication/derived_results" \
  diagnosis-artifact python3 scripts/verify.py
docker run --rm --network none \
  -v "$PWD/clean-derived:/opt/replication/derived_results" \
  diagnosis-artifact python3 -m pytest -q tests/test_rq1_rq2.py
docker run --rm --network none \
  -v "$PWD/clean-derived:/opt/replication/derived_results" \
  diagnosis-artifact python3 scripts/verify_auxiliaries.py
docker run --rm --network none diagnosis-artifact \
  python3 experiments/operator_coverage/run_coverage.py
docker run --rm --network none diagnosis-artifact python3 -m pytest -q \
  tests/test_operator_coverage.py \
  experiments/implementation_fix/test_fix_verification.py \
  experiments/implementation_fix/test_verdict_matrix.py
```

## Known limitations

- Full primary and RQ3 solver reruns are cluster-scale workloads and are not
  part of the routine CI budget.
- The original historical tool/image identity for selected RQ1/RQ2 runs was
  not recorded; reruns use the declared pinned source.
- RQ3 launch configurations are reconstructions documented in their metadata.
