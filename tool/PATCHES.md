# tool/ and its source base

`tool/` is the executable subset of Diagnosis at commit
`05d0750395972662e9be0a1083b09a6dce7e3e65`. It adds `run_batch.py`, `SEMANTICS.md`
and the RTAMT engine, and changes one file:

- `diagnosis/mutation/api.py` repairs the range connective when a bounded
  universal/existential quantifier is flipped and refuses ambiguous or unguarded flips
  (SHA-256 `0c1cb011565e78e966d7dd489219c1e6bc7b5b7e4177a62326d9e92ab8af3151`; the
  source-base file is `a9844ddd1e16310025504b5d35703580312ea49ad70e5e34894efefbdf9acb67`).
  Diagnosis v1.1.0 releases the same correction.

The full source base is in the Zenodo archive. After `python3 scripts/fetch_archive.py`,
`python3 scripts/verify_tool_snapshot.py` checks that every other file in `tool/` is
identical to it.

The archived runs were produced by the tool trees recorded in each run's
`tool_commit`: `diagnosis-experiments@9b34118` for campaign 20260803171759,
`diagnosis-experiments@28edea0` for the 20260812103600 and 20260903113951 re-runs,
and `Diagnosis@fc96c7e` for the RQ3 runs. The cluster image copies the tool in when
it is built (`hpc/diagnosis.def` in diagnosis-experiments). `9b34118` is the only tool
commit before campaign 20260803171759, and all of its trees still carry the undecided
class that `d668fe4` removed from the training-set writer. No tree of the two later
campaigns does, and `28edea0` is the last tool commit before either. The RQ3 runs date
from 23 to 30 December 2025, after `fc96c7e` and before the next tool commit in March
2026. The archive holds all three trees.
