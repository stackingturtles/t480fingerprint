#!/bin/bash
set -euo pipefail
cd -- "$(dirname -- "$(readlink -f -- "$0")")/.."
[[ $EUID != 0 ]] || { echo 'Run simulated tests as your normal user.' >&2; exit 1; }
[[ -f build/build.ninja || -f build/guarded/build.ninja ]] || { echo 'Run scripts/build.sh first.' >&2; exit 1; }
if [[ -f build/guarded/build.ninja ]]; then
  cc -Wall -Wextra -Werror -Itools tests/workflow.c -o build/guarded/test-workflow
  build/guarded/test-workflow
  meson test -C build/guarded --print-errorlogs --num-processes 2
else
  meson test -C build --print-errorlogs --num-processes 2
fi

if [[ -f build/guarded/build.ninja ]]; then
# Exercise FpPrint ownership across the prepare/verify boundary without hardware.
cc -Wall -Wextra -Werror -Itools -Isources/libfprint-guarded/libfprint -Ibuild/guarded/libfprint \
  tests/print-lifetime.c -o build/guarded/test-print-lifetime \
  $(pkg-config --cflags --libs gio-2.0 gusb) -Lbuild/guarded/libfprint -lfprint-2 \
  -Wl,-rpath,'$ORIGIN/libfprint'
build/guarded/test-print-lifetime
fi
