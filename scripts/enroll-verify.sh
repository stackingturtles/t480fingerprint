#!/bin/bash
set -euo pipefail
if [[ $# -gt 1 || ( $# -eq 1 && $1 != --check && $1 != --help ) ]]; then
  echo 'Usage: scripts/enroll-verify.sh [--check|--help]' >&2
  exit 2
fi
program=/opt/t480fingerprint/bin/t480-enroll-verify
[[ -x $program ]] || { echo 'Install the interactive laboratory package first; see docs/testing.md.' >&2; exit 2; }
if [[ ${1:-} == --help ]]; then exec "$program" --help; fi
if systemctl is-active --quiet fprintd.service || systemctl is-active --quiet python3-validity.service; then
  echo 'Fingerprint daemon active. Wait for it to idle, or stop it before testing.' >&2
  exit 2
fi
if [[ $EUID == 0 ]]; then exec "$program" "$@"; fi
exec sudo "$program" "$@"
