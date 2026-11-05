#!/bin/sh
# Install Java and Graphviz at the tested versions from the Debian snapshot of the
# tested image. If the snapshot cannot be reached, install the current bookworm
# packages instead: Weka is pinned by checksum, and Graphviz only renders tree PDFs.
set -e
SNAPSHOT=20260821T000000Z
PINNED="openjdk-17-jre-headless=17.0.20+8-1~deb12u1 graphviz=2.42.2-7+deb12u1"
cp /etc/apt/sources.list.d/debian.sources /tmp/debian.sources
rm /etc/apt/sources.list.d/debian.sources
cat > /etc/apt/sources.list <<LIST
deb [check-valid-until=no] http://snapshot.debian.org/archive/debian/$SNAPSHOT bookworm main
deb [check-valid-until=no] http://snapshot.debian.org/archive/debian/$SNAPSHOT bookworm-updates main
deb [check-valid-until=no] http://snapshot.debian.org/archive/debian-security/$SNAPSHOT bookworm-security main
LIST
if apt-get -o Acquire::Retries=5 update && apt-get -o Acquire::Retries=5 install -y --no-install-recommends $PINNED ca-certificates curl; then
    echo "installed the tested versions from snapshot $SNAPSHOT"
else
    echo "WARNING: Debian snapshot unreachable; installing current bookworm Java and Graphviz" >&2
    rm /etc/apt/sources.list
    mv /tmp/debian.sources /etc/apt/sources.list.d/debian.sources
    apt-get update
    apt-get install -y --no-install-recommends openjdk-17-jre-headless graphviz ca-certificates curl
fi
rm -rf /var/lib/apt/lists/* /tmp/debian.sources
