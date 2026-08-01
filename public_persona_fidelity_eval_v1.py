#!/usr/bin/env python3
"""Validate the public-persona fidelity evaluation protocol and readiness."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import NormalDist, median


ROOT = Path(__file__).resolve().parent
DEFAULT_PREREGISTRATION = (
    ROOT / "configs/public_persona_fidelity_eval_v1_preregistration.json"
)
DEFAULT_METHOD_REGISTRY = (
    ROOT / "configs/public_persona_fidelity_eval_v1_method_registry.json"
)
DEFAULT_READINESS_INVENTORY = (
    ROOT / "datasets/public_persona_fidelity_eval_v1_readiness_inventory.json"
)
DEFAULT_OUTPUT_JSON = ROOT / "reports/public_persona_fidelity_eval_v1_construction.json"
DEFAULT_OUTPUT_MD = ROOT / "reports/public_persona_fidelity_eval_v1_construction.md"

PREREGISTRATION_SCHEMA = "uruha_public_persona_fidelity_eval_preregistration_v1"
METHOD_REGISTRY_SCHEMA = "uruha_public_persona_fidelity_method_registry_v1"
READINESS_SCHEMA = "uruha_public_persona_fidelity_readiness_inventory_v1"
EXPERIMENT_ID = "public_persona_fidelity_eval_v1"
TARGET_ID = "ichinose_uruha_public_persona"
PROTOCOL_PASS_DECISION = (
    "authorize_provenance_only_reference_manifest_and_consented_rater_protocol_construction"
)
PROTOCOL_FAIL_DECISION = (
    "repair_fidelity_protocol_before_collecting_or_scoring_persona_data"
)
PILOT_READY_DECISION = "authorize_a_separately_preregistered_pilot_only"

EXPECTED_DEPENDENCIES = {
    "configs/public_persona_evidence_v1_result_lock.json": (
        "public_persona_evidence_contract_v1",
        "authorize_public_persona_development_hypotheses_only",
    ),
    "configs/public_persona_observation_v2_result_lock.json": (
        "public_persona_observation_protocol_v2",
        "authorize_conditional_persona_development_hypotheses_and_sealed_holdout_protocol_only",
    ),
}
EXPECTED_CONDITIONS = {
    "s0_full_cognitive_persona",
    "c1_matched_prompt_only",
    "c2_matched_persona_disabled",
}
EXPECTED_EVALUATION_FAMILIES = {
    "naturalistic_masked_continuation",
    "counterfactual_unseen_open_scenarios",
    "dynamic_multi_turn_episodes",
}
EXPECTED_TARGET_DIMENSIONS = {
    "situation_interpretation_and_response_stance",
    "dialogue_act_social_distance_and_relationship_response",
    "wording_rhythm_directness_humor_and_affect",
    "publicly_observable_preferences_values_and_action_choices",
    "memory_selection_experience_update_and_reflection",
    "uncertainty_private_information_and_unsupported_claim_restraint",
}
EXPECTED_METHOD_IDS = {
    "incharacter_acl_2024",
    "charactereval_acl_2024",
    "personagym_emnlp_2025",
    "emocharacter_naacl_2025",
    "raven_tacl_2024",
}
REQUIRED_CONTROLS = {
    "base_local_model_and_quantization",
    "hardware_and_ollama_version",
    "input_scenario_and_dialogue_history",
    "development_persona_information_content_for_s0_and_c1",
    "total_context_token_budget",
    "generation_token_budget",
    "temperature_top_p_seed_and_stop_rules",
    "memory_initial_state",
    "Function_Calling_and_VRM_action_permissions",
    "blind_assignment_and_response_order_seed",
}
REQUIRED_NON_REGRESSION_MARGINS = {
    "semantic_correctness_pp_min",
    "reasoning_correctness_pp_min",
    "memory_correctness_pp_min",
    "unknown_refusal_pp_min",
    "response_diversity_relative_min",
    "latency_relative_max",
    "peak_memory_relative_max",
    "new_unsafe_action_count_max",
}
READINESS_COUNT_MAP = {
    "target_development_observation_count_min": "target_development_observation_count",
    "target_calibration_source_count_min": "target_calibration_source_count",
    "target_calibration_event_count_min": "target_calibration_event_count",
    "target_final_holdout_source_count_min": "target_final_holdout_source_count",
    "target_final_holdout_event_count_min": "target_final_holdout_event_count",
    "matched_contrast_person_count_min": "matched_contrast_person_count",
    "contrast_event_count_per_person_min": "contrast_event_count_per_person_min",
    "same_topic_reference_pair_count_min": "same_topic_reference_pair_count",
    "counterfactual_final_scenario_count_min": "counterfactual_final_scenario_count",
    "dynamic_multi_turn_episode_count_min": "dynamic_multi_turn_episode_count",
    "target_familiar_final_rater_count_min": "target_familiar_final_rater_count",
    "general_japanese_final_rater_count_min": "general_japanese_final_rater_count",
    "ratings_per_item_min": "ratings_per_item_min",
}
READINESS_FLAG_MAP = {
    "pilot_completed_required": "pilot_completed",
    "power_plan_frozen_required": "power_plan_frozen",
    "runtime_manifest_frozen_required": "runtime_manifest_frozen",
    "source_rights_review_complete_required": (
        "source_rights_review_complete_for_formal_corpus"
    ),
    "holdout_access_log_ready_required": "holdout_access_log_ready",
}
EVIDENCE_BINDING_REQUIREMENTS = {
    "target_calibration_source_count": "target_calibration_manifest",
    "target_calibration_event_count": "target_calibration_manifest",
    "target_final_holdout_source_count": "target_final_holdout_manifest",
    "target_final_holdout_event_count": "target_final_holdout_manifest",
    "matched_contrast_person_count": "contrast_reference_manifest",
    "contrast_event_count_per_person_min": "contrast_reference_manifest",
    "same_topic_reference_pair_count": "same_topic_reference_manifest",
    "counterfactual_final_scenario_count": "counterfactual_scenario_manifest",
    "dynamic_multi_turn_episode_count": "dynamic_episode_manifest",
    "target_familiar_final_rater_count": "rater_manifest",
    "general_japanese_final_rater_count": "rater_manifest",
    "ratings_per_item_min": "rater_manifest",
}
PROHIBITED_AUTHORIZATIONS = {
    "runtime_persona_activation",
    "model_execution",
    "prompt_change",
    "model_training",
    "sealed_holdout_unsealing",
    "formal_persona_scoring",
    "public_persona_fidelity_claim",
    "private_person_copy_claim",
}
EXPECTED_READINESS_FLAGS = {
    "pilot_completed",
    "power_plan_frozen",
    "runtime_manifest_frozen",
    "source_rights_review_complete_for_formal_corpus",
    "holdout_access_log_ready",
    "formal_execution_ready",
    "persona_fidelity_claim_available",
}


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _display_path(path):
    path = Path(path).resolve()
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _finite_number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


def _reference_median(values, name):
    numbers = [_finite_number(value, name) for value in values]
    if not numbers:
        raise ValueError(f"{name} must not be empty")
    return float(median(numbers))


def calibrated_similarity(
    agent_target_similarity,
    target_target_similarities,
    other_target_similarities,
):
    """Place agent-target similarity between the other-target floor and target self-range."""

    agent = _finite_number(agent_target_similarity, "agent_target_similarity")
    target = _reference_median(
        target_target_similarities, "target_target_similarities"
    )
    other = _reference_median(
        other_target_similarities, "other_target_similarities"
    )
    denominator = target - other
    if denominator <= 0:
        raise ValueError("similarity reference denominator must be positive")
    return (agent - other) / denominator


def calibrated_distance(
    agent_target_distance,
    target_target_distances,
    other_target_distances,
):
    """Place agent-target distance between the other-target floor and target self-range."""

    agent = _finite_number(agent_target_distance, "agent_target_distance")
    target = _reference_median(target_target_distances, "target_target_distances")
    other = _reference_median(other_target_distances, "other_target_distances")
    denominator = other - target
    if denominator <= 0:
        raise ValueError("distance reference denominator must be positive")
    return (other - agent) / denominator


def wilson_interval(successes, trials, confidence=0.95):
    """Return a two-sided Wilson score interval for a binomial proportion."""

    if isinstance(successes, bool) or isinstance(trials, bool):
        raise TypeError("successes and trials must be integers")
    if not isinstance(successes, int) or not isinstance(trials, int):
        raise TypeError("successes and trials must be integers")
    confidence = _finite_number(confidence, "confidence")
    if trials <= 0 or successes < 0 or successes > trials:
        raise ValueError("require 0 <= successes <= trials and trials > 0")
    if not 0 < confidence < 1:
        raise ValueError("confidence must be between zero and one")
    z = NormalDist().inv_cdf(1 - (1 - confidence) / 2)
    proportion = successes / trials
    denominator = 1 + z * z / trials
    center = (proportion + z * z / (2 * trials)) / denominator
    half_width = (
        z
        * math.sqrt(
            proportion * (1 - proportion) / trials
            + z * z / (4 * trials * trials)
        )
        / denominator
    )
    return max(0.0, center - half_width), min(1.0, center + half_width)


def pairwise_preference_summary(s0_wins, control_wins, ties):
    for name, value in (
        ("s0_wins", s0_wins),
        ("control_wins", control_wins),
        ("ties", ties),
    ):
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(f"{name} must be an integer")
        if value < 0:
            raise ValueError(f"{name} must be non-negative")
    total = s0_wins + control_wins + ties
    non_tie = s0_wins + control_wins
    if total <= 0 or non_tie <= 0:
        raise ValueError("at least one non-tie judgment is required")
    lower, upper = wilson_interval(s0_wins, non_tie)
    return {
        "judgment_count": total,
        "non_tie_count": non_tie,
        "s0_non_tie_win_rate": s0_wins / non_tie,
        "s0_tie_adjusted_win_rate": (s0_wins + 0.5 * ties) / total,
        "s0_non_tie_wilson_95_ci": [lower, upper],
    }


def _validate_binding(binding, root):
    if not isinstance(binding, dict):
        return False
    path_value = str(binding.get("path") or "")
    expected_hash = str(binding.get("sha256") or "")
    if not path_value or len(expected_hash) != 64:
        return False
    path = root / path_value
    return path.is_file() and sha256_file(path) == expected_hash


def audit(preregistration, method_registry, readiness, dependency_results, root=ROOT):
    violations = defaultdict(list)

    if preregistration.get("schema") != PREREGISTRATION_SCHEMA:
        violations["preregistration"].append("schema")
    if preregistration.get("experiment_id") != EXPERIMENT_ID:
        violations["preregistration"].append("experiment_id")
    if preregistration.get("target_id") != TARGET_ID:
        violations["preregistration"].append("target_id")
    if not str(preregistration.get("research_question") or "").strip():
        violations["preregistration"].append("research_question")
    if not str(preregistration.get("falsifiable_hypothesis") or "").strip():
        violations["preregistration"].append("falsifiable_hypothesis")
    if not str(preregistration.get("single_changed_variable") or "").strip():
        violations["preregistration"].append("single_changed_variable")

    dependencies = preregistration.get("depends_on") or []
    dependency_paths = {str(row.get("result_lock") or "") for row in dependencies}
    if dependency_paths != set(EXPECTED_DEPENDENCIES):
        violations["dependency"].append("dependency_set")
    for row in dependencies:
        path = str(row.get("result_lock") or "")
        expected = EXPECTED_DEPENDENCIES.get(path)
        result = dependency_results.get(path)
        if not expected or not result:
            violations["dependency"].append(f"{path}:missing")
            continue
        expected_experiment, expected_decision = expected
        if row.get("experiment_id") != expected_experiment:
            violations["dependency"].append(f"{path}:experiment_id")
        if row.get("required_decision") != expected_decision:
            violations["dependency"].append(f"{path}:required_decision")
        if result.get("experiment_id") != expected_experiment:
            violations["dependency"].append(f"{path}:result_experiment_id")
        if result.get("decision") != expected_decision:
            violations["dependency"].append(f"{path}:result_decision")

    construct = preregistration.get("target_construct") or {}
    if construct.get("name") != "public_observable_persona_fidelity":
        violations["target_construct"].append("name")
    if set(construct.get("dimensions") or []) != EXPECTED_TARGET_DIMENSIONS:
        violations["target_construct"].append("dimensions")
    excluded = set(construct.get("explicitly_not_measured") or [])
    for requirement in ("performer_identity", "complete_person_identity", "public_deception_success"):
        if requirement not in excluded:
            violations["target_construct"].append(f"missing_exclusion:{requirement}")

    conditions = preregistration.get("system_conditions") or {}
    if set(conditions) != EXPECTED_CONDITIONS:
        violations["conditions"].append("condition_set")
    for condition_id, condition in conditions.items():
        if not str(condition.get("role") or "").strip():
            violations["conditions"].append(f"{condition_id}:role")
        if not str(condition.get("description") or "").strip():
            violations["conditions"].append(f"{condition_id}:description")
    if not REQUIRED_CONTROLS.issubset(set(preregistration.get("control_variables") or [])):
        violations["controls"].append("required_controls")

    families = preregistration.get("evaluation_families") or {}
    if set(families) != EXPECTED_EVALUATION_FAMILIES:
        violations["evaluation_families"].append("family_set")
    for family_id, family in families.items():
        for field in ("purpose", "agent_input", "reference", "source_independence"):
            if not str(family.get(field) or "").strip():
                violations["evaluation_families"].append(f"{family_id}:{field}")

    reference = preregistration.get("reference_design") or {}
    for field in (
        "target_target_reference",
        "other_target_reference",
        "agent_target_reference",
        "topic_control",
        "raw_data_boundary",
    ):
        if not str(reference.get(field) or "").strip():
            violations["reference_design"].append(field)

    blind = preregistration.get("human_blind_protocol") or {}
    if blind.get("setting") != "closed_consented_anonymous_evaluation":
        violations["human_blind_protocol"].append("setting")
    for flag in (
        "condition_blinding",
        "response_order_randomized",
        "pilot_required_before_power_freeze",
        "debrief_required",
    ):
        if blind.get(flag) is not True:
            violations["human_blind_protocol"].append(flag)
    if int(blind.get("minimum_ratings_per_item") or 0) < 3:
        violations["human_blind_protocol"].append("minimum_ratings_per_item")
    if float(blind.get("minimum_usable_agreement") or 0) <= 0:
        violations["human_blind_protocol"].append("minimum_usable_agreement")

    primary = preregistration.get("primary_endpoint") or {}
    thresholds = primary.get("success_thresholds") or {}
    if primary.get("name") != "paired_blind_persona_preference_s0_over_c1":
        violations["primary_endpoint"].append("name")
    if float(thresholds.get("non_tie_win_rate_min") or 0) < 0.6:
        violations["primary_endpoint"].append("non_tie_win_rate_min")
    if float(thresholds.get("confidence_interval_level") or 0) != 0.95:
        violations["primary_endpoint"].append("confidence_interval_level")
    if float(thresholds.get("confidence_interval_lower_bound_above") or 0) != 0.5:
        violations["primary_endpoint"].append("confidence_interval_lower_bound_above")
    if float(thresholds.get("two_sided_alpha_max") or 1) > 0.05:
        violations["primary_endpoint"].append("two_sided_alpha_max")

    formulas = preregistration.get("calibration_formulas") or {}
    if "agent_target_similarity" not in str(formulas.get("similarity") or ""):
        violations["calibration_formulas"].append("similarity")
    if "agent_target_distance" not in str(formulas.get("distance") or ""):
        violations["calibration_formulas"].append("distance")
    if not str(formulas.get("invalid_when") or "").strip():
        violations["calibration_formulas"].append("invalid_when")

    margins = preregistration.get("non_regression_margins") or {}
    if set(margins) != REQUIRED_NON_REGRESSION_MARGINS:
        violations["non_regression"].append("margin_set")
    ablation = preregistration.get("module_ablation_policy") or {}
    for flag in (
        "required_after_primary_system_freeze",
        "one_component_changed_per_comparison",
        "same_items_and_control_variables_required",
        "leftbrain_plan_and_final_output_scored_separately",
    ):
        if ablation.get(flag) is not True:
            violations["ablation"].append(flag)
    if ablation.get("compound_ablation_as_causal_evidence") is not False:
        violations["ablation"].append("compound_ablation_as_causal_evidence")

    formal_minimum = preregistration.get("formal_execution_readiness_minimum") or {}
    if set(READINESS_COUNT_MAP) - set(formal_minimum):
        violations["readiness_contract"].append("count_threshold_set")
    if set(READINESS_FLAG_MAP) - set(formal_minimum):
        violations["readiness_contract"].append("flag_threshold_set")
    for field in READINESS_COUNT_MAP:
        if int(formal_minimum.get(field) or 0) <= 0:
            violations["readiness_contract"].append(field)

    leakage_controls = preregistration.get("leakage_and_rights_controls") or []
    leakage_text = " ".join(str(item) for item in leakage_controls).lower()
    for token in ("source", "date", "prompt", "training", "public access", "consented"):
        if token not in leakage_text:
            violations["leakage_and_rights"].append(token)

    decision = preregistration.get("decision_policy") or {}
    if decision.get("protocol_pass") != PROTOCOL_PASS_DECISION:
        violations["decision_policy"].append("protocol_pass")
    if decision.get("protocol_fail") != PROTOCOL_FAIL_DECISION:
        violations["decision_policy"].append("protocol_fail")
    if decision.get("execution_ready") != PILOT_READY_DECISION:
        violations["decision_policy"].append("execution_ready")
    for field in PROHIBITED_AUTHORIZATIONS:
        if decision.get(field) is not False:
            violations["decision_policy"].append(field)

    if method_registry.get("schema") != METHOD_REGISTRY_SCHEMA:
        violations["method_registry"].append("schema")
    if method_registry.get("dataset_or_code_imported") is not False:
        violations["method_registry"].append("dataset_or_code_imported")
    methods = list(method_registry.get("methods") or [])
    method_ids = [str(row.get("method_id") or "") for row in methods]
    if set(method_ids) != EXPECTED_METHOD_IDS or len(method_ids) != len(set(method_ids)):
        violations["method_registry"].append("method_ids")
    urls = []
    dois = []
    for row in methods:
        method_id = str(row.get("method_id") or "")
        urls.append(str(row.get("url") or ""))
        dois.append(str(row.get("doi") or ""))
        if row.get("authority") != "peer_reviewed_primary_paper":
            violations["method_registry"].append(f"{method_id}:authority")
        if not str(row.get("url") or "").startswith("https://aclanthology.org/"):
            violations["method_registry"].append(f"{method_id}:url")
        if not str(row.get("doi") or "").startswith("10."):
            violations["method_registry"].append(f"{method_id}:doi")
        for field in ("title", "venue", "adopted_element", "not_claimed"):
            if not str(row.get(field) or "").strip():
                violations["method_registry"].append(f"{method_id}:{field}")
    if len(urls) != len(set(urls)) or len(dois) != len(set(dois)):
        violations["method_registry"].append("duplicate_url_or_doi")

    if readiness.get("schema") != READINESS_SCHEMA:
        violations["readiness_inventory"].append("schema")
    if readiness.get("target_id") != TARGET_ID:
        violations["readiness_inventory"].append("target_id")
    counts = readiness.get("counts") or {}
    flags = readiness.get("flags") or {}
    bindings = readiness.get("evidence_bindings") or {}
    for name, value in counts.items():
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            violations["readiness_inventory"].append(f"{name}:non_negative_integer")
    if set(flags) != EXPECTED_READINESS_FLAGS:
        violations["readiness_inventory"].append("flag_set")
    for name, value in flags.items():
        if not isinstance(value, bool):
            violations["readiness_inventory"].append(f"{name}:boolean")
    boundary = readiness.get("data_boundary") or {}
    for field, value in boundary.items():
        if value is not False:
            violations["readiness_inventory"].append(f"data_boundary:{field}")

    v2_result = dependency_results.get(
        "configs/public_persona_observation_v2_result_lock.json", {}
    )
    v2_formal = v2_result.get("formal_result") or {}
    locked_count_expectations = {
        "target_development_observation_count": v2_formal.get(
            "development_observation_count"
        ),
        "sealed_target_source_reservation_count": v2_formal.get(
            "sealed_holdout_source_count"
        ),
        "holdout_content_reviewed_count": v2_formal.get(
            "holdout_content_reviewed_count"
        ),
        "holdout_label_available_count": v2_formal.get(
            "holdout_label_available_count"
        ),
        "training_authorized_record_count": v2_formal.get(
            "training_authorized_count"
        ),
    }
    for name, expected in locked_count_expectations.items():
        if expected is None or counts.get(name) != expected:
            violations["readiness_inventory"].append(f"{name}:v2_lock_mismatch")

    for count_name, binding_name in EVIDENCE_BINDING_REQUIREMENTS.items():
        if int(counts.get(count_name) or 0) > 0 and not _validate_binding(
            bindings.get(binding_name), Path(root)
        ):
            violations["readiness_evidence"].append(
                f"{count_name}:{binding_name}"
            )
    flag_binding_requirements = {
        "pilot_completed": "pilot_report",
        "power_plan_frozen": "power_plan",
        "runtime_manifest_frozen": "runtime_manifest",
        "source_rights_review_complete_for_formal_corpus": "rights_review",
        "holdout_access_log_ready": "holdout_access_log",
    }
    for flag_name, binding_name in flag_binding_requirements.items():
        if flags.get(flag_name) is True and not _validate_binding(
            bindings.get(binding_name), Path(root)
        ):
            violations["readiness_evidence"].append(
                f"{flag_name}:{binding_name}"
            )

    readiness_checks = {}
    for threshold_name, count_name in READINESS_COUNT_MAP.items():
        readiness_checks[count_name] = int(counts.get(count_name) or 0) >= int(
            formal_minimum.get(threshold_name) or 0
        )
    for threshold_name, flag_name in READINESS_FLAG_MAP.items():
        readiness_checks[flag_name] = (
            flags.get(flag_name) is bool(formal_minimum.get(threshold_name))
            and flags.get(flag_name) is True
        )
    readiness_checks["all_nonzero_claims_hash_bound"] = not violations[
        "readiness_evidence"
    ]
    readiness_derived = all(readiness_checks.values())
    if flags.get("formal_execution_ready") is not readiness_derived:
        violations["readiness_inventory"].append(
            "formal_execution_ready:derived_state_mismatch"
        )
    if flags.get("persona_fidelity_claim_available") is not False:
        violations["readiness_inventory"].append(
            "persona_fidelity_claim_available:must_remain_false_before_formal_result"
        )

    protocol_checks = {
        "preregistration_identity_and_hypothesis": not violations["preregistration"],
        "locked_dependencies_match": not violations["dependency"],
        "public_observable_target_construct": not violations["target_construct"],
        "matched_system_conditions": not violations["conditions"],
        "control_variables_complete": not violations["controls"],
        "three_complementary_evaluation_families": not violations[
            "evaluation_families"
        ],
        "human_reference_design_complete": not violations["reference_design"],
        "closed_blind_protocol_complete": not violations["human_blind_protocol"],
        "primary_endpoint_frozen": not violations["primary_endpoint"],
        "calibration_formulas_defined": not violations["calibration_formulas"],
        "general_capability_non_regression_frozen": not violations[
            "non_regression"
        ],
        "single_component_ablation_required": not violations["ablation"],
        "formal_readiness_contract_complete": not violations[
            "readiness_contract"
        ],
        "leakage_and_rights_controls_complete": not violations[
            "leakage_and_rights"
        ],
        "narrow_authorization_boundary": not violations["decision_policy"],
        "primary_method_registry_complete": not violations["method_registry"],
        "readiness_inventory_is_locked_evidence_bound": not violations[
            "readiness_inventory"
        ]
        and not violations["readiness_evidence"],
    }
    protocol_passed = all(protocol_checks.values())
    formal_execution_ready = protocol_passed and readiness_derived
    if not protocol_passed:
        final_decision = PROTOCOL_FAIL_DECISION
    elif formal_execution_ready:
        final_decision = PILOT_READY_DECISION
    else:
        final_decision = PROTOCOL_PASS_DECISION

    compact_violations = {
        key: values for key, values in sorted(violations.items()) if values
    }
    synthetic_pairwise = pairwise_preference_summary(12, 6, 2)
    return {
        "schema": "uruha_public_persona_fidelity_eval_construction_audit_v1",
        "experiment_id": EXPERIMENT_ID,
        "target_id": TARGET_ID,
        "protocol_passed": protocol_passed,
        "formal_execution_ready": formal_execution_ready,
        "persona_score_computed": False,
        "decision": final_decision,
        "summary": {
            "protocol_check_count": len(protocol_checks),
            "protocol_check_pass_count": sum(protocol_checks.values()),
            "readiness_check_count": len(readiness_checks),
            "readiness_check_pass_count": sum(readiness_checks.values()),
            "method_count": len(methods),
            "system_condition_count": len(conditions),
            "evaluation_family_count": len(families),
            "development_observation_count": counts.get(
                "target_development_observation_count", 0
            ),
            "sealed_target_source_reservation_count": counts.get(
                "sealed_target_source_reservation_count", 0
            ),
            "formal_agent_response_count": counts.get(
                "formal_agent_response_count", 0
            ),
            "formal_persona_score_count": counts.get(
                "formal_persona_score_count", 0
            ),
            "model_call_count": 0,
            "runtime_change_count": 0,
            "holdout_content_review_count": counts.get(
                "holdout_content_reviewed_count", 0
            ),
        },
        "protocol_checks": protocol_checks,
        "readiness_checks": readiness_checks,
        "readiness_current": counts,
        "readiness_required": formal_minimum,
        "violations": compact_violations,
        "synthetic_arithmetic_examples_not_results": {
            "calibrated_similarity": calibrated_similarity(
                0.7, [0.88, 0.9, 0.92], [0.38, 0.4, 0.42]
            ),
            "calibrated_distance": calibrated_distance(
                0.3, [0.18, 0.2, 0.22], [0.58, 0.6, 0.62]
            ),
            "pairwise_preference": synthetic_pairwise,
        },
        "system_conditions": conditions,
        "evaluation_families": families,
        "method_inventory": [
            {
                "method_id": row.get("method_id"),
                "title": row.get("title"),
                "url": row.get("url"),
                "doi": row.get("doi"),
                "adopted_element": row.get("adopted_element"),
                "not_claimed": row.get("not_claimed"),
            }
            for row in methods
        ],
        "authorizations": {
            "reference_manifest_construction": protocol_passed,
            "consented_rater_protocol_construction": protocol_passed,
            "separately_preregistered_pilot": formal_execution_ready,
            "model_execution": False,
            "runtime_change": False,
            "prompt_change": False,
            "model_training": False,
            "sealed_holdout_unsealing": False,
            "formal_persona_scoring": False,
            "public_persona_fidelity_claim": False,
            "private_person_copy_claim": False,
        },
        "next_required_evidence": (
            "建立只含來源、日期、分割、權利邊界與雜湊的參考資料 manifest，補足目標校準、"
            "相近人物同主題對照及知情同意評分者流程；在全部 readiness gate 通過前不執行模型或打開 holdout。"
        ),
        "evidence_boundary": preregistration.get("evidence_boundary"),
    }


def build_markdown(report):
    summary = report["summary"]
    required = report["readiness_required"]
    current = report["readiness_current"]
    rows = [
        ("目標開發觀察", current["target_development_observation_count"], required["target_development_observation_count_min"]),
        ("目標校準事件", current["target_calibration_event_count"], required["target_calibration_event_count_min"]),
        ("最終目標 holdout 事件", current["target_final_holdout_event_count"], required["target_final_holdout_event_count_min"]),
        ("相近人物", current["matched_contrast_person_count"], required["matched_contrast_person_count_min"]),
        ("同主題參考配對", current["same_topic_reference_pair_count"], required["same_topic_reference_pair_count_min"]),
        ("反事實新情境", current["counterfactual_final_scenario_count"], required["counterfactual_final_scenario_count_min"]),
        ("多輪事件", current["dynamic_multi_turn_episode_count"], required["dynamic_multi_turn_episode_count_min"]),
        ("目標熟悉評分者", current["target_familiar_final_rater_count"], required["target_familiar_final_rater_count_min"]),
        ("一般日語評分者", current["general_japanese_final_rater_count"], required["general_japanese_final_rater_count_min"]),
    ]
    lines = [
        "# 公開人格重現評測 V1 建構稽核",
        "",
        f"- 評測協定完整：`{report['protocol_passed']}` ({summary['protocol_check_pass_count']}/{summary['protocol_check_count']})",
        f"- 正式執行就緒：`{report['formal_execution_ready']}` ({summary['readiness_check_pass_count']}/{summary['readiness_check_count']})",
        f"- 人格分數已計算：`{report['persona_score_computed']}`",
        f"- 決策：`{report['decision']}`",
        "- 本輪模型呼叫、runtime 修改、holdout 檢視：`0 / 0 / 0`",
        "",
        "## 現在具備什麼",
        "",
        "評測尺的比較條件、資料隔離、盲評主指標、真人參考範圍、同主題控制、非退步界線與單一部件消融規則已凍結。",
        "目前只有 5 筆開發觀察與 2 個未開封來源；因此沒有產生或暗示任何一ノ瀬うるは人格相似分數。",
        "",
        "## 正式執行缺口",
        "",
        "| 證據 | 現有 | 最低需求 | 就緒 |",
        "|---|---:|---:|---:|",
    ]
    for label, available, minimum in rows:
        lines.append(f"| {label} | {available} | {minimum} | {available >= minimum} |")
    lines.extend(
        [
            "",
            "## 公平比較",
            "",
            "| 條件 | 作用 |",
            "|---|---|",
        ]
    )
    for condition_id, condition in report["system_conditions"].items():
        lines.append(f"| `{condition_id}` | {condition['description']} |")
    lines.extend(
        [
            "",
            "主比較是 `S0 完整系統` 對 `C1 同模型、同人格資訊、同預算的 prompt-only`。",
            "`C2 人格關閉` 只驗證差異是否來自目標人格層；單一部件貢獻仍要另外逐一消融。",
            "",
            "## 五條互補證據",
            "",
            "1. 熟悉目標人物的知情同意匿名盲評。",
            "2. 目標人物跨時期的自然差異作參考範圍。",
            "3. 至少三位相近人物的同主題對照，防止話題捷徑。",
            "4. 來源獨立的新情境與多輪動態事件。",
            "5. 語意、推理、記憶、拒答、多樣性、延遲、記憶體與動作安全不退步。",
            "",
            "## 主成功門檻",
            "",
            "S0 對 C1 的非平手人格盲評勝率至少 60%，95% 信賴區間下界高於 50%，並以評分者與情境相依的配對模型確認。",
            "單一向量、單一 benchmark 或 LLM judge 即使很高，也不能單獨通過。",
            "",
            "## 校準公式示意，不是真實結果",
            "",
            "若代理對目標相似度為 0.70、目標跨期中位數 0.90、相近人物中位數 0.40，校準值為 0.60。",
            "其中 0 代表相近人物基準，1 代表目標跨期自身基準；數值不截斷，大於 1 不代表比真人更像真人。",
            "",
            "## 方法來源",
            "",
            "| 方法 | 本研究採用 | 不代表 |",
            "|---|---|---|",
        ]
    )
    for method in report["method_inventory"]:
        lines.append(
            f"| [{method['method_id']}]({method['url']}) | {method['adopted_element']} | {method['not_claimed']} |"
        )
    lines.extend(
        [
            "",
            "## 證據邊界",
            "",
            str(report["evidence_boundary"]),
            "",
            "下一步：" + report["next_required_evidence"],
        ]
    )
    return "\n".join(lines)


def build_audit_from_paths(
    preregistration_path=DEFAULT_PREREGISTRATION,
    method_registry_path=DEFAULT_METHOD_REGISTRY,
    readiness_path=DEFAULT_READINESS_INVENTORY,
):
    preregistration = load_json(preregistration_path)
    method_registry = load_json(method_registry_path)
    readiness = load_json(readiness_path)
    dependency_results = {
        path: load_json(ROOT / path) for path in EXPECTED_DEPENDENCIES
    }
    report = audit(
        preregistration,
        method_registry,
        readiness,
        dependency_results,
        root=ROOT,
    )
    report["inputs"] = {
        "preregistration": {
            "path": _display_path(preregistration_path),
            "sha256": sha256_file(preregistration_path),
        },
        "method_registry": {
            "path": _display_path(method_registry_path),
            "sha256": sha256_file(method_registry_path),
        },
        "readiness_inventory": {
            "path": _display_path(readiness_path),
            "sha256": sha256_file(readiness_path),
        },
        "dependencies": {
            path: {"path": path, "sha256": sha256_file(ROOT / path)}
            for path in EXPECTED_DEPENDENCIES
        },
    }
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preregistration", default=DEFAULT_PREREGISTRATION)
    parser.add_argument("--method-registry", default=DEFAULT_METHOD_REGISTRY)
    parser.add_argument("--readiness", default=DEFAULT_READINESS_INVENTORY)
    parser.add_argument("--output-json", default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", default=DEFAULT_OUTPUT_MD)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--require-protocol-pass", action="store_true")
    parser.add_argument("--require-execution-ready", action="store_true")
    args = parser.parse_args()
    output_json = Path(args.output_json)
    output_md = Path(args.output_md)
    if not args.overwrite and (output_json.exists() or output_md.exists()):
        raise FileExistsError("refusing to overwrite fidelity audit without --overwrite")
    report = build_audit_from_paths(
        args.preregistration,
        args.method_registry,
        args.readiness,
    )
    output_json.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    output_md.write_text(build_markdown(report) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "protocol_passed": report["protocol_passed"],
                "formal_execution_ready": report["formal_execution_ready"],
                "persona_score_computed": report["persona_score_computed"],
                "decision": report["decision"],
                "summary": report["summary"],
                "violations": report["violations"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if args.require_protocol_pass and not report["protocol_passed"]:
        return 1
    if args.require_execution_ready and not report["formal_execution_ready"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
