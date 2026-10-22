"""No-launch contracts for the additive compute-receipt product controller."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

import p4_preference_fallback_detached_control as base_controller
import p4_preference_fallback_launchd_control as launchd
import p4_reported_receipt_destination_compute_detached_control as compute_control
import p4_reported_receipt_destination_detached_control as latest_controller


ROOT = Path(__file__).resolve().parent
FROZEN_SHA256 = {
    "p4_preference_fallback_launchd_control.py": "48c6be526b10588c8c483d314a2cef2f14bf869600103bae8936558acb8b03a6",
    "p4_preference_fallback_detached_control.py": "a50c28867201afd164f031e0293c26708f7f2f34ba330455d4cc8b3adc13feca",
    "p4_reported_receipt_destination_detached_control.py": "e8ac14bcee3dd41e6c798bc299783617c027ed601ff1f128de1a2211ba575abf",
    "uruha_web_ui_product_p4_reported_receipt_destination.py": "6d5bcfb14e9d5e019d3f37e49d13da047d10396637afdae263ad2a88fec77cc0",
}


def _layout(tmp_path: Path) -> dict[str, Path]:
    return {
        "runtime_root": tmp_path,
        "memory_db": tmp_path / "memory_db",
        "session_db": tmp_path / "session_db",
        "web_logs": tmp_path / "web_logs",
        "jsonl_log": tmp_path / "web_logs" / "conversation.jsonl",
        "text_log": tmp_path / "web_logs" / "conversation.txt",
    }


def test_frozen_controllers_and_latest_entry_are_unchanged():
    for name, expected in FROZEN_SHA256.items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected
    assert compute_control.ENTRYPOINT == latest_controller.ENTRYPOINT
    assert latest_controller.base_controller is base_controller
    assert latest_controller.base_controller.start is base_controller.start
    assert latest_controller.base_controller.verify_ready is base_controller.verify_ready
    assert latest_controller.base_controller.stop is base_controller.stop


def test_both_preflight_and_product_env_gain_only_fixed_flag(tmp_path, monkeypatch):
    original = launchd._isolated_env
    entry_main = latest_controller.base_controller.main
    layout = _layout(tmp_path)
    observed = []

    def no_launch_main(argv):
        assert argv == ["start", "--mode", "product"]
        for port in (None, base_controller.PORT):
            env = launchd._isolated_env(layout, port=port)
            before = original(layout, port=port)
            assert env == {**before, "URUHA_WEB_COMPUTE_LEDGER": "1"}
            observed.append(port)
        # Exercise the real controller's allowlist expression without starting
        # its preflight/model process: the flag must survive to Popen's env.
        preflight_env = launchd._isolated_env(layout, port=None)
        launcher_env = launchd.base.child_environment(
            preflight_env, layout, port=base_controller.PORT, prewarm=False,
        )
        launcher_env["URUHA_PRODUCT_WRITE_SANDBOX"] = "1"  # v2 preflight addition
        final_env = {
            key: value for key, value in launcher_env.items()
            if key in set(launchd._isolated_env(layout, port=base_controller.PORT))
        }
        assert final_env["URUHA_WEB_COMPUTE_LEDGER"] == "1"
        assert final_env["URUHA_PRODUCT_WRITE_SANDBOX"] == "1"
        assert final_env["URUHA_WEB_PORT"] == str(base_controller.PORT)
        return 17

    monkeypatch.setattr(latest_controller.base_controller, "main", no_launch_main)
    try:
        assert compute_control.main(["start", "--mode", "product"]) == 17
    finally:
        monkeypatch.setattr(latest_controller.base_controller, "main", entry_main)
    assert observed == [None, base_controller.PORT]
    assert launchd._isolated_env is original


def test_original_environment_and_identity_functions_restore_on_failure(monkeypatch):
    original_env = launchd._isolated_env
    original_identity = base_controller._validated_stage
    original_ready = base_controller.verify_ready
    original_stop = base_controller.stop

    def fail_without_launch(argv):
        assert launchd._isolated_env is not original_env
        raise LookupError("synthetic_no_launch")

    monkeypatch.setattr(latest_controller.base_controller, "main", fail_without_launch)
    with pytest.raises(LookupError, match="synthetic_no_launch"):
        compute_control.main(["start"])
    assert launchd._isolated_env is original_env
    assert base_controller._validated_stage is original_identity
    assert base_controller.verify_ready is original_ready
    assert base_controller.stop is original_stop
