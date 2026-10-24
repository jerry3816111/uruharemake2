import json
from copy import deepcopy
from pathlib import Path

import p4_as_selected_action_surface_execution_gate as gate
import uruha_adaptive_person_model as adaptive
import uruha_executed_action_receipt_m44 as receipt_m44
import uruha_selected_action_surface_execution_p4 as p4_as


ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "datasets" / "p4_as_selected_action_surface_execution_v1.json"


def test_p4_as_offline_evidence_passes_the_prospective_gate():
    evidence = p4_as.build_dataset_evidence_p4_as(DATASET)
    evaluated = gate.evaluate_offline_evidence(gate.load_contract(), evidence)

    assert evaluated["status"] == "pass", (evaluated, evidence["metrics"])
    assert evaluated["failed_gates"] == []


def test_p4_as_positive_surface_is_japanese_clarification_without_role_inversion():
    evidence = p4_as.build_dataset_evidence_p4_as(DATASET)
    positives = [row for row in evidence["cases"] if row["expected_status"] == p4_as.FINAL_STATUS]

    assert len(positives) == 7
    for row in positives:
        assert row["selected_policy"] == "calibrate_need"
        assert row["surface_policy_act_match"] is True
        assert row["surface_unresolved"] == []
        assert "どっち" in row["visible_reply"]
        assert "うちの頭" not in row["visible_reply"]
        assert row["receipt_prediction_id"] == row["prediction_id"]
        assert row["pending_prediction_id"] == row["prediction_id"]
        assert row["p4_ar_authorized"] is True


def test_p4_as_controls_never_commit_a_prediction_or_change_surface():
    evidence = p4_as.build_dataset_evidence_p4_as(DATASET)
    controls = [row for row in evidence["cases"] if row["expected_status"] == "not_applicable"]

    assert len(controls) == 6
    for row in controls:
        assert row["status"] == "not_applicable"
        assert row["receipt_status"] != "registered_for_next_user_turn"
        assert row["pending_prediction_id"] is None
        assert row["surface_changed"] is False
        assert row["p4_ar_authorized"] is False


def test_p4_as_promotion_never_mutates_the_source_state():
    source = {
        "active": False,
        "observable_trigger_m37": adaptive.extract_observable_trigger_predicates_m37(
            "My mind cannot switch off even though I want it to rest."
        ),
        "atoms": {},
        "activation_reasons": [],
    }
    before = deepcopy(source)

    promoted, trace = p4_as.promote_selected_action_state_p4(
        "My mind cannot switch off even though I want it to rest.",
        source,
    )

    assert source == before
    assert promoted is not source
    assert promoted["active"] is True
    assert trace["source_state_mutated"] is False
    assert trace["private_state_truth_claimed"] is False


def test_p4_as_receipt_fails_closed_when_m39_has_not_verified_the_act():
    model = adaptive.empty_model()
    logic = {
        "desired_response_decision_m18": {
            "status": "applied",
            "prediction_id": "p1-1-1111111111111111",
            "selected": {"policy_id": "calibrate_need"},
            "state": {
                "turn_index": 1,
                "input_digest": receipt_m44._digest("My mind cannot settle."),
                p4_as.LABEL: {"schema": p4_as.SCHEMA, "status": p4_as.EARLY_STATUS},
            },
        },
        "adaptive_person_model_m18": {
            "applied": True,
            "prediction_id": "p1-1-1111111111111111",
            "policy_id": "calibrate_need",
        },
        "semantic_persona_surface_verifier_m39": {
            "status": "repair_failed_closed",
            "protected_route": False,
            "selected_policy_id": "calibrate_need",
            "policy_act_match_after": False,
            "unresolved_violations": ["selected_policy_not_realized"],
            "final_reply_digest": receipt_m44._digest("そのまま。"),
            "source_frame": {
                "speaker_role": "user_first_person",
                "third_party_present": False,
                "source_digest": receipt_m44._digest("My mind cannot settle."),
            },
        },
    }

    state, trace = p4_as.register_selected_action_surface_execution_p4(
        model,
        logic,
        "My mind cannot settle.",
        "そのまま。",
        1,
        original_register=lambda model, logic, user_input, reply, turn_index: (
            deepcopy(model),
            {"status": "not_registered", "reason": "fixture"},
        ),
    )

    assert state.get("pending_prediction") is None
    assert trace["status"] == "not_registered"
    assert "m39_verified" in trace["p4_as_authority"]["failed_checks"]
    assert "m39_policy_act_realized" in trace["p4_as_authority"]["failed_checks"]


