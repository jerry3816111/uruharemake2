"""M38 target-guarded multilingual feedback linkage.

The module classifies only an observable relation between the current turn and
an immediately pending response-policy prediction.  It does not infer private
intent and it never persists raw dialogue.  Runtime integration is an adapter
around the frozen pre-M38 ``observe_next_turn`` implementation so M37 formal
artifacts remain untouched.
"""

from __future__ import annotations

import hashlib
import re
from copy import deepcopy

import uruha_adaptive_person_model as uapm


SCHEMA_M38 = "uruha_target_guarded_multiscript_feedback_linkage_m38"
VALID_POLICIES = {
    "listen_presence",
    "solve_regulation",
    "share_arousal",
    "playful_tease",
}


def _digest(text):
    return hashlib.sha256(str(text or "").encode("utf-8")).hexdigest()[:16]


def _normalise(text):
    return re.sub(r"\s+", " ", str(text or "").strip()).lower()


def _matches(text, patterns):
    return [rule_id for rule_id, pattern in patterns if re.search(pattern, text, re.I)]


CORRECTION_REFERENCE_PATTERNS = (
    ("zh:not_right", r"(?:^|[。！？!?；;])\s*不對(?:啦|啊|呀)?(?:[，,。！？!?；;]|$)"),
    ("zh:leading_not", r"^\s*不是[，,。！？!?；;]"),
    ("zh:not_this_response", r"不是(?:這|这种|這種)(?:個意思|意思|接法|回法|回答)"),
    ("zh:not_want_response", r"不是要[^。！？!?；;]{0,12}(?:吐槽|建議|建议|方法|陪|聽|听)"),
    ("zh:misread", r"(?:你)?(?:理解反了|理解錯了|理解错了|搞錯了|搞错了|讀反了|读反了)"),
    ("en:not_meant", r"(?:that(?:'s| is) not what i meant|not the (?:response|way) i meant)"),
    ("en:leading_no", r"^\s*no\b[\s,;:!\-—–]*"),
    ("en:misread", r"(?:you (?:read|got) that wrong|you misunderstood)"),
    ("ja:leading_chigau", r"^\s*(?:違う|いや)[\s、,。！!\-—–]*"),
    ("ja:not_that", r"(?:そうじゃなくて|そういう[^。！？!?]{0,18}じゃない|読み違えて|勘違いしてる)"),
)

NEGATION_PATTERNS = (
    ("zh:negation", r"(?:不是|沒有|没有|不要|別|别|不會|不会)"),
    ("en:negation", r"\b(?:no|not|don't|doesn't|didn't|cannot|can't)\b"),
    ("ja:negation", r"(?:じゃなくて|じゃない|ない|いらない|違う)"),
)

POLICY_PATTERNS = {
    "listen_presence": (
        ("zh:finish", r"(?:先)?讓我[^。！？!?]{0,16}(?:講完|说完|說完)"),
        ("zh:listen_until_finish", r"(?:先)?(?:聽|听)我[^。！？!?]{0,16}(?:講完|说完|說完)"),
        ("zh:listen", r"(?:先)?(?:聽|听)我(?:說|说|講|讲)"),
        ("en:finish", r"(?:let me finish|hear me out|listen until i finish)"),
        ("en:listen", r"\b(?:just listen|listen to me)\b"),
        ("ja:finish", r"(?:最後まで|話が終わるまで)聞いて"),
        ("ja:listen", r"(?:今は|まず|とりあえず)?[^。！？!?]{0,8}聞いて"),
    ),
    "solve_regulation": (
        ("zh:first_step", r"(?:第一步|第一個步驟|第一个步骤|現在能做的(?:一步|方法)|现在能做的(?:一步|方法))"),
        ("zh:direct_action", r"(?:直接)?告訴我[^。！？!?]{0,18}(?:做什麼|怎么做|怎麼做)"),
        ("zh:wants_method", r"(?:真的|其實|其实)?想要[^。！？!?]{0,8}(?:方法|步驟|步骤)"),
        ("en:one_move", r"(?:one concrete (?:move|step)|one practical step|one step i can|what i can do right now)"),
        ("ja:one_move", r"(?:今できる一手|今できる一つ|一手を先に|一つだけ方法)"),
    ),
    "share_arousal": (
        ("zh:stay_with", r"(?:陪我|跟我一起|和我一起)[^。！？!?]{0,18}(?:緊張|紧张|等|撐|撑|待著|待着|慌)"),
        ("en:stay_with", r"(?:stay in this with me|stay here with me|wait(?:[^。!?]{0,18})? with me|be here with me)"),
        ("ja:stay_with", r"(?:一緒に[^。！？!?]{0,18}(?:付き合って|待って|そわそわして)|そばにいて)"),
    ),
    "playful_tease": (
        ("zh:tease", r"(?:吐槽我|虧我|亏我|笑我|調侃我|调侃我)"),
        ("en:tease", r"(?:tease me|roast me|make fun of me)"),
        ("ja:tease", r"(?:ツッコんで|ツッコミ入れて|いじって|からかって)"),
    ),
}

