// SPDX-License-Identifier: GPL-3.0-or-later
#include "stdafx.h"
#include "callbacks.hpp"
#include "message_dialogs.hpp"
#include "Emu/System.h"
#include "Emu/emu_callbacks.h"
#include "Emu/system_config.h"
#include "Emu/RSX/Null/NullGSRender.h"
#include "Emu/Audio/Null/NullAudioBackend.h"
#include "Emu/Audio/Null/null_enumerator.h"
#include "Emu/Io/Null/NullKeyboardHandler.h"
#include "Emu/Io/Null/NullMouseHandler.h"
#include "Emu/Io/Null/null_camera_handler.h"
#include "Emu/Io/Null/null_music_handler.h"
#include "Emu/Io/pad_config.h"
#include "Emu/Cell/Modules/cellMsgDialog.h"
#include "Emu/Cell/Modules/cellOskDialog.h"
#include "Emu/Cell/Modules/cellSaveData.h"
#include "Emu/Cell/Modules/sceNpTrophy.h"
#include "Input/pad_thread.h"
#include "util/video_source.h"
#include <cstdio>
#include <cstdlib>

 
std::string g_input_config_override;
cfg_input_configurations g_cfg_input_configs;

[[noreturn]] void report_fatal_error(std::string_view message, bool, bool) {
    std::fprintf(stderr, "RPCS3 fatal: %.*s\n", static_cast<int>(message.size()), message.data());
    std::abort();
}

namespace {
void unavailable(const char* service) {
    std::fprintf(stderr, "RPCS3 PS5: %s unavailable in this core integration build.\n", service);
}
void wake(atomic_t<u32>* waiter) {
    if (waiter) { *waiter = 1; waiter->notify_one(); }
}
}

void zd::install_callbacks(main_queue& queue) {
    auto& cb = g_emu_callbacks;
    cb.call_from_main_thread = [&queue](std::function<void()> fn, atomic_t<u32>* waiter) {
        const bool accepted = queue.post([fn = std::move(fn), waiter] {
            try { fn(); }
            catch (...) { wake(waiter); throw; }
            wake(waiter);
        });
        if (!accepted) report_fatal_error("Main callback queue closed or full", false, false);
    };
    cb.on_run = [](bool) { std::fprintf(stderr, "RPCS3 core running with Null output/input providers.\n"); };
    cb.on_pause = [] { std::fprintf(stderr, "RPCS3 paused.\n"); };
    cb.on_resume = [] { std::fprintf(stderr, "RPCS3 resumed.\n"); };
    cb.on_stop = [] { std::fprintf(stderr, "RPCS3 stopped.\n"); };
    cb.on_ready = [] { std::fprintf(stderr, "RPCS3 ready.\n"); };
    cb.on_missing_fw = [] { std::fprintf(stderr, "RPCS3: PS3 firmware missing from /download0/rpcs3/dev_flash.\n"); };
    cb.on_emulation_stop_no_response = [](std::shared_ptr<atomic_t<bool>> done, int) {
        if (!done || !*done) report_fatal_error("Emulator shutdown timed out", false, false);
    };
    cb.on_save_state_progress = [](std::shared_ptr<atomic_t<bool>>, stx::shared_ptr<utils::serial>,
                                   stx::atomic_ptr<std::string>*, std::shared_ptr<void>) {};
    cb.enable_disc_eject = [](bool) {};
    cb.enable_disc_insert = [](bool) {};
     
    cb.try_to_quit = [](bool, std::function<void()>) { return false; };
    cb.handle_taskbar_progress = [](s32, s32) {};
    cb.init_kb_handler = [] {
        ensure(g_fxo->init<KeyboardHandlerBase, NullKeyboardHandler>(Emu.DeserialManager()));
    };
    cb.init_mouse_handler = [] {
        ensure(g_fxo->init<MouseHandlerBase, NullMouseHandler>(Emu.DeserialManager()));
    };
    cb.init_pad_handler = [](std::string_view title) {
        ensure(g_fxo->init<named_thread<pad_thread>>(nullptr, nullptr, title));
    };
    cb.update_emu_settings = [] {};
    cb.save_emu_settings = [] {
        Emu.BlockingCallFromMainThread([] {
            Emulator::SaveSettings(g_cfg.to_string(), Emu.GetTitleID());
        });
    };
    cb.close_gs_frame = [] {};
    cb.get_gs_frame = [] { return std::unique_ptr<GSFrameBase>{}; };
    cb.get_camera_handler = [] { return std::make_shared<null_camera_handler>(); };
    cb.get_music_handler = [] { return std::make_shared<null_music_handler>(); };
    cb.init_gs_render = [](utils::serial* ar) {
        if (g_cfg.video.renderer != video_renderer::null)
            fmt::throw_exception("PS5 game video provider is not qualified");
        ensure(g_fxo->init<rsx::thread, named_thread<NullGSRender>>(ar));
    };
    cb.get_audio = [] { return std::make_shared<NullAudioBackend>(); };
    cb.get_audio_enumerator = [](u64) { return std::make_shared<null_enumerator>(); };
    cb.get_msg_dialog = [] { unavailable("message dialog"); return std::shared_ptr<MsgDialogBase>{}; };
    cb.get_osk_dialog = [] { unavailable("on-screen keyboard"); return std::shared_ptr<OskDialogBase>{}; };
    cb.get_save_dialog = [] { unavailable("save dialog"); return std::unique_ptr<SaveDialogBase>{}; };
    install_message_callbacks(cb);
    cb.get_trophy_notification_dialog = [] { return std::unique_ptr<TrophyNotificationBase>{}; };
    cb.get_localized_string = [](localized_string_id id, const char* args) {
        return fmt::format("RPCS3 message %u: %s", static_cast<u32>(id), args ? args : "");
    };
    cb.get_localized_u32string = [](localized_string_id, const char*) {
        return std::u32string{U"RPCS3 message: see application log"};
    };
    cb.get_localized_setting = [](const cfg::_base* setting, u32) {
        return setting ? setting->get_name() : std::string{};
    };
    cb.get_photo_path = [](std::string_view) { unavailable("photo service"); return std::string{}; };
    cb.play_sound = [](const std::string&, std::optional<f32>) {};
    cb.get_image_info = [](const std::string&, std::string& type, s32& w, s32& h, s32& orientation) {
        type.clear(); w = h = orientation = 0; unavailable("game image metadata"); return false;
    };
    cb.get_scaled_image = [](const std::string&, s32, s32, s32& w, s32& h, u8*, bool) {
        w = h = 0; unavailable("game image scaling"); return false;
    };
    cb.resolve_path = [](std::string_view path) {
        return fs::exists(std::string{path}) ? std::string{path} : std::string{};
    };
    cb.resolve_path_may_not_exist = [](std::string_view path) { return std::string{path}; };
    cb.get_font_dirs = [] { return std::vector<std::string>{"/download0/rpcs3/dev_flash/data/font/"}; };
    cb.on_install_pkgs = [](const std::vector<std::string>&, bool) { unavailable("automatic package installation"); return false; };
    cb.add_breakpoint = [](u32) {};
    cb.display_sleep_control_supported = [] { return false; };
    cb.enable_display_sleep = [](bool) {};
    cb.check_microphone_permissions = [] { unavailable("microphone capture"); };
    cb.make_video_source = [] { unavailable("video source"); return std::unique_ptr<video_source>{}; };
    cb.enable_gamemode = [](bool) {};
    cb.get_database_config = [](const std::string&) { return std::string{}; };
}
