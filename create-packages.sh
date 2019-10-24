#!/bin/bash

set -e

mkdir packages || true
rm packages/* || true

for TARANTOOL_VERSION in enterprise opensource-1.10 opensource-2.2
do
    IMAGE=${TARANTOOL_VERSION}-packages-builder
    CONTAINER=${IMAGE}-container

    echo "Build ${PKG} for ${TARANTOOL_VERSION}"

    docker rm ${CONTAINER} || true

    docker build --build-arg TARANTOOL_DOWNLOAD_TOKEN=${TARANTOOL_DOWNLOAD_TOKEN} \
                 --build-arg BUNDLE_VERSION=${BUNDLE_VERSION} \
                 -t ${IMAGE}\
                 --target ${IMAGE} .
    docker create --name ${CONTAINER} ${IMAGE} usr/bin/true
    docker cp ${CONTAINER}:/opt/myapp/myapp-1.0.0-0.rpm packages/myapp-1.0.0-0.${TARANTOOL_VERSION}.rpm
    docker cp ${CONTAINER}:/opt/myapp/myapp-1.0.0-0.deb packages/myapp-1.0.0-0.${TARANTOOL_VERSION}.deb
    docker rm ${CONTAINER}
done
