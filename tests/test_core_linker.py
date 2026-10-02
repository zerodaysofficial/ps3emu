"""Exercise the real PS5 application linker, including absent weak imports."""
import os
import re
import struct
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SDK = ROOT / "deps/openprospero/sdk"
LINKER = ROOT / "deps/openprospero/build/bin/prospero-link"


class CoreLinkerTests(unittest.TestCase):
    def link(self, source, *options):
        compiler = os.environ.get("OPENPROSPERO_CLANG")
        lld = os.environ.get("OPENPROSPERO_LLD")
        if not compiler or not lld or not LINKER.is_file():
            self.skipTest("PS5 compiler/linker environment is required")
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            c = tmp / "probe.c"
            obj, elf = tmp / "probe.o", tmp / "probe.elf"
            c.write_text(source)
            built = subprocess.run([compiler, "--target=x86_64-sie-ps5", "-ffreestanding",
                                    "-fPIC", "-fno-stack-protector", "-c", str(c), "-o", str(obj)],
                                   capture_output=True, text=True)
            self.assertEqual(built.returncode, 0, built.stderr)
            env = dict(os.environ)
            env["LD_LIBRARY_PATH"] = str(LINKER.parent.parent / "lib") + ":" + env.get("LD_LIBRARY_PATH", "")
            linked = subprocess.run([str(LINKER), "--profile", "application", "--sdk-root", str(SDK),
                                     "--lld", lld, "--no-companion", "--", *options,
                                     str(obj), "-o", str(elf)], env=env, capture_output=True, text=True)
            symbols = subprocess.check_output(["nm", str(elf)], text=True) if linked.returncode == 0 else ""
            data = elf.read_bytes() if linked.returncode == 0 else b""
            return linked, symbols, data

    def test_absent_optional_weak_reference_binds_to_zero(self):
        result, symbols, data = self.link('''
            extern int zd_absent_optional(void) __attribute__((weak));
            int main(void) { return zd_absent_optional ? zd_absent_optional() : 7; }
        ''')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertRegex(symbols, r"(?m)^0+ A zd_absent_optional$")
        self.assertEqual(struct.unpack_from("<H", data, 16)[0], 0xfe10)

    def test_required_reference_still_fails_with_optional_reference_present(self):
        result, _, _ = self.link('''
            extern int zd_absent_optional(void) __attribute__((weak));
            extern int zd_absent_required(void);
            int main(void) { return zd_absent_required() +
                (zd_absent_optional ? zd_absent_optional() : 7); }
        ''')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("zd_absent_required", result.stderr)

    def test_available_weak_provider_remains_an_import(self):
        result, symbols, data = self.link('''
            extern unsigned long long sceKernelGetProcessTime(void) __attribute__((weak));
            int main(void) { return sceKernelGetProcessTime ?
                (int)sceKernelGetProcessTime() : 7; }
        ''', "-lkernel")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(re.search(r"(?m)^0+ A sceKernelGetProcessTime$", symbols))
        self.assertIn("sceKernelGetProcessTime", symbols)
        self.assertEqual(struct.unpack_from("<H", data, 16)[0], 0xfe10)
