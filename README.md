# T480 Fingerprint

Fingerprint authentication for the **Lenovo ThinkPad T480** on **Omarchy**, using
its Synaptics Metallica MIS Touch reader (USB `06cb:009a`).

The package provides a guarded native driver, persistent fingerprint enrollment,
and integration with sudo's PAM stack. A matching fingerprint authenticates;
a failed scan or scan timeout falls back to your password. Setup enables
fingerprint authentication only after enrollment and verification succeed.

## Install

You need Omarchy on x86-64 and the supported fingerprint reader. The sudo setup
uses Omarchy's laptop-lid helper and the standard `auth include system-auth`
PAM configuration.

Install the build, test and authentication dependencies:

```sh
sudo pacman -S --needed base-devel git meson ninja glib2-devel \
  gobject-introspection libgusb libgudev openssl cairo pixman umockdev \
  python python-cairo python-gobject python-mako python-markdown python-tqdm \
  fprintd uv
```

Clone the repository, build as your regular user, and install the package:

```sh
git clone https://github.com/stackingturtles/t480fingerprint.git
cd t480fingerprint
./scripts/build-interactive.sh
./scripts/test.sh
./scripts/package.sh
sudo pacman -U build/package/t480fingerprint-lab-1.94.100.r626.0fd7856-4-x86_64.pkg.tar.zst
```

The build fetches pinned driver and runtime-data sources. The package installs
under `/opt/t480fingerprint`; sudo setup loads its driver through a local
`fprintd` service override and backs up configuration before changing it.

## Use

From the repository directory, run in a terminal:

```sh
./scripts/setup-sudo.sh
```

Enter your password, then follow the prompts:

1. **PREPARE:** repeatedly touch and lift your right index finger to enroll it.
2. **VERIFY:** lift your finger and scan it again.
3. After successful verification, the helper enables fingerprint authentication
   in `/etc/pam.d/sudo`, preserving the existing password stack.

Enrollment is retained for your Linux account. An existing enrollment for the
selected finger is reused. To enroll and verify another finger:

```sh
./scripts/setup-sudo.sh --finger left-index-finger
```

Test sudo authentication:

```sh
sudo -k
sudo -v
```

Scan your enrolled finger to authenticate. One failed attempt or a 10-second
scan timeout leads to the password prompt. With the lid closed, sudo skips the
scanner. Cached sudo credentials and commands permitted with `NOPASSWD` do not
prompt; use `sudo -k` before each test.

To check password fallback, repeat the test with an unenrolled finger or wait
without scanning, then enter your password.

To restore password-only sudo while retaining enrolled fingerprints:

```sh
pkexec /opt/t480fingerprint/bin/t480-sudo-auth disable
```

Run this before uninstalling with `sudo pacman -R t480fingerprint-lab`.
The integration covers sudo; desktop login and screen unlocking require
separate configuration. Sensor deletion and clearing are blocked while the
service's preservation policy is active.

## Develop and test

Build the guarded driver and run the automated tests as your regular user:

```sh
./scripts/build-interactive.sh
./scripts/test.sh
uv run --with pytest pytest -q -p no:cacheprovider \
  tests/test_sudo_auth.py tests/test_build_packaging.py
uv run --with ruff ruff check tools/sudo-auth.py tests/test_sudo_auth.py
uv run --with ruff ruff format --check tools/sudo-auth.py tests/test_sudo_auth.py
```

These tests cover simulated reader operations, enrollment workflow, print
ownership, storage preservation, PAM password fallback, and packaging.
They do not require fingerprint scans or change system authentication.
Run `./scripts/package.sh` after rebuilding to produce an updated Arch package.

For a physical verification check after persistent enrollment:

```sh
fprintd-verify -f right-index-finger "$USER"
```

Before enabling the fprintd integration, `./scripts/enroll-verify.sh` offers a
standalone temporary **prepare → verify → result** test. It removes its own
completed enrollment afterward and refuses to run while a competing fingerprint
daemon is active. See the [testing guide](docs/testing.md) for test results,
exit codes and recovery instructions.

## Contribute

Contributions are welcome via pull requests. Include relevant tests and describe
any hardware validation performed. Keep fingerprints, enrollment databases and
sensor pairing keys out of commits.

## License

Original project code and documentation are licensed under the [MIT license](LICENSE).
Copyright (c) 2026 Stacking Turtles Ltd.

Bundled third-party components retain their own licenses and notices, including
libfprint's LGPL-2.1-or-later license and the runtime data's MIT license.
