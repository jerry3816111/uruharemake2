from pathlib import Path

from p3_private_scratch_tokenizer_probe import build_preflight, load_probe


ROOT = Path(__file__).resolve().parent
PROBE = ROOT / "configs/p3_private_scratch_tokenizer_binding_probe_v1.json"


def test_private_scratch_probe_is_two_shape_and_non_authorizing():
    probe = load_probe(PROBE)
    assert [row["stage"] for row in probe["fixtures"]] == ["critique", "revise"]
    for fixture in probe["fixtures"]:
        assert [row["role"] for row in fixture["messages"]] == [
            "system", "user", "user"
        ]
    assert probe["execution_boundary"]["provider_calls_exact"] == 2
    assert probe["execution_boundary"]["raw_output_retained"] is False
    assert probe["execution_boundary"]["real_model_calls_authorized_by_this_config"] is False


def test_private_scratch_preflight_has_exact_offline_shapes_and_zero_calls():
    result = build_preflight(PROBE)
    assert result["status"] == "ready_for_private_scratch_binding_review"
    assert {row["stage"] for row in result["rows"]} == {"critique", "revise"}
    assert all(row["offline_prompt_tokens"] > 0 for row in result["rows"])
    assert result["counter_evidence"]["adjacent_same_role_rule"] != "not_applied"
    assert result["real_model_calls"] == result["network_calls"] == 0
    assert result["developer_case_accessed"] == result["annotations_accessed"] == 0
    assert all(result["checks"].values())
