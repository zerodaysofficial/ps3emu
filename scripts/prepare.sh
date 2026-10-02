#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
set -euo pipefail
source "$(dirname -- "$0")/env.sh"
python3 "$ZD_PROJECT/scripts/prepare_sdk.py" "$OPENPROSPERO_ROOT"
[[ -f "$OPENPROSPERO_ROOT/third_party/openagc/CMakeLists.txt" ]] || {
  printf 'OpenAGC source is missing. See docs/DEPENDENCIES.md.\n' >&2; exit 1;
}
ZD_ARGS=(-S "$OPENPROSPERO_ROOT" -B "$OPENPROSPERO_ROOT/build" -G Ninja
  -DCMAKE_MAKE_PROGRAM="$ZD_NINJA" -DCMAKE_C_COMPILER="$OPENPROSPERO_CLANG"
  -DCMAKE_CXX_COMPILER="$OPENPROSPERO_CLANGXX" -DCMAKE_CXX_SCAN_FOR_MODULES=OFF
  -DOP_BUILD_GUI=OFF -DOP_BUILD_EXAMPLES=OFF -DOP_BUILD_TESTS=ON
  -DSDL_UNIX_CONSOLE_BUILD=ON)
# The ZIP carries the exact fetched sources, permitting an offline host rebuild.
for dependency in SDL QUICKJS NLOHMANN_JSON PUGIXML LZMA_SDK; do
  ZD_LOWER=${dependency,,}
  ZD_FETCH="$OPENPROSPERO_ROOT/offline/$ZD_LOWER-src"
  if [[ -d "$ZD_FETCH" ]]; then
    ZD_ARGS+=("-DFETCHCONTENT_SOURCE_DIR_$dependency=$ZD_FETCH")
  fi
done
"$ZD_CMAKE" "${ZD_ARGS[@]}" "$@"
"$ZD_CMAKE" --build "$OPENPROSPERO_ROOT/build" --target prospero prospero-link prospero-stub -j "${ZD_JOBS:-4}"
export OPENPROSPERO_STUB="$OPENPROSPERO_ROOT/build/bin/prospero-stub"
"$OPENPROSPERO_ROOT/tools/build-crt.sh"
printf 'OPSDK ready. Next: bash scripts/build_ps5.sh\n'
