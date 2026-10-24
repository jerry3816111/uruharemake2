"""P4-AU: bind an exact prior user problem source to the current action request.

P4-AT can distinguish feedback about an earlier executed clarification from a
new request for practical help.  P4-AU changes one later variable only: under
an exact next-turn receipt and bounded observable-source checks, it makes the
immediately preceding USER problem statement available to the existing M45
delivery gate.  It neither generates an action nor relaxes M39/M45.
"""

from __future__ import annotations

from contextvars import ContextVar
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re

import uruha_actionable_help_delivery_m45 as action45
import uruha_adaptive_person_model as adaptive
import uruha_crosslingual_help_routing_m47 as help_route
import uruha_executed_action_outcome_closure_p4 as p4_at
import uruha_japanese_trigger_morphology_p4 as morphology
import uruha_multilingual_observable_trigger_p4 as trigger
import uruha_semantic_persona_surface_m39 as surface39


LABEL = "source_bound_current_action_delivery_p4"
SCHEMA = "uruha_source_bound_current_action_delivery_p4"
MAX_PRIOR_SOURCE_CHARS = 2000

_TRACE = ContextVar("p4_au_source_trace", default=None)
_INSTALLED_P4_AU = False
_ORIGINAL_SOURCE_PACKET_P4_AU = action45.source_packet
_ORIGINAL_MATERIALIZE_P4_AU = action45.materialize_trace_m45


def _digest(value):
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()[:16]


def _feedback_span(text):
    return bool(
        p4_at._last_match(p4_at._SUPPORT_PATTERNS, str(text or ""))
        or p4_at._last_match(p4_at._CONTRADICTION_PATTERNS, str(text or ""))
    )


def _current_nonfeedback_task_refs(user_input):
    text = str(user_input or "")
    route = help_route.classify_help_route_m47(text)
    refs = []
    for raw in route.get("task_spans") or []:
        try:
            start, end = int(raw.get("start")), int(raw.get("end"))
        except (TypeError, ValueError):
            continue
        if start < 0 or end <= start or end > len(text):
            continue
        raw_span = text[start:end]
        for match in re.finditer(r"[^。！？!?；;.\n]+", raw_span):
            segment_start = start + match.start()
            segment_end = start + match.end()
            span = match.group().strip(" \t\r\n，,、；;。.!！?？")
            if not span or _feedback_span(span):
                continue
            # M47 can expose a short prefix such as "今は具体的な" that only
            # modifies the adjacent response-form request.  It is not an
            # independent task.  Longer non-feedback material remains a
            # conservative current-task replacement.
            frame = surface39._source_frame_m39(span)
            if len(span) <= 8 and not frame.get("observable_concepts"):
                continue
            refs.append(
                {
                    "start": segment_start,
                    "length": segment_end - segment_start,
                    "span_digest": _digest(match.group()),
                    "role": raw.get("role"),
                }
            )
    return route, refs


def _prior_trigger(prior_text):
    predecessor = trigger.extend_observable_trigger_p4(prior_text)
    return morphology.extend_japanese_morphology_p4(prior_text, predecessor)


