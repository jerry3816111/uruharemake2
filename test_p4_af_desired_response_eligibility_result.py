import json
from pathlib import Path

import p4_af_desired_response_eligibility_gate as gate


ROOT = Path(__file__).resolve().parent
EVIDENCE = ROOT / "analysis" / "p4_af_desired_response_eligibility_evidence_2026-09-23.json"
RESULT = ROOT / "analysis" / "p4_af_desired_response_eligibility_result_2026-09-23.json"


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_saved_evidence_reproduces_frozen_pass():
    evidence = _load(EVIDENCE)
    result = _load(RESULT)
    assert gate.evaluate_evidence(gate.load_contract(), evidence) == result
    assert result["status"] == "pass"
    assert result["failed_gates"] == []


def test_topic_only_false_positive_is_removed_without_reranking_eligible_cases():
    evidence = _load(EVIDENCE)
    fixed = next(row for row in evidence["cases"] if row["case_id"] == "af_dev_ae_false_positive_zh")
    assert fixed["status"] == "not_applicable"
    assert fixed["eligibility_authority"] == "none_topic_only"
    assert fixed["candidate_count"] == 0
    assert evidence["metrics"]["fresh_negative_exact_status_count"] == 6
    assert evidence["metrics"]["eligible_candidate_ranking_unchanged_count"] == 8
    assert evidence["metrics"]["topic_only_authorization_count"] == 0


def test_pass_has_no_visible_model_or_memory_side_effect():
    metrics = _load(EVIDENCE)["metrics"]
    assert metrics["visible_reply_changed_count"] == 0
    assert metrics["new_model_call_count"] == 0
    assert metrics["fact_write_count"] == 0
    assert metrics["profile_write_count"] == 0
    assert metrics["episode_write_count"] == 0
