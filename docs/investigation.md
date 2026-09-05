# Fingerprint investigation — 2026-09-05

Live reader: Synaptics Metallica MIS Touch, USB `06cb:009a`.
Installed: fprintd 1.94.5-2, libfprint 1.94.100-1.
`fprintd-list ijonas` reports `No devices available`.
No active pam_fprintd entries found under /etc/pam.d.
No packages, PAM settings, firmware or enrollment changed during investigation.

The installed `/usr/share/omarchy/bin/omarchy-setup-security-fingerprint`
installs stock libfprint/fprintd, enrolls and verifies, then configures sudo,
polkit and Omarchy's separate fingerprint lock PAM stack. It does not add SDDM
login or encrypted-disk unlocking. Running it alone cannot fix this driver gap;
it also replaces libfprint-git with stock libfprint.

## Driver routes

- Stock supported-device list does not include this ID:
  https://fprint.freedesktop.org/supported-devices.html
- python-validity explicitly supports 06cb:009a in validitysensor/usb.py:
  https://github.com/uunicorn/python-validity
  It requires open-fprintd and fprintd clients. AUR currently lists
  python-validity 0.15-1 and open-fprintd 0.7-2; RPC lookup did not find the
  exact fprintd-clients dependency, so upstream's one-command recipe needs work.
- open-fprintd's own README warns that D-Bus requests lack authorization checks:
  https://github.com/uunicorn/open-fprintd#warning
  Do not treat this stack as a drop-in authentication solution without review.
- Native libfprint candidate: merge request !626:
  https://gitlab.freedesktop.org/libfprint/libfprint/-/merge_requests/626
  Direct inspection was blocked by GitLab's anti-bot page, so current merge
  status and source security have NOT been verified.
  Maintainer's Launchpad API description confirms a patched Ubuntu libfprint,
  validity-data and firmware fetcher tested on 06cb:009a:
  https://api.launchpad.net/1.0/~m-jedrasik/+archive/ubuntu/libfprint-validity
  These Ubuntu packages cannot be installed directly on Arch/Omarchy.

Next engineering step: obtain/review !626 source and build a pinned Arch package
plus required data/firmware tooling; test detection, then interactive enrollment
and verification BEFORE enabling PAM. Preserve password fallback and existing
passphrase disk unlocking. Any sensor reset/deletion of existing prints needs
specific review, not an automatic troubleshooting command.
