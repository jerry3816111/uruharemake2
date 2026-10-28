import json
from pathlib import Path

from p4_z_source_bound_proposition_gate import evaluate_evidence, load_contract
from uruha_source_bound_proposition_preservation_p4 import (
    LABEL,
    append_source_bound_proposition_node_p4,
    build_dataset_evidence_p4_z,
    extract_source_bound_proposition_p4,
    preserve_source_bound_proposition_p4,
)


ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "datasets" / "p4_z_source_bound_proposition_v1.json"


def test_p4_z_frozen_dataset_passes_all_bounded_gates():
    contract = load_contract()
    evidence = build_dataset_evidence_p4_z(DATASET)
    result = evaluate_evidence(contract, evidence)
    assert result["status"] == "pass", result["failed_gates"]
    assert result["failed_gates"] == []


def test_p4_z_candidate_cannot_supply_or_replace_source_fields():
    source = "後輩は紫のマグカップをなくしたらしい。"
    adversarial = "先輩が黄色い手帳を駅に置き忘れたらしいって話ね。"
    visible, trace = preserve_source_bound_proposition_p4(source, adversarial)
    assert visible == "後輩が紫のマグカップをなくしたらしいって話ね。"
    assert trace["status"] == "repaired_and_verified"
    assert {"source_subject_missing", "source_predicate_missing", "source_object_missing"}.issubset(trace["violations_before"])


def test_p4_z_unsupported_source_fails_closed_unchanged():
    source = "Maybe this means several different things, but I am not sure."
    candidate = "まだ意味を一つに決められないんだね。"
    visible, trace = preserve_source_bound_proposition_p4(source, candidate)
    assert visible == candidate
    assert trace["status"] == "source_pattern_unavailable"
    assert trace["action"] == "abstain_unchanged"
    assert trace["changed"] is False


def test_p4_z_trace_is_raw_free_and_has_typed_source_digests():
    source = "Apparently Maya left the green folder in the taxi."
    candidate = "マヤが緑のフォルダーらしいって話ね。"
    visible, trace = preserve_source_bound_proposition_p4(source, candidate)
    encoded = json.dumps(trace, ensure_ascii=False)
    assert source not in encoded
    assert visible not in encoded
    assert trace["raw_source_or_reply_persisted"] is False
    assert trace["known_field_types"] == ["location_jp", "object_jp", "predicate_jp", "subject_jp"]
    assert set(trace["source_anchor_digests"]) == set(trace["known_field_types"])
    assert all(len(value) == 64 for value in trace["source_anchor_digests"].values())


def test_p4_z_graph_node_is_inserted_once_before_utterance():
    trace = {"schema": "fixture", "changed": True}
    result = {
        "logic": {LABEL: trace},
        "runtime_trace": {
            "blackboard": [
                {"stage": "surface", "label": LABEL, "payload": {"stale": True}},
                {"stage": "surface", "label": "utterance", "payload": {}},
            ]
        },
    }
    delivered = append_source_bound_proposition_node_p4(result)
    labels = [row["label"] for row in delivered["runtime_trace"]["blackboard"]]
    assert labels == [LABEL, "utterance"]
    assert labels.count(LABEL) == 1
    assert delivered["runtime_trace"][LABEL] == trace
    assert delivered["runtime_trace"]["blackboard"][0]["payload"] == trace


def test_p4_z_extractor_marks_missing_fields_unknown_instead_of_inventing():
    contract = extract_source_bound_proposition_p4("後輩は紫のマグカップをなくしたらしい。")
    assert contract["location_jp"] is None
    assert contract["time_jp"] is None
    assert contract["field_status"]["location_jp"] == "unknown_not_in_source_rule"
    assert contract["field_status"]["time_jp"] == "unknown_not_in_source_rule"
