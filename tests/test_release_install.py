"""Release integrity failures must never reach privileged package installation."""

import importlib.util
import io
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "plugin_release", Path(__file__).resolve().parents[1] / "scripts/plugin.py"
)
plugin = importlib.util.module_from_spec(spec)
spec.loader.exec_module(plugin)


def test_corrupt_release_never_requests_privileges(monkeypatch):
    calls = []
    monkeypatch.setattr(
        plugin, "fetch_artifact", lambda target: target.write(b"corrupt"), raising=False
    )
    monkeypatch.setattr(plugin, "run", lambda *args, **kwargs: calls.append(args))
    with pytest.raises(ValueError, match="integrity"):
        plugin.install()
    assert not calls


def test_release_verification_rejects_wrong_size_and_hash(monkeypatch):
    import hashlib

    monkeypatch.setattr(plugin, "ARTIFACT_SIZE", 4, raising=False)
    monkeypatch.setattr(
        plugin, "ARTIFACT_SHA256", hashlib.sha256(b"good").hexdigest(), raising=False
    )
    for data in (b"bad", b"evil", b"goodextra"):
        with pytest.raises(ValueError, match="integrity"):
            plugin.verify_artifact(io.BytesIO(data))
    plugin.verify_artifact(io.BytesIO(b"good"))


@pytest.mark.parametrize("failure", [None, "copy", "checksum", "pacman"])
def test_root_copy_is_verified_before_pacman_and_always_cleaned(
    tmp_path, monkeypatch, failure
):
    import hashlib
    import subprocess

    data = b"reviewed package bytes"
    digest = hashlib.sha256(data).hexdigest()
    monkeypatch.setattr(plugin, "ARTIFACT_SIZE", len(data))
    monkeypatch.setattr(plugin, "ARTIFACT_SHA256", digest)
    monkeypatch.setattr(plugin, "fetch_artifact", lambda target: target.write(data))
    calls = []
    root = "/var/tmp/t480fingerprint.ABCDE12345"

    def process(args, **kwargs):
        calls.append(args)
        if args[1] == "/usr/bin/mktemp":
            return subprocess.CompletedProcess(args, 0, root + "\n")
        if args[1] == "/usr/bin/sha256sum":
            return subprocess.CompletedProcess(
                args,
                0,
                ("0" * 64 if failure == "checksum" else digest)
                + "  "
                + root
                + "/driver.pkg.tar.zst\n",
            )
        if args[1] == "/usr/bin/install":
            # The source is an open descriptor, containing exactly the verified bytes.
            assert Path(args[-2]).read_bytes() == data
            if failure == "copy":
                raise subprocess.CalledProcessError(1, args)
        if args[1] == "/usr/bin/pacman" and failure == "pacman":
            raise subprocess.CalledProcessError(1, args)
        return subprocess.CompletedProcess(args, 0, "")

    monkeypatch.setattr(plugin.subprocess, "run", process)
    if failure:
        with pytest.raises((ValueError, subprocess.CalledProcessError)):
            plugin.install()
    else:
        plugin.install()
    operations = [args[1] for args in calls]
    assert operations[-2:] == ["/usr/bin/rm", "/usr/bin/rmdir"]
    if failure in ("copy", "checksum"):
        assert "/usr/bin/pacman" not in operations
    else:
        assert operations.index("/usr/bin/sha256sum") < operations.index(
            "/usr/bin/pacman"
        )
    assert all(
        "omarchy" not in " ".join(args) and "git" not in args and "bash" not in args
        for args in calls
    )


def test_download_failure_never_requests_privileges(monkeypatch):
    import subprocess

    def fail(target):
        raise subprocess.TimeoutExpired("curl", 130)

    monkeypatch.setattr(plugin, "fetch_artifact", fail)
    monkeypatch.setattr(
        plugin.subprocess, "run", lambda *a, **kw: pytest.fail("unexpected subprocess")
    )
    with pytest.raises(subprocess.TimeoutExpired):
        plugin.install()


def test_test_dependencies_are_version_and_hash_locked():
    import tomllib

    root = Path(__file__).resolve().parents[1]
    project = tomllib.loads((root / "pyproject.toml").read_text())
    lock = tomllib.loads((root / "uv.lock").read_text())
    assert all(
        "==" in requirement for requirement in project["dependency-groups"]["dev"]
    )
    packages = {package["name"]: package for package in lock["package"]}
    assert {"pytest", "ruff"} <= packages.keys()
    for package in packages.values():
        if "registry" not in package["source"]:
            continue
        artifacts = package.get("wheels", []) + [package["sdist"]]
        assert artifacts
        assert all(
            artifact["hash"].startswith("sha256:") and len(artifact["hash"]) == 71
            for artifact in artifacts
        )


def test_download_has_kernel_byte_ceiling_even_if_transport_ignores_size(monkeypatch):
    import subprocess
    import tempfile

    original_run = subprocess.run
    monkeypatch.setattr(plugin, "ARTIFACT_SIZE", 100)

    def ignoring_transport(args, **kwargs):
        # Preserve the production resource limiter but replace the network client
        # with a producer that ignores Content-Length and writes too many bytes.
        command = args[: args.index("/usr/bin/curl")] + [
            "/usr/bin/python3",
            "-I",
            "-c",
            "import os; os.write(1, b'x' * 1000); os.write(1, b'x')",
        ]
        return original_run(command, **kwargs)

    monkeypatch.setattr(plugin.subprocess, "run", ignoring_transport)
    with tempfile.TemporaryFile() as target:
        with pytest.raises(subprocess.CalledProcessError):
            plugin.fetch_artifact(target)
        assert target.seek(0, 2) <= 101
