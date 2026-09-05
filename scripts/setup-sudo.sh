#!/bin/bash
set -euo pipefail
exec sudo /opt/t480fingerprint/bin/t480-sudo-auth setup "$@"
