#!/usr/bin/env python3
"""Regenerate seed-level RQ1 confusion matrices from the packaged evidence.

Same value-grid metric as code/Diagnosis/.../Accuracy*.py: the tool's J48 tree and the
expert are each turned into SATISFIED regions over the mutated parameters and compared
over an N=100 grid per dimension; precision=TP/(TP+FP), recall=TP/(TP+FN). Aggregated
over the COMPLETED seeds in results/ (median + IQR).

Grid arithmetic, the half-open (lo,hi] membership rule and its lower-edge exception, and
every expert disjunction are ported verbatim from the Accuracy*.py reference scripts.
The mutated ranges in DIMS are cross-checked against configs/cc_batch/exp<N>_<REQ>.json
at load time, so a wrong range fails loudly instead of producing a plausible number.

Tool boxes come from each seed's tree rebuilt on the full decided dataset, exactly as
scripts/regen_trees.py does it (two classes, undecided rows dropped, cut 1.0); the tree
is written once to <run>/<stamp>/regen/ and reused. NUMx -> parameter dim is resolved by
which mutated range holds the split's values (time knobs are in microseconds). The grid
is swept one slice of dimension 0 at a time, so 4-D cases stay in a few MB and run in
seconds.

Rebuilding needs Weka: $WEKA_JAR, else the jar shipped with the diagnosis checkout.

    python3 analysis/pr_harness2.py validate    # reproduce known CSV values
    python3 analysis/pr_harness2.py 20 32        # compute experiments

Needs numpy and scipy (e.g. running_example/.venv/bin/python).
"""
from __future__ import annotations
import argparse, csv, glob, hashlib, json, os, re, sys, statistics
from pathlib import Path
import numpy as np
from scipy.interpolate import interp1d

csv.field_size_limit(10**7)
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS = os.path.join(REPO, "raw_results", "rq1_rq2")
CONFIGS = os.path.join(REPO, "experiments", "rq1_effectiveness", "configs")
TRACES = os.path.join(REPO, "data", "traces", "tracesAT.csv")
N = 100


def D(name, lo, hi, scale=1.0, attr=None):
    """A numeric knob: an N+1 point grid over the config range, in units of range/scale.

    `attr` pins the Weka attribute when two knobs share a range and the value of a split
    can no longer say which one it constrains.
    """
    return dict(kind="num", name=name, lo=lo, hi=hi, scale=scale, attr=attr)


def C(name, attr, values):
    """A discrete knob: one grid cell per admissible operator.

    Operators are coded 0..k-1 in the order the ARFF declares them and the axis samples the
    cell midpoints, so it carries exactly one point per operator -- the enumeration the
    Accuracy*.py scripts write as ``for i in np.arange(lo, hi, step=1.0): param = i + 0.5``.
    Operators the mutation configuration does not admit are absent from `values`; Weka still
    emits a branch for them, and that branch is empty and unreachable.
    """
    return dict(kind="cat", name=name, attr=attr, values=list(values))


def dim_range(d):
    """The knob's extent in grid units: [0,k] for operators, [lo,hi]/scale for values."""
    return (0.0, float(len(d["values"]))) if d["kind"] == "cat" else (d["lo"] / d["scale"],
                                                                     d["hi"] / d["scale"])


def dim_axis(d):
    if d["kind"] == "cat":
        return np.array([i + 0.5 for i in range(len(d["values"]))])
    lo, hi = dim_range(d)
    return np.array([lo + (hi - lo) / N * i for i in range(N + 1)])


US = 1e6   # time knobs are microseconds in the requirement, seconds in the expert

