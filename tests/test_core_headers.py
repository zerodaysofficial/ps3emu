import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class CoreHeaderTests(unittest.TestCase):
    def test_integer_headers_are_self_contained_in_both_orders(self):
        cc = os.environ.get("OPENPROSPERO_CLANG") or shutil.which("clang-19")
        if not cc:
            self.skipTest("Clang 19 target compiler unavailable")
        sdk = Path(os.environ.get("OPENPROSPERO_SDK", ROOT / "deps/openprospero/sdk"))
        resource = subprocess.check_output([cc, "-print-resource-dir"], text=True).strip()
        for headers in (("inttypes.h", "stdint.h"), ("stdint.h", "inttypes.h")):
            with self.subTest(headers=headers), tempfile.TemporaryDirectory() as tmp:
                src = Path(tmp) / "header.c"
                src.write_text("".join(f"#include <{h}>\n" for h in headers) +
                               '_Static_assert(sizeof(uint64_t) == 8, "64-bit ABI");\n'
                               '_Static_assert(sizeof(intmax_t) == 8, "intmax ABI");\n'
                               'const char *format = PRIu64;\n')
                result = subprocess.run([
                    cc, "--target=x86_64-sie-ps5", "-std=c17", "-ffreestanding",
                    "-nostdinc", "-I", str(ROOT / "core/compat"),
                    "-isystem", str(sdk / "target/cxx/include"),
                    "-isystem", str(Path(resource) / "include"),
                    "-isystem", str(sdk / "target/include"),
                    "-fsyntax-only", str(src)
                ], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
