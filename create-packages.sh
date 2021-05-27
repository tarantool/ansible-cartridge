#!/bin/bash

# This script (re)creates `packages` directory
# In this directory application `myapp` is created
# Then, this application is packed into RPM and DEB
# Note, that if you are using OS X, you should have `gnu-sed` installed
# and packing will be performed in docker in this case

set -e

#########
# Flags #
#########

packages_dirname="packages"
keep_old_packages=""
skip_cartridge=""
skip_tdg=""
tdg_version="1.7.7-0-g76c31fca"

usage() {
    echo "Usage: ./create-packages.sh [options]"
    echo "Options:"
    echo "  -h, --help                              Show this help message"
    echo "  -d <path>, --dir <path>                 Folder to save packages (default: ${packages_dirname})"
    echo "  -k, --keep                              Don't delete packages folder (will be removed by default)"
    echo "  --skip-cartridge                        Skip Cartridge packages creation (will be created by default)"
    echo "  --skip-tdg                              Skip TDG packages creation (will be created by default)"
    echo "  -t <version>, --tdg-version <version>   Version of TDG to download (default: ${tdg_version})"
}

while [ "$1" != "" ]; do
    case "$1" in
    -h | --help)
        usage
        exit
        ;;
    -d | --dir)
        packages_dirname="$2"
        shift
        shift
        ;;
    -k | --keep)
        keep_old_packages="true"
        shift
        ;;
    --skip-cartridge)
        skip_cartridge="true"
        shift
        ;;
    --skip-tdg)
        skip_tdg="true"
        shift
        ;;
    -t | --tdg-version)
        tdg_version="$2"
        shift
        shift
        ;;
    *)
        echo "Unexpected parameter: ${1}"
        exit 1
        ;;
    esac
done

if [ -z "${skip_cartridge}" ]; then
    pack_flags='--use-docker'
    if [[ $(tarantool -V) == "Tarantool Enterprise"* && -z "${TARANTOOL_SDK_PATH}" ]]; then
        if [[ $(tarantool -V) == *"Target: Darwin"* ]]; then
            echo "Set the path to Linux Tarantool SDK using the TARANTOOL_SDK_PATH environment variable!"
            exit 1
        else
            pack_flags+=' --sdk-local'
        fi
    fi
fi

###############
# Preparation #
###############

lazy_pack() {
    lp_format="${1}"
    lp_app_name="${2}"
    lp_version="${3}"

    lp_suffix="${4}"
    if [ -n "${lp_suffix}" ]; then
        lp_suffix_with_dash="-${lp_suffix}"
    fi

    lp_extension=${lp_format}
    if [ "${lp_extension}" = "tgz" ]; then
        lp_extension="tar.gz"
    fi

    package_name="${lp_app_name}-${lp_version}${lp_suffix_with_dash}.${lp_extension}"
    if [ ! -f "${package_name}" ]; then
        echo " - Package '${package_name}' creation:"

        cartridge pack "${lp_format}" \
            --version "${lp_version}" \
            --suffix "${lp_suffix}" \
            ${pack_flags} \
            "${lp_app_name}"
    else
        echo " - Package '${package_name}' already created"
    fi
}

if [ -d "${packages_dirname}" ] && [ -z "${keep_old_packages}" ]; then
    printf "Removing an existing package directory... "
    rm -rf "${packages_dirname}"
    echo "OK"
fi

mkdir -p "${packages_dirname}" >/dev/null
pushd "${packages_dirname}" >/dev/null

#######################################
# Packages for default test scenarios #
#######################################

if [ -z "${skip_cartridge}" ]; then
    app_name=myapp
    version=1.0.0-0

    echo ""
    echo "Creating packages for default test scenarios:"

    echo " - Application creation:"
    rm -rf ${app_name}
    cartridge create --name ${app_name}

    awk '{gsub(/cartridge.cfg\({/, "&\n    vshard_groups = { hot = { bucket_count = 20000 } },")}1' \
        ${app_name}/init.lua >${app_name}/temp.lua
    mv ${app_name}/temp.lua ${app_name}/init.lua

    awk '{gsub(/-- dependencies/, "dependencies")}1' \
        ${app_name}/app/roles/custom.lua >${app_name}/temp.lua
    mv ${app_name}/temp.lua ${app_name}/app/roles/custom.lua

    lazy_pack tgz "${app_name}" "${version}"
    lazy_pack rpm "${app_name}" "${version}"
    lazy_pack deb "${app_name}" "${version}"

    rm -rf ${app_name}
fi

#################################################
# Packages for 'update_cartridge' test scenario #
#################################################

if [ -z "${skip_cartridge}" ]; then
    app_name=myapp

    echo ""
    echo "Creating packages for 'update_cartridge' test scenario:"

    echo " - Application creation:"
    rm -rf ${app_name}
    cartridge create --name ${app_name}

    version=1 # myapp X version uses Cartridge 2.X.0 version
    for cartridge_version in '2.1.2' '2.2.0' '2.3.0' '2.4.0' '2.5.0'; do
        awk -v cartridge_dep_str="cartridge == ${cartridge_version}-1" \
            '{gsub(/cartridge == [0-9.-]+/, cartridge_dep_str);}1' \
            ${app_name}/${app_name}-scm-1.rockspec >${app_name}/temp.rockspec
        mv ${app_name}/temp.rockspec ${app_name}/${app_name}-scm-1.rockspec

        lazy_pack tgz "${app_name}" "${version}.0.0-0" "with-c-${cartridge_version}"

        ((version++))
    done

    rm -rf ${app_name}
fi

###################################
# Packages for TDG test scenarios #
###################################

if [ -z "${skip_tdg}" ]; then
    echo ""

    if [ -f "tdg.tar.gz" ]; then
        echo "TDG package 'tdg.tar.gz' already downloaded"
    else
        if [ -n "${DOWNLOAD_TNT_TOKEN}" ]; then
            printf "Downloading TDG package from 'download.tarantool.io'... "
            curl -L -s -o "tdg.tar.gz" \
                "https://tarantool:${DOWNLOAD_TNT_TOKEN}@download.tarantool.io/tdg/tdg-${tdg_version}.tar.gz" >/dev/null
            echo 'OK'
        elif (command -v aws &>/dev/null) && [ -n "${AWS_ACCESS_KEY_ID}" ] && [ -n "${AWS_SECRET_ACCESS_KEY}" ]; then
            printf "Downloading TDG package from MCS... "
            aws --endpoint-url https://hb.bizmrg.com s3 cp \
                "s3://packages/tdg/tdg-${tdg_version}.tar.gz" "tdg.tar.gz" >/dev/null
            echo 'OK'
        else
            echo "[WARNING] Impossible to download TDG. It's necessary to run TDG tests. You can:"
            echo " - specify 'DOWNLOAD_TNT_TOKEN' in environment to download from 'download.tarantool.io';"
            echo " - install AWS CLI and specify 'AWS_ACCESS_KEY_ID' and 'AWS_SECRET_ACCESS_KEY' in environment to download from MCS;"
            echo " - put 'tdg.tar.gz' package in '${packages_dirname}' directory manually."
        fi
    fi
fi

##############
# Completion #
##############

echo ""
popd >/dev/null
echo "Packages are placed in '${packages_dirname}' directory"
