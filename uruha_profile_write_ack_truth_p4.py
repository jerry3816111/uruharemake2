"""Product-only authority for a visible user-profile write acknowledgement.

P4-H recognizes the request before the profile writer runs.  This overlay uses
the P4-I extraction and P4 owner admission *unchanged* to withhold P4-H's plan
and final promise when that writer will reject the source.  After writeback it
checks the actual outcome and the already-saved utterance/episode; it never
repairs only the returned reply after those records have been made.
"""

from __future__ import annotations

from contextvars import ContextVar
from copy import deepcopy
import datetime
import hashlib

import uruha_adaptive_person_model as adaptive_person
import uruha_explicit_preference_acknowledgement_p4 as p4h
import uruha_multilingual_current_preference_p4 as p4i
import uruha_profile_owner_admission_p4 as owner


LABEL = "profile_write_ack_truth_p4"
SCHEMA = "uruha_profile_write_ack_truth_p4_v1"
NON_COMMITMENT_REPLY = "ん、その話は聞いた。お前の好みとしては覚えない。"
MULTIPLE_VALUES_REPLY = "ん、好みが複数あるな。今のはどれか教えて。"
UNCLEAR_VALUE_REPLY = "ん、今の好みがはっきりしない。もう少し教えて。"
AMBIGUOUS_SCOPE_REPLY = "ん、前の好みが複数の種類に残ってる。どの種類を直すか教えて。"
_INSTALLED = False
_ORIGINAL_RULE_PLAN = None
_ORIGINAL_VISIBLE_GUARD = None
_ORIGINAL_QUERY = None
_ORIGINAL_RUN = None
_ORIGINAL_EMIT = None
_ORIGINAL_LEGACY_PROFILE_FALLBACK = None
_RUN_ACTIVE = ContextVar("p4_profile_write_ack_run_active", default=False)


class ProfileWriteAckIntegrityError(RuntimeError):
    """No successful UI reply may be delivered after a contract mismatch."""


def _digest(value):
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def _scope_state_eligibility(extraction, memory):
    """Mirror P4-I's default-general correction scope test, read-only."""
    expected_scope = extraction.get("scope")
    base = {
        "status": "not_required",
        "active_old_scope_count": None,
        "expected_scope_sha256": _digest(p4i._normalize(expected_scope)) if expected_scope else None,
        "raw_scope_persisted": False,
    }
    if extraction.get("act") != "correction" or extraction.get("scope_source") != "default_general":
        return base
    if memory is None or getattr(memory, "profile_col", None) is None:
        return {**base, "status": "unavailable", "expected_scope_sha256": None}
    try:
        reference_time = datetime.datetime.now().astimezone().isoformat(timespec="microseconds")
        before = p4i._current_preference_rows(memory.profile_col, reference_time=reference_time)
        old_value = p4i._normalize(extraction.get("previous_value"))
        old_matches = [
            row for row in before["active"]
            if old_value and p4i._normalize((row.get("metadata") or {}).get("value")) == old_value
        ]
        scopes = {
            str((row.get("metadata") or {}).get("preference_scope") or "")
            for row in old_matches
            if str((row.get("metadata") or {}).get("preference_scope") or "")
        }
    except Exception:
        return {**base, "status": "unavailable", "expected_scope_sha256": None}
    if len(scopes) > 1:
        return {
            **base,
            "status": "ambiguous",
            "active_old_scope_count": len(scopes),
            "expected_scope_sha256": None,
        }
    if len(scopes) == 1:
        expected_scope = next(iter(scopes))
    return {
        **base,
        "status": "unique" if scopes else "no_active_old_value",
        "active_old_scope_count": len(scopes),
        "expected_scope_sha256": _digest(p4i._normalize(expected_scope)),
    }


