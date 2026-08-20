#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "usage: $0 TARGET_DIRECTORY" >&2
  exit 2
fi

target=$1
git clone https://github.com/SNTSVV/TD-SB-TemPsy.git "$target"
git -C "$target" checkout --detach 410753400e58e2a386a3e65f48374211214b4dc0
git -C "$target" fetch origin pull/2/head
git -C "$target" checkout --detach 8efd304987a8f7355606fa3951576d00f316df51
test "$(git -C "$target" rev-parse HEAD)" = "8efd304987a8f7355606fa3951576d00f316df51"
echo "checked out pinned Apache-2.0 upstream plus reproducibility/OCL-import fix"
