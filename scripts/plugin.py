#!/usr/bin/python3 -I
"""Unprivileged Omarchy panel bridge; mutations run only in a visible terminal."""

# Copyright (c) 2026 Stacking Turtles Ltd. SPDX-License-Identifier: MIT
import argparse
import fcntl
import hashlib
import json
import os
import pwd
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import BinaryIO

REPO = Path(__file__).resolve().parents[1]
HELPER = Path("/opt/t480fingerprint/bin/t480-sudo-auth")
PACKAGE = "1.94.100.r626.0fd7856-5"
FINGERS = [
    f"{hand}-{finger}-finger"
    for hand in ("left", "right")
    for finger in ("index", "middle", "ring", "little")
]
FINGERS += ["left-thumb", "right-thumb"]
# Updated only after building, testing and retaining the exact release artifact.
ARTIFACT_URL = (
    "https://github.com/stackingturtles/t480fingerprint/releases/download/v1.0.2/"
    "t480fingerprint-lab-1.94.100.r626.0fd7856-5-x86_64.pkg.tar.zst"
)
ARTIFACT_SIZE = 270334
ARTIFACT_SHA256 = "7af9fdb4ca35344ec3c7aa02742e15cd3a06a15266557b1a26c9d5443f6d8c94"


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


def fetch_artifact(target: BinaryIO) -> None:
    """Fixed public release URL; HTTPS-only redirects, byte and time limits."""
    subprocess.run(
        [
            "/usr/bin/prlimit",
            f"--fsize={ARTIFACT_SIZE + 1}:{ARTIFACT_SIZE + 1}",
            "--core=0:0",
            "--",
            "/usr/bin/curl",
            "-q",
            "--fail",
            "--location",
            "--silent",
            "--show-error",
            "--proto",
            "=https",
            "--proto-redir",
            "=https",
            "--max-redirs",
            "5",
            "--connect-timeout",
            "15",
            "--max-time",
            "120",
            "--max-filesize",
            str(ARTIFACT_SIZE),
            "--",
            ARTIFACT_URL,
        ],
        stdout=target,
        check=True,
        timeout=130,
    )


def verify_artifact(source: BinaryIO) -> None:
    source.seek(0)
    digest = hashlib.sha256()
    size = 0
    while chunk := source.read(min(65536, ARTIFACT_SIZE + 1 - size)):
        size += len(chunk)
        digest.update(chunk)
        if size > ARTIFACT_SIZE:
            break
    if size != ARTIFACT_SIZE or digest.hexdigest() != ARTIFACT_SHA256:
        raise ValueError("Release package integrity check failed; nothing installed.")
    source.seek(0)


def install() -> None:
    # No source checkout, compiler, dependency resolution or build runs here.
    print("Downloading the checksum-pinned driver package…", flush=True)
    with tempfile.TemporaryFile() as artifact:
        fetch_artifact(artifact)
        verify_artifact(artifact)
        print(
            "Package verified. sudo will stage a root-owned copy for pacman.",
            flush=True,
        )
        staging = subprocess.run(
            [
                "/usr/bin/sudo",
                "/usr/bin/mktemp",
                "-d",
                "/var/tmp/t480fingerprint.XXXXXXXXXX",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=120,
        ).stdout.strip()
        if not re.fullmatch(r"/var/tmp/t480fingerprint\.[A-Za-z0-9]{10}", staging):
            raise ValueError("Unexpected root staging path; refusing installation.")
        package = staging + "/driver.pkg.tar.zst"
        try:
            # Copy the held descriptor, not a re-resolved user-controlled pathname.
            run(
                [
                    "/usr/bin/sudo",
                    "/usr/bin/install",
                    "-o",
                    "root",
                    "-g",
                    "root",
                    "-m",
                    "600",
                    f"/proc/{os.getpid()}/fd/{artifact.fileno()}",
                    package,
                ]
            )
            checksum = subprocess.run(
                ["/usr/bin/sudo", "/usr/bin/sha256sum", "--", package],
                check=True,
                capture_output=True,
                text=True,
                timeout=120,
            ).stdout.split()
            if not checksum or checksum[0] != ARTIFACT_SHA256:
                raise ValueError("Root-staged package integrity check failed.")
            # The directory is root-owned 0700: user processes cannot replace the
            # verified bytes during pacman's interactive confirmation prompt.
            run(["/usr/bin/sudo", "/usr/bin/pacman", "-U", "--", package])
        finally:
            run(["/usr/bin/sudo", "/usr/bin/rm", "-f", "--", package], 120)
            run(["/usr/bin/sudo", "/usr/bin/rmdir", "--", staging], 120)
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
    except EOFError, KeyboardInterrupt:
        pass
    return result


if __name__ == "__main__":
    sys.exit(main())
