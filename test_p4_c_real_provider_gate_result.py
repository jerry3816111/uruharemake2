import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RESULT = ROOT / "analysis" / "p4_c_real_provider_gate_result_2026-09-20.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_result_is_bound_to_pre_call_freeze():
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    binding = result["freeze_binding"]
    assert _sha256(ROOT / binding["path"]) == binding["sha256"]
    assert result["status"] == "real_positive_call_and_zero_call_negative_guards_pass"


def test_result_preserves_exact_call_and_cost_evidence():
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    positive = result["positive"]
    assert positive["model_call_count"] == 1
    assert positive["retry_count"] == 0
    assert positive["prompt_tokens"] == 310
    assert positive["completion_tokens"] == 15
    assert positive["tool_call_count"] == 1
    assert positive["tool_name"] == "get_runtime_status"
    assert positive["tool_arguments"] == {}
    assert positive["production_runtime_read_count"] == 0
    assert positive["trace_labels"] == [
        "function_request_p4_c",
        "function_model_decision_p4_c",
        "function_validated_call_p4_c",
        "function_tool_result_p4_c",
        "function_surface_p4_c",
    ]


def test_negative_guards_and_claim_boundary_remain_explicit():
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    assert result["negative_guards"]["case_count"] == 6
    assert result["negative_guards"]["provider_call_count"] == 0
    assert result["negative_guards"]["tool_execution_count"] == 0
    assert result["access_accounting"]["external_network_call_count"] == 0
    assert result["next_gate"]["isolated_safari_acceptance_required"] is True
    assert "not live product state" in result["claim_boundary"]

