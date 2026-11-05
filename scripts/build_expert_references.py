#!/usr/bin/env python3
"""Build auditable expert-tree specifications and vector renderings for exp1-exp34."""
from __future__ import annotations

import ast
import csv
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

csv.field_size_limit(10**8)


ROOT = Path(__file__).resolve().parents[1]
REF = ROOT / "references" / "expert_trees"
ORIGINAL = REF / "original_accuracy_scripts"

SOURCE = {
    **{1: ("AccuracyAT1.py", 1), 2: ("AccuracyAT1.py", 2)},
    **{3: ("AccuracyAT2.py", 1), 4: ("AccuracyAT2.py", 2)},
    **{5: ("AccuracyAT51.py", 1), 6: ("AccuracyAT51.py", 2)},
    **{7: ("AccuracyAT52.py", 1), 8: ("AccuracyAT52.py", 2)},
    **{9: ("AccuracyAT53.py", 1), 10: ("AccuracyAT53.py", 2)},
    **{11: ("AccuracyAT54.py", 1), 12: ("AccuracyAT54.py", 2)},
    **{13: ("AccuracyAT6a.py", 1), 14: ("AccuracyAT6a.py", 2)},
    **{15: ("AccuracyAT6b.py", 1), 16: ("AccuracyAT6b.py", 2)},
    **{17: ("AccuracyAT6c.py", 1), 18: ("AccuracyAT6c.py", 2)},
    **{19: ("AccuracyAT6abc.py", 1), 20: ("AccuracyAT6abc.py", 2)},
    **{21: ("AccuracyCC1.py", 1), 22: ("AccuracyCC1.py", 2)},
    **{23: ("AccuracyCC2.py", 1), 24: ("AccuracyCC2.py", 2)},
    **{25: ("AccuracyCC3.py", 1), 26: ("AccuracyCC3.py", 2)},
    **{27: ("AccuracyCC4.py", 1), 28: ("AccuracyCC4.py", 2)},
    **{29: ("AccuracyCC5.py", 1), 30: ("AccuracyCC5.py", 2)},
    **{31: ("AccuracyCCx.py", 1), 32: ("AccuracyCCx.py", 2)},
    **{33: ("AccuracyRR.py", 1), 34: ("AccuracyRR.py", 2)},
}


def n(name: str, attribute: str, unit: str, scale: float = 1.0) -> dict:
    return {"name": name, "kind": "numeric", "arff_attribute": attribute,
            "unit": unit, "archive_to_expert_scale": scale}


def c(name: str, attribute: str, values: list[str]) -> dict:
    return {"name": name, "kind": "categorical", "arff_attribute": attribute,
            "values": values, "unit": "categorical", "archive_to_expert_scale": 1.0}


# Dimension order is the order used by each archived Accuracy*.py Cartesian product.
DIMS = {
    "AT1": [n("t0", "NUM0", "s", 1e6), n("t1", "NUM1", "s", 1e6), n("speed", "NUM2", "mph")],
    "AT2": [n("t0", "NUM0", "s", 1e6), n("t1", "NUM1", "s", 1e6), n("rpm", "NUM2", "rpm")],
    "AT5": [n("t0", "NUM0", "s", 100), n("t1", "NUM1", "s", 100), n("delay", "NUM4", "s", 1e6)],
    "AT6": [n("t0", "NUM1", "s", 1e6), n("rpm", "NUM2", "rpm"), n("t1", "NUM4", "s", 1e6), n("speed", "NUM5", "mph")],
    "AT6ABC": [n("t0", "NUM13", "s", 1e6), n("rpm", "NUM14", "rpm"), n("t1", "NUM16", "s", 1e6), n("speed", "NUM17", "mph")],
    "CC1": [n("t0", "NUM0", "s", 1e6), n("t1", "NUM1", "s", 1e6), n("distance", "NUM2", "m")],
    "CC2": [n("t0", "NUM0", "s", 1e6), n("t1", "NUM1", "s", 1e6), n("distance", "NUM2", "m")],
    "CC3": [c("quantifier0", "QUANTIFIERS0", ["ForAll", "Exists"]), c("quantifier1", "QUANTIFIERS1", ["ForAll", "Exists"]), c("logical", "LOGICALS2", ["And", "Or"])],
    "CC4": [c("quantifier0", "QUANTIFIERS0", ["ForAll", "Exists"]), c("quantifier1", "QUANTIFIERS1", ["ForAll", "Exists"]), n("distance", "NUM4", "m")],
    "CC5": [c("relation0", "RELATIONALS6", ["<", ">"]), n("distance0", "NUM4", "m"), c("relation1", "RELATIONALS9", ["<", ">"]), n("distance1", "NUM7", "m")],
    "CCX": [n("t0", "NUM0", "s", 1e6), n("t1", "NUM1", "s", 1e6), n("distance", "NUM2", "m")],
    "RR": [c("logical", "LOGICALS2", ["And", "Or", "Implies"]), n("d2obs", "NUM2", "m"), n("distance", "NUM3", "m")],
}