def _verified_fixture(prediction_id="p1-1-1111111111111111", turn_index=1):
    user_input = "My mind cannot settle."
    reply = "今ほしいの、方法と、ただ聞いてほしいのと、どっちに近い？"
    logic = {
        "desired_response_decision_m18": {
            "status": "applied",
            "prediction_id": prediction_id,
            "selected": {"policy_id": "calibrate_need"},
            "state": {
                "turn_index": turn_index,
                "input_digest": receipt_m44._digest(user_input),
                p4_as.LABEL: {
                    "schema": p4_as.SCHEMA,
                    "status": p4_as.EARLY_STATUS,
                    "trigger_evidence_digest": "abc123",
                },
            },
        },
        "adaptive_person_model_m18": {
            "applied": True,
            "prediction_id": prediction_id,
            "policy_id": "calibrate_need",
        },
        "semantic_persona_surface_verifier_m39": {
            "status": "repaired_and_verified",
            "protected_route": False,
            "selected_policy_id": "calibrate_need",
            "policy_act_match_after": True,
            "unresolved_violations": [],
            "final_reply_digest": receipt_m44._digest(reply),
            "source_frame": {
                "speaker_role": "user_first_person",
                "third_party_present": False,
                "source_digest": receipt_m44._digest(user_input),
            },
        },
    }
    return user_input, reply, logic


def test_p4_as_adds_only_missing_receipt_for_exact_preexisting_pending():
    user_input, reply, logic = _verified_fixture()
    decision = logic["desired_response_decision_m18"]
    model = adaptive.set_pending_prediction(
        adaptive.empty_model(),
        decision,
        turn_index=1,
    )
    pending_before = deepcopy(model["pending_prediction"])
    ledger_before = deepcopy(model["outcome_calibration_ledger_m27"])

    state, trace = p4_as.register_selected_action_surface_execution_p4(
        model,
        logic,
        user_input,
        reply,
        1,
        original_register=receipt_m44.register_executed_action_m44,
    )

    assert trace["status"] == "registered_for_next_user_turn"
    assert trace["p4_as_authority"]["status"] == p4_as.RECEIPT_STATUS
    assert trace["p4_as_authority"]["pending_preexisting_exact"] is True
    assert state["pending_prediction"] == pending_before
    assert state["outcome_calibration_ledger_m27"] == ledger_before
    assert len(state[receipt_m44.STORE]) == 1
    assert state[receipt_m44.STORE][0]["prediction_id"] == decision["prediction_id"]


def test_p4_as_rejects_mismatched_preexisting_pending_without_mutation():
    user_input, reply, logic = _verified_fixture()
    _other_input, _other_reply, other_logic = _verified_fixture(turn_index=2)
    model = adaptive.set_pending_prediction(
        adaptive.empty_model(),
        other_logic["desired_response_decision_m18"],
        turn_index=2,
    )
    before = deepcopy(model)

    state, trace = p4_as.register_selected_action_surface_execution_p4(
        model,
        logic,
        user_input,
        reply,
        1,
        original_register=receipt_m44.register_executed_action_m44,
    )

    assert state == before
    assert trace["status"] == "not_registered"
    assert "pending_absent_or_exact" in trace["p4_as_authority"]["failed_checks"]
    assert state.get(receipt_m44.STORE) in (None, [])


def test_p4_as_product_entry_is_additive_after_p4_ar():
    source = (ROOT / "uruha_web_ui_product_p4_as.py").read_text(encoding="utf-8")
    launcher = (ROOT / "p4_as_safe_isolated_product_launcher.py").read_text(encoding="utf-8")

    assert "import uruha_web_ui_product_p4_ar as _p4_ar" in source
    assert "install_selected_action_surface_execution_p4()" in source
    assert 'ENTRYPOINT = ROOT / "uruha_web_ui_product_p4_as.py"' in launcher
    assert "sandboxed_p4_as_probe" in launcher
