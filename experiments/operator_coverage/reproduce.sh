#!/bin/sh
set -eu
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ROOT=$(CDPATH= cd -- "$HERE/../.." && pwd)
export PYTHONPATH="$ROOT/tool${PYTHONPATH:+:$PYTHONPATH}"
python3 "$HERE/run_coverage.py" --seed 42 --timeout 50 --outdir "$HERE"
exec python3 "$HERE/build_matrix.py"
