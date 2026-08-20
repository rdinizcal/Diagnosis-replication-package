# Diagnosis-to-implementation fix

This example was executed. `sim_lc_faulty.py` is the original seeded controller,
`sim_lc.py` is the repaired controller, and `flag_rearming_and_controller_fixes.patch`
is generated from them. The `retry` scenario is the flag-rearming witness: phi3
is violated before the fix and satisfied afterwards.

Run:

```sh
python reproduce.py
python -m pytest -q test_verdict_matrix.py test_fix_verification.py
```

The first command preserves pre/post CSV traces and detailed requirement checks
under `raw/`. The second independently checks the faulty verdict matrix and all
16 post-fix requirement/scenario combinations.
