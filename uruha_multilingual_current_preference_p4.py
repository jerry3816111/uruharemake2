"""Product-only typed state for explicit multilingual current preferences.

P4-H owns the bounded acknowledgement plan and visible surface.  P4-I reuses
that exact classifier as its activation gate and projects the explicitly stated
preference into a scope-aware typed profile record.  The persistent profile
state remains observation-only and is not added to answer generation here.
"""

from __future__ import annotations

from copy import deepcopy
import datetime
import hashlib
import re
import unicodedata
import uuid

import uruha_explicit_preference_acknowledgement_p4 as p4h
from uruha_memory_validity import resolve_memory_validity
import uruha_profile_memory as upm


LABEL = "multilingual_current_preference_p4"
SCHEMA = "uruha_multilingual_current_preference_p4"
SEMANTICS_SCHEMA = "uruha_current_preference_typed_state_p4_v1"
_INSTALLED = False
_ORIGINAL_REMEMBER_PROFILE_FACTS = None
_ORIGINAL_MEMORY_SNAPSHOT = None
_ORIGINAL_RUN = None
_ORIGINAL_EMIT = None


_WRITE_PATTERNS = {
    "en": re.compile(r"\bI\s+(?:prefer|like)\s+(?P<new>[^.!?\n]{1,100})", re.I),
    "zh": re.compile(
        r"我(?:現在|现在)?(?:比較|比较)?(?:喜歡|喜欢)\s*"
        r"(?P<new>[^，。！？!?\n]{1,60})"
    ),
    "ja": re.compile(
        r"(?:私は|うちは|自分は|今は)\s*(?P<new>[^、。！？!?\n]{1,60}?)"
        r"(?:が|を)(?:好き|好み)"
    ),
}

_CORRECTION_PATTERNS = {
    "en": re.compile(
        r"\bI\s+(?:(?:do\s+not|don't)\s+(?:prefer|like)\s+"
        r"(?P<old_a>[^.!?\n]{1,100}?)\s+anymore|"
        r"no\s+longer\s+(?:prefer|like)\s+(?P<old_b>[^.!?\n]{1,100}))"
        r"\s*[.!?]+\s*I\s+(?:prefer|like)\s+"
        r"(?P<new>[^.!?\n]{1,100}?)(?:\s+now)?(?:[.!?]|$)",
        re.I,
    ),
    "zh": re.compile(
        r"我(?:現在|现在)?(?:不再|不|已經不|已经不)(?:喜歡|喜欢)\s*"
        r"(?P<old>[^，。！？!?\n]{1,60}?)(?:了)?"
        r"[，。；;！!？?\s]+(?:我)?(?:現在|现在)(?:比較|比较)?(?:喜歡|喜欢)\s*"
        r"(?P<new>[^，。！？!?\n]{1,60})"
    ),
    "ja": re.compile(
        r"もう(?:私は|うちは|自分は)?\s*(?P<old>[^、。！？!?\n]{1,60}?)"
        r"(?:は|が)(?:好みじゃない|好きじゃない|好みではない|好きではない)"
        r"[、。；;！!？?\s]+(?:私は|うちは|自分は)?今は\s*"
        r"(?P<new>[^、。！？!?\n]{1,60}?)(?:が|を)(?:好き|好み)"
    ),
}

_SCOPE_PATTERNS = {
    "en": re.compile(
        r"\bcurrent\s+(?P<scope>[a-z][a-z -]{0,30}?)\s+preference\b",
        re.I,
    ),
    "zh": re.compile(
        r"(?:現在|现在)(?:的)?(?P<scope>[^，。！？!?\s]{1,16}?)(?:偏好|喜好)"
    ),
    "ja": re.compile(
        r"(?:今の)?(?P<scope>飲み物|食べ物|おやつ|服|音楽|ゲーム)(?:の)?好みとして"
    ),
}


def _digest(value) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def _normalize(value) -> str:
    return upm.normalize_profile_value(value)


