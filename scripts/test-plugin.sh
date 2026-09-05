#!/bin/bash
set -euo pipefail
cd -- "$(dirname -- "$(readlink -f -- "$0")")/.."
stage=$(mktemp -d)
trap 'rm -rf -- "$stage"' EXIT
mkdir -p "$stage/plugin" "$stage/imports"
# Validate distributable files, excluding local builds, dependencies and Git state.
git ls-files -z --cached --others --exclude-standard | while IFS= read -r -d '' file; do
  mkdir -p "$stage/plugin/$(dirname -- "$file")"
  cp -- "$file" "$stage/plugin/$file"
done
omarchy plugin validate "$stage/plugin"
ln -s /usr/share/omarchy/shell "$stage/imports/qs"
# Installed Quickshell metadata marks PanelWindow uncreatable and omits
# QProcess::ExitStatus. These two metadata warnings also affect built-ins.
/usr/lib/qt6/bin/qmllint -I "$stage/imports" \
  --uncreatable-type disable --signal-handler-parameters disable "$stage/plugin/Panel.qml"
desktop-file-validate "$stage/plugin/t480fingerprint.desktop"
uv run --with pytest pytest -q -p no:cacheprovider tests/test_plugin.py tests/test_sudo_auth.py tests/test_launcher.py
