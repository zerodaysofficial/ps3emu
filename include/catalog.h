#ifndef ZD_CATALOG_H
#define ZD_CATALOG_H
#include <stddef.h>
#include <stdint.h>
#define ZD_MAX_GAMES 1024
#define ZD_PATH 1024
#define ZD_TITLE 256
typedef struct {
  char key[ZD_PATH], title[ZD_TITLE], title_id[20], version[20];
  char root[ZD_PATH], eboot[ZD_PATH], cover[ZD_PATH];
  uint64_t fingerprint;
  unsigned metadata_ok, files_ok;
} zd_game;
typedef struct {
  zd_game games[ZD_MAX_GAMES];
  unsigned count, mounts, warnings, limited;
  uint64_t generation;
} zd_catalog;
typedef struct zd_scanner zd_scanner;
zd_scanner *zd_scan_begin(zd_catalog *out, const char *const *roots,
                          size_t count);
int zd_scan_step(zd_scanner *scanner, unsigned budget);
void zd_scan_end(zd_scanner *scanner);
int zd_catalog_scan(zd_catalog *out, const char *const *roots, size_t count);
int zd_game_revalidate(const zd_game *game);
#endif
