"""Accuracy vs analytical ground truth (paper methodology) for Z3 vs RTAMT trees."""
import numpy as np, pandas as pd
from scipy.interpolate import interp1d

TRACES = "replication/analysis/data/tracesAT.csv"


def box_hit(param, box, tr):
    return ((box[0] < param[0] <= box[1] or param[0] == tr[0] == box[0]) and
            (box[2] < param[1] <= box[3] or param[1] == tr[2] == box[2]) and
            (box[4] < param[2] <= box[5] or param[2] == tr[4] == box[4]))


def pr(totalRange, toolSatis, expert, N=100, single=False):
    tp = tn = fp = fn = 0
    p = np.zeros(3)
    for i in range(N + 1):
        p[0] = totalRange[0] + (totalRange[1] - totalRange[0]) / N * i
        for j in range(N + 1):
            p[1] = totalRange[2] + (totalRange[3] - totalRange[2]) / N * j
            for k in range(N + 1):
                p[2] = totalRange[4] + (totalRange[5] - totalRange[4]) / N * k
                tb = any(box_hit(p, b, totalRange) for b in toolSatis)
                eb = expert(p)
                tp += tb and eb; tn += (not tb) and (not eb)
                fp += tb and (not eb); fn += (not tb) and eb
            if single: break
        if single: break
    precision = tp / (tp + fp) if (tp + fp) else float('nan')
    recall = tp / (tp + fn) if (tp + fn) else float('nan')
    acc = (tp + tn) / (tp + tn + fp + fn)
    return precision, recall, acc, (tp, tn, fp, fn)


# ---- AT1: analytical expert = threshold > v_speed(window_hi) ----
df = pd.read_csv(TRACES); df = df[df['Requirement'] == "AT1"]
s = "[" + df.at[df.index[0], ' Output Trace'] + "]"
s = s.replace("; ", "],[").replace(" ", ",")
td = np.array(eval(s)[:-1]); td = np.delete(td, [2, 3], 1)
tf = interp1d(td[:, 0], td[:, 1])
at1_range = np.array([0.0, 10.0, 10.0, 30.0, 100.0, 140.0])
at1_expert = lambda p: p[2] > tf(p[1])

# Z3 tree (paper AccuracyAT1 exp2, verbatim)
at1_z3 = np.array([[0.0,10.0,10.0,12.696411,100.0,105.291267],
    [0.0,10.0,12.696411,13.309259,102.890852,105.291267],
    [0.0,10.0,10.0,13.986527,105.291267,124.873017],
    [0.0,10.0,13.986527,15.896834,108.980719,115.435108],
    [0.0,10.0,15.896834,17.003177,111.497926,115.435108],
    [0.0,10.0,13.986527,18.917859,115.435108,124.873017],
    [0.0,10.0,18.917859,19.969545,119.726918,120.487499],
    [0.0,10.0,18.917859,21.228596,120.487499,124.873017],
    [0.0,10.0,10.0,23.563323,124.873017,140.0],
    [0.0,10.0,23.563323,25.066859,127.344796,131.000874],
    [0.0,10.0,25.066859,25.842157,129.003908,131.000874],
    [0.0,10.0,23.563323,28.286904,131.000874,140.0],
    [0.0,10.0,28.286904,30.0,134.017274,140.0]])
# RTAMT tree: NUM2<=120 & NUM1<=19.256836 -> TRUE ; NUM2>120 -> TRUE
at1_rt = np.array([[0.0,10.0,10.0,19.256836,100.0,120.0],
                   [0.0,10.0,10.0,30.0,120.0,140.0]])

print("== AT1 (vs analytical ground truth) ==")
for name, tool in [("Z3   ", at1_z3), ("RTAMT", at1_rt)]:
    p, r, a, c = pr(at1_range, tool, at1_expert)
    print(f"  {name}: precision={p*100:.2f}%  recall={r*100:.2f}%  acc={a*100:.2f}%  (TP,TN,FP,FN)={c}")

# ---- CCX exp1: single threshold; expert boundary = min(y5-y4) = 7.3894 ----
ccx_range = np.array([0.0, 0.0, 50.0, 50.0, 5.0, 10.0])
ccx_expert = np.array([[0.0,0.0,50.0,50.0,5.0,7.389400]])
ccx_exp_fn = lambda p: any(box_hit(p, b, ccx_range) for b in ccx_expert)
ccx_z3 = np.array([[0.0,0.0,50.0,50.0,5.0,7.366460]])   # paper AccuracyCCx exp1
ccx_rt = np.array([[0.0,0.0,50.0,50.0,5.0,7.382655]])   # RTAMT tree boundary

print("== CCX (vs analytical ground truth, boundary 7.3894) ==")
for name, tool in [("Z3   ", ccx_z3), ("RTAMT", ccx_rt)]:
    p, r, a, c = pr(ccx_range, tool, ccx_exp_fn, single=True)
    print(f"  {name}: precision={p*100:.2f}%  recall={r*100:.2f}%  acc={a*100:.2f}%  (TP,TN,FP,FN)={c}")
