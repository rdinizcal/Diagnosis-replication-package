#!/usr/bin/env python3
"""Write the RQ3 run configurations: launch template + run record, runnable on this snapshot."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIGS = ROOT / "experiments" / "rq3_sensitivity" / "configs"
TEMPLATES = ROOT / "inputs" / "launch_templates" / "sensitivity"
RUNS = ROOT / "raw_results" / "rq3_sensitivity"

ORIGINALS = {
    "phi2": {12: -3.0, 15: 1.5},
    "phi3": {4: 0, 8: 9_900_000.0, 10: "And", 18: 3.5, 40: 1.0},
    "phi4": {8: 90, 12: 7.0, 15: 1.0},
    "AT53_AT119": {2: "And", 8: 30_000_000, 17: "ForAll", 18: "Implies"},
    "RR": {9: "And", 12: 50.0, 17: 20.0},
}


def rationale(label: str) -> str:
    if label == "B":
        return "broad: widest archived admissible domains and alternatives"
    if label == "G":
        return "guided: domain-plausible narrowed domains; one mutation at a time"
    if label in {"G2", "G3"}:
        return f"interaction: guided domains; up to {label[-1]} simultaneous mutations"
    return "omit: guided configuration with the position named by the suffix removed"


def main() -> None:
    count = 0
    for path in sorted(CONFIGS.rglob("seed*.json")):
        req, label = path.parent.parent.name, path.parent.name
        config = json.loads(path.read_text(encoding="utf-8"))
        mutation = config["mutation"]
        template = TEMPLATES / ("AT53" if req == "AT53_AT119" else req) / f"{req}_{label}.json"
        record = RUNS / req / label / path.stem / "summary.json"
        config["ga"]["target_sats"] = json.loads(record.read_text())["ga_target_sats"]
        prior_metadata = config.get("replication_metadata", {})
        historical = list(prior_metadata.get("historical_allowed_positions", mutation["allowed_positions"]))
        current = [38 if req == "phi3" and pos == 40 else pos for pos in historical]
        if historical != current and "40" in mutation["allowed_changes"]:
            mutation["allowed_changes"]["38"] = mutation["allowed_changes"].pop("40")
        mutation["allowed_positions"] = current
        original_values = {
            str(38 if req == "phi3" and pos == 40 else pos): ORIGINALS[req][pos]
            for pos in historical
        }
        mutation["original_values"] = original_values
        metadata = config.setdefault("replication_metadata", {})
        for stale in ("archive_caveat", "archive_run_configuration_byte_identity"):
            metadata.pop(stale, None)
        metadata.update({
            "configuration_provenance": "launch_template_with_run_record",
            "launch_template": str(template.relative_to(ROOT)),
            "run_record": str(record.relative_to(ROOT)),
            "label_rationale": rationale(label),
            "historical_position_namespace": "archived_2025_preorder_encoder",
            "historical_allowed_positions": historical,
            "current_position_namespace": "bundled_tool_preorder_encoder_at_05d0750",
            "position_translation": ({"40": 38} if req == "phi3" else {}),
            "effective_max_simultaneous_mutations": min(
                mutation["max_mutations"], len(mutation["allowed_positions"])
            ),
            **({"quantifier_mutation": "guarded range repair"} if req == "AT53_AT119" else {}),
        })
        if mutation["max_mutations"] > len(mutation["allowed_positions"]):
            metadata["label_rationale"] += (
                f"; effective maximum {len(mutation['allowed_positions'])} because only "
                f"{len(mutation['allowed_positions'])} positions are mutable"
            )
        path.write_text(json.dumps(config, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        count += 1
    print(f"enriched {count} RQ3 configurations")


if __name__ == "__main__":
    main()
