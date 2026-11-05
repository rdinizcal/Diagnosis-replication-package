#!/usr/bin/env python3
"""Validate materialized configs, registry coverage, hashes, and immutable inputs."""
from __future__ import annotations
import csv, hashlib, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def fail(msg): print(f"ERROR: {msg}", file=sys.stderr); return 1
def schema_errors(data, schema, path="$"):
    out=[];typ=schema.get("type")
    types={"object":dict,"array":list,"string":str,"integer":int,"number":(int,float),"boolean":bool,"null":type(None)}
    if typ and not isinstance(data,types[typ]):return [f"{path}: expected {typ}"]
    if isinstance(data,dict):
        for key in schema.get("required",[]):
            if key not in data:out.append(f"{path}: missing {key}")
        for key,sub in schema.get("properties",{}).items():
            if key in data:out.extend(schema_errors(data[key],sub,f"{path}.{key}"))
    return out

def main():
    schema = json.loads((ROOT / "experiments/config.schema.json").read_text())
    required = schema["required"]
    with (ROOT / "experiments/configuration_hashes.csv").open(newline="") as f:
        configs = list(csv.DictReader(f))
    errors = 0
    for row in configs:
        p = ROOT / row["path"]
        if not p.is_file(): errors += fail(f"missing config {p}"); continue
        d = json.loads(p.read_text())
        for e in schema_errors(d,schema):errors += fail(f"schema {row['path']}: {e}")
        if sha(p) != row["sha256"]: errors += fail(f"hash mismatch: {row['path']}")
        for block in ("interval_inference", "two_tier_timeout", "adaptive_range", "time_quantization"):
            if block not in d.get("heuristics", {}): errors += fail(f"{row['path']}: missing heuristic {block}")
        for field in ("seed", "stopping"):
            if field not in d.get("ga", {}): errors += fail(f"{row['path']}: missing ga.{field}")
    if len(configs) != 480: errors += fail(f"expected 480 materialized primary configs, found {len(configs)}")
    with (ROOT / "experiments/auxiliary_configuration_hashes.csv").open(newline="") as f:
        auxiliary=list(csv.DictReader(f))
    aux_schema=json.loads((ROOT/"experiments/auxiliary.schema.json").read_text())
    for row in auxiliary:
        p=ROOT/row["path"]
        if not p.is_file() or sha(p)!=row["sha256"]:errors += fail(f"auxiliary config hash mismatch: {row['path']}");continue
        selected=schema if row["schema"]=="config.schema.json" else aux_schema
        for e in schema_errors(json.loads(p.read_text()),selected):errors += fail(f"schema {row['path']}: {e}")
    if len(auxiliary)!=5:errors += fail(f"expected 5 materialized auxiliary configurations, found {len(auxiliary)}")
    with (ROOT / "experiments/registry.csv").open(newline="") as f: registry = list(csv.DictReader(f))
    if [r["paper_experiment_id"] for r in registry] != [f"exp{i}" for i in range(1, 35)]:
        errors += fail("canonical registry is not exactly exp1..exp34 in order")
    with (ROOT / "inputs/provenance/inputs.csv").open(newline="") as f:
        for row in csv.DictReader(f):
            p = ROOT / row["artifact_path"]
            if not p.is_file() or sha(p) != row["sha256"]: errors += fail(f"input checksum mismatch: {p}")
    try:
        import jsonschema
        validator = jsonschema.Draft202012Validator(schema)
        for row in configs:
            for e in validator.iter_errors(json.loads((ROOT / row["path"]).read_text())):
                errors += fail(f"schema {row['path']}: {e.message}")
        print("JSON Schema engine: jsonschema")
    except ImportError:
        print("JSON Schema engine unavailable; built-in schema type/required validator used")
    print(f"validated {len(configs)} primary + {len(auxiliary)} auxiliary configs, 34 canonical experiments, and immutable inputs")
    return int(bool(errors))

if __name__ == "__main__": raise SystemExit(main())
