"""Pure, conservative source-event coverage check for existing P4 compact cores.

This module does not generate, revise, score, or select a plan.  Its only
positive claim is that an original candidate core literally preserves the
object/action relation in one supported current-User Japanese event sentence.
The return value contains digests and fixed reason codes, never source spans.
"""

from __future__ import annotations

import hashlib
import re

from uruha_direct_reply_act_m29_priority_p4 import classify_direct_reply_act_p4
from uruha_direct_reply_act_planner_handoff_p4 import SCHEMA as HANDOFF_SCHEMA


SCHEMA = "uruha_source_event_core_utility_p4_v1"

_LABELS = ("default", "softer", "sharper")
_SCENES = frozenset({"casual", "support"})
_MODES = frozenset({"direct_answer", "direct_answer_with_hedge"})
_JP_SPAN = re.compile(r"[\u3040-\u30ff\u3400-\u9fff々ー]+\Z")
_KANA = re.compile(r"[\u3040-\u30ff]")
_HIRAGANA = re.compile(r"[\u3040-\u309f]")
_NESTED_ACTOR_PARTICLE = re.compile(r"[がはもとに]")
_COMPLETED_PREDICATE = re.compile(r"[ただ]\Z")
_RELATIVE_CLAUSE_BEFORE_NOUN = re.compile(r"[うくすつぬむるぐぶい][\u3400-\u9fff々]")
_NOMINAL_COPULA = re.compile(r"(?:でした|であった|だった|なんだ)")
_QUOTE = re.compile(r"[「」『』“”\"'〈〉《》‘’`]")
_NEGATION = re.compile(
    r"(?:じゃない|じゃなく|ではない|ではなく|わけじゃない|"
    r"なかった|ない|なく|なければ|ません|ぬ|ず|否定|してない)"
)
_CLAUSE_BREAK = re.compile(r"[。！？!?、，,;；\n]")
_ACTOR_BEFORE = re.compile(r"(?:は|が|も|と|によって|による)")
_ACTOR_AFTER = re.compile(r"(?:のは|のが|のも|のを|のは誰|のは人)")
_REPORT = re.compile(r"(?:と言った|って言った|と言って|って言って|らしい|そうだ)")
_INTERROGATIVE = re.compile(r"[？?]|(?:のか|かな|かも)(?:[。！？!?]|\Z)")
_SAFE_EVENT_SUFFIX = re.compile(r"(?:んだね|んだよ|んだ|じゃん|ね|よ|な|の)?[。！!]*\Z")
_SAFE_EVALUATION = re.compile(
    r"(?:いいね|いいじゃん|すごい|すごいね|よかったね|やるじゃん|"
    r"頑張ったね|頑張ったな|えらいね|おめでとう)[。！!]*\Z"
)


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _coverage_rows(plans: object, reason: str) -> list[dict]:
    """Expose bounded original positions and core hashes even on a veto."""
    if not isinstance(plans, list) or len(plans) != 3:
        return []
    return [
        {
            "original_index": index,
            "core_sha256": _sha(plan["core_message_jp"])
            if isinstance(plan, dict) and isinstance(plan.get("core_message_jp"), str)
            else None,
            "grounded": False,
            "reason": reason,
        }
        for index, plan in enumerate(plans)
    ]


def _valid_handoff(source: str, handoff: object, expected: dict) -> bool:
    if not isinstance(handoff, dict) or expected["status"] != "direct":
        return False
    return (
        handoff.get("schema") == HANDOFF_SCHEMA
        and handoff.get("requested_act") == expected["requested_act"]
        and handoff.get("requested_act") in {"brief_care", "brief_encouragement"}
        and handoff.get("input_sha256") == _sha(source)
        and handoff.get("cue_sha256") == expected["cue_sha256"]
        and handoff.get("cue_span") == expected["cue_span"]
        and handoff.get("source_kind") == "current_user_direct_request"
        and handoff.get("m29_status") == "direct_reply_act_precedes_literal_projection_p4"
        and handoff.get("m33_status") == "not_applicable"
        and handoff.get("raw_dialogue_persisted") is False
        and handoff.get("private_state_truth_claimed") is False
    )


def _source_event(source: str, cue_start: int) -> tuple[str, str, str] | None:
    # The cue must follow exactly one completed sentence.  Do not search later
    # sentences, infer a missing subject, or parse translated event claims.
    sentence = source[:cue_start]
    if sentence.count("。") != 1 or not sentence.endswith("。"):
        return None
    body = sentence[:-1]
    if body.startswith("初めて"):
        body = body[len("初めて"):]
    if not body.startswith("自分で"):
        return None
    body = body[len("自分で"):]
    if body.count("を") != 1:
        return None
    obj, action = body.split("を")
    if (
        not obj or not action
        or not _JP_SPAN.fullmatch(obj)
        or not _JP_SPAN.fullmatch(action)
        # Han-only objects cannot distinguish Japanese from Chinese here.
        or not _KANA.search(obj)
        or not _HIRAGANA.search(action)
        or _NESTED_ACTOR_PARTICLE.search(obj)
        or _NESTED_ACTOR_PARTICLE.search(action)
        or not _COMPLETED_PREDICATE.search(action)
        # A present-form relative clause followed by a noun/copula can
        # describe someone else's act ("磨く兄だ"), not the User's act.
        or _RELATIVE_CLAUSE_BEFORE_NOUN.search(action)
        or _NOMINAL_COPULA.search(action)
        # A second completed predicate inside the putative action can make
        # the first verb a relative clause modifying another actor.
        or re.search(r"[ただ]", action[:-1])
        or _QUOTE.search(sentence)
        or _NEGATION.search(sentence)
    ):
        return None
    return sentence, obj, action