def legacy_profile_fallback_with_profile_write_ack_truth_p4(self, user_input):
    """Suppress only P4-I's state-blocked correction fallback to the legacy writer.

    The owner has already admitted the source, but that is not permission for a
    second, untyped write after P4-I refuses an ambiguous existing scope.
    Other selected and ordinary legacy paths retain their original writer.
    """
    text = str(user_input or "").strip()
    input_sha256 = _digest(text)
    self._last_profile_write_ack_legacy_fallback = None
    typed = getattr(self, "_last_multilingual_current_preference_p4", None)
    if (
        isinstance(typed, dict)
        and typed.get("input_sha256") == input_sha256
        and typed.get("status") == "ambiguous_extraction"
        and typed.get("reason") == "old_value_has_multiple_active_scopes"
    ):
        extraction = p4i.extract_explicit_current_preference_p4(text)
        if (
            extraction.get("input_sha256") != input_sha256
            or not extraction.get("selected")
            or extraction.get("act") != "correction"
        ):
            raise ProfileWriteAckIntegrityError(f"{LABEL}:correction_changed_before_legacy_fallback")
        state = _scope_state_eligibility(extraction, self)
        if (
            state.get("status") != "ambiguous"
            or state.get("active_old_scope_count") != typed.get("matching_active_old_scope_count")
        ):
            raise ProfileWriteAckIntegrityError(f"{LABEL}:scope_state_changed_before_legacy_fallback")
        episode_id = getattr(self, "_last_saved_episode_id", None)
        self._last_profile_write_ack_legacy_fallback = {
            "schema": SCHEMA,
            "input_sha256": input_sha256,
            "episode_id_sha256": _digest(episode_id) if episode_id else None,
            "active_old_scope_count": state["active_old_scope_count"],
            "reason": "old_value_has_multiple_active_scopes",
            "suppressed": True,
            "raw_dialogue_persisted": False,
        }
        return None
    return _ORIGINAL_LEGACY_PROFILE_FALLBACK(self, user_input)


def preflight_profile_write_ack_p4(user_input, *, memory=None):
    """Use the exact writer admission functions without retaining raw dialogue."""
    text = str(user_input or "").strip()
    contract = p4h.build_explicit_preference_memory_act_contract_p4(text)
    audit = {
        "schema": SCHEMA,
        "selected": bool(contract.get("selected")),
        "input_sha256": _digest(text),
        "act": contract.get("act"),
        "language": contract.get("language"),
        "raw_dialogue_persisted": False,
        "model_call_added": False,
    }
    if not audit["selected"]:
        return {**audit, "status": "not_selected", "reason": contract.get("reason")}

    extraction = p4i.extract_explicit_current_preference_p4(text)
    if not extraction.get("classifier_cue_id"):
        return {
            **audit,
            "status": "preflight_rejected",
            "admitted": False,
            "reason": "p4_i_classifier_cue_missing",
            "owner_admission": None,
        }
    admitted, admission = owner.admit_selected_current_preference(text, extraction)
    scope_state = _scope_state_eligibility(extraction, memory)
    if admission.get("input_sha256") != audit["input_sha256"]:
        admitted = False
        reason = "preflight_input_hash_mismatch"
    elif admitted and scope_state["status"] == "ambiguous":
        admitted = False
        reason = "old_value_has_multiple_active_scopes"
    elif admitted and scope_state["status"] == "unavailable":
        admitted = False
        reason = "current_preference_scope_state_unavailable"
    else:
        reason = admission.get("reason") or "explicit_self_source_span"
    return {
        **audit,
        "status": "preflight_admitted" if admitted else "preflight_rejected",
        "admitted": bool(admitted),
        "reason": reason,
        "owner_admitted": bool(admission.get("admitted_count")),
        "scope_state": scope_state,
        "current_value_sha256": extraction.get("current_value_sha256"),
        "previous_value_sha256": extraction.get("previous_value_sha256"),
        "extraction_status": extraction.get("status"),
        "extraction_reason": extraction.get("reason"),
        "extracted_positive_count": extraction.get("extracted_positive_count"),
        "extracted_pair_count": extraction.get("extracted_pair_count"),
        "owner_admission": deepcopy(admission),
    }


