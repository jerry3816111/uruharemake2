"""Opt-in, bounded actor/scope evidence for temporal response-form requests.

This gate does not infer private intent.  It distinguishes a current user's
own deferred reply from a request that the assistant ask about response form.
The typed evidence is shared by M25, P4-AT, the planner, and the product graph.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import hashlib
import re

import uruha_adaptive_person_model as adaptive
import uruha_executed_action_outcome_closure_p4 as p4_at


LABEL = "temporal_actor_scope_p4"
SCHEMA = "uruha_temporal_actor_scope_p4_v1"
_INSTALLED = False
_ORIGINAL_BASE_CLASSIFIER = None
_ORIGINAL_APPLY = None
_ORIGINAL_EMIT = None
_ORIGINAL_RUN = None

_QUOTED = re.compile(r"「[^」]*」|『[^』]*』|“[^”]*”|\"[^\"]*\"")
_THIRD_PARTY_JP = r"(?:友達|友人|先輩|後輩|同僚|先生|母|父|親|兄|姉|弟|妹|彼|彼女)"
_VISIBLE_THIRD_PARTY_SUBJECT = re.compile(
    rf"{_THIRD_PARTY_JP}(?:が|は|も)", re.I,
)
_VISIBLE_THIRD_PARTY_RECIPIENT = re.compile(
    rf"{_THIRD_PARTY_JP}(?:に|へ)", re.I,
)
_THIRD_PARTY_REPORT = re.compile(
    rf"{_THIRD_PARTY_JP}(?:が|は|も|に)[^。！？\n]{{0,24}}"
    r"(?:と言われ|って言われ|と言った|って言った|と言って|って言って|"
    r"が言った|が言って)"
    r"|\b(?:my friend|a friend|she|he|they|my teacher)\b[^.!?;\n]{0,24}"
    r"\b(?:said|told|quoted)\b"
    r"|\b(?:said|told|quoted)\b[^.!?;\n]{0,24}"
    r"\b(?:my friend|a friend|she|he|they|my teacher)\b"
    r"|(?:朋友|同學|同学|老師|老师|前輩|前辈|同事|媽媽|妈妈|爸爸)"
    r"[^。！？\n]{0,12}(?:說|说|告訴|告诉)",
    re.I,
)
_SELF_DEFER = (
    ("ja:self_check_then_reply",
     re.compile(
         r"(?:先に|まず)[^。！？\n]{0,40}(?:確認|調べ|見|チェック)"
         r"[^。！？\n]{0,36}(?:それから|そのあと|後で|てから)"
         r"[^。！？\n]{0,24}(?:返事|返信|連絡)"
         r"[^。！？\n]{0,16}(?:してもいい|していい|する|したい|できる|しておく)",
         re.I,
     )),
    ("en:self_check_then_reply",
     re.compile(
         r"\b(?:can|could|may)\s+i\b[^.!?;\n]{0,55}"
         r"\b(?:check|look|verify)\b[^.!?;\n]{0,55}"
         r"\b(?:reply|respond|get back)\b",
         re.I,
     )),
    ("zh:self_check_then_reply",
     re.compile(
         r"(?:我|俺|本人)先[^。！？\n]{0,20}(?:確認|确认|查|看)"
         r"[^。！？\n]{0,22}(?:再|晚點|晚点|之後|之后)"
         r"[^。！？\n]{0,15}(?:回覆|回复|答覆|答复|回答|回你)",
         re.I,
     )),
)
_ASSISTANT_REQUEST = (
    ("ja:response_form_ask",
     re.compile(
         r"(?:先に|まず)?[^。！？\n]{0,8}"
         r"(?:何がほしいか|欲しい返し(?:方)?|返し方|何を求めてるか)"
         r"[^。！？\n]{0,10}(?:聞いて|確認して)",
         re.I,
     )),
    ("ja:ask_me_first",
     re.compile(
         r"(?:私|僕|俺|うち)に[^。！？\n]{0,10}"
         r"(?:先に)?(?:聞いて|確認して)",
         re.I,
     )),
    ("en:ask_me_first",
     re.compile(
         r"\b(?:ask|clarify with|check with)\s+me\b[^.!?;\n]{0,20}\bfirst\b"
         r"|\bfirst\s+(?:ask|check)\s+(?:me|what i want)\b",
         re.I,
     )),
    ("zh:ask_me_first",
     re.compile(
         r"(?:你|妳|請|请)[^。！？\n]{0,4}先(?:問|问)我"
         r"|先(?:確認|确认)我要(?:什麼|什么)",
         re.I,
     )),
)
_NEGATED_ASSISTANT_REQUEST = re.compile(
    r"(?:聞いて|確認して)(?:ほしくない|欲しくない|ないで|なくていい)"
    r"|\b(?:don['’]?t|do\s+not|never)\b[^.!?;\n]{0,30}"
    r"\b(?:ask|check|clarify)\b"
    r"|(?:不要|別|别|不用|不必)[^。！？\n]{0,8}"
    r"(?:先問|先问|先確認|先确认)",
    re.I,
)
_DEFER_REPLY_JP = "うん、先に確認してからでいいよ。返事はそのあとで。"
_REPORTED_CHECK_REPLY_JP = "そう言ってたんだ。何を先に確認する話？"


def _digest(value):
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()[:16]


def _matched_cues(patterns, text):
    return [cue_id for cue_id, pattern in patterns if pattern.search(text)]


def _direct_assistant_cues(text):
    cues = []
    for cue_id, pattern in _ASSISTANT_REQUEST:
        for match in pattern.finditer(text):
            clause_start = max(
                (text.rfind(mark, 0, match.start()) for mark in "。！？?!\n"),
                default=-1,
            )
            comma_start = text.rfind("、", clause_start + 1, match.end())
            if (
                comma_start > clause_start
                and re.match(
                    r"、\s*(?:あなた|君|そっち|うるは)(?:は|が|に)?",
                    text[comma_start:match.end()],
                )
            ):
                # A new, explicit second-person clause after a report must
                # not inherit the report's third-party actor.
                clause_start = comma_start
            clause = text[clause_start + 1:match.end()]
            if (
                _VISIBLE_THIRD_PARTY_SUBJECT.search(clause)
                or _VISIBLE_THIRD_PARTY_RECIPIENT.search(clause)
            ):
                continue
            cues.append(cue_id)
            break
    return cues


def _direct_self_cues(text):
    cues = []
    for cue_id, pattern in _SELF_DEFER:
        for match in pattern.finditer(text):
            clause_start = max(
                (text.rfind(mark, 0, match.start()) for mark in "。！？?!\n"),
                default=-1,
            )
            clause = text[clause_start + 1:match.end()]
            if _VISIBLE_THIRD_PARTY_SUBJECT.search(clause):
                continue
            cues.append(cue_id)
            break
    return cues


def classify_temporal_actor_scope_p4(user_input):
    """Classify a narrow observable action relation; leave others unknown."""

    text = str(user_input or "")
    quoted = bool(_QUOTED.search(text))
    direct_text = _QUOTED.sub(" ", text)
    reported = bool(quoted and _THIRD_PARTY_REPORT.search(direct_text))
    negated_assistant = bool(_NEGATED_ASSISTANT_REQUEST.search(direct_text))
    extra_clause = bool(
        re.search(r"[。！？?!\n]\s*\S", direct_text)
        or re.search(
            r"[、,]\s*(?:あと|それと|ついでに|また|あなたは|君は|"
            r"そっちは|うるはは|另外|還有|还有|also|and)",
            direct_text, re.I,
        )
    )
    self_cues = _direct_self_cues(direct_text)
    assistant_cues = (
        [] if negated_assistant
        else _direct_assistant_cues(direct_text)
    )
    if assistant_cues:
        actor, action, status = (
            "assistant", "ask_response_form_first", "direct_assistant_request"
        )
    elif self_cues:
        actor, action, status = (
            "user_self", "defer_reply_after_self_check", "direct_user_self_defer"
        )
    elif reported:
        actor, action, status = (
            "third_party", "unresolved", "reported_instruction_not_direct"
        )
    else:
        actor, action, status = "unknown", "unresolved", "actor_or_action_unresolved"
    return {
        "schema": SCHEMA,
        "status": status,
        "source_kind": (
            "mixed_direct_and_reported" if reported and assistant_cues
            else "third_party_report" if reported and not self_cues
            else "current_user_input"
        ),
        "actor": actor,
        "action": action,
        "temporal_relation": (
            "assistant_question_before_reply" if assistant_cues
            else "self_check_before_later_reply" if self_cues
            else "unknown"
        ),
        "self_defer_observed": bool(self_cues),
        "assistant_request_authorized": bool(assistant_cues),
        "negated_assistant_request_observed": negated_assistant,
        "additional_clause_observed": extra_clause,
        "evidence_cue_ids": [*self_cues, *assistant_cues],
        "quoted_span_present": quoted,
        "input_digest": _digest(text),
        "raw_dialogue_persisted": False,
        "stable_preference_claimed": False,
        "private_state_truth_claimed": False,
        "claim_boundary": "bounded observable actor/action relation, not open-domain intent",
    }


def gate_base_explicit_request_p4(user_input, original_classifier):
    """Gate only the M25 clarifier cue before P4-AT can inherit it."""

    base = deepcopy(original_classifier(user_input))
    scope = classify_temporal_actor_scope_p4(user_input)
    if (
        base.get("protected_risk_cue")
        or "calibrate_need" in (base.get("negated_policies") or [])
        or base.get("selected_policy") != "calibrate_need"
    ):
        scope["assistant_request_authorized"] = False
        if scope["actor"] == "assistant":
            scope["status"] = "direct_request_not_effectively_authorized"
    base[LABEL] = scope
    if (
        base.get("selected_policy") != "calibrate_need"
        or base.get("protected_risk_cue")
        or scope["assistant_request_authorized"]
    ):
        return base
    remaining = [
        row for row in base.get("alternatives") or []
        if row.get("policy_id") != "calibrate_need"
    ]
    selected = remaining[0] if remaining else {}
    if (
        scope["source_kind"] == "third_party_report"
        and not selected
        and not re.search(r"[?？]", _QUOTED.sub(" ", str(user_input or "")))
    ):
        # The report is a current observable speech act, but the instruction
        # inside the quote is not an instruction to this assistant.
        scope = {
            **scope,
            "status": "reported_check_instruction_not_direct",
            "action": "reported_check_instruction",
            "temporal_relation": "third_party_instruction_reported_now",
        }
        base[LABEL] = scope
    base.update({
        "detected": bool(selected),
        "status": "selected" if selected else "not_detected",
        "selected_policy": selected.get("policy_id"),
        "selected_mode": selected.get("mode"),
        "authority": (
            "current_explicit_desired_response" if selected else "not_applicable"
        ),
        "confidence": 0.90 if selected else 0.0,
        "alternatives": remaining,
        "matched_languages": sorted({
            row.get("language") for row in remaining if row.get("language")
        }),
        "actor_scope_rejection_reason_p4": (
            "calibrate_cue_lacks_direct_assistant_response_form_actor"
        ),
    })
    return base


def apply_temporal_actor_scope_to_plan_p4(plan, decision, original_apply):
    updated, original_trace = original_apply(plan, decision)
    scope = deepcopy(
        (((decision or {}).get("state") or {})
         .get("explicit_desired_response_m25") or {}).get(LABEL) or {}
    )
    if scope.get("schema") != SCHEMA:
        return updated, original_trace
    updated[LABEL] = scope
    selected = ((decision or {}).get("selected") or {})
    if (
        scope.get("action") not in {
            "defer_reply_after_self_check", "reported_check_instruction",
        }
        or scope.get("assistant_request_authorized")
        or scope.get("additional_clause_observed")
        or selected
        or updated.get("intent") != "chat"
        or updated.get("scene") != "casual"
        or str(updated.get("intent") or "") in adaptive.PROTECTED_INTENTS
        or str(updated.get("scene") or "") in adaptive.PROTECTED_SCENES
        or updated.get("memory_recall_contract")
        or updated.get("profile_grounding_shadow")
    ):
        return updated, original_trace
    reported = scope.get("action") == "reported_check_instruction"
    updated.update({
        "intent": "chat",
        "scene": "casual",
        "surface_act": (
            "ack_reported_check_instruction_p4"
            if reported else "ack_user_self_deferred_reply_p4"
        ),
        "reply_goal": (
            "第三者から先に確認するよう言われた報告として受ける"
            if reported else
            "使用者自身が先に確認し、後で返事する順序を尊重する"
        ),
        "core_message_jp": (
            _REPORTED_CHECK_REPLY_JP if reported else _DEFER_REPLY_JP
        ),
        "jp_summary": (
            _REPORTED_CHECK_REPLY_JP if reported else _DEFER_REPLY_JP
        ),
        "response_mode": (
            "acknowledge_reported_instruction"
            if reported else "acknowledge_user_deferred_reply"
        ),
    })
    updated[LABEL] = {**scope, "selected_action": updated["surface_act"]}
    return updated, {
        **deepcopy(original_trace or {}),
        LABEL: {
            "status": (
                "reported_instruction_action_selected"
                if reported else "self_defer_action_selected"
            ),
            "input_digest": scope["input_digest"],
        },
    }


def materialize_temporal_actor_scope_p4(result):
    """Attach the same bounded evidence before M25/selected/utterance in graph."""

    if not isinstance(result, dict):
        return result
    logic = result.get("logic")
    runtime_trace = result.get("runtime_trace")
    if not isinstance(logic, dict) or not isinstance(runtime_trace, dict):
        return result
    scope = deepcopy(
        (logic.get("explicit_desired_response_m25") or {}).get(LABEL)
        or logic.get(LABEL) or {}
    )
    if scope.get("schema") != SCHEMA:
        return result
    selected_plan = runtime_trace.get("selected_plan") or {}
    reply = str(result.get("reply") or "")
    scope.update({
        "selected_surface_act": selected_plan.get("surface_act"),
        "utterance_digest": _digest(reply),
        "surface_status": (
            "self_defer_ack_visible"
            if scope["action"] == "defer_reply_after_self_check"
            and selected_plan.get("surface_act") == "ack_user_self_deferred_reply_p4"
            and reply == _DEFER_REPLY_JP
            else "self_defer_ack_missing"
            if scope["action"] == "defer_reply_after_self_check"
            else "reported_instruction_ack_visible"
            if scope["action"] == "reported_check_instruction"
            and selected_plan.get("surface_act") == "ack_reported_check_instruction_p4"
            and reply == _REPORTED_CHECK_REPLY_JP
            else "reported_instruction_ack_missing"
            if scope["action"] == "reported_check_instruction"
            else "assistant_question_visible"
            if scope["action"] == "ask_response_form_first"
            and (
                ((logic.get("desired_response_decision_m18") or {})
                 .get("selected") or {}).get("policy_id") == "calibrate_need"
            )
            and reply == selected_plan.get("core_message_jp")
            and ("？" in reply or "?" in reply)
            else "assistant_question_missing"
            if scope["action"] == "ask_response_form_first"
            else "not_applicable"
        ),
    })
    logic[LABEL] = deepcopy(scope)
    runtime_trace[LABEL] = deepcopy(scope)
    rows = runtime_trace.get("blackboard")
    if isinstance(rows, list) and not any(
        isinstance(row, dict) and row.get("label") == LABEL for row in rows
    ):
        insert_at = next(
            (
                index for index, row in enumerate(rows)
                if isinstance(row, dict)
                and row.get("label") in {
                    "explicit_desired_response_m25", "desired_response_state_m18",
                    "selected_plan", "utterance",
                }
            ),
            len(rows),
        )
        rows.insert(insert_at, {
            "stage": "evidence",
            "label": LABEL,
            "payload": deepcopy(scope),
            "salience": 0.95,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        })
    return result


def install_temporal_actor_scope_p4():
    global _INSTALLED, _ORIGINAL_BASE_CLASSIFIER, _ORIGINAL_APPLY
    global _ORIGINAL_EMIT, _ORIGINAL_RUN
    if _INSTALLED:
        return False
    if not p4_at._INSTALLED_P4_AT or not callable(p4_at._ORIGINAL_CLASSIFIER_P4_AT):
        raise RuntimeError("p4_at_classifier_must_be_installed_first")
    from uruha_brain_mac import UruhaBrainV4_Mac

    _ORIGINAL_BASE_CLASSIFIER = p4_at._ORIGINAL_CLASSIFIER_P4_AT
    _ORIGINAL_APPLY = adaptive.apply_decision_to_plan
    _ORIGINAL_EMIT = UruhaBrainV4_Mac.emit_response_if_ready
    _ORIGINAL_RUN = UruhaBrainV4_Mac.run_turn_debug

    def base_with_actor_scope(user_input):
        return gate_base_explicit_request_p4(
            user_input, _ORIGINAL_BASE_CLASSIFIER
        )

    def apply_with_actor_scope(plan, decision):
        return apply_temporal_actor_scope_to_plan_p4(
            plan, decision, _ORIGINAL_APPLY
        )

    def emit_with_actor_scope(self, event, tick_result):
        result = _ORIGINAL_EMIT(self, event, tick_result)
        result = materialize_temporal_actor_scope_p4(result)
        if not isinstance(result, dict) or LABEL not in (result.get("runtime_trace") or {}):
            return result
        from uruha_trace_history_sync_m41_1 import sync_current_history_m41_1

        self.runtime.blackboard = deepcopy(result["runtime_trace"]["blackboard"])
        sync_current_history_m41_1(result)
        if getattr(self.runtime, "turn_traces", None):
            self.runtime.turn_traces[-1] = deepcopy(result["runtime_trace"])
        return result

    def run_with_actor_scope(self, user_input, input_context=None):
        # Base run_turn_debug appends M19 latency *after* emit and caps the
        # blackboard at 67 nodes.  Deliver the typed node again at the final
        # returned-trace boundary, instead of letting that cap erase it.
        result = _ORIGINAL_RUN(self, user_input, input_context=input_context)
        result = materialize_temporal_actor_scope_p4(result)
        if not isinstance(result, dict) or LABEL not in (result.get("runtime_trace") or {}):
            return result
        from uruha_trace_history_sync_m41_1 import sync_current_history_m41_1

        self.runtime.blackboard = deepcopy(result["runtime_trace"]["blackboard"])
        sync_current_history_m41_1(result)
        if getattr(self.runtime, "turn_traces", None):
            self.runtime.turn_traces[-1] = deepcopy(result["runtime_trace"])
        return result

    # P4-AT's already-installed classifier and observer both read this global
    # at call time.  Updating only adaptive.classify_explicit... would leave its
    # observer using the old evidence and could corrupt feedback calibration.
    p4_at._ORIGINAL_CLASSIFIER_P4_AT = base_with_actor_scope
    adaptive.apply_decision_to_plan = apply_with_actor_scope
    UruhaBrainV4_Mac.emit_response_if_ready = emit_with_actor_scope
    UruhaBrainV4_Mac.run_turn_debug = run_with_actor_scope
    _INSTALLED = True
    return True


__all__ = [
    "LABEL", "SCHEMA", "classify_temporal_actor_scope_p4",
    "gate_base_explicit_request_p4", "apply_temporal_actor_scope_to_plan_p4",
    "materialize_temporal_actor_scope_p4", "install_temporal_actor_scope_p4",
]
