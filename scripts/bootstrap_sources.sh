#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
 
set -euo pipefail
ROOT=$(cd -- "$(dirname -- "$0")/.." && pwd)
DEPS="$ROOT/deps"
CACHE="$DEPS/.downloads"
mkdir -p "$DEPS" "$CACHE" "$DEPS/core-extra"
need() { command -v "$1" >/dev/null || { echo "Missing host tool: $1" >&2; exit 2; }; }
for tool in git curl tar sha256sum python3; do need "$tool"; done
clone_at() {
  local url=$1 dest=$2 ref=$3
  if [[ ! -d "$dest/.git" ]]; then git clone --filter=blob:none "$url" "$dest"; fi
  git -C "$dest" fetch --tags origin || true
  git -C "$dest" checkout --detach "$ref"
}
fetch() {
  local url=$1 out=$2 sha=$3
  if [[ ! -f "$out" ]]; then curl -L --fail --retry 3 -o "$out" "$url"; fi
  printf '%s  %s\n' "$sha" "$out" | sha256sum -c -
}
unpack() {
  local archive=$1 dest=$2
  rm -rf "$dest"; mkdir -p "$dest"
  tar -xf "$archive" -C "$dest" --strip-components=1
}
clone_at https://github.com/RPCS3/rpcs3.git "$DEPS/rpcs3-official" 17320679e329908af40b76a8a48c43025d4acc9a
git -C "$DEPS/rpcs3-official" submodule update --init --recursive
clone_at https://github.com/SvenGDK/SharpProspero.git "$DEPS/SharpProspero" 5dfdb4b0b166e83dc9ae275001afb695f12c7174
clone_at https://github.com/blackbearreloaded/ps5-opengl.git "$DEPS/ps5-opengl" dce74910af7f4274c48d05e0ae001b3038462588
OPENPROSPERO_REPO=${OPENPROSPERO_REPO:-https://github.com/OpenProspero/sdk.git}
OPENPROSPERO_REF=${OPENPROSPERO_REF:-main}
clone_at "$OPENPROSPERO_REPO" "$DEPS/openprospero" "$OPENPROSPERO_REF"
git -C "$DEPS/openprospero" submodule update --init --recursive || true
PS5GL="$CACHE/ps5-opengl-sdk-1.0.0.tar.gz"
fetch https://github.com/blackbearreloaded/ps5-opengl/releases/download/v1.0.0/ps5-opengl-sdk-1.0.0.tar.gz "$PS5GL" f93643c04c843d56143b00951df1f8042ea7706ae9f19e4e9abf158e1ead77c5
unpack "$PS5GL" "$DEPS/ps5-opengl-sdk"
ABSL="$CACHE/abseil-cpp-20250512.1.tar.gz"
fetch https://codeload.github.com/abseil/abseil-cpp/tar.gz/20250512.1 "$ABSL" 9b7a064305e9fd94d124ffa6cc358592eb42b5da588fb4e07d09254aa40086db
unpack "$ABSL" "$DEPS/core-extra/abseil-cpp"
FFMPEG="$CACHE/ffmpeg-8.1.1.tar.xz"
fetch https://ffmpeg.org/releases/ffmpeg-8.1.1.tar.xz "$FFMPEG" b6863adde98898f42602017462871b5f6333e65aec803fdd7a6308639c52edf3
unpack "$FFMPEG" "$DEPS/core-extra/ffmpeg-8.1.1"
GLEW="$CACHE/glew-2.2.0.tgz"
fetch https://github.com/nigels-com/glew/releases/download/glew-2.2.0/glew-2.2.0.tgz "$GLEW" d4fc82893cfb00109578d0a1a2337fb8ca335b3ceccf97b97e5cc7f08e4353e1
unpack "$GLEW" "$DEPS/core-extra/glew-2.2.0"
ICONV="$CACHE/libiconv-1.18.tar.gz"
fetch https://ftp.gnu.org/gnu/libiconv/libiconv-1.18.tar.gz "$ICONV" 3b08f5f4f9b4eb82f151a7040bfd6fe6c6fb922efe4b1659c66ea933276965e8
unpack "$ICONV" "$DEPS/core-extra/libiconv-1.18"
mkdir -p "$ROOT/third_party/stb"
cp "$DEPS/rpcs3-official/3rdparty/stblib/stb/stb_image.h" "$ROOT/third_party/stb/stb_image.h"
if python3 -c 'import PIL' >/dev/null 2>&1; then
  python3 "$ROOT/scripts/generate_font.py" "$ROOT/assets/font.zdf"
else
  printf 'Pillow not installed: run pip install Pillow, then scripts/generate_font.py.\n' >&2
fi
printf '\nAll source/build dependencies populated under %s\n' "$DEPS"
printf 'Next: bash scripts/prepare.sh && bash scripts/build_ps5.sh\n'