def query_all_layers_with_profile_write_ack_truth_p4(self, text):
    memory_data = _ORIGINAL_QUERY(self, text)
    if not isinstance(memory_data, dict):
        return memory_data
    preflight = preflight_profile_write_ack_p4(text, memory=self)
    if preflight.get("selected") and (preflight.get("scope_state") or {}).get("status") == "unavailable":
        raise ProfileWriteAckIntegrityError(f"{LABEL}:scope_state_unavailable_prewrite")
    memory_data[LABEL] = preflight
    return memory_data


def _preflight_from_memory_data(user_input, memory_data):
    stored = (memory_data or {}).get(LABEL) if isinstance(memory_data, dict) else None
    if (
        isinstance(stored, dict)
        and stored.get("schema") == SCHEMA
        and stored.get("input_sha256") == _digest(str(user_input or "").strip())
    ):
        return deepcopy(stored)
    return preflight_profile_write_ack_p4(user_input)


def _rejection_reply(preflight):
    if preflight.get("reason") == "old_value_has_multiple_active_scopes":
        return AMBIGUOUS_SCOPE_REPLY
    if preflight.get("reason") == "current_preference_scope_state_unavailable":
        return UNCLEAR_VALUE_REPLY
    if preflight.get("reason") == "selected_act_ambiguous_extraction":
        if (preflight.get("extracted_positive_count") or 0) > 1:
            return MULTIPLE_VALUES_REPLY
        return UNCLEAR_VALUE_REPLY
    return NON_COMMITMENT_REPLY


def _rejected_plan(preflight):
    final = _rejection_reply(preflight)
    return {
        "candidate_label": "p4_profile_write_ack_rejected",
        "intent": "profile_write_ack_rejected",
        "mood_impact": 0,
        "trust_impact": 0,
        "scene": "casual",
        "listener_state": "本人の好みとしては確認できない発話を受け取った",
        "reply_goal": "profile への記憶を約束せず、出所か値の曖昧さを伝える",
        "jp_summary": "本人の好みとしての書き込みは未確定。",
        "core_message_jp": final,
        "cognitive_mode": "direct",
        "response_mode": "direct_answer",
        "uncertainty": 0.5,
        "premise_check": "question",
        "self_check": True,
        "subjective_note_jp": "出所や値が曖昧なら、記憶したと確約しない",
        "surface_act": "plain_reply",
        "grounding": {
            "source": "source_span_bound_profile_owner_admission",
            "input_sha256": preflight["input_sha256"],
        },
        "payload_level": "low",
        "planner_path": "profile_write_ack_truth_p4",
        LABEL: deepcopy(preflight),
        "constraints": {"casual_japanese_only": True, "forbid_polite": True},
        "must_avoid": ["覚えとく", "覚えておく", "記憶した"],
    }


def rule_plan_with_profile_write_ack_truth_p4(self, user_input, current_psyche, memory_data=None):
    preflight = _preflight_from_memory_data(user_input, memory_data)
    if preflight["selected"] and not preflight["admitted"]:
        return _rejected_plan(preflight)
    return _ORIGINAL_RULE_PLAN(self, user_input, current_psyche, memory_data)


def _protected_logic(logic_data):
    logic = logic_data or {}
    route = str(((logic.get("semantic_route_m22") or {}).get("selected_type") or ""))
    return bool(
        route == "safety_sensitive"
        or str(logic.get("intent") or "") in adaptive_person.PROTECTED_INTENTS
        or str(logic.get("scene") or "") in adaptive_person.PROTECTED_SCENES
    )


