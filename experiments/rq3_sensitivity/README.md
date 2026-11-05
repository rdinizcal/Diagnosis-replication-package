# RQ3 sensitivity study

28 configurations for phi2, phi3, phi4, AT53 and RR, with five seed-specific JSON
files each. Every file is the variant's launch template in
`evaluation_inputs/sensitivity/` with the seed and GA settings recorded in the run's
`summary.json`; `replication_metadata` names both files. Positions use the bundled
tool's numbering: phi3's last numeric position is 38 here and 40 in the template, and
`position_translation` records the mapping. AT53's quantifier mutation is the tool's
guarded range repair.

`scripts/validate_rq3_configs.py` checks every configuration against the AST mutator;
`scripts/rq3_auxiliary.py` derives per-run runtime, split, tree size, depth, leaves and
root data from the 140 runs and generates Table 9.
