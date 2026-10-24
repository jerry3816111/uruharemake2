"""Current entry must add the repair without changing frozen product entries."""

from pathlib import Path

import p4_status_truth_safe_isolated_product_launcher as launcher
import p4_status_truth_isolated_safari_probe as safari_probe


ROOT = Path(__file__).resolve().parent


def test_current_entry_layers_after_p4_az_and_reuses_its_runtime():
    source = (ROOT / "uruha_web_ui_product_p4_status_truth.py").read_text(
        encoding="utf-8"
    )
    assert "import uruha_web_ui_product_p4_az as _prior" in source
    assert "install_product_tool_failure_truth_p4(_base)" in source
    assert source.index("import uruha_web_ui_product_p4_az as _prior") < source.index(
        "install_product_tool_failure_truth_p4(_base)"
    )
    assert "RUNTIME = _prior.RUNTIME" in source
    assert launcher.ENTRYPOINT == ROOT / "uruha_web_ui_product_p4_status_truth.py"


def test_preflight_reuses_prior_isolation_and_probes_new_entry(monkeypatch, tmp_path):
    runtime_root = tmp_path / "runtime"
    profile = tmp_path / "profile.sb"
    before = {"python": "/isolate/python", "port": 7892, "entrypoint": "old"}
    seen = {}

    def fake_prior(**kwargs):
        seen["kwargs"] = kwargs
        return before, {"ISOLATED": "1"}, {"runtime_root": runtime_root}, False, profile

    def fake_probe(python, env, sandbox_profile):
        seen["probe"] = (python, env, sandbox_profile)
        return {"ok": True, "runtime_reused": True, "overlay_installed": True, "demo_builder": True}

    monkeypatch.setattr(launcher.prior, "preflight_p4_az", fake_prior)
    monkeypatch.setattr(launcher, "_probe_current_entry", fake_probe)
    summary, env, layout, created, actual_profile = launcher.preflight_status_truth(
        python_arg="/isolate/python", runtime_root_arg=str(runtime_root),
        reuse_runtime=True, port=7892, prewarm=False,
    )
    assert seen["kwargs"]["port"] == 7892
    assert seen["probe"] == (Path("/isolate/python"), env, profile)
    assert summary["entrypoint"] == str(launcher.ENTRYPOINT)
    assert summary["sandboxed_status_truth_probe"]["overlay_installed"] is True
    assert layout["runtime_root"] == runtime_root
    assert created is False
    assert actual_profile == profile


def test_one_off_safari_probe_is_status_only_and_denies_real_status_reader():
    compile(safari_probe.CHILD_CODE, "p4_status_truth_probe_child", "exec")
    assert "core.classify_runtime_status_request" in safari_probe.CHILD_CODE
    assert "diagnostic_status_only" in safari_probe.CHILD_CODE
    assert "product._PROVIDER_FACTORY = InvalidToolProvider" in safari_probe.CHILD_CODE
    assert "product.read_product_runtime_status = reject_status_reader" in safari_probe.CHILD_CODE
