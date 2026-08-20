#!/usr/bin/env python3
"""Run authorized experiment configurations; defaults to a dry-run inventory."""
import argparse, csv, os, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument("--study",choices=("rq1_rq2","rq3_sensitivity","all"),default="all");p.add_argument("--execute",action="store_true");p.add_argument("--ids",default="all");p.add_argument("--seeds",default="all");p.add_argument("--profile",choices=("at1","multi-token","discrete-operator"));a=p.parse_args()
profiles={"at1":("exp1","0"),"multi-token":("exp2","0"),"discrete-operator":("exp30","0")}
if a.profile:
    a.study="rq1_rq2";a.ids,a.seeds=profiles[a.profile]
with (ROOT/"experiments/configuration_hashes.csv").open(newline="") as f: rs=list(csv.DictReader(f))
if a.study!="all":rs=[r for r in rs if r["study_id"]==a.study]
if a.ids!="all":
    ids=set(a.ids.split(","));rs=[r for r in rs if r["experiment_id"] in ids]
if a.seeds!="all":
    seeds=set(a.seeds.split(","));rs=[r for r in rs if r["seed"] in seeds]
print(f"authorized configurations: {len(rs)}")
if a.profile: print(f"reproduction profile: {a.profile} ({a.ids}, seed {a.seeds})")
if not a.execute:
    for r in rs[:20]:print(r["path"])
    if len(rs)>20:print(f"... {len(rs)-20} more")
    print("dry run only; pass --execute after sizing the five-day-per-run budget")
    raise SystemExit(0)
env=os.environ.copy();env["PYTHONPATH"]=str(ROOT/"tool")+(os.pathsep+env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
for i,r in enumerate(rs,1):
    print(f"[{i}/{len(rs)}] {r['experiment_id']} seed {r['seed']}",flush=True)
    subprocess.run([sys.executable,"-m","diagnosis.cli","run","--config",str(ROOT/r["path"])],cwd=ROOT,env=env,check=True)
