#!/usr/bin/env python3
"""Apply the versioned target adapter, or verify that it is already applied."""
import subprocess
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
patch = Path(__file__).resolve().parents[1] / "core/patches/rpcs3-ps5.patch"
base = ["git", "apply", "--whitespace=nowarn"]
def check(reverse=False):
    return subprocess.run(base + (["--reverse"] if reverse else []) +
                          ["--check", str(patch)], cwd=root,
                          capture_output=True, text=True)
if check().returncode == 0:
    subprocess.run(base + [str(patch)], cwd=root, check=True)
elif check(True).returncode != 0:
    sys.exit("RPCS3 source does not match the pinned PS5 patch; refusing to modify it")
