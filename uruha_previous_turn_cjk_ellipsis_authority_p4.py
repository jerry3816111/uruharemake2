"""P4-AZ: bounded authority for an exact previous Chinese ellipsis source.

P4-AW authorizes a current direct CJK subject-ellipsis turn to create an exact
executed-action receipt.  P4-AZ applies the same observable-source grammar to
the immediately previous user source only after P4-AX/P4-AT feedback and P4-AY
task continuity are exact.  It keeps ``speaker_role=unspecified`` and changes
no generation or memory truth.
"""

from __future__ import annotations

from contextvars import ContextVar
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import uruha_actionable_help_delivery_m45 as action45
import uruha_cjk_subject_ellipsis_action_authority_p4 as p4_aw
import uruha_compound_feedback_request_split_p4 as p4_ax
import uruha_executed_action_outcome_closure_p4 as p4_at
import uruha_response_form_constraint_boundary_p4 as p4_ay
import uruha_source_bound_current_action_delivery_p4 as p4_au


LABEL = "previous_turn_cjk_ellipsis_authority_p4"
SCHEMA = "uruha_previous_turn_cjk_ellipsis_authority_p4"
AUTHORIZED_STATUS = "authorized_previous_turn_cjk_ellipsis"

_TRACE = ContextVar("p4_az_previous_turn_ellipsis_trace", default=None)
_INSTALLED_P4_AZ = False
_ORIGINAL_SOURCE_PACKET_P4_AZ = None
_ORIGINAL_MATERIALIZE_P4_AZ = None


def _digest(value):
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()[:16]


def _exact_current_chain(closure, p4_au_trace, p4_ay_trace):
    p4_ax_payload = (closure or {}).get(p4_ax.LABEL) or {}
    predecessor_status = (p4_au_trace or {}).get("status")
    direct_prior_role_stop = predecessor_status == "blocked_prior_source_role"
    p4_ay_prior_role_stop = bool(
        predecessor_status == "blocked_current_task_replacement"
        and (p4_ay_trace or {}).get("status") == "blocked_non_task_p4_au_guard"
        and (p4_ay_trace or {}).get("remaining_p4_au_guard_status") == "blocked_prior_source_role"
        and int((p4_ay_trace or {}).get("authorized_constraint_ref_count") or 0) > 0
        and int((p4_ay_trace or {}).get("genuine_task_ref_count") or 0) == 0
    )
    checks = {
        "p4_au_stopped_only_at_prior_role": direct_prior_role_stop or p4_ay_prior_role_stop,
        "p4_ax_authorized": p4_ax_payload.get("status") == p4_ax.AUTHORIZED_STATUS,
        "exact_pending_receipt_identity": closure.get("exact_pending_receipt_identity") is True,
        "previous_action_supported": closure.get("previous_action_outcome") == "supported",
        "two_independent_acts": closure.get("two_independent_acts") is True,
        "current_policy_solve": closure.get("current_request_policy") == "solve_regulation",
        "current_source_authorized": closure.get("source_authorized") is True,
        "performed_action_strictly_earlier": closure.get("performed_action_strictly_earlier") is True,
    }
    return checks


