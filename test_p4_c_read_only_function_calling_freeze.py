import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
FREEZE = ROOT / "research" / "p4_c_read_only_function_calling_implementation_freeze_2026-09-20.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_freeze_binds_contract_implementation_tests_and_offline_result():
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    assert freeze["status"] == "frozen_before_any_p4_c_real_model_call"
    for binding in freeze["frozen_artifacts"].values():
        path = ROOT / binding["path"]
        assert path.is_file()
        assert _sha256(path) == binding["sha256"]


def test_freeze_keeps_real_execution_bounded_and_product_pending():
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    assert freeze["pre_freeze_accounting"]["p4_c_real_model_call_count"] == 0
    assert freeze["post_commit_authorization"]["one_positive_local_model_call"] is True
    assert freeze["post_commit_authorization"]["automatic_retry_or_fallback"] is False
    assert freeze["post_commit_authorization"]["product_integration_before_positive_pass"] is False
    assert freeze["post_commit_authorization"]["external_network_login_paid_api_or_vrm_execution"] is False

