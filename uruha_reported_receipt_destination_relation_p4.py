"""Opt-in, source-bound receiving-destination surface check after frozen P4-D.

This is a narrow product repair, not a claim that the model understands a
general proposition.  The original P4-Z module and historical SHA stay fixed.
"""

from __future__ import annotations

from contextvars import ContextVar
from copy import deepcopy
from datetime import date
import hashlib
import re
import unicodedata

import uruha_adaptive_person_model as adaptive_person
import uruha_current_decision_ack_authority_p4 as p4d
from uruha_deterministic_plan_leak_surface_p4 import _sync_selected_short_history


LABEL = "receipt_destination_relation_p4"
SCHEMA = "uruha_reported_receipt_destination_relation_p4_v1"
RULE_ID = "p4_reported_receipt_destination_ja_source_v1"
_SOURCE = re.compile(
    r"(?P<actor>[^\s\n\r。！？!?「」『』“”\"']{1,20})は"
    r"(?P<year>[0-9]{4})年(?P<month>[0-9]{1,2})月(?P<day>[0-9]{1,2})日に"
    r"(?P<object>[^\s\n\r。！？!?「」『』“”\"'を]{1,36})を受け取る場所を"
    r"(?P<destination>[^\s\n\r。！？!?「」『』“”\"']{1,48})に決めたらしい。?"
)
_REJECTED_ACTORS = frozenset({"私", "わたし", "僕", "俺", "自分", "あなた", "君", "そっち", "うるは", "一ノ瀬うるは"})
_SENSITIVE = re.compile(r"暗証番号|パスワード|パスコード|認証コード|住所|電話番号|口座|秘密|自殺|自傷")
_INSTALLED = False
_PRIOR_GUARD = None
_PRIOR_POST_CHECK = None
_PRIOR_RUN = None
_PRIOR_EMIT = None
_PRIOR_PROFILE_REMEMBER = None
_ACTIVE_EMIT = ContextVar("p4_reported_receipt_destination_active_emit", default=None)


def _sha(value: str) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def extract_reported_receipt_destination_p4(source: str) -> dict | None:
    """Parse a single unquoted report; slots and relation come only from User."""
    raw = str(source or "")
    if not raw or raw != raw.strip() or len(raw) > 180 or _SENSITIVE.search(raw):
        return None
    if any(unicodedata.category(ch) in {"Cc", "Cf", "Cs", "Zl", "Zp"} for ch in raw):
        return None
    matched = _SOURCE.fullmatch(raw)
    if not matched:
        return None
    actor = matched.group("actor")
    obj = matched.group("object")
    destination = matched.group("destination")
    if (
        actor in _REJECTED_ACTORS
        or "うるは" in actor or "一ノ瀬" in actor
        or any(value.startswith(("私", "僕", "俺", "あなた", "君")) for value in (actor,))
        or any("決め" in value or "受け取る場所" in value for value in (actor, obj, destination))
    ):
        return None
    try:
        date(int(matched.group("year")), int(matched.group("month")), int(matched.group("day")))
    except ValueError:
        return None
    date_text = f"{matched.group('year')}年{matched.group('month')}月{matched.group('day')}日"
    return {
        "actor": actor, "date": date_text, "object": obj, "destination": destination,
        "location_role": "receiving_destination_selected",
        "embedding_stance": "third_party_hearsay",
        "temporal_scope": "unresolved_source_ambiguity",
        "rule_id": RULE_ID,
    }


def inspect_reported_receipt_destination_p4(contract: dict, candidate: str) -> list[str]:
    """A quoted, negated, or contradictory correct substring is not enough."""
    if not contract:
        return ["source_pattern_unavailable"]
    pattern = (
        re.escape(contract["actor"]) + "は" + re.escape(contract["date"]) + "に"
        + re.escape(contract["object"]) + "を受け取る場所を"
        + re.escape(contract["destination"]) + r"に決めたらしい(?:ね|んだね|って話ね)?。?"
    )
    return [] if re.fullmatch(pattern, str(candidate or "")) else ["receiving_destination_relation_or_stance_not_exact"]


def _render(contract: dict) -> str:
    return (
        f"{contract['actor']}は{contract['date']}に{contract['object']}を受け取る場所を"
        f"{contract['destination']}に決めたらしいね。"
    )