def _clean_value(value, language) -> str:
    text = unicodedata.normalize("NFKC", str(value or ""))
    text = re.sub(r"\s+", " ", text).strip(" \t\r\n、,，。．.!！?？;；:：")
    if language == "en":
        text = re.sub(r"\s+(?:right\s+)?now$", "", text, flags=re.I).strip()
    elif language == "zh":
        text = re.sub(r"(?:了|現在|现在)$", "", text).strip()
    elif language == "ja":
        text = re.sub(r"(?:今|現在)$", "", text).strip()
    return text


def _extract_scope(text, language) -> tuple[str, str]:
    pattern = _SCOPE_PATTERNS.get(language)
    match = pattern.search(text) if pattern else None
    if not match:
        return "general", "default_general"
    scope = _clean_value(match.group("scope"), language)
    return (scope, "explicit_utterance") if scope else ("general", "default_general")


def _public_extraction(base, *, selected, status, reason=None, **fields):
    result = {
        **base,
        "selected": bool(selected),
        "status": status,
        "raw_dialogue_persisted": False,
    }
    if reason:
        result["reason"] = reason
    result.update(fields)
    return result


def extract_explicit_current_preference_p4(user_input):
    """Extract one bounded self-reported preference without retaining the utterance."""
    text = str(user_input or "").strip()
    gate = p4h.classify_explicit_preference_acknowledgement_p4(text)
    base = {
        "schema": SCHEMA,
        "input_sha256": _digest(text),
        "classifier_source": "p4_h_frozen_multilingual_classifier",
        "classifier_cue_id": gate.get("cue_id"),
    }
    if not gate.get("selected"):
        return _public_extraction(
            base,
            selected=False,
            status="not_selected",
            reason=gate.get("reason") or "p4_h_classifier_not_selected",
        )

    language = str(gate.get("language") or "")
    act = str(gate.get("act") or "")
    scope, scope_source = _extract_scope(text, language)
    if act == "write":
        pattern = _WRITE_PATTERNS.get(language)
        matches = list(pattern.finditer(text)) if pattern else []
        if len(matches) != 1:
            return _public_extraction(
                base,
                selected=False,
                status="ambiguous_extraction",
                reason="positive_value_count_not_one",
                act=act,
                language=language,
                extracted_positive_count=len(matches),
            )
        new_value = _clean_value(matches[0].group("new"), language)
        if not new_value:
            return _public_extraction(
                base,
                selected=False,
                status="ambiguous_extraction",
                reason="empty_positive_value",
                act=act,
                language=language,
            )
        return _public_extraction(
            base,
            selected=True,
            status="explicit_current_preference_extracted",
            act=act,
            language=language,
            scope=scope,
            scope_source=scope_source,
            current_value=new_value,
            current_value_sha256=_digest(_normalize(new_value)),
            epistemic_status="observed_explicit_user_self_report",
            _current_value_runtime_only=new_value,
            _old_value_runtime_only=None,
        )

    pattern = _CORRECTION_PATTERNS.get(language)
    matches = list(pattern.finditer(text)) if pattern else []
    if len(matches) != 1:
        return _public_extraction(
            base,
            selected=False,
            status="ambiguous_extraction",
            reason="correction_pair_count_not_one",
            act=act,
            language=language,
            extracted_pair_count=len(matches),
        )
    match = matches[0]
    old_group = (
        match.groupdict().get("old")
        or match.groupdict().get("old_a")
        or match.groupdict().get("old_b")
    )
    old_value = _clean_value(old_group, language)
    new_value = _clean_value(match.group("new"), language)
    if not old_value or not new_value:
        return _public_extraction(
            base,
            selected=False,
            status="ambiguous_extraction",
            reason="empty_correction_value",
            act=act,
            language=language,
        )
    if _normalize(old_value) == _normalize(new_value):
        return _public_extraction(
            base,
            selected=False,
            status="ambiguous_extraction",
            reason="correction_values_not_distinct",
            act=act,
            language=language,
        )
    return _public_extraction(
        base,
        selected=True,
        status="explicit_current_preference_correction_extracted",
        act=act,
        language=language,
        scope=scope,
        scope_source=scope_source,
        previous_value=old_value,
        previous_value_sha256=_digest(_normalize(old_value)),
        current_value=new_value,
        current_value_sha256=_digest(_normalize(new_value)),
        epistemic_status="observed_explicit_user_self_report",
        _current_value_runtime_only=new_value,
        _old_value_runtime_only=old_value,
    )


