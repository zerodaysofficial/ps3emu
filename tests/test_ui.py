import ctypes as C
import unittest
from test_catalog import Catalog, Game, load_lib


class Ui(C.Structure):
    _fields_ = [("selected",C.c_char*1024),("fingerprint",C.c_uint64),
                ("initialized",C.c_uint),("present",C.c_uint),("page",C.c_uint)]


class Intent(C.Structure):
    _fields_ = [("key",C.c_char*1024),("fingerprint",C.c_uint64),("valid",C.c_uint)]


class Pad(C.Structure):
    _fields_ = [("buttons",C.c_uint32),("connected",C.c_uint),("lx",C.c_ubyte),("ly",C.c_ubyte)]


def catalog(*names):
    c = Catalog()
    c.count = len(names)
    for i, name in enumerate(names):
        c.games[i].key = ("/usb/"+name).encode()
        c.games[i].title = name.encode()
        c.games[i].fingerprint = sum(name.encode())
        c.games[i].metadata_ok = c.games[i].files_ok = 1
    return c


class UiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lib=load_lib()
        cls.lib.zd_ui_refresh.argtypes=[C.POINTER(Ui),C.POINTER(Catalog)]
        cls.lib.zd_ui_index.argtypes=[C.POINTER(Ui),C.POINTER(Catalog)]
        cls.lib.zd_ui_index.restype=C.c_int
        cls.lib.zd_ui_move.argtypes=[C.POINTER(Ui),C.POINTER(Catalog),C.c_int]
        cls.lib.zd_ui_capture.argtypes=[C.POINTER(Ui),C.POINTER(Catalog)]
        cls.lib.zd_ui_capture.restype=Intent
        cls.lib.zd_ui_validate.argtypes=[C.POINTER(Intent),C.POINTER(Catalog)]
        cls.lib.zd_ui_validate.restype=C.c_int
        cls.lib.zd_ui_pick.argtypes=[C.POINTER(Ui),C.POINTER(Catalog),C.c_float,C.c_float]
        cls.lib.zd_pad_decode.argtypes=[C.POINTER(C.c_ubyte),C.c_size_t]
        cls.lib.zd_pad_decode.restype=Pad

    def refresh(self,u,c): self.lib.zd_ui_refresh(C.byref(u),C.byref(c))
    def move(self,u,c,d): self.lib.zd_ui_move(C.byref(u),C.byref(c),d)
    def index(self,u,c): return self.lib.zd_ui_index(C.byref(u),C.byref(c))
    def capture(self,u,c): return self.lib.zd_ui_capture(C.byref(u),C.byref(c))
    def valid(self,i,c): return self.lib.zd_ui_validate(C.byref(i),C.byref(c))

    def test_selected_title_survives_insertion_before_it(self):
        u,c=Ui(),catalog("Bravo","Delta")
        self.refresh(u,c)
        self.move(u,c,2)
        self.refresh(u,catalog("Alpha","Bravo","Delta"))
        self.assertEqual(u.selected,b"/usb/Delta")
        self.assertEqual(self.index(u,catalog("Alpha","Bravo","Delta")),2)

    def test_removed_selection_never_falls_back_to_another_game(self):
        u,c=Ui(),catalog("Alpha","Bravo")
        self.refresh(u,c)
        i=self.capture(u,c)
        updated=catalog("Bravo")
        self.refresh(u,updated)
        self.assertEqual(self.index(u,updated),-1)
        self.assertEqual(self.capture(u,updated).valid,0)
        self.assertEqual(self.valid(i,updated),0)
        self.move(u,updated,2)
        self.assertEqual(self.index(u,updated),0)

    def test_captured_confirm_cannot_transfer_after_reorder(self):
        u,c=Ui(),catalog("Bravo","Delta")
        self.refresh(u,c)
        i=self.capture(u,c)
        updated=catalog("Alpha","Bravo","Delta")
        self.assertEqual(self.valid(i,updated),1)
        self.assertEqual(i.key,b"/usb/Bravo")

    def test_replaced_game_at_same_path_invalidates_capture(self):
        u,c=Ui(),catalog("Alpha")
        self.refresh(u,c)
        i=self.capture(u,c)
        c.games[0].fingerprint+=1
        self.refresh(u,c)
        self.assertEqual(self.valid(i,c),0)

    def test_initial_empty_catalog_selects_first_when_usb_appears(self):
        u=Ui()
        self.refresh(u,catalog())
        self.refresh(u,catalog("Alpha"))
        self.assertEqual(u.selected,b"/usb/Alpha")

    def test_refresh_cannot_accept_replacement_until_explicit_reselection(self):
        u,c=Ui(),catalog("Alpha")
        self.refresh(u,c)
        old=u.fingerprint
        c.games[0].fingerprint+=1
        self.refresh(u,c)
        self.assertEqual(u.fingerprint,old)
        self.assertEqual(self.capture(u,c).valid,0)
        self.assertEqual(self.index(u,c),-1)
        self.lib.zd_ui_pick(C.byref(u),C.byref(c),100,250)
        self.assertEqual(self.capture(u,c).valid,1)

    def test_page_navigation_and_final_partial_page(self):
        u,c=Ui(),catalog(*(f"Game{i:02d}" for i in range(13)))
        self.refresh(u,c)
        self.move(u,c,5)
        self.assertEqual((self.index(u,c),u.page),(6,1))
        self.move(u,c,5)
        self.assertEqual((self.index(u,c),u.page),(12,2))
        self.move(u,c,5)
        self.assertEqual(self.index(u,c),12)
        self.move(u,c,6)
        self.assertEqual((self.index(u,c),u.page),(6,1))

    def test_mouse_select_and_visible_page_controls(self):
        u,c=Ui(),catalog(*(f"Game{i:02d}" for i in range(9)))
        self.refresh(u,c)
        self.assertEqual(self.lib.zd_ui_pick(C.byref(u),C.byref(c),390,240),1)
        self.assertEqual(self.index(u,c),1)
        self.assertEqual(self.lib.zd_ui_pick(C.byref(u),C.byref(c),877,182),1)
        self.assertEqual(u.page,1)

    def test_invalid_entry_cannot_capture_launch(self):
        u,c=Ui(),catalog("Alpha")
        c.games[0].metadata_ok=0
        self.refresh(u,c)
        self.assertEqual(self.capture(u,c).valid,0)

    def test_controller_connection_interception_and_short_buffer_neutral(self):
        b=(C.c_ubyte*1024)()
        b[0]=0x20;b[4]=b[5]=128;b[76]=1
        p=self.lib.zd_pad_decode(b,1024)
        self.assertEqual((p.buttons,p.connected,p.lx,p.ly),(0x20,1,128,128))
        b[3]=0x80
        p=self.lib.zd_pad_decode(b,1024)
        self.assertEqual((p.buttons,p.connected,p.lx,p.ly),(0,0,128,128))
        b[3]=0;b[76]=0
        self.assertEqual(self.lib.zd_pad_decode(b,1024).buttons,0)
        self.assertEqual(self.lib.zd_pad_decode(b,12).lx,128)


if __name__=="__main__": unittest.main()
