#!/usr/bin/env python3
"""Generate the release inventory after all other package files exist."""
from __future__ import annotations
import csv, hashlib, json, re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
EXCLUDED_TOP_LEVEL={".git","Diagnosis","ci-derived"}
IMAGE_DIGEST=json.loads((ROOT/"environment/versions.json").read_text()).get("container_image_digest","UNRECORDED")
FIELDS=["artifact_path","artifact_role","associated_claim_table_figure","experiment","seed","input_sha256","configuration_sha256","tool_commit","environment_image_digest","generation_command","status","checksum_sha256"]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def input_hashes(r):
    if not r:return ""
    d=__import__("json").loads((ROOT/r["path"]).read_text());parts=[]
    for key in ("requirement_file","traces_file"):
        q=ROOT/d["input"].get(key,"")
        if q.is_file():parts.append(f"{key}={sha(q)}")
    return ";".join(parts)
config={}
config_key={}
with (ROOT/"experiments/configuration_hashes.csv").open(newline="") as f:
    for r in csv.DictReader(f):
        config[r["path"]]=r;config_key[(r["study_id"],r["experiment_id"],r["seed"])]=r
prov={}
with (ROOT/"data/provenance/inputs.csv").open(newline="") as f:
    for r in csv.DictReader(f):prov[r["artifact_path"]]=r["sha256"]
def classify(rel):
    s=str(rel)
    if s.startswith("data/"):return "immutable input","C-RQ1;C-RQ3"
    if s.startswith("evaluation_inputs/"):return "historical evaluation input","C-RQ1;C-RQ2;C-RQ3"
    if s.startswith("raw_results/rq1_rq2") or s.endswith("experiment_seed_reconciliation.csv"):return "selected archived raw output","C-RQ1;C-RQ2;Table 8"
    if s.startswith("raw_results/rq3") or s.endswith("rq3_seed_reconciliation.csv"):return "selected archived raw output","C-RQ3;Table 9"
    if s.startswith("derived_results/"):return "derived result","C-RQ1;C-RQ2;C-RQ3;Figures"
    if s.startswith("expected/"):return "expected result oracle","C-RQ1;C-RQ2;C-RQ3"
    if s.startswith("tool/"):return "rerun tool snapshot","method"
    if s.startswith("environment/"):return "locked environment","all"
    if s.startswith("references/"):return "reference evidence","C-RQ1"
    if s.startswith("experiments/"):return "experiment definition or registry","method"
    if s.startswith("LICENSES/") or s=="CITATION.cff":return "legal/attribution metadata","release"
    return "documentation or entry point","all"
out=[]
for p in sorted(ROOT.rglob("*")):
    rel=p.relative_to(ROOT)
    if (rel.parts and rel.parts[0] in EXCLUDED_TOP_LEVEL):continue
    if (not p.is_file() or p.name=="MANIFEST.csv" or "__pycache__" in p.parts
            or ".venv" in p.parts or ".pytest_cache" in p.parts):continue
    s=str(rel);role,claim=classify(rel);exp=seed="";cfgsha="";inputsha=""
    m=re.search(r"/(exp\d+)(?:/|_)","/"+s)
    if m:exp=m.group(1)
    m=re.search(r"seed(\d+)",s)
    if m:seed=m.group(1)
    if s in config:
        r=config[s];exp=r["experiment_id"];seed=r["seed"];cfgsha=r["sha256"]
        inputsha=input_hashes(r)
    elif s.startswith("raw_results/rq1_rq2/") and exp and seed:
        r=config_key.get(("rq1_rq2",exp,seed),{});cfgsha=r.get("sha256","");inputsha=input_hashes(r)
    elif s.startswith("raw_results/rq3_sensitivity/") and seed:
        parts=rel.parts;req,variant=parts[2],parts[3]
        exp=f"{req}:{variant}"
        r=config_key.get(("rq3_sensitivity",req,variant and seed),{})
        # key's third component is seed; variant is encoded in configuration,
        # so resolve without guessing experiment aliases.
        r=next((x for x in config.values() if x["study_id"]=="rq3_sensitivity" and x["experiment_id"]==req and x["configuration"]==variant and x["seed"]==seed),{})
        cfgsha=r.get("sha256","");inputsha=input_hashes(r)
    elif s.startswith("experiments/") and p.suffix==".json" and ("configuration" in p.name or "/configs/" in "/"+s):
        cfgsha=sha(p)
    if s in prov:inputsha=prov[s]
    if s.startswith("derived_results/"):cmd="./reproduce-analysis";status="generated_verified"
    elif s.startswith("raw_results/rerun/"):cmd="./reproduce-full --execute";status="generation_target"
    elif s.startswith("experiments/") and "/configs/" in s:cmd="python3 ../scripts/build_replication_package.py";status="schema_validated"
    else:cmd="python3 ../scripts/build_replication_package.py" if role.startswith(("selected","immutable","rerun tool")) else "release authored";status="immutable" if role not in ("derived result",) else "generated"
    toolcommit="UNRECORDED" if role=="selected archived raw output" else "05d0750395972662e9be0a1083b09a6dce7e3e65"
    out.append({"artifact_path":s,"artifact_role":role,"associated_claim_table_figure":claim,"experiment":exp,"seed":seed,"input_sha256":inputsha,"configuration_sha256":cfgsha,"tool_commit":toolcommit,"environment_image_digest":IMAGE_DIGEST,"generation_command":cmd,"status":status,"checksum_sha256":sha(p)})
with (ROOT/"MANIFEST.csv").open("w",newline="") as f:
    w=csv.DictWriter(f,FIELDS,lineterminator="\n");w.writeheader();w.writerows(out)
print(f"wrote MANIFEST.csv with {len(out)} artifacts (manifest itself excluded to avoid a circular checksum)")
