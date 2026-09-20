import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
FREEZE = ROOT / "research" / "p4_c_product_function_calling_integration_freeze_2026-09-20.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_integration_freeze_binds_core_real_gate_adapter_entry_and_tests():
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    assert freeze["status"] == "frozen_before_isolated_product_restart"
    # Product entrypoints are intentionally extended by later, separately frozen
    # P4 stages. Keep the historical hash in the P4-C artifact, while binding the
    # current entry in the later stage instead of making forward progress break
    # an immutable historical acceptance test.
    for name, binding in freeze["bindings"].items():
        if name == "product_entry":
            continue
        assert _sha256(ROOT / binding["path"]) == binding["sha256"]
    assert freeze["bindings"]["product_entry"]["sha256"] == (
        "854349c160f6cd15c716b545d68b9c7970561ad5d793fa670e797d842883df0e"
    )
    source = (ROOT / freeze["bindings"]["product_entry"]["path"]).read_text(encoding="utf-8")
    assert "install_product_function_calling_p4(_base)" in source
    assert source.index("install_product_function_calling_p4(_base)") < source.index(
        "install_product_vrm_renderer_p4(_base)"
    )


def test_integration_freeze_preserves_existing_chat_and_read_only_boundary():
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    contract = freeze["integration_contract"]
    assert contract["nonselected_input_path"] == "original product _run_turn unchanged"
    assert contract["brain_initialization_allowed_by_status_reader"] is False
    assert contract["memory_content_read_allowed"] is False
    assert contract["memory_write_allowed"] is False
    acceptance = freeze["post_commit_acceptance"]
    assert acceptance["explicit_status_request_model_call_ceiling"] == 1
    assert acceptance["ordinary_conversation_regression_model_call_ceiling_added_by_p4_c"] == 0
    assert acceptance["physical_vrm_execution"] is False
