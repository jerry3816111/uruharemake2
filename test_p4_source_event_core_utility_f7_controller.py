"""f7 child-only opt-in scope; no provider or Web start."""

from __future__ import annotations

import pytest

import p4_direct_reply_act_m29_priority_detached_control as controller


def test_f7_flag_reaches_only_control_product_child_with_compact_schema(monkeypatch, tmp_path):
    layout = {
        "runtime_root": tmp_path,
        "memory_db": tmp_path / "memory_db",
        "session_db": tmp_path / "session_db",
        "web_logs": tmp_path / "web_logs",
        "jsonl_log": tmp_path / "web_logs/conversation.jsonl",
        "text_log": tmp_path / "web_logs/conversation.txt",
    }
    observed = []

    def preflight(**kwargs):
        observed.append(("preflight_input", dict(kwargs["environ"])))
        return {}, dict(kwargs["environ"]), layout, False, None

    def no_launch(argv):
        base = controller.launchd._isolated_env(layout, port=None)
        child = controller.launchd._isolated_env(layout, port=7934)
        if argv[0] == "start" and "product" in argv:
            _, final, _, _, _ = controller.product_launcher.preflight_preference_fallback(
                environ=base, prewarm=False
            )
            observed.append(("start", base, child, final))
        else:
            observed.append(("other", base, child, None))
        return 0

    monkeypatch.setattr(controller.product_launcher, "preflight_preference_fallback", preflight)
    monkeypatch.setattr(controller.prior.base_controller, "main", no_launch)
    monkeypatch.setenv("URUHA_P4_SOURCE_EVENT_CORE_UTILITY", "1")
    assert controller.main(["prepare"]) == 0
    assert "URUHA_P4_SOURCE_EVENT_CORE_UTILITY" not in observed[-1][2]
    assert controller.main(["--compact-json-schema", "start", "--mode", "product"]) == 0
    assert "URUHA_P4_SOURCE_EVENT_CORE_UTILITY" not in observed[-1][2]

    assert controller.main([
        "--source-event-core-utility", "--compact-json-schema", "--direct-act-arm", "control",
        "--product-port", "7934", "start", "--mode", "product",
    ]) == 0
    _, base, child, final = observed[-1]
    assert "URUHA_P4_SOURCE_EVENT_CORE_UTILITY" not in base
    assert child["URUHA_P4_SOURCE_EVENT_CORE_UTILITY"] == "1"
    assert final["URUHA_P4_SOURCE_EVENT_CORE_UTILITY"] == "1"
    assert child["URUHA_P4_DIRECT_REPLY_ACT_HANDOFF_ARM"] == "control"
    assert child["URUHA_P4_COMPACT_JSON_SCHEMA"] == "1"
    for rejected in (
        ["--source-event-core-utility", "prepare"],
        ["--source-event-core-utility", "start", "--mode", "inert"],
        ["--source-event-core-utility", "start", "--mode", "product"],
        ["--source-event-core-utility", "--compact-json-schema", "--direct-act-arm", "treatment", "start", "--mode", "product"],
    ):
        before = len(observed)
        with pytest.raises(SystemExit):
            controller.main(rejected)
        assert len(observed) == before
