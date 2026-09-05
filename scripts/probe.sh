#!/bin/bash
set -euo pipefail
cd -- "$(dirname -- "$(readlink -f -- "$0")")/.."
if systemctl is-active --quiet fprintd.service || systemctl is-active --quiet python3-validity.service; then
  echo 'A fingerprint daemon is active. Wait for fprintd to idle, or stop it before probing.' >&2
  exit 1
fi
if [[ -x /opt/t480fingerprint/bin/t480-probe ]]; then
  probe=/opt/t480fingerprint/bin/t480-probe
else
  probe="$PWD/build/t480-probe"
fi
[[ -x $probe ]] || { echo 'Run scripts/build.sh first.' >&2; exit 1; }
# Use sudo from a visible terminal. This does not enroll or configure PAM.
if [[ $EUID == 0 ]]; then
  exec "$probe"
else
  exec sudo "$probe"
fi
