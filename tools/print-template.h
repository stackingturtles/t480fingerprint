/* Copyright (c) 2026 Stacking Turtles Ltd. SPDX-License-Identifier: MIT */
#ifndef T480_PRINT_TEMPLATE_H
#define T480_PRINT_TEMPLATE_H
#include <fprint.h>
/* enroll_sync consumes a floating reference. Hold our own strong reference so
 * g_autoptr cleanup cannot invalidate the returned enrolled-print reference. */
static inline FpPrint *owned_template(FpDevice *device) {
  return g_object_ref_sink(fp_print_new(device));
}
#endif
