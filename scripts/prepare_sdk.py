#!/usr/bin/env python3
"""Repair evidenced defects in the uploaded OPSDK source, idempotently."""
from pathlib import Path
import argparse
import subprocess

p = argparse.ArgumentParser()
p.add_argument("root", type=Path)
args = p.parse_args()
root = args.root
if not (root / "src/packaging/pfs.cpp").is_file():
    p.error("OPSDK root must contain src/packaging/pfs.cpp")
changed = []
for base in (root / "tools", root / "sdk/target/stubs"):
    for f in sorted(base.rglob("*")):
        if not f.is_file():
            continue
        if base.name == "tools" and f.suffix != ".sh":
            continue
        if base.name == "stubs" and f.suffix not in (
                ".manifest", ".functions", ".objects", ".txt"):
            continue
        raw = f.read_bytes()
        normalized = raw.replace(b"\r\n", b"\n")
        if raw != normalized:
            f.write_bytes(normalized)
            changed.append(str(f.relative_to(root)))
        if f.suffix == ".sh":
            f.chmod(f.stat().st_mode | 0o111)
f = root / "src/packaging/pfs.cpp"
raw = f.read_bytes()
if b"#include <optional>" not in raw:
    nl = b"\r\n" if b"\r\n" in raw else b"\n"
    f.write_bytes(b"#include <optional>" + nl + raw)
    changed.append(str(f.relative_to(root)))
f = root / "sdk/target/stubs/libSceVideoOut.extras.functions"
raw = f.read_text() if f.exists() else "# Additional imports required by ps5-opengl 1.0.0.\n"
for symbol in ("sceVideoOutGetResolutionStatus", "sceVideoOutGetOutputStatus"):
    if symbol not in raw.splitlines():
        raw += symbol + "\n"
if not f.exists() or f.read_text() != raw:
    f.write_text(raw)
    changed.append(str(f.relative_to(root)))
patch = Path(__file__).resolve().parents[1] / "core/patches/openprospero-weak-imports.patch"
apply = ["git", "apply", "--ignore-space-change", "--whitespace=nowarn"]
checked = subprocess.run(apply + ["--check", str(patch)], cwd=root,
                         capture_output=True, text=True)
if checked.returncode == 0:
    subprocess.run(apply + [str(patch)], cwd=root, check=True)
    changed.append("src/sdk/linker.cpp (ELF weak-reference semantics)")
elif subprocess.run(apply + ["--reverse", "--check", str(patch)], cwd=root,
                    capture_output=True, text=True).returncode != 0:
    p.error("OPSDK linker source does not match the versioned weak-import patch")
print("OPSDK repairs: " + (", ".join(changed) if changed else "already applied"))
