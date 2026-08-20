# TD-SB-TemPsy baseline status

The public upstream is Apache-2.0. `fetch_and_patch.sh` checks out exact upstream
commit `410753400e58e2a386a3e65f48374211214b4dc0`, fetches pull request 2, and
verifies patched head `8efd304987a8f7355606fa3951576d00f316df51`. The relevant Complete-OCL import
fallback is commit `8164cb8cfc0a8c054d41ad8317642e6cbcfe384a`; the PR also supplies a Docker-based Eclipse Mars /
Java 7 environment.

The revision's converted 17 trace/specification pairs, stdout/stderr, five
diagnosis logs, four one-hour timeout logs, eight unsupported/crash records,
and per-run timings were not retained and are not present upstream. Their
historical summary is therefore not reproducible from this workspace. The
paper has been changed so these values are not presented as verified evidence.
This directory intentionally does not manufacture replacement outputs.

To complete this study, reconstruct and review all 17 XMI/CSV pairs, execute
them in the pinned environment, and preserve command, stdout, stderr, exit
status, start/end timestamps, timeout status, and hashes for every input.