POLICY_NEGATION_PATTERNS = {
    "listen_presence": (
        r"(?:不要|別|别)(?:再)?(?:聽|听)",
        r"(?:don't|do not) listen",
        r"聞かないで",
    ),
    "solve_regulation": (
        r"(?:不要|別|别)[^。！？!?]{0,12}(?:分析|方法|建議|建议|步驟|步骤)",
        r"不是要[^。！？!?]{0,6}(?:方法|建議|建议|步驟|步骤)",
        r"(?:don't|do not|instead of)[^。!?]{0,14}(?:troubleshoot|fix|advise|give advice)",
        r"(?:方法|アドバイス|解決策)[^。！？!?]{0,6}(?:はいらない|いらない)",
    ),
    "share_arousal": (
        r"(?:不要|別|别)[^。！？!?]{0,8}(?:陪|一起)",
        r"(?:don't|do not) stay",
        r"(?:一緒|そば)[^。！？!?]{0,8}(?:いらない|いなくていい)",
    ),
    "playful_tease": (
        r"(?:不是要|不要|別|别)[^。！？!?]{0,8}(?:逗|吐槽|笑|虧|亏)",
        r"(?:don't|do not)[^。!?]{0,8}(?:tease|roast|make fun)",
        r"(?:そういう)?(?:ツッコミ|いじり|からかい)[^。！？!?]{0,8}(?:じゃない|いらない)",
    ),
}


def _policy_candidates(text):
    candidates = {}
    for policy_id, patterns in POLICY_PATTERNS.items():
        matched = _matches(text, patterns)
        if not matched:
            continue
        if any(re.search(pattern, text, re.I) for pattern in POLICY_NEGATION_PATTERNS[policy_id]):
            continue
        candidates[policy_id] = matched
    return candidates


