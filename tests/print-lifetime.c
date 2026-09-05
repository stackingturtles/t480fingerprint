#include <glib/gstdio.h>
#include "print-template.h"
/* Reproduce the documented libfprint ownership transfers using an actual
 * FpPrint and virtual device, without USB access or biometric capture. */
static FpPrint *prepare_return(FpDevice *device, gboolean fixed, gpointer *weak) {
  g_autoptr(FpPrint) template = fixed ? owned_template(device) : fp_print_new(device);
  *weak = template;
  g_object_add_weak_pointer(G_OBJECT(template), weak);
  FpPrint *task_print = g_object_ref_sink(template); /* enroll takes template */
  FpPrint *result = g_object_ref(task_print); /* driver returns enrolled object */
  g_object_unref(task_print); /* completed task releases its input */
  return result; /* automatic local cleanup runs here */
}
int main(void) {
  g_autofree gchar *dir = g_dir_make_tmp("t480-lifetime-XXXXXX", NULL);
  g_autofree gchar *socket = g_build_filename(dir, "sensor.sock", NULL);
  g_setenv("FP_DRIVERS_ALLOWLIST", "virtual_device", TRUE);
  g_setenv("FP_VIRTUAL_DEVICE", socket, TRUE);
  g_autoptr(FpContext) ctx = fp_context_new();
  fp_context_enumerate(ctx);
  GPtrArray *devices = fp_context_get_devices(ctx);
  g_assert_cmpuint(devices->len, ==, 1);
  FpDevice *device = g_ptr_array_index(devices, 0);
  gpointer weak = NULL;
  /* Old implementation destroys the object before verify can use it. */
  (void)prepare_return(device, FALSE, &weak);
  g_assert_null(weak);
  FpPrint *result = prepare_return(device, TRUE, &weak);
  g_assert_nonnull(weak);
  g_assert_true(FP_IS_PRINT(result));
  g_assert_false(g_object_is_floating(result));
  g_object_unref(result);
  g_assert_null(weak);
  g_rmdir(dir);
  g_print("PASS: reproduced old dangling print; fixed print survives prepare and releases cleanly.\n");
}