def refine_previous_turn_cjk_ellipsis_authority_p4_az(
    user_input,
    memory_data,
    feedback,
    turn_index,
    base_sources,
    p4_au_trace,
    p4_ay_trace,
):
    """Return copied sources, refined P4-AU trace, and a raw-free P4-AZ trace."""

    sources = deepcopy(list(base_sources or []))
    original_sources = deepcopy(sources)
    updated_p4_au = deepcopy(p4_au_trace or {})
    closure = deepcopy((feedback or {}).get(p4_at.LABEL) or {})
    exact_checks = _exact_current_chain(closure, p4_au_trace, p4_ay_trace)
    recent = (memory_data or {}).get("recent_turns") or []
    prior = recent[-1] if recent and isinstance(recent[-1], dict) else {}
    prior_text = prior.get("user") if isinstance(prior.get("user"), str) else ""
    assessment = p4_aw.assess_cjk_subject_ellipsis_candidate_p4_aw(prior_text)
    source_checks = {
        "prior_source_present": bool(prior_text),
        "prior_source_within_budget": len(prior_text) <= p4_au.MAX_PRIOR_SOURCE_CHARS,
        "previous_turn_chinese": assessment.get("language") == "zh",
        "typed_cognitive_overactivity": assessment.get("trigger_predicate") == "cognitive_overactivity",
        "source_role_unspecified": assessment.get("source_speaker_role_preserved") == "unspecified",
        "p4_aw_provisional_authority": assessment.get("status") == p4_aw.PROVISIONAL_STATUS,
        "no_failed_p4_aw_source_checks": not assessment.get("failed_checks"),
    }
    authorized = bool(all(exact_checks.values()) and all(source_checks.values()))
    status = AUTHORIZED_STATUS if authorized else "blocked_prior_source_authority"
    reason = (
        "exact_previous_turn_chinese_ellipsis_source_authorized"
        if authorized
        else "exact_chain_or_bounded_previous_source_checks_failed"
    )
    prior_source_id = f"prior:{max(0, int(turn_index) - 1)}"
    added = False
    if authorized:
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

    payload = {
        "schema": SCHEMA,
        "status": status,
        "reason": reason,
        "turn_index": int(turn_index),
        "p4_au_predecessor_status": (p4_au_trace or {}).get("status"),
        "p4_ay_status": (p4_ay_trace or {}).get("status"),
        "exact_chain_checks": exact_checks,
        "source_checks": source_checks,
        "failed_exact_chain_checks": [key for key, value in exact_checks.items() if not value],
        "failed_source_checks": [key for key, value in source_checks.items() if not value],
        "source_speaker_role_preserved": assessment.get("source_speaker_role_preserved"),
        "language": assessment.get("language"),
        "trigger_predicate": assessment.get("trigger_predicate"),
        "prior_source_added": added,
        "prior_source_digest": _digest(prior_text) if prior_text else None,
        "prior_source_length": len(prior_text),
        "predecessor_source_mutated": list(base_sources or []) != original_sources,
        "p4_ay_task_boundary_mutated": False,
        "p4_au_non_role_guard_bypassed": False,
        "source_role_rewritten": False,
        "candidate_score_or_order_changed": False,
        "visible_reply_changed": False,
        "model_call_added": False,
        "factual_memory_write_count": 0,
        "assistant_source_count": sum(row.get("kind") == "assistant" for row in sources),
        "private_inference_source_count": 0,
        "raw_dialogue_persisted": False,
        "evidence_digest": _digest(user_input),
        "claim_boundary": "exact previous-turn Chinese ellipsis source authority only; source role stays unspecified and no private mental truth is claimed",
    }
    if authorized:
        updated_p4_au.update(
            {
                "status": "prior_source_linked",
                "reason": "bounded_previous_turn_cjk_ellipsis_authority_p4_az",
                "prior_source_added": added,
                "prior_source_id": prior_source_id if added else None,
                "prior_source_digest": _digest(prior_text),
                "prior_episode_id_digest": _digest(prior.get("episode_id")) if prior.get("episode_id") else None,
                "prior_source_length": len(prior_text),
                "final_source_count": len(sources),
                "assistant_source_count": payload["assistant_source_count"],
                "private_inference_source_count": 0,
                LABEL: deepcopy(payload),
            }
        )
    else:
        updated_p4_au[LABEL] = deepcopy(payload)
    return sources, updated_p4_au, payload


def materialize_previous_turn_cjk_ellipsis_authority_p4_az(result):
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
            if row.get("label") in {p4_au.LABEL, "current_task_source_bundle_m50", action45.LABEL, "utterance"}
        ),
        len(rows),
    )
    rows.insert(
        insert_at,
        {"stage": "authorize", "label": LABEL, "payload": deepcopy(trace), "salience": 1.0},
    )
    runtime["blackboard"] = rows
    return result


def install_previous_turn_cjk_ellipsis_authority_p4_az():
    global _INSTALLED_P4_AZ, _ORIGINAL_SOURCE_PACKET_P4_AZ, _ORIGINAL_MATERIALIZE_P4_AZ
    if _INSTALLED_P4_AZ:
        return False
    _ORIGINAL_SOURCE_PACKET_P4_AZ = action45.source_packet
    _ORIGINAL_MATERIALIZE_P4_AZ = action45.materialize_trace_m45

    def source_packet(user_input, memory_data=None, feedback=None, turn_index=0):
        base_sources = _ORIGINAL_SOURCE_PACKET_P4_AZ(
            user_input,
            memory_data=memory_data,
            feedback=feedback,
            turn_index=turn_index,
        )
        base_p4_au = deepcopy(p4_au._TRACE.get() or {})
        base_p4_ay = deepcopy(p4_ay._TRACE.get() or {})
        sources, updated_p4_au, trace = refine_previous_turn_cjk_ellipsis_authority_p4_az(
            user_input,
            memory_data,
            feedback,
            turn_index,
            base_sources,
            base_p4_au,
            base_p4_ay,
        )
        p4_au._TRACE.set(deepcopy(updated_p4_au))
        _TRACE.set(deepcopy(trace))
        return sources

    def materialize(result, feedback=None):
        _ORIGINAL_MATERIALIZE_P4_AZ(result, feedback)
        materialize_previous_turn_cjk_ellipsis_authority_p4_az(result)
        return result

    action45.source_packet = source_packet
    action45.materialize_trace_m45 = materialize
    _INSTALLED_P4_AZ = True
    return True


