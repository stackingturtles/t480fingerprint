"""Unprivileged setup failure tests and real Linux-PAM control-flow tests."""

import ctypes
import importlib.util
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("sudo_auth", REPO / "tools/sudo-auth.py")
auth = importlib.util.module_from_spec(spec)
spec.loader.exec_module(auth)
ORIGINAL = "#%PAM-1.0\nauth include system-auth\naccount include system-auth\n"


def test_policy_preserves_password_and_rollback():
    enabled = auth.pam_content(ORIGINAL, True)
    assert auth.pam_content(enabled, True) == enabled
    assert (
        auth.pam_content(enabled + "# later admin edit\n", False)
        == ORIGINAL + "# later admin edit\n"
    )
    with pytest.raises(ValueError):
        auth.pam_content("auth required pam_deny.so\n", True)
    with pytest.raises(ValueError):
        auth.pam_content(enabled.replace("timeout=10", "timeout=20"), False)


@pytest.mark.parametrize("enabled", [False, True])
def test_prepare_does_not_change_sudo(tmp_path, monkeypatch, enabled):
    import getpass

    pam = tmp_path / "sudo"
    original = auth.pam_content(ORIGINAL, True) if enabled else ORIGINAL
    pam.write_text(original)
    monkeypatch.setattr(auth, "PAM", pam)
    monkeypatch.setattr(auth, "prepare_driver", lambda: None)
    calls = []

    def run(command, *args, **kwargs):
        calls.append(command)
        return ""

    monkeypatch.setattr(auth, "run", run)
    auth.setup(getpass.getuser(), "right-index-finger", enable_sudo=False)
    assert pam.read_text() == original
    assert calls == [
        "/usr/bin/fprintd-list",
        "/usr/bin/fprintd-enroll",
        "/usr/bin/fprintd-verify",
    ]


@pytest.mark.parametrize("fail_at", ["enroll", "verify", "timeout", None])
@pytest.mark.parametrize("existing", [False, True])
def test_setup_requires_successful_verification(
    tmp_path, monkeypatch, fail_at, existing
):
    pam = tmp_path / "sudo"
    pam.write_text(ORIGINAL)
    monkeypatch.setattr(auth, "PAM", pam)
    monkeypatch.setattr(auth, "BACKUPS", tmp_path / "backups")
    monkeypatch.setattr(auth, "prepare_driver", lambda: None)
    calls = []

    def run(command, *args, **kwargs):
        calls.append(command)
        if command == "/usr/bin/fprintd-list":
            return (
                " - #0: right-index-finger\n" if existing else "No fingers enrolled\n"
            )
        if command == f"/usr/bin/fprintd-{fail_at}":
            raise subprocess.CalledProcessError(1, command)
        if fail_at == "timeout" and command == "/usr/bin/fprintd-verify":
            raise subprocess.TimeoutExpired(command, 30)
        return ""

    monkeypatch.setattr(auth, "run", run)
    # Use an existing non-root account; no operation on that account occurs.
    import getpass

    failure = fail_at in ("verify", "timeout") or (fail_at == "enroll" and not existing)
    if failure:
        with pytest.raises(subprocess.SubprocessError):
            auth.setup(getpass.getuser(), "right-index-finger")
        assert pam.read_text() == ORIGINAL
    else:
        auth.setup(getpass.getuser(), "right-index-finger")
        assert pam.read_text() == auth.PAM_BLOCK + ORIGINAL
    assert ("/usr/bin/fprintd-enroll" in calls) != existing


@pytest.fixture
def pam_module(tmp_path):
    source = tmp_path / "module.c"
    source.write_text("""#include <security/pam_modules.h>
#include <stdio.h>
#include <stdlib.h>
int pam_sm_authenticate(pam_handle_t *p, int f, int n, const char **a) {
  if (n > 1) { FILE *out = fopen(a[1], "w"); if (!out) return PAM_SYSTEM_ERR;
    fputs("password path reached", out); fclose(out); }
  return n ? atoi(a[0]) : PAM_SYSTEM_ERR;
}
int pam_sm_setcred(pam_handle_t *p, int f, int n, const char **a) { return PAM_SUCCESS; }
""")
    module = tmp_path / "module.so"
    subprocess.run(
        ["cc", "-shared", "-fPIC", str(source), "-o", str(module)],
        check=True,
        timeout=30,
    )
    return module


@pytest.mark.parametrize("scan_status", [0, 7, 9, 11])
@pytest.mark.parametrize("password_status", [0, 7])
def test_real_pam_match_or_password_fallback(
    tmp_path, pam_module, scan_status, password_status
):
    """Linux-PAM, simulated scanner results: success, mismatch, unavailable, max tries."""
    marker = tmp_path / "password-reached"
    # Remove only the lid gate, tested separately below; retain generated controls.
    policy = auth.pam_content(ORIGINAL, True).replace(
        "auth [success=1 default=ignore] pam_exec.so quiet /usr/bin/omarchy-hw-laptop-closed\n",
        "",
    )
    policy = policy.replace(
        "pam_fprintd.so max-tries=1 timeout=10", f"{pam_module} {scan_status}"
    )
    (tmp_path / "sudo").write_text(policy)
    (tmp_path / "system-auth").write_text(
        f"auth required {pam_module} {password_status} {marker}\n"
    )
    status = authenticate(tmp_path)
    assert (status == 0) == (scan_status == 0 or password_status == 0)
    assert marker.exists() == (scan_status != 0)


def test_closed_lid_skips_scanner(tmp_path, pam_module):
    marker = tmp_path / "password-reached"
    scanner = tmp_path / "scanner-reached"
    policy = auth.pam_content(ORIGINAL, True).replace(
        "pam_exec.so quiet /usr/bin/omarchy-hw-laptop-closed", f"{pam_module} 0"
    )
    policy = policy.replace(
        "pam_fprintd.so max-tries=1 timeout=10", f"{pam_module} 0 {scanner}"
    )
    (tmp_path / "sudo").write_text(policy)
    (tmp_path / "system-auth").write_text(f"auth required {pam_module} 0 {marker}\n")
    assert authenticate(tmp_path) == 0
    assert marker.exists()
    assert not scanner.exists()


def authenticate(confdir):
    pam = ctypes.CDLL("libpam.so.0")

    # This test's modules do not converse; leave callback NULL intentionally.
    class Conversation(ctypes.Structure):
        _fields_ = [("conv", ctypes.c_void_p), ("appdata_ptr", ctypes.c_void_p)]

    handle = ctypes.c_void_p()
    pam.pam_start_confdir.argtypes = [
        ctypes.c_char_p,
        ctypes.c_char_p,
        ctypes.POINTER(Conversation),
        ctypes.c_char_p,
        ctypes.POINTER(ctypes.c_void_p),
    ]
    pam.pam_authenticate.argtypes = [ctypes.c_void_p, ctypes.c_int]
    pam.pam_end.argtypes = [ctypes.c_void_p, ctypes.c_int]
    assert (
        pam.pam_start_confdir(
            b"sudo",
            b"test",
            ctypes.byref(Conversation()),
            str(confdir).encode(),
            ctypes.byref(handle),
        )
        == 0
    )
    try:
        return pam.pam_authenticate(handle, 0)
    finally:
        pam.pam_end(handle, 0)
