FROM node:22-slim

RUN set -x \
    && apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y \
        git \
        vim \
        less \
        curl \
        jq \
        python3-pip \
        python3-venv \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && npm install -g npm

ENV LESSCHARSET=utf-8
USER node
WORKDIR /usr/src/app
