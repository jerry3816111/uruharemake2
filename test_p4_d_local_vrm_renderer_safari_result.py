import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RESULT = ROOT / "analysis" / "p4_d_local_vrm_renderer_safari_result_2026-09-20.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_result_is_bound_to_contract_and_both_freezes():
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    assert result["status"] == "local_vrm_renderer_and_product_regressions_pass"
    for binding_name in ("contract", "implementation_freeze", "network_audit_repair_freeze"):
        binding = result["bindings"][binding_name]
        assert _sha256(ROOT / binding["path"]) == binding["sha256"]


def test_actual_safari_states_distinguish_waiting_success_and_failure():
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    assert result["initial_state"]["status"] == "waiting_for_local_vrm"
    assert result["initial_state"]["false_render_claim_count"] == 0
    valid = result["valid_local_fixture"]
    assert valid["status"] == "rendering_vrm"
    assert valid["canvas_model_visible"] is True
    assert set(valid["flow_nodes"].values()) == {"done"}
    assert valid["server_upload_count"] == 0
    assert valid["action_execution_count"] == 0
    invalid = result["invalid_local_fixture"]
    assert invalid["status"] == "load_failed"
    assert invalid["placeholder_restored"] is True
    assert invalid["vrm_parsed_node"] == "error"
    assert invalid["vrm_rendered_node"] == "idle"
    assert invalid["false_render_claim_count"] == 0


def test_no_renderer_authored_network_or_product_side_effect_is_claimed():
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    boundary = result["network_and_asset_boundary"]
    assert boundary["renderer_authored_remote_url_count"] == 0
    assert boundary["renderer_authored_fetch_or_xhr_count"] == 0
    assert boundary["loader_allowed_url_schemes"] == ["blob", "data"]
    assert boundary["whole_safari_network_capture_performed"] is False
    logs = result["conversation_log_isolation"]
    assert logs["rows_before_vrm_only_acceptance"] == logs["rows_after_valid_invalid_valid_vrm_sequence"]
    assert logs["vrm_only_added_conversation_rows"] == 0
    accounting = result["dependency_and_build_accounting"]
    assert accounting["p4_d_model_call_count"] == 0
    assert accounting["p4_d_tool_execution_count"] == 0
    assert accounting["paid_api_call_count"] == 0
    assert accounting["character_asset_download_count"] == 0


def test_status_tool_chat_and_claim_boundaries_remain_explicit():
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    status = result["status_tool_regression"]
    assert status["tool_execution_count"] == 1
    assert status["side_effect_count"] == 0
    assert status["function_trace_node_count"] == 5
    assert status["vrm_remained_visible"] is True
    chat = result["ordinary_chat_regression"]
    assert chat["selected_policy"] == "listen_presence"
    assert chat["negated_policy"] == "solve_regulation"
    assert chat["p4_d_added_model_call_count"] == 0
    assert chat["p4_d_added_tool_execution_count"] == 0
    assert chat["vrm_remained_visible"] is True
    assert result["remaining"]["vrm_action_policy_connection"] == "not_present"
    assert "does not establish an Uruha likeness" in result["claim_boundary"]
