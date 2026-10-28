"""Product-only, current-turn evidence for the bare Japanese relationship question.

The inherited compact matcher is intentionally unchanged.  Only the two bare
``好き？/好き?`` relationship cues need a full-turn question and target check.
M42's baseline and guarded rule clones receive the same detector, so an M42
before/after audit cannot claim this later P4 correction as its own effect.
"""

from __future__ import annotations

from contextvars import ContextVar
from functools import wraps
from types import FunctionType

import uruha_cjk_relationship_evidence_m42 as m42
import uruha_leftbrain_rules as rules


_FULL_TURN = ContextVar("p4_relationship_question_full_turn", default=None)
_BARE_CUES = frozenset({"好き？", "好き?"})
_AUTHORIZED_TURNS = frozenset({"好き？", "好き?", "ねえ、好き？", "ねえ、好き?"})
_ORIGINAL_DETECTOR = rules._detect_relationship_intent
_ORIGINAL_RULE_PLAN = None
_ORIGINAL_INLINE_PLAN = None
_ORIGINAL_INLINE_CONTAINS = None
_ORIGINAL_M42_CLONES = None
_INSTALLED = False


def bare_question_authorized_p4(user_input):
    """The four permitted whole-turn surfaces; no clause or quote expansion."""
    return str(user_input or "").strip() in _AUTHORIZED_TURNS


def _full_turn_or(text):
    current = _FULL_TURN.get()
    return str(text or "") if current is None else current


def relationship_intent_with_question_evidence_p4(text):
    """Run the inherited detector on the actual text with a scoped cue matcher."""
    return _SCOPED_DETECTOR(text)


def _relationship_contains_with_question_evidence(text, keywords):
    words = tuple(keywords)
    if _BARE_CUES.intersection(words) and not bare_question_authorized_p4(_full_turn_or(text)):
        words = tuple(word for word in words if word not in _BARE_CUES)
    return rules.contains_any(text, words)


_SCOPED_DETECTOR = FunctionType(
    _ORIGINAL_DETECTOR.__code__,
    dict(_ORIGINAL_DETECTOR.__globals__, contains_any=_relationship_contains_with_question_evidence),
    argdefs=_ORIGINAL_DETECTOR.__defaults__,
)


def _with_full_turn(original):
    @wraps(original)
    def wrapped(user_input, *args, **kwargs):
        token = _FULL_TURN.set(str(user_input or ""))
        try:
            return original(user_input, *args, **kwargs)
        finally:
            _FULL_TURN.reset(token)

    wrapped._p4_question_full_turn = True
    return wrapped


def _inline_plan_with_full_turn(self, user_input, current_psyche, memory_data=None):
    token = _FULL_TURN.set(str(user_input or ""))
    try:
        return _ORIGINAL_INLINE_PLAN(self, user_input, current_psyche, memory_data)
    finally:
        _FULL_TURN.reset(token)


def _inline_contains_with_question_evidence(self, text, keywords):
    words = tuple(keywords)
    if _BARE_CUES.intersection(words) and not bare_question_authorized_p4(_full_turn_or(text)):
        words = tuple(word for word in words if word not in _BARE_CUES)
    return _ORIGINAL_INLINE_CONTAINS(self, text, words)


def install_relationship_question_evidence_p4():
    """Add one scoped matcher after the existing M42/product install chain."""
    global _INSTALLED, _ORIGINAL_RULE_PLAN, _ORIGINAL_INLINE_PLAN
    global _ORIGINAL_INLINE_CONTAINS, _ORIGINAL_M42_CLONES
    if _INSTALLED:
        return False
    from uruha_brain_mac import LeftBrain

    if not m42._INSTALLED:
        raise RuntimeError("P4 question evidence requires installed M42 rule clones")
    if rules._detect_relationship_intent is not _ORIGINAL_DETECTOR:
        raise RuntimeError("relationship detector changed before P4 question install")
    clones = (m42._BASELINE_RULE, m42._GATED_RULE)
    if any(clone.__globals__.get("_detect_relationship_intent") is not _ORIGINAL_DETECTOR for clone in clones):
        raise RuntimeError("M42 rule-clone detector changed before P4 question install")

    _ORIGINAL_RULE_PLAN = rules.get_rule_based_plan
    _ORIGINAL_INLINE_PLAN = LeftBrain._rule_based_plan
    _ORIGINAL_INLINE_CONTAINS = LeftBrain._contains_any
    _ORIGINAL_M42_CLONES = clones
    rules._detect_relationship_intent = relationship_intent_with_question_evidence_p4
    for clone in clones:
        clone.__globals__["_detect_relationship_intent"] = relationship_intent_with_question_evidence_p4
    m42._BASELINE_RULE = _with_full_turn(clones[0])
    m42._GATED_RULE = _with_full_turn(clones[1])
    rules.get_rule_based_plan = _with_full_turn(_ORIGINAL_RULE_PLAN)
    LeftBrain._contains_any = _inline_contains_with_question_evidence
    LeftBrain._rule_based_plan = _inline_plan_with_full_turn
    _INSTALLED = True
    return True


