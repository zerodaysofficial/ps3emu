#ifndef ZD_UI_H
#define ZD_UI_H
#include "catalog.h"
typedef struct {
  char selected[ZD_PATH];
  uint64_t fingerprint;
  unsigned initialized, present, page;
} zd_ui;
typedef struct {
  char key[ZD_PATH];
  uint64_t fingerprint;
  unsigned valid;
} zd_intent;
typedef struct {
  uint32_t buttons;
  unsigned connected;
  unsigned char lx, ly;
} zd_pad;
enum {
  ZD_LEFT = 1,
  ZD_RIGHT = 2,
  ZD_UP = 3,
  ZD_DOWN = 4,
  ZD_NEXT = 5,
  ZD_PREV = 6
};
void zd_ui_refresh(zd_ui *ui, const zd_catalog *catalog);
int zd_ui_index(const zd_ui *ui, const zd_catalog *catalog);
void zd_ui_move(zd_ui *ui, const zd_catalog *catalog, int direction);
int zd_ui_pick(zd_ui *ui, const zd_catalog *catalog, float x, float y);
zd_intent zd_ui_capture(const zd_ui *ui, const zd_catalog *catalog);
int zd_ui_validate(const zd_intent *intent, const zd_catalog *catalog);
zd_pad zd_pad_decode(const unsigned char *bytes, size_t count);
int zd_render_init(const char *font_file);
void zd_render_shutdown(void);
int zd_render(uint32_t *pixels, unsigned width, unsigned height,
              const zd_ui *ui, const zd_catalog *catalog, int scanning,
              int sample_data, const char *notice);
#endif
