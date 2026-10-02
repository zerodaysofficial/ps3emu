// SPDX-License-Identifier: GPL-3.0-or-later
#pragma once
#include <string_view>
namespace zd {
inline bool valid_launch(std::string_view path, std::string_view title) {
    constexpr std::string_view prefix = "/mnt/usb";
    if (path.size() >= 1024 || !path.starts_with(prefix) ||
        path.size() < prefix.size() + 3 || path[8] < '0' || path[8] > '7' ||
        path[9] != '/' || !path.ends_with("/EBOOT.BIN")) return false;
    for (unsigned char ch : path)
        if (ch < 32 || ch == 127) return false;
    std::size_t offset = 1;
    while (offset < path.size()) {
        auto end = path.find('/', offset);
        if (end == path.npos) end = path.size();
        const auto part = path.substr(offset, end - offset);
        if (part.empty() || part == "." || part == "..") return false;
        offset = end + 1;
    }
    if (!title.empty() && title.size() != 9) return false;
    for (unsigned char ch : title)
        if (!(ch >= 'A' && ch <= 'Z') && !(ch >= '0' && ch <= '9')) return false;
    return true;
}
}
