#!/bin/sh

set -ex

# Get directory of script
src_path=$(cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P)/..

USE_SUDO_INSTALL="${USE_SUDO_INSTALL:-yes}"
if [ "${USE_SUDO_INSTALL:-yes}" = "yes" ]; then
    SUDO_INSTALL=sudo
else
    SUDO_INSTALL=""
fi

sudo apt-get update

sudo apt-get install -y build-essential m4 tcsh csh libx11-dev tcl-dev tk-dev

sudo apt-get install -y git

mkdir -p deps
cd deps

git clone $(python3 ${src_path}/_tools.py --tool magic --field git-url) magic
cd magic
git checkout $(python3 ${src_path}/_tools.py --tool magic --field git-commit)

args=
if [ ! -z ${PREFIX} ]; then
    args=--prefix="$PREFIX"
fi

LD_FLAGS=-shared ./configure $args
make -j$(nproc)
$SUDO_INSTALL make install
