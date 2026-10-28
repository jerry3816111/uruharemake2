"""Product-only Japanese free-text instruction for an eligible M46 review.

The released P4 candidate adapter owns route/source eligibility and its
per-turn ContextVar. This adapter changes only the instruction on the
existing M46 review call; M46's verifier and model transport remain unchanged.
"""

from __future__ import annotations

import hashlib

import uruha_actionable_help_delivery_m45 as action45
import uruha_goal_progress_delivery_m46 as m46
import uruha_source_bound_candidate_prompt_p4 as candidate_adapter


LABEL = "reviewer_japanese_counterfactual_prompt_p4"
_BASE_REVIEW_SYSTEM = m46.REVIEW_SYSTEM
_REVIEWER_JAPANESE_AMENDMENT = """

CROSS-LINGUAL REVIEW FREE-TEXT BOUNDARY: Copy source_id and source_span byte-
exactly from the allowed source, even if that source is Chinese or English.
Only counterfactual_before_jp and counterfactual_after_jp are generated
free-text fields here: write both as concise, natural JAPANESE sentences with
Japanese grammatical material, even when the source is Chinese or English.
Do not put Chinese or English explanatory text in those two fields. Keep
observed_progress_mechanism as its exact schema enum in English, and keep
content_checks and surface_checks as JSON booleans. Do not translate or
replace the source span. Do not invent a before-state fact, hidden preference,
or after-state guarantee not supported by the source and action. If the
causal change is not supportable, mark its relevant content check false;
never change a false check to true merely to pass the review."""
REVIEWER_JAPANESE_SYSTEM = _BASE_REVIEW_SYSTEM + _REVIEWER_JAPANESE_AMENDMENT

_INSTALLED = False
_PRIOR_NATIVE_JSON = None


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _review_schema(schema) -> bool:
    if not isinstance(schema, dict):
        return False
    properties = schema.get("properties")
    if not isinstance(properties, dict):
        return False
    return all(
        isinstance(properties.get(key), dict)
        and properties[key].get("type") == "string"
        for key in ("counterfactual_before_jp", "counterfactual_after_jp")
    )


def reviewer_native_json_p4(system, payload, schema, deadline, metrics):
    """Substitute one reviewer instruction; keep other call arguments exact."""
    context = candidate_adapter._CONTEXT.get()
    if (
        isinstance(context, dict)
        and context.get("eligible") is True
        and context.get("applied") is True
        and system == _BASE_REVIEW_SYSTEM
        and m46.REVIEW_SYSTEM == _BASE_REVIEW_SYSTEM
        and _review_schema(schema)
    ):
        system = REVIEWER_JAPANESE_SYSTEM
        if isinstance(metrics, dict):
            metrics[LABEL] = {
                "schema": "uruha_reviewer_japanese_counterfactual_p4",
                "applied": True,
                "old_instruction_sha256": _digest(_BASE_REVIEW_SYSTEM),
                "new_instruction_sha256": _digest(REVIEWER_JAPANESE_SYSTEM),
                "model_calls_added": 0,
                "raw_review_text_persisted": False,
                "long_term_memory_write": False,
                "claim_boundary": (
                    "M46 reviewer instruction only; old verifier and actual "
                    "delivery decision remain authoritative"
                ),
            }
    return _PRIOR_NATIVE_JSON(system, payload, schema, deadline, metrics)


def installed_reviewer_japanese_counterfactual_p4() -> bool:
    """Sandbox preflight checks live identity and the old adapter boundary."""
    return bool(
        _INSTALLED
        and candidate_adapter.installed_source_bound_candidate_prompt_p4()
        and action45._native_json is reviewer_native_json_p4
        and m46.REVIEW_SYSTEM == _BASE_REVIEW_SYSTEM
    )


def install_reviewer_japanese_counterfactual_p4() -> bool:
    """Install after the released candidate adapter without wrapping delivery."""
    global _INSTALLED, _PRIOR_NATIVE_JSON
    if _INSTALLED:
        if not installed_reviewer_japanese_counterfactual_p4():
            raise RuntimeError("p4_reviewer_japanese_counterfactual_overwritten")
        return False
    if not candidate_adapter.installed_source_bound_candidate_prompt_p4():
        raise RuntimeError("p4_source_bound_candidate_adapter_required")
    if m46.REVIEW_SYSTEM != _BASE_REVIEW_SYSTEM:
        raise RuntimeError("p4_m46_reviewer_instruction_changed")
    _PRIOR_NATIVE_JSON = action45._native_json
    if _PRIOR_NATIVE_JSON is reviewer_native_json_p4:
        raise RuntimeError("p4_reviewer_japanese_counterfactual_duplicate_install")
    action45._native_json = reviewer_native_json_p4
    _INSTALLED = True
    return True


__all__ = [
    "LABEL", "REVIEWER_JAPANESE_SYSTEM", "reviewer_native_json_p4",
    "install_reviewer_japanese_counterfactual_p4",
    "installed_reviewer_japanese_counterfactual_p4",
]