def bind_prior_problem_source_p4_au(
    user_input,
    memory_data,
    feedback,
    turn_index,
    base_sources,
):
    """Return a new transient source packet plus a raw-free authority trace."""

    original_sources = deepcopy(list(base_sources or []))
    sources = deepcopy(original_sources)
    closure = deepcopy((feedback or {}).get(p4_at.LABEL) or {})
    current_route, current_task_refs = _current_nonfeedback_task_refs(user_input)
    recent = (memory_data or {}).get("recent_turns") or []
    prior = recent[-1] if recent and isinstance(recent[-1], dict) else {}
    prior_text = prior.get("user") if isinstance(prior.get("user"), str) else ""

    status = "prior_source_linked"
    reason = "exact_previous_problem_authorized_for_current_practical_action"
    if not (
        closure.get("exact_pending_receipt_identity") is True
        and closure.get("performed_policy") == "calibrate_need"
        and closure.get("performed_action_strictly_earlier") is True
        and int(closure.get("observed_turn") or -1) == int(turn_index)
    ):
        status, reason = "blocked_exact_action_identity", "exact_next_turn_receipt_not_available"
    elif closure.get("previous_action_outcome") != "supported" or closure.get("two_independent_acts") is not True:
        status, reason = "blocked_no_decisive_action_feedback", "earlier_action_not_explicitly_supported"
    elif closure.get("current_request_policy") != "solve_regulation":
        status, reason = "blocked_current_policy", "current_request_is_not_practical_help"
    elif closure.get("source_authorized") is not True:
        status, reason = "blocked_current_source_role", "current_feedback_is_not_direct_user_evidence"
    elif current_task_refs:
        status, reason = "blocked_current_task_replacement", "current_turn_contains_independent_task_source"
    elif not prior_text:
        status, reason = "blocked_prior_source_missing", "immediately_preceding_user_source_missing"
    elif len(prior_text) > MAX_PRIOR_SOURCE_CHARS:
        status, reason = "blocked_prior_source_budget", "prior_user_source_exceeds_budget"
    else:
        frame = surface39._source_frame_m39(prior_text)
        prior_trigger = _prior_trigger(prior_text)
        trigger_languages = set(prior_trigger.get("matched_languages") or [])
        japanese_subject_ellipsis = bool(
            "ja" in trigger_languages
            and frame.get("speaker_role") == "unspecified"
            and frame.get("third_party_present") is False
            and p4_at._source_is_direct(prior_text)
        )
        if frame.get("third_party_present") is True:
            status, reason = "blocked_prior_source_role", "prior_source_not_direct_user_first_person"
        elif not p4_at._source_is_direct(prior_text):
            status, reason = "blocked_prior_trigger", "prior_source_is_metalinguistic_or_quoted"
        elif (
            frame.get("speaker_role") != "user_first_person"
            and not japanese_subject_ellipsis
        ):
            status, reason = "blocked_prior_source_role", "prior_source_not_direct_user_first_person"
        elif "cognitive_overactivity" not in set(prior_trigger.get("predicates") or []):
            status, reason = "blocked_prior_trigger", "prior_problem_lacks_bounded_observable_trigger"

    added = False
    prior_source_id = f"prior:{max(0, int(turn_index) - 1)}"
    if status == "prior_source_linked":
        existing = next(
            (
                row
                for row in sources
                if row.get("kind") == "linked_previous_user"
                and row.get("id") == prior_source_id
                and row.get("text") == prior_text
            ),
            None,
        )
        if existing is None:
            sources.append(
                {
                    "id": prior_source_id,
                    "kind": "linked_previous_user",
                    "text": prior_text,
                    "episode_id": str(prior.get("episode_id") or "")[:80],
                    "source_role": "p4_au_exact_prior_problem",
                }
            )
            added = True
        else:
            status = "prior_source_already_present"
            reason = "exact_predecessor_source_preserved_without_duplicate"

    trace = {
        "schema": SCHEMA,
        "status": status,
        "reason": reason,
        "turn_index": int(turn_index),
        "performed_policy": closure.get("performed_policy"),
        "previous_action_outcome": closure.get("previous_action_outcome"),
        "current_request_policy": closure.get("current_request_policy"),
        "exact_pending_receipt_identity": closure.get("exact_pending_receipt_identity") is True,
        "performed_action_strictly_earlier": closure.get("performed_action_strictly_earlier") is True,
        "current_source_authorized": closure.get("source_authorized") is True,
        "current_help_route_status": current_route.get("status"),
        "current_nonfeedback_task_ref_count": len(current_task_refs),
        "current_nonfeedback_task_refs": current_task_refs,
        "prior_source_added": added,
        "prior_source_id": prior_source_id if added else None,
        "prior_source_digest": _digest(prior_text) if prior_text else None,
        "prior_episode_id_digest": _digest(prior.get("episode_id")) if prior.get("episode_id") else None,
        "prior_source_length": len(prior_text),
        "final_source_count": len(sources),
        "assistant_source_count": sum(row.get("kind") == "assistant" for row in sources),
        "private_inference_source_count": 0,
        "predecessor_source_mutated": list(base_sources or []) != original_sources,
        "candidate_score_or_order_changed": False,
        "model_call_added": False,
        "factual_memory_write_count": 0,
        "raw_dialogue_persisted": False,
        "claim_boundary": (
            "exact next-turn direct-user source handoff only; not action quality, "
            "private-state truth, stable preference, or human-equivalent understanding"
        ),
    }
    return sources, trace


