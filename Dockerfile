FROM docker:git

RUN set -x \
    && apk update && apk add --no-cache \
        docker python3-dev py3-pip docker \
        gcc git curl build-base autoconf automake py3-cryptography linux-headers \
        musl-dev libffi-dev openssl-dev openssh bash

RUN apk add py3-virtualenv

COPY requirements.txt /tmp/
RUN virtualenv activate && pip3 install --upgrade -r /tmp/requirements.txt
