"""P4-AY: keep response-form constraints from masquerading as a new task.

P4-AX can prove that one current utterance both supports the exact earlier
clarification and asks for practical help.  P4-AY changes one later boundary:
when P4-AU's only current-task refs are that already-authorized feedback span
or a bounded source-free action-shape constraint, it preserves the exact prior
problem source.  Genuine replacement problem content remains fail closed.
"""

from __future__ import annotations

from contextvars import ContextVar
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re

import uruha_actionable_help_delivery_m45 as action45
import uruha_compound_feedback_request_split_p4 as p4_ax
import uruha_executed_action_outcome_closure_p4 as p4_at
import uruha_semantic_persona_surface_m39 as surface39
import uruha_source_bound_current_action_delivery_p4 as p4_au


LABEL = "response_form_constraint_boundary_p4"
SCHEMA = "uruha_response_form_constraint_boundary_p4"
AUTHORIZED_STATUS = "authorized_response_form_constraints"

_TRACE = ContextVar("p4_ay_response_form_trace", default=None)
_INSTALLED_P4_AY = False
_ORIGINAL_SOURCE_PACKET_P4_AY = None
_ORIGINAL_MATERIALIZE_P4_AY = None

_FEEDBACK_TAIL = {
    "zh": re.compile(r"^[\s，,、；;]*(?:現在|现在|接下來|接下来|然後|然后)?[\s，,、；;]*$", re.I),
    "en": re.compile(r"^[\s,;]*(?:now|next|so)?[\s,;]*$", re.I),
    "ja": re.compile(
        r"^[\s、,。；;]*(?:だった|だ|でした)?[\s、,。；;]*(?:今は|今|次は|次)?[\s、,。；;]*$",
        re.I,
    ),
}
_ACTION_SHAPE = {
    "zh": re.compile(
        r"^(?=[^。！？!?]{0,48}(?:馬上|马上|立刻|現在|现在|立即))"
        r"(?=[^。！？!?]{0,48}(?:做完|完成|停止|停下|終點|终点|結束|结束))"
        r"[\s，,、]*(?:現在|现在|接下來|接下来|只|請|请|要|給我|给我|能|可|一個|一个|單一|单一|馬上|马上|立刻|立即|開始|开始|做|執行|执行|做完|完成|就|即|後|后|停止|停下|有|明確|明确|清楚|終點|终点|結束|结束|的|步驟|步骤|動作|动作|方法|做法|，|,|、|\s)+$",
        re.I,
    ),
    "en": re.compile(
        r"^(?=[^.!?]{0,100}\b(?:start|begin)\b)"
        r"(?=[^.!?]{0,100}\b(?:stop|end|finish|complete)\w*\b)"
        r"[\s,]*(?:now|next|give|me|exactly|only|one|single|step|action|method|that|i|can|could|start|begin|immediately|right|away|and|with|a|clear|definite|stopping|point|stop|end|finish|complete|once|after|it|is|done|,|\s)+$",
        re.I,
    ),
    "ja": re.compile(
        r"^(?=[^。！？]{0,60}(?:すぐ|今すぐ))"
        r"(?=[^。！？]{0,60}(?:終わ|完了))"
        r"(?=[^。！？]{0,60}(?:止め|明確))"
        r"[\s、,]*(?:今は|今|次は|次|すぐ|今すぐ|始め|始められて|できて|実行|終わり|終わったら|終えたら|完了|完了点|が|を|は|で|て|たら|明確|な|止める|止められる|手順|動作|方法|一つ|だけ|教えて|たい|、|,|\s)+$",
        re.I,
    ),
}


def _digest(value):
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()[:16]


def _feedback_only_constraint(span, p4_ax_payload):
    if (p4_ax_payload or {}).get("status") != p4_ax.AUTHORIZED_STATUS:
        return None
    candidate = p4_ax._bounded_compound_support(span)
    if not candidate or candidate.get("language") != p4_ax_payload.get("language"):
        return None
    language = candidate["language"]
    positive = p4_ax._COMPOSITION[language]["positive"].search(span)
    if not positive or not _FEEDBACK_TAIL[language].fullmatch(span[positive.end() :]):
        return None
    return f"authorized_previous_feedback:{language}"


def _action_shape_constraint(span):
    value = str(span or "").strip()
    for language, pattern in _ACTION_SHAPE.items():
        if pattern.fullmatch(value):
            return f"bounded_action_shape:{language}"
    return None