def visible_guard_with_profile_write_ack_truth_p4(
    self, reply, logic_data, user_input="", memory_data=None
):
    # Preserve the prior language/safety guard's actual surface before P4-H
    # mutates its audit and may replace a generic reply with a false promise.
    prior_guard_final = (
        str(((logic_data or {}).get("visible_language_guard") or {}).get("final_reply") or "").strip()
        if isinstance(logic_data, dict) else ""
    )
    visible = _ORIGINAL_VISIBLE_GUARD(
        self, reply, logic_data, user_input=user_input, memory_data=memory_data
    )
    preflight = _preflight_from_memory_data(user_input, memory_data)
    if not preflight["selected"] or not isinstance(logic_data, dict):
        return visible
    if (preflight.get("scope_state") or {}).get("status") == "unavailable":
        raise ProfileWriteAckIntegrityError(f"{LABEL}:scope_state_unavailable_prewrite")
    if _protected_logic(logic_data):
        guard = deepcopy(logic_data.get("visible_language_guard") or {})
        final = str(visible or "").strip()
        if final in p4h.AUTHORITATIVE_SURFACES.values():
            # P4-H's safety branch can still change a generic underlying guard
            # reply into its write promise.  Restore that already-guarded reply.
            prior = prior_guard_final
            if not prior or prior in p4h.AUTHORITATIVE_SURFACES.values():
                raise ProfileWriteAckIntegrityError(f"{LABEL}:protected_surface_unavailable_prewrite")
            final = prior
        p4h_audit = deepcopy(logic_data.get(p4h.LABEL) or {})
        if p4h_audit:
            p4h_audit.update(
                status="blocked_by_protected_logic",
                reason="protected_route_or_intent_or_scene",
                plan_authority=False,
                surface_authority=False,
                surface_changed=False,
                final_visible_surface_jp=None,
                final_visible_surface_sha256=_digest(final),
            )
            logic_data[p4h.LABEL] = p4h_audit
        guard.update(
            final_reply=final,
            final_reply_sha256=_digest(final),
            explicit_preference_acknowledgement_p4=False,
            profile_write_ack_truth_p4=final != str(visible or "").strip(),
        )
        logic_data["visible_language_guard"] = guard
        logic_data[LABEL] = {
            **preflight,
            "status": "protected_surface_pending_episode",
            "reason": "protected_route_or_intent_or_scene",
            "protected_logic": True,
            "plan_authority": False,
            "surface_authority": final != str(visible or "").strip(),
            "final_visible_surface_sha256": _digest(final),
            "writeback_outcome_in_scope": False,
        }
        return final

    audit = {
        **preflight,
        "status": "preflight_admitted_pending_writer" if preflight["admitted"] else "preflight_rejected_pending_writer",
        "protected_logic": False,
        "plan_authority": not preflight["admitted"],
        "surface_authority": not preflight["admitted"],
    }
    if preflight["admitted"]:
        audit["final_visible_surface_sha256"] = _digest(visible)
        logic_data[LABEL] = audit
        return visible

    final = _rejection_reply(preflight)
    p4h_audit = deepcopy(logic_data.get(p4h.LABEL) or {})
    if p4h_audit:
        p4h_audit.update(
            status="blocked_by_profile_owner_admission_p4",
            reason=preflight["reason"],
            plan_authority=False,
            surface_authority=False,
            surface_changed=False,
            final_visible_surface_jp=None,
            final_visible_surface_sha256=_digest(final),
        )
        logic_data[p4h.LABEL] = p4h_audit
    guard = deepcopy(logic_data.get("visible_language_guard") or {})
    guard.update(
        changed=final != str(guard.get("original_reply") or reply or "").strip(),
        repair_action=LABEL,
        final_reply=final,
        final_reply_sha256=_digest(final),
        explicit_preference_acknowledgement_p4=False,
        profile_write_ack_truth_p4=True,
    )
    logic_data["visible_language_guard"] = guard
    audit.update(
        final_visible_surface_sha256=_digest(final),
        p4h_surface_vetoed=True,
    )
    logic_data[LABEL] = audit
    return final


def _check(value):
    return "matched" if value is True else "mismatch" if value is False else "unknown"