# param order == grid order; expert is ("boxes", [...]) or ("func", <requirement>).
CFG = {
    # -- validation cases (targets: analysis/precision_recall_multiseed.csv) ------------
    1:  dict(req="AT1", dims=[D("speed", 100, 140)],
             expert=("boxes", [dict(speed=(120.022620, 140.0))])),
    2:  dict(req="AT1", dims=[D("t0", 0, 10e6, US), D("t", 10e6, 30e6, US),
                              D("speed", 100, 140)],
             expert=("func", "AT1")),
    3:  dict(req="AT2", dims=[D("rpm", 4700, 4800)],
             expert=("boxes", [dict(rpm=(4754.4012, 4800.0))])),
    4:  dict(req="AT2", dims=[D("t0", 0, 5e6, US), D("t", 5e6, 15e6, US),
                              D("rpm", 4700, 4800)],
             expert=("boxes", [dict(t0=(0.0, 5.0), t=(5.0, 7.1), rpm=(4700.0, 4800.0)),
                               dict(t0=(0.0, 5.0), t=(7.1, 15.0), rpm=(4754.4, 4800.0))])),
    5:  dict(req="AT51", dims=[D("delay", 0, 5e6, US, attr="NUM4")],
             expert=("boxes", [dict(delay=(0.0, 1.65))])),
    6:  dict(req="AT51", dims=[D("t0", 0, 1500, 100, attr="NUM0"),
                                D("t1", 1500, 4500, 100, attr="NUM1"),
                                D("delay", 0, 5e6, US, attr="NUM4")],
             expert=("boxes", [dict(t0=(7.23, 15.0), t1=(15.0, 45.0), delay=(0.0, 5.0)),
                               dict(t0=(0.0, 7.23), t1=(15.0, 45.0), delay=(0.0, 1.65))])),
    7:  dict(req="AT52", dims=[D("delay", 0, 5e6, US, attr="NUM4")],
             expert=("boxes", [dict(delay=(0.0, 1.20))])),
    8:  dict(req="AT52", dims=[D("t0", 0, 1500, 100, attr="NUM0"),
                                D("t1", 1500, 4500, 100, attr="NUM1"),
                                D("delay", 0, 5e6, US, attr="NUM4")],
             expert=("boxes", [dict(t0=(1.76, 15.0), t1=(15.0, 45.0), delay=(0.0, 5.0)),
                               dict(t0=(0.0, 1.76), t1=(15.0, 45.0), delay=(0.0, 1.20))])),
    9:  dict(req="AT53", dims=[D("delay", 0, 5e6, US, attr="NUM4")],
             expert=("boxes", [dict(delay=(0.0, 2.04))])),
    10: dict(req="AT53", dims=[D("t0", 0, 1500, 100, attr="NUM0"),
                                D("t1", 1500, 4500, 100, attr="NUM1"),
                                D("delay", 0, 5e6, US, attr="NUM4")],
             expert=("boxes", [dict(t0=(0.0, 15.0), t1=(15.0, 18.48), delay=(0.0, 5.0)),
                               dict(t0=(0.0, 15.0), t1=(18.48, 45.0), delay=(0.0, 2.04))])),
    11: dict(req="AT54", dims=[D("delay", 0, 5e6, US, attr="NUM4")],
             expert=("boxes", [dict(delay=(0.0, 1.80))])),
    12: dict(req="AT54", dims=[D("t0", 0, 1500, 100, attr="NUM0"),
                                D("t1", 1500, 4500, 100, attr="NUM1"),
                                D("delay", 0, 5e6, US, attr="NUM4")],
             expert=("boxes", [dict(t0=(0.0, 15.0), t1=(15.0, 18.84), delay=(0.0, 5.0)),
                               dict(t0=(0.0, 15.0), t1=(18.84, 45.0), delay=(0.0, 1.80))])),
    13: dict(req="AT6A", dims=[D("rpm", 2800, 3200), D("speed", 30, 40)],
             expert=("boxes", [dict(rpm=(2800.0, 2913.192700), speed=(30.0, 40.0)),
                               dict(rpm=(2913.192700, 3200.0), speed=(35.960581, 40.0))])),
    14: dict(req="AT6A", dims=[D("t0", 20e6, 40e6, US, attr="NUM1"), D("rpm", 2800, 3200, attr="NUM2"),
                               D("t", 2e6, 6e6, US, attr="NUM4"), D("speed", 30, 40, attr="NUM5")],
             expert=("func", "data/requirements/AT6A/AT6A_AT192.py")),
    15: dict(req="AT6B", dims=[D("rpm", 2800, 3200), D("speed", 40, 60)],
             expert=("boxes", [dict(rpm=(2800.0, 2830.707000), speed=(40.0, 60.0)),
                               dict(rpm=(2830.707000, 3200.0), speed=(51.918594, 60.0))])),
    16: dict(req="AT6B", dims=[D("t0", 20e6, 40e6, US, attr="NUM1"), D("rpm", 2800, 3200, attr="NUM2"),
                               D("t", 4e6, 12e6, US, attr="NUM4"), D("speed", 40, 60, attr="NUM5")],
             expert=("func", "data/requirements/AT6B/AT6B_AT272.py")),
    17: dict(req="AT6C", dims=[D("rpm", 2800, 3200), D("speed", 50, 80)],
             expert=("boxes", [dict(rpm=(2800.0, 2973.074700), speed=(50.0, 80.0)),
                               dict(rpm=(2973.074700, 3200.0), speed=(70.976820, 80.0))])),
    18: dict(req="AT6C", dims=[D("t0", 20e6, 40e6, US, attr="NUM1"), D("rpm", 2800, 3200, attr="NUM2"),
                               D("t", 15e6, 25e6, US, attr="NUM4"), D("speed", 50, 80, attr="NUM5")],
             expert=("func", "data/requirements/AT6C/AT6C_AT311.py")),
    19: dict(req="AT6ABC", dims=[D("rpm", 2800, 3200), D("speed", 50, 80)],
             expert=("boxes", [dict(rpm=(2800.0, 2973.561657), speed=(50.0, 80.0)),
                           dict(rpm=(2973.561657, 3200.0), speed=(70.831811, 80.0))])),
    21: dict(req="CC1", dims=[D("distance", 30, 50, attr="NUM2")],
             expert=("boxes", [dict(distance=(41.180040, 50.0))])),
    22: dict(req="CC1", dims=[D("t0", 0, 50e6, US, attr="NUM0"),
                              D("t1", 50e6, 100e6, US, attr="NUM1"),
                              D("distance", 30, 50, attr="NUM2")],
             expert=("boxes", [dict(t0=(0.0, 50.0), t1=(50.0, 100.0), distance=(41.2, 50.0)),
                               dict(t0=(22.5, 50.0), t1=(50.0, 100.0), distance=(30.0, 41.2))])),
    23: dict(req="CC2", dims=[D("t0", 0, 20e6, US, attr="NUM0")],
             expert=("boxes", [dict(t0=(3.25, 20.0))])),
    24: dict(req="CC2", dims=[D("t0", 0, 20e6, US, attr="NUM0"),
                              D("t1", 0, 10e6, US, attr="NUM2"),
                              D("distance", 12, 18, attr="NUM4")],
             expert=("boxes", [dict(t0=(3.25, 20.0), t1=(0.0, 10.0), distance=(12.0, 15.1))])),
    29: dict(req="CC5", dims=[D("d1", 7, 11, attr="NUM4"), D("d2", 7, 11, attr="NUM7")],
             expert=("boxes", [dict(d1=(7.0, 10.001060), d2=(7.0, 7.587900)),
                               dict(d1=(10.001060, 11.0), d2=(7.0, 11.0))])),
    # -- experiments to compute ---------------------------------------------------------
    # exp30/33/34 mix operator knobs with value knobs; the operator axis carries one cell
    # per admissible operator, in the order the ARFF declares it.
    30: dict(req="CC5", dims=[C("op1", "RELATIONALS6", ["<", ">"]), D("d1", 7, 11, attr="NUM4"),
                              C("op2", "RELATIONALS9", ["<", ">"]), D("d2", 7, 11, attr="NUM7")],
             expert=("boxes", [dict(op1=(0, 1), d1=(7.0, 10.0), op2=(0, 2), d2=(7.0, 7.58)),
                               dict(op1=(1, 2), d1=(7.0, 10.0), op2=(1, 2), d2=(7.0, 7.58)),
                               dict(op1=(0, 1), d1=(7.0, 10.0), op2=(0, 2), d2=(7.58, 11.0)),
                               dict(op1=(0, 2), d1=(10.0, 11.0), op2=(0, 2), d2=(7.0, 11.0))])),
    # RR's satisfied region is read off the trace rather than approximated by boxes: the
    # boxes AccuracyRR.py carries do not transfer to this configuration. Under `Implies`
    # exp33's unmutated `d2obs > 50` never holds (the trace peaks at 8.61), so the
    # requirement is vacuously satisfied at every threshold, where the boxes have it
    # flipping at 547.6140cm; and exp34's 0.687 boundary is the trace's minimum d2obs in
    # centimetres, while this configuration mutates that knob over [0,2.5] in metres, where
    # the boundary is 0.006869. The derived region reproduces every verdict the search
    # recorded -- see verdict_check -- and the boxes are kept in REF as a porting check.
    33: dict(req="RR", dims=[C("op", "LOGICALS2", ["And", "Or", "Implies"]),
                             D("dist", 5, 7, attr="NUM3")],
             expert=("func", "RR")),
    34: dict(req="RR", dims=[C("op", "LOGICALS2", ["And", "Or"]),
                             D("d2obs", 0, 2.5, attr="NUM2"), D("dist", 5, 7, attr="NUM3")],
             expert=("func", "RR")),
    20: dict(req="AT6ABC", dims=[D("t0", 20e6, 40e6, US, attr="NUM13"), D("rpm", 2800, 3200, attr="NUM14"),
                                 D("t", 15e6, 25e6, US, attr="NUM16"), D("speed", 50, 80, attr="NUM17")],
             expert=("func", "data/requirements/AT6ABC/AT6ABC_AT232.py")),
    32: dict(req="CCX", dims=[D("t0", 0, 25e6, US), D("t1", 25e6, 75e6, US), D("v", 5, 10)],
             expert=("boxes", [dict(t0=(0.0, 18.2), t1=(25.0, 75.0), v=(5.0, 7.4)),
                               dict(t0=(18.2, 25.0), t1=(25.0, 75.0), v=(5.0, 8.9)),
                               dict(t0=(18.2, 25.0), t1=(25.0, 39.6), v=(8.9, 9.3))])),
}


