#!/usr/bin/env python3
"""Report host suitability without changing it."""
import hashlib, importlib, os, platform, shutil, subprocess, sys
from importlib.metadata import version as package_version
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def version(cmd):
    try:return subprocess.run(cmd,capture_output=True,text=True,timeout=10).stdout.strip() or subprocess.run(cmd,capture_output=True,text=True,timeout=10).stderr.strip()
    except Exception:return "MISSING"
print("platform:",platform.platform());print("cpu:",platform.processor() or platform.machine());print("logical_cpus:",os.cpu_count())
try:
    import resource
    if sys.platform=="darwin": print("ram_bytes:",int(version(["sysctl","-n","hw.memsize"])))
    else: print("ram:",next(x for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemTotal')))
except Exception: print("ram: unknown")
disk=shutil.disk_usage(ROOT);print("disk_free_bytes:",disk.free);print("python:",sys.version.splitlines()[0]);print("java:",version(["java","-version"]).splitlines()[0]);print("graphviz:",version(["dot","-V"]).splitlines()[0])
missing=[]
for mod,distribution in (("z3","z3-solver"),("numpy","numpy"),("scipy","scipy"),("matplotlib","matplotlib"),("rtamt","rtamt"),("jsonschema","jsonschema")):
    try:importlib.import_module(mod);print(f"{mod}:",package_version(distribution))
    except Exception:print(f"{mod}: MISSING");missing.append(mod)
for rel,expected in (("environment/vendor/bounce-0.18.jar","bffff1505335c02256b7ab2ccffbe4aa4d3ac9fe14c17557809b7c9d99d666ca"),):
    p=ROOT/rel;actual=hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else "MISSING";print(f"{rel}: {actual}");missing += [rel] if actual!=expected else []
weka_expected="932ea2f342b58fe45736389e9c426d5b5955e610d1f5f6485117f532068915e9"
weka=os.environ.get("WEKA_JAR","").split(":")[0];
if not weka or not Path(weka).is_file(): print("WEKA_JAR: MISSING");missing.append("WEKA_JAR")
else:
    weka_actual=hashlib.sha256(Path(weka).read_bytes()).hexdigest();print("WEKA_JAR:",weka,weka_actual)
    if weka_actual!=weka_expected:missing.append("WEKA_JAR checksum")
print("preflight:","FAIL missing="+",".join(missing) if missing else "PASS")
raise SystemExit(bool(missing))
