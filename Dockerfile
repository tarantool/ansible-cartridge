FROM docker:git

RUN set -x \
    && apk update && apk add --no-cache \
        docker python3-dev py3-pip docker \
        gcc git curl build-base autoconf automake py3-cryptography linux-headers \
        musl-dev libffi-dev openssl-dev openssh bash \
    && pip3 install --upgrade ansible molecule==3.0.2 docker flake8 testinfra
