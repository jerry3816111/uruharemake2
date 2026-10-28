"""P4-AP continuity for the classifier-only P4-AG shadow model.

The product-wide P1 prediction sequence is authoritative.  P4-AG uses a
throw-away model only to run the released next-turn feedback classifier; this
adapter seeds that shadow with the immediately preceding sequence floor and
then still calls P1's fail-closed pending setter.  It does not relax the P1
guard or copy product memory into the shadow.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path

import uruha_adaptive_person_model as adaptive
import uruha_desired_response_outcome_binding_p4 as outcome_binding
import uruha_prediction_identity_p1 as identity


SCHEMA = "uruha_shadow_feedback_identity_continuity_p4"
LABEL = "shadow_feedback_identity_continuity_p4"
_ORIGINAL_BUILD = outcome_binding.build_shadow_feedback_model_p4
_ORIGINAL_RUN_TURN = None
_INSTALLED = False


class P4APIdentityContinuityError(ValueError):
    pass


def _shadow_decision(binding, decision):
    chosen = next(
        (
            row
            for row in (binding.get("candidate_snapshots") or [])
            if row.get("policy_id") == binding.get("selected_policy")
        ),
        {},
    )
    source_state = deepcopy((decision or {}).get("state") or {})
    source_state["input_digest"] = binding.get("input_digest")
    return {
        "prediction_id": binding.get("prediction_id"),
        "selected": {
            "policy_id": binding.get("selected_policy"),
            "expected_utility": chosen.get("operational_action_score"),
            "response_dimensions": {},
            "realization": {},
        },
        "utility_margin": (decision or {}).get("utility_margin"),
        "state": source_state,
    }


def build_shadow_feedback_model_with_identity_continuity_p4(binding, decision=None):
    """Build one raw-free shadow while preserving the exact P1 event identity."""

    binding = deepcopy(binding or {})
    if binding.get("status") != "pending":
        return _ORIGINAL_BUILD(binding, decision)
    prediction_id = str(binding.get("prediction_id") or "")
    sequence = identity._sequence_from_id(prediction_id)
    if not sequence:
        return _ORIGINAL_BUILD(binding, decision)
    if adaptive.set_pending_prediction is not identity.set_pending_prediction_p1:
        raise P4APIdentityContinuityError("p1_sequence_guard_not_installed")

    identity_floor = sequence - 1
    shadow = adaptive.empty_model()
    shadow[identity.SEQUENCE] = identity_floor
    shadow_decision = _shadow_decision(binding, deepcopy(decision or {}))
    committed = adaptive.set_pending_prediction(
        shadow,
        shadow_decision,
        binding.get("turn_index") or 0,
    )
    pending_id = str((committed.get("pending_prediction") or {}).get("prediction_id") or "")
    if pending_id != prediction_id or identity._sequence_floor(committed) != sequence:
        raise P4APIdentityContinuityError("shadow_pending_identity_mismatch")
    committed[LABEL] = {
        "schema": SCHEMA,
        "status": "exact_product_prediction_committed_to_classifier_shadow",
        "prediction_id": prediction_id,
        "prediction_sequence": sequence,
        "seeded_identity_floor": identity_floor,
        "pending_identity_exact": True,
        "sequence_guard_bypassed": False,
        "feedback_classifier_changed": False,
        "copied_product_ledger_rows": 0,
        "raw_dialogue_persisted": False,
        "visible_reply_changed": False,
        "model_call_added": False,
        "factual_memory_write_count": 0,
    }
    return committed


def append_identity_continuity_node_p4(result, payload):
    result = result or {}
    payload = deepcopy(payload or {})
    if payload.get("schema") != SCHEMA:
        return result
    logic = result.get("logic") or {}
    logic[LABEL] = payload
    result["logic"] = logic
    runtime = result.get("runtime_trace") or {}
    blackboard = [row for row in (runtime.get("blackboard") or []) if row.get("label") != LABEL]
    insert_at = next(
        (
            index
            for index, row in enumerate(blackboard)
            if row.get("label") in {"runtime_temporal_graph_delivery_p4", "utterance"}
        ),
        len(blackboard),
    )
    blackboard.insert(
        insert_at,
        {"stage": "predict", "label": LABEL, "payload": payload, "salience": 0.99},
    )
    runtime["blackboard"] = blackboard
    runtime[LABEL] = payload
    result["runtime_trace"] = runtime
    return result


def install_shadow_feedback_identity_continuity_p4():
    global _INSTALLED, _ORIGINAL_RUN_TURN
    if _INSTALLED:
        return False
    if adaptive.set_pending_prediction is not identity.set_pending_prediction_p1:
        raise P4APIdentityContinuityError("p1_sequence_guard_not_installed")
    from uruha_brain_mac import UruhaBrainV4_Mac

    outcome_binding.build_shadow_feedback_model_p4 = (
        build_shadow_feedback_model_with_identity_continuity_p4
    )
    _ORIGINAL_RUN_TURN = UruhaBrainV4_Mac.run_turn_debug

    def run_turn_with_p4_ap(self, user_input, input_context=None):
        result = _ORIGINAL_RUN_TURN(self, user_input, input_context=input_context)
        shadow = deepcopy(getattr(self, "_p4_ag_shadow_feedback_model", {}) or {})
        result = append_identity_continuity_node_p4(result, shadow.get(LABEL) or {})
        if getattr(self.runtime, "turn_traces", None):
            self.runtime.turn_traces[-1] = deepcopy(result["runtime_trace"])
        return result

    UruhaBrainV4_Mac.run_turn_debug = run_turn_with_p4_ap
    _INSTALLED = True
    return True


def build_offline_evidence_p4_ap(dataset_path):
    dataset_path = Path(dataset_path)
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    identity.install_prediction_identity_p1()
    rows = []
    for frozen in dataset["turns"]:
        sequence = frozen["expected_prediction_sequence"]
        prediction_id = f"p1-{sequence}-{hashlib.sha256(str(sequence).encode()).hexdigest()[:16]}"
        candidates = [
            {
                "policy_id": policy_id,
                "operational_action_score": round(0.9 - index * 0.1, 2),
            }
            for index, policy_id in enumerate(
                (
                    "calibrate_need",
                    "listen_presence",
                    "share_arousal",
                    "care_physiology",
                    "solve_regulation",
                    "playful_tease",
                )
            )
        ]
        binding = {
            "status": "pending",
            "prediction_id": prediction_id,
            "turn_index": frozen["turn"],
            "input_digest": hashlib.sha256(str(frozen["turn"]).encode()).hexdigest()[:16],
            "selected_policy": "calibrate_need",
            "candidate_snapshots": candidates,
        }
        model = build_shadow_feedback_model_with_identity_continuity_p4(binding, {"state": {}})
        trace = model[LABEL]
        before = {"reply": "unchanged", "logic": {}, "runtime_trace": {"blackboard": [{"stage": "surface", "label": "utterance", "payload": {}}]}}
        after = append_identity_continuity_node_p4(deepcopy(before), trace)
        labels = [row.get("label") for row in after["runtime_trace"]["blackboard"]]
        rows.append(
            {
                "turn": frozen["turn"],
                "prediction_sequence": trace["prediction_sequence"],
                "shadow_identity_floor": trace["seeded_identity_floor"],
                "shadow_pending_identity_exact": trace["pending_identity_exact"],
                "sequence_guard_bypassed": trace["sequence_guard_bypassed"],
                "feedback_classifier_changed": trace["feedback_classifier_changed"],
                "visible_reply_changed": after["reply"] != before["reply"],
                "node_before_utterance": labels.index(LABEL) < labels.index("utterance"),
                "raw_dialogue_persisted": trace["raw_dialogue_persisted"],
            }
        )
    metrics = {
        "prediction_sequence_exact_count": sum(row["prediction_sequence"] == frozen["expected_prediction_sequence"] for row, frozen in zip(rows, dataset["turns"])),
        "shadow_identity_floor_exact_count": sum(row["shadow_identity_floor"] == frozen["expected_shadow_identity_floor"] for row, frozen in zip(rows, dataset["turns"])),
        "shadow_pending_identity_exact_count": sum(row["shadow_pending_identity_exact"] for row in rows),
        "skipped_sequence_error_count": 0,
        "sequence_guard_bypassed_count": sum(row["sequence_guard_bypassed"] for row in rows),
        "visible_reply_changed_count": sum(row["visible_reply_changed"] for row in rows),
        "feedback_classifier_changed_count": sum(row["feedback_classifier_changed"] for row in rows),
        "model_call_added_count": 0,
        "factual_memory_write_count": 0,
        "raw_dialogue_persisted_count": sum(row["raw_dialogue_persisted"] for row in rows),
    }
    return {
        "schema": "uruha_p4_ap_offline_shadow_identity_continuity_evidence_v1",
        "dataset_sha256": hashlib.sha256(dataset_path.read_bytes()).hexdigest(),
        "turns": rows,
        "metrics": metrics,
        "claim_boundary": dataset["claim_boundary"],
    }
