import ctypes as C
import os
import shutil
import struct
import subprocess
import tempfile
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
PATH = 1024


class Game(C.Structure):
    _fields_ = [("key", C.c_char * PATH), ("title", C.c_char * 256),
                ("title_id", C.c_char * 20), ("version", C.c_char * 20),
                ("root", C.c_char * PATH), ("eboot", C.c_char * PATH),
                ("cover", C.c_char * PATH), ("fingerprint", C.c_uint64),
                ("metadata_ok", C.c_uint), ("files_ok", C.c_uint)]


class Catalog(C.Structure):
    _fields_ = [("games", Game * 1024), ("count", C.c_uint),
                ("mounts", C.c_uint), ("warnings", C.c_uint),
                ("limited", C.c_uint), ("generation", C.c_uint64)]


def make_sfo(title="Test Game", title_id="BLES00001", version="01.00"):
    keys, values, indices = bytearray(), bytearray(), []
    for key, value in [("TITLE", title), ("TITLE_ID", title_id), ("APP_VER", version)]:
        encoded = value.encode("utf-8") + b"\0"
        indices.append(struct.pack("<HHIII", len(keys), 0x0204, len(encoded), len(encoded), len(values)))
        keys += key.encode("ascii") + b"\0"
        values += encoded
    key_start = 20 + 16 * len(indices)
    return struct.pack("<4sIIII", b"\0PSF", 0x101, key_start, key_start + len(keys), len(indices)) + b"".join(indices) + keys + values


def make_game(root, folder="A", title="Test Game", title_id="BLES00001", disc=True):
    game = Path(root) / "GAMES" / folder
    metadata = game / "PS3_GAME" if disc else game
    (metadata / "USRDIR").mkdir(parents=True)
    (metadata / "PARAM.SFO").write_bytes(make_sfo(title, title_id))
    (metadata / "USRDIR" / "EBOOT.BIN").write_bytes(b"SCE\0test-fixture")
    (metadata / "ICON0.PNG").write_bytes(b"placeholder")
    return game, metadata


def load_lib():
    build = PROJECT / "build"
    build.mkdir(exist_ok=True)
    sources = [PROJECT / "src" / name for name in ("catalog.c", "fs.c", "ui_model.c", "input.c")]
    sources = [str(p) for p in sources if p.exists()]
    subprocess.run(["gcc", "-std=c11", "-D_POSIX_C_SOURCE=200809L", "-D_XOPEN_SOURCE=700", "-fPIC", "-shared", "-Wall", "-Wextra", "-Werror", "-I", str(PROJECT / "include"), *sources, "-o", str(build / "libcatalog.so")], check=True)
    lib = C.CDLL(str(build / "libcatalog.so"))
    lib.zd_catalog_scan.argtypes = [C.POINTER(Catalog), C.POINTER(C.c_char_p), C.c_size_t]
    lib.zd_catalog_scan.restype = C.c_int
    lib.zd_game_revalidate.argtypes = [C.POINTER(Game)]
    lib.zd_game_revalidate.restype = C.c_int
    return lib


class CatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lib = load_lib()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "usb0"
        self.root.mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def scan(self, *roots):
        roots = roots or (self.root,)
        encoded = (C.c_char_p * len(roots))(*(os.fsencode(r) for r in roots))
        out = Catalog()
        self.assertEqual(self.lib.zd_catalog_scan(C.byref(out), encoded, len(roots)), 0)
        return out

    def test_disc_metadata_cover_and_boot(self):
        game, meta = make_game(self.root)
        out = self.scan()
        self.assertEqual(out.count, 1)
        self.assertEqual(out.games[0].title, b"Test Game")
        self.assertEqual(out.games[0].title_id, b"BLES00001")
        self.assertEqual(out.games[0].version, b"01.00")
        self.assertEqual(out.games[0].key, os.fsencode(game))
        self.assertEqual(out.games[0].cover, os.fsencode(meta / "ICON0.PNG"))
        self.assertEqual(out.games[0].files_ok, 1)

    def test_psn_directory_and_utf8(self):
        make_game(self.root, title="L'avventura è qui", disc=False)
        out = self.scan()
        self.assertEqual(out.count, 1)
        self.assertEqual(out.games[0].title.decode(), "L'avventura è qui")

    def test_unplug_and_replug(self):
        make_game(self.root)
        self.assertEqual(self.scan().count, 1)
        moved = self.root.with_name("removed")
        self.root.rename(moved)
        self.assertEqual(self.scan().count, 0)
        moved.rename(self.root)
        self.assertEqual(self.scan().count, 1)

    def test_repeated_roots_deduplicated(self):
        make_game(self.root)
        out = self.scan(self.root, self.root)
        self.assertEqual(out.count, 1)
        self.assertEqual(out.mounts, 1)

    def test_same_title_on_two_drives_remains_two_entries(self):
        second = Path(self.temp.name) / "usb1"
        make_game(self.root)
        make_game(second)
        out = self.scan(self.root, second)
        self.assertEqual(out.count, 2)
        self.assertNotEqual(out.games[0].key, out.games[1].key)

    def test_corrupt_sfo_keeps_entry_with_warning(self):
        _, meta = make_game(self.root, folder="Fallback")
        (meta / "PARAM.SFO").write_bytes(b"\0PSF" + b"\xff" * 20)
        out = self.scan()
        self.assertEqual(out.count, 1)
        self.assertEqual(out.games[0].title, b"Fallback")
        self.assertEqual(out.games[0].metadata_ok, 0)
        self.assertGreater(out.warnings, 0)

    def test_overflow_offsets_and_truncated_string_rejected(self):
        _, meta = make_game(self.root)
        data = bytearray(make_sfo())
        struct.pack_into("<I", data, 36, 0xffffffff)
        (meta / "PARAM.SFO").write_bytes(data)
        self.assertEqual(self.scan().games[0].metadata_ok, 0)
        data = bytearray(make_sfo())
        data[-1] = ord("X")
        (meta / "PARAM.SFO").write_bytes(data)
        self.assertEqual(self.scan().games[0].metadata_ok, 0)

    def test_missing_boot_is_visible_but_invalid(self):
        _, meta = make_game(self.root)
        (meta / "USRDIR" / "EBOOT.BIN").unlink()
        out = self.scan()
        self.assertEqual(out.count, 1)
        self.assertEqual(out.games[0].files_ok, 0)

    def test_symlink_outside_root_and_loop_ignored(self):
        external = Path(self.temp.name) / "outside"
        make_game(external)
        (self.root / "outside").symlink_to(external, target_is_directory=True)
        (self.root / "loop").symlink_to(self.root, target_is_directory=True)
        self.assertEqual(self.scan().count, 0)

    def test_symlink_boot_is_not_a_valid_game(self):
        _, meta = make_game(self.root)
        eboot = meta / "USRDIR" / "EBOOT.BIN"
        eboot.unlink()
        outside = Path(self.temp.name) / "EBOOT.BIN"
        outside.write_bytes(b"SCE\0outside")
        eboot.symlink_to(outside)
        self.assertEqual(self.scan().games[0].files_ok, 0)

    def test_natural_scan_result_sorted_by_title(self):
        make_game(self.root, "Z", "Zeta")
        make_game(self.root, "A", "Alpha")
        out = self.scan()
        self.assertEqual([out.games[i].title for i in range(out.count)], [b"Alpha", b"Zeta"])

    def test_incremental_scan_and_cancel(self):
        make_game(self.root)
        self.lib.zd_scan_begin.argtypes = [C.POINTER(Catalog), C.POINTER(C.c_char_p), C.c_size_t]
        self.lib.zd_scan_begin.restype = C.c_void_p
        self.lib.zd_scan_step.argtypes = [C.c_void_p, C.c_uint]
        self.lib.zd_scan_end.argtypes = [C.c_void_p]
        roots = (C.c_char_p * 1)(os.fsencode(self.root))
        out = Catalog()
        s = self.lib.zd_scan_begin(C.byref(out), roots, 1)
        self.assertTrue(s)
        iterations = 0
        while not self.lib.zd_scan_step(s, 1):
            iterations += 1
            self.assertLess(iterations, 100)
        self.lib.zd_scan_end(s)
        self.assertGreater(iterations, 0)
        self.assertEqual(out.count, 1)
        s = self.lib.zd_scan_begin(C.byref(out), roots, 1)
        self.lib.zd_scan_end(s)

    def test_revalidation_rejects_replaced_metadata_and_unplug(self):
        _, meta = make_game(self.root)
        out = self.scan()
        g = out.games[0]
        self.assertEqual(self.lib.zd_game_revalidate(C.byref(g)), 1)
        (meta / "PARAM.SFO").write_bytes(make_sfo("Another Game", "BLES99999"))
        self.assertEqual(self.lib.zd_game_revalidate(C.byref(g)), 0)

    def test_revalidation_rejects_ancestor_redirect_even_with_same_game_inodes(self):
        make_game(self.root)
        g = self.scan().games[0]
        original = self.root / "GAMES"
        outside = Path(self.temp.name) / "relocated"
        original.rename(outside)
        original.symlink_to(outside, target_is_directory=True)
        self.assertEqual(self.lib.zd_game_revalidate(C.byref(g)), 0)
        self.assertEqual(self.scan().count, 0)
        shutil.rmtree(self.root)
        self.assertEqual(self.lib.zd_game_revalidate(C.byref(g)), 0)


if __name__ == "__main__":
    unittest.main()
