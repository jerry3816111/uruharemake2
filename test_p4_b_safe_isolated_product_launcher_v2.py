import os
import stat
import subprocess
import tempfile
from pathlib import Path
from unittest import mock

import pytest

import p4_b_safe_isolated_product_launcher as v1
import p4_b_safe_isolated_product_launcher_v2 as v2


def test_profile_denies_each_protected_root_and_uses_default_allow():
    roots = [Path("/tmp/safe-worktree"), Path("/tmp/original-checkout")]
    profile = v2.sandbox_profile_text(roots)
    assert "(allow default)" in profile
    for root in roots:
        assert f'(deny file-write* (subpath "{root.resolve()}"))' in profile


def test_profile_is_private_and_inside_isolated_runtime():
    with tempfile.TemporaryDirectory() as temporary:
        runtime = Path(temporary)
        profile = v2.write_sandbox_profile(
            runtime, protected_roots=[runtime / "protected"]
        )
        assert profile.parent == runtime
        assert stat.S_IMODE(profile.stat().st_mode) == 0o600


@pytest.mark.skipif(not v2.SANDBOX_EXEC.is_file(), reason="macOS sandbox-exec unavailable")
def test_sandbox_denies_protected_write_but_allows_runtime_write():
    with tempfile.TemporaryDirectory() as temporary:
        base = Path(temporary)
        protected = base / "protected"
        runtime = base / "runtime"
        protected.mkdir()
        runtime.mkdir()
        profile = v2.write_sandbox_profile(runtime, protected_roots=[protected])
        denied = protected / "must-not-exist"
        allowed = runtime / "allowed"
        denied_run = subprocess.run(
            v2.sandbox_command(profile, ["/usr/bin/touch", str(denied)]),
            check=False,
            capture_output=True,
        )
        allowed_run = subprocess.run(
            v2.sandbox_command(profile, ["/usr/bin/touch", str(allowed)]),
            check=False,
            capture_output=True,
        )
        assert denied_run.returncode != 0
        assert not denied.exists()
        assert allowed_run.returncode == 0
        assert allowed.is_file()


def test_sandboxed_probe_failure_is_redacted_and_fails_closed():
    completed = subprocess.CompletedProcess(
        args=["sandbox-exec"], returncode=1, stdout="private", stderr="private"
    )
    with mock.patch.object(v2.subprocess, "run", return_value=completed):
        with pytest.raises(v1.LauncherError) as caught:
            v2.sandboxed_probe(Path("/fake/python"), {}, Path("/fake/profile"))
    assert "returncode=1" in str(caught.value)
    assert "private" not in str(caught.value)


def test_v2_preflight_adds_bytecode_guard_and_sandbox_evidence():
    with tempfile.TemporaryDirectory() as temporary:
        runtime = Path(temporary) / "runtime"
        runtime.mkdir(mode=0o700)
        v1._write_manifest(runtime)
        layout = v1.build_runtime_layout(runtime)
        summary = {
            "schema": "v1",
            "python": "/fake/python",
            "port": 7860,
            "server_started": False,
        }
        with mock.patch.object(
            v2.v1, "preflight", return_value=(summary, {}, layout, False)
        ), mock.patch.object(
            v2, "sandboxed_probe", return_value={"ok": True, "demo_builder": True}
        ):
            result, env, _, created, profile = v2.preflight_v2(
                python_arg=None,
                runtime_root_arg=str(runtime),
                reuse_runtime=True,
                port=7860,
                prewarm=False,
            )
        assert created is False
        assert env["PYTHONDONTWRITEBYTECODE"] == "1"
        assert env["URUHA_PRODUCT_WRITE_SANDBOX"] == "1"
        assert result["sandbox"]["enabled"] is True
        assert result["sandbox"]["profile_mode"] == "0o600"
        assert profile.is_file()


def test_v2_check_mode_never_starts_server_and_cleans_created_root():
    with tempfile.TemporaryDirectory() as temporary:
        runtime = Path(temporary) / "runtime"
        runtime.mkdir(mode=0o700)
        v1._write_manifest(runtime)
        layout = v1.build_runtime_layout(runtime)
        profile = v2.write_sandbox_profile(runtime, protected_roots=[Path(temporary) / "protected"])
        summary = {
            "schema": "v2",
            "status": "ready",
            "python": "/fake/python",
            "port": 7860,
            "server_started": False,
        }
        with mock.patch.object(
            v2, "preflight_v2", return_value=(summary, {}, layout, True, profile)
        ), mock.patch.object(v2.subprocess, "Popen") as popen:
            assert v2.main(["check"]) == 0
        popen.assert_not_called()
        assert not runtime.exists()