def current_preference_predicate(scope) -> str:
    normalized = _normalize(scope)
    if not normalized:
        raise ValueError("preference scope is required")
    return f"current_preference_scope:{_digest(normalized)[:16]}"


def _current_preference_rows(collection, *, reference_time):
    candidates = upm.read_profile_candidates(collection)
    resolved = resolve_memory_validity(candidates, reference_time=reference_time)

    def selected(rows):
        return [
            row
            for row in rows
            if (row.get("metadata") or {}).get("preference_semantics_schema") == SEMANTICS_SCHEMA
            and (row.get("metadata") or {}).get("preference_semantics") == "current_preference"
        ]

    return {
        "active": selected(resolved["eligible_candidates"]),
        "historical": selected(resolved["historical_candidates"]),
        "decisions": resolved["decisions"],
    }


def _recent_first(values, value):
    normalized = _normalize(value)
    kept = [item for item in values if _normalize(item) != normalized]
    return [value, *kept][:8]


def _remove_values(values, removed):
    targets = {_normalize(value) for value in removed if _normalize(value)}
    return [item for item in values if _normalize(item) not in targets]


def _typed_record(fact_type, value, *, timestamp, memory_id, extraction, scope, semantics):
    record = upm.compile_profile_memory_record(
        fact_type,
        value,
        timestamp=timestamp,
        memory_id=memory_id,
        typed_state=True,
    )
    metadata = record["metadata"]
    metadata.update(
        {
            "preference_semantics_schema": SEMANTICS_SCHEMA,
            "preference_semantics": semantics,
            "preference_scope": str(scope),
            "preference_scope_sha256": _digest(_normalize(scope)),
            "source_language": extraction["language"],
            "source_input_sha256": extraction["input_sha256"],
            "preference_act": extraction["act"],
            "classifier_cue_id": extraction["classifier_cue_id"],
            "epistemic_status": "observed_explicit_user_self_report",
            "source_kind": "explicit_current_user_utterance",
        }
    )
    if semantics == "current_preference":
        metadata["predicate"] = current_preference_predicate(scope)
        metadata["fact_cardinality"] = "single"
    return record