def _episode_checks(brain, result):
    reply = str(result.get("reply") or "")
    episode_doc = result.get("episode_doc")
    session_turns = getattr(getattr(brain, "memory", None), "session_turns", None)
    last_turn = session_turns[-1] if session_turns else None
    episode_id = last_turn.get("episode_id") if isinstance(last_turn, dict) else None
    checks = {
        "episode_returned_reply": _check(
            f" | Uruha: {reply} | Mood:" in episode_doc
            if isinstance(episode_doc, str) else None
        ),
        "session_turn_reply": _check(
            last_turn.get("reply") == reply if isinstance(last_turn, dict) else None
        ),
    }
    if not episode_id:
        checks["episode_persistent_reply"] = "unknown"
        return checks, None
    try:
        rows = brain.memory.episode_col.get(ids=[episode_id], include=["documents"])
        ids = rows.get("ids") or []
        docs = rows.get("documents") or []
        checks["episode_persistent_reply"] = _check(
            ids == [episode_id]
            and len(docs) == 1
            and docs[0] == episode_doc
            and f" | Uruha: {reply} | Mood:" in docs[0]
        )
    except Exception:
        checks["episode_persistent_reply"] = "unknown"
    return checks, _digest(episode_id)


def _profile_readback_check(brain, preflight, typed):
    if not isinstance(typed, dict):
        return "unknown"
    expected_scope_sha256 = (preflight.get("scope_state") or {}).get("expected_scope_sha256")
    current_value_sha256 = preflight.get("current_value_sha256")
    old_value_sha256 = preflight.get("previous_value_sha256")
    if not expected_scope_sha256 or not current_value_sha256:
        return "unknown"
    current_id = typed.get("current_memory_id")
    ids = [current_id]
    if preflight.get("act") == "correction":
        ids.append(typed.get("negative_old_memory_id"))
    if any(not memory_id for memory_id in ids) or (len(ids) == 2 and not old_value_sha256):
        return "unknown"
    try:
        rows = brain.memory.profile_col.get(ids=ids, include=["metadatas"])
        found_ids = rows.get("ids") or []
        metas = rows.get("metadatas") or []
        if set(found_ids) != set(ids) or len(metas) != len(ids):
            return "mismatch"
        by_id = dict(zip(found_ids, metas))

        def base_matches(meta):
            return bool(
                isinstance(meta, dict)
                and meta.get("subject") == "user"
                and meta.get("source_input_sha256") == preflight["input_sha256"]
                and meta.get("preference_act") == preflight["act"]
                and meta.get("preference_semantics_schema") == p4i.SEMANTICS_SCHEMA
                and _digest(p4i._normalize(meta.get("preference_scope"))) == expected_scope_sha256
                and meta.get("preference_scope_sha256") == expected_scope_sha256
            )

        current = by_id[current_id]
        current_matches = bool(
            base_matches(current)
            and current.get("fact_type") == "like"
            and current.get("preference_semantics") == "current_preference"
            and _digest(p4i._normalize(current.get("value"))) == current_value_sha256
            and current.get("predicate") == p4i.current_preference_predicate(current.get("preference_scope"))
        )
        if len(ids) == 1:
            return _check(current_matches)
        negative = by_id[ids[1]]
        return _check(bool(
            current_matches
            and base_matches(negative)
            and negative.get("fact_type") == "dislike"
            and negative.get("preference_semantics") == "explicitly_negated_preference"
            and _digest(p4i._normalize(negative.get("value"))) == old_value_sha256
            and negative.get("correction_current_memory_id") == current_id
        ))
    except Exception:
        return "unknown"


