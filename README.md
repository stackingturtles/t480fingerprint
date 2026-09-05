# T480 Fingerprint

Enable the ThinkPad T480's **Synaptics Metallica MIS Touch fingerprint reader
(USB 06cb:009a)** on Arch Linux / Omarchy, starting with host `tank`.

**Status (2026-09-05):** native driver built; automated tests and live USB
detection passed. An isolated `t480fingerprint-lab` Arch package provides the
probe under `/opt/t480fingerprint`. The guarded reader-open check passed. The interactive prepare/verify test is
available; a real matching result
requires you to scan a finger. Login integration remains disabled. See [testing](docs/testing.md) and [source review](docs/source-review.md).

## Run the fingerprint test

From a visible terminal:

```sh
cd ~/code/t480fingerprint
./scripts/enroll-verify.sh
```

Enter your sudo password if asked. During **PREPARE**, repeatedly touch and lift
your **right index finger** until enrollment completes. During **VERIFY**, lift
it and scan again. The test prints **RESULT: SUCCESS** for a match or
**RESULT: FAIL (no match)** for a different finger. Hardware/setup errors print
**RESULT: ERROR (test incomplete)** and never count as a match.

This is a temporary enrollment: the test removes only its own completed print
after verification. It does not enable fingerprint login. You can rerun the same
command to repeat the test. See [the full testing guide](docs/testing.md) for
exit codes, timeouts, cancellation, installation and troubleshooting.

## Build and automated tests

```sh
./scripts/build.sh               # original pinned upstream baseline
./scripts/build-interactive.sh   # guarded driver, runtime data, interactive test
./scripts/test.sh                # workflow and simulated upstream tests
./scripts/package.sh             # package the guarded build
```

Build dependencies: `base-devel git meson ninja glib2-devel gobject-introspection
libgusb libgudev openssl cairo umockdev python-cairo python-gobject`.
Install missing dependencies with `omarchy pkg add <packages...>`.

The laboratory library is loaded only by test executables. The system's
libfprint/fprintd and PAM configuration remain in place.

The 2026-09-05 inspection found fprintd 1.94.5-2 and libfprint 1.94.100-1
installed, but `fprintd-list ijonas` returned `No devices available`.
See [the investigation](docs/investigation.md) for sources and uncertainties.

## Approach

Investigate native libfprint support from upstream merge request !626, review
its source and required firmware/data handling, then build a pinned Arch package.
Git and the GitLab API are accessible; MR !626 was still open at this inspection.
The pinned commit is `0fd78560a245eebec1c93e71ee1f29b15ec1be67`.
Ubuntu packages mentioned in the investigation are reference material, not Arch
installation artifacts. The older python-validity/open-fprintd route has an
upstream D-Bus authorization warning that needs resolution before authentication use.

## Development milestones

1. Obtain the native driver source; record its upstream URL, commit, license,
   patch set, firmware requirements, and current review/merge status.
2. Review initialization, sensor writes, enrollment storage, and authorization.
   Establish whether existing sensor data would be affected before device tests.
3. Create a reproducible Arch package with pinned inputs and verified downloads.
   Record a package rollback procedure before installing it.
4. Verify device detection, then enroll and verify a finger with the user present.
5. Enable Omarchy screen unlocking after verification, retaining password access.
   Test password fallback, failed matches, and suspend/resume with the user.
6. Configure sudo/polkit only within the user's chosen authentication scope;
   document installation, updates, and recovery for Fleet integration later.

## Read-only checks

```sh
lsusb -d 06cb:009a
pacman -Q fprintd libfprint
fprintd-list "$USER"
```

The last command queries the service and may activate it through D-Bus. It does
not enroll a finger. Do not commit its output if it contains enrollment details.

## Omarchy integration

The installed `omarchy setup security fingerprint` workflow normally installs
stock libfprint/fprintd, enrolls and verifies, then configures sudo, polkit and
the lock screen. It does not resolve the current driver gap and may replace a
custom libfprint-git installation with stock libfprint. Review the installed
command before integrating a custom driver.

Disk-unlock passphrases remain in use. TPM configuration, Secure Boot and BIOS
updates are outside this project's fingerprint setup scope.

## License

Original project material: copyright (c) 2026 Stacking Turtles Ltd., under the
[MIT license](LICENSE). Any future third-party driver code retains its own license
and attribution; this project license does not relicense upstream components.
