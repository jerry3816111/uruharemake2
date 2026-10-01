import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
FREEZE = ROOT / "research" / "p4_b_safe_launcher_sandbox_repair_freeze_2026-09-20.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_repair_freeze_preserves_failure_and_binds_v2():
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    assert freeze["status"] == "frozen_before_only_sandboxed_real_rerun"
    assert freeze["preserves"]["first_real_launch_acceptance"] == "failed_product_child_not_fully_write_isolated"
    for binding in freeze["bindings"].values():
        path = ROOT / binding["path"]
        assert path.is_file()
        assert _sha256(path) == binding["sha256"]
    assert freeze["offline_gate"]["affected_test_pass_count"] == 24


def test_repair_freeze_allows_only_bounded_local_rerun():
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    rerun = freeze["rerun_contract"]
    assert rerun["reuse_runtime"] is True
    assert rerun["host"] == "127.0.0.1"
    assert rerun["port"] == 7860
    assert rerun["prewarm"] is False
    assert rerun["automatic_retry"] is False
    assert rerun["chat_turn_before_sandbox_visibility_check"] is False
