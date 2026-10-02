#!/usr/bin/env python3
"""Verify actual core objects and retained definitions in the final target ELF."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument("build", type=Path)
p.add_argument("elf", type=Path)
args = p.parse_args()
archive = args.build / "emu/librpcs3_emu.a"
members = subprocess.check_output(["ar", "t", str(archive)], text=True).splitlines()
for required in ("System.cpp.o", "PPUInterpreter.cpp.o", "SPUInterpreter.cpp.o",
                 "sys_memory.cpp.o", "cellGcmSys.cpp.o", "RSXThread.cpp.o"):
    if required not in members:
        p.error("Original emulation archive is incomplete: " + required)
symbols = subprocess.check_output(["nm", "-C", "--defined-only", str(args.elf)], text=True)
for required in ("Emulator::Init()", "Emulator::BootGame(", "Emulator::Kill(",
                 "zd_core_initialize", "zd_core_boot", "ppu_thread::cpu_task()",
                 "spu_thread::cpu_task()"):
    if required not in symbols:
        p.error("Final application does not retain core definition: " + required)
linkmap = (args.build / "application.map").read_text()
if "librpcs3_emu.a(System.cpp.o)" not in linkmap:
    p.error("Final emulator lifecycle did not come from the original source archive")
compiled = json.loads((args.build / "compile_commands.json").read_text())
core = [entry for entry in compiled if "/rpcs3_emu.dir/" in entry.get("output", entry["command"])]
if len(core) != len(members):
    p.error("Archive member count differs from the complete configured original target")
if any("--target=x86_64-sie-ps5" not in entry["command"] for entry in core):
    p.error("Emulation target contains a non-PS5 compile command")
record = {
    "rpcs3_revision": "17320679e329908af40b76a8a48c43025d4acc9a",
    "original_core_translation_units": len(core),
    "archive_members": len(members),
    "core_archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
    "application_sha256": hashlib.sha256(args.elf.read_bytes()).hexdigest(),
    "link_profile": "application --no-companion; unresolved references rejected",
    "console_execution_verified": False,
    "game_video_audio_input": "Original Null providers; native providers pending",
}
(args.build / "core-link-proof.json").write_text(json.dumps(record, indent=2) + "\n")
print(json.dumps(record, indent=2))
