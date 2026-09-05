"""Launcher lifecycle tests in temporary application directories."""

import importlib.util
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("launcher", REPO / "scripts/launcher.py")
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)


def test_install_and_remove_are_idempotent(tmp_path):
    applications = tmp_path / "applications"
    content = launcher.SOURCE.read_bytes()
    launcher.update("install", applications, content)
    target = applications / launcher.NAME
    original_time = target.stat().st_mtime_ns
    launcher.update("install", applications, content)
    assert target.stat().st_mtime_ns == original_time
    assert target.read_bytes() == content
    assert target.stat().st_mode & 0o777 == 0o644
    unrelated = applications / "another.desktop"
    unrelated.write_text("another application")
    launcher.update("remove", applications, content)
    launcher.update("remove", applications, content)
    assert not target.exists()
    assert unrelated.read_text() == "another application"


@pytest.mark.parametrize("action", ["install", "remove"])
def test_custom_launcher_is_preserved(tmp_path, action):
    target = tmp_path / launcher.NAME
    target.write_text("custom launcher")
    with pytest.raises(ValueError, match="custom contents"):
        launcher.update(action, tmp_path, launcher.SOURCE.read_bytes())
    assert target.read_text() == "custom launcher"


@pytest.mark.parametrize("action", ["install", "remove"])
def test_symlink_is_preserved(tmp_path, action):
    target = tmp_path / launcher.NAME
    target.symlink_to(tmp_path / "missing")
    with pytest.raises(ValueError, match="symlink"):
        launcher.update(action, tmp_path, launcher.SOURCE.read_bytes())
    assert target.is_symlink()