def question_evidence_preflight_p4():
    """No-model route checks used by the isolated product launcher."""
    from uruha_brain_mac import LeftBrain

    psyche = {"mood": 0, "trust": 50}

    def intent(plan):
        return (plan or {}).get("intent")

    installed = bool(
        _INSTALLED
        and rules._detect_relationship_intent is relationship_intent_with_question_evidence_p4
        and LeftBrain._contains_any is _inline_contains_with_question_evidence
        and LeftBrain._rule_based_plan is _inline_plan_with_full_turn
        and all(getattr(clone, "_p4_question_full_turn", False) for clone in (m42._BASELINE_RULE, m42._GATED_RULE))
        and all(clone.__wrapped__.__globals__.get("_detect_relationship_intent") is relationship_intent_with_question_evidence_p4 for clone in (m42._BASELINE_RULE, m42._GATED_RULE))
    )
    token = _FULL_TURN.set("私は紅茶が好き。好き？")
    try:
        scoped_rejected = relationship_intent_with_question_evidence_p4("好き？") != "ask_like_me"
    finally:
        _FULL_TURN.reset(token)
    full_turn_context = bool(scoped_rejected and _FULL_TURN.get() is None)

    mixed = "私は紅茶が好き。好き？"
    before, after, trace, _ = m42.evaluate_relationship_route_m42(mixed, level="rule")
    positive_before, positive_after, positive_trace, _ = m42.evaluate_relationship_route_m42("好き？", level="rule")
    m42_clone_symmetry = bool(
        intent(before) != "ask_like_me" and intent(after) != "ask_like_me"
        and intent(positive_before) == intent(positive_after) == "ask_like_me"
        and trace["changed"] is False and positive_trace["changed"] is False
    )

    extracted_route = bool(
        intent(rules.get_rule_based_plan("好き？", [], psyche)) == "ask_like_me"
        and intent(rules.get_rule_based_plan("ねえ、好き?", [], psyche)) == "ask_like_me"
        and intent(rules.get_rule_based_plan("紅茶、好き？", [], psyche)) != "ask_like_me"
        and intent(rules.get_rule_based_plan(mixed, [], psyche)) != "ask_like_me"
    )

    left = LeftBrain.__new__(LeftBrain)
    inline_keywords = ("喜歡我", "好き？", "好き?", "うちのこと好き", "like me")
    inline_fallback = bool(
        _inline_contains_with_question_evidence(left, "好き？", inline_keywords)
        and _inline_contains_with_question_evidence(left, "ねえ、好き?", inline_keywords)
        and not _inline_contains_with_question_evidence(left, "紅茶、好き？", inline_keywords)
        and not _inline_contains_with_question_evidence(left, mixed, inline_keywords)
        and _inline_contains_with_question_evidence(left, "うちのこと好き？", inline_keywords)
    )
    contract = {
        "installed": installed,
        "full_turn_context": full_turn_context,
        "m42_clone_symmetry": m42_clone_symmetry,
        "extracted_route": extracted_route,
        "inline_fallback": inline_fallback,
    }
    if not all(contract.values()):
        raise RuntimeError(f"P4 question evidence preflight failed: {contract}")
    return contract


__all__ = [
    "bare_question_authorized_p4",
    "relationship_intent_with_question_evidence_p4",
    "install_relationship_question_evidence_p4",
    "question_evidence_preflight_p4",
]
