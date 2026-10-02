# SPDX-License-Identifier: GPL-3.0-or-later
# The upstream finder assumes it is below RPCS3's desktop source root.
# This parent uses the same real dependency at its explicit source path.
if(NOT TARGET wolfssl)
  message(FATAL_ERROR "The source-built wolfssl target must already exist")
endif()
set(WOLFSSL_LIBRARY wolfssl)
set(WOLFSSL_INCLUDE_DIR "${RPCS3_ROOT}/3rdparty/wolfssl/wolfssl")
set(WOLFSSL_INCLUDE_DIRS "${WOLFSSL_INCLUDE_DIR};${CMAKE_BINARY_DIR}/third_party/wolfssl/wolfssl")
set(WOLFSSL_FOUND TRUE)
