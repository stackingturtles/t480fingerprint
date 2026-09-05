#!/bin/bash
set -euo pipefail
cd -- "$(dirname -- "$(readlink -f -- "$0")")/.."
[[ $EUID != 0 ]] || { echo 'Package as your normal user.' >&2; exit 1; }
[[ -x build/guarded/t480-probe ]] || { echo 'Run scripts/build-interactive.sh first.' >&2; exit 1; }
mkdir -p build/package
package_stage=$(mktemp -d "$PWD/build/package-stage.XXXXXX")
# Only remove the unique directory allocated for this invocation, even after cd.
trap 'python3 -c "import shutil, sys; shutil.rmtree(sys.argv[1])" "$package_stage"' EXIT
mkdir -p "$package_stage"/lab/{bin,lib,licenses}
install -m755 build/guarded/t480-probe build/guarded/t480-enroll-verify "$package_stage"/lab/bin/
# Copy only shared libraries/symlinks, not Meson's similarly named object directory.
for library in build/guarded/libfprint/libfprint-2.so*; do
  [[ -f $library ]] || continue
  cp -a "$library" "$package_stage"/lab/lib/
done
install -m644 sources/libfprint/COPYING "$package_stage"/lab/licenses/libfprint-LGPL
mkdir -p "$package_stage"/lab/share/validity
cp -a sources/validity-data/output/. "$package_stage"/lab/share/validity/
install -m644 sources/validity-data/LICENSE "$package_stage"/lab/licenses/validity-data-MIT
install -m644 patches/0001-guard-sensor-initialization.patch "$package_stage"/lab/
install -m644 LICENSE "$package_stage"/lab/licenses/project-MIT
printf '%s\n' 'libfprint MR !626 commit 0fd78560a245eebec1c93e71ee1f29b15ec1be67' 'local patch: 0001-guard-sensor-initialization.patch' 'validity-data commit 4b03b2a1e607b4fea4b7a447644aaf02aa92e2e7' > "$package_stage"/lab/SOURCE
# Deterministic input archive; Arch package metadata still records build time.
tar --sort=name --mtime='2026-09-05 UTC' --owner=0 --group=0 --numeric-owner \
  -czf build/package/lab.tar.gz -C "$package_stage" lab
archive_hash=$(sha256sum build/package/lab.tar.gz | cut -d ' ' -f1)
sed "s/REPLACE_BY_PACKAGE_SCRIPT/$archive_hash/" packaging/PKGBUILD > build/package/PKGBUILD
cd build/package
makepkg --force --cleanbuild --noconfirm
