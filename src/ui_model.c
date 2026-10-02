/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "ui.h"
#include <string.h>
static void select_at(zd_ui *u, const zd_catalog *c, unsigned at) {
  if (at >= c->count)
    return;
  memcpy(u->selected, c->games[at].key, ZD_PATH);
  u->fingerprint = c->games[at].fingerprint;
  u->initialized = u->present = 1;
  u->page = at / 6;
}
int zd_ui_index(const zd_ui *u, const zd_catalog *c) {
  if (!u || !c || !u->selected[0])
    return -1;
  for (unsigned i = 0; i < c->count; ++i)
    if (!strcmp(u->selected, c->games[i].key) &&
        u->fingerprint == c->games[i].fingerprint)
      return (int)i;
  return -1;
}
void zd_ui_refresh(zd_ui *u, const zd_catalog *c) {
  if (!u || !c)
    return;
  if (!u->initialized && c->count) {
    select_at(u, c, 0);
    return;
  }
  int at = zd_ui_index(u, c);
  u->present = at >= 0;
  if (at >= 0) {
    u->page = (unsigned)at / 6;
  } else if (!c->count)
    u->page = 0;
  else if (u->page > (c->count - 1) / 6)
    u->page = (c->count - 1) / 6;
}
void zd_ui_move(zd_ui *u, const zd_catalog *c, int direction) {
  if (!u || !c || !c->count)
    return;
  int at = zd_ui_index(u, c);
  if (at < 0) {
    unsigned first = u->page * 6;
    select_at(u, c, first < c->count ? first : 0);
    return;
  }
  int next = at;
  switch (direction) {
  case ZD_LEFT:
    --next;
    break;
  case ZD_RIGHT:
    ++next;
    break;
  case ZD_UP:
    next -= 3;
    break;
  case ZD_DOWN:
    next += 3;
    break;
  case ZD_NEXT:
    if ((unsigned)at / 6 < (c->count - 1) / 6)
      next = at + 6;
    break;
  case ZD_PREV:
    if (at >= 6)
      next = at - 6;
    break;
  default:
    return;
  }
  if (next < 0)
    next = 0;
  if ((unsigned)next >= c->count)
    next = (int)c->count - 1;
  select_at(u, c, (unsigned)next);
}
int zd_ui_pick(zd_ui *u, const zd_catalog *c, float x, float y) {
  if (!u || !c)
    return 0;
  if (y >= 166 && y <= 202) {
    if (x >= 858 && x <= 898) {
      zd_ui_move(u, c, ZD_NEXT);
      return 1;
    }
    if (x >= 810 && x <= 850) {
      zd_ui_move(u, c, ZD_PREV);
      return 1;
    }
  }
  for (unsigned i = 0; i < 6; ++i) {
    float left = 80 + (i % 3) * 272, top = 214 + (i / 3) * 220;
    unsigned at = u->page * 6 + i;
    if (at >= c->count)
      break;
    if (x >= left && x < left + 256 && y >= top && y < top + 200) {
      select_at(u, c, at);
      return 1;
    }
  }
  return 0;
}
zd_intent zd_ui_capture(const zd_ui *u, const zd_catalog *c) {
  zd_intent intent;
  memset(&intent, 0, sizeof(intent));
  int at = zd_ui_index(u, c);
  if (at >= 0 && u->present && u->fingerprint == c->games[at].fingerprint &&
      c->games[at].metadata_ok && c->games[at].files_ok) {
    memcpy(intent.key, c->games[at].key, ZD_PATH);
    intent.fingerprint = c->games[at].fingerprint;
    intent.valid = 1;
  }
  return intent;
}
int zd_ui_validate(const zd_intent *intent, const zd_catalog *c) {
  if (!intent || !c || !intent->valid)
    return 0;
  for (unsigned i = 0; i < c->count; ++i)
    if (!strcmp(intent->key, c->games[i].key))
      return c->games[i].fingerprint == intent->fingerprint &&
             c->games[i].metadata_ok && c->games[i].files_ok;
  return 0;
}