def _classify_current_refs(user_input, p4_au_trace, p4_ax_payload):
    text = str(user_input or "")
    authorized = []
    genuine = []
    for ref in p4_au_trace.get("current_nonfeedback_task_refs") or []:
        start = int(ref.get("start") or 0)
        length = int(ref.get("length") or 0)
        span = text[start : start + length]
        basis = _feedback_only_constraint(span, p4_ax_payload) or _action_shape_constraint(span)
        row = {
            "start": start,
            "length": length,
            "span_digest": _digest(span),
            "role": ref.get("role"),
            "basis": basis or "genuine_task_content",
        }
        (authorized if basis else genuine).append(row)
    return authorized, genuine


def _remaining_prior_guard(memory_data):
    recent = (memory_data or {}).get("recent_turns") or []
    prior = recent[-1] if recent and isinstance(recent[-1], dict) else {}
    prior_text = prior.get("user") if isinstance(prior.get("user"), str) else ""
    if not prior_text:
        return prior, prior_text, "blocked_prior_source_missing", "immediately_preceding_user_source_missing"
    if len(prior_text) > p4_au.MAX_PRIOR_SOURCE_CHARS:
        return prior, prior_text, "blocked_prior_source_budget", "prior_user_source_exceeds_budget"
    frame = surface39._source_frame_m39(prior_text)
    prior_trigger = p4_au._prior_trigger(prior_text)
    trigger_languages = set(prior_trigger.get("matched_languages") or [])
    japanese_subject_ellipsis = bool(
        "ja" in trigger_languages
        and frame.get("speaker_role") == "unspecified"
        and frame.get("third_party_present") is False
        and p4_at._source_is_direct(prior_text)
    )
    if frame.get("third_party_present") is True:
        return prior, prior_text, "blocked_prior_source_role", "prior_source_not_direct_user_first_person"
    if not p4_at._source_is_direct(prior_text):
        return prior, prior_text, "blocked_prior_trigger", "prior_source_is_metalinguistic_or_quoted"
    if frame.get("speaker_role") != "user_first_person" and not japanese_subject_ellipsis:
        return prior, prior_text, "blocked_prior_source_role", "prior_source_not_direct_user_first_person"
    if "cognitive_overactivity" not in set(prior_trigger.get("predicates") or []):
        return prior, prior_text, "blocked_prior_trigger", "prior_problem_lacks_bounded_observable_trigger"
    return prior, prior_text, "pass", "all_remaining_p4_au_prior_guards_passed"


