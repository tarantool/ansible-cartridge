#!/bin/bash
# Call this script to install unit test dependencies

set -e

pushd ./unit/mock

tarantoolctl rocks install cartridge 2.6.0
tarantoolctl rocks install luacheck

popd
