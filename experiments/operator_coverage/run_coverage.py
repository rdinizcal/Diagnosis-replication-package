"""
Operator-coverage harness.

For every (synthetic requirement, applicable operator) pair this script:
  1. parses the requirement with the tool's own parser  -> typed AST
  2. applies the operator (operators.py)                 -> mutant AST
  3. wraps the mutant in Not(...) EXACTLY as the GA does (ga.py:1123-1124),
     prints it with the tool's printer, and injects it with the tool's
     ``replace_property_assertion`` (preserving every trace constraint)
  4. runs the resulting property script with the tool's harness -> verdict

Success criterion (coverage completeness, NOT effectiveness): every OP1..OP15
is applied at least once and yields a non-ERROR, solver-evaluable mutant
(a well-formed change the trace-checker can decide as SAT or UNSAT).

Reuses tool components only; nothing under diagnosis/ is modified.

Usage:
    python run_coverage.py [--seed 42] [--timeout 50]
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import random
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
# Make the tool importable when run from anywhere (repo root = code/Diagnosis).
REPO = HERE.parents[1] / "tool"
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))  # so `import operators` works from any CWD

from diagnosis.ga import replace_property_assertion            # noqa: E402
from diagnosis.harness import run_property_script, Verdict      # noqa: E402
from diagnosis.lang.theodore_parser import load_formula_from_property  # noqa: E402
from diagnosis.lang.python_printer import formula_to_python_expr       # noqa: E402
from diagnosis.lang.ast import Not                              # noqa: E402
from diagnosis.lang.internal_encoder import formula_to_internal_obj  # noqa: E402

import operators  # noqa: E402  (local module, same folder)

REQ_DIR = HERE / "requirements"
REQUIREMENTS = ["SYN1_time.py", "SYN2_index.py", "SYN3_record.py"]

PRECONDITIONS = {
    "OP1": "a Boolean predicate is present", "OP2": "a relational operator is present",
    "OP3": "an explicit Not node is present", "OP4": "a Boolean connective is present",
    "OP4a": "an Implies node with ordered operands is present",
    "OP5": "a time quantifier has a recognized bounded range guard",
    "OP6": "an index quantifier has a recognized bounded range guard",
    "OP7": "a record quantifier has a recognized bounded range guard",
    "OP8": "a time arithmetic term is present", "OP9": "an index arithmetic term is present",
    "OP10": "a value arithmetic term is present", "OP11": "a time constant is present",
    "OP12": "an index constant is present", "OP13": "a value constant is present",
    "OP14": "two signals are available at an index access",
    "OP15": "two signals are available at a time access",
}


def evaluate_mutant(original_lines, mutant_formula, timeout, output_path=None):
    """Inject Not(mutant) into the original script and run it -> Verdict."""
    nline = formula_to_python_expr(Not(mutant_formula))   # mirror ga.py:1123-1124
    new_lines = replace_property_assertion(original_lines, nline)
    if output_path is not None:
        output_path.write_text("".join(new_lines), encoding="utf-8")
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as tf:
        tf.writelines(new_lines)
        tmp = tf.name
    try:
        res = run_property_script(tmp, timeout=timeout)
    finally:
        os.unlink(tmp)
    return res.verdict, nline


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--timeout", type=int, default=50)
    ap.add_argument("--outdir", default=str(HERE))
    ap.add_argument("--update-expected", action="store_true",
                    help="replace expected_results.json after intentional semantic changes")
    args = ap.parse_args()
    random.seed(args.seed)  # determinism (operators are first-match, but be explicit)

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    rows = []          # detailed: one row per (op, req) application
    fixtures = []      # exactly one minimal successful fixture per operator
    generated = outdir / "generated"
    generated.mkdir(parents=True, exist_ok=True)
    per_op = {op_id: {"desc": desc, "applicable": False, "fired": 0, "reqs": [], "verdicts": []}
              for op_id, desc, _ in operators.CATALOGUE}

    for req in REQUIREMENTS:
        path = REQ_DIR / req
        formula = load_formula_from_property(str(path))
        original_lines = path.read_text(encoding="utf-8").splitlines(keepends=True)

        for op_id, desc, fn in operators.CATALOGUE:
            muts = fn(formula)
            if not muts:
                continue
            m = muts[0]
            per_op[op_id]["applicable"] = True
            fixture_dir = generated / op_id
            is_minimal_fixture = not per_op[op_id]["fired"]
            if is_minimal_fixture:
                fixture_dir.mkdir(parents=True, exist_ok=True)
                (fixture_dir / "original.py").write_text("".join(original_lines), encoding="utf-8")
                (fixture_dir / "original_ast.json").write_text(
                    json.dumps(formula_to_internal_obj(formula), indent=2) + "\n", encoding="utf-8")
                (fixture_dir / "mutated_ast.json").write_text(
                    json.dumps(formula_to_internal_obj(m.formula), indent=2) + "\n", encoding="utf-8")
            verdict, nline = evaluate_mutant(
                original_lines, m.formula, args.timeout,
                fixture_dir / "mutated.py" if is_minimal_fixture else None)
            non_error = verdict != Verdict.ERROR
            if non_error:
                per_op[op_id]["fired"] += 1
                per_op[op_id]["reqs"].append(req)
                per_op[op_id]["verdicts"].append(verdict.name)
                if is_minimal_fixture:
                    fixtures.append({
                        "operator": op_id,
                        "requirement": req,
                        "trace_fixture": f"requirements/{req}",
                        "applicability_precondition": PRECONDITIONS[op_id],
                        "original_source": f"generated/{op_id}/original.py",
                        "original_ast": f"generated/{op_id}/original_ast.json",
                        "mutated_source": f"generated/{op_id}/mutated.py",
                        "mutated_ast": f"generated/{op_id}/mutated_ast.json",
                        "parser_result": "parsed",
                        "injection_result": "injected",
                        "trace_checker_verdict": verdict.name,
                        "expected_evaluable": True,
                    })
            rows.append({
                "op": op_id,
                "description": desc,
                "requirement": req,
                "applicability_precondition": PRECONDITIONS[op_id],
                "original_ast": json.dumps(formula_to_internal_obj(formula), separators=(",", ":")),
                "mutated_ast": json.dumps(formula_to_internal_obj(m.formula), separators=(",", ":")),
                "original_subtree": m.original,
                "mutated_subtree": m.mutated,
                "parser_result": "parsed",
                "injection_result": "injected",
                "verdict": verdict.name,
                "evaluable": "yes" if non_error else "no",
            })
            print(f"[{op_id:5}] {req:16} {m.original!r:>22} -> {m.mutated!r:<22} "
                  f"verdict={verdict.name}")

    # --- write detailed CSV --------------------------------------------------
    detail_csv = outdir / "operator_coverage_detail.csv"
    with detail_csv.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["op", "description", "requirement",
                                           "applicability_precondition", "original_ast",
                                           "mutated_ast", "original_subtree", "mutated_subtree",
                                           "parser_result", "injection_result", "verdict", "evaluable"])
        w.writeheader()
        w.writerows(rows)

    # --- write per-operator summary CSV -------------------------------------
    summary_csv = outdir / "operator_coverage.csv"
    with summary_csv.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["operator", "description", "applicable", "fired_count",
                    "verdicts", "triggering_requirements"])
        for op_id, desc, _ in operators.CATALOGUE:
            d = per_op[op_id]
            w.writerow([op_id, desc, "yes" if d["applicable"] else "no", d["fired"],
                        ";".join(d["verdicts"]), ";".join(d["reqs"])])

    # --- write rendered Markdown table --------------------------------------
    md = outdir / "operator_coverage.md"
    lines = [
        "# Operator coverage results",
        "",
        "One row per mutation operator from Table `tab:mutations`. **Fired** counts the",
        "synthetic requirements on which the operator produced a well-formed, "
        "solver-evaluable mutant (verdict SAT or UNSAT, never ERROR).",
        "",
        "| Operator | Description | Applicable? | Fired (count) | Verdicts | Triggering requirement(s) |",
        "|----------|-------------|:-----------:|:-------------:|----------|---------------------------|",
    ]
    for op_id, desc, _ in operators.CATALOGUE:
        d = per_op[op_id]
        lines.append(f"| {op_id} | {desc} | {'yes' if d['applicable'] else 'no'} "
                     f"| {d['fired']} | {';'.join(d['verdicts']) or '-'} "
                     f"| {', '.join(d['reqs']) or '-'} |")
    md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    actual_path = outdir / "actual_results.json"
    actual_path.write_text(json.dumps(fixtures, indent=2) + "\n", encoding="utf-8")
    expected_path = outdir / "expected_results.json"
    if args.update_expected:
        expected_path.write_text(json.dumps(fixtures, indent=2) + "\n", encoding="utf-8")
    elif not expected_path.is_file():
        raise FileNotFoundError(f"missing {expected_path}; initialize with --update-expected")
    else:
        expected = json.loads(expected_path.read_text(encoding="utf-8"))
        if fixtures != expected:
            raise AssertionError("operator results differ from expected_results.json")

    # --- verdict / success summary ------------------------------------------
    all_ops = [op_id for op_id, _, _ in operators.CATALOGUE]
    fired_ops = [op for op in all_ops if per_op[op]["fired"] >= 1]
    missing = [op for op in all_ops if per_op[op]["fired"] < 1]
    print("\n" + "=" * 64)
    print(f"Operators exercised (>=1 non-ERROR mutant): {len(fired_ops)}/{len(all_ops)}")
    if missing:
        print(f"NOT exercised: {missing}")
        print("RESULT: INCOMPLETE")
        print(f"Wrote: {summary_csv.name}, {detail_csv.name}, {md.name}")
        return 1
    print("RESULT: COMPLETE - every operator produced a solver-evaluable mutant.")
    print(f"Wrote: {summary_csv.name}, {detail_csv.name}, {md.name}, {actual_path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
