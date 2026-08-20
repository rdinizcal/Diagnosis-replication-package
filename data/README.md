# Data format and provenance

`tracesAT.csv` contains a header and ten benchmark trace rows; `tracesCC.csv`
contains a header and six rows; `traceRR.csv` is the seventeenth trace in long
form. AT/CC cells store the original trace serialization consumed by the
generated requirement programs. RR rows are
`timestamp,signal,value,signal,value,...`.

Time inside generated AT/CC/RR requirements is represented in microseconds;
paper-facing time-window ranges are seconds. The running-example TSV files use
seconds as documented in their header/source. Signal units are requirement
specific and recorded per mutable token in `experiments/registry.csv`: mph,
rpm, metres, or seconds. Values without a physical unit are marked categorical.

No normalization, interpolation, down-sampling, or unit conversion is applied
by the package builder. The requirement programs contain their fixed sampled
traces and checker encodings. `data/provenance/inputs.csv` records upstream,
commit, original identifier, transformation, kind, and checksum for every file.
There is no validated trace-regeneration recipe for the benchmark, so all 17
traces are declared fixed primary inputs. Running-example traces can be
regenerated only from the upstream simulator; this package preserves the fixed
inputs used for analysis rather than claiming a simulator seed not recorded.
