/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "catalog.h"
#include "fs.h"
#include <dirent.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>
#ifdef __PROSPERO__
 
extern DIR *fdopendir(int fd);
#endif
#define MAX_DEPTH 8
#define MAX_ROOTS 16
#define MAX_VISITS 32768
#define MAX_SFO 65536
typedef struct {
  DIR *dir;
  int fd;
  char path[ZD_PATH];
} frame;
struct zd_scanner {
  zd_catalog *out;
  char roots[MAX_ROOTS][ZD_PATH];
  unsigned root_count, root_next, depth, visits, done;
  int root_fd;
  frame stack[MAX_DEPTH + 1];
};
static uint16_t u16(const unsigned char *p) {
  return (uint16_t)(p[0] | (p[1] << 8));
}
static uint32_t u32(const unsigned char *p) {
  return (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) |
         ((uint32_t)p[3] << 24);
}
static uint64_t hash_bytes(uint64_t h, const void *data, size_t n) {
  const unsigned char *p = data;
  for (size_t i = 0; i < n; ++i) {
    h ^= p[i];
    h *= UINT64_C(1099511628211);
  }
  return h;
}
static int copy(char *out, size_t cap, const char *text) {
  size_t n = strlen(text);
  if (n >= cap)
    return 0;
  memcpy(out, text, n + 1);
  return 1;
}
static int join(char *out, const char *base, const char *part) {
  size_t a = strlen(base), b = strlen(part);
  if (a + b + 2 > ZD_PATH)
    return 0;
  memcpy(out, base, a);
  out[a] = '/';
  memcpy(out + a + 1, part, b + 1);
  return 1;
}
static int utf8_ok(const unsigned char *t, size_t n) {
  size_t i = 0;
  while (i < n) {
    unsigned c = t[i++], extra = 0, val = c, minimum = 0;
    if (c < 0x80) {
      if (c < 0x20 && c != '\t')
        return 0;
      continue;
    }
    if ((c & 0xe0) == 0xc0) {
      extra = 1;
      val = c & 31;
      minimum = 0x80;
    } else if ((c & 0xf0) == 0xe0) {
      extra = 2;
      val = c & 15;
      minimum = 0x800;
    } else if ((c & 0xf8) == 0xf0) {
      extra = 3;
      val = c & 7;
      minimum = 0x10000;
    } else
      return 0;
    if (extra > n - i)
      return 0;
    while (extra--) {
      unsigned k = t[i++];
      if ((k & 0xc0) != 0x80)
        return 0;
      val = (val << 6) | (k & 63);
    }
    if (val < minimum || val > 0x10ffff || (val >= 0xd800 && val <= 0xdfff))
      return 0;
  }
  return 1;
}
static int text_field(char *out, size_t cap, const unsigned char *data,
                      size_t len) {
  const unsigned char *nul = memchr(data, 0, len);
  if (!nul)
    return 0;
  size_t n = (size_t)(nul - data);
  if (!utf8_ok(data, n))
    return 0;
  if (n >= cap) {
    n = cap - 1;
    while (n && (data[n] & 0xc0) == 0x80)
      --n;
  }
  memcpy(out, data, n);
  out[n] = 0;
  return 1;
}
static int parse_sfo(zd_game *g, const unsigned char *b, size_t len) {
  if (len < 20 || memcmp(b, "\0PSF", 4) || u32(b + 4) != 0x101)
    return 0;
  uint32_t ko = u32(b + 8), vo = u32(b + 12), count = u32(b + 16);
  if (!count || count > 128 || 20u + count * 16u > len ||
      ko < 20u + count * 16u || ko >= vo || vo > len)
    return 0;
  for (uint32_t i = 0; i < count; ++i) {
    const unsigned char *e = b + 20 + i * 16;
    uint32_t key = u16(e), format = u16(e + 2), n = u32(e + 4),
             max = u32(e + 8), value = u32(e + 12);
    if (key >= vo - ko || value > len - vo || max > len - vo - value || n > max)
      return 0;
    const char *name = (const char *)b + ko + key;
    if (!memchr(name, 0, vo - ko - key))
      return 0;
    const unsigned char *data = b + vo + value;
    if (format == 0x0204 && (!n || !memchr(data, 0, n)))
      return 0;
    if (format != 0x0204)
      continue;
    if (!strcmp(name, "TITLE") &&
        !text_field(g->title, sizeof(g->title), data, n))
      return 0;
    if (!strcmp(name, "TITLE_ID") &&
        !text_field(g->title_id, sizeof(g->title_id), data, n))
      return 0;
    if (!strcmp(name, "APP_VER") &&
        !text_field(g->version, sizeof(g->version), data, n))
      return 0;
  }
  return g->title[0] && g->title_id[0];
}
 