def remember_explicit_current_preference_p4(memory, user_input, *, timestamp=None):
    """Write the bounded typed state and return a raw-dialogue-free audit."""
    extraction = extract_explicit_current_preference_p4(user_input)
    if not extraction.get("selected"):
        return extraction
    timestamp = timestamp or datetime.datetime.now().astimezone().isoformat(timespec="microseconds")
    before = _current_preference_rows(memory.profile_col, reference_time=timestamp)
    old_value = extraction.pop("_old_value_runtime_only", None)
    new_value = extraction.pop("_current_value_runtime_only")
    scope = extraction["scope"]
    scope_source = extraction["scope_source"]

    old_matches = [
        row
        for row in before["active"]
        if old_value and _normalize((row.get("metadata") or {}).get("value")) == _normalize(old_value)
    ]
    if extraction["act"] == "correction" and scope_source == "default_general":
        inherited_scopes = {
            str((row.get("metadata") or {}).get("preference_scope") or "")
            for row in old_matches
            if str((row.get("metadata") or {}).get("preference_scope") or "")
        }
        if len(inherited_scopes) > 1:
            return {
                **extraction,
                "selected": False,
                "status": "ambiguous_extraction",
                "reason": "old_value_has_multiple_active_scopes",
                "matching_active_old_scope_count": len(inherited_scopes),
            }
        if len(inherited_scopes) == 1:
            scope = next(iter(inherited_scopes))
            scope_source = "inherited_unique_active_old_value"

    same_scope_before = [
        row
        for row in before["active"]
        if _normalize((row.get("metadata") or {}).get("preference_scope")) == _normalize(scope)
    ]
    current_memory_id = str(uuid.uuid4())
    positive = _typed_record(
        "like",
        new_value,
        timestamp=timestamp,
        memory_id=current_memory_id,
        extraction=extraction,
        scope=scope,
        semantics="current_preference",
    )
    previous_current_memory_id = (
        str(same_scope_before[0].get("memory_id")) if len(same_scope_before) == 1 else None
    )
    if previous_current_memory_id:
        positive["metadata"]["previous_current_memory_id"] = previous_current_memory_id
    if old_value:
        positive["metadata"]["previous_value_sha256"] = _digest(_normalize(old_value))

    records = [positive]
    negative_old_memory_id = None
    if old_value:
        negative_old_memory_id = str(uuid.uuid4())
        negative = _typed_record(
            "dislike",
            old_value,
            timestamp=timestamp,
            memory_id=negative_old_memory_id,
            extraction=extraction,
            scope=scope,
            semantics="explicitly_negated_preference",
        )
        negative["metadata"]["correction_current_memory_id"] = current_memory_id
        negative["metadata"]["negated_value_sha256"] = _digest(_normalize(old_value))
        records.append(negative)

    memory.profile_col.add(
        documents=[row["document"] for row in records],
        ids=[row["memory_id"] for row in records],
        metadatas=[row["metadata"] for row in records],
    )

    superseded_values = [
        (row.get("metadata") or {}).get("value")
        for row in same_scope_before
        if (row.get("metadata") or {}).get("value")
    ]
    if old_value:
        superseded_values.append(old_value)
    memory.session_profile["likes"] = _remove_values(
        memory.session_profile.get("likes", []), superseded_values
    )
    memory.session_profile["favorites"] = _remove_values(
        memory.session_profile.get("favorites", []), superseded_values
    )
    memory.session_profile["dislikes"] = _remove_values(
        memory.session_profile.get("dislikes", []), [new_value]
    )
    memory.session_profile["likes"] = _recent_first(memory.session_profile["likes"], new_value)
    if old_value:
        memory.session_profile["dislikes"] = _recent_first(
            memory.session_profile["dislikes"], old_value
        )

    memory._refresh_profile_state_shadow(reference_time=timestamp)
    after = _current_preference_rows(memory.profile_col, reference_time=timestamp)
    active_ids = [str(row.get("memory_id")) for row in after["active"]]
    historical_ids = [str(row.get("memory_id")) for row in after["historical"]]
    prior_ids = [str(row.get("memory_id")) for row in same_scope_before]
    history_preserved = bool(prior_ids) and all(memory_id in historical_ids for memory_id in prior_ids)
    return {
        **extraction,
        "selected": True,
        "status": "typed_current_preference_written",
        "scope": scope,
        "scope_source": scope_source,
        "current_value": new_value,
        "previous_value": old_value,
        "current_memory_id": current_memory_id,
        "previous_current_memory_id": previous_current_memory_id,
        "negative_old_memory_id": negative_old_memory_id,
        "profile_write_count": len(records),
        "active_current_ids": active_ids,
        "historical_current_ids": historical_ids,
        "same_scope_prior_ids": prior_ids,
        "history_preserved": history_preserved,
        "old_records_deleted_or_rewritten": False,
        "episode_write_changed": False,
        "profile_shadow_only": True,
        "answer_use_authorized": False,
        "private_psychological_state_inferred": False,
        "raw_dialogue_persisted": False,
        "claim_boundary": (
            "bounded explicit self-reported current-preference typed state only; "
            "not conversational recall, human-like memory or research advantage"
        ),
    }


