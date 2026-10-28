"""M42: authorize a relationship act, not a character inside another word.

Observable acts and their scope are separate from inferred private desires.
Uruha supplies the persona boundary; this mechanism neither copies her private
life nor claims consciousness. No raw dialogue or mental facts are persisted.
Two inherited rule entry points share one evidence gate. No reply is authored
here and no other safety family is disabled. Unknown targeting retains the old
boundary conservatively; it is never promoted to a known relationship demand.
"""
from contextvars import ContextVar
from copy import deepcopy
import hashlib
import re
import time
from types import FunctionType

import uruha_leftbrain_rules as rules
import uruha_lexical_boundary_route_m40 as m40

SCHEMA_M42 = "uruha_cjk_relationship_act_evidence_m42"
LABEL_M42 = "cjk_relationship_evidence_m42"
_ORIGINAL_RULE = rules.get_rule_based_plan
_GATE = ContextVar("m42_relationship_evidence", default=None)
_BOUNDARY_AUDITS = ContextVar("m42_boundary_audits", default=None)
_RULE_AUDITS = ContextVar("m42_rule_audits", default=None)
_INSTALLED = False


def _relationship_group(keywords):
    # Identify only the four inherited relationship cue groups. The dependency
    # code is frozen; do not globally change shared substring matching.
    words = set(keywords)
    return (({"marry", "嫁"} <= words)
            or {"call me baby", "うちだけのもの"} <= words
            or {"今すぐ結婚", "跟我交往"} <= words
            or {"cut off every other vtuber", "只看我"} <= words)


_CUE_GROUPS = [c for f in (_ORIGINAL_RULE, m40._ORIGINAL_BOUNDARY)
               for c in f.__code__.co_consts if isinstance(c, tuple)
               and all(isinstance(x, str) for x in c) and _relationship_group(c)]
assert len(_CUE_GROUPS) == 4, "Inherited relationship groups changed; review scope"
_CUES = tuple(dict.fromkeys(c for group in _CUE_GROUPS for c in group))
_RELATION = re.compile(r"結婚|结婚|求婚|付き合|交往|嫁|妻|夫|旦那|彼氏|彼女|男朋友|女朋友|只[屬属][於于]|只看我|うちだけ|うちなし|うち無し|ベイビー")
_QUOTE = re.compile(r'「[^」]*」|『[^』]*』|“[^”]*”|"[^"\n]*"')
_REPORT = re.compile(r"小説|小說|小说|故事|劇情|剧情|台詞|セリフ|翻[譯译]|引用|と言っ|と[話書]し|という|[說说]道?|聞かれ|書いて")
_SAY_TO_ME = re.compile(r"(?:對|对|跟)我[說说]|(?:私|俺|僕|うち)に.{0,6}言って|(?:そう|それ)って言って|そう呼んで")
_NEGATION = re.compile(r"わけ(?:では|じゃ)?ない|つもり(?:は|も)?ない|(?:とは|と)?(?:頼|望|求)んで(?:は)?いない|要求して(?:は)?いない|したくない|(?:不是|並非|并非).{0,12}(?:要|想|求)|(?:沒有|没有|沒|没|不曾).{0,6}(?:要求|請求|请求)|(?:不要|別|别).{0,8}(?:當|当|成為|成为|結婚|结婚)")
_THIRD_PARTY = re.compile(r"(?:姉|兄|妹|弟|母|父|友人|友達|知人|同僚|彼|彼女)(?:の|が|は)|(?:私|僕|俺|うち)の(?:夫|妻|旦那|嫁)|(?:我的|我家|朋友|同事|鄰居|邻居|[她他]的).{0,5}(?:丈夫|妻子|太太|先生|結婚|结婚)")
_TOPIC = re.compile(r"について|という言葉|の意味|這個詞|这个词|這個字|这个字|用詞|用词")
_DIRECT = re.compile(
    r"(?:結婚|付き合)(?:して|って|しよう|おう|しない[？?]|わない[？?])"
    r"|(?:夫|嫁|妻|旦那|彼氏|彼女)に(?:なって|なれ|なろう)"
    r"|(?:跟|和|與|与)我.{0,3}(?:結婚|结婚|交往)"
    r"|(?:當|当|成為|成为|做)(?:我(?:的)?)(?:丈夫|妻子|老婆|老公|男朋友|女朋友)"
    r"|(?:[你妳].{0,4})?只[屬属][於于]我|只看我|彼氏扱い|うちだけのもの"
    r"|(?:把我[當当]男朋友|叫我[寶宝][貝贝]|うちなしじゃ無理|うち無しじゃ無理)"
)


