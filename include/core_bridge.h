/* SPDX-License-Identifier: GPL-3.0-or-later */
#ifndef ZD_CORE_BRIDGE_H
#define ZD_CORE_BRIDGE_H
#include <stddef.h>
#ifdef __cplusplus
extern "C" {
#endif
/* Owner thread only. Messages are always terminated when capacity > 0. */
int zd_core_initialize(char *message, size_t capacity);
int zd_core_boot(const char *eboot, const char *title_id,
                 char *message, size_t capacity);
void zd_core_poll(void);
void zd_core_shutdown(void);
#ifdef __cplusplus
}
#endif
#endif