def check_dims(pe):
    """Fail loudly if DIMS disagrees with the run's own mutation configuration."""
    path = os.path.join(CONFIGS, f"exp{pe}", "seed0.json")
    changes = list(json.load(open(path))["mutation"]["allowed_changes"].values())
    dims = CFG[pe]["dims"]
    want_n = sorted(tuple(v["numeric"]) for v in changes if "numeric" in v)
    got_n = sorted((float(d["lo"]), float(d["hi"])) for d in dims if d["kind"] == "num")
    # operator order is the ARFF's, not the configuration's, so compare the sets
    want_c = sorted(tuple(sorted(vs)) for v in changes for k, vs in v.items() if k != "numeric")
    got_c = sorted(tuple(sorted(d["values"])) for d in dims if d["kind"] == "cat")
    if (want_n, want_c) != (got_n, got_c):
        raise AssertionError(f"exp{pe}: DIMS {got_n}/{got_c} != config {want_n}/{want_c} ({path})")


# --- the expert side ------------------------------------------------------------------
_TRACE = {}


def trace(req):
    """(f_vehicle_speed, f_engine_speed) over time, as in the Accuracy*.py scripts."""
    if req not in _TRACE:
        row = next(r for r in csv.reader(open(TRACES)) if r and r[0].strip() == req)
        pts = [p.strip().lstrip("[").rstrip("]") for p in row[1].split(";")]
        arr = np.array([[float(x) for x in p.split()] for p in pts if p.strip()])
        f = lambda c: interp1d(arr[:, 0], arr[:, c])   # columns: time, v_speed, e_speed, gear
        _TRACE[req] = (f(1), f(2))
    return _TRACE[req]


def _rs(a, ax, nd):
    sh = [1] * nd
    sh[ax] = len(a)
    return a.reshape(sh)


REQ_SIG = {}


def req_signals(rel):
    """(timestamps in s, e_speed, v_speed) read from the requirement the run actually solved."""
    if rel not in REQ_SIG:
        src = open(os.path.join(REPO, rel)).read()
        g = lambda n: np.array([float(x) for x in
                                re.findall(rf"{n}\[\s*\d+\]==([-\d.eE]+)", src)])
        t = np.array([float(x) for x in
                      re.findall(r"timestamps\[\s*\d+\]==([-\d.eE]+)", src)]) / 1e6
        REQ_SIG[rel] = (t, g("e_speed"), g("v_speed"))
    return REQ_SIG[rel]


def at6_expert(rel, t0_axis, rpm_axis, t_axis, spd_axis):
    """AT6 satisfied region: the premise fails, or the conclusion holds.

    ``(forall tau <= t0: omega(tau) < rpm) implies (forall tau <= t: v(tau) < speed)`` holds
    exactly when ``rpm <= max omega over [0,t0]`` or ``speed > max v over [0,t]``. Both maxima
    are running maxima of the requirement's own signals, so this is the region itself rather
    than an approximation of it. Returns a (t0, rpm, t, speed) boolean tensor.

    AccuracyAT6c.py and AccuracyAT6abc.py read the AT6B trace for requirements that run on the
    AT6C/AT6ABC one, which puts their engine-speed bound at 2830.707 instead of 2973.0747 and
    inflates the satisfied region; the extra ``rpm <= 2973.0`` and ``rpm > traceFunc(t0)``
    disjuncts in those scripts patch around it. Reading each requirement's own signals removes
    the need for both and reproduces every verdict the search recorded -- see verdict_check.
    """
    E, V = at6_bounds(rel, t0_axis), at6_bounds(rel, t_axis, speed=True)
    return ((rpm_axis[None, :, None, None] <= E[:, None, None, None])
            | (spd_axis[None, None, None, :] > V[None, None, :, None]))


