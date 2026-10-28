"""M43: let verified feedback own this turn without guessing another need.

Research intent is operational, corrigible human pragmatics. Uruha is the
persona instance; no private intent, acoustic signal or human equivalence is
asserted. Current act, prior outcome and provisional mental model are separate.
The full-coverage grammar is deliberately bounded. Residual content stays with
the existing planner. No reserve/example file is loaded by runtime code.
"""
from contextvars import ContextVar
from copy import deepcopy
import hashlib
import json
import re
import time

import uruha_adaptive_person_model as adaptive
import uruha_personhood_loop as personhood
import uruha_semantic_persona_surface_m39 as surface39

SCHEMA_M43 = "uruha_supported_feedback_closure_m43"
LABEL_M43 = "supported_feedback_closure_m43"
_BASE_BUILD = adaptive.build_feedback_topic_transition_m28
_BASE_APPLY = adaptive.apply_feedback_topic_transition_m28
_BASE_LONGITUDINAL = personhood.apply_longitudinal_model_to_plan
_BASE_VERIFY39 = surface39.verify_and_repair_surface_m39
_TURN = ContextVar("m43_current_turn", default=None)
_INSTALLED = False

_QUOTE = re.compile(r'「|」|『|』|“|”|"|(?<!\w)\x27[^\x27]+\x27(?!\w)')
_SEPARATOR = re.compile(r"[\s,，、。.!！;；:：…~～]+")
_ATOMS = [
    ("support", re.compile(p, re.I)) for p in (
        r"that(?:'s|\s+is)\s+(?:exactly\s+)?what\s+i\s+meant\b",
        r"(?:that(?:'s|\s+is)\s+)?(?:(?:exactly|precisely|absolutely)\s+)?(?:right|correct)\b",
        r"you\s+(?:(?:really|totally)\s+)?got\s+(?:it|that)(?:\s+right)?\b",
        r"exactly\b|indeed\b",
        r"(?:沒|没)錯|(?:正是|就是|是)(?:這|这)(?:樣|样|個意思|个意思)",
        r"你(?:理解|說|说)(?:得|的)?(?:很|完全)?(?:對|对|正確|正确)|對|对",
        r"その通り(?:だ(?:よ|ね)?|です)?|それで(?:合ってる|大丈夫|いい)|合ってる",
        r"そう(?:そう|だ(?:よ|ね)?|です)",
    )
] + [
    ("thanks", re.compile(r"thanks(?:\s+a\s+lot)?\b|thank\s+you\b|ありがとう(?:ございます|ね)?|謝謝你?|谢谢你?", re.I)),
    ("softener", re.compile(r"(?:yes|yeah|yep|well|okay|ok|really|absolutely)\b|嗯+|うん|ええ|まさに|本当に|確實|确实|真的", re.I)),
    ("particle", re.compile(r"だよ|だね|よ|ね|啦|喔|哦|啊|呀|呢")),
]


def _digest(value):
    if isinstance(value,(dict,list)):
        value = json.dumps(value,ensure_ascii=False,sort_keys=True)
    return hashlib.sha256(str(value or "").encode()).hexdigest()


def classify_support_act_m43(user_input):
    """Consume every character; a support word cannot swallow a new clause."""
    source = str(user_input or "")
    text = source.replace("’", "'")
    trace = {"status":"not_pure_support","source_digest":_digest(source),"source_length":len(source),
             "atoms":[],"unparsed_char_count":len(source),"has_thanks":False,
             "raw_dialogue_persisted":False,"private_intent":"unknown","acoustic_evidence":"unavailable"}
    if not text.strip() or re.search(r"[?？]",text) or _QUOTE.search(text):
        trace["reason"] = "empty_quoted_or_question_scope"
        return trace
    position = 0
    while position < len(text):
        sep = _SEPARATOR.match(text,position)
        if sep:
            position = sep.end()
            continue
        matches = [(kind,p.match(text,position)) for kind,p in _ATOMS]
        matches = [(kind,m) for kind,m in matches if m]
        if not matches:
            break
        kind,match = max(matches,key=lambda pair:pair[1].end())
        trace["atoms"].append({"kind":kind,"span":[position,match.end()],
                               "source_digest":_digest(source[position:match.end()])})
        position = match.end()
    trace["unparsed_char_count"] = len(text)-position
    trace["has_thanks"] = any(x["kind"]=="thanks" for x in trace["atoms"])
    pure = position==len(text) and any(x["kind"]=="support" for x in trace["atoms"])
    trace.update(status="pure_support" if pure else "not_pure_support",
                 reason="whole_utterance_is_support_act" if pure else "new_negative_or_unresolved_content_remains")
    return trace


