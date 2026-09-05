# Persistent enrollment and sudo authentication

Validated on `tank` on 2026-09-05: the user confirmed enrollment, verification
and the sudo workflow working. The managed sudo PAM block is active. Automated
tests verify password fallback routing; individual physical fallback, closed-lid
and suspend/resume results have not been separately reported.

Release -5 adds opt-in sudo authentication using Arch's stock fprintd and
pam_fprintd with the guarded native driver. Setup changes only sudo's PAM
service and a local fprintd service override. The lock screen, polkit, SDDM,
disk passphrase and TPM settings are unaffected.

## Install and prepare

Build and install as documented in testing.md, using package release -5:

```sh
./scripts/build-interactive.sh
./scripts/test.sh
./scripts/package.sh
sudo pacman -U build/package/t480fingerprint-lab-1.94.100.r626.0fd7856-5-x86_64.pkg.tar.zst
./scripts/setup-sudo.sh
```

The wrapper runs the root-owned `/opt/t480fingerprint/bin/t480-sudo-auth`.
It takes the login account from SUDO_USER; explicit `--user ijonas` is also
supported. It refuses root enrollment. PREPARE enrolls the right index finger
for up to 120 seconds. VERIFY waits up to 30 seconds. Failed/cancelled setup
does not enable a new PAM rule. A completed enrollment is retained even if
verification fails, so rerunning verifies it without enrolling again.

To add another finger, use `./scripts/setup-sudo.sh --finger left-index-finger`.
The service refuses all sensor deletion and clearing, including automatic
garbage collection. If enrollment reports a duplicate from the earlier crashed
laboratory test, try a different finger. Do not clear the reader or bulk-delete
records to recover. Replacement/removal of prints requires a separate reviewed
workflow; fprintd-delete is intentionally blocked by this preservation policy.

The old `enroll-verify.sh` remains a temporary laboratory test and cannot run
while fprintd owns the reader. Use `fprintd-verify` for normal testing now.
Enrollment references are private system state in `/var/lib/fprint`; never
copy them or raw biometric output into this repository.

The builder requires the exact current guard patch. If upgrading an older
checkout with its old guarded worktree, preserve that worktree using
`git -C sources/libfprint worktree move ../libfprint-guarded ../libfprint-guarded-before-auth`
and move `build/guarded` to an unused backup name before rebuilding.
Do not bypass the source checker or discard unknown local source edits.

## Configuration and behavior

`/etc/systemd/system/fprintd.service.d/90-t480fingerprint.conf` directs only
fprintd to `/opt/t480fingerprint/lib`, allows only the validity driver, and
sets `FP_T480_PRESERVE_PRINTS=1`. The setup verifies the running daemon's
library mapping. The existing systemd sandbox and D-Bus/Polkit policy remain.
Package installation alone does not activate this override.

After a successful scan, setup prepends a marked block to `/etc/pam.d/sudo`:

```pam
auth [success=1 default=ignore] pam_exec.so quiet /usr/bin/omarchy-hw-laptop-closed
auth sufficient pam_fprintd.so max-tries=1 timeout=10
```

The existing `auth include system-auth` follows this block unchanged. A match
is sufficient; a non-match, unavailable reader or timeout falls through to
password authentication. Account and session checks still run. The lid gate
uses Omarchy's existing helper. A scan retry such as a poor touch can also
consume the single attempt. The 10-second setting bounds the scan window;
daemon startup or communication failures may add their own timeout.

The helper accepts the stock sudo authentication include; it refuses custom
authentication stacks or an existing unmanaged fingerprint rule. Configuration
writes are atomic and backed up under `/var/backups/t480fingerprint-auth/`.
No PAM change occurs in the separate `driver` action, which is used for
noninteractive service installation and detection before the user scans.

## Tests to run yourself

Keep your current terminal open during these checks:

1. Run `./scripts/setup-sudo.sh`; expect PREPARE, VERIFY, then SUCCESS.
2. Run `fprintd-verify -f right-index-finger "$USER"` and scan your enrolled
   finger. Expect `verify-match` and exit status 0. Use the finger you selected
   if different. A different finger should report a non-match and nonzero status.
3. Run `sudo -k`, then `sudo -v`; scan the enrolled finger and expect success.
4. Run `sudo -k`, then `sudo -v`; scan an unenrolled finger. Expect the password
   prompt, enter your usual password, and expect success.
5. Repeat step 4 without touching the reader. After about 10 seconds, expect
   the password prompt. Repeat after suspend/resume. With an external keyboard
   and the lid closed, expect an immediate password prompt.

Use `sudo -k` between cases because cached sudo credentials skip authentication.
Do not test repeatedly with wrong passwords: normal system lockout rules apply.
Automated checks do not establish physical matching, cutoff timing or resume
reliability; record those results separately after performing these steps.

Automated tests (no root, no real reader, no authentication-policy changes):

```sh
uv run --with pytest pytest -q -p no:cacheprovider tests/test_sudo_auth.py
uv run --with pytest pytest -q -p no:cacheprovider tests/test_build_packaging.py
./scripts/test.sh
```

Tests cover setup failures, retaining existing prints, policy idempotency and
rollback. Linux-PAM executes a temporary configuration with simulated scanner
results to verify match/password routing, including password rejection.
Validity's USB emulation checks that deletion and clearing are blocked while
matching still works with preservation enabled. No user biometrics are used.

## Recovery

Restore password-only sudo and the stock daemon library:

```sh
sudo /opt/t480fingerprint/bin/t480-sudo-auth disable
```

Wait for fingerprint timeout and enter your password if needed. If sudo itself
cannot authenticate, use the unaffected graphical Polkit authentication:

```sh
pkexec /opt/t480fingerprint/bin/t480-sudo-auth disable
```

This removes only the exact managed PAM block and service drop-in, preserves
other PAM edits, and retains enrollment data. Edited managed blocks require
manual review. For emergency recovery from a root shell, remove the lines
between `# BEGIN t480fingerprint sudo` and `# END t480fingerprint sudo` inclusive
in `/etc/pam.d/sudo`, then remove the drop-in and run `systemctl daemon-reload`
and `systemctl stop fprintd`. The original config is also in the backup directory.
Disable integration before `sudo pacman -R t480fingerprint-lab`.

## References

The implementation follows the installed Omarchy fingerprint setup's PAM/lid
pattern, scoped to sudo. fprintd v1.94.5 `utils/enroll.c` and `utils/verify.c`
were inspected: they return success only for completed enrollment and a match.
The [fprintd Device API](https://fprint.freedesktop.org/fprintd-dev/Device.html)
defines enrollment and verification results; local `man pam_fprintd` documents
`max-tries` and `timeout`.