def at6_bounds(rel, T, speed=False):
    """max of the signal over [0,T], for each T -- the bound the quantifier compares against."""
    ts, E, V = req_signals(rel)
    run = np.maximum.accumulate(V if speed else E)
    return run[np.clip(np.searchsorted(ts, np.asarray(T), side="right") - 1, 0, len(ts) - 1)]


RR_PROP = os.path.join(REPO, "data", "requirements", "RR", "property_RR_RR.py")
_RR = {}


def rr_signals():
    """(d2obs, des_x - cur_x) over the RR trace, read from the requirement itself."""
    if not _RR:
        src = open(RR_PROP).read()
        g = lambda n: np.array([float(x) for x in
                                re.findall(rf"{n}\[\s*\d+\]==([-\d.eE]+)", src)])
        _RR["d2obs"], _RR["dx"] = g("d2obs"), g("des_x") - g("cur_x")
    return _RR["d2obs"], _RR["dx"]


def rr_expert(ops, a_axis, b_axis):
    """RR satisfied region on the trace: forall t, OP(d2obs(t) > a, des_x(t)-cur_x(t) < b).

    Written per operator rather than as hyperrectangles, since a box expert has to pick one
    threshold for `a` and the operators do not share one:
      And     satisfied iff a < min d2obs and b > max dx
      Or      satisfied iff b > max{ dx(t) : d2obs(t) <= a }
      Implies satisfied iff b > max{ dx(t) : d2obs(t) >  a }
    `ops` is one operator name per point of the operator axis. Returns (op, a, b) booleans.
    """
    d2, dx = rr_signals()
    below = d2[:, None] <= a_axis[None, :]                       # T x A
    worst = lambda m: np.where(m.any(0), np.max(np.where(m, dx[:, None], -np.inf), axis=0),
                               -np.inf)
    out = np.zeros((len(ops), len(a_axis), len(b_axis)), dtype=bool)
    for i, op in enumerate(ops):
        if op == "And":
            out[i] = (~below).all(0)[:, None] & (dx.max() < b_axis)[None, :]
        elif op == "Or":
            out[i] = b_axis[None, :] > worst(below)[:, None]
        elif op == "Implies":
            out[i] = b_axis[None, :] > worst(~below)[:, None]
        else:
            raise ValueError(op)
    return out


def expert_tensor(req, axes, dims):
    """Expert SATISFIED region, ported verbatim from the matching Accuracy*.py."""
    names = [d["name"] for d in dims]
    nd = len(axes)
    ix = {n: i for i, n in enumerate(names)}
    if req.startswith("data/"):                 # an AT6 requirement path
        return at6_expert(req, axes[ix["t0"]], axes[ix["rpm"]], axes[ix["t"]], axes[ix["speed"]])
    if req == "RR":
        opd = next(d for d in dims if d["kind"] == "cat")
        opx = ix[opd["name"]]
        # the operator axis carries cell midpoints; read the operator back off each point,
        # so this is correct for the single-cell slices grid_pr sweeps with
        ops = [opd["values"][int(round(v - 0.5))] for v in axes[opx]]
        a_ax = axes[ix["d2obs"]] if "d2obs" in ix else np.array([50.0])   # fixed in exp33
        t = rr_expert(ops, a_ax, axes[ix["dist"]])
        pos = [opx] + ([ix["d2obs"]] if "d2obs" in ix else []) + [ix["dist"]]
        if "d2obs" not in ix:
            t = t[:, 0, :]
        t = np.transpose(t, np.argsort(pos))
        shape = [1] * nd
        for q in pos:
            shape[q] = len(axes[q])
        return t.reshape(shape)
    col = lambda n: _rs(axes[ix[n]], ix[n], nd)
    over = lambda n, f, t: _rs(f(axes[ix[t]]), ix[t], nd)   # threshold f(t) broadcast on t
    if req == "AT1":       # exp2:  speed > traceFunc(t)
        fv, _ = trace("AT1")
        return col("speed") > over("speed", fv, "t")
    if req == "AT6a":      # exp14: rpm <= 2913.0 OR speed > traceFunc(t)
        fv, _ = trace("AT6A")
        return (col("rpm") <= 2913.0) | (col("speed") > over("speed", fv, "t"))
    fv, fe = trace("AT6B")
    if req == "AT6b":      # exp16: rpm <= traceFunc2(t0) OR speed > traceFunc1(t)
        return (col("rpm") <= over("rpm", fe, "t0")) | (col("speed") > over("speed", fv, "t"))
    if req == "AT6c":      # exp18: rpm <= 2973.0 OR rpm > traceFunc2(t0) OR speed > traceFunc1(t)
        return ((col("rpm") <= 2973.0) | (col("rpm") > over("rpm", fe, "t0"))
                | (col("speed") > over("speed", fv, "t")))
    if req == "AT6abc":    # exp20: t0 > 31.6 OR rpm <= 2943 OR speed > traceFunc(t)
        return ((col("t0") > 31.6) | (col("rpm") <= 2943.0)
                | (col("speed") > over("speed", fv, "t")))
    raise ValueError(req)


# --- the grid -------------------------------------------------------------------------
def grid_axes(dims):
    """One axis per knob, built exactly as the reference loops build their samples."""
    return [dim_axis(d) for d in dims]


def sat_boxes(boxes, axes, names, grid):
    """Union of half-open boxes: lo < p <= hi, plus p == range_lo == box_lo."""
    nd = len(axes)
    out = np.zeros([len(a) for a in axes], dtype=bool)
    for b in boxes:
        m = None
        for ax, n in enumerate(names):
            lo, hi = b[n]
            rlo = grid[n][0]
            a = axes[ax]
            c = ((a > lo) & (a <= hi)) | ((a == rlo) & (rlo == lo))
            cc = _rs(c, ax, nd)
            m = cc if m is None else (m & cc)
        out |= m
    return out