def _evidence(kind, text, start=0, end=None):
    end = len(text) if end is None else end
    return {"kind": kind, "span": [start, end],
            "source_sha256": hashlib.sha256(text[start:end].encode()).hexdigest()}


def relationship_evidence_m42(user_input):
    """Bounded surface grammar; evidence is not a user's mental-state truth."""
    text = str(user_input or "")
    hits = [cue for cue in _CUES if m40.lexical_match_m40(text, cue)[0]]
    cjk = [cue for cue in hits if not cue.isascii()]
    latin = [cue for cue in hits if cue.isascii()]
    result = {"authorization": "not_applicable", "reason": "no_cjk_relationship_candidate",
              "evidence": [], "known": "current visible wording only",
              "private_intent": "unknown", "acoustic_evidence": "unavailable",
              "alternatives": ["literal mention", "direct relationship request", "unclear target"]}
    if not cjk or latin:
        if latin:
            result["reason"] = "latin_or_mixed_candidate_preserved_outside_scope"
        return result
    evidence = []
    outer = list(text)
    quotes = list(_QUOTE.finditer(text))
    for q in quotes:
        outer[q.start():q.end()] = " " * (q.end() - q.start())
        evidence.append(_evidence("quoted_scope", text, q.start(), q.end()))
    outside = "".join(outer)
    unresolved_quote = bool(quotes and not _REPORT.search(outside))
    # Quoting is not always mentioning: asking the agent to say an exclusive
    # phrase is still a request. Otherwise parse only unquoted clauses.
    if quotes and _SAY_TO_ME.search(outside) and any(_RELATION.search(q.group()) for q in quotes):
        result.update(authorization="authorized", reason="directed_quoted_utterance_request", evidence=evidence)
        return result
    denied = reported = False
    for clause_match in re.finditer(r"[^。！？!?；;\n，,]+", outside):
        clause = clause_match.group()
        if not _RELATION.search(clause):
            continue
        if _NEGATION.search(clause):
            denied = True
            evidence.append(_evidence("explicit_denial_scope", text, *clause_match.span()))
            continue
        # Third-party reporting must not become the agent's own relationship.
        # An explicit second-person imperative in another clause is still kept.
        third = _THIRD_PARTY.search(clause)
        action = _DIRECT.search(clause)
        if third and (not action or re.search(r"(?:と[言話]|[說说]|らしい|くれた|予定|参加|參加)", clause)):
            reported = True
            evidence.append(_evidence("third_party_report", text, *clause_match.span()))
            continue
        if action:
            result.update(authorization="authorized", reason="directed_relationship_act",
                          evidence=evidence + [_evidence("directive_construction", text,
                                                        clause_match.start()+action.start(), clause_match.start()+action.end())])
            return result
        if _TOPIC.search(clause):
            reported = True
            evidence.append(_evidence("metalinguistic_mention", text, *clause_match.span()))
    if unresolved_quote:
        authorization, reason = "uncertain", "quoted_target_unresolved"
    elif denied:
        authorization, reason = "not_authorized", "explicit_denial_without_positive_request"
    elif reported or (quotes and _REPORT.search(outside) and not _RELATION.search(outside)):
        authorization, reason = "not_authorized", "reported_or_quoted_not_directed"
    else:
        # A substring inside a larger expression supplies neither an act nor
        # a target. No sentence whitelist: all one-character cues follow this.
        meaningful = [cue for cue in cjk if len(cue) > 1]
        standalone = any(text.strip(" 。？！?!，,、") == cue for cue in cjk)
        if not meaningful and not standalone and not re.search(r"(?:の|的)(?:夫|嫁)|(?:夫|嫁)[にと？?]", text):
            authorization, reason = "not_authorized", "lexical_fragment_without_relationship_act"
        else:
            authorization, reason = "uncertain", "relationship_target_or_act_unresolved"
    result.update(authorization=authorization, reason=reason, evidence=evidence)
    return result


