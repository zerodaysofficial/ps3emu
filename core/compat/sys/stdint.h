/* SPDX-License-Identifier: GPL-3.0-or-later */
/* OPSDK's sys/stdint shim predefines the include guard of the real stdint
 * header and thereby skips all typedefs when inttypes.h is included first. */
#pragma once
#include <stdint.h>