def family(exp: int) -> str:
    if exp <= 2: return "AT1"
    if exp <= 4: return "AT2"
    if exp <= 12: return "AT5"
    if exp <= 18: return "AT6"
    if exp <= 20: return "AT6ABC"
    if exp <= 22: return "CC1"
    if exp <= 24: return "CC2"
    if exp <= 26: return "CC3"
    if exp <= 28: return "CC4"
    if exp <= 30: return "CC5"
    if exp <= 32: return "CCX"
    return "RR"


def arrays(path: Path, case: int) -> tuple[list[float], list[list[float]] | None]:
    tree = ast.parse(path.read_text())
    for node in ast.walk(tree):
        if not isinstance(node, ast.If) or not isinstance(node.test, ast.Compare):
            continue
        test = node.test
        if not (isinstance(test.left, ast.Name) and test.left.id == "exp"
                and isinstance(test.ops[0], ast.Eq)):
            continue
        try:
            current = ast.literal_eval(test.comparators[0])
        except Exception:
            continue
        if current != case:
            continue
        values = {}
        for statement in node.body:
            if not isinstance(statement, ast.Assign) or not isinstance(statement.targets[0], ast.Name):
                continue
            key = statement.targets[0].id
            if key in {"totalRange", "expertSatis"}:
                values[key] = ast.literal_eval(statement.value.args[0])
        return values["totalRange"], values.get("expertSatis")
    raise RuntimeError(f"cannot extract case {case} from {path}")


TRACE_RULES = {
    2: "speed > vehicle_speed(t1); t0 is irrelevant",
    14: "rpm <= running_max(engine_speed,[0,t0]) OR speed > running_max(vehicle_speed,[0,t1])",
    16: "rpm <= running_max(engine_speed,[0,t0]) OR speed > running_max(vehicle_speed,[0,t1])",
    18: "rpm <= running_max(engine_speed,[0,t0]) OR speed > running_max(vehicle_speed,[0,t1])",
    20: "rpm <= running_max(engine_speed,[0,t0]) OR speed > running_max(vehicle_speed,[0,t1])",
    33: "forall t: logical(d2obs(t) > 50, desired_x(t)-current_x(t) < distance)",
    34: "forall t: logical(d2obs(t) > d2obs_threshold, desired_x(t)-current_x(t) < distance)",
}


def bounds(total: list[float], dims: list[dict]) -> list[dict]:
    return [{**dim, "minimum": total[2*i], "maximum": total[2*i+1]}
            for i, dim in enumerate(dims)]


def boxes(raw: list[list[float]] | None, dims: list[dict]) -> list[dict]:
    if raw is None:
        return []
    return [{dim["name"]: {"lower_exclusive": row[2*i], "upper_inclusive": row[2*i+1]}
             for i, dim in enumerate(dims)} for row in raw]


def write_dot(spec: dict, path: Path) -> None:
    label = spec["canonical_experiment_id"] + " expert satisfied region"
    lines = ["digraph ExpertTree {", "rankdir=TB;", "node [shape=box,fontname=Helvetica];",
             f'root [label="{label}"];']
    if spec["evaluator"]["type"] == "trace_rule":
        rule = spec["evaluator"]["rule"].replace('"', '\\"')
        lines += [f'rule [label="{rule}"];', 'root -> rule;', 'rule -> sat [label="true"];',
                  'rule -> unsat [label="false"];', 'sat [label="SATISFIED",shape=ellipse];',
                  'unsat [label="VIOLATED",shape=ellipse];']
    else:
        lines.append('or [label="OR"];'); lines.append('root -> or;')
        for i, box in enumerate(spec["evaluator"]["satisfied_boxes"]):
            text = "\\n".join(f"{key}: ({value['lower_exclusive']}, {value['upper_inclusive']}]" for key, value in box.items())
            lines += [f'b{i} [label="{text}"];', f'or -> b{i};', f'b{i} -> sat{i};',
                      f'sat{i} [label="SATISFIED",shape=ellipse];']
        lines.append('root -> unsat [label="otherwise"];'); lines.append('unsat [label="VIOLATED",shape=ellipse];')
    lines.append("}")
    path.write_text("\n".join(lines) + "\n")


