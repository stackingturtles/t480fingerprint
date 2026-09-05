#!/usr/bin/python3 -I
"""Opt-in fprintd/sudo setup. Run the packaged copy as root from a terminal."""

# Copyright (c) 2026 Stacking Turtles Ltd. SPDX-License-Identifier: MIT
import argparse
import fcntl
import os
import pwd
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PAM = Path("/etc/pam.d/sudo")
DROPIN = Path("/etc/systemd/system/fprintd.service.d/90-t480fingerprint.conf")
BACKUPS = Path("/var/backups/t480fingerprint-auth")
SERVICE_CONFIG = """# Managed by t480fingerprint sudo-auth
[Service]
Environment="LD_LIBRARY_PATH=/opt/t480fingerprint/lib"
Environment="FP_DRIVERS_ALLOWLIST=validity"
Environment="FP_T480_PRESERVE_PRINTS=1"
"""
PAM_BLOCK = """# BEGIN t480fingerprint sudo
auth [success=1 default=ignore] pam_exec.so quiet /usr/bin/omarchy-hw-laptop-closed
auth sufficient pam_fprintd.so max-tries=1 timeout=10
# END t480fingerprint sudo
"""
FINGERS = [
    f"{hand}-{finger}-finger"
    for hand in ("left", "right")
    for finger in ("index", "middle", "ring", "little")
]
FINGERS += ["left-thumb", "right-thumb"]


def pam_content(original: str, enable: bool) -> str:
    """Preserve the existing stack; reject configurations needing manual review."""
    remaining = original.replace(PAM_BLOCK, "")
    if "t480fingerprint sudo" in remaining:
        raise ValueError("Managed PAM block was edited; review it manually.")
    if not enable:
        return remaining
    if "pam_fprintd.so" in remaining:
        raise ValueError("Existing fingerprint PAM configuration needs manual review.")
    auth = [
        line.split()
        for line in remaining.splitlines()
        if line.strip()
        and not line.lstrip().startswith("#")
        and line.split()[0].lstrip("-") == "auth"
    ]
    if auth != [["auth", "include", "system-auth"]]:
        raise ValueError(
            "Expected the stock sudo auth include system-auth; refusing to replace custom policy."
        )
    return PAM_BLOCK + remaining


def replace_config(path: Path, content: str) -> None:
    """Back up existing configuration and atomically replace it with mode intact."""
    if path.is_symlink():
        raise ValueError(f"Refusing symlink: {path}")
    if path.exists() and path.read_text() == content:
        return
    BACKUPS.mkdir(mode=0o700, parents=True, exist_ok=True)
    backup = Path(tempfile.mkdtemp(prefix="change-", dir=BACKUPS))
    if path.exists():
        shutil.copy2(path, backup / path.name)
    (backup / "target.txt").write_text(str(path) + "\n")
    path.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
    mode = path.stat().st_mode & 0o777 if path.exists() else 0o644
    fd, name = tempfile.mkstemp(prefix=".t480-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
            os.fchmod(stream.fileno(), mode)
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)
    print(f"Configuration backup: {backup}", flush=True)


def run(*args: str, timeout: int = 30, capture: bool = False) -> str:
    result = subprocess.run(
        args,
        check=True,
        text=True,
        capture_output=capture,
        timeout=timeout,
        env={"PATH": "/usr/bin", "LANG": "C", "LC_ALL": "C"},
    )
    return result.stdout if capture else ""


def prepare_driver() -> None:
    if DROPIN.exists() and DROPIN.read_text() != SERVICE_CONFIG:
        raise ValueError(f"{DROPIN} has custom contents; review before setup.")
    run("/usr/bin/pacman", "-Q", "fprintd", "t480fingerprint-lab")
    if not Path("/usr/lib/security/pam_fprintd.so").is_file():
        raise ValueError("Install the Arch fprintd package first.")
    replace_config(DROPIN, SERVICE_CONFIG)
    run("/usr/bin/systemctl", "daemon-reload")
    run("/usr/bin/systemctl", "restart", "fprintd.service")
    pid = run(
        "/usr/bin/systemctl",
        "show",
        "fprintd.service",
        "-p",
        "MainPID",
        "--value",
        capture=True,
    ).strip()
    maps = Path(f"/proc/{int(pid)}/maps").read_text()
    if "/opt/t480fingerprint/lib/libfprint-2.so" not in maps:
        raise ValueError(
            "fprintd did not load the private library; sudo policy was not enabled."
        )
    print("fprintd loaded the guarded T480 driver.", flush=True)


def setup(user: str, finger: str) -> None:
    account = pwd.getpwnam(user)
    if account.pw_uid == 0 or user.startswith("-"):
        raise ValueError("Choose a non-root login account.")
    # Validate policy before touching the reader. Read it again after scans.
    pam_content(PAM.read_text(), True)
    if not Path("/usr/bin/omarchy-hw-laptop-closed").is_file():
        raise ValueError("Omarchy lid helper is missing.")
    prepare_driver()
    listing = run("/usr/bin/fprintd-list", user, capture=True)
    enrolled = re.findall(r"^ - #\d+: ([-a-z]+)$", listing, re.MULTILINE)
    if finger not in enrolled:
        print(
            f"PREPARE: repeatedly touch and lift your {finger} (up to 120 seconds).",
            flush=True,
        )
        run("/usr/bin/fprintd-enroll", "-f", finger, user, timeout=120)
    else:
        print(f"PREPARE: keeping the existing {finger} enrollment.", flush=True)
    print(
        "VERIFY: lift your finger, then scan it again (up to 30 seconds).", flush=True
    )
    # fprintd v1.94.5 exits zero only for verify-match, not a non-match/error.
    run("/usr/bin/fprintd-verify", "-f", finger, user, timeout=30)
    replace_config(PAM, pam_content(PAM.read_text(), True))
    print(
        "SUCCESS: sudo fingerprint authentication enabled; password fallback remains.",
        flush=True,
    )


def disable() -> None:
    # Remove only our exact block, retaining subsequent administrator edits.
    replace_config(PAM, pam_content(PAM.read_text(), False))
    if DROPIN.exists():
        if DROPIN.read_text() != SERVICE_CONFIG:
            raise ValueError(
                "Sudo restored; custom fprintd drop-in needs manual review."
            )
        replace_config(DROPIN, "")
        DROPIN.unlink()
        run("/usr/bin/systemctl", "daemon-reload")
        run("/usr/bin/systemctl", "stop", "fprintd.service")
    print("Password-only sudo restored. Fingerprint enrollments retained.", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["driver", "setup", "disable"])
    parser.add_argument("--user", default=os.environ.get("SUDO_USER"))
    parser.add_argument("--finger", choices=FINGERS, default="right-index-finger")
    args = parser.parse_args()
    if os.geteuid() != 0:
        parser.error("Run with sudo (or pkexec for driver/disable).")
    if args.action == "setup" and (not args.user or not sys.stdin.isatty()):
        parser.error("Setup needs --user and a visible terminal for fingerprint scans.")
    try:
        with open("/run/t480fingerprint-auth.lock", "w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            if args.action == "setup":
                setup(args.user, args.finger)
            elif args.action == "driver":
                prepare_driver()
            else:
                disable()
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print(
            f"ERROR: {error}\nSetup did not complete. Existing enrollments were retained.",
            file=sys.stderr,
        )
        return 1
    except KeyboardInterrupt:
        print("\nCancelled; existing enrollments retained.", file=sys.stderr)
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
