#!/bin/bash

# This script (re)creates `packages` directory
# In this directory application `myapp` is created
# Then, this application is packed into RPM and DEB
# Note, that if you are using OS X, you should have `gnu-sed` installed
# and packing will be performed in docker in this case

set -xe

packages_dirname="packages"

if [ -d "${packages_dirname}" ]; then
    echo "Remove existent packages directory"
    rm -rf ${packages_dirname}
fi

appname=myapp
version=1.0.0-0

pack_flags=''
if [[ $(tarantool -V) == *"Target: Darwin"* ]]; then
    pack_flags+=' --use-docker'

    if [[ $(tarantool -V) == "Tarantool Enterprise"* && -z "${TARANTOOL_SDK_PATH}" ]]; then
        echo "Set the path to Linux Tarantool SDK using the TARANTOOL_SDK_PATH environment variable!"
        exit 1
    fi
fi

mkdir ${packages_dirname}
pushd ${packages_dirname}

cartridge create --name ${appname}

awk '{gsub(/cartridge.cfg\({/, "&\n    vshard_groups = { hot = { bucket_count = 20000 } },")}1' \
    ${appname}/init.lua >${appname}/temp.lua
mv ${appname}/temp.lua ${appname}/init.lua

cartridge pack tgz --version ${version} ${pack_flags} ${appname}
cartridge pack rpm --version ${version} ${pack_flags} ${appname}
cartridge pack deb --version ${version} ${pack_flags} ${appname}

rm -rf ${appname}

echo "Packages are placed in ${packages_dirname} directory"
popd
