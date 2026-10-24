import json
from pathlib import Path

import p4_am_real_runtime_temporal_graph_gate as gate
import uruha_past_present_future_commitment_p4 as temporal
import uruha_runtime_temporal_graph_delivery_p4 as delivery


ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "datasets" / "p4_am_real_runtime_temporal_graph_v1.json"


def test_empty_past_commitment_is_honest_and_hash_valid():
    pending = temporal._synthetic_pending(
        {"case_id": "p4-am-empty", "selected_policy": "calibrate_need", "current_turn": 10}
    )
    commitment = delivery._empty_past_commitment(pending, 10)
    assert commitment["past"] == {
        "status": "no_prior_verified_evidence",
        "records": [],
        "record_count": 0,
        "strictly_before_present": True,
    }
    assert temporal.validate_commitment_hash_p4(commitment) is True


def test_three_turn_offline_cycle_keeps_current_verification_out_of_current_past():
    evidence = delivery.build_offline_evidence_p4_am(DATASET)
    assert [row["past_record_count"] for row in evidence["turns"]] == [0, 0, 1]
    assert [row["previous_outcome"] for row in evidence["turns"]] == [None, "supported", "supported"]
    assert evidence["metrics"]["same_turn_outcome_promoted_to_past_count"] == 0
    assert evidence["metrics"]["raw_or_private_payload_leak_count"] == 0
    assert gate.evaluate_offline_evidence(gate.load_contract(), evidence)["status"] == "pass"


def test_graph_payload_is_exact_and_inserted_before_utterance():
    payload = {"schema": delivery.SCHEMA, "summary": "過去 0｜現在 6候選｜本輪未來 已封存"}
    result = delivery.append_temporal_graph_delivery_node_p4(
        {
            "logic": {},
            "runtime_trace": {
                "blackboard": [
                    {"stage": "learn", "label": "desired_response_outcome_binding_p4", "payload": {}},
                    {"stage": "surface", "label": "utterance", "payload": {}},
                ]
            },
        },
        payload,
    )
    labels = [row["label"] for row in result["runtime_trace"]["blackboard"]]
    assert labels == [
        "desired_response_outcome_binding_p4",
        delivery.LABEL,
        "utterance",
    ]
    assert result["logic"][delivery.LABEL] == result["runtime_trace"][delivery.LABEL] == payload


def test_product_and_launcher_are_additive_and_target_p4_am():
    entry = (ROOT / "uruha_web_ui_product_p4_am.py").read_text(encoding="utf-8")
    launcher = (ROOT / "p4_am_safe_isolated_product_launcher.py").read_text(encoding="utf-8")
    assert "import uruha_web_ui_product_p4_ah as _p4_ah" in entry
    assert "install_runtime_temporal_graph_delivery_p4()" in entry
    assert 'ENTRYPOINT = ROOT / "uruha_web_ui_product_p4_am.py"' in launcher
    assert "sandboxed_p4_am_probe" in launcher


def test_evidence_contains_no_frozen_raw_dialogue():
    dataset = json.loads(DATASET.read_text(encoding="utf-8"))
    evidence = delivery.build_offline_evidence_p4_am(DATASET)
    serialized = json.dumps(evidence, ensure_ascii=False, sort_keys=True)
    assert all(row["input"] not in serialized for row in dataset["turns"])
