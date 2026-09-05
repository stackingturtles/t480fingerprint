#!/usr/bin/python3 -I
"""Unprivileged Omarchy panel bridge; mutations run only in a visible terminal."""

# Copyright (c) 2026 Stacking Turtles Ltd. SPDX-License-Identifier: MIT
import argparse
import fcntl
import json
import os
import pwd
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
HELPER = Path("/opt/t480fingerprint/bin/t480-sudo-auth")
PACKAGE = "1.94.100.r626.0fd7856-5"
FINGERS = [
    f"{hand}-{finger}-finger"
    for hand in ("left", "right")
    for finger in ("index", "middle", "ring", "little")
]
FINGERS += ["left-thumb", "right-thumb"]
DEPENDENCIES = [
    "base-devel",
    "git",
    "meson",
    "ninja",
    "glib2-devel",
    "gobject-introspection",
    "libgusb",
    "libgudev",
    "openssl",
    "cairo",
    "pixman",
    "umockdev",
    "python",
    "python-cairo",
    "python-gobject",
    "python-mako",
    "python-markdown",
    "python-tqdm",
    "fprintd",
]


def read(path: Path) -> str:
    try:
        return path.read_text().strip()
    except OSError:
        return ""


def status(
    sysfs: Path = Path("/sys/bus/usb/devices"), pam: Path = Path("/etc/pam.d/sudo")
) -> dict:
    reader = any(
        read(device / "idVendor") == "06cb" and read(device / "idProduct") == "009a"
        for device in sysfs.glob("*")
    )
    package = subprocess.run(
        ["/usr/bin/pacman", "-Q", "t480fingerprint-lab"],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    version = package.stdout.strip().split()[-1] if package.returncode == 0 else ""
    policy = read(pam)
    sudo_enabled = any(
        line.strip()
        and not line.lstrip().startswith("#")
        and "pam_fprintd.so" in line.split()
        for line in policy.splitlines()
    )
    return {
        "reader": reader,
        "version": version,
        "ready": version == PACKAGE and HELPER.is_file(),
        "sudoEnabled": sudo_enabled,
    }


def run(args: list[str], timeout: int = 1800, cwd: Path | None = None) -> None:
    subprocess.run(args, check=True, timeout=timeout, cwd=cwd)


def install() -> None:
    # Build the installed plugin's immutable commit outside the live shell tree.
    revision = subprocess.run(
        ["/usr/bin/git", "-C", str(REPO), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    ).stdout.strip()
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("Cannot resolve the plugin commit to build.")
    cache = (
        Path(os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache")))
        / "t480fingerprint"
    )
    cache.mkdir(parents=True, exist_ok=True, mode=0o700)
    with tempfile.TemporaryDirectory(prefix="build-", dir=cache) as temporary:
        checkout = Path(temporary) / "source"
        run(
            [
                "/usr/bin/git",
                "clone",
                "--no-hardlinks",
                "--no-checkout",
                "--",
                str(REPO),
                str(checkout),
            ],
            60,
        )
        run(["/usr/bin/git", "-C", str(checkout), "checkout", "--detach", revision], 30)
        print(
            "Installing build dependencies; sudo may ask for your password.", flush=True
        )
        run(["/usr/bin/omarchy", "pkg", "add", *DEPENDENCIES])
        run(["/usr/bin/bash", "./scripts/build-interactive.sh"], cwd=checkout)
        run(["/usr/bin/bash", "./scripts/test.sh"], cwd=checkout)
        run(["/usr/bin/bash", "./scripts/package.sh"], cwd=checkout)
        packages = list(
            (checkout / "build/package").glob("t480fingerprint-lab-*.pkg.tar.zst")
        )
        if len(packages) != 1:
            raise ValueError("Expected exactly one built driver package.")
        run(["/usr/bin/sudo", "/usr/bin/pacman", "-U", str(packages[0])])
    print("Driver installed. Use Prepare fingerprint to enroll and verify.", flush=True)


def action_command(action: str, finger: str, user: str) -> list[str]:
    if (
        action not in ("prepare", "verify", "enable", "disable")
        or finger not in FINGERS
    ):
        raise ValueError("Unsupported fingerprint action or finger.")
    if action == "verify":
        return [
            "/usr/bin/timeout",
            "--foreground",
            "35",
            "/usr/bin/fprintd-verify",
            "-f",
            finger,
            user,
        ]
    helper_action = {"prepare": "prepare", "enable": "setup", "disable": "disable"}[
        action
    ]
    return [
        "/usr/bin/sudo",
        str(HELPER),
        helper_action,
        "--user",
        user,
        "--finger",
        finger,
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=["status", "install", "prepare", "verify", "enable", "disable"],
    )
    parser.add_argument(
        "finger", nargs="?", choices=FINGERS, default="right-index-finger"
    )
    args = parser.parse_args()
    if args.action == "status":
        try:
            print(json.dumps(status()))
            return 0
        except (OSError, subprocess.SubprocessError) as error:
            print(json.dumps({"error": str(error)}))
            return 1
    if os.geteuid() == 0 or not sys.stdin.isatty():
        parser.error("Run as your regular user in a visible terminal.")
    result = 0
    try:
        runtime = Path(os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}"))
        with (runtime / "t480fingerprint-panel.lock").open("w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            if args.action == "install":
                install()
            else:
                if not HELPER.is_file():
                    raise ValueError("Install the driver package first.")
                run(
                    action_command(
                        args.action, args.finger, pwd.getpwuid(os.getuid()).pw_name
                    )
                )
            print("\nSUCCESS", flush=True)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"\nFAILED: {error}", file=sys.stderr)
        result = 1
    except KeyboardInterrupt:
        print("\nCancelled.", file=sys.stderr)
        result = 130
    try:
        input("\nPress Enter to close this terminal. ")
    except (EOFError, KeyboardInterrupt):
        pass
    return result


if __name__ == "__main__":
    sys.exit(main())
