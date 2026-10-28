"""P4-AM runtime delivery for an auditable past-present-future graph.

The adapter consumes the released P4-AG shadow outcome binding.  A result
observed on the current turn remains a current verification and is only
eligible to become past evidence on a later turn.  It never writes factual
memory or changes the visible reply.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path

import uruha_desired_response_outcome_binding_p4 as outcome_binding
import uruha_past_present_future_commitment_p4 as temporal


SCHEMA = "uruha_runtime_temporal_graph_delivery_p4"
LABEL = "runtime_temporal_graph_delivery_p4"
_PAST_FIELDS = {
    "evidence_id",
    "observed_turn",
    "source_kind",
    "epistemic_status",
    "provenance_digest",
}


class P4AMTemporalDeliveryError(ValueError):
    pass


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value):
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _empty_past_commitment(pending_binding, present_turn):
    """Build the first honest commitment without inventing a past record."""

    pending = deepcopy(pending_binding or {})
    present_turn = int(present_turn)
    candidates = pending.get("candidate_snapshots") or []
    if (
        pending.get("schema") != outcome_binding.SCHEMA
        or pending.get("status") != "pending"
        or pending.get("turn_index") != present_turn
        or pending.get("candidate_count") != 6
        or len(candidates) != 6
    ):
        raise P4AMTemporalDeliveryError("pending_binding_invalid")
    present_candidates = [
        {
            "candidate_id": row.get("candidate_id"),
            "policy_id": row.get("policy_id"),
            "mode": row.get("mode"),
            "operational_action_score": row.get("operational_action_score"),
            "score_semantics": row.get("score_semantics"),
            "selected": row.get("policy_id") == pending.get("selected_policy"),
            "epistemic_status": "inferred_operational_action_hypothesis",
            "private_truth_claimed": False,
        }
        for row in candidates
    ]
    material = {
        "schema": temporal.SCHEMA,
        "version": "1.0.0",
        "past": {
            "status": "no_prior_verified_evidence",
            "records": [],
            "record_count": 0,
            "strictly_before_present": True,
        },
        "present": {
            "turn_index": present_turn,
            "input_digest": pending.get("input_digest"),
            "ledger_id": pending.get("ledger_id"),
            "prediction_id": pending.get("prediction_id"),
            "known": ["no_prior_verified_evidence", "current_input_digest"],
            "inferred": present_candidates,
            "unknown": [
                "private_reason_for_current_utterance",
                "which_response_will_be_accepted",
                "next_turn_observable_outcome",
            ],
            "selected_policy": pending.get("selected_policy"),
            "candidate_count": len(present_candidates),
            "selection_is_private_truth_commitment": False,
        },
        "future": {
            "status": "committed_outcome_locked",
            "target": "next_turn_linked_response_action_feedback",
            "earliest_observable_turn": present_turn + 1,
            "selected_policy_prediction": pending.get("selected_policy"),
            "possible_outcomes": ["supported", "contradicted", "unknown"],
            "outcome_accessed": False,
            "candidate_score_is_calibrated_human_probability": False,
        },
        "boundaries": {
            "past_lt_present_lt_future": True,
            "future_content_in_present": False,
            "private_state_truth_claimed": False,
            "raw_dialogue_persisted": False,
            "factual_memory_write_allowed": False,
        },
    }
    return {
        **material,
        "commitment_hash": _digest(material),
        "claim_boundary": (
            "honest empty-past next-turn action commitment; not private-state "
            "truth or evidence of real-person predictive validity"
        ),
    }


def _build_commitment(past_records, pending_binding, present_turn):
    if past_records:
        return temporal.build_temporal_commitment_p4(
            past_records,
            pending_binding,
            present_turn,
        )
    return _empty_past_commitment(pending_binding, present_turn)


def _past_projection(record):
    projected = {key: deepcopy(record.get(key)) for key in _PAST_FIELDS}
    if set(projected) != _PAST_FIELDS:
        raise P4AMTemporalDeliveryError("past_projection_invalid")
    return projected


def initial_delivery_state_p4():
    return {
        "past_records": [],
        "queued_past_records": [],
        "previous_commitment": {},
    }


def advance_temporal_graph_delivery_p4(state, p4_ag_trace, present_turn):
    """Advance one turn while keeping current verification out of current past."""

    present_turn = int(present_turn)
    state = deepcopy(state or initial_delivery_state_p4())
    past_records = list(state.get("past_records") or [])
    queued = list(state.get("queued_past_records") or [])

    promoted = [row for row in queued if int(row.get("observed_turn", -1)) < present_turn]
    queued = [row for row in queued if int(row.get("observed_turn", -1)) >= present_turn]
    known_ids = {row.get("evidence_id") for row in past_records}
    for row in promoted:
        if row.get("evidence_id") not in known_ids:
            past_records.append(deepcopy(row))
            known_ids.add(row.get("evidence_id"))
    past_records.sort(key=lambda row: (row["observed_turn"], row["evidence_id"]))

    trace = deepcopy(p4_ag_trace or {})
    previous_resolution = deepcopy(trace.get("previous_resolution") or {})
    previous_commitment = deepcopy(state.get("previous_commitment") or {})
    resolved_temporal = {}
    previous_outcome = None
    if previous_resolution.get("status") == "resolved" and previous_commitment:
        resolved_temporal = temporal.resolve_temporal_commitment_p4(
            previous_commitment,
            previous_resolution,
        )
        queued.append(_past_projection(resolved_temporal["next_past_record"]))
        previous_outcome = resolved_temporal.get("outcome")

    current_binding = deepcopy(trace.get("current_binding") or {})
    current_commitment = {}
    if current_binding.get("status") == "pending":
        current_commitment = _build_commitment(
            past_records,
            current_binding,
            present_turn,
        )

    candidate_count = int((current_commitment.get("present") or {}).get("candidate_count") or 0)
    future_status = (current_commitment.get("future") or {}).get("status") or "not_available"
    selected_policy = (current_commitment.get("present") or {}).get("selected_policy")
    past_count = len(past_records)
    summary_parts = [f"過去 {past_count}", f"現在 {candidate_count}候選/選択 {selected_policy or 'なし'}"]
    if promoted:
        summary_parts.append("既有驗證→過去")
    if previous_outcome:
        summary_parts.append(f"前輪 {previous_outcome}→本輪驗證")
    summary_parts.append("本輪未來 已封存" if future_status == "committed_outcome_locked" else "本輪未來 無承諾")

    payload = {
        "schema": SCHEMA,
        "summary": "｜".join(summary_parts),
        "past": {
            "record_count": past_count,
            "statuses": [row.get("epistemic_status") for row in past_records],
            "strictly_before_present": all(
                int(row.get("observed_turn", -1)) < present_turn for row in past_records
            ),
        },
        "present": {
            "turn_index": present_turn,
            "candidate_count": candidate_count,
            "selected_policy": selected_policy,
            "previous_outcome_verification": previous_outcome,
            "previous_outcome_is_current_past": False,
            "private_truth_unknown": True,
        },
        "future": {
            "status": future_status,
            "target": (current_commitment.get("future") or {}).get("target"),
            "outcome_accessed": False,
        },
        "transition": {
            "promoted_prior_verification_count": len(promoted),
            "current_verification_queued_for_later": bool(resolved_temporal),
            "same_turn_outcome_promoted_to_past": False,
        },
        "commitment_hash": current_commitment.get("commitment_hash"),
        "raw_dialogue_persisted": False,
        "private_state_truth_claimed": False,
        "visible_reply_changed": False,
        "model_call_added": False,
        "factual_memory_write_count": 0,
    }
    next_state = {
        "past_records": past_records,
        "queued_past_records": queued,
        "previous_commitment": current_commitment,
    }
    return next_state, payload


def append_temporal_graph_delivery_node_p4(result, payload):
    result = result or {}
    payload = deepcopy(payload or {})
    logic = result.get("logic") or {}
    logic[LABEL] = payload
    result["logic"] = logic
    runtime = result.get("runtime_trace") or {}
    blackboard = [row for row in (runtime.get("blackboard") or []) if row.get("label") != LABEL]
    insert_at = next(
        (index for index, row in enumerate(blackboard) if row.get("label") == "utterance"),
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


_INSTALLED_P4_AM = False
_ORIGINAL_EMIT_RESPONSE_P4_AM = None


def install_runtime_temporal_graph_delivery_p4():
    global _INSTALLED_P4_AM, _ORIGINAL_EMIT_RESPONSE_P4_AM
    if _INSTALLED_P4_AM:
        return False
    from uruha_brain_mac import UruhaBrainV4_Mac

    _ORIGINAL_EMIT_RESPONSE_P4_AM = UruhaBrainV4_Mac.emit_response_if_ready

    def emit_with_p4_am(self, event, tick_result):
        result = _ORIGINAL_EMIT_RESPONSE_P4_AM(self, event, tick_result)
        runtime = (result or {}).get("runtime_trace") or {}
        logic = (result or {}).get("logic") or {}
        p4_ag_trace = runtime.get(outcome_binding.LABEL) or logic.get(outcome_binding.LABEL) or {}
        present_turn = int((result or {}).get("runtime_state", {}).get("cycle_index") or 0)
        state, payload = advance_temporal_graph_delivery_p4(
            getattr(self, "_p4_am_temporal_delivery_state", None),
            p4_ag_trace,
            present_turn,
        )
        self._p4_am_temporal_delivery_state = state
        result = append_temporal_graph_delivery_node_p4(result, payload)
        if getattr(self.runtime, "turn_traces", None):
            self.runtime.turn_traces[-1] = deepcopy(result["runtime_trace"])
        return result

    UruhaBrainV4_Mac.emit_response_if_ready = emit_with_p4_am
    _INSTALLED_P4_AM = True
    return True


def _supported_resolution(pending, observed_turn):
    return outcome_binding.resolve_outcome_binding_p4(
        pending,
        {
            "previous_prediction_id": pending["prediction_id"],
            "feedback_linked_to_previous_prediction": True,
            "status": "supported",
            "explicit_target_policy": None,
            "feedback_linkage_reason": "p4_am_frozen_offline_fixture",
            "evidence": {"digest": _digest({"turn": observed_turn})[:32]},
        },
        observed_turn,
    )


def build_offline_evidence_p4_am(dataset_path):
    dataset_path = Path(dataset_path)
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    state = initial_delivery_state_p4()
    rows = []
    previous_pending = None
    for ordinal, frozen in enumerate(dataset["turns"], start=1):
        runtime_turn = 100 + ordinal
        pending = temporal._synthetic_pending(
            {
                "case_id": f"{dataset['case_id']}-turn-{ordinal}",
                "selected_policy": "calibrate_need",
                "current_turn": runtime_turn,
            }
        )
        previous = (
            _supported_resolution(previous_pending, runtime_turn)
            if previous_pending is not None
            else {"schema": outcome_binding.SCHEMA, "status": "not_available"}
        )
        state, payload = advance_temporal_graph_delivery_p4(
            state,
            {
                "schema": outcome_binding.SCHEMA,
                "previous_resolution": previous,
                "current_binding": pending,
            },
            runtime_turn,
        )
        result = append_temporal_graph_delivery_node_p4(
            {
                "reply": "unchanged",
                "logic": {},
                "runtime_trace": {
                    "blackboard": [{"stage": "surface", "label": "utterance", "payload": {}}]
                },
            },
            payload,
        )
        blackboard = result["runtime_trace"]["blackboard"]
        labels = [row.get("label") for row in blackboard]
        serialized = _canonical(payload)
        rows.append(
            {
                "turn": frozen["turn"],
                "past_record_count": payload["past"]["record_count"],
                "present_candidate_count": payload["present"]["candidate_count"],
                "current_future_status": payload["future"]["status"],
                "previous_outcome": payload["present"]["previous_outcome_verification"],
                "graph_summary": payload["summary"],
                "node_before_utterance": labels.index(LABEL) < labels.index("utterance"),
                "logic_graph_payload_exact": (
                    result["logic"][LABEL] == result["runtime_trace"][LABEL] == payload
                ),
                "raw_or_private_payload_leak": any(
                    frozen_row["input"] in serialized for frozen_row in dataset["turns"]
                ),
                "same_turn_outcome_promoted_to_past": payload["transition"]["same_turn_outcome_promoted_to_past"],
            }
        )
        previous_pending = pending

    metrics = {
        "turn_count": len(rows),
        "temporal_node_count": len(rows),
        "node_before_utterance_count": sum(row["node_before_utterance"] for row in rows),
        "logic_graph_payload_exact_count": sum(row["logic_graph_payload_exact"] for row in rows),
        "first_turn_empty_past_count": int(rows[0]["past_record_count"] == 0),
        "second_turn_current_verification_not_past_count": int(
            rows[1]["past_record_count"] == 0 and rows[1]["previous_outcome"] == "supported"
        ),
        "third_turn_verified_past_count": int(rows[2]["past_record_count"] == 1),
        "six_candidate_present_count": sum(row["present_candidate_count"] == 6 for row in rows),
        "current_future_locked_count": sum(
            row["current_future_status"] == "committed_outcome_locked" for row in rows
        ),
        "previous_supported_transition_count": sum(
            row["previous_outcome"] == "supported" for row in rows
        ),
        "same_turn_outcome_promoted_to_past_count": sum(
            row["same_turn_outcome_promoted_to_past"] for row in rows
        ),
        "raw_or_private_payload_leak_count": sum(row["raw_or_private_payload_leak"] for row in rows),
        "visible_reply_changed_count": 0,
        "model_call_added_count": 0,
        "factual_memory_write_count": 0,
    }
    return {
        "schema": "uruha_p4_am_offline_temporal_graph_evidence_v1",
        "dataset_sha256": hashlib.sha256(dataset_path.read_bytes()).hexdigest(),
        "turns": rows,
        "metrics": metrics,
        "claim_boundary": dataset["claim_boundary"],
    }
