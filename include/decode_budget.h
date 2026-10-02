#ifndef ZD_DECODE_BUDGET_H
#define ZD_DECODE_BUDGET_H
#include <stddef.h>
#define ZD_DECODE_LIMIT (32u * 1024u * 1024u)
int zd_decode_begin(size_t limit);
void *zd_decode_malloc(size_t bytes);
void *zd_decode_realloc(void *address, size_t bytes);
void zd_decode_free(void *address);
size_t zd_decode_live(void);
size_t zd_decode_peak(void);
#endif
