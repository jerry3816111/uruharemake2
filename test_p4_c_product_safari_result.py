import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RESULT = ROOT / "analysis" / "p4_c_product_function_calling_safari_result_2026-09-20.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_result_is_bound_to_product_integration_freeze():
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    binding = result["freeze_binding"]
    assert _sha256(ROOT / binding["path"]) == binding["sha256"]
    assert result["status"] == "product_read_only_function_calling_and_chat_regression_pass"


def test_real_status_turn_is_single_call_read_only_and_visible_in_graph():
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    turn = result["status_turn"]
    assert turn["model_call_count"] == 1
    assert turn["tool_execution_count"] == 1
    assert turn["side_effect_count"] == 0
    assert turn["memory_content_read_count"] == 0
    assert turn["brain_initialization_count"] == 0
    assert turn["function_trace_labels"] == [
        "function_request_p4_c",
        "function_model_decision_p4_c",
        "function_validated_call_p4_c",
        "function_tool_result_p4_c",
        "function_surface_p4_c",
    ]
    assert turn["observed_live_values"]["brain_loaded"] is False
    assert turn["observed_live_values"]["turn_count"] == 0
    assert turn["observed_live_values"]["memory_isolation"] == "isolated"
    assert turn["latency_target_met"] is True


def test_ordinary_chat_idle_and_claim_boundaries_are_preserved():
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    chat = result["ordinary_chat_regression_turn"]
    assert chat["selected_policy"] == "listen_presence"
    assert chat["negated_policy"] == "solve_regulation"
    assert chat["p4_c_added_model_call_count"] == 0
    assert chat["tool_execution_count"] == 0
    assert chat["function_trace_node_count"] == 0
    assert result["idle_guard"]["new_visible_idle_prompt_count"] == 0
    assert result["call_accounting"]["retry_count"] == 0
    assert result["call_accounting"]["paid_api_call_count"] == 0
    assert result["call_accounting"]["physical_vrm_action_count"] == 0
    assert result["remaining"]["vrm_3d"] == "not_present"
    assert "does not establish general Function Calling" in result["claim_boundary"]
