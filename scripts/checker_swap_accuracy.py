"""DT accuracy of the checker-swap trees against the analytical ground truth.

AT1: parse a J48 tree -> SAT boxes over (lo, hi, thr), compared on a 101^3 grid with
the trace-derived expert (SAT iff thr > v_speed(hi)). CCx: the tree is one threshold on
the y5-y4 bound, compared with the trace minimum of y5-y4 as interval overlap on the
mutation range [5, 10].
"""
import csv, re, sys
from pathlib import Path

import numpy as np
from scipy.interpolate import interp1d

TRACES = Path(__file__).resolve().parents[1] / "inputs" / "traces"
# feature -> (param index, unit divisor). NUM0=lo(us), NUM1=hi(us), NUM2=thr.
FEAT = {"NUM0": (0, 1e6), "NUM1": (1, 1e6), "NUM2": (2, 1.0)}
CCX_RANGE = (5.0, 10.0)


def trace(requirement, family):
    csv.field_size_limit(sys.maxsize)
    for row in list(csv.reader(open(TRACES / f"traces{family}.csv")))[1:]:
        if row[0].strip() == requirement:
            return np.array([[float(x) for x in record.split()]
                             for record in row[1].strip().strip("[]").split(";") if record.strip()])
    raise KeyError(requirement)


def tree_lines(tree_text):
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
    return lines


def parse_sat_boxes(tree_text):
    """Return list of boxes [lo_lo,lo_hi,hi_lo,hi_hi,thr_lo,thr_hi] for TRUE leaves."""
    boxes = []
    stack = []  # (attr, op, val) per depth
    rng = {0: [0.0, 10.0], 1: [10.0, 30.0], 2: [100.0, 140.0]}  # AT1 param ranges (s, s, thr)
    for ln in tree_lines(tree_text):
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


def at1_accuracy(tree_path, N=100):
    """Precision, recall and accuracy of an AT1 tree on the 101^3 grid."""
    td = trace("AT1", "AT")
    tf = interp1d(td[:, 0], td[:, 1])  # analytical expert: SAT iff thr > v_speed(window_hi)
    boxes = parse_sat_boxes(Path(tree_path).read_text())
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


def ccx_accuracy(tree_path):
    """Precision, recall and accuracy of a one-split CCx tree (SAT iff bound <= threshold)."""
    (line,) = [ln for ln in tree_lines(Path(tree_path).read_text()) if ": TRUE" in ln]
    tool = float(re.search(r"<=\s*([-\d.]+)", line)[1])
    td = trace("CCX", "CC")
    expert = float(min(td[:, 5] - td[:, 4]))
    lo, hi = CCX_RANGE
    tp = min(tool, expert) - lo; fp = max(0.0, tool - expert); fn = max(0.0, expert - tool)
    tn = hi - max(tool, expert)
    return tp/(tp+fp), tp/(tp+fn), (tp+tn)/(hi-lo)


if __name__ == "__main__":
    for path in sys.argv[1:]:
        p, r, a = (ccx_accuracy if "CCX" in path.upper() else at1_accuracy)(path)
        print(f"{path}: precision={p*100:.2f}%  recall={r*100:.2f}%  acc={a*100:.2f}%")
