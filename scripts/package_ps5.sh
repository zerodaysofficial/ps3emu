#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
set -euo pipefail
source "$(dirname -- "$0")/env.sh"
ZD_STRUCTURAL=0
case "${1:-}" in
  --structural-only) ZD_STRUCTURAL=1; shift ;;
  "") ;;
  *) printf 'usage: package_ps5.sh [--structural-only]\n' >&2; exit 2 ;;
esac
[[ $# == 0 ]] || { printf 'Unexpected arguments.\n' >&2; exit 2; }
ZD_EBOOT="$ZD_PROJECT/build/ps5/eboot.bin"
[[ -f "$ZD_EBOOT" ]] || { printf 'Build the application first.\n' >&2; exit 1; }
if [[ ! -f "$ZD_PROJECT/assets/font.zdf" ]]; then
  python3 "$ZD_PROJECT/scripts/generate_font.py" "$ZD_PROJECT/assets/font.zdf"
fi
ZD_APP="$ZD_PROJECT/build/ps5/app"
mkdir -p "$ZD_APP/assets" "$ZD_APP/sce_sys" "$ZD_APP/sce_module"
cp "$ZD_EBOOT" "$ZD_APP/eboot.bin"
cp "$ZD_PROJECT/assets/font.zdf" "$ZD_APP/assets/font.zdf"
find "$ZD_APP/sce_module" -maxdepth 1 -type f -delete
if [[ $ZD_STRUCTURAL == 0 ]]; then
  ZD_MODULES="${ZD_RUNTIME_MODULES:-$ZD_PROJECT/build/ps5/runtime}"
  if [[ ! -f "$ZD_MODULES/libc.prx" ]]; then
    python3 "$ZD_PROJECT/scripts/build_libc_prx.py" --output "$ZD_MODULES/libc.prx"
  fi
  cp "$ZD_MODULES/libc.prx" "$ZD_APP/sce_module/libc.prx"
fi
ZD_OUTPUT="$ZD_PROJECT/build/ps5/package-$(date -u +%Y%m%dT%H%M%S)-$$"
"$OPENPROSPERO_ROOT/build/bin/prospero" inspect "$ZD_EBOOT"
"$OPENPROSPERO_ROOT/build/bin/prospero" package "$ZD_APP" "$ZD_OUTPUT" \
  --content-id UP9000-PPSA99050_00-ZER0RPCS3PS50000 \
  --title 'ZER0DAY PS3 Library - core integration' --version 00.07 \
  --no-companion --experimental
PKG=$(find "$ZD_OUTPUT" -maxdepth 1 -type f -name '*.pkg' -print -quit)
[[ -n "$PKG" ]] && "$OPENPROSPERO_ROOT/build/bin/prospero" validate "$PKG"
if [[ $ZD_STRUCTURAL == 1 ]]; then
  printf 'STRUCTURAL ONLY: sce_module runtime omitted.\n' > "$ZD_OUTPUT/STRUCTURAL-ONLY.txt"
fi
printf 'Package output: %s\n' "$ZD_OUTPUT"
