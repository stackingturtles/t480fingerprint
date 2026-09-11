# Testing and recovery

## Automated tests

Use system Python 3.14 and uv. Run `uv sync --locked` once to download the exact
locked pytest/Ruff artifacts, or `uv sync --frozen --offline` with a populated
cache. All test commands use `uv run --frozen --offline`; do not use `--with`.

Contributor source-build prerequisites are base-devel, Git, Meson, Ninja,
glib2-devel, gobject-introspection, libgusb, libgudev, OpenSSL, Cairo, Pixman,
umockdev, Python, python-cairo, python-gobject, python-mako, python-markdown and
python-tqdm. Provision these through your system administrator. This development
workflow uses the local toolchain; the panel installs a fixed package instead.

Run `./scripts/build-interactive.sh`, then `./scripts/test.sh` as your ordinary user.
Tests use virtual devices and prerecorded fixtures, with hardware access limited
by the upstream test environment. Do not run the suite as root or run the upstream
hardware-capture scripts. Test logs stay under ignored `build/meson-logs/`.

Observed: 99 Meson test entries passed, 32 skipped, zero failed. The Validity unit
entry contains 172 individual cases; its umockdev fixture also passed. Skips are
other drivers omitted from this focused build and disabled hwdb generation.

## Install the laboratory package

```sh
./scripts/package.sh
sudo pacman -U build/package/t480fingerprint-lab-1.94.100.r626.0fd7856-5-x86_64.pkg.tar.zst
```

This installs a private shared library, runtime data and test programs in `/opt/t480fingerprint`.
It does not replace the system libfprint, install a daemon, add permissive USB
rules, or change PAM. The library contains Validity plus virtual test drivers;
the probe explicitly allows only Validity. Upstream LGPL notices are included.

## Physical reader detection

```sh
./scripts/probe.sh
```

Expected output includes:

```
PASS: native Validity driver detected a reader.
Enrollment stages: 8; verification API: yes
Detection only: opening, enrollment and fingerprint matching remain untested.
```

The script uses the installed probe, falling back to the local build if needed.
It checks for competing active fingerprint daemons and asks for sudo in your
terminal. The reviewed driver probe performs a USB connection reset, claims the
interface, reads GET_VERSION, and releases it. This is not a factory reset and
performs no fingerprint capture, enrollment or flash writes. Device serials are
not printed. A nonzero exit is a failed test, not evidence of working enrollment.

You can repeat this test manually after a normal suspend/resume. The test script
never suspends, locks or reboots the laptop itself. Exit status: 0 detected;
1 no reader detected; 2 invalid probe arguments.

## Interactive prepare → verify test

Run in a visible terminal so you can enter your password and see the prompts:

```sh
cd ~/code/t480fingerprint
./scripts/enroll-verify.sh
```

1. Enter your sudo password if asked. The tool opens the guarded driver.
2. **PREPARE:** repeatedly touch and lift your **right index finger**. Reposition
   it slightly for each scan. Progress shows accepted scans out of eight. You
   have up to 120 seconds; poor scans ask you to retry.
3. **VERIFY:** lift your finger, then touch again within 30 seconds. Use the
   enrolled finger to check a match. To test rejection, use another finger.
4. The tool reports **VERIFY SUCCEEDED** or **VERIFY FAILED**, removes the
   temporary enrolled print, closes the reader, then prints the final **RESULT**.

Rerun the command for another test. There is no permanent enrollment or local
fingerprint file. A random per-run record distinguishes the test from existing
prints; cleanup deletes only that completed enrollment. SIGKILL, power loss or
failure during enrollment/cleanup can leave a temporary sensor record; the tool
never clears all sensor storage as recovery. Do not repeatedly retry after a
cleanup failure without investigating remaining sensor records.

| Final status | Exit code | Meaning |
| --- | --- | --- |
| RESULT: SUCCESS | 0 | Match, cleanup and close succeeded |
| RESULT: FAIL (no match) | 1 | Scan did not match; cleanup completed |
| RESULT: ERROR (test incomplete) | 2 | Setup, scan, timeout or close error |
| RESULT: ERROR (test incomplete) | 3 | Cleanup failed; test print may remain |
| RESULT: ERROR (test incomplete) | 130 | Cancelled with Ctrl+C/SIGTERM |

