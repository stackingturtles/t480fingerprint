#!/bin/bash
set -euo pipefail
cd -- "$(dirname -- "$(readlink -f -- "$0")")/.."
revision=0fd78560a245eebec1c93e71ee1f29b15ec1be67
source_url=https://gitlab.freedesktop.org/libfprint/libfprint.git
[[ $EUID != 0 ]] || { echo 'Build as your normal user.' >&2; exit 1; }
for command in git meson ninja cc pkg-config; do
  command -v "$command" >/dev/null || { echo "Missing dependency: $command" >&2; exit 1; }
done
if [[ ! -d sources/libfprint/.git ]]; then
  mkdir -p sources
  git init sources/libfprint
  git -C sources/libfprint remote add origin "$source_url"
  git -C sources/libfprint fetch --depth=1 origin "$revision"
  git -C sources/libfprint checkout --detach "$revision"
fi
# Python fixture tests create only bytecode caches inside the source tree.
if ! grep -qxF "__pycache__/" sources/libfprint/.git/info/exclude; then
  echo "__pycache__/" >> sources/libfprint/.git/info/exclude
fi
[[ $(git -C sources/libfprint rev-parse HEAD) == "$revision" ]] || { echo 'Source revision mismatch.' >&2; exit 1; }
[[ -z $(git -C sources/libfprint status --porcelain) ]] || { echo 'Source has local changes; refusing an unrecorded build.' >&2; exit 1; }
if [[ ! -f build/build.ninja ]]; then
  meson setup build sources/libfprint --prefix=/opt/t480fingerprint --libdir=lib \
    -Ddrivers=validity,virtual_image,virtual_device,virtual_device_storage \
    -Ddoc=false -Dinstalled-tests=false -Dudev_rules=disabled -Dudev_hwdb=disabled
fi
meson compile -C build -j 4
# Link explicitly to the laboratory build, not the system libfprint.
cc -Wall -Wextra -Werror tools/probe.c -o build/t480-probe \
  -Isources/libfprint/libfprint -Ibuild/libfprint \
  $(pkg-config --cflags --libs gio-2.0 gusb) \
  -Lbuild/libfprint -lfprint-2 -Wl,-rpath,'$ORIGIN/libfprint:$ORIGIN/../lib'
echo 'Built the isolated driver and build/t480-probe. Run scripts/test.sh.'
