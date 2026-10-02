import ctypes as C
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class DecodeBudgetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        out = ROOT / "build/libdecode-budget.so"
        out.parent.mkdir(exist_ok=True)
        subprocess.run(["cc", "-std=c11", "-shared", "-fPIC", "-Wall", "-Wextra", "-Werror",
                        "-I", str(ROOT / "include"), str(ROOT / "src/decode_budget.c"),
                        "-o", str(out)], check=True)
        cls.lib = C.CDLL(str(out))
        cls.lib.zd_decode_begin.argtypes = [C.c_size_t]
        cls.lib.zd_decode_malloc.argtypes = [C.c_size_t]
        cls.lib.zd_decode_malloc.restype = C.c_void_p
        cls.lib.zd_decode_realloc.argtypes = [C.c_void_p, C.c_size_t]
        cls.lib.zd_decode_realloc.restype = C.c_void_p
        cls.lib.zd_decode_free.argtypes = [C.c_void_p]
        cls.lib.zd_decode_live.restype = cls.lib.zd_decode_peak.restype = C.c_size_t

    def test_peak_allocation_is_bounded_including_reallocation_and_cleanup(self):
        self.assertEqual(self.lib.zd_decode_begin(65536), 1)
        a = self.lib.zd_decode_malloc(40000)
        self.assertTrue(a)
        try:
            C.memset(a, 0x41, 40000)
            self.assertFalse(self.lib.zd_decode_malloc(40000))
            self.assertFalse(self.lib.zd_decode_realloc(a, 50000))
            self.assertEqual(C.string_at(a, 4), b"AAAA")
            b = self.lib.zd_decode_realloc(a, 1024)
            self.assertTrue(b)
            a = b
            self.assertEqual(C.string_at(a, 4), b"AAAA")
            self.assertLessEqual(self.lib.zd_decode_peak(), 65536)
        finally:
            self.lib.zd_decode_free(a)
        self.assertEqual(self.lib.zd_decode_live(), 0)

    def test_size_overflow_fails_without_an_allocation(self):
        self.assertEqual(self.lib.zd_decode_begin(65536), 1)
        self.assertFalse(self.lib.zd_decode_malloc(C.c_size_t(-1).value))
        self.assertEqual(self.lib.zd_decode_live(), 0)
