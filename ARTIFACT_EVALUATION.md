# Artifact evaluation

## Verdict

**Not ready for a versioned GitHub release or immutable Zenodo archive.** The
standalone payload builds and its smoke and main computational analyses pass in
a clean, network-disabled container. Release completion nevertheless fails
because the payload is untracked, the supplied manuscript and evidence map are
inconsistent, a paper baseline has no raw evidence, two auxiliary campaigns
lack required raw evidence, and the bundled Bounce JAR has no license text.

Evaluation date: 2026-08-20. Evaluator timezone: Europe/Rome. Repository HEAD:
`e882f3cc705b22de11d8547cf7928a5a89147f62` (`cc-batch-prep`). The evaluated
manuscript was the 22-page PDF with SHA-256
`6db3ee8b1e5116334e89396b7672f5462c791ba1b1d1e6b10d2cef03812f961e`.
The manuscript is outside, and is not included in, the replication payload.

## Clean-room results

A tracked-only `git archive HEAD` was expanded into a fresh temporary
directory. It contained only 19 MiB of legacy `replication/evaluation_inputs`
and did not contain `replication/README.md`, `CLAIMS.md`, `smoke`, or any release
entry point. The proposed `replication/` payload was then copied independently
to a second fresh directory (`/private/tmp/diagnosis-artifact-audit.x6O0yY`)
without sibling repositories. This second standalone test is useful but does
not cure the Git-tracking failure.

The host preflight failed as expected (Python 3.14, Java 8, no Python analysis
dependencies, and no `WEKA_JAR`). Building `environment/Dockerfile` from the
standalone payload succeeded. With `--network none`, container preflight passed
on Linux/arm64 with 8 logical CPUs and about 8 GB RAM: CPython 3.13.5, OpenJDK
17.0.20, Graphviz 2.43.0, Z3 4.15.4.0, NumPy 2.4.2, SciPy 1.17.1, Matplotlib
3.10.8, RTAMT 0.3.5, jsonschema 4.25.1, Weka 3.8.6, and the verified Bounce JAR.

Smoke passed with networking disabled. Analysis was regenerated into an empty
mounted `derived_results/` directory: 34 expert references, 340 RQ1 slots (284
scored), 340 RQ2 rows (36 censored), 340 tool-tree slots, 31 modal selections,
140 RQ3 rows, 28 Table 9 rows, 4,350 paired RTAMT/Z3 verdicts, and all packaged
paper-facing CSV oracles. This run exposed that `reproduce-analysis` omitted
`ms_sensitivity_comparison.csv`; the orchestration was repaired to generate the
explicit 0/40 status table. Before that repair, both permissive and strict
verification crashed rather than reporting the evidence gaps.

Graphviz-generated PDF and SVG bytes differed from the prepackaged versions
when regenerated with the locked Graphviz 2.43.0 image; machine-readable CSV,
JSON, DOT, and paper-value oracles matched. Therefore visual content is
regenerable, but byte-for-byte determinism of rendered graphics is not claimed.

## Reproduced claims

- **C-RQ1 (archived/computational):** 340 slots, 284 scored seeds, 29 scored
  experiment medians, precision 95.0–100.0% (mean 98.8%, sample SD 1.5), and
  recall 69.3–100.0% (mean 97.5%, sample SD 5.9) regenerated.
- **C-RQ2 (archived/computational):** 340 run rows, 284 informative, 20
  degenerate, and 36 120-hour-censored slots regenerated; Table 8 matched its
  oracle exactly.
- **C-OP (coverage only):** OP1–OP15 plus OP4a each parsed, mutated, injected,
  and produced SAT or UNSAT on at least one minimal fixture (16/16).
- The package-only implementation-fix regression executed: 28 available pytest
  checks passed when run with generated analysis present, including quantifier
  guard checks and the 32-verdict implementation-fix matrix.

## Partially reproduced claims

- **C-MODE:** 31 modal tool trees regenerated. Three experiments have no
  selectable completed tree. The external Appendix A cited by the paper is not
  bundled, so equality with the publication artifact cannot be checked.
- **C-RQ3:** all 140 archived rows and Table 9 regenerate, but executable
  configurations are reconstructions, not retained historical effective JSON.
  AT53's archived binder-only quantifier semantics differ from the current
  range-guard repair.
- **C-RTAMT:** two RTAMT raw measurements and 4,350/4,350 matching paired
  verdicts regenerate. Raw Z3 timing logs are absent, so the 152x/1250x speedups
  are estimates, not reproduced measurements. The claim is absent from the
  evaluated manuscript.

## Unverified or failed claims

