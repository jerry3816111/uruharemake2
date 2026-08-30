"""M40: preserve lexical evidence before a boundary cue becomes social threat.

Research core: observable human signals must not be replaced by invented tokens.
Uruha is the persona instance, not a claim of private-state truth or consciousness.
The same existing rule code/cue inventory runs with one scoped matcher change.
This is not an affirmation whitelist, a safety bypass, or a new reply template.
"""

from contextvars import ContextVar
from copy import deepcopy
from functools import lru_cache
import hashlib
import re
import time
from types import FunctionType

import uruha_leftbrain_rules as rules


SCHEMA_M40 = "uruha_evidence_bounded_lexical_route_m40"
_ORIGINAL_BOUNDARY = rules.get_boundary_refusal_plan
_ORIGINAL_CONTAINS = rules.contains_any
_ORIGINAL_HITS = rules.keyword_hits
_MATCH_AUDIT = ContextVar("m40_match_audit", default=None)
_SIGNAL_AUDIT = ContextVar("m40_signal_audit", default=None)
_INSTALLED_M40 = False


@lru_cache(maxsize=512)
def _latin_pattern(keyword):
    tokens = re.findall(r"[a-z0-9]+", keyword.lower())
    # Keep both outer word boundaries. Separators may occur inside a cue
    # (e.g. a deliberately spaced/slashed word) but cannot erase a neighbor.
    body = r"[\W_]*".join(re.escape(c) for c in "".join(tokens))
    return re.compile(r"(?<![a-z0-9])" + body + r"(?![a-z0-9])", re.I)


def lexical_match_m40(text, keyword):
    """Match a fixed inventory cue, returning raw-free evidence only."""
    text = str(text or "").lower()
    keyword = str(keyword or "").lower()
    legacy = bool(keyword and _ORIGINAL_CONTAINS(text, [keyword]))
    latin = bool(keyword and keyword.isascii() and re.search(r"[a-z]", keyword))
    matched = bool(_latin_pattern(keyword).search(text)) if latin else legacy
    if not latin:
        kind = "unchanged_non_latin" if matched else "absent"
    elif matched:
        kind = "bounded_latin_cue"
    elif legacy:
        kind = "rejected_embedded_or_cross_token_cue"
    else:
        kind = "absent"
    evidence = {
        "cue_id": hashlib.sha256(keyword.encode()).hexdigest()[:12],
        "kind": kind,
        "legacy_match": legacy,
        "bounded_match": matched,
    }
    collector = _MATCH_AUDIT.get()
    if collector is not None and (matched or legacy):
        collector.append(evidence)
    return matched, evidence


def _contains_m40(text, keywords):
    return any(lexical_match_m40(text, keyword)[0] for keyword in keywords)


def _hits_m40(text, keywords):
    return sum(lexical_match_m40(text, keyword)[0] for keyword in keywords)


# Share byte-identical rule code without mutating the global helpers used by
# unrelated rules or concurrent requests. Only this function's globals differ.
_GUARDED_BOUNDARY = FunctionType(
    _ORIGINAL_BOUNDARY.__code__,
    dict(_ORIGINAL_BOUNDARY.__globals__, contains_any=_contains_m40, keyword_hits=_hits_m40),
    name="get_boundary_refusal_plan_m40",
    argdefs=_ORIGINAL_BOUNDARY.__defaults__,
    closure=_ORIGINAL_BOUNDARY.__closure__,
)


def _plan_type(plan):
    return {"intent": (plan or {}).get("intent"), "scene": (plan or {}).get("scene")}


