import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class CoreLaunchTests(unittest.TestCase):
    def test_launch_accepts_only_bounded_usb_executables(self):
        source = r'''
        #include "launch_request.hpp"
        #include <string>
        int main() {
            using zd::valid_launch;
            if(!valid_launch("/mnt/usb0/GAME/PS3_GAME/USRDIR/EBOOT.BIN", "BLUS12345")) return 1;
            if(!valid_launch("/mnt/usb7/A B/USRDIR/EBOOT.BIN", "")) return 2;
            for(const char* bad : {"/mnt/usb8/GAME/EBOOT.BIN", "/mnt/usb0/../EBOOT.BIN",
                 "/mnt/usb0/GAME/./EBOOT.BIN", "/mnt/usb0//EBOOT.BIN", "/app0/EBOOT.BIN",
                 "/mnt/usb0/GAME/EBOOT.BIN\n", "/mnt/usb0/GAME/PARAM.SFO"})
                if(valid_launch(bad, "BLUS12345")) return 3;
            if(valid_launch("/mnt/usb0/GAME/EBOOT.BIN", "BLUS/2345")) return 4;
            if(valid_launch("/mnt/usb0/"+std::string(1024,'A')+"/EBOOT.BIN", "")) return 5;
            return 0;
        }
        '''
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / "launch.cpp").write_text(source)
            result = subprocess.run(["c++", "-std=c++23", "-Wall", "-Wextra", "-Werror",
                                     "-I", str(ROOT / "core"), str(tmp / "launch.cpp"),
                                     "-o", str(tmp / "launch")], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(subprocess.run([str(tmp / "launch")]).returncode, 0)
