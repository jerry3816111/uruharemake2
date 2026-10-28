import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RESULT = ROOT / "analysis" / "p4_o_safe_isolated_launcher_preflight_2026-09-22.json"


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_preflight_binds_launcher_and_reports_no_product_turn():
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    assert result["status"] == "ready"
    assert _sha256(ROOT / result["launcher"]["path"]) == result["launcher"]["sha256"]
    assert _sha256(ROOT / result["launcher_test"]["path"]) == result["launcher_test"]["sha256"]
    check = result["executed_check"]
    assert check["sandbox_enabled"] is True
    assert check["builder_module"] == "uruha_persisted_reference_time_p4"
    assert check["server_started"] is False
    assert check["model_call_count"] == 0
    assert check["safari_operation_count"] == 0
