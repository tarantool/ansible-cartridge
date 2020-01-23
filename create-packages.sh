#!/bin/bash

set -e

packages_dirname="packages"

if [ -d "${packages_dirname}" ]; then
    echo "Directory packages already exists"
    exit 0
fi

tarantool_version=${TARANTOOL_VERSION:-opensource-1.10}
dockerfile_suffix=opensource
cartridge_cli_version=${CARTRIDGE_CLI_VERSION:-1.2.1}

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
             --build-arg CARTRIDGE_CLI_VERSION=${cartridge_cli_version} \
             -t ${IMAGE} \
             -f Dockerfile.${dockerfile_suffix} \
             -t ${IMAGE} .

docker create --name ${CONTAINER} ${IMAGE} usr/bin/true

mkdir "${packages_dirname}"

docker cp ${CONTAINER}:/opt/myapp/myapp-1.0.0-0.rpm ${packages_dirname}
docker cp ${CONTAINER}:/opt/myapp/myapp-1.0.0-0.deb ${packages_dirname}
docker rm ${CONTAINER}

echo "Packages are placed in packages directory"