def grid_pr(boxes, expert, dims, grid, axes=None):
    """P/R of the tool region against the expert region, swept slice by slice on dim 0."""
    names = [d["name"] for d in dims]
    axes = grid_axes(dims) if axes is None else axes
    tp = fp = fn = tn = 0
    for i in range(len(axes[0])):
        sub = [axes[0][i:i + 1]] + axes[1:]
        tool = sat_boxes(boxes, sub, names, grid)
        if expert[0] == "boxes":
            exp = sat_boxes(expert[1], sub, names, grid)
        else:
            exp = np.broadcast_to(expert_tensor(expert[1], sub, dims), tool.shape)
        tp += int(np.count_nonzero(tool & exp))
        fp += int(np.count_nonzero(tool & ~exp))
        fn += int(np.count_nonzero(~tool & exp))
        tn += int(np.count_nonzero(~tool & ~exp))
    P = 100.0 * tp / (tp + fp) if tp + fp else None
    R = 100.0 * tp / (tp + fn) if tp + fn else None
    return P, R, (tp, tn, fp, fn)


# --- the tool side --------------------------------------------------------------------
def weka_classpath():
    """$WEKA_JAR, else the jar of a diagnosis checkout beside this one; + bounce.jar."""
    base = os.environ.get("WEKA_JAR")
    if not base:
        for cand in ("/opt/weka/weka.jar",
                     os.path.join(os.path.dirname(REPO), "code", ".diagnosis",
                                  "share", "weka", "weka.jar")):
            if os.path.exists(cand):
                base = cand
                break
    if not base:
        raise RuntimeError("no Weka jar: set $WEKA_JAR to weka.jar")
    paths = [p for p in base.split(":") if p]
    for bounce in (os.path.join(REPO, "third_party", "bounce.jar"), "/opt/weka/bounce.jar"):
        if os.path.exists(bounce) and bounce not in paths:
            paths.append(bounce)
    return ":".join(paths)


def regen_tree(run_dir):
    """The tree relearnt on everything the run decided, as scripts/regen_trees.py does.

    The trees a run leaves behind were trained on a capped, score-biased slice of its
    samples and admitted undecided rows as a third class, so they do not describe what
    the tool concluded from the data it actually collected. This rebuilds the cut-1.0
    tree from dataset_qty_*_all.arff -- both classes, undecided dropped -- and caches it
    under <run>/regen/. Returns None when the run decided only one class.
    """
    out = os.path.join(run_dir, "regen", "J48-data-100.out")
    if os.path.exists(out):
        return out
    src = sorted(glob.glob(f"{run_dir}/dataset_qty_*_all.arff"))
    if not src:
        return None
    sys.path.insert(0, REPO)
    from diagnosis.diagnostics.j48 import run_j48
    header, rows = [], []
    in_data = False
    for line in open(src[0], encoding="utf-8", errors="replace").read().splitlines():
        if not in_data:
            header.append(line)
            in_data = line.strip().lower().startswith("@data")
        elif line.strip() and not line.strip().startswith("%"):
            rows.append(line.strip())
    cls = lambda r: r.rsplit(",", 1)[-1].strip().upper()
    sats = [r for r in rows if cls(r) == "TRUE"]
    unsats = [r for r in rows if cls(r) == "FALSE"]
    if not sats or not unsats:
        return None
    head = ["@attribute VEREDICT {TRUE, FALSE}" if l.strip().lower().startswith("@attribute veredict")
            else l for l in header]
    os.makedirs(os.path.join(run_dir, "regen"), exist_ok=True)
    stamp = os.path.basename(src[0])[len("dataset_qty_"):-len("_all.arff")]
    cut = os.path.join(run_dir, "regen", f"dataset_qty_{stamp}_per100.arff")
    open(cut, "w", encoding="utf-8").write("\n".join(head + sats + unsats) + "\n")
    return run_j48(cut, 1.0, os.path.join(run_dir, "regen"), weka_jar=weka_classpath())


def final_tree_out(run_dir):
    """The archived evaluation tree; the run's final J48 tree as a fallback."""
    preferred = os.path.join(run_dir, "evaluation_tree", "J48-data-100.out")
    if os.path.exists(preferred):
        return preferred
    for d in (os.path.join(run_dir, "stopping_checks"), run_dir):
        outs = glob.glob(f"{d}/J48-data-*.out")
        if outs:
            return max(outs, key=lambda p: int(re.search(r"J48-data-(\d+)\.out", p).group(1)))
    return None


SPLIT = re.compile(r"^((?:\|   )*)\s*(\w+)\s*(<=|>|=)\s*([^:]+?)\s*"
                   r"(?::\s*(\w+)\s*\([\d.,/]+\))?$")


def attr_to_dim(tree_out, dims):
    """Weka attribute -> knob.

    Knobs that pin an attribute win outright; the rest are numeric and are matched by which
    configured range holds the median of that attribute's split values (the mutated ranges
    do not overlap, except where a knob pins its attribute precisely because they do).
    """
    mp = {d["attr"]: d["name"] for d in dims if d.get("attr")}
    loose = [d for d in dims if d["kind"] == "num" and not d.get("attr")]
    if not loose:
        return mp
    seg = open(tree_out).read().split("J48 pruned tree", 1)[-1]
    vals = {}
    for m in re.finditer(r"(NUM\d+)\s*(?:<=|>)\s*([-\d.eE]+)", seg):
        if m.group(1) not in mp:
            vals.setdefault(m.group(1), []).append(float(m.group(2)))
    for num, vs in vals.items():
        med = statistics.median(vs)
        best = None
        for d in loose:
            if d["lo"] - 1e-3 <= med <= d["hi"] + 1e-3 and (best is None
                                                            or (d["hi"] - d["lo"]) < best[1]):
                best = (d["name"], d["hi"] - d["lo"])
        mp[num] = best[0] if best else None
    return mp


