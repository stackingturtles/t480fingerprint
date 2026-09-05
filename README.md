# T480 Fingerprint

Enable the ThinkPad T480's **Synaptics Metallica MIS Touch fingerprint reader
(USB 06cb:009a)** on Arch Linux / Omarchy, starting with host `tank`.

**Status (2026-09-05):** the user confirmed persistent enrollment, verification
and fingerprint sudo working on `tank`. Package release -4 provides the guarded
native driver and setup helper under `/opt/t480fingerprint`. Automated tests
passed. Optional sudo integration is available below; it activates only after
a successful persistent enrollment and verification.
See [testing](docs/testing.md) and [source review](docs/source-review.md).

## Enable fingerprint sudo

With package release **-4** installed, run in a visible terminal:

```sh
cd ~/code/t480fingerprint
./scripts/setup-sudo.sh
```

Enter your password, then follow **PREPARE** (repeated finger scans) and
**VERIFY** (scan once more). This enrollment is retained for your Linux account.
An existing right-index enrollment is verified without replacing it.
Choose another finger with `./scripts/setup-sudo.sh --finger left-index-finger`.

After success, run `sudo -k` then `sudo -v`. A matching fingerprint authenticates;
one failed attempt or a 10-second scan timeout leads to the normal password prompt.
With the laptop lid closed, sudo skips the scanner. Cached sudo authorization
and commands allowed with NOPASSWD do not prompt.

See [sudo setup, tests and recovery](docs/sudo-auth.md) for installation,
additional fingerprints, password fallback tests and rollback.

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

By default the laboratory library is loaded only by test executables.
Optional sudo setup makes the stock fprintd service load this private library
through a local systemd drop-in. System libfprint is not replaced.

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