def _evaluate_sequence(frozen, partition):
    feedback = p4_au._fixture_feedback(frozen)
    memory = {
        "recent_turns": [
            {
                "user": frozen["turn_1"],
                "reply": "verified previous visible clarification",
                "episode_id": f"episode-{frozen['case_id']}",
            }
        ]
    }
    base = p4_au._ORIGINAL_SOURCE_PACKET_P4_AU(
        frozen["turn_2"], memory, feedback, turn_index=2
    )
    sources, p4_au_trace = p4_au.bind_prior_problem_source_p4_au(
        frozen["turn_2"], memory, feedback, 2, base
    )
    sources, updated_p4_au, p4_ay_trace = p4_ay.refine_response_form_constraint_boundary_p4_ay(
        frozen["turn_2"], memory, feedback, 2, sources, p4_au_trace
    )
    p4_ay_before = deepcopy(p4_ay_trace)
    sources, final_p4_au, trace = refine_previous_turn_cjk_ellipsis_authority_p4_az(
        frozen["turn_2"], memory, feedback, 2, sources, updated_p4_au, p4_ay_trace
    )
    exact_sources = [
        row for row in sources if row.get("source_role") == "p4_au_exact_prior_problem"
    ]
    effective_prior_source_present = bool(
        exact_sources
        and exact_sources[0]["text"] == frozen["turn_1"]
        and exact_sources[0].get("episode_id") == memory["recent_turns"][-1]["episode_id"]
    )
    downstream = False
    if effective_prior_source_present:
        logic = {
            "desired_response_policy_m18": "solve_regulation",
            "semantic_route_m22": {"selected_type": "general_conversation"},
        }
        _final, delivery = action45.deliver_action(
            frozen["turn_2"],
            "今すぐできる一個だけ、一緒に決めよ。",
            logic,
            sources,
            call_json=p4_au._fake_downstream_call(exact_sources[0]),
        )
        downstream = delivery.get("delivered") is True
    serialized = json.dumps(trace, ensure_ascii=False, sort_keys=True)
    return {
        "case_id": frozen["case_id"],
        "partition": partition,
        "language": frozen.get("language"),
        "control_family": frozen.get("control_family"),
        "p4_au_status_before": p4_au_trace.get("status"),
        "p4_ay_status": p4_ay_trace.get("status"),
        "p4_au_status_after": final_p4_au.get("status"),
        "expected_status": frozen.get("expected_status", "predecessor_preserved"),
        "p4_az_status": trace["status"],
        "expected_prior_source_added": frozen.get("expected_prior_source_added", True),
        "prior_source_added": trace["prior_source_added"],
        "effective_prior_source_present": effective_prior_source_present,
        "exact_source_identity": bool(
            effective_prior_source_present
            and trace["prior_source_digest"] == _digest(frozen["turn_1"])
        ),
        "downstream_action_contract_passed": downstream,
        "source_speaker_role_preserved": trace["source_speaker_role_preserved"],
        "typed_cognitive_trigger": trace["trigger_predicate"] == "cognitive_overactivity",
        "exact_feedback_chain_preserved": all(trace["exact_chain_checks"].values()),
        "p4_ay_task_boundary_mutated": p4_ay_trace != p4_ay_before,
        "p4_au_non_role_guard_bypassed": trace["p4_au_non_role_guard_bypassed"],
        "candidate_score_or_order_changed": trace["candidate_score_or_order_changed"],
        "visible_reply_changed": trace["visible_reply_changed"],
        "added_model_call_count": int(trace["model_call_added"]),
        "factual_memory_write_count": trace["factual_memory_write_count"],
        "assistant_source_count": trace["assistant_source_count"],
        "private_inference_source_count": trace["private_inference_source_count"],
        "raw_dialogue_persisted": bool(
            trace["raw_dialogue_persisted"]
            or frozen["turn_1"] in serialized
            or frozen["turn_2"] in serialized
        ),
    }


