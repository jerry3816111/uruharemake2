import json
import os
import stat
import subprocess
import tempfile
from pathlib import Path
from unittest import mock

import pytest

import p4_b_safe_isolated_product_launcher as p4b


ROOT = Path(__file__).resolve().parent
CONTRACT = ROOT / "configs" / "p4_b_safe_isolated_product_launcher_contract_v1.json"


def _executable(path: Path) -> Path:
    path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


def test_contract_freezes_single_change_and_forbidden_expansion():
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert contract["single_changed_variable"] == "add_safe_isolated_product_launcher"
    assert contract["required_behavior"]["host_exact"] == "127.0.0.1"
    assert contract["forbidden_behavior"]["production_memory_default"] is True
    assert contract["forbidden_behavior"]["brain_prompt_research_vrm_or_function_calling_change"] is True
    assert contract["offline_acceptance"]["model_call_count"] == 0
    assert contract["offline_acceptance"]["runtime_server_start_count"] == 0


def test_explicit_python_precedes_environment_and_fallback():
    with tempfile.TemporaryDirectory() as temporary:
        base = Path(temporary)
        explicit = _executable(base / "explicit-python")
        environment = _executable(base / "environment-python")
        root = base / "repo"
        root.mkdir()
        resolved = p4b.resolve_python(
            str(explicit), {"URUHA_PRODUCT_PYTHON": str(environment)}, root=root
        )
        assert resolved == explicit.absolute()


def test_python_resolution_preserves_venv_symlink_path():
    with tempfile.TemporaryDirectory() as temporary:
        base = Path(temporary)
        underlying = _executable(base / "python3.12")
        venv = base / "venv"
        (venv / "bin").mkdir(parents=True)
        link = venv / "bin" / "python"
        link.symlink_to(underlying)
        resolved = p4b.resolve_python(str(link), {}, root=base / "unused")
        assert resolved == link.absolute()
        assert resolved != underlying.resolve()


def test_missing_or_nonexecutable_python_fails_closed():
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary) / "worktrees" / "safe"
        root.mkdir(parents=True)
        missing = root / "missing-python"
        with pytest.raises(p4b.LauncherError, match="no_executable_product_python"):
            p4b.resolve_python(str(missing), {}, root=root)


@pytest.mark.parametrize("port", [0, 80, 1023, 65536, 99999])
def test_invalid_port_fails_closed(port):
    with pytest.raises(p4b.LauncherError, match="invalid_port"):
        p4b.validate_port(port)


def test_fresh_runtime_root_is_private_and_layout_is_disjoint():
    with tempfile.TemporaryDirectory() as temporary:
        parent = Path(temporary).resolve()
        runtime_root, created = p4b.prepare_runtime_root(
            None, reuse=False, temporary_parent=parent
        )
        try:
            layout = p4b.build_runtime_layout(runtime_root)
            assert created is True
            assert stat.S_IMODE(runtime_root.stat().st_mode) == 0o700
            assert p4b._valid_launcher_root(runtime_root) is True
            values = [layout[key] for key in ("memory_db", "session_db", "web_logs")]
            assert len({value.resolve() for value in values}) == 3
            assert all(stat.S_IMODE(value.stat().st_mode) == 0o700 for value in values)
            assert all(p4b._within(value.resolve(), parent) for value in values)
        finally:
            import shutil

            shutil.rmtree(runtime_root, ignore_errors=True)


def test_existing_root_requires_explicit_reuse_and_launcher_manifest():
    with tempfile.TemporaryDirectory() as temporary:
        parent = Path(temporary).resolve()
        unmarked = parent / "unmarked"
        unmarked.mkdir()
        with pytest.raises(p4b.LauncherError, match="requires_reuse"):
            p4b.prepare_runtime_root(str(unmarked), reuse=False, temporary_parent=parent)
        with pytest.raises(p4b.LauncherError, match="not_launcher_owned"):
            p4b.prepare_runtime_root(str(unmarked), reuse=True, temporary_parent=parent)

        marked = parent / "marked"
        marked.mkdir(mode=0o700)
        p4b._write_manifest(marked)
        reused, created = p4b.prepare_runtime_root(
            str(marked), reuse=True, temporary_parent=parent
        )
        assert reused == marked
        assert created is False