def preserve_reported_receipt_destination_p4(source: str, candidate: str) -> tuple[str, dict]:
    before = str(candidate or "")
    contract = extract_reported_receipt_destination_p4(source)
    if contract is None:
        return before, {
            "schema": SCHEMA, "status": "source_pattern_unavailable", "action": "abstain_unchanged",
            "summary": "來源句型未確定，不改寫接收地點",
            "changed": False, "before_digest": _sha(before), "after_digest": _sha(before),
            "rule_id": None, "known_field_types": [], "location_role": "unknown",
            "temporal_scope": "unknown", "source_anchor_digests": {},
            "violations_before": ["source_pattern_unavailable"],
            "violations_after": ["source_pattern_unavailable"],
            "raw_source_or_reply_persisted": False, "model_call_added": False,
            "fact_write_count": 0, "profile_write_count": 0, "episode_write_count": 0,
            "claim_boundary": "unsupported grammar unchanged; not open-domain semantics",
        }
    before_violations = inspect_reported_receipt_destination_p4(contract, before)
    after = _render(contract) if before_violations else before
    after_violations = inspect_reported_receipt_destination_p4(contract, after)
    if after_violations:
        raise RuntimeError("reported receipt destination repair failed closed")
    return after, {
        "schema": SCHEMA,
        "status": "repaired_and_verified" if before_violations else "accepted_verified",
        "action": "source_bound_repair" if before_violations else "verified_noop",
        "summary": "接收地點角色已按來源校正；日期範圍未定" if before_violations else "接收地點角色與來源一致；日期範圍未定",
        "changed": after != before,
        "before_digest": _sha(before), "after_digest": _sha(after),
        "rule_id": RULE_ID, "known_field_types": ["actor", "date", "object", "destination"],
        "location_role": contract["location_role"],
        "temporal_scope": contract["temporal_scope"],
        "source_anchor_digests": {key: _sha(contract[key]) for key in ("actor", "date", "object", "destination")},
        "violations_before": before_violations, "violations_after": after_violations,
        "raw_source_or_reply_persisted": False, "model_call_added": False,
        "fact_write_count": 0, "profile_write_count": 0, "episode_write_count": 0,
        "claim_boundary": "bounded source relation preservation; date attachment unresolved; no open-domain understanding",
    }


def _protected(right_brain, logic: dict) -> bool:
    return bool(
        p4d._selected(logic) is not None
        or logic.get("routing_path") == "low_road"
        or (logic.get("semantic_route_m22") or {}).get("selected_type") == "safety_sensitive"
        or logic.get("intent") in adaptive_person.PROTECTED_INTENTS
        or logic.get("scene") in adaptive_person.PROTECTED_SCENES
        or logic.get("intent") in {"reference_probe", "self_intro"}
        or logic.get("surface_act") == "reference_probe"
        or getattr(right_brain, "_structured_surface_required", lambda: False)()
    )


def _guard_with_reported_receipt_destination_p4(
    right_brain, reply, logic: dict, source: str, memory_data, prior_guard
):
    if not isinstance(logic, dict) or "受け取る場所" not in str(source or ""):
        return prior_guard(right_brain, reply, logic, user_input=source, memory_data=memory_data)
    contract = extract_reported_receipt_destination_p4(source)
    if contract is None or _protected(right_brain, logic):
        visible = prior_guard(right_brain, reply, logic, user_input=source, memory_data=memory_data)
        _, trace = preserve_reported_receipt_destination_p4("", visible)
        if contract is not None:
            trace["status"] = "protected_route_not_repaired"
            trace["action"] = "prior_authority_unchanged"
            trace["summary"] = "保護路由保留既有權限，不改寫"
            trace["rule_id"] = RULE_ID
            trace["known_field_types"] = ["actor", "date", "object", "destination"]
            trace["location_role"] = contract["location_role"]
            trace["temporal_scope"] = contract["temporal_scope"]
            trace["source_anchor_digests"] = {
                key: _sha(contract[key]) for key in ("actor", "date", "object", "destination")
            }
        logic[LABEL] = trace
        return visible

    proposed, trace = preserve_reported_receipt_destination_p4(source, reply)
    visible = prior_guard(right_brain, proposed, logic, user_input=source, memory_data=memory_data)
    guard = logic.get("visible_language_guard") or {}
    if (
        inspect_reported_receipt_destination_p4(contract, visible)
        or guard.get("final_reply") != visible
        or guard.get("final_reply_sha256") != _sha(visible)
    ):
        raise RuntimeError("reported receipt destination final guard mismatch")
    trace["after_digest"] = _sha(visible)
    trace["changed"] = visible != str(reply or "")
    history = getattr(right_brain, "history", None)
    intent = str(logic.get("intent") or "")
    if not (
        isinstance(history, list) and len(history) >= 2
        and isinstance(history[-2], dict) and isinstance(history[-1], dict)
        and history[-2].get("role") == "user"
        and history[-2].get("intent") == intent
        and history[-1].get("role") == "assistant"
        and history[-1].get("intent") == intent
    ):
        raise RuntimeError("reported receipt destination current history mismatch")
    # speak records jp_summary, not raw source, immediately before the selected
    # assistant candidate. Match it when available so an older same-intent pair
    # cannot be rebound as this turn. Legacy minimal contract fixtures have no
    # summary; the final pre-episode binding still applies to those fixtures.
    summary = logic.get("jp_summary")
    if summary and history[-2].get("content") != summary:
        raise RuntimeError("reported receipt destination current history mismatch")
    before_history = str(history[-1].get("content") or "")
    if before_history != visible:
        status = _sync_selected_short_history(right_brain, before_history, visible, intent)
        if status != "current_assistant_synced":
            raise RuntimeError("reported receipt destination current history mismatch")
        trace["history_status"] = status
    else:
        trace["history_status"] = "current_assistant_already_bound"
    logic[LABEL] = trace
    right_brain._bind_forbidden_projection_shadow_visible_reply(logic, visible)
    return visible


