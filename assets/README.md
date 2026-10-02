# Runtime font asset

`font.zdf` is generated from DejaVu Sans and is not required to be stored as an opaque binary in Git.

```sh
python3 scripts/generate_font.py assets/font.zdf
```

The renderer expects `ZDF1`, a 1024×896 8-bit alpha atlas containing Latin-1 codepoints 32–255 in 64×64 cells plus 224 little-endian advance widths. The DejaVu font license is preserved in `FONT-LICENSE.txt`.
