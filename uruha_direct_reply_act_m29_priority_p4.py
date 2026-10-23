"""Opt-in, source-bound priority for an explicit current-turn reply act.

This changes only M29 admission.  It does not write a reply, infer a private
need, or claim that the full planner will necessarily be selected.  The latter
is a separate zero-model and product acceptance condition.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import re
import unicodedata

import uruha_adaptive_person_model as adaptive
import uruha_source_semantic_atoms_m33 as atoms_m33


LABEL = "direct_reply_act_m29_priority_p4"
SCHEMA = "uruha_direct_reply_act_m29_priority_p4_v1"
_DIRECT = re.compile(r"(?:今は|今日は|いまは)?一言だけ(?P<light>軽く)?(?P<verb>労って|励まして)(?:[。！!])?$")
_CUE = re.compile(r"一言だけ|労って|励まして")
_QUOTE = re.compile(r"[「」『』“”\"'〈〉《》]")
_NEGATION = re.compile(r"(?:じゃない|ではない|わけじゃない|いらない|要らない|しないで|やめて|不要|なしで|違う)")
_REPORTED = re.compile(
    r"(?:メモ\s*[:：]|(?:次の文|この文|例文|引用|翻訳|訳して|翻訳して)|"
    # Speaker nouns cannot be enumerated: family, roles, and names may all
    # introduce reported speech.  A preceding attribution makes the source
    # of a later imperative uncertain, so the direct-act gate fails closed.
    r"[^。！？!?\n]{1,48}(?:"
    r"(?:からの|の)(?:依頼|伝言|指示)"
    r"|(?:が|は)[^。！？!?\n]{0,12}(?:言った|話した|書いた|頼んだ|伝えた)"
    r"|(?:から|に)[^。！？!?\n]{0,12}(?:頼まれた|伝えられた|指示された)"
    r"|(?:と|って)(?:言った|書いた)"
    r")"
    r"(?:[。！？!?：:]|$))"
)
# This admission gate cannot establish who owns an unquoted imperative after
# a prior speech, report, or request.  Prefer a false negative (ordinary
# planner still sees the User text) to a false current-User certificate.  This
# is a finite Japanese cue policy, not universal reported-speech parsing.
_SOURCE_AMBIGUOUS_PREFIX = re.compile(
    r"言|話|聞|伝|頼|書|お願い|依頼|指示|要望|要求|引用|メモ|リクエスト"
)
_PROTECTED = re.compile(
    r"(?:パスワード|パスコード|暗証番号|認証コード|秘密鍵|個人情報|住所|電話番号|口座|"
    r"自殺|自傷|死にたい|死のう|飛び降り|飛び込む|首を吊|人を殴|人を刺|人を殺|殺して|"
    r"爆弾|武器|違法|ハッキング)"
)
_INSTALLED = False
_PRIOR_M29 = None


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def classify_direct_reply_act_p4(source: str) -> dict:
    """Return a raw-free certificate; unknown/conflicting forms fail closed."""
    text = str(source or "")
    digest = _sha(text)
    certificate = {
        "schema": SCHEMA,
        "status": "narrative",
        "requested_act": None,
        "source_kind": "current_user_text",
        "input_sha256": digest,
        "cue_span": None,
        "cue_sha256": None,
        "model_call_added": False,
        "raw_dialogue_persisted": False,
        "private_state_truth_claimed": False,
        "claim_boundary": "explicit current-turn reply action only; no private desired-response inference",
    }
    if not text or len(text) > 240 or text != text.strip() or any(
        unicodedata.category(ch) in {"Cc", "Cf", "Cs", "Zl", "Zp"} for ch in text
    ):
        certificate["status"] = "ambiguous"
        return certificate
    if _PROTECTED.search(text):
        certificate["status"] = "protected"
        return certificate
    if _QUOTE.search(text):
        certificate["status"] = "quoted"
        return certificate
    if _REPORTED.search(text):
        certificate["status"] = "ambiguous"
        certificate["source_kind"] = "reported_or_non_user_text"
        return certificate
    if _NEGATION.search(text):
        certificate["status"] = "negated"
        return certificate
    matched = _DIRECT.search(text)
    cues = list(_CUE.finditer(text))
    if matched is None:
        certificate["status"] = "ambiguous" if cues else "narrative"
        return certificate
    if _SOURCE_AMBIGUOUS_PREFIX.search(text[:matched.start()]):
        certificate["status"] = "ambiguous"
        certificate["source_kind"] = "reported_or_non_user_text"
        return certificate
    # A unique direct final clause, with no competing earlier command.  The
    # rest of the turn may describe a user event but does not license emotion.
    if len(cues) != 2 or [cue.group(0) for cue in cues] != ["一言だけ", matched.group("verb")]:
        certificate["status"] = "ambiguous"
        return certificate
    start, end = matched.span()
    if start and text[start - 1] not in "、。！？!? ":
        certificate["status"] = "ambiguous"
        return certificate
    certificate.update(
        {
            "status": "direct",
            "requested_act": "brief_care" if matched.group("verb") == "労って" else "brief_encouragement",
            "source_kind": "current_user_direct_request",
            "cue_span": [start, end],
            "cue_sha256": _sha(text[start:end]),
        }
    )
    return certificate


def literal_topic_projection_with_direct_reply_priority_p4(
    user_input,
    adaptive_feedback,
    pragmatic_understanding,
    feedback_topic_transition_m28=None,
):
    """Veto only an original M29 candidate with an exact direct-act source."""
    candidate = _PRIOR_M29(
        user_input,
        adaptive_feedback,
        pragmatic_understanding,
        feedback_topic_transition_m28,
    )
    if not isinstance(candidate, dict):
        return candidate
    certificate = classify_direct_reply_act_p4(user_input)
    if not (
        certificate["status"] == "direct"
        and candidate.get("schema") == adaptive.LITERAL_TOPIC_PROJECTION_SCHEMA_M29
        and candidate.get("projection_required") is True
        and candidate.get("surface_authority") is False
        and candidate.get("input_digest") == certificate["input_sha256"][:16]
        and not (feedback_topic_transition_m28 or {}).get("surface_authority")
        and not candidate.get("source_statement_priority_p4")
        and not candidate.get("source_bound_preference_priority_p4")
        and not candidate.get("required_observable_act")
    ):
        return candidate
    # Do not hide an available M33 source-atom path merely to make M29 false.
    original_atoms = atoms_m33.extract_source_semantic_atoms_m33(user_input, candidate)
    if not isinstance(original_atoms, dict) or original_atoms.get("status") != "source_pattern_unavailable":
        return candidate
    updated = deepcopy(candidate)
    updated.update(
        {
            "status": "direct_reply_act_precedes_literal_projection_p4",
            "reason": "exact_current_user_reply_action_has_priority_over_general_literal_projection",
            "projection_required": False,
            LABEL: {
                **certificate,
                "status": "admitted_direct_reply_act",
                "original_m29_status": candidate.get("status"),
                "original_projection_required": True,
                "original_m33_status": original_atoms["status"],
                "m29_projection_after": False,
                "planner_handoff": "pending_actual_route_verification",
            },
        }
    )
    return updated


def install_direct_reply_act_m29_priority_p4() -> bool:
    global _INSTALLED, _PRIOR_M29
    if _INSTALLED:
        if adaptive.build_literal_topic_projection_candidate_m29 is not literal_topic_projection_with_direct_reply_priority_p4:
            raise RuntimeError("direct_reply_act_m29_priority_overlay_overwritten")
        return False
    _PRIOR_M29 = adaptive.build_literal_topic_projection_candidate_m29
    adaptive.build_literal_topic_projection_candidate_m29 = (
        literal_topic_projection_with_direct_reply_priority_p4
    )
    _INSTALLED = True
    return True


__all__ = [
    "LABEL", "SCHEMA", "classify_direct_reply_act_p4",
    "literal_topic_projection_with_direct_reply_priority_p4",
    "install_direct_reply_act_m29_priority_p4",
]
