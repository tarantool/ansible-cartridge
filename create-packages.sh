#!/bin/bash

set -e

mkdir packages || true
rm packages/* || true

tarantool_version=${TARANTOOL_VERSION:-opensource-1.10}

IMAGE=${tarantool_version}-packages-builder
CONTAINER=${IMAGE}-container

echo "Build packages for ${tarantool_version}"

docker rm ${CONTAINER} || true

docker build --build-arg TARANTOOL_DOWNLOAD_TOKEN=${TARANTOOL_DOWNLOAD_TOKEN} \
                --build-arg BUNDLE_VERSION=${BUNDLE_VERSION} \
                -t ${IMAGE}\
                --target ${IMAGE} .
docker create --name ${CONTAINER} ${IMAGE} usr/bin/true
docker cp ${CONTAINER}:/opt/myapp/myapp-1.0.0-0.rpm .
docker cp ${CONTAINER}:/opt/myapp/myapp-1.0.0-0.deb .
docker rm ${CONTAINER}
