#!/usr/bin/env python3
"""Download the bulk evidence archived on Zenodo, check it, and unpack it in place.

Only needed to inspect per-generation run data, rebuild the operator-coverage matrix
from it, or compare tool/ with its source base. Analysis and smoke tests do not need it.

    python3 scripts/fetch_archive.py              # from the Zenodo record
    python3 scripts/fetch_archive.py --from DIR   # from already downloaded files
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tarfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECORD = json.loads((ROOT / "raw_results" / "ARCHIVE.json").read_text())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--from", dest="source", type=Path, help="directory holding the archive files")
    args = parser.parse_args()
    downloads = ROOT / "raw_results" / "archive_downloads"
    downloads.mkdir(exist_ok=True)
    for entry in RECORD["files"]:
        target = downloads / entry["name"]
        if args.source:
            shutil.copyfile(args.source / entry["name"], target)
        elif not target.exists():
            if not RECORD["zenodo_record"]:
                raise SystemExit("raw_results/ARCHIVE.json names no Zenodo record; use --from DIR")
            url = f"https://zenodo.org/records/{RECORD['zenodo_record']}/files/{entry['name']}?download=1"
            print(f"downloading {url}")
            urllib.request.urlretrieve(url, target)
        if sha256(target) != entry["sha256"]:
            raise SystemExit(f"checksum mismatch: {entry['name']}")
        destination = ROOT / entry["extract_to"]
        destination.mkdir(parents=True, exist_ok=True)
        with tarfile.open(target) as archive:
            archive.extractall(destination, filter="data")
        print(f"{entry['name']}: checksum OK, unpacked into {destination.relative_to(ROOT) or '.'}")


if __name__ == "__main__":
    main()
