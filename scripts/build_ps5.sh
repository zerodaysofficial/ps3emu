#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
set -euo pipefail
source "$(dirname -- "$0")/env.sh"
ZD_OUT="$ZD_PROJECT/build/ps5"
mkdir -p "$ZD_OUT" "$ZD_PROJECT/logs"
for f in "$OPENPROSPERO_ROOT/build/bin/prospero-link" \
         "$OPENPROSPERO_SDK/target/lib/app_crt1.o" \
         "$PS5_OPENGL_SDK/lib/libPS5OpenGL.a"; do
  [[ -f "$f" ]] || { printf 'Missing dependency: %s\nRun scripts/prepare.sh first.\n' "$f" >&2; exit 1; }
done
# These are public, generated link stubs, never firmware runtime modules.
cp "$PS5_OPENGL_SDK/lib/libSceAgc.so" "$OPENPROSPERO_SDK/target/lib/"
cp "$PS5_OPENGL_SDK/lib/libSceAgcDriver.so" "$OPENPROSPERO_SDK/target/lib/"
bash "$ZD_PROJECT/scripts/build_core.sh"
"$ZD_CMAKE" --build "$ZD_PROJECT/build/core-ps5" --target zd_application --parallel "${ZD_JOBS:-4}"
cp "$ZD_PROJECT/build/core-ps5/application.elf" "$ZD_OUT/application.elf"
cp "$ZD_OUT/application.elf" "$ZD_OUT/eboot.bin"
python3 "$ZD_PROJECT/scripts/verify_ps5.py" "$ZD_OUT/application.elf"
python3 "$ZD_PROJECT/scripts/verify_core.py" "$ZD_PROJECT/build/core-ps5" "$ZD_OUT/application.elf"
"$OPENPROSPERO_ROOT/build/bin/prospero" inspect "$ZD_OUT/eboot.bin"
printf 'Original RPCS3 C++ core linked into PS5 application: %s\nGame output/input use Null providers; console execution remains unverified.\n' "$ZD_OUT/eboot.bin"
