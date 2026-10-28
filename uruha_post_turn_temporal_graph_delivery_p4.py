"""P4-AN post-run-turn delivery of the existing P4-AM temporal payload.

P4-AM established the temporal state machine but its emit-time blackboard node
was overwritten by the final ``run_turn_debug`` refresh.  This module changes
only delivery timing: it reuses the already-computed raw-free payload after the
refresh and inserts it before the utterance node.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path

import uruha_desired_response_outcome_binding_p4 as outcome_binding
import uruha_past_present_future_commitment_p4 as temporal
import uruha_runtime_temporal_graph_delivery_p4 as p4_am


SCHEMA = "uruha_post_turn_temporal_graph_delivery_p4"


def deliver_existing_temporal_payload_after_turn_p4(result):
    """Insert the existing P4-AM payload into the final blackboard only."""

    result = result or {}
    runtime = result.get("runtime_trace") or {}
    logic = result.get("logic") or {}
    payload = deepcopy(runtime.get(p4_am.LABEL) or logic.get(p4_am.LABEL) or {})
    if payload.get("schema") != p4_am.SCHEMA:
        return result
    return p4_am.append_temporal_graph_delivery_node_p4(result, payload)


_INSTALLED_P4_AN = False
_ORIGINAL_RUN_TURN_P4_AN = None


def install_post_turn_temporal_graph_delivery_p4():
    global _INSTALLED_P4_AN, _ORIGINAL_RUN_TURN_P4_AN
    if _INSTALLED_P4_AN:
        return False
    from uruha_brain_mac import UruhaBrainV4_Mac

    _ORIGINAL_RUN_TURN_P4_AN = UruhaBrainV4_Mac.run_turn_debug

    def run_turn_with_p4_an(self, user_input, input_context=None):
        result = _ORIGINAL_RUN_TURN_P4_AN(self, user_input, input_context=input_context)
        result = deliver_existing_temporal_payload_after_turn_p4(result)
        if getattr(self.runtime, "turn_traces", None):
            self.runtime.turn_traces[-1] = deepcopy(result["runtime_trace"])
        return result

    UruhaBrainV4_Mac.run_turn_debug = run_turn_with_p4_an
    _INSTALLED_P4_AN = True
    return True


def build_offline_evidence_p4_an(dataset_path):
    dataset_path = Path(dataset_path)
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    state = p4_am.initial_delivery_state_p4()
    rows = []
    previous_pending = None
    for ordinal, frozen in enumerate(dataset["turns"], start=1):
        runtime_turn = 200 + ordinal
        pending = temporal._synthetic_pending(
            {
                "case_id": f"{dataset['case_id']}-turn-{ordinal}",
                "selected_policy": "calibrate_need",
                "current_turn": runtime_turn,
            }
        )
        previous = (
            p4_am._supported_resolution(previous_pending, runtime_turn)
            if previous_pending is not None
            else {"schema": outcome_binding.SCHEMA, "status": "not_available"}
        )
        state, payload = p4_am.advance_temporal_graph_delivery_p4(
            state,
            {
                "schema": outcome_binding.SCHEMA,
                "previous_resolution": previous,
                "current_binding": pending,
            },
            runtime_turn,
        )
        # Reproduce the real P4-AM failure boundary: top-level payload survives,
        # but the final blackboard refresh contains no P4-AM node.
        result = {
            "reply": "unchanged",
            "logic": {p4_am.LABEL: deepcopy(payload)},
            "runtime_trace": {
                p4_am.LABEL: deepcopy(payload),
                "blackboard": [
                    {"stage": "learn", "label": "memory_updates", "payload": {}},
                    {"stage": "surface", "label": "utterance", "payload": {}},
                ],
            },
        }
        before_reply = result["reply"]
        result = deliver_existing_temporal_payload_after_turn_p4(result)
        blackboard = result["runtime_trace"]["blackboard"]
        labels = [row.get("label") for row in blackboard]
        serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        rows.append(
            {
                "turn": frozen["turn"],
                "past_record_count": payload["past"]["record_count"],
                "present_candidate_count": payload["present"]["candidate_count"],
                "current_future_status": payload["future"]["status"],
                "previous_outcome": payload["present"]["previous_outcome_verification"],
                "graph_summary": payload["summary"],
                "node_before_utterance": labels.index(p4_am.LABEL) < labels.index("utterance"),
                "logic_graph_payload_exact": (
                    result["logic"][p4_am.LABEL]
                    == result["runtime_trace"][p4_am.LABEL]
                    == next(
                        row["payload"] for row in blackboard if row.get("label") == p4_am.LABEL
                    )
                ),
                "final_blackboard_contains_node": p4_am.LABEL in labels,
                "raw_or_private_payload_leak": any(
                    frozen_row["input"] in serialized for frozen_row in dataset["turns"]
                ),
                "same_turn_outcome_promoted_to_past": payload["transition"]["same_turn_outcome_promoted_to_past"],
                "visible_reply_changed": result["reply"] != before_reply,
            }
        )
        previous_pending = pending

    metrics = {
        "turn_count": len(rows),
        "temporal_node_count": len(rows),
        "node_before_utterance_count": sum(row["node_before_utterance"] for row in rows),
        "logic_graph_payload_exact_count": sum(row["logic_graph_payload_exact"] for row in rows),
        "final_blackboard_contains_node_count": sum(row["final_blackboard_contains_node"] for row in rows),
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
        "visible_reply_changed_count": sum(row["visible_reply_changed"] for row in rows),
        "model_call_added_count": 0,
        "factual_memory_write_count": 0,
    }
    return {
        "schema": "uruha_p4_an_offline_post_turn_temporal_graph_evidence_v1",
        "dataset_sha256": hashlib.sha256(dataset_path.read_bytes()).hexdigest(),
        "turns": rows,
        "metrics": metrics,
        "claim_boundary": dataset["claim_boundary"],
    }