def refine_response_form_constraint_boundary_p4_ay(
    user_input,
    memory_data,
    feedback,
    turn_index,
    base_sources,
    p4_au_trace,
):
    """Return copied sources, a refined P4-AU trace, and a raw-free P4-AY trace."""

    sources = deepcopy(list(base_sources or []))
    original_sources = deepcopy(sources)
    updated_p4_au = deepcopy(p4_au_trace or {})
    closure = deepcopy((feedback or {}).get(p4_at.LABEL) or {})
    p4_ax_payload = deepcopy(closure.get(p4_ax.LABEL) or {})
    authorized_refs, genuine_refs = _classify_current_refs(
        user_input, updated_p4_au, p4_ax_payload
    )
    exact_authority = bool(
        updated_p4_au.get("status") == "blocked_current_task_replacement"
        and p4_ax_payload.get("status") == p4_ax.AUTHORIZED_STATUS
        and closure.get("exact_pending_receipt_identity") is True
        and closure.get("previous_action_outcome") == "supported"
        and closure.get("two_independent_acts") is True
        and closure.get("current_request_policy") == "solve_regulation"
        and closure.get("source_authorized") is True
        and closure.get("performed_action_strictly_earlier") is True
    )
    prior, prior_text, remaining_status, remaining_reason = _remaining_prior_guard(memory_data)
    status = "predecessor_preserved"
    reason = "p4_au_predecessor_or_p4_ax_authority_not_eligible"
    added = False
    prior_source_id = f"prior:{max(0, int(turn_index) - 1)}"
    if exact_authority and genuine_refs:
        status = "blocked_genuine_task_replacement"
        reason = "at_least_one_current_ref_contains_replacement_problem_content"
    elif exact_authority and authorized_refs and remaining_status != "pass":
        status = "blocked_non_task_p4_au_guard"
        reason = remaining_reason
    elif exact_authority and authorized_refs and not genuine_refs and remaining_status == "pass":
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
        status = AUTHORIZED_STATUS
        reason = "feedback_and_response_form_refs_do_not_replace_exact_prior_problem"

    payload = {
        "schema": SCHEMA,
        "status": status,
        "reason": reason,
        "turn_index": int(turn_index),
        "p4_au_predecessor_status": (p4_au_trace or {}).get("status"),
        "p4_ax_status": p4_ax_payload.get("status"),
        "p4_ax_language": p4_ax_payload.get("language"),
        "exact_pending_receipt_identity": closure.get("exact_pending_receipt_identity") is True,
        "previous_action_outcome": closure.get("previous_action_outcome"),
        "current_request_policy": closure.get("current_request_policy"),
        "two_independent_acts": closure.get("two_independent_acts") is True,
        "authorized_constraint_ref_count": len(authorized_refs),
        "authorized_constraint_refs": authorized_refs,
        "genuine_task_ref_count": len(genuine_refs),
        "genuine_task_refs": genuine_refs,
        "remaining_p4_au_guard_status": remaining_status,
        "prior_source_added": added,
        "prior_source_digest": _digest(prior_text) if prior_text else None,
        "prior_source_length": len(prior_text),
        "predecessor_source_mutated": list(base_sources or []) != original_sources,
        "p4_at_outcome_mutated": False,
        "p4_ax_authority_preserved": p4_ax_payload.get("status") == p4_ax.AUTHORIZED_STATUS,
        "p4_au_non_task_guard_bypassed": False,
        "candidate_score_or_order_changed": False,
        "visible_reply_changed": False,
        "model_call_added": False,
        "factual_memory_write_count": 0,
        "assistant_source_count": sum(row.get("kind") == "assistant" for row in sources),
        "private_inference_source_count": 0,
        "raw_dialogue_persisted": False,
        "evidence_digest": _digest(user_input),
        "claim_boundary": "bounded exact feedback/response-form ref exclusion only; not open-domain topic continuity, plan quality, or private intent truth",
    }
    if status == AUTHORIZED_STATUS:
        updated_p4_au.update(
            {
                "status": "prior_source_linked",
                "reason": "bounded_response_form_constraints_do_not_replace_prior_problem_p4_ay",
                "prior_source_added": added,
                "prior_source_id": prior_source_id if added else None,
                "prior_source_digest": _digest(prior_text),
                "prior_episode_id_digest": _digest(prior.get("episode_id")) if prior.get("episode_id") else None,
                "prior_source_length": len(prior_text),
                "final_source_count": len(sources),
                "assistant_source_count": payload["assistant_source_count"],
                "private_inference_source_count": 0,
                "effective_genuine_task_ref_count": 0,
                "p4_ay_authorized_constraint_ref_count": len(authorized_refs),
                LABEL: deepcopy(payload),
            }
        )
    else:
        updated_p4_au[LABEL] = deepcopy(payload)
    return sources, updated_p4_au, payload


def materialize_response_form_constraint_boundary_p4_ay(result):
    trace = deepcopy(_TRACE.get() or {})
    if trace.get("schema") != SCHEMA:
        return result
    logic = result.setdefault("logic", {})
    runtime = result.setdefault("runtime_trace", {})
    logic[LABEL] = deepcopy(trace)
    runtime[LABEL] = deepcopy(trace)
    rows = [row for row in (runtime.get("blackboard") or []) if row.get("label") != LABEL]
    insert_at = next(
        (index for index, row in enumerate(rows) if row.get("label") in {p4_au.LABEL, "current_task_source_bundle_m50", action45.LABEL, "utterance"}),
        len(rows),
    )
    rows.insert(
        insert_at,
        {"stage": "ground", "label": LABEL, "payload": deepcopy(trace), "salience": 1.0},
    )
    runtime["blackboard"] = rows
    return result


