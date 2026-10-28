"""Product-only canonical scope projection for explicit P4-I preference writes.

P4-I deliberately preserved the extracted surface scope.  P4-J deliberately
queries one canonical scope.  P4-L joins only three prospectively frozen,
already-extractable drink aliases without changing value extraction, query
classification, answer authority, or any frozen research entrypoint.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import unicodedata

import uruha_multilingual_current_preference_p4 as p4i


LABEL = "preference_scope_canonicalization_p4"
SCHEMA = "uruha_preference_scope_canonicalization_p4"
_INSTALLED = False
_ORIGINAL_EXTRACT = None
_ORIGINAL_TYPED_RECORD = None
_ORIGINAL_RUN = None
_ORIGINAL_EMIT = None

_ALIASES = {
    ("zh", "飲料"): ("drink", "drink:zh-Hant:v1"),
    ("zh", "饮料"): ("drink", "drink:zh-Hans:v1"),
    ("ja", "飲み物"): ("drink", "drink:ja:v1"),
}


def _digest(value) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def _exact_surface(value) -> str:
    return unicodedata.normalize("NFKC", str(value or "")).strip()


def _audit(*, applied, reason, extraction, alias_id=None, source_scope=None, canonical=None):
    return {
        "schema": SCHEMA,
        "canonicalization_applied": bool(applied),
        "status": "canonical_scope_projected" if applied else "not_applied",
        "reason": reason,
        "alias_id": alias_id,
        "source_scope_alias_sha256": _digest(source_scope) if applied else None,
        "canonical_scope": canonical if applied else None,
        "source_language": extraction.get("language"),
        "source_input_sha256": extraction.get("input_sha256"),
        "source_scope_source": extraction.get("scope_source"),
        "value_sha256": extraction.get("current_value_sha256"),
        "model_call_added": False,
        "answer_use_authorized": False,
        "raw_dialogue_persisted": False,
        "raw_scope_alias_persisted": False,
        "claim_boundary": (
            "bounded exact explicit-scope alias projection; not open-domain ontology "
            "alignment, preference inference or answer authority"
        ),
    }


def canonicalize_preference_scope_extraction_p4(extraction):
    """Return a copy with one frozen exact alias projected to canonical scope."""
    result = deepcopy(extraction or {})
    if result.get("schema") != p4i.SCHEMA:
        result[LABEL] = _audit(
            applied=False,
            reason="not_a_p4_i_extraction",
            extraction=result,
        )
        return result
    if not result.get("selected"):
        result[LABEL] = _audit(
            applied=False,
            reason="p4_i_not_selected",
            extraction=result,
        )
        return result
    if result.get("scope_source") != "explicit_utterance":
        result[LABEL] = _audit(
            applied=False,
            reason="scope_not_explicit",
            extraction=result,
        )
        return result

    language = str(result.get("language") or "")
    source_scope = _exact_surface(result.get("scope"))
    mapped = _ALIASES.get((language, source_scope))
    if not mapped:
        result[LABEL] = _audit(
            applied=False,
            reason="scope_alias_not_in_frozen_table",
            extraction=result,
        )
        return result

    canonical_scope, alias_id = mapped
    result["scope"] = canonical_scope
    result["scope_source"] = "canonical_alias_projection"
    result[LABEL] = _audit(
        applied=True,
        reason="exact_language_and_scope_alias_match",
        extraction=extraction,
        alias_id=alias_id,
        source_scope=source_scope,
        canonical=canonical_scope,
    )
    return result


def extract_with_preference_scope_canonicalization_p4(user_input):
    extraction = _ORIGINAL_EXTRACT(user_input)
    return canonicalize_preference_scope_extraction_p4(extraction)


def typed_record_with_preference_scope_canonicalization_p4(
    fact_type,
    value,
    *,
    timestamp,
    memory_id,
    extraction,
    scope,
    semantics,
):
    record = _ORIGINAL_TYPED_RECORD(
        fact_type,
        value,
        timestamp=timestamp,
        memory_id=memory_id,
        extraction=extraction,
        scope=scope,
        semantics=semantics,
    )
    audit = extraction.get(LABEL) or {}
    if audit.get("schema") == SCHEMA and audit.get("canonicalization_applied") is True:
        record["metadata"].update(
            {
                "preference_scope_canonicalization_schema": SCHEMA,
                "preference_scope_canonicalization_applied": True,
                "preference_scope_alias_id": audit["alias_id"],
                "preference_source_scope_sha256": audit["source_scope_alias_sha256"],
            }
        )
    return record


def materialize_preference_scope_canonicalization_p4(result):
    p4_i_payload = deepcopy(
        (result.get("logic") or {}).get(p4i.LABEL)
        or (result.get("memory_runtime") or {}).get(p4i.LABEL)
        or {}
    )
    audit = deepcopy(p4_i_payload.get(LABEL) or {})
    trace = result.setdefault("runtime_trace", {})
    rows = [row for row in trace.get("blackboard", []) if row.get("label") != LABEL]
    if audit.get("schema") == SCHEMA and audit.get("canonicalization_applied") is True:
        audit["current_memory_id"] = p4_i_payload.get("current_memory_id")
        audit["canonical_scope"] = p4_i_payload.get("scope")
        audit["source_language"] = p4_i_payload.get("language")
        audit["raw_dialogue_persisted"] = False
        audit["raw_scope_alias_persisted"] = False
        result.setdefault("logic", {})[LABEL] = deepcopy(audit)
        insert_at = next(
            (index + 1 for index, row in enumerate(rows) if row.get("label") == p4i.LABEL),
            next((index for index, row in enumerate(rows) if row.get("label") == "utterance"), len(rows)),
        )
        rows.insert(
            insert_at,
            {
                "stage": "memory",
                "label": LABEL,
                "payload": deepcopy(audit),
                "salience": 0.98,
            },
        )
        trace[LABEL] = deepcopy(audit)
    trace["blackboard"] = rows


def install_preference_scope_canonicalization_p4():
    global _INSTALLED, _ORIGINAL_EXTRACT, _ORIGINAL_TYPED_RECORD, _ORIGINAL_RUN, _ORIGINAL_EMIT
    if _INSTALLED:
        return False
    from uruha_brain_mac import UruhaBrainV4_Mac
    from uruha_trace_history_sync_m41_1 import sync_current_history_m41_1

    _ORIGINAL_EXTRACT = p4i.extract_explicit_current_preference_p4
    _ORIGINAL_TYPED_RECORD = p4i._typed_record
    _ORIGINAL_RUN = UruhaBrainV4_Mac.run_turn_debug
    _ORIGINAL_EMIT = UruhaBrainV4_Mac.emit_response_if_ready
    p4i.extract_explicit_current_preference_p4 = extract_with_preference_scope_canonicalization_p4
    p4i._typed_record = typed_record_with_preference_scope_canonicalization_p4

    def finish(self, result):
        materialize_preference_scope_canonicalization_p4(result)
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