def _gated_contains(text, keywords):
    if _relationship_group(keywords) and (_GATE.get() or {}).get("authorization") == "not_authorized":
        return False
    return rules.contains_any(text, keywords)


def _gated_boundary_contains(text, keywords):
    if _relationship_group(keywords) and (_GATE.get() or {}).get("authorization") == "not_authorized":
        return False
    return m40._contains_m40(text, keywords)


_GATED_BOUNDARY = FunctionType(m40._ORIGINAL_BOUNDARY.__code__,
    dict(m40._ORIGINAL_BOUNDARY.__globals__, contains_any=_gated_boundary_contains, keyword_hits=m40._hits_m40),
    argdefs=m40._ORIGINAL_BOUNDARY.__defaults__)


def _baseline_boundary(text, recent):
    _old, plan, trace = m40.evaluate_boundary_route_m40(text, recent)
    collector = _BOUNDARY_AUDITS.get()
    if collector is not None:
        collector.append(trace)
    return plan


def _guarded_boundary(text, recent):
    candidate = _baseline_boundary(text, recent)
    if (candidate or {}).get("intent") == "marriage_boundary" and (_GATE.get() or {}).get("authorization") == "not_authorized":
        return _GATED_BOUNDARY(text, recent)
    return candidate


_BASELINE_RULE = FunctionType(_ORIGINAL_RULE.__code__,
    dict(_ORIGINAL_RULE.__globals__, get_boundary_refusal_plan=_baseline_boundary), argdefs=_ORIGINAL_RULE.__defaults__)
_GATED_RULE = FunctionType(_ORIGINAL_RULE.__code__,
    dict(_ORIGINAL_RULE.__globals__, contains_any=_gated_contains, get_boundary_refusal_plan=_guarded_boundary), argdefs=_ORIGINAL_RULE.__defaults__)


def evaluate_relationship_route_m42(user_input, recent_turns=None, current_psyche=None, *, level="boundary"):
    started = time.perf_counter()
    evidence = relationship_evidence_m42(user_input)
    context = _GATE.set(evidence)
    collector = _BOUNDARY_AUDITS.set([])
    try:
        args = (user_input, list(recent_turns or []))
        if level == "rule":
            before = _BASELINE_RULE(*args, current_psyche=current_psyche)
            _BOUNDARY_AUDITS.get().clear()
            after = _GATED_RULE(*args, current_psyche=current_psyche)
        else:
            before = _baseline_boundary(*args)
            _BOUNDARY_AUDITS.get().clear()
            after = _guarded_boundary(*args)
        m40_trace = deepcopy((_BOUNDARY_AUDITS.get() or [None])[-1])
    finally:
        _BOUNDARY_AUDITS.reset(collector)
        _GATE.reset(context)
    kinds = lambda p: {"intent":(p or {}).get("intent"),"scene":(p or {}).get("scene")}
    trace = {"schema":SCHEMA_M42, **evidence, "candidate_plan":kinds(before),
             "authorized_plan":kinds(after), "changed":before != after,
             "evaluation_level":level, "status":"relationship_attribution_corrected" if before != after else "existing_attribution_preserved",
             "added_seconds":round(time.perf_counter()-started,8),
             "raw_dialogue_persisted":False,"mental_fact_write_count":0,"model_call_count":0,
             "claim_boundary":"bounded current act evidence, not private intent, universal safety or human understanding"}
    if m40_trace:
        m40_trace["downstream_cjk_authorization_m42"] = evidence["authorization"]
    return before, after, trace, m40_trace