def classify_target_guarded_feedback_m38(user_input, pending_prediction=None):
    """Classify whether a turn observably revises one pending response policy."""

    text = _normalise(user_input)
    pending = deepcopy(pending_prediction or {})
    previous_policy = str(pending.get("policy_id") or "")
    previous_prediction_id = str(pending.get("prediction_id") or "")
    correction_rule_ids = _matches(text, CORRECTION_REFERENCE_PATTERNS)
    negation_rule_ids = _matches(text, NEGATION_PATTERNS)
    policy_candidates = _policy_candidates(text)
    replacement_policies = sorted(policy_candidates)
    correction_reference = bool(correction_rule_ids)
    pending_available = bool(previous_prediction_id and previous_policy)

    if not pending_available:
        status = "fail_closed_no_pending_prediction"
        outcome = "uncertain"
        linked = False
        replacement = None
    elif not correction_reference:
        status = (
            "ordinary_negation_not_feedback"
            if negation_rule_ids
            else "no_observable_correction_reference"
        )
        outcome = "uncertain"
        linked = False
        replacement = None
    elif len(replacement_policies) == 0:
        status = "fail_closed_no_replacement_target"
        outcome = "uncertain"
        linked = False
        replacement = None
    elif len(replacement_policies) > 1:
        status = "fail_closed_multiple_replacement_targets"
        outcome = "uncertain"
        linked = False
        replacement = None
    elif replacement_policies[0] == previous_policy:
        status = "fail_closed_target_matches_pending_policy"
        outcome = "uncertain"
        linked = False
        replacement = None
    else:
        status = "linked_unique_replacement_contradiction"
        outcome = "contradicted"
        linked = True
        replacement = replacement_policies[0]

    return {
        "schema": SCHEMA_M38,
        "status": status,
        "outcome": outcome,
        "feedback_linked_to_previous_prediction": linked,
        "previous_prediction_id": previous_prediction_id or None,
        "previous_policy_id": previous_policy or None,
        "replacement_policy_id": replacement,
        "pending_prediction_available": pending_available,
        "correction_reference_detected": correction_reference,
        "correction_rule_ids": correction_rule_ids,
        "negation_detected": bool(negation_rule_ids),
        "negation_rule_ids": negation_rule_ids,
        "replacement_candidates": replacement_policies,
        "replacement_evidence_rule_ids": {
            policy_id: rule_ids for policy_id, rule_ids in policy_candidates.items()
        },
        "evidence_digest": _digest(user_input),
        "raw_dialogue_persisted": False,
        "private_state_truth_claimed": False,
        "claim_scope": "observable_feedback_linkage_not_private_intent_truth",
    }


CANONICAL_FEEDBACK_BY_POLICY = {
    "listen_presence": "No. I wanted you to let me finish and listen without advice.",
    "solve_regulation": "No. I wanted you to tell me what I can do right now.",
    "share_arousal": "No. I wanted you to stay here with me while we wait.",
    "playful_tease": "No. I wanted you to tease me.",
}

POLICY_ATOM_TARGETS_M38 = {
    "listen_presence": {
        "listening_request": (0.98, 0.99),
        "solution_request": (0.03, 0.98),
    },
    "solve_regulation": {"solution_request": (0.98, 0.99)},
    "share_arousal": {"companionship_request": (0.99, 0.99)},
    "playful_tease": {
        "humor_invitation": (0.98, 0.99),
        "relationship_familiarity": (0.90, 0.90),
        "solution_request": (0.04, 0.94),
    },
}

POLICY_ATOM_REVOCATIONS_M38 = {
    "listen_presence": {"listening_request": (0.03, 0.94)},
    "solve_regulation": {"solution_request": (0.03, 0.94)},
    "share_arousal": {"companionship_request": (0.03, 0.94)},
    "playful_tease": {"humor_invitation": (0.03, 0.94)},
}


def _replace_digest(value, old_digest, new_digest):
    if isinstance(value, dict):
        return {
            key: _replace_digest(item, old_digest, new_digest)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_replace_digest(item, old_digest, new_digest) for item in value]
    if value == old_digest:
        return new_digest
    return value


