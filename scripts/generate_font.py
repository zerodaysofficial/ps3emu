#!/usr/bin/env python3
"""Generate the ZDF1 Latin-1 font atlas consumed by src/ui_render.c."""
import argparse
import struct
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

DEFAULTS = [
    Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),
    Path('/usr/share/fonts/dejavu/DejaVuSans.ttf'),
]


def find_font(explicit):
    if explicit:
        p = Path(explicit)
        if p.is_file():
            return p
        raise SystemExit(f'Font not found: {p}')
    for p in DEFAULTS:
        if p.is_file():
            return p
    raise SystemExit('DejaVuSans.ttf not found; pass --font PATH')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('output', nargs='?', default='assets/font.zdf')
    ap.add_argument('--font')
    args = ap.parse_args()
    font_path = find_font(args.font)
    font = ImageFont.truetype(str(font_path), 48)
    atlas = Image.new('L', (1024, 896), 0)
    draw = ImageDraw.Draw(atlas)
    advances = []
    for codepoint in range(32, 256):
        ch = bytes([codepoint]).decode('latin-1')
        slot = codepoint - 32
        x = (slot % 16) * 64
        y = (slot // 16) * 64
        bbox = draw.textbbox((0, 0), ch, font=font)
        w = max(1, bbox[2] - bbox[0])
        h = max(1, bbox[3] - bbox[1])
        tx = x + max(0, (64 - w) // 2) - bbox[0]
        ty = y + max(0, (64 - h) // 2) - bbox[1]
        draw.text((tx, ty), ch, fill=255, font=font)
        advance = int(round(draw.textlength(ch, font=font)))
        advances.append(max(1, min(0xffff, advance)))
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
     
    header = b'ZDF1' + struct.pack('<HH', 1024, 896) + struct.pack('<224H', *advances)
    out.write_bytes(header + atlas.tobytes())
    print(f'{out}: {out.stat().st_size} bytes from {font_path}')


if __name__ == '__main__':
    main()
