#ifndef ZD_FS_H
#define ZD_FS_H
#include <stddef.h>
#include <sys/stat.h>
int zd_fs_root(const char *path);
int zd_fs_open(int parent, const char *name, int directory, struct stat *info);
int zd_fs_path(const char *root, const char *path, int directory,
               struct stat *info);
int zd_fs_beneath(int root_fd, const char *root, const char *path,
                  int directory, struct stat *info);
size_t zd_fs_read(int fd, void *buffer, size_t bytes);
#endif
