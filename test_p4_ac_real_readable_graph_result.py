import hashlib
import json
from pathlib import Path

import p4_ac_real_readable_graph_gate as gate


ROOT = Path(__file__).resolve().parent
EVIDENCE = ROOT / "analysis" / "p4_ac_real_readable_graph_evidence_2026-09-23.json"
RESULT = ROOT / "analysis" / "p4_ac_real_readable_graph_result_2026-09-23.json"


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_saved_real_safari_evidence_reproduces_frozen_pass():
    evidence = _load(EVIDENCE)
    result = _load(RESULT)
    assert gate.evaluate_evidence(gate.load_contract(), evidence) == result
    assert result["status"] == "pass"
    assert result["failed_gates"] == []


def test_readable_summaries_are_logic_exact_and_not_generic_field_counts():
    evidence = _load(EVIDENCE)
    assert [row["graph_summary"] for row in evidence["turns"]] == [
        "引用｜引文命題｜主體/動作/時間｜修正 3→0",
        "未支援來源｜歸屬未知｜欄位無｜保留原文 1→1",
    ]
    assert all(row["graph_summary"] == row["logic_derived_summary"] for row in evidence["turns"])
    assert all(" fields" not in row["graph_summary"] for row in evidence["turns"])
    assert evidence["metrics"]["summary_logic_exact_count"] == 2


def test_runtime_memory_resource_and_no_rerun_boundaries_are_preserved():
    evidence = _load(EVIDENCE)
    assert [row["episode_id"] for row in evidence["turns"]] == [
        "d9aaa2f2-97d4-431b-bdf4-bbe266890cf9",
        "cfbc3b52-87e4-4dec-9666-601c7a677032",
    ]
    assert evidence["raw_runtime_artifacts"]["conversation_jsonl_rows"] == 2
    assert evidence["raw_runtime_artifacts"]["conversation_jsonl_sha256"] == (
        "97bf92b762c11978aae3e718874f1f5f79b978bbda8ece65430d47f1d67ad08b"
    )
    assert evidence["raw_runtime_artifacts"]["user_profile_count"] == 0
    assert evidence["resource_notes"]["semantic_authorization_model_calls"] == 2
    assert evidence["resource_notes"]["p4_ab_added_model_calls"] == 0
    assert evidence["resource_notes"]["token_accounting"] == "unavailable"
    assert evidence["decision"]["same_case_rerun_allowed"] is False
    assert evidence["accounting"]["closed_user_tab_count"] == 0


def test_committed_dataset_and_evidence_hash_bindings_are_unchanged():
    contract = gate.load_contract()
    dataset_path = ROOT / contract["dataset"]["path"]
    assert hashlib.sha256(dataset_path.read_bytes()).hexdigest() == contract["dataset"]["sha256"]
    assert _load(EVIDENCE)["dataset_sha256"] == contract["dataset"]["sha256"]