def _post_check_with_reported_receipt_destination_p4(brain, logic, source, visible, memory_data, prior_post):
    trace = (logic or {}).get(LABEL) or {}
    eligible = bool(
        extract_reported_receipt_destination_p4(source)
        and isinstance(logic, dict)
        and not _protected(getattr(brain, "right_brain", None), logic)
    )
    if eligible:
        if trace.get("status") not in {"repaired_and_verified", "accepted_verified"}:
            raise RuntimeError("reported receipt destination verification missing before episode")
        contract = extract_reported_receipt_destination_p4(source)
        guard = (logic or {}).get("visible_language_guard") or {}
        history = getattr(getattr(brain, "right_brain", None), "history", None)
        mismatch_codes = []
        if contract is None or inspect_reported_receipt_destination_p4(contract, visible):
            mismatch_codes.append("source_relation")
        if trace.get("after_digest") != _sha(visible):
            mismatch_codes.append("trace_digest")
        if guard.get("final_reply") != visible or guard.get("final_reply_sha256") != _sha(visible):
            mismatch_codes.append("guard_binding")
        if (
            not isinstance(history, list) or not history
            or not isinstance(history[-1], dict)
            or history[-1].get("role") != "assistant" or history[-1].get("content") != visible
        ):
            mismatch_codes.append("current_history")
        if mismatch_codes:
            raise RuntimeError("reported receipt destination pre-episode mismatch: " + ",".join(mismatch_codes))
        trace["pre_episode_status"] = "verified_before_episode_write"
    return prior_post(brain, logic, source, visible, memory_data)


def _short_history_snapshot(right_brain):
    names = (
        "reply_variant_counts", "intent_variant_counts",
        "normalized_reply_counts", "intent_normalized_counts",
    )
    history = getattr(right_brain, "history", None)
    counters = {name: getattr(right_brain, name, None) for name in names}
    if not isinstance(history, list) or any(not isinstance(item, dict) for item in counters.values()):
        raise RuntimeError("reported receipt destination history snapshot unavailable")
    return deepcopy(history), {name: deepcopy(value) for name, value in counters.items()}


def _restore_short_history(right_brain, snapshot):
    history, counters = snapshot
    right_brain.history[:] = history
    for name, value in counters.items():
        target = getattr(right_brain, name)
        target.clear()
        target.update(value)


def _emit_with_reported_receipt_destination_p4(brain, event, tick_result, prior_emit):
    source = (event or {}).get("user_input") if isinstance(event, dict) else ""
    logic = (tick_result or {}).get("logic") if isinstance(tick_result, dict) else None
    eligible = bool(
        extract_reported_receipt_destination_p4(source)
        and isinstance(logic, dict)
        and not _protected(getattr(brain, "right_brain", None), logic)
    )
    if not eligible:
        return prior_emit(brain, event, tick_result)
    snapshot = _short_history_snapshot(brain.right_brain)
    tx = {"memory": getattr(brain, "memory", None), "source": source,
          "logic": logic, "profile_suppressed": False}
    token = _ACTIVE_EMIT.set(tx)
    try:
        result = prior_emit(brain, event, tick_result)
        trace = (logic or {}).get(LABEL) or {}
        if (
            trace.get("pre_episode_status") != "verified_before_episode_write"
            or trace.get("profile_write_status") != "suppressed_for_third_party_report"
            or not tx["profile_suppressed"]
        ):
            raise RuntimeError("reported receipt destination pre-episode verification missing")
        return append_reported_receipt_destination_node_p4(result)
    except Exception:
        _restore_short_history(brain.right_brain, snapshot)
        raise
    finally:
        _ACTIVE_EMIT.reset(token)


