/* SPDX-License-Identifier: GPL-3.0-or-later */
/* Renderer is serialized by the platform loop / host preview lock. The budget
 * counts allocation headers and the temporary old+new buffers during growth. */
#include "decode_budget.h"
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
typedef union {
  struct {
    size_t bytes;
  } value;
  max_align_t alignment;
} allocation;
static size_t budget, live, peak;
int zd_decode_begin(size_t limit) {
  if (live)
    return 0;
  budget = limit;
  peak = 0;
  return 1;
}
void *zd_decode_malloc(size_t bytes) {
  if (bytes > SIZE_MAX - sizeof(allocation))
    return NULL;
  size_t total = bytes + sizeof(allocation);
  if (live > budget || total > budget - live)
    return NULL;
  allocation *a = malloc(total);
  if (!a)
    return NULL;
  a->value.bytes = total;
  live += total;
  if (live > peak)
    peak = live;
  return a + 1;
}
void zd_decode_free(void *address) {
  if (!address)
    return;
  allocation *a = (allocation *)address - 1;
  live -= a->value.bytes;
  free(a);
}
void *zd_decode_realloc(void *address, size_t bytes) {
  if (!address)
    return zd_decode_malloc(bytes);
  if (!bytes) {
    zd_decode_free(address);
    return NULL;
  }
  allocation *a = (allocation *)address - 1;
  void *result = zd_decode_malloc(bytes);
  if (!result)
    return NULL;
  size_t old = a->value.bytes - sizeof(allocation);
  memcpy(result, address, old < bytes ? old : bytes);
  zd_decode_free(address);
  return result;
}
size_t zd_decode_live(void) { return live; }
size_t zd_decode_peak(void) { return peak; }
