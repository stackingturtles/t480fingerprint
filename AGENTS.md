# T480 Fingerprint

This project develops fingerprint support for Omarchy/Arch on `tank`, a Lenovo
ThinkPad T480 with USB reader `06cb:009a`. Read README.md and docs/investigation.md
before implementation. Inventory is dated; verify live state before changes.

- Use the Omarchy skill for desktop/system configuration. Never customize files
  under `/usr/share/omarchy/`; use supported local configuration.
- Prefer native libfprint integration. MR !626 is a candidate, not verified or
  installed. Pin and review source and firmware inputs before building/installing.
- Preserve password fallback and passphrase disk unlocking. No incidental TPM,
  Secure Boot, BIOS updates, sensor factory resets or deletion of enrolled prints.
- Back up authentication configuration and document package/PAM recovery before
  changes. Enroll and verify with the user before enabling authentication.
- Never commit fingerprints, templates, sensor pairing keys, serial numbers,
  raw biometric/debug captures, credentials or private enrollment databases.
- Keep upstream licenses/notices intact. Original project contributions belong
  to Stacking Turtles Ltd.; do not apply MIT licensing to third-party drivers.
- Build without root; install through reviewed packages. Test device detection,
  enrollment/verification, password fallback and suspend/resume as applicable.
  Distinguish fixture/build checks from completed physical-device tests.
- Scope authorization from the active conversation. Creating this project alone
  does not authorize deleting sensor data or changing authentication policy.

## Built laboratory workflow — 2026-09-05

- User authorized building/testing. Native driver MR !626 pinned at
  `0fd78560a245eebec1c93e71ee1f29b15ec1be67`; unmodified upstream source under
  ignored sources/libfprint. MR state confirmed opened via GitLab API.
- scripts/build.sh, test.sh, package.sh, probe.sh implement the laboratory flow.
  Installed t480fingerprint-lab in /opt/t480fingerprint; system libfprint untouched.
- Probe must remain enumeration-only: no fp_device_open, enrollment or clearing.
  Upstream open may automatically reset/re-pair the sensor. Read docs/source-review.md
  before implementing enrollment. Creating/testing this probe did not authorize
  factory-resetting the reader or deleting existing fingerprints.
- 99 Meson entries passed, 32 skipped; Validity unit entry has 172 cases, and
  Validity emulation passed. Physical native detection passed; matching untested.
- Runtime data source pinned in docs/source-review.md, generated/verified but not
  installed. Do not commit raw test output that may include private identifiers.

## Interactive testing

- User requested prepare/enroll → verify → success/failure test with run docs.
  `scripts/enroll-verify.sh` runs the installed root-owned native tool. Only the
  newly created temporary enrollment is deleted after verification; no bulk clear.
- `scripts/build-interactive.sh` builds a separate guarded worktree with exactly
  patches/0001-guard-sensor-initialization.patch. The package script now packages
  this build plus pinned runtime data, version release -2. No firmware downloaded.
- `--check` opens/closes the guarded reader without enrolling. Initial pairing,
  re-pairing, factory reset, clean-slate initialization and firmware upload are
  rejected. Do not silently relax these guards to make a physical test pass.
- Run scripts/test.sh for the 8 workflow cases and 99 passing upstream test
  entries (32 skipped). README and docs/testing.md document manual scans,
  cancellation, timeouts, cleanup failures, results, exit codes and recovery.

## Verification crash fix — package -3

The user's prepare stage completed, then verification segfaulted on 2026-09-05.
No core was retained. Fixed floating FpPrint ownership in tools/print-template.h;
tests/print-lifetime.c reproduces old premature finalization and passes the fix
without hardware. Eight workflow cases pass. Do not claim a successful physical
match until the user reruns. Old crash's temporary enrollment may remain; no
saved recovery reference exists, so do not delete uncertain sensor records.