def materialize_profile_write_ack_truth_p4(brain, result):
    """Audit a completed turn; never replace its already-persisted reply."""
    logic = result.get("logic") or {}
    preflight = logic.get(LABEL)
    if not isinstance(preflight, dict) or preflight.get("schema") != SCHEMA:
        return result
    trace = result.setdefault("runtime_trace", {})
    rows = [row for row in trace.get("blackboard", []) if row.get("label") != LABEL]
    protected = bool(preflight.get("protected_logic"))
    rejected = not preflight.get("admitted") and not protected
    if rejected or protected:
        # P4-H's frozen materializer otherwise adds a success-shaped select row.
        rows = [row for row in rows if row.get("label") != p4h.LABEL]
        trace.pop(p4h.LABEL, None)
        p4h_audit = logic.get(p4h.LABEL)
        if isinstance(p4h_audit, dict):
            p4h_audit = deepcopy(p4h_audit)
            p4h_audit.update(
                status="blocked_by_protected_logic" if protected else "blocked_by_profile_owner_admission_p4",
                reason=preflight.get("reason"),
                plan_authority=False,
                surface_authority=False,
                final_visible_surface_matches_contract=False,
            )
            p4h_audit.pop("flow", None)
            logic[p4h.LABEL] = p4h_audit

    owner_audit = (result.get("memory_runtime") or {}).get(owner.LABEL)
    typed_audit = (result.get("memory_runtime") or {}).get(p4i.LABEL)
    reply = str(result.get("reply") or "")
    utterances = [row for row in rows if row.get("label") == "utterance"]
    owner_rows = [row for row in rows if row.get("label") == owner.LABEL]
    episode_checks, episode_id_sha256 = _episode_checks(brain, result)
    fallback_marker = getattr(getattr(brain, "memory", None), "_last_profile_write_ack_legacy_fallback", None)
    fallback_suppressed = bool(
        isinstance(fallback_marker, dict)
        and fallback_marker.get("schema") == SCHEMA
        and fallback_marker.get("suppressed") is True
        and fallback_marker.get("reason") == "old_value_has_multiple_active_scopes"
        and fallback_marker.get("input_sha256") == preflight.get("input_sha256")
        and episode_id_sha256
        and fallback_marker.get("episode_id_sha256") == episode_id_sha256
        and fallback_marker.get("active_old_scope_count")
        == (preflight.get("scope_state") or {}).get("active_old_scope_count")
    )
    shared_checks = {
        "utterance_reply": _check(
            len(utterances) == 1 and (utterances[0].get("payload") or {}).get("reply") == reply
        ),
        "visible_guard_reply": _check(
            (logic.get("visible_language_guard") or {}).get("final_reply") == reply
        ),
        **episode_checks,
    }
    if protected:
        checks = {
            **shared_checks,
            "protected_logic_preserved": _check(_protected_logic(logic)),
            "p4h_promise_absent": _check(reply not in p4h.AUTHORITATIVE_SURFACES.values()),
            "p4h_success_graph_absent": _check(
                not any(row.get("label") == p4h.LABEL for row in rows)
            ),
        }
    else:
        checks = {
        **shared_checks,
        "input_hash": _check(
            owner_audit.get("input_sha256") == preflight["input_sha256"]
            if isinstance(owner_audit, dict) else None
        ),
        "owner_reason": _check(
            owner_audit.get("reason") == preflight.get("reason")
            if rejected and preflight.get("reason") != "old_value_has_multiple_active_scopes"
            and isinstance(owner_audit, dict) else True if not rejected or preflight.get("reason") == "old_value_has_multiple_active_scopes" else None
        ),
        "owner_graph": _check(
            len(owner_rows) == 1 and owner_rows[0].get("payload") == owner_audit
            if isinstance(owner_audit, dict) else None
        ),
        "owner_path": _check(
            owner_audit.get("path") == "p4_i_selected"
            if isinstance(owner_audit, dict) else None
        ),
        }
    if rejected:
        state_blocked = preflight.get("reason") == "old_value_has_multiple_active_scopes"
        if state_blocked:
            checks["legacy_fallback_suppressed"] = _check(
                fallback_suppressed if episode_id_sha256 else None
            )
        checks.update({
            "writer_outcome": _check(
                (
                    owner_audit.get("admitted_count") == 1
                    and owner_audit.get("writer_status") == "typed_write_not_completed"
                    and owner_audit.get("profile_collection_count_delta") == 0
                    and isinstance(typed_audit, dict)
                    and typed_audit.get("status") == "ambiguous_extraction"
                    and typed_audit.get("reason") == "old_value_has_multiple_active_scopes"
                ) if state_blocked and isinstance(owner_audit, dict) else (
                    owner_audit.get("admitted_count") == 0
                    and owner_audit.get("profile_collection_count_delta") == 0
                    and owner_audit.get("persistence_evidence") == "writer_not_invoked"
                ) if isinstance(owner_audit, dict) else None
            ),
            "non_commitment_surface": _check(reply == _rejection_reply(preflight)),
            "p4h_success_graph_absent": _check(
                not any(row.get("label") == p4h.LABEL for row in rows)
            ),
            "non_commitment_plan": _check(
                logic.get("intent") not in {
                    "explicit_preference_memory_write",
                    "explicit_preference_memory_correction",
                }
            ),
            "p4h_commitment_absent": _check(
                isinstance(logic.get(p4h.LABEL), dict)
                and logic[p4h.LABEL].get("status") == "blocked_by_profile_owner_admission_p4"
                and logic[p4h.LABEL].get("surface_authority") is False
                and "flow" not in logic[p4h.LABEL]
            ),
        })
    elif not protected:
        expected_count = 2 if preflight.get("act") == "correction" else 1
        checks.update({
            "writer_outcome": _check(
                owner_audit.get("admitted_count") == 1
                and owner_audit.get("writer_status") == "typed_write_completed"
                and owner_audit.get("profile_collection_count_delta") == expected_count
                and typed_audit.get("status") == "typed_current_preference_written"
                and typed_audit.get("profile_write_count") == expected_count
                if isinstance(owner_audit, dict) and isinstance(typed_audit, dict) else None
            ),
            "profile_id_readback": _profile_readback_check(brain, preflight, typed_audit),
            "p4h_visible_surface": _check(
                reply == p4h.AUTHORITATIVE_SURFACES.get(preflight.get("act"))
            ),
        })
    status = "mismatch" if "mismatch" in checks.values() else "unknown" if "unknown" in checks.values() else "matched"
    audit = {
        **preflight,
        "status": status,
        "actual_owner_path": owner_audit.get("path") if isinstance(owner_audit, dict) else None,
        "actual_writer_status": owner_audit.get("writer_status") if isinstance(owner_audit, dict) else None,
        "actual_admitted_count": owner_audit.get("admitted_count") if isinstance(owner_audit, dict) else None,
        "actual_profile_collection_count_delta": owner_audit.get("profile_collection_count_delta") if isinstance(owner_audit, dict) else None,
        "legacy_fallback_suppressed": fallback_suppressed if rejected and preflight.get("reason") == "old_value_has_multiple_active_scopes" else False,
        "legacy_fallback_evidence": deepcopy(fallback_marker) if fallback_suppressed else None,
        "episode_id_sha256": episode_id_sha256,
        "checks": checks,
        "final_visible_surface_sha256": _digest(reply),
        "writeback_observed": status == "matched" and not protected,
        "writeback_outcome_in_scope": not protected,
    }
    logic[LABEL] = deepcopy(audit)
    result["logic"] = logic
    rows.append({
        "stage": "verify",
        "label": LABEL,
        "payload": deepcopy(audit),
        "salience": 0.99 if status != "matched" else 0.9,
    })
    trace["blackboard"] = rows
    trace[LABEL] = deepcopy(audit)
    return result


