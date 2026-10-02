/* SPDX-License-Identifier: GPL-3.0-or-later */
/* Optional Mesa facilities unavailable to this native application.
 * No disk shader cache or assembler subprocess is enabled by the frontend.
 * Fail explicitly; never impersonate an implemented OS operation. */
#include <errno.h>
#include <stdio.h>
#ifndef ENOTTY
/* FreeBSD/PS5 ABI: OPSDK's minimal errno header omits this constant. */
#define ENOTTY 25
#endif
/* Mesa's trivial context TLS has no dynamic initializer. This definition
 * matches ps5-opengl/native-app/runtime_shims.c; OPSDK owns emulated TLS. */
void zd_mesa_tls_init(void) __asm__("_ZTH23_mesa_glapi_tls_Context");
void zd_mesa_tls_init(void) {}

int mkstemp(char *template_name) {
  (void)template_name;
  errno = ENOSYS;
  return -1;
}
int mkstemps(char *template_name, int suffix_length) {
  (void)template_name;
  (void)suffix_length;
  errno = ENOSYS;
  return -1;
}
int isatty(int fd) {
  (void)fd;
  errno = ENOTTY;
  return 0;
}
void openlog(const char *identifier, int option, int facility) {
  (void)identifier;
  (void)option;
  (void)facility;
}
FILE *popen(const char *command, const char *mode) {
  (void)command;
  (void)mode;
  errno = ENOSYS;
  return NULL;
}
int pclose(FILE *stream) {
  (void)stream;
  errno = ENOSYS;
  return -1;
}
