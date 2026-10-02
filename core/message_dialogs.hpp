// SPDX-License-Identifier: GPL-3.0-or-later
#pragma once
#include <optional>
#include <vector>
#include "Emu/Cell/Modules/sceNp.h"
#include "Emu/emu_callbacks.h"
#include <cstdio>

namespace zd {
// The upstream NP fallback dereferences these providers unconditionally.
// Preserve its dialog contract and complete unavailable operations as cancel.
class unavailable_send_dialog final : public SendMessageDialogBase {
public:
    error_code Exec(message_data&, std::set<std::string>&) override {
        std::fprintf(stderr, "RPCS3 PS5: send-message dialog unavailable; cancelled.\n");
        return CELL_CANCEL;
    }
    void callback_handler(rpcn::NotificationType, const std::string&, bool) override {
        std::fprintf(stderr, "RPCS3 PS5: send-message notification unavailable.\n");
    }
};
class unavailable_recv_dialog final : public RecvMessageDialogBase {
public:
    error_code Exec(SceNpBasicMessageMainType, SceNpBasicMessageRecvOptions,
                    SceNpBasicMessageRecvAction& action, u64& chosen) override {
        action = 0;
        chosen = 0;
        std::fprintf(stderr, "RPCS3 PS5: receive-message dialog unavailable; cancelled.\n");
        return CELL_CANCEL;
    }
    void callback_handler(const shared_ptr<std::pair<std::string, message_data>>, u64) override {
        std::fprintf(stderr, "RPCS3 PS5: receive-message notification unavailable.\n");
    }
};
inline void install_message_callbacks(emu_callbacks& cb) {
    cb.get_sendmessage_dialog = [] { return std::make_shared<unavailable_send_dialog>(); };
    cb.get_recvmessage_dialog = [] { return std::make_shared<unavailable_recv_dialog>(); };
}
}
