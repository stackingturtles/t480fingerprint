# T480 Fingerprint

Fingerprint authentication for the **Lenovo ThinkPad T480** on **Omarchy**, using
its Synaptics Metallica MIS Touch reader (USB `06cb:009a`).

The plugin provides a settings panel, a guarded native driver, persistent fingerprint enrollment,
and integration with sudo's PAM stack. A matching fingerprint authenticates;
a failed scan or scan timeout falls back to your password. Setup enables
fingerprint authentication only after enrollment and verification succeed.

## Install

Add the plugin to Omarchy and open its settings panel:

```sh
omarchy plugin add https://github.com/stackingturtles/t480fingerprint.git --enable
omarchy-shell shell summon io.github.stackingturtles.t480fingerprint '{}'
```

Choose **Install / update driver**. A terminal opens to install dependencies,
build the pinned driver, run its tests and install the Arch package. Builds run
in a temporary directory under `~/.cache/t480fingerprint`, outside the plugin
folder. Installation may take several minutes and ask for your password.
Opening or enabling the panel does not install software or change authentication.

### Manual package installation

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
sudo pacman -U build/package/t480fingerprint-lab-1.94.100.r626.0fd7856-5-x86_64.pkg.tar.zst
```

The build fetches pinned driver and runtime-data sources. The package installs
under `/opt/t480fingerprint`; sudo setup loads its driver through a local
`fprintd` service override and backs up configuration before changing it.

## Use

Open the panel with:

```sh
omarchy-shell shell summon io.github.stackingturtles.t480fingerprint '{}'
```

Select a finger and choose **Prepare fingerprint** to enroll and verify it in a
terminal. Then choose **Enable fingerprint sudo**; the helper verifies your
finger again before changing PAM. **Test fingerprint** checks a saved enrollment.
**Restore password-only sudo** removes the integration while retaining prints.
Reopen the panel to see updated status. Escape or a click outside closes it.

For the combined enrollment and sudo setup from a source checkout, run:

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

To remove everything, restore password-only sudo first, then run:

```sh
omarchy plugin remove io.github.stackingturtles.t480fingerprint
sudo pacman -R t480fingerprint-lab
```

Removing or disabling just the panel leaves the driver, enrollment and sudo
configuration in place. The panel launches privileged operations only from
explicit button actions; the root-owned helper handles authentication changes.
The integration covers sudo; desktop login and screen unlocking require
separate configuration. Sensor deletion and clearing are blocked while the
service's preservation policy is active.

## Develop and test

Build the guarded driver and run the automated tests as your regular user:

```sh
./scripts/build-interactive.sh
./scripts/test.sh
./scripts/test-plugin.sh
uv run --with pytest pytest -q -p no:cacheprovider \
  tests/test_sudo_auth.py tests/test_plugin.py tests/test_build_packaging.py
uv run --with ruff ruff check tools/sudo-auth.py scripts/plugin.py tests/test_sudo_auth.py tests/test_plugin.py
uv run --with ruff ruff format --check tools/sudo-auth.py scripts/plugin.py tests/test_sudo_auth.py tests/test_plugin.py
```

`test-plugin.sh` validates a clean plugin snapshot and lints QML against the
installed shell imports. It suppresses two known Quickshell metadata warnings
(`PanelWindow` creatability and `QProcess::ExitStatus`); test the live panel too.
See [plugin development](docs/plugin.md) for the lifecycle checklist.

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
