#!/usr/bin/env python3
"""Materialize controlled MS=100/1000 configs from the main pipeline snapshot."""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAIN = HERE.parent / "rq1_effectiveness" / "configs"

for experiment in ("exp2", "exp4"):
    for ms in (100, 1000):
        for seed in range(10):
            source = MAIN / experiment / f"seed{seed}.json"
            config = json.loads(source.read_text())
            config["ga"]["target_sats"] = ms
            config["ga"]["stopping"]["mode"] = "count"
            config["ga"]["stopping"]["max_samples"] = None
            config["input"]["output_dir"] = f"raw_results/ms_sensitivity/{experiment}/MS{ms}/seed{seed}"
            config["replication_metadata"].update({
                "study": "ms_sensitivity",
                "MS": ms,
                "controlled_source": str(source.relative_to(HERE.parents[2])),
                "execution_status": "not_executed",
            })
            target = HERE / "configs" / experiment / f"MS{ms}" / f"seed{seed}.json"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(config, indent=2, sort_keys=True) + "\n")
print("materialized 40 current-snapshot MS sensitivity configurations")