- **C-BASE — FAIL:** the paper retains TD-SB-TemPsy empirical claims in §5.2,
  Table 7, RQ2 context, discussion, and conclusion. All 17 evidence-inventory
  rows say `unverified`; converted XMI/CSV inputs, stdout, stderr, timings, five
  diagnosis logs, four one-hour timeout logs, and eight crash/unsupported logs
  are absent. No supported baseline case can be run from the package.
- **C-MS — NOT EXECUTED:** 40 configurations exist, but there are no current-
  pipeline results and metrics are intentionally blank. This study is absent
  from the evaluated manuscript.
- **C-FIX — NOT A PAPER CLAIM:** package-only sources/traces/verdicts pass, but
  there is no location in the evaluated manuscript against which to validate
  the assertion.

The full field-by-field chains, paper pages, commands, raw paths, derived paths,
and verdicts are in `CLAIMS.md`.

## Deviations from paper values and scope

The PDF and package appear to describe different evaluation states. The PDF
abstract says “33/34 experiments within budget,” while the package computes 29
experiments with scored medians. The PDF's RQ2 prose reports 14 of 34 completed
and 20 not completed within five days; the package's Table 8 classifies 28 as
informative for all seeds, two as degenerate for all seeds, and four as
timeout/incomplete, with 36 of 340 seed slots censored. The PDF presents
TD-SB-TemPsy results for 17 cases and a five-case comparison; the package has no
raw evidence for any case and incorrectly states that the paper removed those
claims. These are release-blocking manuscript-value inconsistencies.

## Representative reruns

All launches used canonical configs, the locked container, serial workers, and
networking disabled. Audit caps were deliberately much shorter than the
declared 120-hour per-configuration wall guard and are recorded as incomplete:

- numeric single-token `exp1/seed0`: launched; cap 120 s; exit 124; generation
  0 reached 5/50 evaluations;
- multi-token `exp2/seed0`: launched; cap 30 s; exit 124; generation 0 reached
  2/50 evaluations;
- discrete-operator `exp30/seed0`: launched; cap 30 s; exit 124 before one
  checker evaluation completed;
- sensitivity `phi2/G/seed0`: launched; cap 30 s; exit 124 after generation 0
  completed and generation 1 reached 50/250 evaluations;
- operator coverage: completed, 16/16 operators;
- Z3/RTAMT comparison: analysis completed, 4,350/4,350 verdict matches;
- supported baseline: unavailable because its converted inputs and logs were
  not retained.

Partial rerun artifacts were preserved only in the evaluator's temporary
directory, not inserted into immutable `raw_results/`. The runner emits a
Python `KeyboardInterrupt` traceback on an externally enforced SIGINT timeout;
it does not write a concise structured timeout record for these audit caps.

## Portability, integrity, and archive checks

- **Untracked files — fail:** the proposed payload, new CI workflow, and release
  metadata are untracked at the observed HEAD. A clean Git checkout cannot run
  them. No commit or tag was created during this independent audit.
- **Hidden dependencies — pass for standalone payload:** container build,
  smoke, and analysis succeeded from the copied payload without sibling files.
  Runtime configs use relative paths and write under `raw_results/rerun/`.
- **Network isolation — pass after setup:** every execution after image build
  used Docker `--network none`. Image construction itself downloads the pinned
  base/dependencies and checksum-verifies Weka.
- **Absolute paths — qualified pass:** active configs and scripts have no
  developer-home dependency. Two immutable RTAMT `summary.json` files retain
  historical developer-home values only in non-executed `output_dir` metadata.
  Archived RQ1/RQ2 and RQ3 records similarly retain `/opt/...` historical paths.
- **Secrets — pass:** no private-key header, AWS access key, or GitHub-token
  pattern was found. Public author e-mail addresses occur only in the manuscript
  outside the payload.
- **Seeds — pass:** 340 primary configs declare seeds 0–9; 140 RQ3 configs
  declare seeds 0–4; J48 seed is 1; operator coverage defaults to 42; workers
  are pinned to one. Running-example traces have no claimed simulator seed.
- **Checksums — pass after manifest refresh:** input, configuration, archive,
  external dependency, and whole-payload SHA-256 inventories exist. CI now
  verifies exact manifest coverage and hashes.
- **Canonical IDs — pass:** the public primary registry is exactly `exp1` to
  `exp34`; historical AT/CC aliases are retained only as audit metadata.
- **Raw/derived separation — pass:** archived raw evidence is under
  `raw_results/`; regenerated disposable results are under `derived_results/`;
  reruns target `raw_results/rerun/`.
- **Failure/timeout evidence — partial:** the 36 primary censored slots retain
  required logs and scheduler metadata, with missing stopping histories marked
  explicitly. Baseline timeout/crash records and raw Z3 timing logs are absent.
