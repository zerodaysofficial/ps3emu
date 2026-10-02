# SPDX-License-Identifier: GPL-3.0-or-later
# The library itself only needs these two original C files. Keep the GPL
# command-line programs and desktop gnulib utility probes out of this target.
set(ZD_ICONV_SOURCE "${ZD_EXTRA_DEPS}/libiconv-1.18")
set(ZD_ICONV_HEADERS "${CMAKE_BINARY_DIR}/iconv-headers")
file(MAKE_DIRECTORY "${ZD_ICONV_HEADERS}")
set(DLL_VARIABLE "")
set(ICONV_CONST "")
set(EILSEQ 86)
set(USE_MBSTATE_T 1)
set(BROKEN_WCHAR_H 0)
set(HAVE_VISIBILITY 1)
configure_file("${ZD_ICONV_SOURCE}/include/iconv.h.in" "${ZD_ICONV_HEADERS}/iconv.h" @ONLY)
configure_file("${ZD_ICONV_SOURCE}/libcharset/include/localcharset.h.in" "${ZD_ICONV_HEADERS}/localcharset.h" @ONLY)
# mbrtowc/wcrtomb/setlocale are declared and exported by this SDK. The final
# application link still validates every retained reference. nl_langinfo is
# not exported: libcharset uses its genuine environment fallback instead.
file(WRITE "${ZD_ICONV_HEADERS}/config.h" "#define ENABLE_EXTRA 1\n#define ENABLE_RELOCATABLE 0\n#define ICONV_CONST\n#define HAVE_MBRTOWC 1\n#define HAVE_WCRTOMB 1\n#define HAVE_SETLOCALE 1\n#define HAVE_LANGINFO_CODESET 0\n#define HAVE_STDDEF_H 1\n#define HAVE_STDLIB_H 1\n#define HAVE_STRING_H 1\n#define HAVE_VISIBILITY 1\n#define WORDS_LITTLEENDIAN 1\n#define INSTALLPREFIX \"/app0\"\n")
add_library(zd_iconv STATIC "${ZD_ICONV_SOURCE}/lib/iconv.c" "${ZD_ICONV_SOURCE}/libcharset/lib/localcharset.c")
target_include_directories(zd_iconv PRIVATE "${ZD_ICONV_HEADERS}" "${ZD_ICONV_SOURCE}/lib" "${ZD_ICONV_SOURCE}/libcharset/include")
