#!/bin/bash

set -e

mkdir packages || true
rm packages/* || true

tarantool_version=${TARANTOOL_VERSION:-opensource-1.10}
dockerfile_suffix=opensource

if [[ $tarantool_version == "enterprise" ]] ;
then
    dockerfile_suffix=enterprise
fi

if [[ $tarantool_version == "opensource-2.2" ]] ;
then
    tarantool_repo=tarantool/2_2
elif [[ $tarantool_version == "opensource-1.10" ]] ;
then
    tarantool_repo=tarantool/1_10
fi

IMAGE=${tarantool_version}-packages-builder
CONTAINER=${IMAGE}-container

echo "Build packages for ${tarantool_version}"

docker rm ${CONTAINER} || true

docker build --build-arg TARANTOOL_DOWNLOAD_TOKEN=${TARANTOOL_DOWNLOAD_TOKEN} \
             --build-arg BUNDLE_VERSION=${BUNDLE_VERSION} \
             --build-arg TARANTOOL_REPO=${tarantool_repo} \
             -t ${IMAGE} \
             -f Dockerfile.${dockerfile_suffix} \
             -t ${IMAGE} .

docker create --name ${CONTAINER} ${IMAGE} usr/bin/true
docker cp ${CONTAINER}:/opt/myapp/myapp-1.0.0-0.rpm .
docker cp ${CONTAINER}:/opt/myapp/myapp-1.0.0-0.deb .
docker rm ${CONTAINER}
