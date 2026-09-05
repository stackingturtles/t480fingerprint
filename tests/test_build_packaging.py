"""Integration regressions using the prepared build; never install a package."""
from pathlib import Path
import os
import shutil
import subprocess
import sys

import pytest

REPO = Path(__file__).resolve().parents[1]


def test_failed_checkout_stops_baseline_build(tmp_path):
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    shutil.copy2(REPO / "scripts/build.sh", scripts / "build.sh")
    (tmp_path / "sources").mkdir()
    (tmp_path / "sources/libfprint").symlink_to(REPO / "sources/libfprint", target_is_directory=True)
    (tmp_path / "build").mkdir()
    (tmp_path / "build/build.ninja").touch()
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    marker = tmp_path / "executed-after-failed-pin"
    git = fake_bin / "git"
    git.write_text('#!/bin/bash\nfor arg in "$@"; do [[ $arg != checkout ]] || exit 42; done\nexec /usr/bin/git "$@"\n')
    git.chmod(0o755)
    for command in ("meson", "cc"):
        fake = fake_bin / command
        fake.write_text('#!/bin/sh\ntouch "$PIN_FAILURE_MARKER"\n')
        fake.chmod(0o755)
    result = subprocess.run(["bash", str(scripts / "build.sh")],
                            env=os.environ | {"PATH": str(fake_bin) + ":" + os.environ["PATH"],
                                              "PIN_FAILURE_MARKER": str(marker)},
                            capture_output=True, text=True, timeout=30)
    assert result.returncode != 0, result.stdout + result.stderr
    assert not marker.exists(), "No build step may run after a failed checkout pin"


def test_default_git_diff_prefix():
    env = os.environ | {
        "GIT_CONFIG_COUNT": "1",
        "GIT_CONFIG_KEY_0": "diff.mnemonicPrefix",
        "GIT_CONFIG_VALUE_0": "false",
    }
    result = subprocess.run(
        ["bash", "scripts/build-interactive.sh"], cwd=REPO, env=env,
        capture_output=True, text=True, timeout=180,
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("package_failure", [False, True])
def test_package_discards_obsolete_staging(tmp_path, package_failure):
    files = [
        "scripts/package.sh", "packaging/PKGBUILD", "LICENSE", "tools/sudo-auth.py",
        "patches/0001-guard-sensor-initialization.patch",
        "sources/libfprint/COPYING", "sources/validity-data/LICENSE",
        "build/guarded/t480-probe", "build/guarded/t480-enroll-verify",
    ]
    for name in files:
        dest = tmp_path / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO / name, dest)
    shutil.copytree(REPO / "sources/validity-data/output",
                    tmp_path / "sources/validity-data/output")
    libdir = tmp_path / "build/guarded/libfprint"
    libdir.mkdir()
    for path in (REPO / "build/guarded/libfprint").glob("libfprint-2.so*"):
        if path.is_file():
            shutil.copy2(path, libdir / path.name, follow_symlinks=False)
    obsolete = tmp_path / "build/package-input/lab/bin/obsolete-test-tool"
    obsolete.parent.mkdir(parents=True)
    obsolete.write_text("obsolete executable from a previous package\n")
    env = os.environ.copy()
    if package_failure:
        fake_bin = tmp_path / "fake-bin"
        fake_bin.mkdir()
        makepkg = fake_bin / "makepkg"
        makepkg.write_text("#!/bin/sh\nexit 17\n")
        makepkg.chmod(0o755)
        env["PATH"] = str(fake_bin) + os.pathsep + env["PATH"]
    result = subprocess.run(
        ["bash", str(tmp_path / "scripts/package.sh")], env=env,
        capture_output=True, text=True, timeout=90,
    )
    assert not list((tmp_path / "build").glob("package-stage.*"))
    assert obsolete.exists(), "Pre-existing staging contents must remain untouched"
    if package_failure:
        assert result.returncode == 17, result.stdout + result.stderr
        return
    assert result.returncode == 0, result.stdout + result.stderr
    package = next((tmp_path / "build/package").glob("*.pkg.tar.zst"))
    members = subprocess.run(
        ["bsdtar", "-tf", str(package)], check=True,
        capture_output=True, text=True, timeout=10,
    ).stdout.splitlines()
    assert "opt/t480fingerprint/bin/obsolete-test-tool" not in members
    assert "opt/t480fingerprint/bin/t480-enroll-verify" in members


@pytest.mark.parametrize("mnemonic_prefix", ["true", "false"])
def test_source_validation_preserves_index_and_rejects_edits(tmp_path, mnemonic_prefix):
    source = tmp_path / "source"
    source.mkdir()
    git = ["git", "-C", str(source)]
    subprocess.run(git + ["init", "-q"], check=True, timeout=10)
    target = source / "driver.c"
    target.write_text("baseline\n")
    subprocess.run(git + ["add", "driver.c"], check=True, timeout=10)
    subprocess.run(git + ["-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                          "commit", "-qm", "baseline"], check=True, timeout=10)
    target.write_text("guarded\n")
    patch = tmp_path / "guard.patch"
    patch.write_bytes(subprocess.run(git + ["diff", "--binary", "--no-color"],
                                    check=True, capture_output=True, timeout=10).stdout)
    original_index = (source / ".git/index").read_bytes()
    env = os.environ | {"GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "diff.mnemonicPrefix",
                       "GIT_CONFIG_VALUE_0": mnemonic_prefix}
    command = [sys.executable, str(REPO / "scripts/check-patched-source.py"), str(source), str(patch)]
    result = subprocess.run(command, env=env, capture_output=True, timeout=40)
    assert result.returncode == 0, result.stderr
    assert (source / ".git/index").read_bytes() == original_index
    target.write_text("guarded\nunreviewed modification\n")
    result = subprocess.run(command, env=env, capture_output=True, timeout=40)
    assert result.returncode == 1
    assert (source / ".git/index").read_bytes() == original_index