def _persist_replacement_policy_m38(state, pending, replacement_policy, evidence_digest, turn_index):
    """Persist only typed response-form atoms to the pending causal scopes."""

    state = deepcopy(state or {})
    pending = deepcopy(pending or {})
    scope = deepcopy(pending.get("context_scope") or {})
    primary_scope_id = str(scope.get("scope_id") or "")
    scope_ids = list(
        dict.fromkeys(
            [
                primary_scope_id,
                *[
                    str(scope_id)
                    for scope_id in (pending.get("causal_scope_ids") or [])
                    if str(scope_id).strip()
                ],
            ]
        )
    )
    scope_ids = [scope_id for scope_id in scope_ids if scope_id]
    revision = int(state.get("revision_count") or 0)
    atom_targets = deepcopy(POLICY_ATOM_TARGETS_M38.get(replacement_policy) or {})
    previous_policy = str(pending.get("policy_id") or "")
    for atom, target in (POLICY_ATOM_REVOCATIONS_M38.get(previous_policy) or {}).items():
        # A replacement can explicitly retain an atom (for example, listening
        # while rejecting advice).  In that case the replacement has authority
        # and the revoked policy must not overwrite it.
        atom_targets.setdefault(atom, target)
    dimension_targets = uapm.POLICY_DIMENSION_PROFILES.get(replacement_policy) or {}
    atom_changes = []
    dimension_changes = []
    state.setdefault("scoped_atoms", {})
    state.setdefault("learned_atoms", {})
    for scope_id in scope_ids:
        record = state["scoped_atoms"].setdefault(
            scope_id,
            {
                "scope": deepcopy(scope),
                "atoms": {},
                "dimensions": {},
                "last_updated_revision": revision,
                "ttl_revisions": uapm.DEFAULT_SCOPE_TTL_REVISIONS,
            },
        )
        record.setdefault("atoms", {})
        record.setdefault("dimensions", {})
        for atom, (value, confidence) in atom_targets.items():
            before = deepcopy(record["atoms"].get(atom))
            after = {
                "value": value,
                "confidence": confidence,
                "source_kind": "m38_explicit_correction_unique_replacement",
                "evidence_digest": evidence_digest,
                "updated_turn": int(turn_index),
                "updated_revision": revision,
                "contradiction_count": int((before or {}).get("contradiction_count") or 0),
            }
            if before and abs(float(before.get("value") or 0.0) - value) >= 0.45:
                after["contradiction_count"] += 1
            record["atoms"][atom] = after
            state["learned_atoms"][atom] = deepcopy(after)
            atom_changes.append(
                {"scope_id": scope_id, "atom": atom, "before": before, "after": deepcopy(after)}
            )
        for dimension, value in dimension_targets.items():
            if dimension not in uapm.RESPONSE_DIMENSIONS:
                continue
            before = deepcopy(record["dimensions"].get(dimension))
            after = {
                "value": float(value),
                "confidence": 0.94,
                "source_kind": "m38_explicit_correction_unique_replacement",
                "evidence_digest": evidence_digest,
                "updated_turn": int(turn_index),
                "updated_revision": revision,
                "contradiction_count": int((before or {}).get("contradiction_count") or 0),
            }
            if before and abs(float(before.get("value") or 0.0) - float(value)) >= 0.45:
                after["contradiction_count"] += 1
            record["dimensions"][dimension] = after
            dimension_changes.append(
                {
                    "scope_id": scope_id,
                    "dimension": dimension,
                    "before": before,
                    "after": deepcopy(after),
                }
            )
        record["scope"] = deepcopy(scope)
        record["last_updated_revision"] = revision
    return state, atom_changes, dimension_changes