static int describe(const char *root, const char *path, int root_fd,
                    int game_fd, zd_game *out) {
  char metadata[ZD_PATH], sfo[ZD_PATH], usrdir[ZD_PATH];
  struct stat rs, ds, bs, ss;
  if (fstat(root_fd, &rs) || fstat(game_fd, &ds))
    return 0;
  int meta_fd = zd_fs_open(game_fd, "PS3_GAME", 1, NULL);
  int owned = meta_fd >= 0;
  if (!join(metadata, path, "PS3_GAME")) {
    if (owned)
      close(meta_fd);
    return 0;
  }
  if (!owned) {
    meta_fd = game_fd;
    if (!copy(metadata, sizeof(metadata), path))
      return 0;
  }
  int sfo_fd = zd_fs_open(meta_fd, "PARAM.SFO", 0, &ss);
  if (sfo_fd < 0) {
    if (owned)
      close(meta_fd);
    return 0;
  }
  memset(out, 0, sizeof(*out));
  int result = 0;
  if (!copy(out->key, sizeof(out->key), path) ||
      !copy(out->root, sizeof(out->root), root) ||
      !join(sfo, metadata, "PARAM.SFO") || !join(usrdir, metadata, "USRDIR") ||
      !join(out->eboot, usrdir, "EBOOT.BIN") ||
      !join(out->cover, metadata, "ICON0.PNG"))
    goto cleanup;
  const char *base = strrchr(path, '/');
  base = base ? base + 1 : path;
  text_field(out->title, sizeof(out->title), (const unsigned char *)base,
             strlen(base) + 1);
  copy(out->version, sizeof(out->version), "—");
  memset(&bs, 0, sizeof(bs));
  int usr_fd = zd_fs_open(meta_fd, "USRDIR", 1, NULL);
  int boot_fd = zd_fs_open(usr_fd, "EBOOT.BIN", 0, &bs);
  out->files_ok = boot_fd >= 0 && bs.st_size > 0;
  if (boot_fd >= 0)
    close(boot_fd);
  if (usr_fd >= 0)
    close(usr_fd);
  int cover_fd = zd_fs_open(meta_fd, "ICON0.PNG", 0, NULL);
  if (cover_fd < 0)
    out->cover[0] = 0;
  else
    close(cover_fd);
  uint64_t h = UINT64_C(14695981039346656037);
  h = hash_bytes(h, path, strlen(path));
  h = hash_bytes(h, &rs.st_dev, sizeof(rs.st_dev));
  h = hash_bytes(h, &rs.st_ino, sizeof(rs.st_ino));
  h = hash_bytes(h, &ds.st_ino, sizeof(ds.st_ino));
  h = hash_bytes(h, &bs.st_ino, sizeof(bs.st_ino));
  h = hash_bytes(h, &bs.st_size, sizeof(bs.st_size));
  h = hash_bytes(h, &bs.st_mtim, sizeof(bs.st_mtim));
  if (ss.st_size >= 20 && ss.st_size <= MAX_SFO) {
    size_t n = (size_t)ss.st_size;
    unsigned char *bytes = malloc(n);
    if (bytes && zd_fs_read(sfo_fd, bytes, n) == n) {
      h = hash_bytes(h, bytes, n);
      zd_game parsed = *out;
      parsed.title[0] = parsed.title_id[0] = 0;
      out->metadata_ok = (unsigned)parse_sfo(&parsed, bytes, n);
      if (out->metadata_ok) {
        copy(out->title, sizeof(out->title), parsed.title);
        copy(out->title_id, sizeof(out->title_id), parsed.title_id);
        copy(out->version, sizeof(out->version), parsed.version);
      }
    }
    free(bytes);
  }
  out->fingerprint = h;
  result = 1;
cleanup:
  close(sfo_fd);
  if (owned)
    close(meta_fd);
  return result;
}
static int compare(const void *a, const void *b) {
  const zd_game *x = a, *y = b;
  const unsigned char *p = (const unsigned char *)x->title,
                      *q = (const unsigned char *)y->title;
  while (*p && *q) {
    unsigned l = *p++, r = *q++;
    if (l >= 'A' && l <= 'Z')
      l += 32;
    if (r >= 'A' && r <= 'Z')
      r += 32;
    if (l != r)
      return l < r ? -1 : 1;
  }
  if (*p != *q)
    return *p ? 1 : -1;
  return strcmp(x->key, y->key);
}
static int add(zd_scanner *s, const char *root, const char *path, int fd) {
  zd_game g;
  if (!describe(root, path, s->root_fd, fd, &g))
    return 0;
  for (unsigned i = 0; i < s->out->count; ++i)
    if (!strcmp(s->out->games[i].key, g.key))
      return 1;
  if (s->out->count == ZD_MAX_GAMES) {
    s->out->limited = 1;
    return 1;
  }
  s->out->games[s->out->count++] = g;
  if (!g.metadata_ok || !g.files_ok)
    ++s->out->warnings;
  return 1;
}
zd_scanner *zd_scan_begin(zd_catalog *out, const char *const *roots, size_t n) {
  if (!out || (!roots && n))
    return NULL;
  zd_scanner *s = calloc(1, sizeof(*s));
  if (!s)
    return NULL;
  memset(out, 0, sizeof(*out));
  s->out = out;
  if (n > MAX_ROOTS) {
    n = MAX_ROOTS;
    out->limited = 1;
  }
  for (size_t i = 0; i < n; ++i) {
    char normalized[ZD_PATH];
    if (!roots[i] || !copy(normalized, sizeof(normalized), roots[i]) ||
        normalized[0] != '/') {
      ++out->warnings;
      continue;
    }
    size_t len = strlen(normalized);
    while (len > 1 && normalized[len - 1] == '/')
      normalized[--len] = 0;
    if (strstr(normalized, "/../") || strstr(normalized, "/./") ||
        (len >= 3 && !strcmp(normalized + len - 3, "/.."))) {
      ++out->warnings;
      continue;
    }
    int duplicate = 0;
    for (unsigned k = 0; k < s->root_count; ++k)
      if (!strcmp(s->roots[k], normalized))
        duplicate = 1;
    if (!duplicate)
      copy(s->roots[s->root_count++], ZD_PATH, normalized);
  }
  return s;
}
int zd_scan_step(zd_scanner *s, unsigned budget) {
  if (!s)
    return -1;
  if (s->done)
    return 1;
  if (!budget)
    budget = 1;
  while (budget--) {
    if (s->visits++ >= MAX_VISITS) {
      s->out->limited = 1;
      s->done = 1;
      break;
    }
    if (!s->depth) {
      if (s->root_next == s->root_count) {
        s->done = 1;
        break;
      }
      const char *root = s->roots[s->root_next++];
      int fd = zd_fs_root(root);
      if (fd < 0)
        continue;
      s->root_fd = fd;
      ++s->out->mounts;
      if (add(s, root, root, fd)) {
        close(fd);
        continue;
      }
      DIR *dir = fdopendir(fd);
      if (!dir) {
        close(fd);
        ++s->out->warnings;
        continue;
      }
      s->stack[0].fd = fd;
      copy(s->stack[0].path, ZD_PATH, root);
      s->stack[0].dir = dir;
      s->depth = 1;
      continue;
    }
    frame *f = &s->stack[s->depth - 1];
    struct dirent *entry = readdir(f->dir);
    if (!entry) {
      closedir(f->dir);
      f->dir = NULL;
      --s->depth;
      continue;
    }
    if (entry->d_name[0] == '.' || !strcmp(entry->d_name, "PS3_UPDATE") ||
        !strcmp(entry->d_name, "System Volume Information"))
      continue;
    char child[ZD_PATH];
    if (!join(child, f->path, entry->d_name)) {
      ++s->out->warnings;
      continue;
    }
    int fd = zd_fs_open(f->fd, entry->d_name, 1, NULL);
    if (fd < 0)
      continue;
    if (add(s, s->roots[s->root_next - 1], child, fd)) {
      close(fd);
      continue;
    }
    if (s->depth == MAX_DEPTH) {
      close(fd);
      s->out->limited = 1;
      continue;
    }
    DIR *dir = fdopendir(fd);
    if (!dir) {
      close(fd);
      ++s->out->warnings;
      continue;
    }
    copy(s->stack[s->depth].path, ZD_PATH, child);
    s->stack[s->depth].fd = fd;
    s->stack[s->depth++].dir = dir;
  }
  if (s->done) {
    qsort(s->out->games, s->out->count, sizeof(zd_game), compare);
    uint64_t h = UINT64_C(14695981039346656037);
    for (unsigned i = 0; i < s->out->count; ++i)
      h = hash_bytes(h, &s->out->games[i].fingerprint, sizeof(uint64_t));
    s->out->generation = h;
  }
  return s->done ? 1 : 0;
}
void zd_scan_end(zd_scanner *s) {
  if (!s)
    return;
  for (unsigned i = 0; i < s->depth; ++i)
    if (s->stack[i].dir)
      closedir(s->stack[i].dir);
  free(s);
}
int zd_catalog_scan(zd_catalog *out, const char *const *roots, size_t n) {
  zd_scanner *s = zd_scan_begin(out, roots, n);
  if (!s)
    return -1;
  while (!zd_scan_step(s, 256)) {
  }
  zd_scan_end(s);
  return 0;
}
int zd_game_revalidate(const zd_game *g) {
  if (!g)
    return 0;
  int root_fd = zd_fs_root(g->root);
  if (root_fd < 0)
    return 0;
  int game_fd = zd_fs_beneath(root_fd, g->root, g->key, 1, NULL);
  if (game_fd < 0) {
    close(root_fd);
    return 0;
  }
  zd_game current;
  int valid = describe(g->root, g->key, root_fd, game_fd, &current) &&
              current.metadata_ok && current.files_ok &&
              current.fingerprint == g->fingerprint;
  close(game_fd);
  close(root_fd);
  return valid;
}
