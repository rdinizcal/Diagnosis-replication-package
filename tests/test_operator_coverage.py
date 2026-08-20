from __future__ import annotations

import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tool"
OP_DIR = ROOT / "experiments" / "operator_coverage"
sys.path[:0] = [str(TOOL), str(OP_DIR)]

import operators  # noqa: E402
from diagnosis.lang.ast import And, Exists, ForAll, Implies, IntConst, RelOp, Var  # noqa: E402
from diagnosis.lang.theodore_parser import load_formula_from_property  # noqa: E402
from diagnosis.mutation.api import MutationConfig, _flip_quantifier  # noqa: E402


def fixture(name: str):
    return load_formula_from_property(str(OP_DIR / "requirements" / name))


def test_op4a_swaps_implies_operands() -> None:
    formula = fixture("SYN1_time.py")
    original = formula.body
    assert isinstance(original, Implies)
    mutant = operators.op4a(formula)[0].formula
    assert isinstance(mutant.body, Implies)
    assert mutant.body.left == original.right
    assert mutant.body.right == original.left


def test_op5_time_quantifier_repairs_guard() -> None:
    mutant = operators.op5(fixture("SYN1_time.py"))[0].formula
    assert isinstance(mutant, Exists)
    assert isinstance(mutant.body, And)
    assert isinstance(mutant.body.args[0], And)  # range guard


def test_op6_index_quantifier_repairs_guard() -> None:
    mutant = operators.op6(fixture("SYN2_index.py"))[0].formula
    assert isinstance(mutant, Exists)
    assert isinstance(mutant.body, And)
    assert isinstance(mutant.body.args[0], And)


def test_op7_record_quantifier_repairs_guard() -> None:
    mutant = operators.op7(fixture("SYN3_record.py"))[0].formula
    assert isinstance(mutant, ForAll)
    assert isinstance(mutant.body, Implies)
    assert isinstance(mutant.body.left, And)


def test_engine_does_not_flip_unguarded_quantifier() -> None:
    formula = ForAll(vars=["t"], body=RelOp(">", Var("t"), IntConst(0)))
    config = MutationConfig(allowed_changes={0: {"quantifier": ["Exists"]}})
    assert _flip_quantifier(formula, config, random.Random(0), 0) == formula
    assert operators.op5(formula) == []


def test_engine_does_not_guess_ambiguous_exists_guard() -> None:
    formula = Exists(vars=["r"], body=And(args=[
        RelOp(">", Var("r"), IntConst(0)), RelOp("<", Var("r"), IntConst(3))
    ]))
    config = MutationConfig(allowed_changes={0: {"quantifier": ["ForAll"]}})
    assert _flip_quantifier(formula, config, random.Random(0), 0) == formula
    assert operators.op7(formula) == []


def test_expected_manifest_has_complete_fixture_bundle() -> None:
    expected = json.loads((OP_DIR / "expected_results.json").read_text(encoding="utf-8"))
    assert {row["operator"] for row in expected} == {
        "OP1", "OP2", "OP3", "OP4", "OP4a", "OP5", "OP6", "OP7",
        "OP8", "OP9", "OP10", "OP11", "OP12", "OP13", "OP14", "OP15",
    }
    for row in expected:
        assert row["parser_result"] == "parsed"
        assert row["injection_result"] == "injected"
        assert row["trace_checker_verdict"] in {"SAT", "UNSAT"}
        for key in ("original_source", "original_ast", "mutated_source", "mutated_ast"):
            assert (OP_DIR / row[key]).is_file()
