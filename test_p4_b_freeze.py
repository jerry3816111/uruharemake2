import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
FREEZE = ROOT / "research" / "p4_b_safe_isolated_product_launcher_implementation_freeze_2026-09-20.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_freeze_binds_exact_offline_passed_implementation():
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    assert freeze["status"] == "frozen_before_first_real_product_server_launch"
    for binding in freeze["bindings"].values():
        path = ROOT / binding["path"]
        assert path.is_file()
        assert _sha256(path) == binding["sha256"]
    assert freeze["offline_gate"]["focused_test_pass_count"] == 16
    assert freeze["offline_gate"]["actual_product_import_probe_passed"] is True
    assert freeze["offline_gate"]["server_start_count"] == 0


def test_freeze_limits_real_launch_and_preserves_missing_capabilities():
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    contract = freeze["real_launch_contract"]
    assert contract["host"] == "127.0.0.1"
    assert contract["prewarm"] is False
    assert contract["automatic_retry"] is False
    assert contract["public_share"] is False
    assert "function_calling_or_vrm_integration" in freeze["forbidden_changes_after_freeze"]
    assert "production_memory_access" in freeze["forbidden_changes_after_freeze"]
