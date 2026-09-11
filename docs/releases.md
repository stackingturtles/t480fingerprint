# Checksum-pinned driver releases

Normal installation downloads a prebuilt Arch package. The URL, exact byte count
and SHA-256 are constants in `scripts/plugin.py`, so replacing a GitHub release
asset or moving its tag cannot silently change the accepted package. Downloads
have HTTPS-only redirects, time limits and a kernel-enforced output file size
ceiling (expected size + 1 byte, with core dumps disabled). A mismatch fails closed, with
no source-build fallback. Runtime libraries are supplied by the operating system;
they are not compiled into a newly built package during installation.

## v1.0.2 artifact

The local release staging directory is `build/release-v1.0.2/` (ignored by Git).
It contains the tested package and SHA256SUMS. The package remains driver release
`1.94.100.r626.0fd7856-5`; v1.0.2 changes the plugin installer and test tooling,
not fingerprint matching or the PAM helper.

- File: `t480fingerprint-lab-1.94.100.r626.0fd7856-5-x86_64.pkg.tar.zst`
- Bytes: 270334
- SHA-256: `7af9fdb4ca35344ec3c7aa02742e15cd3a06a15266557b1a26c9d5443f6d8c94`
- Package source: `3e8f4e36f576759dd455932bae12d11028f1b11c` (unchanged
  packaging, tools and guard patch at the time this artifact was built).
- libfprint: `0fd78560a245eebec1c93e71ee1f29b15ec1be67`, with
  `patches/0001-guard-sensor-initialization.patch`.
- Runtime data: `4b03b2a1e607b4fea4b7a447644aaf02aa92e2e7`.

The archive retains upstream licenses, the guard patch, source identifiers,
`.PKGINFO` and makepkg's `.BUILDINFO` recording the build environment. It was built
and tested locally, not by reproducible-build CI. We do not claim bit-for-bit
reproducibility or a signed build attestation. The integrity guarantee is that
normal installation accepts only the exact retained artifact reviewed with this
plugin commit. Development rebuilds use the local toolchain and may differ.

## Publishing checklist

1. Finish the code review and test gates, including the offline Python tests,
   QML validation, native simulated suite and build/package regressions.
2. Check the retained package against both SHA256SUMS and the constants in
   `scripts/plugin.py`. Do not regenerate it after setting those pins. If it must
   change, update all three pins, repeat validation, and review the new artifact.
3. Set the manifest version and README install/update examples to the release
   version. Commit all release changes together.
4. Push the reviewed commit, tag it v1.0.2, and publish a GitHub release attaching
   the exact staged package and SHA256SUMS. The source repository contains no
   binary package. Retain the package locally until publication is verified.
5. Download through the public URL and verify it with `verify_artifact`; test the
   installer on a disposable Omarchy system, including a missing-dependency case.
   Do not use an active authentication installation for an unattended reinstall.
6. Update marketplace issue #5052's body with the full final SHA, artifact pin,
   lockfile changes and validation results. Editing the body triggers validation;
   a comment alone does not. Leave that commit unchanged during review.

The installer deliberately fails if its pinned release asset is unavailable.
Do not merge/deploy it to users before the asset is available. A release URL alone
is not an integrity check; the trusted pin is in the reviewed source tree.

## Updating test dependencies

`uv.lock` records exact versions and artifact hashes, including transitive pytest
and Ruff dependencies. `uv sync --locked` is an explicit network-enabled bootstrap;
normal tests use `uv run --frozen --offline`. A cold offline environment fails
instead of selecting or downloading a replacement. Update dependencies only as
a reviewed development change, regenerate the lock, and rerun the offline gates.