def build_feedback_closure_m43(user_input,feedback,pragmatic_understanding):
    start = time.perf_counter()
    original = _BASE_BUILD(user_input,feedback,pragmatic_understanding)
    contract = deepcopy(original)
    act = classify_support_act_m43(user_input)
    decisive = bool((feedback or {}).get("previous_prediction_id")
                    and feedback.get("feedback_linked_to_previous_prediction")
                    and feedback.get("status")=="supported"
                    and (feedback.get("causal_outcome_calibration_m27") or {}).get("status")=="resolved_decisive")
    eligible = bool(decisive and act["status"]=="pure_support"
                    and not feedback.get("current_request_separated_from_feedback"))
    policy = (feedback or {}).get("previous_policy_id")
    realization_kind = "thanks_received" if act["has_thanks"] else "confirmed_interaction_policy" if policy in {"share_arousal","listen_presence"} else "plain_confirmation"
    surface = {"thanks_received":"ん、伝わってたならよかった。",
               "confirmed_interaction_policy":"うん。じゃ、その感じでいこう。",
               "plain_confirmation":"ん、分かった。"}[realization_kind]
    if eligible:
        contract.update(status="pure_feedback_acknowledgement",reason="m43_decisive_support_without_new_content",
                        current_turn_act="acknowledge_previous_response",surface_authority=True,
                        expected_surface_jp=surface,topic_kind="previous_response_feedback",
                        suppresses_new_pending_prediction=True)
    trace = {"schema":SCHEMA_M43,"status":"eligible_current_acknowledgement" if eligible else "existing_turn_preserved",
             "act":act,"decisive_previous_support":decisive,"eligible":eligible,"authoritative":False,
             "baseline_surface_authority":bool(original.get("surface_authority")),
             "previous_prediction_id":(feedback or {}).get("previous_prediction_id"),
             "previous_policy_id":policy,"upstream_feedback_digest":_digest(feedback),
             "upstream_outcome_changed":False,"realization_kind":realization_kind if eligible else None,
             "added_seconds":round(time.perf_counter()-start,8),"raw_dialogue_persisted":False,
             "mental_fact_write_count":0,"model_call_count":0,
             "claim_boundary":"bounded acknowledgement act; not support truth, human preference or general understanding"}
    contract[LABEL_M43] = trace
    return contract


def _protected(plan):
    return bool(str((plan or {}).get("intent") or "") in adaptive.PROTECTED_INTENTS
                or str((plan or {}).get("intent") or "").startswith("recall_")
                or (plan or {}).get("scene") in adaptive.PROTECTED_SCENES
                or (plan or {}).get("memory_recall_contract") or (plan or {}).get("profile_grounding_shadow")
                or ((plan or {}).get("semantic_route_m22") or {}).get("selected_type") in {"safety_sensitive","factual_or_memory","deliberation"})


def apply_feedback_closure_m43(plan,contract):
    updated,transition = _BASE_APPLY(plan,contract)
    trace = deepcopy(transition.get(LABEL_M43) or {})
    if trace:
        if trace.get("eligible") and _protected(plan):
            updated = deepcopy(plan)
            transition.update(status="protected_current_turn_retained",surface_authority=False,
                              suppresses_new_pending_prediction=False,plan_applied=False)
        trace["authoritative"] = bool(trace.get("eligible") and transition.get("surface_authority") and transition.get("plan_applied"))
        trace["status"] = "current_acknowledgement_authoritative" if trace["authoritative"] else "current_plan_preserved"
        trace["protected_current_plan"] = _protected(plan)
        transition[LABEL_M43] = trace
        updated[LABEL_M43] = deepcopy(trace)
        updated["feedback_topic_transition_m28"] = deepcopy(transition)
    return updated,transition


def close_linked_validation_m43(model,closure,turn_index):
    """Close only an explicitly bound response question, never a mental fact."""
    state = deepcopy(model)
    validation = state.get("active_validation") or {}
    pending = validation.get("pending") or {}
    source_id = closure.get("previous_prediction_id")
    matched = bool(closure.get("authoritative") and source_id
                   and pending.get("response_prediction_id_m43")==source_id
                   and pending.get("response_binding_verified_m43") is True
                   and pending.get("status")=="pending"
                   and int(pending.get("asked_turn",turn_index)) < int(turn_index))
    audit = {"status":"linked_response_question_closed" if matched else "unrelated_or_unbound_validation_retained",
             "closed_count":int(matched),"source_prediction_id":source_id,
             "validation_id":pending.get("validation_id"),"mental_fact_promoted":False}
    if matched:
        resolution = {"validation_id":pending.get("validation_id"),"model_item_id":pending.get("model_item_id"),
                      "status":"response_expectation_confirmed","resolved_turn":turn_index,
                      "response_prediction_id":source_id,"evidence_digest":closure.get("upstream_feedback_digest"),
                      "mental_fact_promoted":False}
        validation.update(pending=None,status="response_expectation_confirmed",
                          history=[*validation.get("history",[]),resolution][-12:])
        state["active_validation"] = validation
    return state,audit