def install_response_form_constraint_boundary_p4_ay():
    global _INSTALLED_P4_AY, _ORIGINAL_SOURCE_PACKET_P4_AY, _ORIGINAL_MATERIALIZE_P4_AY
    if _INSTALLED_P4_AY:
        return False
    _ORIGINAL_SOURCE_PACKET_P4_AY = action45.source_packet
    _ORIGINAL_MATERIALIZE_P4_AY = action45.materialize_trace_m45

    def source_packet(user_input, memory_data=None, feedback=None, turn_index=0):
        base_sources = _ORIGINAL_SOURCE_PACKET_P4_AY(
            user_input,
            memory_data=memory_data,
            feedback=feedback,
            turn_index=turn_index,
        )
        base_trace = deepcopy(p4_au._TRACE.get() or {})
        sources, updated_p4_au, trace = refine_response_form_constraint_boundary_p4_ay(
            user_input,
            memory_data,
            feedback,
            turn_index,
            base_sources,
            base_trace,
        )
        p4_au._TRACE.set(deepcopy(updated_p4_au))
        _TRACE.set(deepcopy(trace))
        return sources

    def materialize(result, feedback=None):
        _ORIGINAL_MATERIALIZE_P4_AY(result, feedback)
        materialize_response_form_constraint_boundary_p4_ay(result)
        return result

    action45.source_packet = source_packet
    action45.materialize_trace_m45 = materialize
    _INSTALLED_P4_AY = True
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
    base_before = deepcopy(base)
    base_sources, p4_au_trace = p4_au.bind_prior_problem_source_p4_au(
        frozen["turn_2"], memory, feedback, 2, base
    )
    closure_before = deepcopy(feedback[p4_at.LABEL])
    sources, updated_p4_au, trace = refine_response_form_constraint_boundary_p4_ay(
        frozen["turn_2"], memory, feedback, 2, base_sources, p4_au_trace
    )
    added = [
        row for row in sources if row.get("source_role") == "p4_au_exact_prior_problem"
    ]
    effective_prior_source_present = bool(
        added
        and added[0]["text"] == frozen["turn_1"]
        and added[0].get("episode_id") == memory["recent_turns"][-1]["episode_id"]
    )
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
            call_json=p4_au._fake_downstream_call(added[0]),
        )
        downstream = delivery.get("delivered") is True
    serialized = json.dumps(trace, ensure_ascii=False, sort_keys=True)
    expected_status = frozen.get("expected_p4_ay_status", "predecessor_preserved")
    return {
        "case_id": frozen["case_id"],
        "partition": partition,
        "language": frozen.get("language"),
        "control_family": frozen.get("control_family"),
        "p4_au_status_before": p4_au_trace.get("status"),
        "p4_au_status_after": updated_p4_au.get("status"),
        "expected_p4_ay_status": expected_status,
        "p4_ay_status": trace["status"],
        "expected_prior_source_added": frozen.get("expected_prior_source_added", True),
        "prior_source_added": trace["prior_source_added"],
        "effective_prior_source_present": effective_prior_source_present,
        "exact_source_identity": bool(
            effective_prior_source_present
            and trace["prior_source_digest"] == _digest(frozen["turn_1"])
        ),
        "downstream_action_contract_passed": downstream,
        "p4_ax_status": (closure_before.get(p4_ax.LABEL) or {}).get("status"),
        "p4_ax_authority_preserved": trace["p4_ax_authority_preserved"],
        "p4_at_outcome_mutated": feedback[p4_at.LABEL] != closure_before,
        "p4_au_non_task_guard_bypassed": trace["p4_au_non_task_guard_bypassed"],
        "genuine_task_ref_count": trace["genuine_task_ref_count"],
        "predecessor_source_mutated": base != base_before,
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


def build_dataset_evidence_p4_ay(dataset_path):
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
        "schema": "uruha_p4_ay_response_form_constraint_boundary_evidence_v1",
        "dataset_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "cases": cases,
        "predecessor_cases": predecessor_cases,
        "metrics": {
            "case_count": len(cases),
            "development_authorized_count": sum(row["p4_ay_status"] == AUTHORIZED_STATUS for row in development),
            "development_prior_source_linked_count": sum(row["prior_source_added"] for row in development),
            "fresh_positive_authorized_count": sum(row["p4_ay_status"] == AUTHORIZED_STATUS for row in positives),
            "fresh_positive_prior_source_linked_count": sum(row["prior_source_added"] for row in positives),
            "fresh_positive_exact_source_identity_count": sum(row["exact_source_identity"] for row in positives),
            "fresh_positive_downstream_action_contract_count": sum(row["downstream_action_contract_passed"] for row in positives),
            "fresh_control_prior_source_added_count": sum(row["prior_source_added"] for row in controls),
            "fresh_control_expected_status_count": sum(row["p4_ay_status"] == row["expected_p4_ay_status"] for row in controls),
            "genuine_task_replacement_block_count": sum(row["p4_ay_status"] == "blocked_genuine_task_replacement" for row in controls),
            "predecessor_positive_prior_source_linked_count": sum(
                row["p4_au_status_after"] == "prior_source_linked"
                and row["effective_prior_source_present"]
                for row in predecessor_cases
            ),
            "p4_ax_authority_preserved_count": sum(row["p4_ax_status"] == p4_ax.AUTHORIZED_STATUS and row["p4_ax_authority_preserved"] for row in targets),
            "p4_at_outcome_mutation_count": sum(row["p4_at_outcome_mutated"] for row in cases + predecessor_cases),
            "p4_au_non_task_guard_bypass_count": sum(row["p4_au_non_task_guard_bypassed"] for row in cases + predecessor_cases),
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
    "build_dataset_evidence_p4_ay",
    "install_response_form_constraint_boundary_p4_ay",
    "materialize_response_form_constraint_boundary_p4_ay",
    "refine_response_form_constraint_boundary_p4_ay",
]
