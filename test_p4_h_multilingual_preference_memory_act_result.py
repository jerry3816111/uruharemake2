import hashlib
import json
from pathlib import Path

import p4_h_preference_memory_act_gate as gate


ROOT = Path(__file__).resolve().parent
RESULT = ROOT / "analysis" / "p4_h_multilingual_preference_memory_act_result_2026-09-21.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load():
    return json.loads(RESULT.read_text(encoding="utf-8"))


def test_result_is_bound_to_freeze_and_recomputes_pass():
    result = _load()
    binding = result["freeze_binding"]
    assert _sha256(ROOT / binding["path"]) == binding["sha256"]
    recomputed = gate.evaluate_evidence(gate.load_contract(), result)
    assert recomputed == result["gate_evaluation"]
    assert result["status"] == "pass"


def test_both_turns_used_exact_zero_model_plan_and_surface_authority():
    result = _load()
    first, second = result["turns"]
    assert (first["input_language"], first["act"]) == ("en", "write")
    assert (second["input_language"], second["act"]) == ("zh", "correction")
    assert first["selected_intent"] == "explicit_preference_memory_write"
    assert second["selected_intent"] == "explicit_preference_memory_correction"
    for row in result["turns"]:
        assert row["planner_route"] == "deterministic_rule_plan"
        assert row["product_planner_model_call_count"] == 0
        assert row["plan_authority"] is True
        assert row["surface_authority"] is True
        assert row["graph_node_stage"] == "select"
        assert row["final_visible_surface_matches_contract"] is True
        assert row["latency_target_met"] is True


def test_distinct_episodes_safari_and_zero_side_effect_accounting():
    result = _load()
    assert result["turns"][0]["episode_id"] != result["turns"][1]["episode_id"]
    assert all(row["durable_episode_write_count"] == 1 for row in result["turns"])
    assert result["safari"]["actual_two_turn_acceptance"] is True
    assert result["safari"]["closed_tab_count"] == 0
    accounting = result["accounting"]
    assert accounting["real_product_turns"] == 2
    assert accounting["retry_count"] == 0
    assert accounting["local_product_planner_model_calls"] == 0
    assert accounting["fallback_count"] == 0
    assert accounting["paid_api_call_count"] == 0
    assert accounting["production_memory_access_count"] == 0


def test_result_does_not_hide_incomplete_typed_preference_semantics():
    boundary = _load()["observed_semantic_boundary"]
    assert boundary["typed_profile_after_turn_2"] == {
        "likes": [],
        "dislikes": ["氣泡水"],
    }
    assert boundary["new_current_preference_typed_as_like"] is False
    assert boundary["old_preference_typed_as_dislike"] is True
    assert boundary["both_turns_preserved_as_episodes"] is True