Use `echo $?` immediately after the command to inspect its exit code. A driver
retry/poor-scan error during verification is an error, not a definite non-match.
Ctrl+C cancels the current operation; cleanup still runs after a completed
enrollment. Reader opening has a 60-second timeout, cleanup 30 seconds and close
15 seconds. Timeouts request cancellation; final response also depends on driver
cancellation handling. No images, templates, debug trace or serials are saved.

Readiness was verified on tank: the installed guarded reader opened and closed
successfully. No real enrollment or fingerprint match was performed by the agent;
those results require your scans using the command above.

### Check readiness without enrolling

```sh
./scripts/enroll-verify.sh --check
```

This opens/closes the guarded sensor session, including normal initialization
and calibration. It does not enroll. Automatic pairing/re-pairing, clean-slate
initialization, factory reset and firmware upload are blocked in this build.
If a guard reports initialization is required, stop there: changing that policy
requires a separate review of sensor state and preservation of existing prints.
Do not bypass it by running the unpatched upstream enrollment examples.

`--help` shows usage without accessing the reader. If another fingerprint daemon
is active, the wrapper stops; allow it to idle before retrying. The wrapper only
runs the root-owned installed binary and never points sudo at editable Python.

### Build/install this version

```sh
./scripts/build-interactive.sh
./scripts/test.sh
./scripts/package.sh
sudo pacman -U build/package/t480fingerprint-lab-1.94.100.r626.0fd7856-3-x86_64.pkg.tar.zst
```

Pinned runtime data is installed in `/opt/t480fingerprint/share/validity` with
its original MIT license. The driver guard patch is shipped with the package.
No vendor firmware is downloaded or installed. Both probe and interactive test
use the same guarded private library. Authentication configuration stays unchanged.

## Rollback

```sh
sudo pacman -R t480fingerprint-lab
```

The laboratory package has no service or authentication hooks to undo. Build
outputs can be kept for development. Build dependencies are recorded in the host
inventory; do not blindly remove dependencies used by other projects.

## Fixed verification segfault (package release -3)

The -2 test could crash immediately after enrollment. `fp_print_new()` returns
an initially floating reference, and `fp_device_enroll_sync()` consumes that
floating reference. The test's automatic template cleanup could therefore free
the very print returned for verification. The fix sinks a separately owned
reference before calling enroll; prepare cleanup and verification now have
independent ownership.

`tests/print-lifetime.c` reproduces the old early finalization and verifies the
fix using a real FpPrint with a virtual device, without collecting fingerprints.
It runs from build-interactive.sh and test.sh. The eight workflow tests also pass.
There was no stored core dump for the reported crash; the kernel recorded a
SIGSEGV in libgobject during the prepare-to-verify transition. The ownership
regression is reproduced; a new physical matching test still needs user scans.

Run the same `./scripts/enroll-verify.sh` command after upgrading. The old crash
may have left its temporary sensor record. It cannot safely be distinguished
from other records using a saved reference, because -2 did not persist one.
No existing fingerprint was deleted as part of this repair. Do not bulk-clear
sensor storage to remove it.

## Build and packaging regressions

After `./scripts/build-interactive.sh`, run both test gates:

```sh
./scripts/test.sh
uv run --frozen --offline pytest -q -p no:cacheprovider tests/test_build_packaging.py
```

The five Python cases exercise the real incremental build with default Git diff
prefixes, source validation with both prefix settings (including rejecting extra
edits and preserving the real index), and isolated package builds that exclude
obsolete staging files and clean up after success or failure. They need `uv`,
the normal build dependencies and `makepkg`; no root, install or sensor access
is used. Bootstrap with `uv sync --locked` once; subsequent test runs use the committed
hash-bound lock offline. Missing cache entries fail without a network fallback.

Source validation uses a disposable Git index populated from HEAD plus the
reviewed patch. It compares source contents rather than user-configurable diff
formatting. Packaging allocates a fresh staging directory per invocation and
removes only that directory, leaving any pre-existing staging work untouched.
# Persistent sudo authentication

For retained enrollment, sudo verification, password fallback and recovery,
follow [sudo authentication testing](sudo-auth.md). The laboratory workflow
below uses temporary enrollment and does not configure authentication.
