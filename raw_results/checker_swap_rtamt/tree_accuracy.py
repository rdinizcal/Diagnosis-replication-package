"""Parse a J48 AT1 tree -> SAT boxes -> precision/recall vs analytical ground truth."""
import re, sys, numpy as np, pandas as pd
from scipy.interpolate import interp1d

TRACES = "replication/analysis/data/tracesAT.csv"
# feature -> (param index, unit divisor). NUM0=lo(us), NUM1=hi(us), NUM2=thr.
FEAT = {"NUM0": (0, 1e6), "NUM1": (1, 1e6), "NUM2": (2, 1.0)}


def parse_sat_boxes(tree_text):
    """Return list of boxes [lo_lo,lo_hi,hi_lo,hi_hi,thr_lo,thr_hi] for TRUE leaves."""
    lines = []
    started = False
    for ln in tree_text.splitlines():
        if ln.strip().startswith("J48 pruned tree"):
            started = True; continue
        if started:
            if ln.strip() == "" or ln.strip().startswith("----"):
                continue
            if ln.startswith("Number of Leaves"):
                break
            lines.append(ln)
    boxes = []
    stack = []  # (attr, op, val) per depth
    rng = {0: [0.0, 10.0], 1: [10.0, 30.0], 2: [100.0, 140.0]}  # AT1 param ranges (s, s, thr)
    for ln in lines:
        depth = ln.count("|")
        body = ln.replace("|", "").strip()
        m = re.match(r"(NUM\d)\s*(<=|>)\s*([-\d.]+)(?::\s*(TRUE|FALSE)\s*\(([\d./]+)\))?", body)
        if not m:
            continue
        attr, op, val, cls, _ = m.groups()
        stack = stack[:depth]
        stack.append((attr, op, float(val)))
        if cls is not None:
            if cls == "TRUE":
                box = {0: list(rng[0]), 1: list(rng[1]), 2: list(rng[2])}
                for a, o, v in stack:
                    idx, div = FEAT[a]; vv = v / div
                    if o == "<=":
                        box[idx][1] = min(box[idx][1], vv)
                    else:
                        box[idx][0] = max(box[idx][0], vv)
                boxes.append([box[0][0], box[0][1], box[1][0], box[1][1], box[2][0], box[2][1]])
    return boxes


def in_boxes(p, boxes):
    return any(b[0] <= p[0] <= b[1] and b[2] <= p[1] <= b[3] and b[4] <= p[2] <= b[5]
              for b in boxes)


# analytical expert: SAT iff thr > v_speed(window_hi)
df = pd.read_csv(TRACES); df = df[df['Requirement'] == "AT1"]
s = "[" + df.at[df.index[0], ' Output Trace'] + "]"
s = s.replace("; ", "],[").replace(" ", ",")
td = np.array(eval(s)[:-1]); td = np.delete(td, [2, 3], 1)
tf = interp1d(td[:, 0], td[:, 1])


def pr(boxes, N=100):
    tp = tn = fp = fn = 0; p = np.zeros(3)
    for i in range(N + 1):
        p[0] = 0.0 + 10.0 / N * i
        for j in range(N + 1):
            p[1] = 10.0 + 20.0 / N * j
            for k in range(N + 1):
                p[2] = 100.0 + 40.0 / N * k
                tb = in_boxes(p, boxes); eb = p[2] > tf(p[1])
                tp += tb and eb; tn += (not tb) and (not eb)
                fp += tb and (not eb); fn += (not tb) and eb
    return tp/(tp+fp), tp/(tp+fn), (tp+tn)/(tp+tn+fp+fn)


for name, path in [("RTAMT", sys.argv[1]), ("Z3", sys.argv[2])]:
    boxes = parse_sat_boxes(open(path).read())
    p, r, a = pr(boxes)
    print(f"AT1 {name:5s}: {len(boxes)} SAT boxes  precision={p*100:.2f}%  recall={r*100:.2f}%  acc={a*100:.2f}%")
