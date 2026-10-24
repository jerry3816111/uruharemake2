import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
AMENDMENT = ROOT / "configs" / "p4_t_additive_product_entry_amendment_v1.json"
PRODUCT = ROOT / "uruha_web_ui_product.py"


def _sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def test_amendment_preserves_failure_and_released_product_entry():
    amendment = json.loads(AMENDMENT.read_text(encoding="utf-8"))
    assert amendment["status"] == "frozen_before_second_and_final_integration_attempt"
    assert amendment["preserved_failure"]["affected_suite_passed"] == 174
    assert amendment["preserved_failure"]["affected_suite_failed"] == 5
    assert _sha256(PRODUCT) == amendment["preserved_failure"]["required_released_product_entry_sha256"]
    assert amendment["failure_policy"]["this_is_final_informed_correction_batch"] is True
    assert "uruha_web_ui_product.py" in amendment["forbidden_changes"]
    assert "uruha_web_ui_product_p4_t.py" in amendment["allowed_second_attempt_files"]
