FROM python:3.11-bullseye

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

ARG FLEX_SDK_VERSION=4.16.1
ARG PYTHON2_VERSION=2.7.18

ENV DEBIAN_FRONTEND=noninteractive \
    FLEX_HOME=/opt/apache-flex-sdk \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PYTHON2_PREFIX=/opt/python2.7

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        ca-certificates \
        curl \
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

ENV PATH="${FLEX_HOME}/bin:${PYTHON2_PREFIX}/bin:${PATH}"

RUN python --version \
    && python2.7 --version \
    && mxmlc -version \
    && compc -version

WORKDIR /workspace