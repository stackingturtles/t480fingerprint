/* Copyright (c) 2026 Stacking Turtles Ltd. SPDX-License-Identifier: MIT */
#include <stdio.h>
#include <string.h>
#include <fprint.h>

/* Enumerate only. In this pinned driver, probe resets the USB connection and
 * reads GET_VERSION. Do not add fp_device_open here: that enters pairing and
 * may write/erase sensor flash. Never print device IDs (they contain serials). */
int main(int argc, char **argv)
{
  if (argc == 2 && strcmp(argv[1], "--help") == 0) {
    puts("t480-probe: enumerate the native Validity driver without opening the sensor.\n"
         "Performs a USB connection reset and GET_VERSION query. No enrollment or flash writes.");
    return 0;
  }
  if (argc != 1) {
    fputs("Usage: t480-probe [--help]\n", stderr);
    return 2;
  }
  g_unsetenv("G_MESSAGES_DEBUG");
  g_unsetenv("FP_DEVICE_EMULATION");
  g_setenv("FP_DRIVERS_ALLOWLIST", "validity", TRUE);
  g_autoptr(FpContext) context = fp_context_new();
  fp_context_enumerate(context);
  GPtrArray *devices = fp_context_get_devices(context);
  unsigned found = 0;
  for (unsigned i = 0; i < devices->len; i++) {
    FpDevice *device = g_ptr_array_index(devices, i);
    if (strcmp(fp_device_get_driver(device), "validity") == 0) {
      found++;
      puts("PASS: native Validity driver detected a reader.");
      printf("Enrollment stages: %d; verification API: %s\n",
             fp_device_get_nr_enroll_stages(device),
             fp_device_has_feature(device, FP_DEVICE_FEATURE_VERIFY) ? "yes" : "no");
    }
  }
  if (!found) {
    fputs("FAIL: no Validity reader detected. Check USB presence, permissions and competing services.\n", stderr);
    return 1;
  }
  puts("Detection only: opening, enrollment and fingerprint matching remain untested.");
  return 0;
}
