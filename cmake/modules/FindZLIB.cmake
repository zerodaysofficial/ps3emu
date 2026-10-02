# SPDX-License-Identifier: GPL-3.0-or-later
if(NOT TARGET zlibstatic)
  message(FATAL_ERROR "The source-built zlib target must already exist")
endif()
if(NOT TARGET ZLIB::ZLIB)
  add_library(ZLIB::ZLIB STATIC IMPORTED GLOBAL)
  set_target_properties(ZLIB::ZLIB PROPERTIES
    IMPORTED_LOCATION "${CMAKE_BINARY_DIR}/third_party/zlib/zlib/libz.a"
    INTERFACE_INCLUDE_DIRECTORIES "${RPCS3_ROOT}/3rdparty/zlib/zlib;${CMAKE_BINARY_DIR}/third_party/zlib/zlib")
endif()
set(ZLIB_FOUND TRUE)
set(ZLIB_LIBRARIES ZLIB::ZLIB)
set(ZLIB_INCLUDE_DIRS "${RPCS3_ROOT}/3rdparty/zlib/zlib;${CMAKE_BINARY_DIR}/third_party/zlib/zlib")
