import copy
import json
from pathlib import Path

import pytest

from p3_b47_retained_case_rubric_audit import AuditError, build_audit


ROOT = Path(__file__).resolve().parent
CASE_OUTPUT = ROOT / "analysis/p3_b46_prospective_v3_output_lock_checkpoints_v1/case_results/30ce55cd27b604df4cca.json"
SOURCE = ROOT / "datasets/p3_prospective_developer_source_v3.json"
ANNOTATIONS = ROOT / "datasets/p3_prospective_developer_annotations_v3.json"
ADJUDICATION = ROOT / "datasets/p3_b47_case01_developer_adjudication_v1.json"


def test_actual_retained_case_audit_has_no_batch_winner():
    result = build_audit(CASE_OUTPUT, SOURCE, ANNOTATIONS, ADJUDICATION)
    assert result["status"] == "retained_case01_developer_proxy_audit_complete_no_batch_conclusion"
    assert result["condition_winner"] is None
    assert result["batch_comparison_available"] is False
    assert result["model_calls"] == result["network_calls"] == 0
    assert [row["status"] for row in result["unavailable_cases"]] == ["not_generated", "not_generated"]
    assert result["condition_summaries"]["isolated_product"]["total_score"] == 11
    assert result["condition_summaries"]["full_history_direct"]["total_score"] == 12
    assert result["condition_summaries"]["isolated_product"]["case_pass"] is False
    assert result["condition_summaries"]["full_history_direct"]["case_pass"] is False


def _write_json(path, payload):
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_refuses_mutated_bound_case_output(tmp_path):
    payload = json.loads(CASE_OUTPUT.read_text(encoding="utf-8"))
    payload["total_wall_seconds"] += 1
    changed = tmp_path / "case.json"
    _write_json(changed, payload)
    with pytest.raises(AuditError, match="bound_artifact_hash_mismatch"):
        build_audit(changed, SOURCE, ANNOTATIONS, ADJUDICATION)


def test_refuses_unknown_rubric_act(tmp_path):
    payload = json.loads(ADJUDICATION.read_text(encoding="utf-8"))
    payload["rows"][0]["required_act_findings"]["invented_new_act"] = {
        "present": False,
        "evidence_quote": "",
        "rationale": "not in frozen rubric",
    }
    changed = tmp_path / "adjudication.json"
    _write_json(changed, payload)
    with pytest.raises(AuditError, match="required_act_set_mismatch"):
        build_audit(CASE_OUTPUT, SOURCE, ANNOTATIONS, changed)


def test_refuses_required_dimension_inconsistent_with_findings(tmp_path):
    payload = json.loads(ADJUDICATION.read_text(encoding="utf-8"))
    payload["rows"][0]["scores"]["required_semantic_acts_present"] = 1
    changed = tmp_path / "adjudication.json"
    _write_json(changed, payload)
    with pytest.raises(AuditError, match="required_dimension_inconsistent"):
        build_audit(CASE_OUTPUT, SOURCE, ANNOTATIONS, changed)


def test_refuses_evidence_quote_not_found_in_locked_reply(tmp_path):
    payload = json.loads(ADJUDICATION.read_text(encoding="utf-8"))
    payload["rows"][0]["dimension_evidence"]["source_grounding_correct"]["evidence_quote"] = "not in reply"
    changed = tmp_path / "adjudication.json"
    _write_json(changed, payload)
    with pytest.raises(AuditError, match="dimension_evidence_quote_not_in_reply"):
        build_audit(CASE_OUTPUT, SOURCE, ANNOTATIONS, changed)


def test_refuses_non_japanese_critical_failure_with_positive_surface_score(tmp_path):
    payload = json.loads(ADJUDICATION.read_text(encoding="utf-8"))
    direct_u2 = next(
        row for row in payload["rows"]
        if row["condition"] == "full_history_direct" and row["turn_id"].endswith("-u2")
    )
    direct_u2["scores"]["natural_japanese_surface"] = 1
    changed = tmp_path / "adjudication.json"
    _write_json(changed, payload)
    with pytest.raises(AuditError, match="non_japanese_critical_failure_inconsistent"):
        build_audit(CASE_OUTPUT, SOURCE, ANNOTATIONS, changed)
