// SPDX-License-Identifier: GPL-3.0-or-later
#pragma once
#include <deque>
#include <functional>
#include <mutex>
#include <stdexcept>
#include <thread>
#include <utility>

namespace zd {
class main_queue {
    std::mutex mutex_;
    std::deque<std::function<void()>> pending_;
    std::thread::id owner_;
    std::size_t limit_;
    bool open_ = false;
public:
    explicit main_queue(std::size_t limit = 256) : limit_(limit) {}
    void bind_owner() {
        std::lock_guard lock(mutex_);
        if (!pending_.empty())
            throw std::logic_error("RPCS3 callback queue still has pending work");
        owner_ = std::this_thread::get_id();
        open_ = true;
    }
    bool post(std::function<void()> fn) {
        if (!fn) return false;
        {
            std::lock_guard lock(mutex_);
            if (!open_) return false;
            if (std::this_thread::get_id() != owner_) {
                if (pending_.size() >= limit_) return false;
                pending_.push_back(std::move(fn));
                return true;
            }
        }
        fn();
        return true;
    }
    std::size_t drain() {
        std::size_t budget;
        {
            std::lock_guard lock(mutex_);
            if (std::this_thread::get_id() != owner_)
                throw std::logic_error("RPCS3 callbacks require their owner thread");
            budget = pending_.size();
        }
        std::size_t count = 0;
        while (count < budget) {
            std::function<void()> fn;
            {
                std::lock_guard lock(mutex_);
                // A lifecycle callback may recursively pump this queue and
                // consume the work counted by the outer drain's budget.
                if (pending_.empty()) break;
                fn = std::move(pending_.front());
                pending_.pop_front();
            }
            // If this throws, later callbacks remain queued, including any
            // workers waiting for their completion notification.
            fn();
            ++count;
        }
        return count;
    }
    void close() {
        std::lock_guard lock(mutex_);
        open_ = false;
    }
};
}