def assignment_series(source: Path, name: str) -> list[float]:
    text = source.read_text()
    return [float(value) for value in re.findall(rf"{re.escape(name)}\[\s*\d+\]\s*==\s*([-\d.eE]+)", text)]


def trace_rows(exp: int) -> list[dict[str, float]]:
    if exp == 2:
        with (ROOT / "data" / "traces" / "tracesAT.csv").open(newline="") as stream:
            row = next(item for item in csv.reader(stream) if item and item[0].strip() == "AT1")
        points = [part.strip().lstrip("[").rstrip("]") for part in row[1].split(";")]
        values = [[float(value) for value in part.split()] for part in points if part]
        return [{"time_s": item[0], "vehicle_speed": item[1], "engine_speed": item[2], "gear": item[3]}
                for item in values]
    if exp in (14, 16, 18, 20):
        req = {14: "AT6A/AT6A_AT192.py", 16: "AT6B/AT6B_AT272.py",
               18: "AT6C/AT6C_AT311.py", 20: "AT6ABC/AT6ABC_AT232.py"}[exp]
        source = ROOT / "data" / "requirements" / req
        times = [value / 1e6 for value in assignment_series(source, "timestamps")]
        engine, vehicle = assignment_series(source, "e_speed"), assignment_series(source, "v_speed")
        return [{"time_s": t, "engine_speed": e, "vehicle_speed": v}
                for t, e, v in zip(times, engine, vehicle)]
    if exp in (33, 34):
        source = ROOT / "data" / "requirements" / "RR" / "property_RR_RR.py"
        times = [value / 1e6 for value in assignment_series(source, "timestamps")]
        d2 = assignment_series(source, "d2obs")
        desired, current = assignment_series(source, "des_x"), assignment_series(source, "cur_x")
        if not times:
            times = list(range(min(len(d2), len(desired), len(current))))
        return [{"time_s": t, "d2obs": d, "desired_minus_current_x": des-cur}
                for t, d, des, cur in zip(times, d2, desired, current)]
    raise ValueError(exp)


def write_witnesses(exp: int) -> tuple[str, str, str]:
    rows = trace_rows(exp)
    out = ROOT / "references" / "trace_witnesses" / "expert"
    out.mkdir(parents=True, exist_ok=True)
    csv_path = out / f"exp{exp}.csv"
    with csv_path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    extrema = {}
    for key in rows[0]:
        values = [float(row[key]) for row in rows]
        lo, hi = min(range(len(values)), key=values.__getitem__), max(range(len(values)), key=values.__getitem__)
        extrema[key] = {"minimum": values[lo], "minimum_time_s": rows[lo]["time_s"],
                        "maximum": values[hi], "maximum_time_s": rows[hi]["time_s"]}
    extrema_path = out / f"exp{exp}_extrema.json"
    extrema_path.write_text(json.dumps({"experiment_id": f"exp{exp}", "extrema": extrema,
                                        "derivation_rule": TRACE_RULES[exp]}, indent=2, sort_keys=True) + "\n")

    # Representative decided/undecided mutations are validation witnesses, not expert input.
    reps = []
    seed = ROOT / "raw_results" / "rq1_rq2" / f"exp{exp}" / "seed0" / "archive"
    arffs = sorted(seed.glob("dataset_qty_*_all.arff"))
    if arffs:
        attrs, data = [], False
        for line in arffs[0].read_text(errors="replace").splitlines():
            match = re.match(r"@attribute\s+(\S+)", line, re.I)
            if match: attrs.append(match.group(1))
            elif line.strip().lower() == "@data": data = True
            elif data and line.strip() and not line.lstrip().startswith("%"):
                values = next(csv.reader([line]))
                verdict = values[-1].strip().upper()
                if verdict not in {item["VEREDICT"] for item in reps}:
                    reps.append(dict(zip(attrs, values)))
    rep_path = out / f"exp{exp}_representative_mutations.csv"
    if reps:
        with rep_path.open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(reps[0])); writer.writeheader(); writer.writerows(reps)
    else:
        rep_path.write_text("VEREDICT\n")
    return tuple(str(path.relative_to(ROOT)) for path in (csv_path, extrema_path, rep_path))


