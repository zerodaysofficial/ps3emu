/* SPDX-License-Identifier: GPL-3.0-or-later */
/* All content access is anchored to open directory descriptors. A component
 * can never become a followed symlink between inspection and open. */
#include "fs.h"
#include "catalog.h"
#include <errno.h>
#include <fcntl.h>
#include <string.h>
#include <unistd.h>
#ifdef __PROSPERO__
/* Public FreeBSD 9 definitions from OPSDK's bundled target/cxx headers.
 * OPSDK imports syscall from the application's libkernel. If openat is
 * unavailable, return its error; never fall back to a path-based open. */
#ifndef O_DIRECTORY
#define O_DIRECTORY 0x00020000
#endif
static int open_relative(int fd, const char *name, int flags) {
  return (int)syscall(499, fd, name, flags, 0); /* SYS_openat */
}
#else
static int open_relative(int fd, const char *name, int flags) {
  return openat(fd, name, flags, 0);
}
#endif
static int checked(int fd, int directory, struct stat *info) {
  struct stat local;
  if (!info)
    info = &local;
  if (fd < 0)
    return -1;
  if (fstat(fd, info) ||
      !(directory ? S_ISDIR(info->st_mode) : S_ISREG(info->st_mode))) {
    close(fd);
    return -1;
  }
  return fd;
}
int zd_fs_open(int parent, const char *name, int directory, struct stat *info) {
  if (parent < 0 || !name || !name[0] || strchr(name, '/') ||
      !strcmp(name, ".") || !strcmp(name, ".."))
    return -1;
  int flags = O_RDONLY | O_NOFOLLOW | O_CLOEXEC | O_NONBLOCK;
  if (directory)
    flags |= O_DIRECTORY;
  return checked(open_relative(parent, name, flags), directory, info);
}
static int walk(int fd, const char *relative, int directory,
                struct stat *info) {
  if (!relative[0])
    return checked(fd, directory, info);
  const char *p = relative;
  while (*p) {
    const char *end = strchr(p, '/');
    size_t n = end ? (size_t)(end - p) : strlen(p);
    if (!n || n >= ZD_PATH) {
      close(fd);
      return -1;
    }
    char component[ZD_PATH];
    memcpy(component, p, n);
    component[n] = 0;
    int next =
        zd_fs_open(fd, component, end ? 1 : directory, end ? NULL : info);
    close(fd);
    if (next < 0)
      return -1;
    fd = next;
    if (!end)
      return fd;
    p = end + 1;
  }
  close(fd);
  return -1;
}
int zd_fs_root(const char *path) {
  if (!path || path[0] != '/' || strlen(path) >= ZD_PATH)
    return -1;
  int fd = checked(open("/", O_RDONLY | O_NOFOLLOW | O_DIRECTORY | O_CLOEXEC),
                   1, NULL);
  return fd < 0 ? -1 : walk(fd, path + 1, 1, NULL);
}
int zd_fs_beneath(int root_fd, const char *root, const char *path,
                  int directory, struct stat *info) {
  if (!root || !path || strlen(root) >= ZD_PATH || strlen(path) >= ZD_PATH)
    return -1;
  size_t n = strlen(root);
  if (!n || strncmp(root, path, n) || (n != 1 && path[n] && path[n] != '/'))
    return -1;
  int fd =
      checked(open_relative(root_fd, ".",
                            O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC),
              1, NULL);
  if (fd < 0)
    return -1;
  const char *relative = path + n;
  if (*relative == '/')
    ++relative;
  return walk(fd, relative, directory, info);
}
int zd_fs_path(const char *root, const char *path, int directory,
               struct stat *info) {
  int fd = zd_fs_root(root);
  if (fd < 0)
    return -1;
  int result = zd_fs_beneath(fd, root, path, directory, info);
  close(fd);
  return result;
}
size_t zd_fs_read(int fd, void *buffer, size_t bytes) {
  size_t done = 0;
  while (done < bytes) {
    ssize_t n = read(fd, (char *)buffer + done, bytes - done);
    if (n < 0 && errno == EINTR)
      continue;
    if (n <= 0)
      break;
    done += (size_t)n;
  }
  return done;
}
