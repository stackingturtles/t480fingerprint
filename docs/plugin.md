# Omarchy plugin development

The root manifest declares one standalone panel:
`io.github.stackingturtles.t480fingerprint`. `Panel.qml` runs inside the existing
Omarchy shell. It never starts a second Quickshell process.

`scripts/launcher.py install` registers `t480fingerprint.desktop` as
`$XDG_DATA_HOME/applications/io.github.stackingturtles.t480fingerprint.desktop`
(default `~/.local/share/applications`). The entry opens the panel through the
existing shell IPC command; it never launches another shell process or elevates
privileges. Run `scripts/launcher.py remove` before `omarchy plugin remove`.
Registration/removal preserve custom or symlinked entries and are idempotent.
Omarchy has no custom install/remove hooks, so both steps are explicit.

The panel reads USB vendor/product identifiers, the package version and sudo
configuration through `scripts/plugin.py status`. It does not open the reader,
read templates or request privileges. Status refreshes every five seconds while
the panel is open. Enrollment results appear only in the action terminal.

Button actions open the configured terminal with argument arrays, without shell
interpolation. The bridge serializes actions using a user-runtime lock. The
root-owned authentication helper retains its separate privileged lock.

## Installation and privileges

Driver installation downloads the fixed release URL in `scripts/plugin.py`.
Its expected size and SHA-256 are part of the reviewed plugin tree. curl limits
time and redirects to HTTPS; prlimit independently caps the output file size; failures never fall back to a source build.
The package is checked without privileges, copied from its held descriptor into
a root-owned 0700 temporary directory, checked again, then installed through
pacman. The root directory is removed on success or failure. Neither source builds
nor build dependency installation run from the panel. Existing runtime libraries
remain the operating system's responsibility.

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
Omarchy files. The install button needs the published artifact matching its embedded pin; it
does not need Git metadata. Local builds do not override that pin.

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