def apply_longitudinal_closure_m43(plan,model,hypothesis,turn_index,contract,direct_user_report=None):
    """Preserve model updates while preventing a redundant new confirmation."""
    _,preview = apply_feedback_closure_m43(plan,contract)
    closure = preview.get(LABEL_M43) or {}
    if not closure.get("authoritative") or personhood._protected_plan(plan,hypothesis):
        updated,state,strategy = _BASE_LONGITUDINAL(plan,model,hypothesis,turn_index,direct_user_report)
        return updated,state,strategy,None
    prepared,audit = close_linked_validation_m43(model,closure,turn_index)
    validation_before = deepcopy(prepared.get("active_validation") or {})
    updated,state,strategy = _BASE_LONGITUDINAL(plan,prepared,hypothesis,turn_index,direct_user_report)
    created = bool(strategy.get("changed_plan") and not validation_before.get("pending"))
    if created:
        state["active_validation"] = validation_before
        # Restore only the action fields installed by active validation. Keep
        # the layered model, constraints and communication preference updates.
        for key in ("intent","scene","hidden_intent","reply_goal","core_message_jp",
                    "response_mode","surface_act","dialogue_act","payload_level"):
            if key in plan:
                updated[key] = deepcopy(plan[key])
            else:
                updated.pop(key,None)
        strategy.update(changed_plan=False,pending=deepcopy(validation_before.get("pending")),
                        reason="m43_confirmed_current_act_does_not_need_new_validation")
    audit["new_generic_validation_suppressed"] = created
    strategy[LABEL_M43] = audit
    updated["active_validation_strategy_v2_13"] = strategy
    return updated,state,strategy,audit


def bind_emitted_validation_m43(model,prediction,logic,reply,turn_index):
    """Bind an actually emitted question, not a planned-but-overridden one."""
    state = deepcopy(model)
    pending = (state.get("active_validation") or {}).get("pending") or {}
    matched = bool(pending.get("asked_turn")==turn_index and prediction.get("prediction_id")
                   and logic.get("surface_act")=="functional_understanding_active_verify"
                   and pending.get("question_jp") and pending.get("question_jp")==reply)
    audit = {"schema":"uruha_response_validation_binding_m43","verified":matched,
             "validation_id":pending.get("validation_id"),"prediction_id":prediction.get("prediction_id") if matched else None,
             "reply_digest":_digest(reply),"raw_dialogue_persisted":False,"mental_fact_promoted":False}
    if matched:
        pending["response_prediction_id_m43"] = prediction["prediction_id"]
        pending["response_binding_verified_m43"] = True
    return state,audit


def _live_closure(logic):
    contract = (logic or {}).get("feedback_topic_transition_m28") or {}
    trace = contract.get(LABEL_M43) or {}
    if (trace.get("schema")==SCHEMA_M43 and trace.get("authoritative")
            and contract.get("surface_authority") and contract.get("plan_applied") and not _protected(logic)):
        return contract,trace
    return None,None


def verify_current_act_surface_m43(user_input,reply,logic):
    contract,closure = _live_closure(logic)
    if not closure:
        return _BASE_VERIFY39(user_input,reply,logic)
    expected = contract["expected_surface_jp"]
    projected = deepcopy(logic)
    # Preserve the historical branch ledger. Only the M39 audit view changes:
    # this turn acknowledges a past policy; it must not execute that policy again.
    projected["counterfactual_pragmatic_branch_m34"] = {}
    projected["desired_response_policy_m18"] = None
    projected["desired_response_decision_m18"] = {}
    final,trace39 = _BASE_VERIFY39(user_input,expected,projected)
    trace39.update(current_turn_act_m43="acknowledge_previous_response",
                   previous_policy_not_reexecuted_m43=closure.get("previous_policy_id"))
    closure = deepcopy(closure)
    closure["surface"] = {"status":"verified_acknowledgement" if final==expected else "acknowledgement_verification_failed",
                           "changed":str(reply or "").strip()!=final,"input_reply_digest":_digest(reply),
                           "final_reply_digest":_digest(final),"question_reopened":bool(re.search(r"[?？]|教えて|聞かせて",final)),
                           "m39_role_register_checks_retained":True,"raw_reply_persisted":False}
    logic[LABEL_M43] = deepcopy(closure)
    logic["feedback_topic_transition_m28"][LABEL_M43] = deepcopy(closure)
    return final,trace39