def remember_profile_facts_with_current_preference_p4(self, user_input):
    audit = extract_explicit_current_preference_p4(user_input)
    if not audit.get("selected"):
        self._last_multilingual_current_preference_p4 = deepcopy(audit)
        return _ORIGINAL_REMEMBER_PROFILE_FACTS(self, user_input)
    try:
        audit = remember_explicit_current_preference_p4(self, user_input)
    except Exception as exc:
        audit = {
            **audit,
            "selected": False,
            "status": "typed_write_failed",
            "reason": type(exc).__name__,
            "raw_dialogue_persisted": False,
            "answer_use_authorized": False,
        }
        self._last_multilingual_current_preference_p4 = deepcopy(audit)
        return None
    if not audit.get("selected"):
        self._last_multilingual_current_preference_p4 = deepcopy(audit)
        return _ORIGINAL_REMEMBER_PROFILE_FACTS(self, user_input)
    self._last_multilingual_current_preference_p4 = deepcopy(audit)
    return None


def memory_snapshot_with_current_preference_p4(self):
    snapshot = _ORIGINAL_MEMORY_SNAPSHOT(self)
    snapshot[LABEL] = deepcopy(
        getattr(
            self,
            "_last_multilingual_current_preference_p4",
            {
                "schema": SCHEMA,
                "selected": False,
                "status": "not_observed",
                "raw_dialogue_persisted": False,
                "answer_use_authorized": False,
            },
        )
    )
    return snapshot


def materialize_multilingual_current_preference_p4(result):
    memory_runtime = result.get("memory_runtime") or {}
    payload = deepcopy(memory_runtime.get(LABEL) or {})
    trace = result.setdefault("runtime_trace", {})
    rows = [row for row in trace.get("blackboard", []) if row.get("label") != LABEL]
    if payload.get("schema") == SCHEMA and payload.get("status") == "typed_current_preference_written":
        result.setdefault("logic", {})[LABEL] = deepcopy(payload)
        insert_at = next(
            (index + 1 for index, row in enumerate(rows) if row.get("label") == "memory_updates"),
            next((index for index, row in enumerate(rows) if row.get("label") == "utterance"), len(rows)),
        )
        rows.insert(
            insert_at,
            {
                "stage": "memory",
                "label": LABEL,
                "payload": deepcopy(payload),
                "salience": 0.98,
            },
        )
        trace[LABEL] = deepcopy(payload)
    trace["blackboard"] = rows


def install_multilingual_current_preference_p4():
    global _INSTALLED, _ORIGINAL_REMEMBER_PROFILE_FACTS, _ORIGINAL_MEMORY_SNAPSHOT
    global _ORIGINAL_RUN, _ORIGINAL_EMIT
    if _INSTALLED:
        return False
    from uruha_brain_mac import MemoryManager, UruhaBrainV4_Mac
    from uruha_trace_history_sync_m41_1 import sync_current_history_m41_1

    _ORIGINAL_REMEMBER_PROFILE_FACTS = MemoryManager._remember_profile_facts
    _ORIGINAL_MEMORY_SNAPSHOT = MemoryManager.get_runtime_snapshot
    _ORIGINAL_RUN = UruhaBrainV4_Mac.run_turn_debug
    _ORIGINAL_EMIT = UruhaBrainV4_Mac.emit_response_if_ready
    MemoryManager._remember_profile_facts = remember_profile_facts_with_current_preference_p4
    MemoryManager.get_runtime_snapshot = memory_snapshot_with_current_preference_p4

    def finish(self, result):
        materialize_multilingual_current_preference_p4(result)
        self.runtime.blackboard = deepcopy(result["runtime_trace"]["blackboard"])
        sync_current_history_m41_1(result)
        if (
            self.runtime.turn_traces
            and self.runtime.turn_traces[-1].get("cycle_index")
            == result["runtime_trace"].get("cycle_index")
        ):
            self.runtime.turn_traces[-1] = deepcopy(result["runtime_trace"])
        return result

    def run(self, user_input, input_context=None):
        return finish(self, _ORIGINAL_RUN(self, user_input, input_context=input_context))

    def emit(self, event, tick_result):
        return finish(self, _ORIGINAL_EMIT(self, event, tick_result))

    UruhaBrainV4_Mac.run_turn_debug = run
    UruhaBrainV4_Mac.emit_response_if_ready = emit
    _INSTALLED = True
    return True
