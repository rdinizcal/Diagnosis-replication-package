# Rerun environment

The release environment is CPython 3.13.5, Z3 4.15.4.0, OpenJDK 17,
Weka 3.8.6, RTAMT 0.3.5, Graphviz 2.42.2, and the exact Python pins in
`requirements-lock.txt`. The container definition verifies downloaded JARs.
RTAMT 0.3.5 is installed from `rtamt-compat-lock.txt` with `--no-deps` after
its required ANTLR 4.7 runtime. ANTLR 4.7's two obsolete `typing.io` imports
are changed to `typing` by `patch_antlr47_py313.py`; the patch refuses to run
if either upstream file differs from the expected content. This preserves the
parser's required serialized-ATN format while making it importable on Python
3.13. Debian packages are pinned to OpenJDK `17.0.20+8-1~deb12u1` and Graphviz
`2.42.2-7+deb12u1` (whose `dot -V` reports upstream version 2.43.0).

Build with `docker build -t diagnosis-replication -f environment/Dockerfile .`
or `apptainer build diagnosis-replication.sif environment/replication.def`.
After building, record `docker image inspect --format '{{.Id}}'` (or
`apptainer inspect`) in `versions.json` and regenerate `MANIFEST.csv` before a
release. The tested local image ID and platform are recorded there. The
archived runs did not record an image digest or exact Java and Graphviz patch
versions, so this locked release environment is a rerun target, not a claim
about their unknown historical host. `versions.json` and `MANIFEST.csv` are
excluded from the build context to avoid making the image identity depend on
files whose purpose is to record that identity.

Run `python3 scripts/preflight.py` before any host-native execution.
