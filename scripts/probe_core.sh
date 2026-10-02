#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Compile real upstream translation units to record concrete PS5 port blockers.
# This is a qualification probe, not an emulator build or a generated backend.
set -euo pipefail
source "$(dirname -- "$0")/env.sh"
: "${RPCS3_ROOT:=$ZD_PROJECT/deps/rpcs3-official}"
if [[ ! -d "$RPCS3_ROOT" && -d "$ZD_PROJECT/../vendor/rpcs3-official" ]]; then
  RPCS3_ROOT="$ZD_PROJECT/../vendor/rpcs3-official"
fi
ZD_RESOURCE=$("$OPENPROSPERO_CLANGXX" -print-resource-dir)
ZD_OUT="$ZD_PROJECT/build/core-probe"
mkdir -p "$ZD_OUT" "$ZD_PROJECT/logs"
ZD_FLAGS=(--target=x86_64-sie-ps5 -std=c++23 -O0 -ffreestanding -fPIC
  -fstack-protector-strong -femulated-tls -fexceptions -nostdinc
  -isystem "$OPENPROSPERO_SDK/target/cxx/include/c++/v1"
  -isystem "$ZD_RESOURCE/include" -isystem "$OPENPROSPERO_SDK/target/cxx/include"
  -isystem "$OPENPROSPERO_SDK/target/include" -I "$RPCS3_ROOT"
  -I "$RPCS3_ROOT/rpcs3" -I "$RPCS3_ROOT/3rdparty"
  -I "$RPCS3_ROOT/3rdparty/zlib/zlib"
  -isystem "$PS5_OPENGL_SDK/include" -I "$RPCS3_ROOT/3rdparty/asmjit/asmjit/src"
  -I "$RPCS3_ROOT/3rdparty/yaml-cpp/yaml-cpp/include" -ferror-limit=5)
ZD_FAILED=0
ZD_UNITS=(rpcs3/util/vm_native.cpp Utilities/JITASM.cpp
  rpcs3/Emu/Cell/PPUInterpreter.cpp rpcs3/Emu/Cell/SPUInterpreter.cpp
  Utilities/Thread.cpp Utilities/File.cpp Utilities/sema.cpp
  rpcs3/Emu/Audio/AudioBackend.cpp rpcs3/Emu/RSX/GL/GLGSRender.cpp)
for unit in "${ZD_UNITS[@]}"; do
  ZD_NAME=$(basename "$unit" .cpp)
  if "$OPENPROSPERO_CLANGXX" "${ZD_FLAGS[@]}" -c "$RPCS3_ROOT/$unit" \
      -o "$ZD_OUT/$ZD_NAME.o" > "$ZD_PROJECT/logs/core-$ZD_NAME.log" 2>&1; then
    printf '%s: COMPILED (unit only, not a linked core)\n' "$unit"
  else
    printf '%s: BLOCKED; details in logs/core-%s.log\n' "$unit" "$ZD_NAME"
    ZD_FAILED=$((ZD_FAILED + 1))
  fi
done
printf 'Blocked translation units: %s/%s. No emulation executable was built.\n' "$ZD_FAILED" "${#ZD_UNITS[@]}"
[[ $ZD_FAILED == 0 ]]
