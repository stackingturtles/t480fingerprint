# Omarchy plugin development

The root manifest declares one standalone panel:
`io.github.stackingturtles.t480fingerprint`. `Panel.qml` runs inside the existing
Omarchy shell. It never starts a second Quickshell process.

The panel reads USB vendor/product identifiers, the package version and sudo
configuration through `scripts/plugin.py status`. It does not open the reader,
read templates or request privileges. Status refreshes every five seconds while
the panel is open. Enrollment results appear only in the action terminal.

Button actions open the configured terminal with argument arrays, without shell
interpolation. The bridge serializes actions using a user-runtime lock. The
root-owned authentication helper retains its separate privileged lock.

## Installation and privileges

Driver installation builds the exact local plugin Git commit in a temporary
cache checkout and fetches external sources at full pinned commits. It installs
dependencies through Omarchy, builds/tests without root, then asks pacman to
install the resulting package with sudo. Temporary builds are removed when the
action finishes or fails. The Git-managed plugin folder stays free of generated
libraries, symlinks and nested build repositories.

The package installs the driver and helper under `/opt/t480fingerprint`.
Prepare connects stock fprintd to the private driver, enrolls/verifies, and
leaves sudo policy unchanged. Enable repeats verification before adding PAM.
Disable restores password-only sudo and stock fprintd loading. Privileged
configuration backups live under `/var/backups/t480fingerprint-auth`.

The shell plugin does not install firmware, reset the sensor or remove prints.
The fprintd preservation policy blocks sensor deletion. Password fallback,
PAM backup/recovery and manual verification are described in [sudo setup](sudo-auth.md).

## Local development

Run `./scripts/test-plugin.sh` to validate distributable files and run panel/helper
tests. The script stages only Git-visible files, excluding ignored build output.
Run `./scripts/test.sh` and the build/package pytest suite after helper/package
changes as required by AGENTS.md.

For a live test, copy a clean snapshot into the user plugin directory, back up
`~/.config/omarchy/shell.json`, rescan, and enable the plugin:

```sh
omarchy-shell shell rescanPlugins
omarchy plugin enable io.github.stackingturtles.t480fingerprint
omarchy-shell shell summon io.github.stackingturtles.t480fingerprint '{}'
```

Do not symlink a build checkout into the plugin directory: validation rejects
symlinks and builds contain private development state. Never edit packaged
Omarchy files. A development snapshot should include `.git` if testing the
install button; it builds the snapshot's committed HEAD.

Check open/close, Escape, outside click, keyboard traversal and finger selection.
Check disable/re-enable, shell restart, and removal/reinstallation. Confirm no
authentication changes happen merely from these lifecycle events. Test actions
in visible terminals; a successful unit test does not establish physical
enrollment, matching or suspend/resume behavior.

## Marketplace

Submit the public repository root as category **Hardware**, tags **security**
and **system**. Document installer, package-manager, privilege, remote-build and
service-management capabilities for maintainer review. A marketplace listing
requires exact-commit validation and maintainer approval.

Plugin removal removes the panel only. Restore password-only sudo and uninstall
the Arch package separately when removing authentication support. This distinction
must remain explicit in the README and submission notes.