def source_packet_with_p4_au(user_input, memory_data=None, feedback=None, turn_index=0):
    base = _ORIGINAL_SOURCE_PACKET_P4_AU(
        user_input,
        memory_data=memory_data,
        feedback=feedback,
        turn_index=turn_index,
    )
    sources, trace = bind_prior_problem_source_p4_au(
        user_input,
        memory_data,
        feedback,
        turn_index,
        base,
    )
    _TRACE.set(deepcopy(trace))
    return sources


def materialize_source_bound_current_action_delivery_p4(result, feedback=None):
    trace = deepcopy(_TRACE.get() or {})
    if trace.get("schema") != SCHEMA:
        return result
    logic = result.setdefault("logic", {})
    runtime = result.setdefault("runtime_trace", {})
    logic[LABEL] = deepcopy(trace)
    runtime[LABEL] = deepcopy(trace)
    rows = [row for row in (runtime.get("blackboard") or []) if row.get("label") != LABEL]
    insert_at = next(
        (
            index
            for index, row in enumerate(rows)
            if row.get("label")
            in {
                "current_task_source_bundle_m50",
                "goal_progress_delivery_m46",
                action45.LABEL,
                "utterance",
            }
        ),
        len(rows),
    )
    rows.insert(
        insert_at,
        {"stage": "ground", "label": LABEL, "payload": deepcopy(trace), "salience": 1.0},
    )
    runtime["blackboard"] = rows
    return result


def install_source_bound_current_action_delivery_p4():
    global _INSTALLED_P4_AU, _ORIGINAL_SOURCE_PACKET_P4_AU, _ORIGINAL_MATERIALIZE_P4_AU
    if _INSTALLED_P4_AU:
        return False
    _ORIGINAL_SOURCE_PACKET_P4_AU = action45.source_packet
    _ORIGINAL_MATERIALIZE_P4_AU = action45.materialize_trace_m45

    def materialize(result, feedback=None):
        _ORIGINAL_MATERIALIZE_P4_AU(result, feedback)
        materialize_source_bound_current_action_delivery_p4(result, feedback)
        return result

    action45.source_packet = source_packet_with_p4_au
    action45.materialize_trace_m45 = materialize
    _INSTALLED_P4_AU = True
    return True


def _fake_downstream_call(prior_source):
    instruction = "まず、頭の中の考えをメモに三つだけ書き出して、三つ書いたら止めよ。"

    def call(system, payload, schema, deadline, metrics):
        metrics["model_calls_attempted"] += 1
        metrics["model_calls_completed"] += 1
        if schema is action45.PLAN_SCHEMA:
            return {"status": "action", "instruction_jp": instruction}
        return {
            "source_id": prior_source["id"],
            "source_span": prior_source["text"],
            "object_jp": "頭の中の考え",
            "verb_jp": "書き出す",
            "completion_jp": "三つ書いたら止める",
            "checks": {key: True for key in action45.REVIEW_KEYS},
        }

    return call


def _fixture_feedback(row):
    model, _binding = p4_at._fixture_pending()
    variant = row.get("receipt_variant")
    if variant == "prediction_mismatch":
        model["executed_action_receipts_m44"][0]["prediction_id"] = "p1-99-mismatch"
    elif variant == "expired_turn":
        model["executed_action_receipts_m44"][0]["created_turn"] = 0
    trace = p4_at.decompose_executed_action_feedback_p4(
        row["turn_2"],
        model,
        turn_index=2,
        base_request=adaptive.classify_explicit_desired_response_m25(row["turn_2"]),
    )
    return {p4_at.LABEL: trace}


