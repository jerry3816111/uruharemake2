"""P4-AQ same-turn delivery of a fixed P4-AH trigger to P4-AD/AF/AG/AM.

P4-AH is intentionally additive and therefore runs after the released P4-AD,
P4-AF, and P4-AG hooks.  When that late trace contains the already-authorized
compositional cognitive-overactivity trigger, this adapter rebuilds only the
raw-free downstream shadow chain.  It preserves the visible reply, released
detector and authority rules, candidate policy, feedback classifier, and
product memory.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path

import uruha_adaptive_person_model as adaptive
import uruha_desired_response_ambiguity_p4 as ambiguity
import uruha_desired_response_eligibility_p4 as eligibility
import uruha_desired_response_outcome_binding_p4 as outcome_binding
import uruha_multilingual_observable_trigger_p4 as trigger_coverage
import uruha_runtime_temporal_graph_delivery_p4 as temporal_delivery


LABEL = "live_extended_trigger_ordering_p4"
SCHEMA = "uruha_live_extended_trigger_ordering_p4"


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _extension_is_actionable(trace):
    return bool(
        ((trace or {}).get("coverage_extension") or {}).get("status")
        == "additive_compositional_trigger"
        and "cognitive_overactivity" in set((trace or {}).get("predicates") or [])
        and (trace or {}).get("private_state_truth_claimed") is False
    )


def _not_available_binding(turn_index=0):
    return {
        "schema": outcome_binding.SCHEMA,
        "status": "not_available",
        "turn_index": int(turn_index),
        "candidate_count": 0,
        "raw_dialogue_persisted": False,
    }


def append_live_ordering_node_p4(result, payload):
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
        (index for index, row in enumerate(blackboard) if row.get("label") == "utterance"),
        len(blackboard),
    )
    blackboard.insert(
        insert_at,
        {"stage": "route", "label": LABEL, "payload": payload, "salience": 0.99},
    )
    runtime["blackboard"] = blackboard
    runtime[LABEL] = payload
    result["runtime_trace"] = runtime
    return result


def deliver_existing_live_ordering_payload_after_turn_p4(result):
    """Reinsert the emit-time P4-AQ payload after the final trace refresh."""

    result = result or {}
    runtime = result.get("runtime_trace") or {}
    logic = result.get("logic") or {}
    payload = deepcopy(runtime.get(LABEL) or logic.get(LABEL) or {})
    if payload.get("schema") != SCHEMA:
        return result
    return append_live_ordering_node_p4(result, payload)


def rebuild_late_extended_trigger_chain_p4(result, temporal_state_before=None):
    """Return a repaired result plus state artifacts, or a strict no-op trace."""

    source = deepcopy(result or {})
    reply_before = source.get("reply")
    runtime = source.get("runtime_trace") or {}
    logic = source.get("logic") or {}
    trigger = deepcopy(
        runtime.get(trigger_coverage.LABEL)
        or logic.get(trigger_coverage.LABEL)
        or {}
    )
    ledger_before = deepcopy(
        runtime.get(ambiguity.LABEL) or logic.get(ambiguity.LABEL) or {}
    )
    ag_before = deepcopy(
        runtime.get(outcome_binding.LABEL)
        or logic.get(outcome_binding.LABEL)
        or {}
    )
    binding_before = deepcopy(ag_before.get("current_binding") or {})
    extension_actionable = _extension_is_actionable(trigger)
    already_available = bool(
        ledger_before.get("candidate_count") == 6
        and binding_before.get("status") == "pending"
    )
    should_repair = bool(
        extension_actionable
        and not already_available
        and binding_before.get("status") != "pending"
    )
    common = {
        "schema": SCHEMA,
        "mode": "raw_free_downstream_shadow_reorder",
        "trigger_evidence_digest": str(trigger.get("evidence_digest") or "")[:32],
        "trigger_detector_changed": False,
        "eligibility_authority_changed": False,
        "candidate_score_or_order_changed": False,
        "feedback_classifier_changed": False,
        "temporal_or_identity_rule_changed": False,
        "visible_reply_changed": False,
        "model_call_added": False,
        "factual_memory_write_count": 0,
        "raw_dialogue_persisted": False,
        "private_state_truth_claimed": False,
        "claim_boundary": (
            "same-turn raw-free shadow data-flow repair for an existing typed trigger; "
            "not private-state truth, response preference, or predictive validity"
        ),
    }
    if not should_repair:
        status = (
            "already_downstream_available"
            if already_available
            else "not_applicable"
        )
        trace = {
            **common,
            "status": status,
            "reason": (
                "six_candidate_binding_already_exists"
                if already_available
                else "no_actionable_late_extended_trigger"
            ),
            "before_candidate_count": int(ledger_before.get("candidate_count") or 0),
            "after_candidate_count": int(ledger_before.get("candidate_count") or 0),
            "before_binding_status": binding_before.get("status") or "not_available",
            "after_binding_status": binding_before.get("status") or "not_available",
            "after_future_status": (
                (
                    runtime.get(temporal_delivery.LABEL)
                    or logic.get(temporal_delivery.LABEL)
                    or {}
                ).get("future")
                or {}
            ).get("status")
            or "not_available",
            "previous_resolution_preserved": True,
            "source_state_mutated": False,
            "source_temporal_state_mutated": False,
        }
        output = append_live_ordering_node_p4(source, trace)
        return {
            "applied": False,
            "result": output,
            "trace": trace,
            "pending_binding": deepcopy(binding_before or _not_available_binding()),
            "shadow_feedback_model": None,
            "temporal_state": deepcopy(temporal_state_before),
        }

    state = deepcopy(
        runtime.get("desired_response_state_m18")
        or logic.get("desired_response_state_m18")
        or runtime.get("desired_response_state_m16")
        or logic.get("desired_response_state_m16")
        or {}
    )
    decision = deepcopy(
        runtime.get("desired_response_decision_m18")
        or logic.get("desired_response_decision_m18")
        or runtime.get("desired_response_decision_m16")
        or logic.get("desired_response_decision_m16")
        or {}
    )
    mode_contract = deepcopy(
        runtime.get("desired_response_mode_m23")
        or logic.get("desired_response_mode_m23")
        or {}
    )
    state_before = deepcopy(state)
    temporal_before = deepcopy(temporal_state_before)
    shadow_state = trigger_coverage.apply_extended_trigger_to_shadow_state_p4(
        state,
        trigger,
    )
    ledger = eligibility.build_desired_response_eligibility_guard_p4(
        shadow_state,
        decision,
        mode_contract,
    )
    turn_index = int((source.get("runtime_state") or {}).get("cycle_index") or 0)
    binding = outcome_binding.create_pending_outcome_binding_p4(
        ledger,
        decision,
        turn_index,
    )
    previous_resolution = deepcopy(
        ag_before.get("previous_resolution")
        or {
            "schema": outcome_binding.SCHEMA,
            "status": "not_available",
            "reason": "no_previous_p4_ag_binding",
            "raw_dialogue_persisted": False,
        }
    )
    shadow_feedback_model = outcome_binding.build_shadow_feedback_model_p4(
        binding,
        decision,
    )
    ag_trace = {
        "schema": outcome_binding.SCHEMA,
        "mode": "shadow_only",
        "previous_resolution": previous_resolution,
        "current_binding": binding,
        "visible_reply_changed": False,
        "model_call_added": False,
        "fact_write_count": 0,
        "profile_write_count": 0,
        "episode_write_count": 0,
        "raw_dialogue_persisted": False,
    }
    next_temporal_state, temporal_payload = temporal_delivery.advance_temporal_graph_delivery_p4(
        temporal_before,
        ag_trace,
        turn_index,
    )
    trace = {
        **common,
        "status": "repaired_extended_trigger_downstream_order",
        "reason": "p4_ah_trace_rebuilt_before_p4_ad_af_ag_am_shadow_outputs",
        "before_candidate_count": int(ledger_before.get("candidate_count") or 0),
        "after_candidate_count": int(ledger.get("candidate_count") or 0),
        "before_binding_status": binding_before.get("status") or "not_available",
        "after_binding_status": binding.get("status") or "not_available",
        "after_future_status": (temporal_payload.get("future") or {}).get("status")
        or "not_available",
        "eligibility_authority": (ledger.get("eligibility") or {}).get("authority"),
        "previous_resolution_preserved": previous_resolution
        == (ag_before.get("previous_resolution") or previous_resolution),
        "source_state_mutated": state != state_before,
        "source_temporal_state_mutated": temporal_state_before != temporal_before,
        "temporal_state_rewound_before_single_rebuild": True,
    }
    output = ambiguity.append_desired_response_ambiguity_node_p4(source, ledger)
    output = outcome_binding.append_outcome_binding_node_p4(output, ag_trace)
    output = temporal_delivery.append_temporal_graph_delivery_node_p4(
        output,
        temporal_payload,
    )
    output = append_live_ordering_node_p4(output, trace)
    if output.get("reply") != reply_before:
        raise ValueError("p4_aq_visible_reply_changed")
    return {
        "applied": True,
        "result": output,
        "trace": trace,
        "ledger": ledger,
        "ag_trace": ag_trace,
        "pending_binding": binding,
        "shadow_feedback_model": shadow_feedback_model,
        "temporal_state": next_temporal_state,
        "temporal_payload": temporal_payload,
    }


_INSTALLED_P4_AQ = False
_ORIGINAL_EMIT_RESPONSE_P4_AQ = None
_ORIGINAL_RUN_TURN_P4_AQ = None


def install_live_extended_trigger_ordering_p4():
    global _INSTALLED_P4_AQ, _ORIGINAL_EMIT_RESPONSE_P4_AQ, _ORIGINAL_RUN_TURN_P4_AQ
    if _INSTALLED_P4_AQ:
        return False
    from uruha_brain_mac import UruhaBrainV4_Mac

    _ORIGINAL_EMIT_RESPONSE_P4_AQ = UruhaBrainV4_Mac.emit_response_if_ready
    _ORIGINAL_RUN_TURN_P4_AQ = UruhaBrainV4_Mac.run_turn_debug

    def emit_with_p4_aq(self, event, tick_result):
        temporal_state_before = deepcopy(
            getattr(self, "_p4_am_temporal_delivery_state", None)
        )
        result = _ORIGINAL_EMIT_RESPONSE_P4_AQ(self, event, tick_result)
        repaired = rebuild_late_extended_trigger_chain_p4(
            result,
            temporal_state_before,
        )
        result = repaired["result"]
        if repaired["applied"]:
            self._p4_ag_pending_binding = deepcopy(repaired["pending_binding"])
            self._p4_ag_shadow_feedback_model = deepcopy(
                repaired["shadow_feedback_model"]
            )
            self._p4_am_temporal_delivery_state = deepcopy(repaired["temporal_state"])
        if getattr(self.runtime, "turn_traces", None):
            self.runtime.turn_traces[-1] = deepcopy(result["runtime_trace"])
        return result

    UruhaBrainV4_Mac.emit_response_if_ready = emit_with_p4_aq

    def run_turn_with_p4_aq(self, user_input, input_context=None):
        result = _ORIGINAL_RUN_TURN_P4_AQ(
            self,
            user_input,
            input_context=input_context,
        )
        result = deliver_existing_live_ordering_payload_after_turn_p4(result)
        if getattr(self.runtime, "turn_traces", None):
            self.runtime.turn_traces[-1] = deepcopy(result["runtime_trace"])
        return result

    UruhaBrainV4_Mac.run_turn_debug = run_turn_with_p4_aq
    _INSTALLED_P4_AQ = True
    return True


def _fixture_inputs(frozen, turn_index):
    state, decision, mode = ambiguity._isolated_inputs(frozen["input"], turn_index)
    if frozen.get("predecessor_fixture") == "preserved_p4_an_runtime_general_conversation_mode":
        mode = adaptive.build_desired_response_mode_contract(
            {"selected_type": "general_conversation"},
            state,
            decision,
        )
    return state, decision, mode


def _synthetic_predecessor_result(frozen, turn_index):
    state, decision, mode = _fixture_inputs(frozen, turn_index)
    base_trigger = deepcopy(state.get("observable_trigger_m37") or {})
    extended = trigger_coverage.extend_observable_trigger_p4(
        frozen["input"],
        base_trigger,
    )
    ledger = eligibility.build_desired_response_eligibility_guard_p4(
        state,
        decision,
        mode,
    )
    binding = outcome_binding.create_pending_outcome_binding_p4(
        ledger,
        decision,
        turn_index,
    )
    ag_trace = {
        "schema": outcome_binding.SCHEMA,
        "mode": "shadow_only",
        "previous_resolution": {
            "schema": outcome_binding.SCHEMA,
            "status": "not_available",
            "reason": "no_previous_p4_ag_binding",
            "raw_dialogue_persisted": False,
        },
        "current_binding": binding,
        "visible_reply_changed": False,
        "model_call_added": False,
        "fact_write_count": 0,
        "profile_write_count": 0,
        "episode_write_count": 0,
        "raw_dialogue_persisted": False,
    }
    temporal_state_before = temporal_delivery.initial_delivery_state_p4()
    _after, temporal_payload = temporal_delivery.advance_temporal_graph_delivery_p4(
        temporal_state_before,
        ag_trace,
        turn_index,
    )
    blackboard = [
        {"stage": "select", "label": ambiguity.LABEL, "payload": deepcopy(ledger)},
        {"stage": "learn", "label": outcome_binding.LABEL, "payload": deepcopy(ag_trace)},
        {"stage": "perceive", "label": trigger_coverage.LABEL, "payload": deepcopy(extended)},
        {"stage": "predict", "label": temporal_delivery.LABEL, "payload": deepcopy(temporal_payload)},
        {"stage": "surface", "label": "utterance", "payload": {}},
    ]
    result = {
        "reply": f"unchanged-p4-aq-{frozen['case_id']}",
        "runtime_state": {"cycle_index": turn_index},
        "logic": {
            "desired_response_state_m18": deepcopy(state),
            "desired_response_decision_m18": deepcopy(decision),
            "desired_response_mode_m23": deepcopy(mode),
            ambiguity.LABEL: deepcopy(ledger),
            outcome_binding.LABEL: deepcopy(ag_trace),
            trigger_coverage.LABEL: deepcopy(extended),
            temporal_delivery.LABEL: deepcopy(temporal_payload),
        },
        "runtime_trace": {
            "desired_response_state_m18": deepcopy(state),
            "desired_response_decision_m18": deepcopy(decision),
            "desired_response_mode_m23": deepcopy(mode),
            ambiguity.LABEL: deepcopy(ledger),
            outcome_binding.LABEL: deepcopy(ag_trace),
            trigger_coverage.LABEL: deepcopy(extended),
            temporal_delivery.LABEL: deepcopy(temporal_payload),
            "blackboard": blackboard,
        },
    }
    return result, temporal_state_before, base_trigger, ledger


def build_dataset_evidence_p4_aq(dataset_path):
    dataset_path = Path(dataset_path)
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    cases = []
    partitions = ("development_cases", "fresh_positive_cases", "fresh_control_cases")
    for partition_index, partition in enumerate(partitions):
        for row_index, frozen in enumerate(dataset[partition]):
            turn_index = 900 + partition_index * 100 + row_index + 1
            result, temporal_before, base_trigger, ledger_before = _synthetic_predecessor_result(
                frozen,
                turn_index,
            )
            source_state = deepcopy(
                result["runtime_trace"]["desired_response_state_m18"]
            )
            source_temporal = deepcopy(temporal_before)
            reply_before = result["reply"]
            rebuilt = rebuild_late_extended_trigger_chain_p4(result, temporal_before)
            after = rebuilt["result"]
            trace = rebuilt["trace"]
            ledger_after = (
                after["runtime_trace"].get(ambiguity.LABEL) or {}
            )
            ag_after = after["runtime_trace"].get(outcome_binding.LABEL) or {}
            binding_after = ag_after.get("current_binding") or {}
            temporal_after = after["runtime_trace"].get(temporal_delivery.LABEL) or {}
            labels = [entry.get("label") for entry in after["runtime_trace"]["blackboard"]]
            if rebuilt["applied"]:
                expected_order = [
                    trigger_coverage.LABEL,
                    ambiguity.LABEL,
                    outcome_binding.LABEL,
                    temporal_delivery.LABEL,
                    LABEL,
                    "utterance",
                ]
            else:
                expected_order = [
                    ambiguity.LABEL,
                    outcome_binding.LABEL,
                    trigger_coverage.LABEL,
                    temporal_delivery.LABEL,
                    LABEL,
                    "utterance",
                ]
            serialized = _canonical(
                {
                    "trace": trace,
                    "ledger": ledger_after,
                    "binding": binding_after,
                    "temporal": temporal_after,
                }
            )
            cases.append(
                {
                    "case_id": frozen["case_id"],
                    "partition": partition,
                    "base_trigger_missed": not bool(base_trigger.get("predicates")),
                    "extended_trigger_hit": _extension_is_actionable(
                        after["runtime_trace"].get(trigger_coverage.LABEL) or {}
                    ),
                    "predecessor_candidate_count": int(ledger_before.get("candidate_count") or 0),
                    "repair_status": trace.get("status"),
                    "candidate_count": int(ledger_after.get("candidate_count") or 0),
                    "eligibility_authority": (ledger_after.get("eligibility") or {}).get("authority"),
                    "binding_status": binding_after.get("status") or "not_available",
                    "future_status": (temporal_after.get("future") or {}).get("status") or "not_available",
                    "candidate_ranking_changed": trace.get("candidate_score_or_order_changed"),
                    "source_state_mutated": source_state
                    != result["runtime_trace"]["desired_response_state_m18"],
                    "source_temporal_state_mutated": source_temporal != temporal_before,
                    "visible_reply_changed": after.get("reply") != reply_before,
                    "model_call_added": trace.get("model_call_added"),
                    "factual_memory_write_count": trace.get("factual_memory_write_count"),
                    "raw_dialogue_persisted": bool(
                        trace.get("raw_dialogue_persisted")
                        or frozen["input"] in serialized
                    ),
                    "exact_graph_order": [label for label in labels if label in expected_order]
                    == expected_order,
                }
            )
    development = [row for row in cases if row["partition"] == "development_cases"]
    positives = [row for row in cases if row["partition"] in {"development_cases", "fresh_positive_cases"}]
    fresh_positives = [row for row in cases if row["partition"] == "fresh_positive_cases"]
    controls = [row for row in cases if row["partition"] == "fresh_control_cases"]
    return {
        "schema": "uruha_p4_aq_live_extended_trigger_ordering_evidence_v1",
        "dataset_sha256": hashlib.sha256(dataset_path.read_bytes()).hexdigest(),
        "cases": cases,
        "metrics": {
            "case_count": len(cases),
            "development_reproduction_count": sum(
                row["predecessor_candidate_count"] == 0
                and row["repair_status"] == "repaired_extended_trigger_downstream_order"
                for row in development
            ),
            "fresh_positive_base_miss_count": sum(row["base_trigger_missed"] for row in fresh_positives),
            "fresh_positive_extended_hit_count": sum(row["extended_trigger_hit"] for row in fresh_positives),
            "fresh_control_extended_abstention_count": sum(not row["extended_trigger_hit"] for row in controls),
            "positive_repaired_status_count": sum(row["repair_status"] == "repaired_extended_trigger_downstream_order" for row in positives),
            "positive_six_candidate_count": sum(row["candidate_count"] == 6 for row in positives),
            "positive_typed_authority_count": sum(row["eligibility_authority"] == "typed_cognitive_overactivity" for row in positives),
            "positive_pending_binding_count": sum(row["binding_status"] == "pending" for row in positives),
            "positive_future_locked_count": sum(row["future_status"] == "committed_outcome_locked" for row in positives),
            "control_not_applicable_count": sum(row["repair_status"] == "not_applicable" for row in controls),
            "control_zero_candidate_count": sum(row["candidate_count"] == 0 for row in controls),
            "control_no_binding_count": sum(row["binding_status"] == "not_available" for row in controls),
            "control_no_future_commitment_count": sum(row["future_status"] == "not_available" for row in controls),
            "candidate_ranking_changed_count": sum(row["candidate_ranking_changed"] is not False for row in cases),
            "source_state_mutation_count": sum(row["source_state_mutated"] for row in cases),
            "source_temporal_state_mutation_count": sum(row["source_temporal_state_mutated"] for row in cases),
            "visible_reply_changed_count": sum(row["visible_reply_changed"] for row in cases),
            "model_call_added_count": sum(bool(row["model_call_added"]) for row in cases),
            "factual_memory_write_count": sum(int(row["factual_memory_write_count"] or 0) for row in cases),
            "raw_dialogue_persisted_count": sum(row["raw_dialogue_persisted"] for row in cases),
            "exact_graph_order_count": sum(row["exact_graph_order"] for row in cases),
        },
        "claim_boundary": dataset["claim_boundary"],
    }