def main() -> None:
    records = []
    dots = REF / "dot"; vectors = REF / "svg"; pdfs = REF / "pdf"
    dots.mkdir(parents=True, exist_ok=True); vectors.mkdir(parents=True, exist_ok=True); pdfs.mkdir(parents=True, exist_ok=True)
    for exp in range(1, 35):
        source_name, case = SOURCE[exp]
        source = ORIGINAL / source_name
        total, raw_boxes = arrays(source, case)
        dims = [dict(item) for item in DIMS[family(exp)]]
        original_total, original_dims = list(total), [dict(item) for item in dims]
        # Fixed dimensions are retained because they are part of the original expert tree.
        if exp == 33:
            # AccuracyRR uses centimetres for the distance axis; the corrected registry uses metres.
            original_dims = [n("d2obs", "NUM2", "cm"), c("logical", "LOGICALS2", ["And", "Or", "Implies"]),
                             n("distance", "NUM3", "cm")]
            total = [0.0, 3.0, 50.0, 50.0, 5.0, 7.0]
            dims = [DIMS["RR"][0], DIMS["RR"][1], DIMS["RR"][2]]
        elif exp == 34:
            original_dims = [c("logical", "LOGICALS2", ["And", "Or"]), n("d2obs", "NUM2", "m"),
                             n("distance", "NUM3", "cm")]
            total = [0.0, 2.0, 0.0, 2.5, 5.0, 7.0]
        trace = exp in TRACE_RULES
        derivation = "trace_rule_with_witness" if trace else "expert_region"
        witness_paths = write_witnesses(exp) if trace else (None, None, None)
        record = {
            "schema_version": 1,
            "canonical_experiment_id": f"exp{exp}",
            "requirement_family": family(exp),
            "dimensions": bounds(total, dims),
            "evaluator": ({"type": "trace_rule", "rule": TRACE_RULES[exp]}
                          if trace else {"type": "satisfied_region_union", "satisfied_boxes": boxes(raw_boxes, dims)}),
            "original_reference": {
                "path": f"references/expert_trees/original_accuracy_scripts/{source_name}",
                "case": case, "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                "author_identifier_verbatim": "fedformi_new",
                "creation_date_verbatim": "Thu May 16 00:11:33 2024",
                "role": "expert prediction and original grid evaluator",
            },
            "canonicalization": {
                "date": "2026-08-18", "author": "scripts/build_expert_references.py",
                "role": "mechanical transcription; trace-semantic correction where declared",
                "original_vs_corrected": ("corrected_from_trace; original AccuracyRR boxes retained in provenance"
                                          if exp in (33, 34) else "trace-derived canonical rule" if trace else "verbatim boxes"),
            },
            "trace_witness_derivation": {
                "status": derivation,
                "witness": witness_paths[0],
                "extrema": witness_paths[1],
                "representative_trace_check_mutations": witness_paths[2],
            },
        }
        if exp in (33, 34):
            record["original_reference"]["original_dimensions"] = bounds(original_total, original_dims)
            record["original_reference"]["original_satisfied_boxes"] = boxes(raw_boxes, original_dims)
            record["original_reference"]["known_issue"] = "Original AccuracyRR axis/units do not match the authoritative mutation registry; canonical evaluator is trace-derived."
        dot = dots / f"exp{exp}_expert.dot"; svg = vectors / f"exp{exp}_expert.svg"; pdf = pdfs / f"exp{exp}_expert.pdf"
        write_dot(record, dot)
        subprocess.run(["dot", "-Tsvg", str(dot), "-o", str(svg)], check=True)
        subprocess.run(["dot", "-Tpdf", str(dot), "-o", str(pdf)], check=True,
                       env={**os.environ, "SOURCE_DATE_EPOCH": "0"})  # byte-stable PDFs
        record["dot_path"] = str(dot.relative_to(ROOT)); record["vector_path"] = str(svg.relative_to(ROOT)); record["pdf_path"] = str(pdf.relative_to(ROOT))
        target = REF / "machine_readable" / f"exp{exp}.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
        records.append({"experiment_id": f"exp{exp}", "machine_readable_tree": str(target.relative_to(ROOT)),
                        "dot": str(dot.relative_to(ROOT)), "svg": str(svg.relative_to(ROOT)), "pdf": str(pdf.relative_to(ROOT)),
                        "svg_command": f"dot -Tsvg {dot.relative_to(ROOT)} -o {svg.relative_to(ROOT)}",
                        "pdf_command": f"dot -Tpdf {dot.relative_to(ROOT)} -o {pdf.relative_to(ROOT)}",
                        "derivation_status": derivation, "source": source_name, "source_case": case})
    with (REF / "INDEX.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0])); writer.writeheader(); writer.writerows(records)
    print("wrote 34 machine-readable expert trees and DOT/SVG/PDF renderings")


if __name__ == "__main__":
    main()