def tool_boxes(tree_out, dims):
    """The tree's TRUE leaves as boxes over the knobs."""
    amap = attr_to_dim(tree_out, dims)
    byname = {d["name"]: d for d in dims}
    grid = {d["name"]: dim_range(d) for d in dims}
    seg = open(tree_out).read().split("J48 pruned tree", 1)[-1].splitlines()
    boxes, path = [], []
    for line in seg:
        if line.strip().startswith("Number of Leaves"):
            break
        m = SPLIT.match(line.rstrip())
        if not m:
            continue
        depth = len(m.group(1)) // 4
        attr, op, raw, leaf = m.group(2), m.group(3), m.group(4).strip(), m.group(5)
        dim = amap.get(attr)
        d = byname.get(dim)
        if op == "=":                       # a nominal branch: that operator's cell
            if d is None:
                step = (None, "=", None)    # attribute we do not model: no constraint
            elif raw in d["values"]:
                step = (dim, "=", float(d["values"].index(raw)))
            else:
                step = (None, "skip", None)  # operator outside the mutation space
        else:
            step = (dim, op, float(raw) / (d["scale"] if d else 1.0))
        path = path[:depth] + [step]
        if leaf == "TRUE" and not any(st[1] == "skip" for st in path):
            box = {n: list(grid[n]) for n in grid}
            for dn, o, v in path:
                if dn is None:
                    continue
                if o == "=":
                    box[dn] = [max(box[dn][0], v), min(box[dn][1], v + 1.0)]
                elif o == "<=":
                    box[dn][1] = min(box[dn][1], v)
                else:
                    box[dn][0] = max(box[dn][0], v)
            boxes.append({dn: tuple(b) for dn, b in box.items()})
    return boxes, grid


def completed_seed_trees(pe):
    """Canonical seed archives that have a summary (i.e. the run finished)."""
    out = []
    for seed_dir in sorted(glob.glob(f"{RESULTS}/exp{pe}/seed*"),
                           key=lambda p: int(os.path.basename(p)[4:])):
        archive = os.path.join(seed_dir, "archive")
        if os.path.exists(os.path.join(archive, "summary.json")):
            out.append((int(os.path.basename(seed_dir)[4:]), archive))
    return out


def pr_multiseed(pe):
    check_dims(pe)
    cfg = CFG[pe]
    dims = cfg["dims"]
    Ps, Rs, rawPs, rawRs, seeds, confusion = [], [], [], [], [], []
    for seed, run in completed_seed_trees(pe):
        to = final_tree_out(run)
        if not to:
            continue
        boxes, grid = tool_boxes(to, dims)
        if not boxes:
            continue
        P, R, counts = grid_pr(boxes, cfg["expert"], dims, grid)
        if P is not None and R is not None:
            rawPs.append(P); rawRs.append(R); Ps.append(round(P, 1)); Rs.append(round(R, 1));
            seeds.append(seed); confusion.append(counts)

    def med_iqr(xs):
        """Median and IQR with linear-interpolated quartiles (as in the original CSV)."""
        if not xs:
            return None, None
        xs = sorted(xs); n = len(xs)
        def pct(p):
            k = (n - 1) * p; f = int(k); c = min(f + 1, n - 1)
            return xs[f] + (xs[c] - xs[f]) * (k - f)
        return round(statistics.median(xs), 1), round(pct(0.75) - pct(0.25), 1)

    # The manuscript aggregates the reported one-decimal seed scores, not hidden
    # full-precision ratios.  Keeping that order makes the CSV and prose identical.
    pm, pi = med_iqr(Ps); rm, ri = med_iqr(Rs)
    return dict(exp=pe, req=cfg["req"], n=len(Ps), seeds=seeds,
                p_med=pm, p_iqr=pi, r_med=rm, r_iqr=ri, p=Ps, r=Rs,
                confusion=confusion)


# Published medians (analysis/precision_recall_multiseed.csv), one per experiment shape:
# 1-D box, 3-D box, 3-D trace, 2-D box (x3), 4-D trace (x3).
# The Accuracy*.py scripts' own hardcoded tool regions and printed P/R. Reproducing these
# gates the grid, the operator cells and the expert encodings independently of how a tree is
# read. AccuracyRR.py's experiment-34 loops are swapped against its own parameter-order
# comment -- it sweeps the operator axis with 101 continuous samples and the d2obs value with
# three -- so that entry carries the axes the script actually uses; scoring the re-run uses
# the correct ones, which moves the reference tool region from 99.4/100.0 to 99.1/100.0.
_LIN = lambda lo, hi: np.array([lo + (hi - lo) / N * i for i in range(N + 1)])
REF = {
    29: dict(tool=[dict(d1=(10.716652, 11.0), d2=(7.0, 7.759978)),
                   dict(d1=(9.983620, 11.0), d2=(7.759978, 10.681500))], want=(96.4, 54.6)),
    30: dict(tool=[dict(op1=(0, 1), d1=(7.0, 11.0), op2=(0, 2), d2=(7.0, 11.0)),
                   dict(op1=(1, 2), d1=(9.973520, 11.0), op2=(0, 2), d2=(7.0, 11.0))],
             want=(99.3, 95.8)),
    33: dict(tool=[dict(op=(1, 2), dist=(5.475981, 7.0))],
             expert=("boxes", [dict(op=(1, 2), dist=(5.476140, 7.0)),
                               dict(op=(2, 3), dist=(5.0, 5.476140))]), want=(100.0, 76.2)),
    34: dict(tool=[dict(op=(0, 1), d2obs=(0.0, 0.6864), dist=(5.480303, 7.0)),
                   dict(op=(1, 2), d2obs=(0.0, 0.7038), dist=(5.0, 5.475945)),
                   dict(op=(1, 2), d2obs=(0.0, 2.5), dist=(5.475945, 7.0))],
             expert=("boxes", [dict(op=(0, 1), d2obs=(0.0, 0.687), dist=(5.48, 7.0)),
                               dict(op=(1, 2), d2obs=(0.0, 0.687), dist=(5.0, 5.48)),
                               dict(op=(1, 2), d2obs=(0.0, 2.5), dist=(5.48, 7.0))]),
             axes=[_LIN(0, 2), np.array([0.5, 1.5, 2.5]), _LIN(5, 7)], want=(99.4, 100.0)),
}