def test_runtime_root_outside_temporary_parent_is_rejected():
    with tempfile.TemporaryDirectory() as temporary, tempfile.TemporaryDirectory() as other:
        with pytest.raises(p4b.LauncherError, match="outside_temporary_parent"):
            p4b.prepare_runtime_root(
                str(Path(other) / "runtime"),
                reuse=False,
                temporary_parent=Path(temporary),
            )


def test_child_environment_forces_localhost_isolation_and_guards():
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        p4b._write_manifest(root)
        layout = p4b.build_runtime_layout(root)
        env = p4b.child_environment(
            {
                "PYTHONPATH": "unsafe",
                "URUHA_WEB_HOST": "0.0.0.0",
                "URUHA_IDLE_VISIBLE_PROACTIVE_ENABLED": "true",
            },
            layout,
            port=7860,
            prewarm=False,
        )
        assert env["URUHA_WEB_HOST"] == "127.0.0.1"
        assert env["URUHA_WEB_PORT"] == "7860"
        assert env["URUHA_MEMORY_DB_PATH"] == str(layout["memory_db"])
        assert env["URUHA_WEB_SESSION_DB_PATH"] == str(layout["session_db"])
        assert env["URUHA_IDLE_VISIBLE_PROACTIVE_ENABLED"] == "false"
        assert env["URUHA_SKIP_AUTO_VENV"] == "1"
        assert env["GRADIO_ANALYTICS_ENABLED"] == "False"
        assert env["URUHA_WEB_PREWARM_BRAIN"] == "0"
        assert "PYTHONPATH" not in env


def test_dependency_probe_failure_fails_closed_without_raw_output():
    completed = subprocess.CompletedProcess(
        args=["python"], returncode=1, stdout="private stdout", stderr="private stderr"
    )
    with mock.patch.object(p4b.subprocess, "run", return_value=completed):
        with pytest.raises(p4b.LauncherError) as caught:
            p4b.probe_python(Path("/fake/python"), {}, root=ROOT)
    assert "returncode=1" in str(caught.value)
    assert "private" not in str(caught.value)


def test_preflight_probe_failure_removes_new_runtime_root():
    with tempfile.TemporaryDirectory() as temporary:
        parent = Path(temporary).resolve()
        fake_python = _executable(parent / "python")
        with mock.patch.object(
            p4b, "probe_python", side_effect=p4b.LauncherError("probe_failed")
        ):
            with pytest.raises(p4b.LauncherError, match="probe_failed"):
                p4b.preflight(
                    python_arg=str(fake_python),
                    runtime_root_arg=None,
                    reuse_runtime=False,
                    port=7860,
                    prewarm=False,
                    environ={},
                    temporary_parent=parent,
                )
        assert sorted(parent.iterdir()) == [fake_python]


def test_check_mode_never_starts_server_and_cleans_created_root():
    with tempfile.TemporaryDirectory() as temporary:
        runtime_root = Path(temporary) / "runtime"
        runtime_root.mkdir(mode=0o700)
        p4b._write_manifest(runtime_root)
        layout = p4b.build_runtime_layout(runtime_root)
        summary = {
            "status": "ready",
            "python": "/fake/python",
            "entrypoint": str(p4b.ENTRYPOINT),
            "host": "127.0.0.1",
            "port": 7860,
            "runtime_root": str(runtime_root),
            "server_started": False,
        }
        with mock.patch.object(
            p4b, "preflight", return_value=(summary, {}, layout, True)
        ), mock.patch.object(p4b.subprocess, "Popen") as popen:
            assert p4b.main(["check"]) == 0
        popen.assert_not_called()
        assert not runtime_root.exists()