def adapt_observe_next_turn_m38(base_observe, model, user_input, turn_index=0):
    """Run the frozen observer through an M38 target-guarded feedback adapter."""

    pending = deepcopy((model or {}).get("pending_prediction") or {})
    linkage = classify_target_guarded_feedback_m38(user_input, pending)
    adapted_input = user_input
    adapter_applied = False

    if pending and linkage["outcome"] == "contradicted":
        adapted_input = CANONICAL_FEEDBACK_BY_POLICY[linkage["replacement_policy_id"]]
        adapter_applied = True
    elif pending and linkage["outcome"] == "uncertain" and (
        linkage["correction_reference_detected"] or linkage["negation_detected"]
    ):
        # The observer only needs an outcome signal.  Current-turn semantics
        # continue through the brain on the original text; this neutral token
        # prevents a bare multilingual negation from mutating prior policy.
        adapted_input = "m38_unlinked_current_turn"
        adapter_applied = True

    state, feedback = base_observe(model, adapted_input, turn_index=turn_index)
    original_digest = _digest(user_input)
    adapted_digest = _digest(adapted_input)
    if adapted_input != user_input:
        state = _replace_digest(state, adapted_digest, original_digest)
        feedback = _replace_digest(feedback, adapted_digest, original_digest)

    feedback = deepcopy(feedback or {})
    feedback["target_guarded_feedback_m38"] = linkage
    feedback["m38_adapter_applied"] = adapter_applied
    if pending and linkage["outcome"] == "contradicted":
        state, atom_changes_m38, dimension_changes_m38 = _persist_replacement_policy_m38(
            state,
            pending,
            linkage["replacement_policy_id"],
            original_digest,
            turn_index,
        )
        feedback.update(
            {
                "status": "contradicted",
                "reason": "m38_unique_target_correction_linked",
                "previous_prediction_id": linkage["previous_prediction_id"],
                "previous_policy_id": linkage["previous_policy_id"],
                "explicit_target_policy": linkage["replacement_policy_id"],
                "feedback_linked_to_previous_prediction": True,
                "feedback_linkage_reason": "m38_observable_correction_plus_unique_replacement",
                "m38_atom_changes": atom_changes_m38,
                "m38_dimension_changes": dimension_changes_m38,
            }
        )
        feedback["atom_changes"] = [
            *(feedback.get("atom_changes") or []),
            *atom_changes_m38,
        ]
        feedback["dimension_changes"] = [
            *(feedback.get("dimension_changes") or []),
            *dimension_changes_m38,
        ]
        primary_scope_id = str(((pending.get("context_scope") or {}).get("scope_id")) or "")
        secondary_scope_ids = [
            str(scope_id)
            for scope_id in (pending.get("causal_scope_ids") or [])
            if str(scope_id) and str(scope_id) != primary_scope_id
        ]
        if secondary_scope_ids:
            existing_repairs = list(feedback.get("causal_scope_repairs_m23") or [])
            for scope_id in secondary_scope_ids:
                existing_repairs.append(
                    {
                        "scope_id": scope_id,
                        "repaired_atoms": [
                            row for row in atom_changes_m38 if row.get("scope_id") == scope_id
                        ],
                        "repaired_dimensions": [
                            row for row in dimension_changes_m38 if row.get("scope_id") == scope_id
                        ],
                        "revoked_policy": linkage["previous_policy_id"],
                        "replacement_policy": linkage["replacement_policy_id"],
                        "source": "m38_target_guarded_causal_scope_repair",
                    }
                )
            feedback["causal_scope_repairs_m23"] = existing_repairs
    elif pending and adapter_applied:
        feedback.update(
            {
                "status": "uncertain",
                "reason": "m38_feedback_linkage_failed_closed",
                "previous_prediction_id": linkage["previous_prediction_id"],
                "previous_policy_id": linkage["previous_policy_id"],
                "explicit_target_policy": None,
                "feedback_linked_to_previous_prediction": False,
                "feedback_linkage_reason": linkage["status"],
            }
        )
    evidence = deepcopy(feedback.get("evidence") or {})
    evidence.update(
        {
            "source": "next_user_turn",
            "digest": original_digest,
            "raw_text_persisted": False,
        }
    )
    feedback["evidence"] = evidence
    feedback["raw_dialogue_persisted"] = False
    return state, feedback


ORIGINAL_OBSERVE_NEXT_TURN_M38 = None


def install_m38_feedback_linkage():
    """Install the adapter once for all UruhaBrain runtime entry points."""

    global ORIGINAL_OBSERVE_NEXT_TURN_M38
    current = uapm.observe_next_turn
    if getattr(current, "_uruha_m38_installed", False):
        return current
    ORIGINAL_OBSERVE_NEXT_TURN_M38 = current

    def wrapped(model, user_input, turn_index=0):
        return adapt_observe_next_turn_m38(
            ORIGINAL_OBSERVE_NEXT_TURN_M38,
            model,
            user_input,
            turn_index=turn_index,
        )

    wrapped._uruha_m38_installed = True
    wrapped._uruha_m38_original = current
    uapm.observe_next_turn = wrapped
    return wrapped


def original_observe_next_turn_m38():
    """Return the frozen pre-M38 observer after ensuring installation."""

    install_m38_feedback_linkage()
    return ORIGINAL_OBSERVE_NEXT_TURN_M38
