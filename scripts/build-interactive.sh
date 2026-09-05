#!/bin/bash
set -euo pipefail
cd -- "$(dirname -- "$(readlink -f -- "$0")")/.."
[[ $EUID != 0 ]] || { echo 'Build as your ordinary user.' >&2; exit 1; }
revision=0fd78560a245eebec1c93e71ee1f29b15ec1be67
data_revision=4b03b2a1e607b4fea4b7a447644aaf02aa92e2e7
if [[ ! -d sources/libfprint/.git ]]; then ./scripts/build.sh; fi
if [[ ! -e sources/libfprint-guarded/.git ]]; then
  git -C sources/libfprint worktree add --detach ../libfprint-guarded "$revision"
  git -C sources/libfprint-guarded apply ../../patches/0001-guard-sensor-initialization.patch
fi
[[ $(git -C sources/libfprint-guarded rev-parse HEAD) == "$revision" ]]
# Require exactly our reviewed patch, not arbitrary edits to privileged runtime code.
git -C sources/libfprint-guarded diff --binary | cmp - patches/0001-guard-sensor-initialization.patch
if [[ ! -d sources/validity-data/.git ]]; then
  git init sources/validity-data
  git -C sources/validity-data remote add origin https://gitlab.freedesktop.org/ggiesen/libfprint-validity-data.git
  git -C sources/validity-data fetch --depth=1 origin "$data_revision"
  git -C sources/validity-data checkout --detach "$data_revision"
fi
[[ $(git -C sources/validity-data rev-parse HEAD) == "$data_revision" ]]
git -C sources/validity-data diff --quiet HEAD
make -C sources/validity-data generate verify
if [[ ! -f build/guarded/build.ninja ]]; then
  meson setup build/guarded sources/libfprint-guarded --prefix=/opt/t480fingerprint --libdir=lib \
    -Ddrivers=validity,virtual_image,virtual_device,virtual_device_storage \
    -Ddoc=false -Dinstalled-tests=false -Dudev_rules=disabled -Dudev_hwdb=disabled
fi
meson compile -C build/guarded -j 4
for tool in probe enroll-verify; do
  cc -Wall -Wextra -Werror "tools/$tool.c" -o "build/guarded/t480-$tool" \
    -Isources/libfprint-guarded/libfprint -Ibuild/guarded/libfprint \
    $(pkg-config --cflags --libs gio-2.0 gusb) -Lbuild/guarded/libfprint -lfprint-2 \
    -Wl,-rpath,'$ORIGIN/libfprint:$ORIGIN/../lib'
done
cc -Wall -Wextra -Werror -Itools tests/workflow.c -o build/guarded/test-workflow
build/guarded/test-workflow

# Exercise FpPrint ownership across the prepare/verify boundary without hardware.
cc -Wall -Wextra -Werror -Itools -Isources/libfprint-guarded/libfprint -Ibuild/guarded/libfprint \
  tests/print-lifetime.c -o build/guarded/test-print-lifetime \
  $(pkg-config --cflags --libs gio-2.0 gusb) -Lbuild/guarded/libfprint -lfprint-2 \
  -Wl,-rpath,'$ORIGIN/libfprint'
build/guarded/test-print-lifetime
