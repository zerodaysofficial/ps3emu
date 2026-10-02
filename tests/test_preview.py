import ctypes as C
import importlib.util
import tempfile
import unittest
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("zd_preview", ROOT / "scripts/preview.py")
preview = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preview)


class PreviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.usb = Path(self.temp.name)
        self.metadata = self.usb / "GAMES/Example/PS3_GAME"
        (self.metadata / "USRDIR").mkdir(parents=True)
        (self.metadata / "PARAM.SFO").write_bytes(preview.sfo("Example", "DEMO0001"))
        (self.metadata / "USRDIR/EBOOT.BIN").write_bytes(b"SCE\0NOT EXECUTABLE")
        self.app = preview.Preview([self.usb], False)

    def tearDown(self):
        self.app.lib.zd_render_shutdown()
        self.temp.cleanup()

    def test_render_two_output_sizes_and_bounded_pixel_writes(self):
        for w, h in ((1280, 720), (1920, 1080)):
            n = w * h
            buffer = (C.c_uint32 * (n + 2))()
            buffer[0], buffer[n + 1] = 0xA1B2C3D4, 0x11223344
            pixels = C.cast(C.byref(buffer, 4), C.POINTER(C.c_uint32))
            self.assertEqual(self.app.lib.zd_render(
                pixels, w, h, C.byref(self.app.ui), C.byref(self.app.catalog), 0, 0, b""), 1)
            self.assertEqual((buffer[0], buffer[n + 1]), (0xA1B2C3D4, 0x11223344))
            self.assertEqual(buffer[1] >> 24, 255)
            self.assertNotEqual(buffer[1], buffer[300 * w + 100])

    def test_malformed_and_oversized_covers_fall_back_without_crashing(self):
        for raw in (b"not a PNG", b"\x89PNG\r\n\x1a\n" + b"x" * (4 * 1024 * 1024)):
            (self.metadata / "ICON0.PNG").write_bytes(raw)
            self.app.scan()
            self.assertEqual(self.app.image().size, (1280, 720))

    def test_confirm_after_unplug_reports_unavailable_without_transferring_selection(self):
        key = self.app.ui.selected
        (self.metadata / "USRDIR/EBOOT.BIN").unlink()
        self.app.action({"confirm": True})
        self.assertIn("non è più disponibile".encode(), self.app.notice)
        self.assertEqual(self.app.ui.selected, key)

    def test_cover_read_rejects_replaced_ancestor(self):
        fallback = self.app.image().tobytes()
        Image.new("RGB", (32, 32), (245, 0, 0)).save(self.metadata / "ICON0.PNG")
        self.app.scan()
        original = self.usb / "GAMES"
        relocated = self.usb.parent / (self.usb.name + "-relocated")
        try:
            original.rename(relocated)
            original.symlink_to(relocated, target_is_directory=True)
            self.assertEqual(self.app.image().tobytes(), fallback)
        finally:
            if original.is_symlink():
                original.unlink()
            if relocated.exists():
                relocated.rename(original)
