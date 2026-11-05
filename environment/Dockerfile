FROM python:3.13.5-slim-bookworm@sha256:4c2cf9917bd1cbacc5e9b07320025bdb7cdf2df7b0ceaccb55e9dd7e30987419
ARG WEKA_URL=https://repo1.maven.org/maven2/nz/ac/waikato/cms/weka/weka-stable/3.8.6/weka-stable-3.8.6.jar
ARG WEKA_SHA256=932ea2f342b58fe45736389e9c426d5b5955e610d1f5f6485117f532068915e9
COPY environment/install_debian_packages.sh /tmp/install_debian_packages.sh
RUN sh /tmp/install_debian_packages.sh
WORKDIR /opt/replication
COPY environment/requirements-lock.txt /tmp/requirements-lock.txt
COPY environment/rtamt-compat-lock.txt /tmp/rtamt-compat-lock.txt
COPY environment/patch_antlr47_py313.py /tmp/patch_antlr47_py313.py
RUN python -m pip install --no-cache-dir -r /tmp/requirements-lock.txt && python /tmp/patch_antlr47_py313.py && python -m pip install --no-cache-dir --no-deps -r /tmp/rtamt-compat-lock.txt
COPY environment/vendor/bounce-0.18.jar /opt/weka/bounce.jar
RUN curl -fsSL "$WEKA_URL" -o /opt/weka/weka.jar && echo "$WEKA_SHA256  /opt/weka/weka.jar" | sha256sum -c -
ENV WEKA_JAR=/opt/weka/weka.jar:/opt/weka/bounce.jar
COPY . /opt/replication
RUN python -m pip install --no-deps -e tool && python scripts/validate_configs.py
CMD ["./run", "smoke"]