def build_dataset_evidence_p4_au(dataset_path):
    dataset_path = Path(dataset_path)
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    rows = []
    for partition in (
        "development_sequences",
        "fresh_positive_sequences",
        "fresh_control_sequences",
    ):
        for frozen in dataset[partition]:
            prior_text = frozen["turn_1"] + (
                "x" * int(frozen.get("turn_1_padding_length") or 0)
            )
            memory = {
                "recent_turns": [
                    {
                        "user": prior_text,
                        "reply": "前の可視質問",
                        "episode_id": f"episode-{frozen['case_id']}",
                    }
                ]
            }
            feedback = _fixture_feedback(frozen)
            base = _ORIGINAL_SOURCE_PACKET_P4_AU(
                frozen["turn_2"], memory, feedback, turn_index=2
            )
            base_before = deepcopy(base)
            sources, trace = bind_prior_problem_source_p4_au(
                frozen["turn_2"], memory, feedback, 2, base
            )
            added = [
                row
                for row in sources
                if row.get("source_role") == "p4_au_exact_prior_problem"
            ]
            downstream = False
            if added:
                logic = {
                    "desired_response_policy_m18": "solve_regulation",
                    "semantic_route_m22": {"selected_type": "general_conversation"},
                }
                _final, delivery = action45.deliver_action(
                    frozen["turn_2"],
                    "今すぐできる一個だけ、一緒に決めよ。",
                    logic,
                    sources,
                    call_json=_fake_downstream_call(added[0]),
                )
                downstream = delivery.get("delivered") is True
            serialized = json.dumps(trace, ensure_ascii=False, sort_keys=True)
            rows.append(
                {
                    "case_id": frozen["case_id"],
                    "partition": partition,
                    "expected_bridge_status": frozen["expected_bridge_status"],
                    "bridge_status": trace["status"],
                    "expected_prior_source_added": frozen["expected_prior_source_added"],
                    "prior_source_added": trace["prior_source_added"],
                    "exact_source_identity": bool(
                        added
                        and added[0]["text"] == prior_text
                        and trace["prior_source_digest"] == _digest(prior_text)
                        and added[0].get("episode_id") == memory["recent_turns"][-1]["episode_id"]
                    ),
                    "downstream_action_contract_passed": downstream,
                    "predecessor_source_mutated": base != base_before,
                    "candidate_score_or_order_changed": trace["candidate_score_or_order_changed"],
                    "new_model_call_count": int(trace["model_call_added"]),
                    "factual_memory_write_count": trace["factual_memory_write_count"],
                    "assistant_source_count": trace["assistant_source_count"],
                    "private_inference_source_count": trace["private_inference_source_count"],
                    "raw_dialogue_persisted": bool(
                        trace["raw_dialogue_persisted"]
                        or frozen["turn_1"] in serialized
                        or frozen["turn_2"] in serialized
                    ),
                }
            )

    development = [row for row in rows if row["partition"] == "development_sequences"]
    positives = [row for row in rows if row["partition"] == "fresh_positive_sequences"]
    controls = [row for row in rows if row["partition"] == "fresh_control_sequences"]
    block_count = lambda status: sum(row["bridge_status"] == status for row in controls)
    return {
        "schema": "uruha_p4_au_source_bound_current_action_delivery_evidence_v1",
        "dataset_sha256": hashlib.sha256(dataset_path.read_bytes()).hexdigest(),
        "cases": rows,
        "metrics": {
            "case_count": len(rows),
            "development_prior_source_linked_count": sum(row["prior_source_added"] for row in development),
            "fresh_positive_prior_source_linked_count": sum(row["prior_source_added"] for row in positives),
            "fresh_positive_exact_source_identity_count": sum(row["exact_source_identity"] for row in positives),
            "fresh_positive_downstream_action_contract_count": sum(row["downstream_action_contract_passed"] for row in positives),
            "fresh_control_prior_source_added_count": sum(row["prior_source_added"] for row in controls),
            "fresh_control_expected_block_reason_count": sum(
                row["bridge_status"] == row["expected_bridge_status"] for row in controls
            ),
            "current_task_replacement_block_count": block_count("blocked_current_task_replacement"),
            "third_party_prior_block_count": block_count("blocked_prior_source_role"),
            "metalinguistic_or_unrelated_prior_block_count": block_count("blocked_prior_trigger"),
            "identity_or_window_block_count": block_count("blocked_exact_action_identity"),
            "no_feedback_block_count": block_count("blocked_no_decisive_action_feedback"),
            "wrong_current_policy_block_count": block_count("blocked_current_policy"),
            "prior_source_budget_block_count": block_count("blocked_prior_source_budget"),
            "predecessor_source_mutation_count": sum(row["predecessor_source_mutated"] for row in rows),
            "candidate_score_or_order_change_count": sum(row["candidate_score_or_order_changed"] for row in rows),
            "new_model_call_count": sum(row["new_model_call_count"] for row in rows),
            "factual_memory_write_count": sum(row["factual_memory_write_count"] for row in rows),
            "assistant_source_count": sum(row["assistant_source_count"] for row in rows),
            "private_inference_source_count": sum(row["private_inference_source_count"] for row in rows),
            "raw_dialogue_persisted_count": sum(row["raw_dialogue_persisted"] for row in rows),
        },
        "claim_boundary": dataset["claim_boundary"],
    }
