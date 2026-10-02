#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
set -euo pipefail
source "$(dirname -- "$0")/env.sh"
: "${ZD_EXTRA_DEPS:=$ZD_PROJECT/deps/core-extra}"
: "${ZD_FFMPEG_SOURCE:=$ZD_EXTRA_DEPS/ffmpeg-8.1.1}"
ZD_OUT="$ZD_PROJECT/build/core-ffmpeg"
ZD_PREFIX="$ZD_PROJECT/build/core-deps"
mkdir -p "$ZD_OUT" "$ZD_PROJECT/logs"
[[ -f "$ZD_FFMPEG_SOURCE/configure" ]] || { printf 'Missing FFmpeg source: %s\n' "$ZD_FFMPEG_SOURCE" >&2; exit 1; }
ZD_RESOURCE=$("$OPENPROSPERO_CLANG" -print-resource-dir)
ZD_CFLAGS="--target=x86_64-sie-ps5 -I$ZD_PROJECT/core/compat -ffreestanding -fPIC -femulated-tls -nostdinc -isystem $OPENPROSPERO_SDK/target/cxx/include -isystem $ZD_RESOURCE/include -isystem $OPENPROSPERO_SDK/target/include"
if [[ ! -f "$ZD_OUT/ffbuild/config.mak" ]]; then
  (cd "$ZD_OUT" && bash "$ZD_FFMPEG_SOURCE/configure" \
    --prefix="$ZD_PREFIX" --enable-cross-compile --arch=x86_64 --target-os=freebsd \
    --cc="$OPENPROSPERO_CLANG" --ld="$OPENPROSPERO_LLD" --ar="$OPENPROSPERO_AR" \
    --extra-cflags="$ZD_CFLAGS" \
    --extra-ldflags="-m elf_x86_64 -L$OPENPROSPERO_SDK/target/lib -e main" \
    --extra-libs="-lc -lkernel -lScePosix" \
    --disable-programs --disable-doc --disable-shared --enable-static --enable-pic \
    --disable-x86asm --disable-autodetect --disable-network --disable-everything \
    --enable-decoder=aac,aac_latm,atrac3,atrac3p,atrac9,mp3,pcm_s16le,pcm_s8,h264,mpeg4,mpeg2video,mjpeg,mjpegb \
    --enable-encoder=pcm_s16le,ac3,aac,ffv1,mpeg4,mjpeg \
    --enable-muxer=avi,h264,mjpeg,mp4 \
    --enable-demuxer=h264,m4v,mp3,mpegvideo,mpegps,mjpeg,mov,avi,aac,pmp,oma,pcm_s16le,pcm_s8,wav \
    --enable-parser=h264,mpeg4video,mpegaudio,mpegvideo,mjpeg,aac,aac_latm \
    --enable-protocol=file --enable-bsf=mjpeg2jpeg)
fi
make -C "$ZD_OUT" -j "${ZD_JOBS:-4}"
make -C "$ZD_OUT" install
printf 'PS5 FFmpeg source build installed: %s\n' "$ZD_PREFIX"