def require_matched_profile_write_ack_p4(result):
    audit = (result.get("logic") or {}).get(LABEL)
    if isinstance(audit, dict) and audit.get("schema") == SCHEMA and audit.get("status") != "matched":
        raise ProfileWriteAckIntegrityError(f"{LABEL}:{audit.get('status') or 'unknown'}")
    return result


def _finish_profile_write_ack_truth_p4(self, result):
    from uruha_trace_history_sync_m41_1 import sync_current_history_m41_1

    materialize_profile_write_ack_truth_p4(self, result)
    if LABEL not in (result.get("logic") or {}):
        return result
    self.runtime.blackboard = deepcopy(result["runtime_trace"]["blackboard"])
    sync_current_history_m41_1(result)
    if (
        self.runtime.turn_traces
        and self.runtime.turn_traces[-1].get("cycle_index") == result["runtime_trace"].get("cycle_index")
    ):
        self.runtime.turn_traces[-1] = deepcopy(result["runtime_trace"])
    return require_matched_profile_write_ack_p4(result)


def run_turn_debug_with_profile_write_ack_truth_p4(self, user_input, input_context=None):
    token = _RUN_ACTIVE.set(True)
    try:
        result = _ORIGINAL_RUN(self, user_input, input_context=input_context)
    finally:
        _RUN_ACTIVE.reset(token)
    return _finish_profile_write_ack_truth_p4(self, result)


