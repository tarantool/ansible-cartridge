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
if [[ `tarantool -V` == *"Target: Darwin"* ]]; then
    pack_flags+='--use-docker'
fi

mkdir ${packages_dirname}
pushd ${packages_dirname}

cartridge create --name ${appname}

sed -i '/cartridge.cfg({/a \ \ \ \ vshard_groups = {hot = { bucket_count = 20000 }},' myapp/init.lua

cartridge pack rpm --quiet --version ${version} ${pack_flags} ${appname}
cartridge pack deb --quiet --version ${version} ${pack_flags} ${appname}

rm -rf ${appname}

echo "Packages are placed in ${packages_dirname} directory"
popd
