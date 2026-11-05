# Expert reference trees

Each `machine_readable/expN.json` is the expert evaluator for one experiment. For 27
experiments it is the expert's satisfied region, transcribed verbatim from the
expert's original grid evaluator in `original_accuracy_scripts/` (file, case, checksum,
author and date are recorded in `original_reference`). For exp2, exp14, exp16, exp18,
exp20, exp33 and exp34 it is a rule over the trace, with the trace witness, extrema and
representative checker mutations under `references/trace_witnesses/`.

`scripts/build_expert_references.py` writes the JSON, DOT, SVG and PDF forms;
`INDEX.csv` records the rendering commands. For exp33 and exp34 the original
`AccuracyRR.py` boxes are kept in the JSON provenance; the canonical evaluator applies
the trace-derived RR rule on the configured mutation axes.
