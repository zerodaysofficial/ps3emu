import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class CoreQueueTests(unittest.TestCase):
    def test_callbacks_run_on_owner_and_queue_pressure_is_explicit(self):
        source = r'''
        #include "main_queue.hpp"
        #include <atomic>
        #include <thread>
        #include <stdexcept>
        int main() {
            zd::main_queue q(2);
            if(q.post([]{})) return 1;
            q.bind_owner();
            const auto owner = std::this_thread::get_id();
            int value = 0;
            if(!q.post([&]{value = 3;} ) || value != 3) return 2;
            bool first=false, second=false, excess=true, wrong_owner=false;
            std::thread worker([&]{
                first=q.post([&]{if(std::this_thread::get_id()!=owner) std::abort(); value=7;});
                second=q.post([&]{value+=5;});
                excess=q.post([&]{value=100;});
                try {q.drain();} catch(const std::logic_error&) {wrong_owner=true;}
            });
            worker.join();
            if(!first || !second || excess || !wrong_owner || value!=3) return 3;
            if(q.drain()!=2 || value!=12) return 4;
            std::thread failure_worker([&]{
                q.post([]{throw std::runtime_error("callback failed");});
                q.post([&]{value=15;});
            });
            failure_worker.join();
            bool failed=false;
            try {q.drain();} catch(const std::runtime_error&) {failed=true;}
            if(!failed || q.drain()!=1 || value!=15) return 6;
            int nested_count=0;
            std::size_t inner=0;
            std::thread nested_worker([&]{
                q.post([&]{++nested_count; inner=q.drain();});
                q.post([&]{++nested_count;});
            });
            nested_worker.join();
            if(q.drain()!=1 || inner!=1 || nested_count!=2 || q.drain()!=0) return 7;
            q.close();
            if(q.post([&]{value=99;}) || value!=15) return 5;
            return 0;
        }
        '''
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / "queue.cpp").write_text(source)
            built = subprocess.run(["c++", "-std=c++23", "-pthread", "-Wall", "-Wextra",
                                    "-Werror", "-D_GLIBCXX_ASSERTIONS", "-I", str(ROOT / "core"),
                                    str(tmp / "queue.cpp"), "-o", str(tmp / "queue")],
                                   capture_output=True, text=True)
            self.assertEqual(built.returncode, 0, built.stderr)
            run = subprocess.run([str(tmp / "queue")], timeout=10)
            self.assertEqual(run.returncode, 0)