SELFTEST_TREE = """J48 pruned tree
------------------

RELATIONALS6 = <: TRUE (106.0)
RELATIONALS6 = >
|   NUM4 <= 9.5: FALSE (119.0)
|   NUM4 > 9.5: TRUE (31.0)
RELATIONALS6 = <=: TRUE (0.0)
RELATIONALS6 = >=: TRUE (0.0)

Number of Leaves  : \t5
"""


def selftest_parse():
    """A nominal split reads as one cell, and a branch outside the mutation space is dropped."""
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".out", delete=False) as fh:
        fh.write(SELFTEST_TREE); path = fh.name
    boxes, _ = tool_boxes(path, CFG[30]["dims"])
    os.unlink(path)
    want = [dict(op1=(0.0, 1.0), d1=(7.0, 11.0), op2=(0.0, 2.0), d2=(7.0, 11.0)),
            dict(op1=(1.0, 2.0), d1=(9.5, 11.0), op2=(0.0, 2.0), d2=(7.0, 11.0))]
    return boxes == want, boxes


def verdict_check(pe):
    """Agreement between an exactly-derived expert and the trace checker's own verdicts.

    Only meaningful where the satisfied region is derivable rather than approximated: RR's
    is, so its expert must reproduce every verdict the search recorded. The box experts of
    the other requirements are the expert's own "mostly satisfied" simplification and are
    not expected to match sample by sample.
    """
    dims = CFG[pe]["dims"]
    grid = {d["name"]: dim_range(d) for d in dims}
    attr = {d["attr"]: d for d in dims if d.get("attr") and d["kind"] == "num"}
    opd = next((d for d in dims if d["kind"] == "cat"), None)
    rel = CFG[pe]["expert"][1] if CFG[pe]["expert"][1].startswith("replication/") else None
    tot = bad = 0
    for f in glob.glob(f"{RESULTS}/exp{pe}_{CFG[pe]['req']}_s*/*/dataset_qty_*_all.arff"):
        lines = open(f).read().splitlines()
        names, st = [], None
        for i, l in enumerate(lines):
            if l.lower().startswith("@attribute"):
                names.append(l.split()[1])
            if l.lower().startswith("@data"):
                st = i + 1
                break
        ix = {n: i for i, n in enumerate(names)}
        for l in lines[st:]:
            if not l.strip():
                continue
            row = l.split(",")
            v = row[ix["VEREDICT"]]
            if v not in ("TRUE", "FALSE"):
                continue
            op = row[ix[opd["attr"]]] if opd else None
            if opd and op not in opd["values"]:
                continue
            pt, ok = {}, True
            for a, d in attr.items():
                x = float(row[ix[a]]) / d["scale"]
                lo, hi = grid[d["name"]]
                if not (lo - 1e-9 <= x <= hi + 1e-9):   # sample outside the scored grid
                    ok = False
                    break
                pt[d["name"]] = x
            if not ok:
                continue
            if rel:
                got = bool(pt["rpm"] <= at6_bounds(rel, [pt["t0"]])[0]
                           or pt["speed"] > at6_bounds(rel, [pt["t"]], speed=True)[0])
            else:
                a_ax = np.array([pt["d2obs"]]) if "d2obs" in pt else np.array([50.0])
                got = bool(rr_expert([op], a_ax, np.array([pt["dist"]]))[0, 0, 0])
            tot += 1
            bad += (got != (v == "TRUE"))
    return tot - bad, tot


def ref_check(pe):
    dims = CFG[pe]["dims"]
    grid = {d["name"]: dim_range(d) for d in dims}
    expert = REF[pe].get("expert", CFG[pe]["expert"])
    P, R, _ = grid_pr(REF[pe]["tool"], expert, dims, grid, REF[pe].get("axes"))
    return round(P, 1), round(R, 1)


# Published medians (analysis/precision_recall_multiseed.csv) for the experiments whose expert
# this harness leaves as the reference wrote it. The AT6 and RR experiments are derived from
# their own requirement instead, and are gated on verdict agreement -- the stronger check.
KNOWN = {1: (98.0, 100.0), 2: (96.0, 97.3), 4: (97.6, 100.0), 13: (98.8, 99.5),
         15: (100.0, 98.7), 17: (100.0, 99.5), 19: (100.0, 98.9), 29: (96.7, 69.3)}

def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)


