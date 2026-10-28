"""New first-step entry adds only a route overlay after frozen product entry."""

from pathlib import Path
import subprocess

import pytest

import p4_first_step_route_safe_isolated_product_launcher as launcher


ROOT = Path(__file__).resolve().parent


def test_entry_layers_after_frozen_status_truth_entry():
    source = (ROOT / "uruha_web_ui_product_p4_first_step_route.py").read_text(
        encoding="utf-8"
    )
    assert "import uruha_web_ui_product_p4_status_truth as _prior" in source
    assert "install_explicit_first_step_route_p4()" in source
    assert source.index("import uruha_web_ui_product_p4_status_truth") < source.index(
        "install_explicit_first_step_route_p4()"
    )
    assert "RUNTIME = _prior.RUNTIME" in source
    assert launcher.ENTRYPOINT == ROOT / "uruha_web_ui_product_p4_first_step_route.py"


def test_new_preflight_reuses_old_sandbox_and_adds_new_entry_probe(monkeypatch, tmp_path):
    profile = tmp_path / "profile.sb"
    runtime_root = tmp_path / "runtime"
    before = {"python": "/isolated/python", "port": 7897, "entrypoint": "old"}
    seen = {}

    def fake_prior(**kwargs):
        seen["kwargs"] = kwargs
        return before, {"ISOLATED": "1"}, {"runtime_root": runtime_root}, False, profile

    def fake_probe(python, env, actual_profile):
        seen["probe"] = (python, env, actual_profile)
        return {"ok": True, "runtime_reused": True, "overlay_installed": True,
                "demo_builder": True}

    monkeypatch.setattr(launcher.prior, "preflight_status_truth", fake_prior)
    monkeypatch.setattr(launcher, "_probe_first_step", fake_probe)
    summary, env, layout, created, actual_profile = launcher.preflight_first_step(
        python_arg="/isolated/python", runtime_root_arg=str(runtime_root),
        reuse_runtime=True, port=7897, prewarm=False,
    )
    assert seen["kwargs"]["port"] == 7897
    assert seen["probe"] == (Path("/isolated/python"), env, profile)
    assert summary["entrypoint"] == str(launcher.ENTRYPOINT)
    assert summary["sandboxed_first_step_probe"]["overlay_installed"] is True
    assert layout["runtime_root"] == runtime_root
    assert created is False
    assert actual_profile == profile


def test_new_sandbox_probe_fails_closed_without_printing_private_output(monkeypatch):
    completed = subprocess.CompletedProcess(
        args=["sandbox-exec"], returncode=1, stdout="private", stderr="private"
    )
    monkeypatch.setattr(launcher.prior.sandbox, "sandbox_command", lambda *_: ["sandbox-exec"])
    monkeypatch.setattr(launcher.subprocess, "run", lambda *_args, **_kwargs: completed)
    with pytest.raises(launcher.prior.base_launcher.LauncherError) as caught:
        launcher._probe_first_step(Path("/isolated/python"), {}, Path("/fake/profile"))
    assert "returncode=1" in str(caught.value)
    assert "private" not in str(caught.value)
