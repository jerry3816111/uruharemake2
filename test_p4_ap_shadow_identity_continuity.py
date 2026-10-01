from copy import deepcopy
from pathlib import Path

import uruha_prediction_identity_p1 as identity
import uruha_shadow_feedback_identity_continuity_p4 as continuity


ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "datasets/p4_ap_shadow_identity_continuity_v1.json"


def test_offline_evidence_passes_frozen_identity_gates():
    evidence = continuity.build_offline_evidence_p4_ap(DATASET)
    import p4_ap_shadow_identity_continuity_gate as gate

    contract = gate.load_contract()
    assert evidence["dataset_sha256"] == contract["dataset"]["sha256"]
    assert evidence["metrics"] == contract["offline_gates"]
    assert [row["prediction_sequence"] for row in evidence["turns"]] == [1, 2, 3]
    assert [row["shadow_identity_floor"] for row in evidence["turns"]] == [0, 1, 2]


def test_sequence_two_and_three_use_p1_guard_without_skipping():
    identity.install_prediction_identity_p1()
    for sequence in (2, 3):
        prediction_id = f"p1-{sequence}-0123456789abcdef"
        binding = {
            "status": "pending",
            "prediction_id": prediction_id,
            "turn_index": sequence,
            "input_digest": "0" * 16,
            "selected_policy": "calibrate_need",
            "candidate_snapshots": [
                {"policy_id": "calibrate_need", "operational_action_score": 0.8}
            ],
        }
        model = continuity.build_shadow_feedback_model_with_identity_continuity_p4(
            binding, {"state": {}}
        )
        trace = model[continuity.LABEL]
        assert trace["seeded_identity_floor"] == sequence - 1
        assert trace["sequence_guard_bypassed"] is False
        assert model[identity.SEQUENCE] == sequence
        assert model["pending_prediction"]["prediction_id"] == prediction_id


def test_graph_trace_is_raw_free_before_utterance_and_no_reply_change():
    trace = {
        "schema": continuity.SCHEMA,
        "prediction_id": "p1-2-0123456789abcdef",
        "prediction_sequence": 2,
        "seeded_identity_floor": 1,
        "pending_identity_exact": True,
        "sequence_guard_bypassed": False,
        "raw_dialogue_persisted": False,
    }
    before = {
        "reply": "そのまま",
        "logic": {},
        "runtime_trace": {
            "blackboard": [
                {"stage": "predict", "label": "runtime_temporal_graph_delivery_p4", "payload": {}},
                {"stage": "surface", "label": "utterance", "payload": {}},
            ]
        },
    }
    after = continuity.append_identity_continuity_node_p4(deepcopy(before), trace)
    labels = [row["label"] for row in after["runtime_trace"]["blackboard"]]
    assert labels.index(continuity.LABEL) < labels.index("runtime_temporal_graph_delivery_p4")
    assert after["reply"] == before["reply"]
    assert after["logic"][continuity.LABEL] == trace
    assert after["runtime_trace"][continuity.LABEL] == trace
