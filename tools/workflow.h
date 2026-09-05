/* Copyright (c) 2026 Stacking Turtles Ltd. SPDX-License-Identifier: MIT */
#ifndef T480_WORKFLOW_H
#define T480_WORKFLOW_H
/* prepare returns 0 only with a completed temporary enrollment.
 * verify: 0 match, 1 non-match, 2 error, 130 cancellation.
 * cleanup deletes only that enrollment; failure overrides match success. */
typedef struct {
  void *data;
  int (*prepare)(void *);
  int (*verify)(void *);
  int (*cleanup)(void *);
} TestSteps;
static inline int run_test(TestSteps *steps) {
  int result = steps->prepare(steps->data);
  if (result) return result;
  result = steps->verify(steps->data);
  if (steps->cleanup(steps->data)) return 3;
  return result;
}
#endif