def build_dataset_evidence_p4_az(dataset_path):
    path = Path(dataset_path)
    dataset = json.loads(path.read_text(encoding="utf-8"))
    p4_ax.install_compound_feedback_request_split_hook_p4_ax()
    cases = []
    for partition in ("development_sequences", "fresh_positive_sequences", "fresh_control_sequences"):
        cases.extend(_evaluate_sequence(row, partition) for row in dataset[partition])

    predecessor_dataset = json.loads(
        (Path(__file__).resolve().parent / dataset["predecessor_dataset"]["path"]).read_text(encoding="utf-8")
    )
    predecessor_cases = [
        _evaluate_sequence(row, "predecessor_positive_sequences")
        for row in predecessor_dataset[dataset["predecessor_dataset"]["partition"]]
    ]
    development = [row for row in cases if row["partition"] == "development_sequences"]
    positives = [row for row in cases if row["partition"] == "fresh_positive_sequences"]
    controls = [row for row in cases if row["partition"] == "fresh_control_sequences"]
    targets = development + positives
    source = Path(__file__).read_text(encoding="utf-8")
    fresh_full_strings = [
        value
        for row in dataset["fresh_positive_sequences"] + dataset["fresh_control_sequences"]
        for value in (row["turn_1"], row["turn_2"])
    ]
    return {
        "schema": "uruha_p4_az_previous_turn_cjk_ellipsis_authority_evidence_v1",
        "dataset_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "cases": cases,
        "predecessor_cases": predecessor_cases,
        "metrics": {
            "case_count": len(cases),
            "development_authorized_count": sum(row["p4_az_status"] == AUTHORIZED_STATUS for row in development),
            "development_prior_source_linked_count": sum(row["prior_source_added"] for row in development),
            "fresh_positive_authorized_count": sum(row["p4_az_status"] == AUTHORIZED_STATUS for row in positives),
            "fresh_positive_prior_source_linked_count": sum(row["prior_source_added"] for row in positives),
            "fresh_positive_exact_source_identity_count": sum(row["exact_source_identity"] for row in positives),
            "fresh_positive_downstream_action_contract_count": sum(row["downstream_action_contract_passed"] for row in positives),
            "fresh_control_prior_source_added_count": sum(row["prior_source_added"] for row in controls),
            "fresh_control_expected_status_count": sum(row["p4_az_status"] == row["expected_status"] for row in controls),
            "blocked_source_authority_control_count": sum(row["p4_az_status"] == "blocked_prior_source_authority" for row in controls),
            "predecessor_positive_prior_source_present_count": sum(row["effective_prior_source_present"] for row in predecessor_cases),
            "source_role_preserved_unspecified_count": sum(row["source_speaker_role_preserved"] == "unspecified" for row in targets),
            "exact_feedback_chain_preserved_count": sum(row["exact_feedback_chain_preserved"] for row in targets),
            "typed_cognitive_trigger_count": sum(row["typed_cognitive_trigger"] for row in targets),
            "p4_ay_task_boundary_mutation_count": sum(row["p4_ay_task_boundary_mutated"] for row in cases + predecessor_cases),
            "p4_au_non_role_guard_bypass_count": sum(row["p4_au_non_role_guard_bypassed"] for row in cases + predecessor_cases),
            "candidate_score_or_order_change_count": sum(row["candidate_score_or_order_changed"] for row in cases + predecessor_cases),
            "added_model_call_count": sum(row["added_model_call_count"] for row in cases + predecessor_cases),
            "factual_memory_write_count": sum(row["factual_memory_write_count"] for row in cases + predecessor_cases),
            "assistant_source_count": sum(row["assistant_source_count"] for row in cases + predecessor_cases),
            "private_inference_source_count": sum(row["private_inference_source_count"] for row in cases + predecessor_cases),
            "raw_dialogue_persisted_count": sum(row["raw_dialogue_persisted"] for row in cases + predecessor_cases),
            "visible_reply_change_count": sum(row["visible_reply_changed"] for row in cases + predecessor_cases),
            "full_fresh_string_patch_count": sum(value in source for value in fresh_full_strings),
        },
        "claim_boundary": dataset["claim_boundary"],
    }


__all__ = [
    "AUTHORIZED_STATUS",
    "LABEL",
    "SCHEMA",
    "build_dataset_evidence_p4_az",
    "install_previous_turn_cjk_ellipsis_authority_p4_az",
    "materialize_previous_turn_cjk_ellipsis_authority_p4_az",
    "refine_previous_turn_cjk_ellipsis_authority_p4_az",
]
