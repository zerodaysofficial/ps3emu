// SPDX-License-Identifier: GPL-3.0-or-later
#include "stdafx.h"
#include "core_bridge.h"
#include "callbacks.hpp"
#include "launch_request.hpp"
#include "Emu/System.h"
#include "Emu/system_config.h"
#include "Utilities/File.h"
#include <chrono>
#include <cstdio>
#include <cstring>
#include <thread>

[[noreturn]] void report_fatal_error(std::string_view, bool, bool);
namespace {
zd::main_queue queue;
bool initialized = false;
std::thread::id owner;
void message(char* out, std::size_t capacity, const char* text) {
    if (out && capacity) std::snprintf(out, capacity, "%s", text);
}
bool on_owner() { return owner == std::this_thread::get_id(); }
}

// Original lifecycle wait helper. Pump our owner queue while waiting for the
// real predicate, so joining core workers never blocks their main callbacks.
void qt_events_aware_op(int interval_ms, std::function<bool()> done) {
    const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(30);
    while (!done()) {
        if (on_owner()) queue.drain();
        if (std::chrono::steady_clock::now() >= deadline)
            report_fatal_error("RPCS3 lifecycle wait timed out", false, false);
        std::this_thread::sleep_for(std::chrono::milliseconds(interval_ms > 0 ? interval_ms : 1));
    }
}

extern "C" int zd_core_initialize(char* out, std::size_t capacity) {
    if (initialized) {
        message(out, capacity, on_owner() ? "Core RPCS3 inizializzato (backend Null)." : "Thread RPCS3 errato.");
        return on_owner();
    }
    owner = std::this_thread::get_id();
    try {
        queue.bind_owner();
        zd::install_callbacks(queue);
        if (!fs::create_path(fs::get_config_dir()) || !fs::create_path(fs::get_cache_dir()))
            throw std::runtime_error("Directory /download0/rpcs3 non scrivibile");
        Emu.SetHasGui(false);
        Emu.SetHeadless(true);
        Emu.SetUsr("00000001");
        Emu.SetSupportedRenderers({video_renderer::null});
        Emu.SetDefaultRenderer(video_renderer::null);
        Emu.Init();
        initialized = true;
        message(out, capacity, "Core RPCS3 inizializzato (backend Null).");
        return 1;
    } catch (const std::exception& error) {
        message(out, capacity, error.what());
        std::fprintf(stderr, "RPCS3 initialization failed: %s\n", error.what());
        Emulator::CleanUp();
        queue.close();
        return 0;
    }
}

extern "C" int zd_core_boot(const char* eboot, const char* title, char* out, std::size_t capacity) {
    if (!initialized || !on_owner()) { message(out, capacity, "Core RPCS3 non inizializzato."); return 0; }
    if (!eboot || !title || !zd::valid_launch(std::string_view{eboot, strnlen(eboot, 1024)},
                                             std::string_view{title, strnlen(title, 20)})) {
        message(out, capacity, "Percorso di avvio RPCS3 non valido."); return 0;
    }
    if (!Emu.IsStopped(true)) { message(out, capacity, "RPCS3 è già attivo."); return 0; }
    try {
        Emu.SetForceBoot(true);
        const auto result = Emu.BootGame(eboot, title, true);
        if (result != game_boot_result::no_errors) {
            const auto error = fmt::format("RPCS3: %s", result);
            message(out, capacity, error.c_str());
            std::fprintf(stderr, "%s\n", error.c_str());
            return 0;
        }
        message(out, capacity, "Avvio RPCS3 richiesto. Video/audio/input gioco: backend Null.");
        return 1;
    } catch (const std::exception& error) {
        message(out, capacity, error.what());
        Emu.Kill(false);
        return 0;
    }
}

extern "C" void zd_core_poll() {
    if (!initialized) return;
    try { queue.drain(); }
    catch (const std::exception& error) { report_fatal_error(error.what(), false, false); }
}

extern "C" void zd_core_shutdown() {
    if (!initialized) return;
    if (!on_owner()) report_fatal_error("Core shutdown on wrong thread", false, false);
    Emu.Kill(false);
    const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(30);
    while (!Emu.IsStopped(true)) {
        zd_core_poll();
        if (std::chrono::steady_clock::now() >= deadline)
            report_fatal_error("Core shutdown timed out", false, false);
        std::this_thread::sleep_for(std::chrono::milliseconds(1));
    }
    zd_core_poll();
    Emulator::CleanUp();
    zd_core_poll();
    queue.close();
    initialized = false;
}
