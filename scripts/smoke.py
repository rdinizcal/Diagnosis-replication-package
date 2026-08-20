#!/usr/bin/env python3
"""Quick parser, mutation, checker, cache, and J48 smoke test."""
import json, os, subprocess, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"tool"))
from diagnosis.lang.internal_parser import parse_internal_obj
from diagnosis.mutation.api import MutationConfig, mutate_formula, _walk
from diagnosis.lang.ast import IntConst, RealConst
from diagnosis.cache import VerdictCache
import random
canonical=json.loads((ROOT/"experiments/rq1_effectiveness/configs/exp1/seed0.json").read_text())
assert canonical["ga"]["seed"] == 0 and canonical["input"]["output_dir"].endswith("exp1/seed0")
formula=parse_internal_obj(["ForAll",[["t"],["Implies",[[">=",["t",0]],["<",["speed[t]",120]]]]]])
pos=next(i for i,n in enumerate(_walk(formula)) if isinstance(n,(IntConst,RealConst)) and float(n.value)==120)
cfg=MutationConfig(allowed_positions={pos},allowed_changes={pos:{"numeric":(100.0,140.0)}},enable_relop_flip=False,enable_logical_flip=False,enable_quantifier_flip=False)
mut=mutate_formula(formula,cfg,random.Random(0));assert str(mut)!=str(formula)
import z3
x=z3.Real("x");s=z3.Solver();s.add(x>0,x<1);assert s.check()==z3.sat
with tempfile.TemporaryDirectory() as td:
    c=VerdictCache(Path(td)/"cache.sqlite",enabled=True);c.put("phi","TRUE",0.1);assert c.get("phi")[0]=="TRUE";c.close()
    arff=Path(td)/"tiny.arff";arff.write_text("@relation tiny\n@attribute x numeric\n@attribute VEREDICT {TRUE,FALSE}\n@data\n0,FALSE\n1,TRUE\n2,TRUE\n")
    cp=os.environ.get("WEKA_JAR");assert cp,"WEKA_JAR is required"
    p=subprocess.run(["java","-cp",cp,"weka.classifiers.trees.J48","-t",str(arff),"-x","3"],capture_output=True,text=True,timeout=60)
    assert p.returncode==0 and "J48" in p.stdout+p.stderr,(p.stdout+p.stderr)[-1000:]
print("AT1 smoke PASS: canonical exp1/seed0 config, parser, numeric mutation, Z3, verdict cache, and J48")