def _remember_profile_with_reported_receipt_destination_p4(memory, source, prior_remember):
    tx = _ACTIVE_EMIT.get()
    if not isinstance(tx, dict) or tx.get("memory") is not memory or tx.get("source") != source:
        return prior_remember(memory, source)
    trace = (tx.get("logic") or {}).get(LABEL) or {}
    if trace.get("pre_episode_status") != "verified_before_episode_write":
        raise RuntimeError("reported receipt destination profile suppression unverified")
    trace["profile_write_status"] = "suppressed_for_third_party_report"
    tx["profile_suppressed"] = True
    return None


def append_reported_receipt_destination_node_p4(result: dict) -> dict:
    if not isinstance(result, dict):
        return result
    trace = deepcopy(((result.get("logic") or {}).get(LABEL)) or {})
    if not trace:
        return result
    runtime_trace = result.setdefault("runtime_trace", {})
    rows = [row for row in list(runtime_trace.get("blackboard") or []) if row.get("label") != LABEL]
    index = next((i for i, row in enumerate(rows) if row.get("label") == "utterance"), len(rows))
    rows.insert(index, {"stage": "surface", "label": LABEL, "payload": deepcopy(trace), "salience": 1.0 if trace.get("changed") else 0.82})
    runtime_trace["blackboard"] = rows
    runtime_trace[LABEL] = deepcopy(trace)
    return result


def install_reported_receipt_destination_relation_p4() -> bool:
    """Install only after the frozen D entry's exact installer sequence."""
    global _INSTALLED, _PRIOR_GUARD, _PRIOR_POST_CHECK, _PRIOR_RUN, _PRIOR_EMIT, _PRIOR_PROFILE_REMEMBER
    if _INSTALLED:
        return False
    from uruha_brain_mac import MemoryManager, RightBrain, UruhaBrainV4_Mac

    _PRIOR_GUARD = RightBrain.enforce_user_visible_japanese
    _PRIOR_POST_CHECK = UruhaBrainV4_Mac._attach_reply_post_check
    _PRIOR_RUN = UruhaBrainV4_Mac.run_turn_debug
    _PRIOR_EMIT = UruhaBrainV4_Mac.emit_response_if_ready
    _PRIOR_PROFILE_REMEMBER = MemoryManager._remember_profile_facts

    def guard(self, reply, logic_data, user_input="", memory_data=None):
        return _guard_with_reported_receipt_destination_p4(
            self, reply, logic_data, user_input, memory_data, _PRIOR_GUARD,
        )

    def post_check(self, logic, user_input, reply, memory_data):
        return _post_check_with_reported_receipt_destination_p4(
            self, logic, user_input, reply, memory_data, _PRIOR_POST_CHECK,
        )

    def run(self, user_input, input_context=None):
        result = _PRIOR_RUN(self, user_input, input_context=input_context)
        result = append_reported_receipt_destination_node_p4(result)
        trace = result.get("runtime_trace") if isinstance(result, dict) else None
        runtime = getattr(self, "runtime", None)
        if isinstance(trace, dict) and runtime is not None:
            runtime.blackboard = deepcopy(trace.get("blackboard") or [])
            if (getattr(runtime, "turn_traces", None)
                    and runtime.turn_traces[-1].get("cycle_index") == trace.get("cycle_index")):
                runtime.turn_traces[-1] = deepcopy(trace)
        return result

    def emit(self, event, tick_result):
        return _emit_with_reported_receipt_destination_p4(self, event, tick_result, _PRIOR_EMIT)

    def remember_profile(self, user_input):
        return _remember_profile_with_reported_receipt_destination_p4(
            self, user_input, _PRIOR_PROFILE_REMEMBER,
        )

    RightBrain.enforce_user_visible_japanese = guard
    UruhaBrainV4_Mac._attach_reply_post_check = post_check
    UruhaBrainV4_Mac.run_turn_debug = run
    UruhaBrainV4_Mac.emit_response_if_ready = emit
    MemoryManager._remember_profile_facts = remember_profile
    _INSTALLED = True
    return True