def _rule_with_m42(user_input, recent_turns, current_psyche=None):
    _old, plan, trace, lexical = evaluate_relationship_route_m42(user_input,recent_turns,current_psyche,level="rule")
    if _RULE_AUDITS.get() is not None:
        _RULE_AUDITS.get().append(trace)
    if lexical and m40._SIGNAL_AUDIT.get() is not None:
        m40._SIGNAL_AUDIT.get().append(lexical)
    return plan


def materialize_relationship_trace_m42(result):
    logic = result.get("logic") or {}
    payload = logic.get(LABEL_M42) or (logic.get("semantic_route_m22") or {}).get(LABEL_M42)
    current = result.setdefault("runtime_trace", {})
    rows = [x for x in current.get("blackboard",[]) if x.get("label") != LABEL_M42]
    if isinstance(payload,dict) and payload.get("schema") == SCHEMA_M42 and payload.get("raw_dialogue_persisted") is False:
        logic[LABEL_M42] = deepcopy(payload)
        current[LABEL_M42] = deepcopy(payload)
        position = next((i for i,x in enumerate(rows) if x.get("label")=="semantic_route_classifier_m22"),len(rows))
        rows.insert(position,{"label":LABEL_M42,"stage":"route","payload":deepcopy(payload),"salience":0.98})
    else:
        current.pop(LABEL_M42,None)
    current["blackboard"] = rows
    result["logic"] = logic


def install_m42_relationship_evidence():
    global _INSTALLED
    if _INSTALLED:
        return False
    from uruha_brain_mac import LeftBrain, UruhaBrainV4_Mac
    from uruha_trace_history_sync_m41_1 import sync_current_history_m41_1
    original_classify = LeftBrain.classify_user_signal
    original_shape = UruhaBrainV4_Mac._classify_task_shape_m22
    original_emit = UruhaBrainV4_Mac.emit_response_if_ready
    original_run = UruhaBrainV4_Mac.run_turn_debug

    def classify(self,user_input,current_psyche,memory_data=None):
        audits = []
        token = _RULE_AUDITS.set(audits)
        try:
            signal = original_classify(self,user_input,current_psyche,memory_data)
        finally:
            _RULE_AUDITS.reset(token)
        if audits:
            trace = deepcopy(audits[-1])
            trace.update(actual_signal_intent=signal.get("actual_intent"),actual_signal_scene=signal.get("actual_scene"))
            signal[LABEL_M42] = trace
        return signal

    def shape(user_input,actual_signal=None,route_info=None,grounded_profile_logic=None,correction_directive=None):
        result = original_shape(user_input,actual_signal,route_info,grounded_profile_logic,correction_directive)
        trace = deepcopy((actual_signal or {}).get(LABEL_M42))
        if trace:
            trace.update(selected_task_shape=result.get("selected_type"),performed_signal_route=(route_info or {}).get("route"))
            result[LABEL_M42] = trace
        return result

    def finish(self,result):
        materialize_relationship_trace_m42(result)
        self.runtime.blackboard = deepcopy(result["runtime_trace"]["blackboard"])
        sync_current_history_m41_1(result)
        if self.runtime.turn_traces and self.runtime.turn_traces[-1].get("cycle_index") == result["runtime_trace"].get("cycle_index"):
            self.runtime.turn_traces[-1] = deepcopy(result["runtime_trace"])
        return result

    def emit(self,event,tick_result):
        return finish(self,original_emit(self,event,tick_result))

    def run(self,user_input,input_context=None):
        return finish(self,original_run(self,user_input,input_context=input_context))

    rules.get_rule_based_plan = _rule_with_m42
    LeftBrain.classify_user_signal = classify
    UruhaBrainV4_Mac._classify_task_shape_m22 = staticmethod(shape)
    UruhaBrainV4_Mac.emit_response_if_ready = emit
    UruhaBrainV4_Mac.run_turn_debug = run
    _INSTALLED = True
    return True