def emit_response_if_ready_with_profile_write_ack_truth_p4(self, event, tick_result):
    source = (event or {}).get("user_input")
    memory_data = (event or {}).get("memory_data")
    preflight = _preflight_from_memory_data(source, memory_data)
    if preflight.get("selected") and (preflight.get("scope_state") or {}).get("status") == "unavailable":
        raise ProfileWriteAckIntegrityError(f"{LABEL}:scope_state_unavailable_prewrite")
    result = _ORIGINAL_EMIT(self, event, tick_result)
    # run_turn_debug invokes emit_response_if_ready internally.  The outer run
    # finishes only after its latency/trace synchronization has been appended.
    if _RUN_ACTIVE.get():
        return result
    return _finish_profile_write_ack_truth_p4(self, result)


def install_profile_write_ack_truth_p4():
    global _INSTALLED, _ORIGINAL_RULE_PLAN, _ORIGINAL_VISIBLE_GUARD
    global _ORIGINAL_QUERY, _ORIGINAL_RUN, _ORIGINAL_EMIT
    global _ORIGINAL_LEGACY_PROFILE_FALLBACK
    if _INSTALLED:
        return False
    from uruha_brain_mac import LeftBrain, MemoryManager, RightBrain, UruhaBrainV4_Mac

    _ORIGINAL_RULE_PLAN = LeftBrain._rule_based_plan
    _ORIGINAL_VISIBLE_GUARD = RightBrain.enforce_user_visible_japanese
    _ORIGINAL_QUERY = MemoryManager.query_all_layers
    _ORIGINAL_RUN = UruhaBrainV4_Mac.run_turn_debug
    _ORIGINAL_EMIT = UruhaBrainV4_Mac.emit_response_if_ready
    _ORIGINAL_LEGACY_PROFILE_FALLBACK = p4i._ORIGINAL_REMEMBER_PROFILE_FACTS
    if not callable(_ORIGINAL_LEGACY_PROFILE_FALLBACK):
        raise ProfileWriteAckIntegrityError(f"{LABEL}:legacy_fallback_not_installed")
    # P4-I calls this only when it delegates to the legacy writer.  Do not
    # replace P4-I or the owner writer: their actual audits must remain intact.
    p4i._ORIGINAL_REMEMBER_PROFILE_FACTS = legacy_profile_fallback_with_profile_write_ack_truth_p4
    LeftBrain._rule_based_plan = rule_plan_with_profile_write_ack_truth_p4
    RightBrain.enforce_user_visible_japanese = visible_guard_with_profile_write_ack_truth_p4
    MemoryManager.query_all_layers = query_all_layers_with_profile_write_ack_truth_p4

    UruhaBrainV4_Mac.run_turn_debug = run_turn_debug_with_profile_write_ack_truth_p4
    UruhaBrainV4_Mac.emit_response_if_ready = emit_response_if_ready_with_profile_write_ack_truth_p4
    _INSTALLED = True
    return True
