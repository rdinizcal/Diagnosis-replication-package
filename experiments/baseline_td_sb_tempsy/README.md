# TD-SB-TemPsy baseline

`inputs/` holds the 17 benchmark traces converted to TD-SB-TemPsy's CSV log format
and the 13 requirements expressible in SB-TemPsy-DSL as XMI specifications. AT6a,
AT6b, AT6c and AT6abc need Before/Between scopes, and CC2 to CC5 need nested temporal
operators; the latter have no XMI because the language cannot express them.

`fetch_and_patch.sh TARGET` checks out the upstream tool (Apache-2.0) at
`410753400e58e2a386a3e65f48374211214b4dc0` plus pull request 2
(`8efd304987a8f7355606fa3951576d00f316df51`), which adds the Complete-OCL import fix
and a Docker environment with Eclipse Mars, Java 7, EMF 2.11 and OCL. Run
`lu.svv.offline/src/lu/svv/offline/main/TraceCheck.java` on each CSV/XMI pair with a
one-hour limit. The output of every run is in
`raw_results/baseline_td_sb_tempsy/outcomes.csv`; `scripts/baseline_outcomes.py`
derives the outcome counts and the diagnosis witnesses.
