#include <assert.h>
#include <stdio.h>
#include "workflow.h"
typedef struct { int prepare_result, verify_result, cleanup_result, state; } Fake;
static int prepare(void *p) { Fake *f=p; assert(f->state++ == 0); return f->prepare_result; }
static int verify(void *p) { Fake *f=p; assert(f->state++ == 1); return f->verify_result; }
static int cleanup(void *p) { Fake *f=p; assert(f->state++ == 2); return f->cleanup_result; }
int main(void) {
  const int cases[][5] = {{0,0,0,0,3},{0,1,0,1,3},{2,0,0,2,1},{130,0,0,130,1},
                         {0,2,0,2,3},{0,130,0,130,3},{0,0,3,3,3},{0,1,3,3,3}};
  for (unsigned i=0;i<sizeof(cases)/sizeof(cases[0]);i++) {
    Fake f = {cases[i][0],cases[i][1],cases[i][2],0};
    TestSteps steps={&f,prepare,verify,cleanup};
    assert(run_test(&steps)==cases[i][3]); assert(f.state==cases[i][4]);
  }
  puts("8 workflow cases passed: match, non-match, prepare failure, cancellation, verify failure and cleanup failure.");
}
