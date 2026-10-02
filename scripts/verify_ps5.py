#!/usr/bin/env python3
"""Independent structural checks for the linked PS5 application ELF."""
import argparse
import hashlib
import struct
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument("elf", type=Path)
args = p.parse_args()
b = args.elf.read_bytes()
if len(b) < 64 or b[:6] != b"\x7fELF\x02\x01":
    p.error("Expected ELF64 little-endian application")
kind, machine = struct.unpack_from("<HH", b, 16)
entry, phoff = struct.unpack_from("<QQ", b, 24)
phsize, phnum = struct.unpack_from("<HH", b, 54)
if kind != 0xFE10 or machine != 62 or not entry or phsize != 56:
    p.error("Unexpected application ABI, entry or program-header format")
if phoff + phnum * phsize > len(b):
    p.error("Truncated program headers")
loads = []
for i in range(phnum):
    kind, flags, off, va, pa, filesz, memsz, align = struct.unpack_from(
        "<IIQQQQQQ", b, phoff + i * phsize)
    if off + filesz > len(b) or filesz > memsz and kind == 1:
        p.error("Invalid segment extent")
    if kind == 1:
        if align != 0x4000 or off % 0x4000 or va % 0x4000:
            p.error("LOAD offsets and addresses must be 16 KiB aligned")
        if flags & 3 == 3:
            p.error("Writable executable segment")
        loads.append((va, memsz, flags))
if not any(va <= entry < va + size and flags & 1 for va, size, flags in loads):
    p.error("Entry does not belong to an executable LOAD")
print(f"PASS: PS5 application ABI, {phnum} headers, {len(loads)} aligned LOAD segments, executable entry, no W+X LOAD")
print("SHA256 " + hashlib.sha256(b).hexdigest())
print("Structural validation only; runtime and console compatibility are unverified.")
