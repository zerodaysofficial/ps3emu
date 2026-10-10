#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
set -euo pipefail
ZD_PROJECT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
if [[ -d "$ZD_PROJECT/deps/openprospero" ]]; then
  ZD_DEPS="$ZD_PROJECT/deps"
  : "${OPENPROSPERO_ROOT:=$ZD_DEPS/openprospero}"
  : "${PS5_OPENGL_ROOT:=$ZD_DEPS/ps5-opengl}"
  : "${PS5_OPENGL_SDK:=$ZD_DEPS/ps5-opengl-sdk/sdk}"
else
  ZD_DEPS="$ZD_PROJECT/../vendor"
  : "${OPENPROSPERO_ROOT:=$ZD_DEPS/sdk}"
  : "${PS5_OPENGL_ROOT:=$ZD_DEPS/ps5-opengl-1.0.0}"
  : "${PS5_OPENGL_SDK:=$ZD_DEPS/ps5-opengl-sdk-1.0.0/sdk}"
fi
: "${OPENPROSPERO_SDK:=$OPENPROSPERO_ROOT/sdk}"
: "${OPENPROSPERO_CLANG:=clang-19}"
: "${OPENPROSPERO_CLANGXX:=clang++-19}"
: "${OPENPROSPERO_LLD:=ld.lld-19}"
: "${OPENPROSPERO_AR:=ar}"
: "${ZD_CMAKE:=cmake}"
: "${ZD_NINJA:=ninja}"
export OPENPROSPERO_ROOT OPENPROSPERO_SDK OPENPROSPERO_CLANG OPENPROSPERO_CLANGXX
export OPENPROSPERO_LLD OPENPROSPERO_AR
 
 
if [[ -d "$OPENPROSPERO_ROOT/build/lib" ]]; then
  export LD_LIBRARY_PATH="$OPENPROSPERO_ROOT/build/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
fi
