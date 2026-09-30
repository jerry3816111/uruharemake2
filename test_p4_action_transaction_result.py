"""Post-result regression: verify committed chronology and preserved FAIL.

This test was written after raw/anonymous labels were locked. It checks the
frozen scorer output and report integrity; it is not a prospective success
criterion, model call, or independent human judgment.
"""

import json
from pathlib import Path

import p4_action_transaction_evidence as evidence


ROOT = Path(__file__).resolve().parent
COMMITS = {
    "runner_commit": "054db9b03fa1f78d7a22e3c2d584b388309b71c2",
    "raw_commit": "49497bfffc819953c9e42795fc40a8a7ff22bbe4",
    "packet_commit": "657a85c6519390f9fdcc6aec2f7aa44f80ee7ccf",
    "submission_commit": "5d16bcf1a1d89c25e792a639d125f1c961438ab5",
    "reveal_commit": "f53da4d62ab3992bd2e644a0a3250afdb24dcf71",
}
RESULT = ROOT / "analysis/p4_action_transaction_v1_result_2026-09-30.json"
PRIOR_RAW = ROOT / "analysis/p4_action_transaction_v1_raw_2026-09-30.json"


def test_previously_failed_prewarm_remains_zero_scored_and_unmodified():
    prior = json.loads(PRIOR_RAW.read_text(encoding="utf-8"))
    assert prior["status"] == "prewarm_failed_no_scored_calls"
    assert prior["scored_calls_started"] == 0
    assert prior["cases"] == []
    assert prior["prewarm"]["ollama_response"]["done_reason"] == "load"


def test_actual_result_recomputes_from_git_locked_raw_and_masked_labels():
    verified = evidence.verify_annotation_lock(ROOT, **COMMITS)
    saved = json.loads(RESULT.read_text(encoding="utf-8"))
    assert saved["status"] == verified["component_status"] == (
        "REVIEW_REQUIRED_COMPONENT_FAIL")
    assert saved["score_summary"] == verified["score_summary"]
    assert saved["score_rows"] == verified["score_rows"]
    assert saved["scored_calls"] == verified["scored_calls"] == 36
    assert saved["annotation_authority"] == (
        "arm_masked_developer_proxy_not_independent_human")
    assert saved["product_runtime_changed"] is False
    summary = verified["score_summary"]
    assert summary["frozen_case_identity_match"] is True
    assert summary["all_raw_observations_locked"] is True
    assert summary["arms"]["A_two_stage"]["valid_action"] == 0
    assert summary["arms"]["B_transaction"]["valid_action"] == 0
    assert summary["arms"]["B_transaction"]["source_bound_reason_hit"] == 0
    assert summary["overall_b_qualified"] is False
