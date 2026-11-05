#!/usr/bin/env python3
"""Validate the RQ3 run configurations against the frozen AST mutator."""
from __future__ import annotations

import json
import math
import random
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tool"))

from diagnosis.config import load_config  # noqa: E402
from diagnosis.lang.ast import And, Exists, ForAll, Implies, IntConst, Or, RealConst  # noqa: E402
from diagnosis.lang.theodore_parser import load_formula_from_property  # noqa: E402
from diagnosis.mutation.api import _mutate_by_positions, _walk  # noqa: E402

CONFIGS = ROOT / "experiments" / "rq3_sensitivity" / "configs"
OUT = ROOT / "analysis" / "rq3_configuration_validation.json"


def node_value(node):
    if isinstance(node, (IntConst, RealConst)):
        return node.value
    if isinstance(node, And):
        return "And"
    if isinstance(node, Or):
        return "Or"
    if isinstance(node, Implies):
        return "Implies"
    if isinstance(node, ForAll):
        return "ForAll"
    if isinstance(node, Exists):
        return "Exists"
    raise AssertionError(f"unsupported configured node type: {type(node).__name__}")


def expected_family(node):
    if isinstance(node, (IntConst, RealConst)):
        return "numeric"
    if isinstance(node, (And, Or, Implies)):
        return "logical"
    if isinstance(node, (ForAll, Exists)):
        return "quantifier"
    raise AssertionError(f"no mutation family for {type(node).__name__}")


def same_value(actual, expected) -> bool:
    if isinstance(actual, (int, float)) and isinstance(expected, (int, float)):
        return math.isclose(float(actual), float(expected), rel_tol=0, abs_tol=1e-9)
    return actual == expected


def main() -> None:
    paths = sorted(CONFIGS.rglob("seed*.json"))
    assert len(paths) == 140, f"expected 140 configurations, found {len(paths)}"
    variants: dict[tuple[str, str], list[Path]] = {}
    mutation_checks = 0

    for path in paths:
        raw = json.loads(path.read_text(encoding="utf-8"))
        cfg = load_config(path)
        requirement = path.parent.parent.name
        variant = path.parent.name
        variants.setdefault((requirement, variant), []).append(path)

        seed = int(path.stem.removeprefix("seed"))
        assert cfg.ga.seed == seed
        requirement_path = ROOT / raw["input"]["requirement_file"]
        assert requirement_path.is_file(), requirement_path
        formula = load_formula_from_property(requirement_path)
        nodes = list(_walk(formula))

        mutation = raw["mutation"]
        positions = mutation["allowed_positions"]
        changes = {int(key): value for key, value in mutation["allowed_changes"].items()}
        originals = {int(key): value for key, value in mutation["original_values"].items()}
        assert positions and len(positions) == len(set(positions))
        assert set(positions) == set(changes) == set(originals)
        assert mutation["max_mutations"] >= 1
        effective_max = min(mutation["max_mutations"], len(positions))
        assert raw["replication_metadata"]["effective_max_simultaneous_mutations"] == effective_max

        for position in positions:
            assert 0 <= position < len(nodes), f"{path}: invalid position {position}"
            node = nodes[position]
            family = expected_family(node)
            assert set(changes[position]) == {family}, (
                f"{path}: position {position} expects {family}, has {set(changes[position])}"
            )
            assert mutation[f"enable_{family}_perturbation" if family == "numeric" else f"enable_{family}_flip"]
            assert same_value(node_value(node), originals[position]), (
                f"{path}: original mismatch at {position}: {node_value(node)!r} != {originals[position]!r}"
            )

            changed = False
            for trial in range(20):
                mutant = _mutate_by_positions(formula, [position], cfg.mutation, random.Random(trial))
                if mutant != formula:
                    changed = True
                    break
            assert changed, f"{path}: position {position} cannot produce a mutation"
            mutation_checks += 1

    assert len(variants) == 28
    for key, group in variants.items():
        assert {int(path.stem.removeprefix("seed")) for path in group} == set(range(5)), key
        canonical = []
        for path in group:
            data = json.loads(path.read_text(encoding="utf-8"))
            data["ga"]["seed"] = 0
            data["ga"]["target_sats"] = "RUN_RECORD"  # per run, as recorded in its summary.json
            data["input"]["output_dir"] = "SEED_OUTPUT"
            data["replication_metadata"]["run_record"] = "RUN_RECORD"
            canonical.append(data)
        assert all(item == canonical[0] for item in canonical[1:]), f"non-run drift in {key}"

    report = {
        "status": "pass",
        "configurations": len(paths),
        "requirement_configuration_pairs": len(variants),
        "seed_histogram": dict(sorted(Counter(int(path.stem.removeprefix("seed")) for path in paths).items())),
        "configured_position_checks": mutation_checks,
        "checks": [
            "configuration parser",
            "requirement parser",
            "five-seed completeness and non-seed identity",
            "position existence and original-value agreement",
            "mutation-family/type compatibility",
            "per-position mutant generation",
        ],
    }
    OUT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"RQ3 configuration validation PASS: {len(paths)} configs, {mutation_checks} position checks")


if __name__ == "__main__":
    main()
