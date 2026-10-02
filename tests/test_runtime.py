import ctypes as C
import errno
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class RuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        out = ROOT / "build/libruntime-shims.so"
        out.parent.mkdir(exist_ok=True)
        subprocess.run(["cc", "-std=c11", "-shared", "-fPIC", "-Wall", "-Wextra",
                        "-Werror", str(ROOT / "src/runtime_shims.c"), "-o", str(out)], check=True)
        cls.lib = C.CDLL(str(out), use_errno=True)
        cls.lib.mkstemp.argtypes = [C.c_char_p]
        cls.lib.mkstemps.argtypes = [C.c_char_p, C.c_int]
        cls.lib.isatty.argtypes = [C.c_int]
        cls.lib.popen.argtypes = [C.c_char_p, C.c_char_p]
        cls.lib.popen.restype = C.c_void_p
        cls.lib.pclose.argtypes = [C.c_void_p]

    def test_unavailable_optional_disk_cache_leaves_template_unchanged(self):
        path = C.create_string_buffer(b"/private/cache.XXXXXX")
        for f, args in ((self.lib.mkstemp, (path,)), (self.lib.mkstemps, (path, 0))):
            C.set_errno(0)
            self.assertEqual(f(*args), -1)
            self.assertEqual(C.get_errno(), errno.ENOSYS)
            self.assertEqual(path.value, b"/private/cache.XXXXXX")

    def test_assembler_diagnostics_do_not_start_host_processes(self):
        C.set_errno(0)
        self.assertFalse(self.lib.popen(b"exit 99", b"r"))
        self.assertEqual(C.get_errno(), errno.ENOSYS)
        self.assertEqual(self.lib.pclose(None), -1)
        self.assertEqual(C.get_errno(), errno.ENOSYS)

    def test_lexer_receives_non_terminal_answer(self):
        C.set_errno(0)
        self.assertEqual(self.lib.isatty(0), 0)
        self.assertEqual(C.get_errno(), errno.ENOTTY)
