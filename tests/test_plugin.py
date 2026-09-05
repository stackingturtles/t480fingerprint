"""Panel status and action tests; no real services, scans or installation."""

import importlib.util
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("plugin", REPO / "scripts/plugin.py")
plugin = importlib.util.module_from_spec(spec)
spec.loader.exec_module(plugin)


@pytest.mark.parametrize("present", [False, True])
@pytest.mark.parametrize("installed", [False, True])
def test_status_distinguishes_hardware_package_and_policy(
    tmp_path, monkeypatch, present, installed
):
    device = tmp_path / "usb/1-1"
    device.mkdir(parents=True)
    (device / "idVendor").write_text("06cb" if present else "ffff")
    (device / "idProduct").write_text("009a")
    helper = tmp_path / "helper"
    helper.touch()
    monkeypatch.setattr(plugin, "HELPER", helper)
    monkeypatch.setattr(
        plugin.subprocess,
        "run",
        lambda *a, **kw: subprocess.CompletedProcess(
            a,
            0 if installed else 1,
            "t480fingerprint-lab " + plugin.PACKAGE if installed else "",
        ),
    )
    pam = tmp_path / "sudo"
    pam.write_text("# auth sufficient pam_fprintd.so\nauth include system-auth\n")
    result = plugin.status(tmp_path / "usb", pam)
    assert result["reader"] == present
    assert result["ready"] == installed
    assert not result["sudoEnabled"]
    pam.write_text("auth sufficient pam_fprintd.so max-tries=1 timeout=10\n")
    assert plugin.status(tmp_path / "usb", pam)["sudoEnabled"]


def test_action_arguments_never_use_a_shell():
    for action in ("prepare", "verify", "enable", "disable"):
        command = plugin.action_command(action, "left-thumb", "name with spaces")
        assert "name with spaces" in command
        assert "/bin/sh" not in command and "/bin/bash" not in command
    assert "prepare" in plugin.action_command("prepare", "left-thumb", "user")
    assert "setup" in plugin.action_command("enable", "left-thumb", "user")
    with pytest.raises(ValueError):
        plugin.action_command("delete", "left-thumb", "user")
    with pytest.raises(ValueError):
        plugin.action_command("prepare", "right-index-finger; id", "user")


@pytest.mark.parametrize("build_fails", [False, True])
def test_install_pins_local_commit_and_cleans_build(tmp_path, monkeypatch, build_fails):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    revision = "a" * 40
    monkeypatch.setattr(
        plugin.subprocess,
        "run",
        lambda *a, **kw: subprocess.CompletedProcess(a, 0, revision),
    )
    calls = []

    def run(args, timeout=1800, cwd=None):
        calls.append(args)
        if args[1] == "clone":
            Path(args[-1]).mkdir()
        if "./scripts/build-interactive.sh" in args and build_fails:
            raise subprocess.CalledProcessError(1, args)
        if "./scripts/package.sh" in args:
            package = cwd / "build/package/t480fingerprint-lab-test.pkg.tar.zst"
            package.parent.mkdir(parents=True)
            package.touch()

    monkeypatch.setattr(plugin, "run", run)
    if build_fails:
        with pytest.raises(subprocess.CalledProcessError):
            plugin.install()
    else:
        plugin.install()
    assert calls[1][-3:] == ["checkout", "--detach", revision]
    assert (
        any(args[:3] == ["/usr/bin/sudo", "/usr/bin/pacman", "-U"] for args in calls)
        != build_fails
    )
    assert not list((tmp_path / "t480fingerprint").iterdir())