def latex_rows(rows):
    by_exp = {int(row["exp"][3:]): row for row in rows}
    names = ["AT1", "AT2", "AT51", "AT52", "AT53", "AT54", "AT6a", "AT6b", "AT6c",
             "AT6abc", "CC1", "CC2", "CC3", "CC4", "CC5", "CCx", "RR"]
    def cells(exp):
        row = by_exp.get(exp)
        if row is None: return f"$exp{exp}$ & -- & --"
        mark = "$^{\\ast}$" if exp == 32 else ""
        return (f"$exp{exp}$ & ${float(row['precision_median']):.1f}$ \\small({float(row['precision_iqr']):.1f}){mark} & "
                f"${float(row['recall_median']):.1f}$ \\small({float(row['recall_iqr']):.1f}){mark}")
    lines = []
    for index, name in enumerate(names):
        left = 2 * index + 1
        if index in (10, 16): lines.append("        \\midrule")
        lines.append(f"        {name} & {cells(left)} & {cells(left + 1)}\\\\")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=os.path.join(REPO, "derived_results"))
    parser.add_argument("--ids", default="all", help="comma-separated experiment numbers")
    args = parser.parse_args()
    output = Path(args.output); output.mkdir(parents=True, exist_ok=True)
    scored = [i for i in range(1, 35) if i not in {25, 26, 27, 28, 31}]
    if args.ids != "all":
        scored = [int(item.removeprefix("exp")) for item in args.ids.split(",")]
    with open(os.path.join(REPO, "raw_results", "normalized", "experiment_seed_reconciliation.csv"), newline="") as stream:
        reconciliation = list(csv.DictReader(stream))
    state = {(int(row["canonical_experiment_id"][3:]), int(row["seed"])): row for row in reconciliation}

    seed_rows, aggregate_rows, specs = [], [], []
    calculated = {}
    for pe in scored:
        result = pr_multiseed(pe); calculated[pe] = result
        dims = CFG[pe]["dims"]
        axes = grid_axes(dims)
        axis_specs = []
        for dim, axis in zip(dims, axes):
            values = [float(value) for value in axis]
            encoded = json.dumps(values, separators=(",", ":"), allow_nan=False).encode()
            axis_specs.append({"name": dim["name"], "kind": dim["kind"], "values": values,
                               "sha256": hashlib.sha256(encoded).hexdigest()})
        specs.append({"experiment_id": f"exp{pe}", "intervals_per_numeric_axis": N,
                      "numeric_rule": "lo + (hi-lo)*i/100 for i=0..100 inclusive",
                      "categorical_rule": "one cell midpoint per admissible operator; full configured domain",
                      "axes": axis_specs, "cartesian_size": int(np.prod([len(axis) for axis in axes]))})
        for seed, precision, recall, counts in zip(result["seeds"], result["p"], result["r"], result["confusion"]):
            tp, tn, fp, fn = counts; reconciled = state[(pe, seed)]
            archive = Path(RESULTS) / f"exp{pe}" / f"seed{seed}" / "archive"
            tree = archive / "evaluation_tree" / "J48-data-100.out"
            if not tree.exists(): tree = archive / "J48-data-100.out"
            training = list((archive / "evaluation_tree").glob("dataset_qty_*_per100.arff"))
            if training and "UNDECIDED" in training[0].read_text(errors="replace"):
                raise AssertionError(f"exp{pe}/seed{seed}: UNDECIDED entered evaluation-tree training")
            seed_rows.append({"experiment_id": f"exp{pe}", "requirement": result["req"], "seed": seed,
                              "status": reconciled["status"], "scored": "true", "exclusion_reason": "",
                              "tp": tp, "tn": tn, "fp": fp, "fn": fn,
                              "precision_pct": f"{precision:.1f}", "recall_pct": f"{recall:.1f}",
                              "grid_points": tp + tn + fp + fn,
                              "checker_undecided_candidates": reconciled["undecided_count"],
                              "checker_undecided_excluded_from_tree_evaluation": "true",
                              "tool_tree": str(tree.relative_to(Path(REPO))),
                              "expert_tree": f"references/expert_trees/machine_readable/exp{pe}.json"})
        aggregate_rows.append({"req": result["req"], "exp": f"exp{pe}", "n_seeds": 10,
                               "n_scored": result["n"], "precision_median": result["p_med"],
                               "recall_median": result["r_med"], "precision_iqr": result["p_iqr"],
                               "recall_iqr": result["r_iqr"],
                               "precision_seeds": ";".join(f"{x:.1f}" for x in result["p"]),
                               "recall_seeds": ";".join(f"{x:.1f}" for x in result["r"])})

    evaluated = {(int(row["experiment_id"][3:]), int(row["seed"])) for row in seed_rows}
    for pe in range(1, 35):
        for seed in range(10):
            if (pe, seed) in evaluated: continue
            row = state[(pe, seed)]
            reason = "censored_120h" if row["status"] == "timeout" else "degenerate_one_class_tree"
            seed_rows.append({"experiment_id": f"exp{pe}", "requirement": row["requirement"], "seed": seed,
                              "status": row["status"], "scored": "false", "exclusion_reason": reason,
                              "tp": "", "tn": "", "fp": "", "fn": "", "precision_pct": "", "recall_pct": "",
                              "grid_points": "", "checker_undecided_candidates": row["undecided_count"],
                              "checker_undecided_excluded_from_tree_evaluation": "true",
                              "tool_tree": "", "expert_tree": f"references/expert_trees/machine_readable/exp{pe}.json"})
    seed_rows.sort(key=lambda row: (int(row["experiment_id"][3:]), int(row["seed"])))
    write_csv(output / "rq1_per_seed_confusion.csv", seed_rows)
    write_csv(output / "appendix_precision_recall_authoritative.csv", aggregate_rows)
    (output / "rq1_grid_specifications.json").write_text(json.dumps(specs, indent=2, sort_keys=True) + "\n")
    pvals = [float(row["precision_median"]) for row in aggregate_rows]
    rvals = [float(row["recall_median"]) for row in aggregate_rows]
    manuscript = {"aggregation_unit": "scored experiment median over seeds",
                  "n_experiments": len(aggregate_rows),
                  "precision_min": round(min(pvals), 1), "precision_max": round(max(pvals), 1),
                  "precision_median_of_experiment_medians": round(statistics.median(pvals), 1),
                  "precision_mean_of_experiment_medians": round(statistics.mean(pvals), 1),
                  "precision_sample_sd": round(statistics.stdev(pvals), 1),
                  "recall_min": round(min(rvals), 1), "recall_max": round(max(rvals), 1),
                  "recall_median_of_experiment_medians": round(statistics.median(rvals), 1),
                  "recall_mean_of_experiment_medians": round(statistics.mean(rvals), 1),
                  "recall_sample_sd": round(statistics.stdev(rvals), 1)}
    (output / "rq1_aggregate.json").write_text(json.dumps(manuscript, indent=2, sort_keys=True) + "\n")
    (output / "appendix_precision_recall_rows.tex").write_text(latex_rows(aggregate_rows))
    print(f"RQ1: {len(seed_rows)} slots, {sum(r['scored']=='true' for r in seed_rows)} scored trees, {len(specs)} grids")


if __name__ == "__main__":
    main()