def evaluate_boundary_route_m40(user_input, recent_turns=None):
    """Return unchanged baseline, guarded rule plan and auditable difference.

    The baseline is a pure deterministic rule call, not another model request.
    Neither this routine nor its trace writes user facts, memory or raw text.
    """
    recent_turns = list(recent_turns or [])
    started = time.perf_counter()
    baseline = _ORIGINAL_BOUNDARY(user_input, recent_turns)
    baseline_seconds = time.perf_counter() - started
    evidence = []
    token = _MATCH_AUDIT.set(evidence)
    guarded_started = time.perf_counter()
    try:
        guarded = _GUARDED_BOUNDARY(user_input, recent_turns)
    finally:
        _MATCH_AUDIT.reset(token)
    guarded_seconds = time.perf_counter() - guarded_started
    rejected = [x for x in evidence if x["kind"] == "rejected_embedded_or_cross_token_cue"]
    before, after = _plan_type(baseline), _plan_type(guarded)
    trace = {
        "schema": SCHEMA_M40,
        "status": "lexical_attribution_corrected" if before != after else "existing_attribution_preserved",
        "baseline_boundary_plan": before,
        "guarded_boundary_plan": after,
        "changed": before != after,
        "rejected_unbounded_cue_count": len(rejected),
        "cue_evidence": evidence,
        "same_rule_code": _GUARDED_BOUNDARY.__code__ is _ORIGINAL_BOUNDARY.__code__,
        "affirmation_whitelist_used": False,
        "safety_cue_inventory_changed": False,
        "matcher_scope": "boundary_refusal_rule_only",
        "baseline_seconds": round(baseline_seconds, 8),
        "guarded_seconds": round(guarded_seconds, 8),
        "added_audit_seconds": round(time.perf_counter() - started, 8),
        "raw_dialogue_persisted": False,
        "mental_fact_write_count": 0,
        "model_call_count": 0,
        "claim_boundary": "bounded lexical attribution; not universal safety or private intent truth",
    }
    return baseline, guarded, trace


def _boundary_with_m40(user_input, recent_turns):
    _baseline, guarded, trace = evaluate_boundary_route_m40(user_input, recent_turns)
    collector = _SIGNAL_AUDIT.get()
    if collector is not None:
        collector.append(trace)
    return guarded


def install_m40_route_guard():
    """Install before brain construction; keep all frozen files unchanged."""
    global _INSTALLED_M40
    if _INSTALLED_M40:
        return False
    from uruha_brain_mac import LeftBrain, UruhaBrainV4_Mac

    original_classify = LeftBrain.classify_user_signal
    original_shape = UruhaBrainV4_Mac._classify_task_shape_m22
    original_emit = UruhaBrainV4_Mac.emit_response_if_ready

    def classify_with_m40(self, user_input, current_psyche, memory_data=None):
        audits = []
        token = _SIGNAL_AUDIT.set(audits)
        try:
            signal = original_classify(self, user_input, current_psyche, memory_data)
        finally:
            _SIGNAL_AUDIT.reset(token)
        if audits:
            trace = deepcopy(audits[-1])
            trace["actual_signal_intent"] = signal.get("actual_intent")
            trace["actual_signal_scene"] = signal.get("actual_scene")
            trace["actual_signal_abuse_like"] = bool(signal.get("abuse_like"))
            signal["lexical_boundary_route_m40"] = trace
        return signal

    def shape_with_m40(user_input, actual_signal=None, route_info=None,
                       grounded_profile_logic=None, correction_directive=None):
        shape = original_shape(user_input, actual_signal, route_info,
                               grounded_profile_logic, correction_directive)
        trace = deepcopy((actual_signal or {}).get("lexical_boundary_route_m40") or {})
        if trace:
            trace["performed_signal_route"] = (route_info or {}).get("route")
            trace["selected_task_shape"] = shape.get("selected_type")
            shape["lexical_boundary_route_m40"] = trace
        return shape

    def emit_with_m40(self, event, tick_result):
        result = original_emit(self, event, tick_result)
        logic = result.get("logic") or {}
        trace = deepcopy((logic.get("semantic_route_m22") or {}).get("lexical_boundary_route_m40") or {})
        if trace:
            runtime = result.get("runtime_trace") or {}
            nodes = list(runtime.get("blackboard") or [])
            index = next((i for i, x in enumerate(nodes) if x.get("label") == "semantic_route_classifier_m22"), 0)
            nodes.insert(index, {"stage": "route", "label": "lexical_boundary_route_m40", "payload": trace, "salience": 0.98})
            runtime["blackboard"] = nodes
            runtime["lexical_boundary_route_m40"] = trace
            result["runtime_trace"] = runtime
            logic["lexical_boundary_route_m40"] = trace
            result["logic"] = logic
            if self.runtime.turn_traces:
                self.runtime.turn_traces[-1] = deepcopy(runtime)
        return result

    rules.get_boundary_refusal_plan = _boundary_with_m40
    LeftBrain.classify_user_signal = classify_with_m40
    UruhaBrainV4_Mac._classify_task_shape_m22 = staticmethod(shape_with_m40)
    UruhaBrainV4_Mac.emit_response_if_ready = emit_with_m40
    _INSTALLED_M40 = True
    return True
