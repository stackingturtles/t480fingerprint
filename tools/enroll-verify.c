/* Copyright (c) 2026 Stacking Turtles Ltd. SPDX-License-Identifier: MIT */
#include <stdio.h>
#include <string.h>
#include <signal.h>
#include <glib-unix.h>
#include <fprint.h>
#include "workflow.h"
#include "print-template.h"

typedef struct {
  FpDevice *device;
  FpPrint *print;
  GCancellable *cancel;
  gboolean timed_out;
} Session;
static gboolean cancel_signal(void *data) {
  g_cancellable_cancel(((Session *)data)->cancel);
  return G_SOURCE_CONTINUE;
}
static gboolean cancel_timeout(void *data) {
  Session *s = data;
  s->timed_out = TRUE;
  g_cancellable_cancel(s->cancel);
  return G_SOURCE_CONTINUE;
}
static int error_result(Session *s, const char *stage, GError *error) {
  if (s->timed_out) fprintf(stderr, "%s: timed out.\n", stage);
  else if (g_cancellable_is_cancelled(s->cancel)) fprintf(stderr, "%s: cancelled.\n", stage);
  else fprintf(stderr, "%s: %s\n", stage, error ? error->message : "device operation failed");
  return g_cancellable_is_cancelled(s->cancel) && !s->timed_out ? 130 : 2;
}
static void progress(FpDevice *device, gint count, FpPrint *print,
                     gpointer data, GError *error) {
  (void)print; (void)data;
  if (error) puts("Scan not accepted. Lift your finger and try again.");
  else printf("Prepare: %d/%d scans accepted. Lift and reposition your finger.\n",
              count, fp_device_get_nr_enroll_stages(device));
}
static int prepare(void *data) {
  Session *s = data;
  g_autoptr(GError) error = NULL;
  g_autoptr(FpPrint) template = owned_template(s->device);
  g_autofree gchar *tag = g_uuid_string_random();
  fp_print_set_username(template, tag); /* Distinct test record, never overwrite a user. */
  fp_print_set_finger(template, FP_FINGER_RIGHT_INDEX);
  puts("\nPREPARE: repeatedly touch and lift your right index finger (up to 120 seconds).");
  guint timeout = g_timeout_add_seconds(120, cancel_timeout, s);
  s->print = fp_device_enroll_sync(s->device, template, s->cancel, progress, s, &error);
  g_source_remove(timeout);
  if (!s->print) return error_result(s, "Prepare failed", error);
  puts("PREPARE SUCCEEDED: temporary fingerprint enrolled.");
  return 0;
}
static int verify(void *data) {
  Session *s = data;
  g_autoptr(GError) error = NULL;
  gboolean matched = FALSE;
  puts("\nVERIFY: lift your finger, then touch the reader again (up to 30 seconds).\n"
       "Use the enrolled finger for SUCCESS, or another finger to test a non-match.");
  /* Allow a clear stage boundary without reading piped input or consuming a scan. */
  guint timeout = g_timeout_add_seconds(30, cancel_timeout, s);
  gboolean ok = fp_device_verify_sync(s->device, s->print, s->cancel,
                                       NULL, NULL, &matched, NULL, &error);
  g_source_remove(timeout);
  if (!ok) return error_result(s, "Verify failed", error);
  puts(matched ? "VERIFY SUCCEEDED: fingerprint matched." : "VERIFY FAILED: fingerprint did not match.");
  return matched ? 0 : 1;
}
static int cleanup(void *data) {
  Session *s = data;
  g_autoptr(GError) error = NULL;
  /* Cancellation must not skip cleanup of the completed temporary enrollment. */
  g_clear_object(&s->cancel);
  s->cancel = g_cancellable_new();
  s->timed_out = FALSE;
  guint timeout = g_timeout_add_seconds(30, cancel_timeout, s);
  gboolean ok = fp_device_delete_print_sync(s->device, s->print, s->cancel, &error);
  g_source_remove(timeout);
  if (!ok) {
    error_result(s, "Cleanup failed; temporary fingerprint may remain on the reader", error);
    return 3;
  }
  puts("Cleanup succeeded: removed this test's temporary fingerprint.");
  return 0;
}
int main(int argc, char **argv) {
  if (argc == 2 && strcmp(argv[1], "--help") == 0) {
    puts("Usage: t480-enroll-verify [--check]\n"
         "Default: temporary right-index enrollment, fresh verification, cleanup.\n"
         "--check: open/close the guarded driver without enrolling.\n"
         "Exit: 0 success, 1 non-match, 2 error, 3 cleanup failure, 130 cancelled.\n"
         "No PAM configuration, template files, firmware upload or sensor factory reset.");
    return 0;
  }
  gboolean check = argc == 2 && strcmp(argv[1], "--check") == 0;
  if (argc != 1 && !check) { fputs("Invalid arguments; use --help.\n", stderr); return 2; }
  setvbuf(stdout, NULL, _IONBF, 0);
  g_unsetenv("G_MESSAGES_DEBUG");
  g_unsetenv("FP_DEVICE_EMULATION");
  g_setenv("FP_DRIVERS_ALLOWLIST", "validity", TRUE);
  g_autoptr(FpContext) context = fp_context_new();
  fp_context_enumerate(context);
  GPtrArray *devices = fp_context_get_devices(context);
  if (devices->len != 1) { fputs("ERROR: expected exactly one accessible Validity reader.\n", stderr); return 2; }
  Session s = {.device = g_ptr_array_index(devices, 0), .cancel = g_cancellable_new()};
  guint interrupt = g_unix_signal_add(SIGINT, cancel_signal, &s);
  guint terminate = g_unix_signal_add(SIGTERM, cancel_signal, &s);
  guint timeout = g_timeout_add_seconds(60, cancel_timeout, &s);
  g_autoptr(GError) error = NULL;
  puts("Opening reader with automatic reset, re-pairing and firmware upload disabled…");
  gboolean opened = fp_device_open_sync(s.device, s.cancel, &error);
  g_source_remove(timeout);
  int result;
  if (!opened) result = error_result(&s, "Reader setup failed", error);
  else {
    if (check) { puts("CHECK SUCCEEDED: reader opened; no fingerprint enrolled."); result = 0; }
    else {
      TestSteps steps = {&s, prepare, verify, cleanup};
      result = run_test(&steps);
    }
    g_clear_error(&error);
    g_cancellable_reset(s.cancel);
    timeout = g_timeout_add_seconds(15, cancel_timeout, &s);
    if (!fp_device_close_sync(s.device, s.cancel, &error)) {
      error_result(&s, "Reader close failed", error);
      if (!result) result = 2;
    }
    g_source_remove(timeout);
  }
  g_source_remove(interrupt); g_source_remove(terminate);
  g_clear_object(&s.print); g_clear_object(&s.cancel);
  puts(result == 0 ? "RESULT: SUCCESS" : result == 1 ? "RESULT: FAIL (no match)" : "RESULT: ERROR (test incomplete)");
  return result;
}
