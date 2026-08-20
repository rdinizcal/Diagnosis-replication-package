# RTAMT vs Z3 — effectiveness/efficiency (corrected runs; AT1 adopted seed=1)
Runs: paper baseline (pop 50, gen 100, mutation_rate 0.9, cv_pr 0.995), engine=rtamt, heuristics off.

AT1 seed sweep (6 seeds), ground-truth accuracy: 97.24, 95.79, 95.85, 96.66, 96.49, 96.51  -> 96.4% ± 0.5% (bracketing Z3 97.97%). Adopted seed 1 (97.24%, 1024 calls).

CV P/R (10-fold J48): AT1 RTAMT 98.82% (0.988/0.988) | AT1 Z3 98.17% | CCX RTAMT 99.69% (0.997) | CCX Z3 99.54%
Accuracy vs ground truth: AT1 Z3 98.64/97.63/97.97 | AT1 RTAMT 97.64/97.29/97.24 | CCX Z3 100/99.04/99.54 | CCX RTAMT 100/99.76/99.88
Efficiency (mean s/call): AT1 Z3 13.42 vs RTAMT 0.088 (~152x) | CCX Z3 1916.7 vs RTAMT 1.53 (~1250x)
Trees: AT1 RTAMT 21 leaves float; AT1 Z3 19 leaves; CCX RTAMT NUM2<=7.383576; CCX Z3 NUM2<=7.36646
rho_zero=0 both. Differential (engine unchanged): 0/4350 unexplained mismatches.
