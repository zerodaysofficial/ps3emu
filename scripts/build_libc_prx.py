#!/usr/bin/env python3
"""Build the small OpenProspero loader-companion libc.prx used by this port.

The real C/C++ imports of eboot.bin resolve against libSceLibcInternal.sprx.
This module only satisfies the application sce_module layout expected by the
PS5 loader; it is generated entirely from OpenProspero output and contains no
Sony firmware code.
"""
import argparse
import os
import struct
import subprocess
from pathlib import Path


def read16(b, o): return struct.unpack_from('<H', b, o)[0]
def read32(b, o): return struct.unpack_from('<I', b, o)[0]
def read64(b, o): return struct.unpack_from('<Q', b, o)[0]
def write16(b, o, v): struct.pack_into('<H', b, o, v)
def write32(b, o, v): struct.pack_into('<I', b, o, v)
def write64(b, o, v): struct.pack_into('<Q', b, o, v)


def va_to_offset(b, phoff, entsz, phnum, va):
    for i in range(phnum):
        p = phoff + i * entsz
        if read32(b, p) != 1:
            continue
        off, addr, size = read64(b, p + 8), read64(b, p + 0x10), read64(b, p + 0x20)
        if addr <= va < addr + size:
            return off + va - addr
    raise RuntimeError(f'VA 0x{va:x} is not file-backed')


def retarget_application(app, module):
    b = bytearray(app.read_bytes())
    if b[:4] != b'\x7fELF' or read16(b, 0x10) != 0xFE10:
        raise RuntimeError('OpenProspero application ELF expected')
    phoff, entsz, phnum = read64(b, 0x20), read16(b, 0x36), read16(b, 0x38)
    if entsz != 56:
        raise RuntimeError('unexpected program-header size')
    write16(b, 0x10, 0xFE18)       # ET_SCE_DYNAMIC
    write64(b, 0x18, 0)            # modules have no application entry point
    proc = dyn = comment = None
    first_load = None
    for i in range(phnum):
        p = phoff + i * entsz
        typ = read32(b, p)
        if typ == 1 and first_load is None:
            first_load = read64(b, p + 8)
        elif typ == 0x61000001:
            proc = p
        elif typ == 2:
            dyn = p
        elif typ == 0x6FFFFF00:
            comment = p
        elif typ == 6:
            raise RuntimeError('PT_PHDR is not valid for this PRX layout')
    if first_load is None or first_load < 0x4000 or proc is None or dyn is None:
        raise RuntimeError('OpenProspero did not emit the expected PS5 application layout')

    # PT_SCE_PROCPARAM -> PT_SCE_MODULEPARAM and canonical 0x20-byte record.
    write32(b, proc, 0x61000002)
    write64(b, proc + 0x20, 0x20); write64(b, proc + 0x28, 0x20); write64(b, proc + 0x30, 8)
    mp = read64(b, proc + 8)
    record = (struct.pack('<Q', 0x20) + struct.pack('<I', 0x3C13F4BF) +
              struct.pack('<I', 3) + struct.pack('<I', 0x08050001) +
              struct.pack('<I', 0x02000009) + struct.pack('<Q', 0))
    b[mp:mp + 0x20] = record

    dynoff, dynsize = read64(b, dyn + 8), read64(b, dyn + 0x20)
    entries = []
    for off in range(dynoff, dynoff + dynsize, 16):
        tag, val = struct.unpack_from('<QQ', b, off)
        entries.append((off, tag, val))
        if tag == 0:
            break
    values = {}
    for off, tag, val in entries:
        values.setdefault(tag, []).append((off, val))
    stroff = va_to_offset(b, phoff, entsz, phnum, values[5][0][1])
    if bytes(b[stroff + 1:stroff + 7]) != b'eboot\0' or bytes(b[stroff + 7:stroff + 17]) != b'eboot.bin\0':
        raise RuntimeError('unexpected OpenProspero module/original filename strings')
    b[stroff + 1:stroff + 7] = b'libc\0\0'
    b[stroff + 7:stroff + 17] = b'libc.prx\0\0'

    replaced = set()
    for off, tag, val in entries:
        if tag == 21:              # DT_DEBUG -> DT_SONAME
            struct.pack_into('<QQ', b, off, 14, 7); replaced.add('soname')
        elif tag == 32:            # zero PREINIT slot -> export library
            struct.pack_into('<QQ', b, off, 0x61000047, (1 << 32) | 1); replaced.add('export')
        elif tag == 33:            # zero PREINIT size -> export attributes
            struct.pack_into('<QQ', b, off, 0x61000017, 1); replaced.add('attr')
        elif tag in (12, 13):      # never run application CRT init/fini as PRX
            struct.pack_into('<QQ', b, off, tag, 0)
    if replaced != {'soname', 'export', 'attr'}:
        raise RuntimeError('required dynamic slots were not present')

    if comment is not None:
        co, cs = read64(b, comment + 8), read64(b, comment + 0x20)
        rel = bytes(b[co:co + cs]).find(b'eboot.bin\0')
        if rel >= 0:
            start = co + rel
            b[start:start + len(b'eboot.bin\0')] = b'libc.prx\0\0'

    # Target loader does not require the ELF section table.
    write64(b, 0x28, 0); write16(b, 0x3C, 0); write16(b, 0x3E, 0)
    module.write_bytes(b)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--output', type=Path, default=Path('build/ps5/runtime/libc.prx'))
    args = ap.parse_args()
    root = Path(__file__).resolve().parents[1]
    op = Path(os.environ.get('OPENPROSPERO_ROOT', root / 'deps/openprospero'))
    sdk = Path(os.environ.get('OPENPROSPERO_SDK', op / 'sdk'))
    clang = os.environ.get('OPENPROSPERO_CLANG', 'clang-19')
    lld = os.environ.get('OPENPROSPERO_LLD', 'ld.lld-19')
    work = root / 'build/openprospero-libc'
    work.mkdir(parents=True, exist_ok=True)
    source, obj, app, module = work / 'main.c', work / 'main.o', work / 'app.elf', work / 'libc.elf'
    source.write_text('int main(void){return 0;}\n')
    subprocess.run([clang, '--target=x86_64-sie-ps5', '-ffreestanding', '-fPIC',
                    '-fno-stack-protector', '-c', str(source), '-o', str(obj)], check=True)
    subprocess.run([str(op / 'build/bin/prospero-link'), '--profile', 'application',
                    '--sdk-root', str(sdk), '--lld', lld, '--no-companion', '--',
                    str(obj), '-o', str(app)], check=True)
    retarget_application(app, module)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env['LD_LIBRARY_PATH'] = str(op / 'build/lib') + (':' + env['LD_LIBRARY_PATH'] if env.get('LD_LIBRARY_PATH') else '')
    subprocess.run([str(op / 'build/bin/prospero'), 'self', str(module), str(args.output)], check=True, env=env)
    print(args.output)


if __name__ == '__main__':
    main()
