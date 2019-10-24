#!/bin/bash

set -e

mkdir packages || true
rm packages/* || true

for PKG in rpm deb
do
    for TARANTOOL_VERSION in enterprise opensource-1.10 opensource-2.2
    do
        IMAGE=${TARANTOOL_VERSION}-${PKG}-builder
        CONTAINER=${IMAGE}-container

        echo "Build ${PKG} for ${TARANTOOL_VERSION}"

        docker rm ${CONTAINER} || true

        docker build --build-arg TARANTOOL_DOWNLOAD_TOKEN=${TARANTOOL_DOWNLOAD_TOKEN} \
                     --build-arg BUNDLE_VERSION=${BUNDLE_VERSION} \
                     -t ${IMAGE}\
                     --target ${IMAGE} .
        docker create --name ${CONTAINER} ${IMAGE} usr/bin/true
        docker cp ${CONTAINER}:/opt/myapp/myapp-1.0.0-0.${PKG} packages/myapp-1.0.0-0.${PKG}.${TARANTOOL_VERSION}
        docker rm ${CONTAINER}
    done
done
