# Bundled rerun-tool differences

The complete upstream source base is the `Diagnosis/` Git submodule at commit
`05d0750395972662e9be0a1083b09a6dce7e3e65`. The archive-safe `tool/` subset
adds two package-authored files (`run_batch.py` and `SEMANTICS.md`) and applies
one semantic correction:

- `diagnosis/mutation/api.py` repairs the range connective when switching a
  bounded universal/existential quantifier and refuses ambiguous or unguarded
  flips. Its SHA-256 is
  `0c1cb011565e78e966d7dd489219c1e6bc7b5b7e4177a62326d9e92ab8af3151`.

The upstream/base file SHA-256 is
`a9844ddd1e16310025504b5d35703580312ea49ad70e5e34894efefbdf9acb67`.
The corresponding correction is released in Diagnosis `v1.1.0`; the bundled
file is retained because it was the exact audited rerun implementation. Run
`python3 scripts/verify_submodule.py` from a recursive clone to verify the
gitlink, upstream checkout, unchanged overlapping files, and patched-file hash.

This correction must not be projected backward onto archived primary runs.
Their effective configurations survived, but their source commit did not; the
artifact records that field as `UNRECORDED`.
