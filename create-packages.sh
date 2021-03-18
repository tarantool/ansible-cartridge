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

pack_flags='--use-docker'

if [[ $(tarantool -V) == "Tarantool Enterprise"* && -z "${TARANTOOL_SDK_PATH}" ]]; then
    if [[ $(tarantool -V) == *"Target: Darwin"* ]]; then
        echo "Set the path to Linux Tarantool SDK using the TARANTOOL_SDK_PATH environment variable!"
        exit 1
    else
        pack_flags+=' --sdk-local'
    fi
fi

mkdir ${packages_dirname}
pushd ${packages_dirname}

# default test scenario
appname=myapp
version=1.0.0-0

echo "Create packages for default test scenario"

cartridge create --name ${appname}

awk '{gsub(/cartridge.cfg\({/, "&\n    vshard_groups = { hot = { bucket_count = 20000 } },")}1' \
    ${appname}/init.lua >${appname}/temp.lua
mv ${appname}/temp.lua ${appname}/init.lua

cartridge pack tgz --version ${version} ${pack_flags} ${appname}
cartridge pack rpm --version ${version} ${pack_flags} ${appname}
cartridge pack deb --version ${version} ${pack_flags} ${appname}

rm -rf ${appname}

# update_cartridge test scenario
appname=myapp

echo "Create packages for update_cartridge test scenario"

cartridge create --name ${appname}

version=1  # myapp X version uses Cartridge 2.X.0 version
for cartridge_version in '2.1.2' '2.2.0' '2.3.0' '2.4.0' '2.5.0'
do
    awk -v cartridge_dep_str="cartridge == ${cartridge_version}-1" \
        '{gsub(/cartridge == [0-9.-]+/, cartridge_dep_str);}1' \
        ${appname}/${appname}-scm-1.rockspec >${appname}/temp.rockspec
    mv ${appname}/temp.rockspec ${appname}/${appname}-scm-1.rockspec

    cartridge pack tgz \
        --version ${version} \
        --suffix with-c-${cartridge_version} \
        ${pack_flags} \
        ${appname}

    ((version++))
done

rm -rf ${appname}

echo "Packages are placed in ${packages_dirname} directory"
popd
