# RQ3 sensitivity study

This directory contains 28 configurations for phi2, phi3, phi4, AT53, and RR,
with five seed-specific JSON files each. Every JSON includes mutable positions,
original values, admissible domains/alternatives, enabled mutation families,
maximum simultaneous mutations, seed, output path, and label rationale.

The original effective 2025 JSON files were not retained. The reconstruction is
therefore not byte-identical: values and domains were recovered from the source
properties and archived ARFF data. Historical position IDs are preserved in
metadata. The bundled parser numbers phi3's final numeric position as 38 rather
than historical ID 40, so the executable field uses 38 and records the mapping.

AT53 has an additional semantic boundary. Its archived raw runs used the legacy
binder-only ForAll/Exists flip. The executable configs use the corrected guarded
transformation (ForAll with `guard => body` becomes Exists with `guard and body`,
and conversely). Thus the archived AT53 rows reproduce historical Table 9 but do
not validate the corrected quantifier mutation.

`scripts/rq3_auxiliary.py` validates five required raw files for all 140 runs and
generates per-run runtime/split/nodes/depth/leaves/root data, aggregate mean/SD,
modal roots, the configuration catalogue, and Table 9.
