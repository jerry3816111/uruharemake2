"""Fail-closed bridge from the 2026 Task A framing to frozen M55/M56.

This module deliberately does not read target datasets, construct model prompts,
run a model, or open an outcome key.  It only verifies that the new research
framing maps to the already frozen temporal comparison machinery without
silently weakening its information, resource, or blinding boundaries.
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "p3_b51_temporal_forecast_bridge_v1.json"


def _canonical_json(value):
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _sha256_bytes(payload):
    return hashlib.sha256(payload).hexdigest()


def _load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_bridge_contract():
    return _load_json(CONFIG_PATH)


def _condition_map(preflight):
    return {
        str(row.get("condition_id")): row
        for row in preflight.get("conditions", [])
        if isinstance(row, dict)
    }


def validate_temporal_forecast_bridge(contract=None, *, root=ROOT):
    """Validate bindings and experimental equivalence without outcome access."""
    root = Path(root)
    contract = deepcopy(contract or load_bridge_contract())
    errors = []
    checks = {}

    expected_schema = "uruha_p3_b51_temporal_forecast_bridge_v1"
    checks["bridge_schema"] = contract.get("schema") == expected_schema
    if not checks["bridge_schema"]:
        errors.append("bridge_schema_mismatch")

    loaded = {}
    for binding_id, binding in (contract.get("bindings") or {}).items():
        relative = str((binding or {}).get("path") or "")
        expected_hash = str((binding or {}).get("sha256") or "")
        path = root / relative
        if not relative or not path.is_file():
            errors.append(f"binding_missing:{binding_id}")
            continue
        actual_hash = _sha256_bytes(path.read_bytes())
        if actual_hash != expected_hash:
            errors.append(f"binding_hash_mismatch:{binding_id}")
            continue
        if path.suffix == ".json":
            loaded[binding_id] = _load_json(path)

    required_bindings = {
        "temporal_row_contract",
        "fair_comparison_preflight",
        "blinded_execution_capsule_freeze",
        "pre_outcome_equation_artifacts",
        "related_work_map",
    }
    checks["all_bindings_content_addressed"] = not any(
        error.startswith("binding_") for error in errors
    ) and required_bindings.issubset(set((contract.get("bindings") or {}).keys()))

    temporal = loaded.get("temporal_row_contract") or {}
    preflight = loaded.get("fair_comparison_preflight") or {}
    capsule = loaded.get("blinded_execution_capsule_freeze") or {}
    equation = loaded.get("pre_outcome_equation_artifacts") or {}
    conditions = _condition_map(preflight)

    mapping = contract.get("task_a_condition_mapping") or []
    mapped_roles = {
        str(row.get("task_a_role")): str(row.get("m56_condition_id"))
        for row in mapping
        if isinstance(row, dict)
    }
    expected_mapping = {
        "current_context_only": "B1_BASE_LLM",
        "persona_prompt": "B2_PERSONA_PROMPT",
        "retrieved_public_history": "B3_RAG",
        "strong_same_information_control": "B5_STRUCTURED_HISTORY",
        "full_person_state_system": "OURS_HYBRID",
    }
    checks["task_a_conditions_map_exactly"] = mapped_roles == expected_mapping
    if not checks["task_a_conditions_map_exactly"]:
        errors.append("task_a_condition_mapping_mismatch")
    checks["mapped_conditions_exist"] = all(
        condition_id in conditions for condition_id in expected_mapping.values()
    )
    if not checks["mapped_conditions_exist"]:
        errors.append("mapped_condition_missing")

    temporal_boundary = temporal.get("temporal_boundary") or {}
    checks["strict_pre_outcome_cutoff"] = bool(
        "prediction_cutoff_seconds < observable_behavior_start_seconds"
        in (temporal_boundary.get("required_order") or [])
        and temporal_boundary.get("current_outcome_may_enter_model_input") is False
    )
    if not checks["strict_pre_outcome_cutoff"]:
        errors.append("strict_pre_outcome_cutoff_missing")

    blinding = preflight.get("blinding") or {}
    checks["outcome_blinded_until_commitment"] = bool(
        blinding.get("generation_process_receives_outcome_key") is False
        and blinding.get("all_condition_predictions_committed_before_scoring") is True
        and blinding.get("outcome_join_only_in_separate_scorer") is True
    )
    if not checks["outcome_blinded_until_commitment"]:
        errors.append("outcome_commitment_boundary_missing")

    controls = preflight.get("model_and_resource_controls") or {}
    checks["same_model_and_measured_resources"] = bool(
        controls.get("same_model_artifact_for_B1_through_B5_and_Ours") is True
        and controls.get(
            "actual_prompt_completion_tokens_latency_and_peak_memory_reported_by_condition"
        )
        is True
        and controls.get("retry_policy") == "no_retry_no_condition_fallback"
    )
    if not checks["same_model_and_measured_resources"]:
        errors.append("matched_model_or_resource_control_missing")

    primary = preflight.get("primary_contrast") or {}
    checks["same_information_primary_contrast"] = bool(
        primary.get("control") == "B5_STRUCTURED_HISTORY"
        and primary.get("system") == "OURS_HYBRID"
        and primary.get("same_pre_cutoff_source_information") is True
    )
    if not checks["same_information_primary_contrast"]:
        errors.append("same_information_primary_contrast_missing")

    metrics = preflight.get("metrics") or {}
    checks["proper_probability_scoring"] = set(metrics.get("co_primary") or []) == {
        "paired_brier_delta_ours_minus_b5",
        "paired_nll_delta_ours_minus_b5",
    }
    if not checks["proper_probability_scoring"]:
        errors.append("proper_probability_scoring_missing")

    success = preflight.get("success_and_failure") or {}
    checks["negative_result_retained"] = success.get("negative_result_retained") is True
    if not checks["negative_result_retained"]:
        errors.append("negative_result_retention_missing")

    equation_auth = equation.get("authorization") or {}
    checks["equation_artifacts_remain_pre_outcome"] = bool(
        equation_auth.get("current_target_outcome_access") is False
        and equation_auth.get("current_formal_model_execution") is False
        and (equation.get("fit") or {}).get("current_sample_outcome_allowed") is False
        and (equation.get("state") or {}).get("unknown_may_be_imputed") is False
    )
    if not checks["equation_artifacts_remain_pre_outcome"]:
        errors.append("pre_outcome_equation_boundary_missing")

    related = contract.get("related_work_inputs") or []
    checks["primary_2026_sources_present"] = bool(
        len(related) >= 6
        and all(
            str(row.get("primary_url") or "").startswith("https://")
            and str(row.get("adopted_scope") or "").strip()
            for row in related
            if isinstance(row, dict)
        )
        and len([row for row in related if isinstance(row, dict)]) == len(related)
    )
    if not checks["primary_2026_sources_present"]:
        errors.append("primary_2026_source_map_incomplete")

    boundary = contract.get("execution_boundary") or {}
    checks["bridge_authorizes_no_execution"] = all(
        boundary.get(name) is False
        for name in (
            "model_calls_authorized",
            "target_outcome_access_authorized",
            "new_source_selection_authorized",
            "production_memory_write_authorized",
            "external_deployment_authorized",
        )
    )
    if not checks["bridge_authorizes_no_execution"]:
        errors.append("bridge_execution_boundary_open")

    live = contract.get("expected_live_status") or {}
    checks["formal_result_still_absent"] = bool(
        live.get("real_temporal_rows") == 0
        and live.get("formal_model_calls") == 0
        and live.get("formal_result_created") is False
        and live.get("formal_execution_blocked") is True
        and (capsule.get("pre_freeze_evidence") or {}).get("formal_result_created")
        is False
    )
    if not checks["formal_result_still_absent"]:
        errors.append("formal_status_overclaimed")

    return {
        "schema": "uruha_p3_b51_temporal_forecast_bridge_audit_v1",
        "valid": not errors and all(checks.values()),
        "checks": checks,
        "errors": errors,
        "mapped_condition_count": len(mapped_roles),
        "related_work_count": len(related),
        "formal_model_calls": 0,
        "target_outcome_access": 0,
        "new_source_selected": False,
        "formal_result_created": False,
        "next_gate": "prospectively_select_and_freeze_one_new_public_source_without_opening_its_future_response",
        "audit_hash": _sha256_bytes(_canonical_json(checks).encode("utf-8")),
        "claim_boundary": (
            "A valid bridge proves protocol reuse and scope alignment only; it "
            "does not prove prediction quality or a human-response equation."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(validate_temporal_forecast_bridge(), ensure_ascii=False, indent=2))
