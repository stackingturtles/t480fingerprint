#!/usr/bin/python3 -I
"""Install or remove the current user's T480 Fingerprint application entry."""

# Copyright (c) 2026 Stacking Turtles Ltd. SPDX-License-Identifier: MIT
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

NAME = "io.github.stackingturtles.t480fingerprint.desktop"
SOURCE = Path(__file__).resolve().parents[1] / "t480fingerprint.desktop"


def update(action: str, applications: Path, content: bytes) -> None:
    target = applications / NAME
    if target.is_symlink():
        raise ValueError(f"Refusing to replace a symlink: {target}")
    if target.exists() and target.read_bytes() != content:
        raise ValueError(
            f"Launcher entry has custom contents; review it manually: {target}"
        )
    if action == "remove":
        target.unlink(missing_ok=True)
        return
    if action != "install":
        raise ValueError("Unsupported launcher action")
    if target.exists():
        return
    applications.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".t480fingerprint-", dir=applications)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
            os.fchmod(stream.fileno(), 0o644)
        os.replace(name, target)
    finally:
        Path(name).unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["install", "remove"])
    args = parser.parse_args()
    if os.geteuid() == 0:
        parser.error("Run as your regular user, without sudo.")
    data = Path(os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local/share"))
    if not data.is_absolute():
        parser.error("XDG_DATA_HOME must be an absolute path.")
    try:
        update(args.action, data / "applications", SOURCE.read_bytes())
    except (OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1
    # Application launchers watch this directory. Refresh MIME metadata when
    # the standard desktop-file-utils command is available as well.
    if shutil.which("update-desktop-database"):
        subprocess.run(
            ["update-desktop-database", str(data / "applications")],
            check=False,
            timeout=10,
        )
    print(
        "T480 Fingerprint launcher "
        + ("installed." if args.action == "install" else "removed.")
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
