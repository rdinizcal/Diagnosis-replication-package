# Release notes — 1.0.0 candidate

Evaluation date: 2026-08-20. Immutable archival date and Zenodo DOI: not yet
assigned. This standalone repository was initialized from the independently
audited payload. Its release commit will be fixed by the eventual version tag
and recorded in the Zenodo deposit.

This candidate packages 34 canonical RQ1/RQ2 experiment definitions and 340
archived run slots, 140 reconstructed RQ3 configurations/runs, fixed inputs,
expert references, operator fixtures, a frozen tool snapshot, and a locked
container environment. Analysis regenerates Tables 8 and 9, appendix
precision/recall values, modal/tool trees, and runtime figures.

Known release blockers are intentionally not hidden: raw Z3 timing logs, all
TD-SB-TemPsy converted inputs/run records, and the 40-run current-pipeline MS
sensitivity campaign are absent. The checked PDF still contains empirical
TD-SB-TemPsy claims, so it is not consistent with the package's statement that
those claims were removed. See `ARTIFACT_EVALUATION.md` for the claim verdicts.

The unpacked payload is approximately 840 MiB; an audit tar.gz measured 116 MiB.
The compressed size and SHA-256 must be measured again after the final manifest
and release commit. Analysis-only
regeneration took about 95 seconds on an 8-vCPU Linux/arm64 Docker VM with 8 GB
RAM. Smoke took under 10 seconds. A full primary configuration declares a
120-hour wall guard and a 3,600-second checker-call timeout; the package has 340
primary and 140 RQ3 configurations, so full reruns require cluster scheduling
and substantial storage. Representative capped audit launches did not finish
within 30–120 seconds and are not reported as completed reproductions.

Recommended artifact citation: Ricardo Caldas, Gabriel Araujo, Federico
Formica, Genaína Rodrigues, Patrizio Pelliccione, and Claudio Menghi,
“Diagnosis: replication package for Search-based Trace Diagnostic for
Cyber-Physical Systems,” version 1.0.0, 2026. Add the Zenodo DOI after deposit.
