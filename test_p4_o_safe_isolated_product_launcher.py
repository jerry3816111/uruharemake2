from pathlib import Path

import p4_o_safe_isolated_product_launcher as launcher


ROOT = Path(__file__).resolve().parent


def test_launcher_targets_only_new_p4_o_entry_and_keeps_v2_sandbox():
    assert launcher.ENTRYPOINT == ROOT / "uruha_web_ui_product_p4_o.py"
    source = (ROOT / "p4_o_safe_isolated_product_launcher.py").read_text(encoding="utf-8")
    assert "v2.preflight_v2" in source
    assert "v2.sandbox_command" in source
    assert "uruha_web_ui_product_p4_o" in source


def test_p4_o_probe_requires_new_builder_and_reused_runtime():
    source = (ROOT / "p4_o_safe_isolated_product_launcher.py").read_text(encoding="utf-8")
    assert 'payload.get("runtime_reused") is not True' in source
    assert 'payload.get("builder_module") != "uruha_persisted_reference_time_p4"' in source


def test_default_listener_does_not_collide_with_preserved_p4_n_server():
    args = launcher._parser().parse_args(["check"])
    assert args.port == 7867
