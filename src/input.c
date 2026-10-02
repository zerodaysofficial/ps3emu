/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "ui.h"
/* Layout and interception semantics checked against SharpProspero GamePad.cs
 * revision 5dfdb4b0b166e83dc9ae275001afb695f12c7174. The service writes into a
 * 1024-byte buffer; the documented sample itself is 120 bytes. */
zd_pad zd_pad_decode(const unsigned char *b, size_t n) {
  zd_pad p = {0, 0, 128, 128};
  if (!b || n < 120 || !b[76])
    return p;
  uint32_t buttons = (uint32_t)b[0] | ((uint32_t)b[1] << 8) |
                     ((uint32_t)b[2] << 16) | ((uint32_t)b[3] << 24);
  if (buttons & UINT32_C(0x80000000))
    return p;
  p.buttons = buttons;
  p.connected = 1;
  p.lx = b[4];
  p.ly = b[5];
  return p;
}