def materialize_feedback_trace_m43(result):
    logic = result.get("logic") or {}
    payload = (logic.get("feedback_topic_transition_m28") or {}).get(LABEL_M43) or logic.get(LABEL_M43)
    current = result.setdefault("runtime_trace",{})
    rows = [x for x in current.get("blackboard",[]) if x.get("label") not in {LABEL_M43,"response_validation_binding_m43"}]
    if isinstance(payload,dict) and payload.get("schema")==SCHEMA_M43 and payload.get("raw_dialogue_persisted") is False:
        logic[LABEL_M43] = deepcopy(payload)
        current[LABEL_M43] = deepcopy(payload)
        anchor = next((i for i,x in enumerate(rows) if x.get("label")=="selected_plan"),len(rows))
        rows.insert(anchor,{"label":LABEL_M43,"stage":"select","payload":deepcopy(payload),"salience":0.98})
    else:
        current.pop(LABEL_M43,None)
    binding = logic.get("response_validation_binding_m43")
    if isinstance(binding,dict) and binding.get("schema")=="uruha_response_validation_binding_m43":
        rows.append({"label":"response_validation_binding_m43","stage":"writeback","payload":deepcopy(binding),"salience":0.9})
    current["blackboard"] = rows
    result["logic"] = logic


def install_m43_feedback_closure():
    global _INSTALLED
    if _INSTALLED:
        return False
    from uruha_brain_mac import UruhaBrainV4_Mac
    from uruha_trace_history_sync_m41_1 import sync_current_history_m41_1
    old_tick = UruhaBrainV4_Mac.cognitive_tick
    old_emit = UruhaBrainV4_Mac.emit_response_if_ready
    old_run = UruhaBrainV4_Mac.run_turn_debug

    def build(user_input,feedback,pragmatic):
        contract = build_feedback_closure_m43(user_input,feedback,pragmatic)
        context = _TURN.get()
        if context is not None:
            context["contract"] = deepcopy(contract)
        return contract

    def longitudinal(plan,model,hypothesis,turn_index,direct_user_report=None):
        contract = (_TURN.get() or {}).get("contract") or {}
        updated,state,strategy,audit = apply_longitudinal_closure_m43(
            plan,model,hypothesis,turn_index,contract,direct_user_report)
        context = _TURN.get()
        if context is not None:
            context["validation"] = deepcopy(audit)
        return updated,state,strategy

    def apply(plan,contract):
        updated,transition = apply_feedback_closure_m43(plan,contract)
        trace = transition.get(LABEL_M43)
        if trace and (_TURN.get() or {}).get("validation"):
            trace["validation"] = deepcopy(_TURN.get()["validation"])
            updated[LABEL_M43] = deepcopy(trace)
            updated["feedback_topic_transition_m28"] = deepcopy(transition)
        return updated,transition

    def tick(self,event):
        token = _TURN.set({})
        try:
            return old_tick(self,event)
        finally:
            _TURN.reset(token)

    def finish(self,result):
        materialize_feedback_trace_m43(result)
        self.runtime.blackboard = deepcopy(result["runtime_trace"]["blackboard"])
        sync_current_history_m41_1(result)
        if self.runtime.turn_traces and self.runtime.turn_traces[-1].get("cycle_index")==result["runtime_trace"].get("cycle_index"):
            self.runtime.turn_traces[-1] = deepcopy(result["runtime_trace"])
        return result

    def emit(self,event,tick_result):
        result = old_emit(self,event,tick_result)
        prediction = self.runtime.adaptive_person_model.get("pending_prediction") or {}
        logic = result.get("logic") or {}
        model,binding = bind_emitted_validation_m43(self.runtime.longitudinal_user_model,prediction,logic,
                                                   result.get("reply"),self.runtime.cycle_index)
        if binding["verified"]:
            self.runtime.longitudinal_user_model = model
            # This is a post-emission binding, not a retroactive edit to earlier
            # planning observations or memory retrieval. Sync only final state.
            snapshot = result.get("runtime_state") or {}
            if "longitudinal_user_model_v2_13" in snapshot:
                snapshot["longitudinal_user_model_v2_13"] = deepcopy(model)
        logic["response_validation_binding_m43"] = binding
        result["logic"] = logic
        return finish(self,result)

    def run(self,user_input,input_context=None):
        return finish(self,old_run(self,user_input,input_context=input_context))

    adaptive.build_feedback_topic_transition_m28 = build
    adaptive.apply_feedback_topic_transition_m28 = apply
    personhood.apply_longitudinal_model_to_plan = longitudinal
    surface39.verify_and_repair_surface_m39 = verify_current_act_surface_m43
    UruhaBrainV4_Mac.cognitive_tick = tick
    UruhaBrainV4_Mac.emit_response_if_ready = emit
    UruhaBrainV4_Mac.run_turn_debug = run
    _INSTALLED = True
    return True