def _candidate_reason(core: str, obj: str, action: str) -> str:
    if _QUOTE.search(core):
        return "quoted_core"
    if _NEGATION.search(core):
        return "negated_core"
    if _INTERROGATIVE.search(core):
        return "interrogative_core"
    if _REPORT.search(core):
        return "reported_core"
    event = obj + "を" + action
    start = core.find(event)
    if start < 0:
        return "event_relation_unverified"
    if core[start + len(event):].startswith("って"):
        return "reported_core"
    # A matching phrase inside another actor's clause is not a User event.
    # Prefer false negatives on topic or companion particles to misattribution.
    clause_start = 0
    clause_end = len(core)
    for break_match in _CLAUSE_BREAK.finditer(core):
        if break_match.end() <= start:
            clause_start = break_match.end()
        elif break_match.start() >= start + len(event):
            clause_end = break_match.start()
            break
    prefix = core[clause_start:start]
    suffix = core[start + len(event):clause_end]
    tail = core[start + len(event):]
    if any(mark in tail for mark in ("、", "，", ",")):
        # A comma starts a fresh clause. Only a small, actor-free evaluative
        # continuation can be certified without a full Japanese parser.
        parts = re.split(r"[、，,]", tail)
        if (
            len(parts) != 2
            or not _SAFE_EVENT_SUFFIX.fullmatch(parts[0])
            or not _SAFE_EVALUATION.fullmatch(parts[1])
        ):
            return "actor_unverified"
    elif not _SAFE_EVENT_SUFFIX.fullmatch(tail):
        return "actor_unverified"
    if (
        clause_start
        or _ACTOR_BEFORE.search(prefix)
        or _ACTOR_AFTER.search(suffix)
        or "。" in tail[:-1]
    ):
        return "actor_unverified"
    return "grounded"


def assess_candidate_coverage_p4(source: str, handoff: dict | None, plans: list[dict]) -> dict:
    """Return a raw-free coverage receipt for three original model candidates.

    ``eligible`` means the same-turn M29/M33 handoff, finite source grammar,
    and original three-candidate shape all validate.  It does *not* mean that
    any candidate is grounded, selected, or preserved by the final surface.
    """
    result = {
        "schema": SCHEMA,
        "status": "unverifiable",
        "eligible": False,
        "reason": "invalid_source",
        "input_sha256": _sha(source) if isinstance(source, str) else None,
        "event_sha256": None,
        "object_sha256": None,
        "action_sha256": None,
        "candidate_coverage": _coverage_rows(plans, "not_eligible"),
    }
    if not isinstance(source, str):
        return result
    expected = classify_direct_reply_act_p4(source)
    if not _valid_handoff(source, handoff, expected):
        result["reason"] = "invalid_handoff"
        return result
    event = _source_event(source, expected["cue_span"][0])
    if event is None:
        result["reason"] = "unsupported_source_event"
        return result
    sentence, obj, action = event
    result.update(
        event_sha256=_sha(sentence),
        object_sha256=_sha(obj),
        action_sha256=_sha(action),
    )
    if not (
        isinstance(plans, list)
        and len(plans) == 3
        and all(
            isinstance(plan, dict)
            and plan.get("candidate_label") == _LABELS[index]
            and isinstance(plan.get("core_message_jp"), str)
            and bool(plan["core_message_jp"].strip())
            and len(plan["core_message_jp"]) <= 32
            for index, plan in enumerate(plans)
        )
        and len({plan["core_message_jp"].strip() for plan in plans}) == 3
    ):
        result["reason"] = "invalid_candidate_set"
        result["candidate_coverage"] = _coverage_rows(plans, "invalid_candidate_set")
        return result
    result["eligible"] = True
    rows = []
    for index, plan in enumerate(plans):
        if plan.get("scene") not in _SCENES:
            reason = "unsupported_scene"
        elif plan.get("response_mode") not in _MODES:
            reason = "unsupported_response_mode"
        else:
            reason = _candidate_reason(plan["core_message_jp"], obj, action)
        rows.append(
            {
                "original_index": index,
                "core_sha256": _sha(plan["core_message_jp"]),
                "grounded": reason == "grounded",
                "reason": reason,
            }
        )
    result["candidate_coverage"] = rows
    result["status"] = "grounded_candidate_available" if any(row["grounded"] for row in rows) else "no_grounded_candidate"
    result["reason"] = result["status"]
    return result


__all__ = ["SCHEMA", "assess_candidate_coverage_p4"]
