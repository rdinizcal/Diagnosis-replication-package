#!/bin/sh
# Install Graphviz from Debian and Java 17.0.20+8 from the Eclipse Temurin release,
# pinned by checksum. Debian drops superseded versions from its mirrors; if the pinned
# Graphviz is gone, the current bookworm one is used, since it only renders tree PDFs.
set -e
apt-get update
apt-get install -y --no-install-recommends graphviz=2.42.2-7+deb12u1 ca-certificates curl \
    || { echo "WARNING: graphviz 2.42.2-7+deb12u1 unavailable; installing the current bookworm graphviz" >&2
         apt-get install -y --no-install-recommends graphviz ca-certificates curl; }
rm -rf /var/lib/apt/lists/*

case "$(dpkg --print-architecture)" in
    amd64) arch=x64;     sha256=ef491a51a46ef90cc47fbc4abb219fde32483ff91be5ec66ddc896df43524b27 ;;
    arm64) arch=aarch64; sha256=9d14a95e07c44bc48666625162baf40db9da4dcb192bfc3e43047790693061a2 ;;
    *) echo "unsupported architecture $(dpkg --print-architecture)" >&2; exit 1 ;;
esac
curl -fsSL -o /tmp/jre.tar.gz \
    "https://github.com/adoptium/temurin17-binaries/releases/download/jdk-17.0.20%2B8/OpenJDK17U-jre_${arch}_linux_hotspot_17.0.20_8.tar.gz"
echo "$sha256  /tmp/jre.tar.gz" | sha256sum -c -
mkdir -p /opt/java
tar -xzf /tmp/jre.tar.gz -C /opt/java --strip-components=1
rm /tmp/jre.tar.gz
ln -sf /opt/java/bin/java /usr/local/bin/java
java -version
