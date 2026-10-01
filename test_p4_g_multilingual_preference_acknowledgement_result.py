import hashlib
import json
from pathlib import Path

import p4_g_preference_acknowledgement_gate as gate


ROOT = Path(__file__).resolve().parent
RESULT = ROOT / "analysis" / "p4_g_multilingual_preference_acknowledgement_result_2026-09-21.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load():
    return json.loads(RESULT.read_text(encoding="utf-8"))


def test_result_is_bound_to_freeze_and_preserves_failure():
    result = _load()
    binding = result["freeze_binding"]
    assert _sha256(ROOT / binding["path"]) == binding["sha256"]
    assert result["status"] == "fail"


def test_frozen_gate_recomputes_the_exact_ten_failures():
    result = _load()
    recomputed = gate.evaluate_evidence(gate.load_contract(), result)
    assert recomputed["status"] == "fail"
    assert recomputed["failed_gates"] == result["gate_evaluation"]["failed_gates"]
    assert len(recomputed["failed_gates"]) == 10


def test_both_acts_were_classified_and_persisted_but_surface_authority_did_not_run():
    result = _load()
    first, second = result["turns"]
    assert (first["input_language"], first["act"]) == ("zh", "write")
    assert (second["input_language"], second["act"]) == ("ja", "correction")
    assert first["episode_id"] != second["episode_id"]
    assert all(row["durable_episode_write_count"] == 1 for row in result["turns"])
    assert all(row["p4_g_status"] == "eligible_surface_already_non_generic" for row in result["turns"])
    assert all(row["surface_authority"] is False for row in result["turns"])
    assert all(row["graph_node_visible"] == "explicit_preference_acknowledgement_p4" for row in result["turns"])


def test_result_preserves_misroute_latency_and_zero_retry_accounting():
    result = _load()
    first, second = result["turns"]
    assert first["latency_target_met"] is False
    assert first["end_to_end_seconds"] == 25.2079
    assert second["selected_intent"] == "ask_like_me"
    assert "安心したいだけだろ" in second["visible_output"]
    assert result["diagnosis"]["same_case_rerun_or_retuning_performed"] is False
    accounting = result["accounting"]
    assert accounting["real_product_turns"] == 2
    assert accounting["local_product_planner_model_calls"] == 1
    assert accounting["retry_count"] == 0
    assert accounting["fallback_count"] == 0
    assert accounting["paid_api_call_count"] == 0
    assert accounting["production_memory_access_count"] == 0

