"""Additive P4-N surface adapter for bounded Japanese typed values.

P4-J remains byte-for-byte bound to its released evidence.  This adapter is
installed after P4-J and only upgrades its unsupported-value abstention when
the unique active record is an explicit Japanese self-report and the value is
a short, punctuation-free Japanese-script surface.
"""

from __future__ import annotations

from copy import deepcopy
import re
import unicodedata

import uruha_multilingual_current_preference_p4 as p4i
import uruha_typed_current_preference_recall_p4 as p4j


LABEL = "source_bound_japanese_value_surface_p4"
SCHEMA = "uruha_source_bound_japanese_value_surface_p4"
_INSTALLED = False
_BASE_BUILD = p4j.build_typed_current_preference_recall_contract_p4
_SAFE_JAPANESE_VALUE = re.compile(
    r"^[\u3041-\u3096\u309d\u309e\u30a1-\u30fa\u30fd\u30fe"
    r"\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaffー・]+$"
)
_MAX_CODEPOINTS = 24


def _bounded_identity_value(value, metadata):
    provenance = dict(metadata or {})
    if provenance.get("source_language") != "ja":
        return ""
    if provenance.get("source_kind") != "explicit_current_user_utterance":
        return ""
    if provenance.get("epistemic_status") != "observed_explicit_user_self_report":
        return ""
    if provenance.get("preference_semantics_schema") != p4i.SEMANTICS_SCHEMA:
        return ""
    if provenance.get("preference_semantics") != "current_preference":
        return ""
    if not provenance.get("source_input_sha256") or not provenance.get(
        "preference_scope_sha256"
    ):
        return ""

    text = unicodedata.normalize("NFKC", str(value or ""))
    if not 1 <= len(text) <= _MAX_CODEPOINTS:
        return ""
    if text != text.strip():
        return ""
    if not _SAFE_JAPANESE_VALUE.fullmatch(text):
        return ""
    return text


def _upgrade_unsupported_contract(base, profile_collection, *, reference_time=None):
    if base.get("status") != "unsupported_active_value_localization":
        result = deepcopy(base)
        if result.get("status") == "resolved_unique_active_typed_current_preference":
            result.update(
                value_surface_strategy="finite_localization_map",
                identity_localization_applied=False,
            )
        return result

    resolved = p4i._current_preference_rows(
        profile_collection,
        reference_time=reference_time,
    )
    scope = base.get("scope")
    rows = [
        row
        for row in resolved.get("active") or []
        if p4j._normalize((row.get("metadata") or {}).get("preference_scope"))
        == p4j._normalize(scope)
    ]
    if len(rows) != 1:
        return deepcopy(base)
    row = rows[0]
    metadata = dict(row.get("metadata") or {})
    memory_id = str(row.get("memory_id") or "")
    localized = _bounded_identity_value(metadata.get("value"), metadata)
    if not memory_id or not localized:
        return deepcopy(base)

    scope_jp = base["scope_surface_jp"]
    surface = f"今の{scope_jp}の好みは{localized}。前のじゃなくて、今の方ね。"
    result = deepcopy(base)
    result.update(
        status="resolved_unique_active_typed_current_preference",
        reason="one_active_exact_scope_p4_i_record_with_source_bound_japanese_identity",
        surface_authority=True,
        answer_use_authorized=True,
        candidate_count=1,
        active_memory_id=memory_id,
        active_memory_ids=[memory_id],
        source_language=metadata["source_language"],
        source_input_sha256=metadata["source_input_sha256"],
        preference_scope_sha256=metadata["preference_scope_sha256"],
        validity_reason=(resolved.get("decisions") or {}).get(memory_id, {}).get(
            "reason", "active"
        ),
        value_sha256=p4j._digest(p4j._normalize(metadata["value"])),
        localized_value_jp=localized,
        localized_value_jp_sha256=p4j._digest(localized),
        value_surface_strategy="bounded_japanese_identity",
        identity_localization_applied=True,
        selected_core_jp=surface,
        selected_core_sha256=p4j._digest(surface),
        historical_answer_use_count=0,
        explicit_negative_answer_use_count=0,
        episode_answer_use_count=0,
        profile_write_count=0,
        episode_write_changed=False,
        model_call_added=False,
        private_state_truth_claimed=False,
        claim_boundary=(
            "one active explicit Japanese P4-I typed current preference with a bounded "
            "Japanese-script identity surface; not arbitrary echoing, translation, "
            "open-domain recall or general profile answer authority"
        ),
    )
    result[LABEL] = {
        "schema": SCHEMA,
        "status": "bounded_japanese_identity_authorized",
        "source_language": "ja",
        "source_kind": "explicit_current_user_utterance",
        "epistemic_status": "observed_explicit_user_self_report",
        "maximum_codepoints": _MAX_CODEPOINTS,
        "normalized_codepoint_count": len(localized),
        "ascii_letters_allowed": False,
        "ascii_digits_allowed": False,
        "spaces_allowed": False,
        "control_characters_allowed": False,
        "sentence_punctuation_allowed": False,
        "raw_dialogue_persisted": False,
        "model_call_added": False,
        "claim_boundary": (
            "bounded source-provenance Japanese identity surface only; not arbitrary echoing"
        ),
    }
    return result


def build_source_bound_japanese_value_surface_p4(
    user_input, profile_collection, *, reference_time=None
):
    base = _BASE_BUILD(
        user_input,
        profile_collection,
        reference_time=reference_time,
    )
    return _upgrade_unsupported_contract(
        base,
        profile_collection,
        reference_time=reference_time,
    )


def install_source_bound_japanese_value_surface_p4():
    global _INSTALLED
    if _INSTALLED:
        return False
    p4j.build_typed_current_preference_recall_contract_p4 = (
        build_source_bound_japanese_value_surface_p4
    )
    _INSTALLED = True
    return True