- **Licensing — fail for final release:** package and tool MIT texts and input
  provenance are present. Weka is downloaded, not redistributed. The bundled
  Bounce 0.18 JAR's POM declares “BSD License,” contradicting the prior
  Apache-2.0 label, and the JAR contains no license text; upstream terms and the
  required notice/text must be resolved before redistribution.
- **Archive suitability — qualified:** 21,484 files, no symlinks, no file over
  100 MiB, about 840 MiB unpacked, and 116 MiB in an audit tar.gz. This is within
  Zenodo limits and GitHub's per-file limit but is a large Git repository;
  GitHub Release assets or Git LFS are preferable for raw archives. Recalculate
  final size and checksum after the release commit.

## CI added

`.github/workflows/artifact-evidence.yml` builds the locked environment and,
with networking disabled after setup, checks manifest hashes, release metadata,
configuration schemas, unit/quantifier regressions, all-operator coverage,
smoke, analysis regeneration into an empty target, RQ1/RQ2 regressions,
manuscript-value oracles, and auxiliary evidence with explicit incompleteness.
The final evaluated-manuscript gate is intentionally red: it records the PDF
fingerprint and detects the 33-versus-29 abstract discrepancy, the 14-versus-30
RQ2 discrepancy, and 0/17 retained baseline evidence. Strict `./verify` also
remains nonzero while auxiliary evidence is missing.

## Exact commands run

Commands were run from the repository root unless a clean-room path is shown:

```sh
python3 scripts/preflight.py
git archive HEAD | tar -x -C "$TRACKED_CLEANROOM"
cp -R replication/. "$PACKAGE_CLEANROOM/"
docker build --progress=plain -t diagnosis-replication-audit \
  -f environment/Dockerfile .
docker run --rm --network none diagnosis-replication-audit \
  python3 scripts/preflight.py
docker run --rm --network none diagnosis-replication-audit ./smoke
docker run --rm --network none \
  -v "$AUDIT/clean-derived:/opt/replication/derived_results" \
  diagnosis-replication-audit ./reproduce-analysis
docker run --rm --network none \
  -v "$AUDIT/clean-derived:/opt/replication/derived_results" \
  diagnosis-replication-audit ./verify --allow-incomplete
docker run --rm --network none diagnosis-replication-audit \
  python3 experiments/operator_coverage/run_coverage.py
docker run --rm --network none diagnosis-replication-audit \
  python3 -m pytest -q tests \
  experiments/implementation_fix/test_fix_verification.py \
  experiments/implementation_fix/test_verdict_matrix.py
docker run --rm --network none -v "$AUDIT/rerun-evidence:/opt/replication/raw_results/rerun" \
  diagnosis-replication-audit timeout --signal=INT 120s \
  ./reproduce-full --profile at1 --execute
docker run --rm --network none -v "$AUDIT/rerun-evidence:/opt/replication/raw_results/rerun" \
  diagnosis-replication-audit timeout --signal=INT 30s \
  ./reproduce-full --profile multi-token --execute
docker run --rm --network none -v "$AUDIT/rerun-evidence:/opt/replication/raw_results/rerun" \
  diagnosis-replication-audit timeout --signal=INT 30s \
  ./reproduce-full --profile discrete-operator --execute
docker run --rm --network none -v "$AUDIT/rerun-evidence:/opt/replication/raw_results/rerun" \
  diagnosis-replication-audit timeout --signal=INT 30s \
  python3 -m diagnosis.cli run \
  --config experiments/rq3_sensitivity/configs/phi2/G/seed0.json
python3 scripts/release_audit.py
python3 scripts/build_manifest.py
python3 scripts/verify_manifest.py
python3 scripts/verify_manuscript_values.py
tar -czf /private/tmp/diagnosis-replication-1.0.0-audit.tar.gz replication
```

## Known limitations and actions required

1. Commit every release file, rerun from an actual clean clone of that commit,
   sign/tag it as `v1.0.0`, and record the final commit in release metadata.
2. Reconcile the manuscript PDF with the generated RQ1/RQ2 values and baseline
   evidence status; include the exact paper/appendix version in the archive.
3. Recover or rerun the 17-case TD-SB-TemPsy study with converted inputs and
   complete command/stdout/stderr/timing/timeout records, or remove the claims
   from the actual manuscript.
4. Recover raw Z3 timing logs or remove measured-speedup language; execute the
   40 MS-sensitivity runs if that study is to be claimed.
5. Resolve Bounce's exact license and include the required license/notice text.
6. Rebuild on the intended release architecture, record the final image digest,
   regenerate the manifest, run strict `./verify`, measure the final archive,
   then record the immutable Zenodo date and DOI in CFF/Zenodo/release metadata.
