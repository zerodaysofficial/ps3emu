import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class CoreDialogTests(unittest.TestCase):
    def test_unavailable_message_callbacks_cancel_without_null_or_mutating_messages(self):
        cc = os.environ.get("OPENPROSPERO_CLANGXX") or shutil.which("clang++-19")
        if not cc:
            self.skipTest("Clang 19 is required for original RPCS3 headers")
        source = r'''
        #include "message_dialogs.hpp"
        int main() {
            emu_callbacks cb;
            zd::install_message_callbacks(cb);
            auto send = cb.get_sendmessage_dialog();
            auto recv = cb.get_recvmessage_dialog();
            if(!send || !recv) return 1;
            message_data message{};
            message.body="unchanged";
            std::set<std::string> recipients{"recipient"};
            if(send->Exec(message,recipients)!=CELL_CANCEL || message.body!="unchanged"
                || recipients!=std::set<std::string>{"recipient"}) return 2;
            SceNpBasicMessageRecvAction action=42;
            u64 chosen=123;
            if(recv->Exec(static_cast<SceNpBasicMessageMainType>(0),
                static_cast<SceNpBasicMessageRecvOptions>(0),action,chosen)!=CELL_CANCEL
                || action!=0 || chosen!=0) return 3;
            return 0;
        }
        '''
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / "dialog.cpp").write_text(source)
            upstream = ROOT / "deps/rpcs3-official"
            result = subprocess.run([cc, "--target=x86_64-unknown-linux-gnu", "-std=c++23",
                                     "-mcx16", "-msse4.1", "-pthread", "-Wno-deprecated-declarations",
                                     "-I", str(ROOT / "core"), "-I", str(upstream),
                                     "-I", str(upstream / "rpcs3"), str(tmp / "dialog.cpp"),
                                     "-o", str(tmp / "dialog")], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(subprocess.run([str(tmp / "dialog")], timeout=10).returncode, 0)
