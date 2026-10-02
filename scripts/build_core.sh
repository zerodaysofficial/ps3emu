#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
set -euo pipefail
source "$(dirname -- "$0")/env.sh"
: "${RPCS3_ROOT:=$ZD_PROJECT/deps/rpcs3-official}"
: "${ZD_EXTRA_DEPS:=$ZD_PROJECT/deps/core-extra}"
export PS5_OPENGL_SDK PS5_OPENGL_ROOT ZD_EXTRA_DEPS
mkdir -p "$ZD_PROJECT/build/core-ps5" "$ZD_PROJECT/logs"
python3 "$ZD_PROJECT/scripts/apply_core_patches.py" "$RPCS3_ROOT"
bash "$ZD_PROJECT/scripts/build_ffmpeg.sh"
"$ZD_CMAKE" -S "$ZD_PROJECT/core" -B "$ZD_PROJECT/build/core-ps5" -G Ninja \
  -DCMAKE_TOOLCHAIN_FILE="$ZD_PROJECT/cmake/ps5-toolchain.cmake" \
  -DCMAKE_MAKE_PROGRAM="$ZD_NINJA" -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_C_FLAGS_RELEASE='-O1 -DNDEBUG' -DCMAKE_CXX_FLAGS_RELEASE='-O1 -DNDEBUG' \
  -DRPCS3_ROOT="$RPCS3_ROOT" -DZD_EXTRA_DEPS="$ZD_EXTRA_DEPS" \
  -DZD_FFMPEG_PREFIX="$ZD_PROJECT/build/core-deps"
"$ZD_CMAKE" --build "$ZD_PROJECT/build/core-ps5" --target rpcs3_emu --parallel "${ZD_JOBS:-4}"
printf 'RPCS3 emulation archive compiled for PS5. Final application link still required.\n'
