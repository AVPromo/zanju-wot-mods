FROM python:3.11-bullseye

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

ARG FLEX_SDK_VERSION=4.16.1
ARG PLAYERGLOBAL_FILENAME=playerglobal32_0.swc
ARG PLAYERGLOBAL_MAJOR=32
ARG PLAYERGLOBAL_VERSION=32.0
ARG PYTHON2_VERSION=2.7.18

ENV DEBIAN_FRONTEND=noninteractive \
    FLEX_HOME=/opt/apache-flex-sdk \
    JAVA_TOOL_OPTIONS=-Djava.awt.headless=true \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PLAYERGLOBAL_HOME=/opt/apache-flex-sdk/frameworks/libs/player \
    PYTHON2_PREFIX=/opt/python2.7

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        ca-certificates \
        curl \
        git \
        libbz2-dev \
        libffi-dev \
        libgdbm-dev \
        liblzma-dev \
        libncurses5-dev \
        libreadline-dev \
        libsqlite3-dev \
        libssl-dev \
        openjdk-11-jre-headless \
        tar \
        tk-dev \
        xz-utils \
        zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL "https://www.python.org/ftp/python/${PYTHON2_VERSION}/Python-${PYTHON2_VERSION}.tgz" -o /tmp/python2.tgz \
    && mkdir -p /tmp/python2-src \
    && tar -xzf /tmp/python2.tgz -C /tmp/python2-src --strip-components=1 \
    && cd /tmp/python2-src \
    && ./configure --prefix="${PYTHON2_PREFIX}" \
    && make -j"$(nproc)" \
    && make install \
    && rm -rf /tmp/python2.tgz /tmp/python2-src

RUN curl -fsSL "https://archive.apache.org/dist/flex/${FLEX_SDK_VERSION}/binaries/apache-flex-sdk-${FLEX_SDK_VERSION}-bin.tar.gz" -o /tmp/flex-sdk.tar.gz \
    && mkdir -p /opt \
    && tar -xzf /tmp/flex-sdk.tar.gz -C /opt \
    && mv "/opt/apache-flex-sdk-${FLEX_SDK_VERSION}-bin" "${FLEX_HOME}" \
    && rm -f /tmp/flex-sdk.tar.gz

RUN mkdir -p "${FLEX_HOME}/frameworks/libs/player/${PLAYERGLOBAL_VERSION}" \
    && curl -fsSL "https://fpdownload.macromedia.com/get/flashplayer/updaters/${PLAYERGLOBAL_MAJOR}/${PLAYERGLOBAL_FILENAME}" \
        -o "${FLEX_HOME}/frameworks/libs/player/${PLAYERGLOBAL_VERSION}/playerglobal.swc"

RUN FLEX_SF="https://sourceforge.net/adobe/flexsdk/code/HEAD/tree/trunk/lib" \
    && mkdir -p "${FLEX_HOME}/lib/external/optional" \
    && curl -fsSL "${FLEX_SF}/afe.jar?format=raw"          -o "${FLEX_HOME}/lib/external/optional/afe.jar" \
    && curl -fsSL "${FLEX_SF}/aglj40.jar?format=raw"       -o "${FLEX_HOME}/lib/external/optional/aglj40.jar" \
    && curl -fsSL "${FLEX_SF}/flex-fontkit.jar?format=raw" -o "${FLEX_HOME}/lib/external/optional/flex-fontkit.jar" \
    && curl -fsSL "${FLEX_SF}/rideau.jar?format=raw"       -o "${FLEX_HOME}/lib/external/optional/rideau.jar" \
    && echo "d1469e163c4fd4c1ef8be82dd6d0f1ee  ${FLEX_HOME}/lib/external/optional/afe.jar" | md5sum -c \
    && echo "b9b6b825787489796d9b6bf607a64824  ${FLEX_HOME}/lib/external/optional/aglj40.jar" | md5sum -c \
    && echo "2abb9f580fa40ad6ef80864f94b6e938  ${FLEX_HOME}/lib/external/optional/flex-fontkit.jar" | md5sum -c \
    && echo "3b3329c1b3de665dc116121b772c5369  ${FLEX_HOME}/lib/external/optional/rideau.jar" | md5sum -c

RUN printf 'env.PLAYERGLOBAL_HOME=%s\n' "${PLAYERGLOBAL_HOME}" > "${FLEX_HOME}/env.properties"

ENV PATH="${FLEX_HOME}/bin:${PATH}:${PYTHON2_PREFIX}/bin"

# Login shells (e.g. the VS Code dev-container terminal) re-run /etc/profile and
# drop the ENV PATH above, which would hide mxmlc/python2.7 from compile_ui's
# shutil.which(). Re-add the toolchain dirs for login shells too.
RUN printf 'export PATH="%s/bin:%s/bin:$PATH"\n' "${FLEX_HOME}" "${PYTHON2_PREFIX}" \
        > /etc/profile.d/10-wot-toolchain.sh

# `zwm` — the single dev entrypoint (zwm build | lint | cycle | deploy | cleanup | help).
# Repo is mounted at /workspace in every flow (WORKDIR, CI, dev container).
RUN printf '#!/bin/sh\nexport PYTHONPATH="/workspace${PYTHONPATH:+:$PYTHONPATH}"\nexec python3 -m tools.cli "$@"\n' \
        > /usr/local/bin/zwm \
    && chmod +x /usr/local/bin/zwm

# Lint/format toolchains baked in so one image serves build + lint (CI and local parity).
# Python 3: ruff/black/autopep8. Python 2.7: flake8 3.9.x (needs pip<21 / setuptools<45).
COPY requirements-dev.txt requirements-lint-py27.txt /tmp/
RUN pip install --no-cache-dir -r /tmp/requirements-dev.txt \
    && "${PYTHON2_PREFIX}/bin/python2.7" -m ensurepip \
    && "${PYTHON2_PREFIX}/bin/python2.7" -m pip install --no-cache-dir "pip<21" "setuptools<45" \
    && "${PYTHON2_PREFIX}/bin/python2.7" -m pip install --no-cache-dir -r /tmp/requirements-lint-py27.txt \
    && rm -f /tmp/requirements-dev.txt /tmp/requirements-lint-py27.txt

RUN python --version \
    && python2.7 --version \
    && test -f "${FLEX_HOME}/frameworks/libs/player/${PLAYERGLOBAL_VERSION}/playerglobal.swc" \
    && mxmlc -version \
    && compc -version \
    && ruff --version \
    && python2.7 -m flake8 --version

WORKDIR /workspace
