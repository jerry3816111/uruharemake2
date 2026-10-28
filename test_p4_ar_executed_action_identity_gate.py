from copy import deepcopy
from pathlib import Path

import p4_ar_executed_action_identity_gate as gate
import uruha_desired_response_outcome_binding_p4 as outcome_binding
import uruha_executed_action_identity_gate_p4 as action_gate
import uruha_runtime_temporal_graph_delivery_p4 as temporal


ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "datasets/p4_ar_executed_action_identity_gate_v1.json"


def test_offline_evidence_passes_frozen_executed_action_gates():
    contract = gate.load_contract()
    evidence = action_gate.build_offline_evidence_p4_ar(DATASET)
    evaluated = gate.evaluate_offline_evidence(contract, evidence)

    assert evidence["dataset_sha256"] == contract["dataset"]["sha256"]
    assert evidence["metrics"] == contract["offline_gates"]
    assert evaluated["status"] == "pass"
    assert evaluated["failed_gates"] == []


def test_p4_aq_exposed_shape_is_blocked_without_promoting_fallback_identity():
    frozen = gate.load_dataset(gate.load_contract())["development_cases"][0]
    source = action_gate._case_result(frozen)
    before = deepcopy(source)
    audit = action_gate.assess_executed_action_identity_p4(source)

    assert audit["status"] == "blocked_unexecuted_shadow_action"
    assert audit["outcome_verification_authorized"] is False
    assert audit["checks"]["genuine_p1_identity"] is False
    assert audit["fallback_identity_promoted_to_p1"] is False
    assert audit["p1_guard_weakened"] is False
    assert source == before


def test_exact_executed_product_event_remains_authorized():
    frozen = gate.load_dataset(gate.load_contract())["fresh_authorized_cases"][0]
    audit = action_gate.assess_executed_action_identity_p4(
        action_gate._case_result(frozen)
    )

    assert audit["status"] == "authorized_executed_product_event"
    assert audit["prediction_sequence"] == 1
    assert audit["outcome_verification_authorized"] is True
    assert audit["failed_checks"] == []


def test_blocked_shadow_action_removes_only_current_binding_and_future():
    frozen = gate.load_dataset(gate.load_contract())["fresh_blocked_cases"][0]
    source = action_gate._case_result(frozen)
    source["logic"][outcome_binding.LABEL]["current_binding"].update(
        {
            "candidate_snapshots": [
                {"policy_id": name, "candidate_id": f"candidate-{index}"}
                for index, name in enumerate(
                    (
                        "calibrate_need",
                        "listen_presence",
                        "share_arousal",
                        "care_physiology",
                        "solve_regulation",
                        "playful_tease",
                    )
                )
            ],
            "candidate_count": 6,
        }
    )
    source_before = deepcopy(source)
    temporal_before = temporal.initial_delivery_state_p4()
    guarded = action_gate.enforce_executed_action_identity_gate_p4(
        source,
        temporal_before,
    )

    assert guarded["blocked"] is True
    assert source == source_before
    assert guarded["pending_binding"]["status"] == "not_available"
    assert guarded["pending_binding"]["suppressed_shadow_candidate_count"] == 6
    assert guarded["temporal_payload"]["present"]["candidate_count"] == 0
    assert guarded["temporal_payload"]["future"]["status"] == "not_available"
    assert guarded["result"]["reply"] == source["reply"]
    labels = [
        row["label"] for row in guarded["result"]["runtime_trace"]["blackboard"]
    ]
    assert labels.index(outcome_binding.LABEL) < labels.index(action_gate.LABEL)
    assert labels.index(action_gate.LABEL) < labels.index(temporal.LABEL)
    assert labels.index(temporal.LABEL) < labels.index("utterance")


def test_control_is_audit_only_noop():
    frozen = gate.load_dataset(gate.load_contract())["control_cases"][0]
    source = action_gate._case_result(frozen)
    guarded = action_gate.enforce_executed_action_identity_gate_p4(
        source,
        temporal.initial_delivery_state_p4(),
    )

    assert guarded["blocked"] is False
    assert guarded["audit"]["status"] == "not_applicable"
    assert guarded["result"]["reply"] == source["reply"]
    assert guarded["result"]["logic"][outcome_binding.LABEL] == source["logic"][outcome_binding.LABEL]


def test_product_entry_is_additive_after_p4_aq():
    source = (ROOT / "uruha_web_ui_product_p4_ar.py").read_text(encoding="utf-8")
    launcher = (ROOT / "p4_ar_safe_isolated_product_launcher.py").read_text(encoding="utf-8")
    assert "import uruha_web_ui_product_p4_aq as _p4_aq" in source
    assert "install_executed_action_identity_gate_p4()" in source
    assert 'ENTRYPOINT = ROOT / "uruha_web_ui_product_p4_ar.py"' in launcher
    assert "sandboxed_p4_ar_probe" in launcher
