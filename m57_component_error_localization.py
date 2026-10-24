#!/usr/bin/env python3
"""M57 outcome-blind component-substitution diagnostic readiness harness."""

from __future__ import annotations

import argparse
from copy import deepcopy
from hashlib import sha256
import html
import inspect
import json
import math
from pathlib import Path
import random
import re
from typing import Any

import m56_13_unidirectional_public_snapshot as snapshot_m56


ROOT = Path(__file__).resolve().parent
CONTRACT_PATH = ROOT / "configs/m57_component_error_localization_v1.json"
CODEBOOK_PATH = ROOT / "configs/public_persona_contrast_coding_codebook_v6.json"
RESULT_PATH = ROOT / "analysis/m57_component_error_localization_rehearsal_result_2026-09-04.json"
BUNDLE_SCHEMA = "uruha_m57_component_substitution_bundle_v1"
RESULT_SCHEMA = "uruha_m57_component_error_localization_result_v1"
REHEARSAL_SCHEMA = "uruha_m57_component_error_localization_rehearsal_v1"
AUDIT_SCHEMA = "uruha_m57_component_error_localization_live_audit_v1"
STAGE_IDS = ("perception", "retrieval", "state", "decision", "realization")


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return sha256(canonical(value).encode("utf-8")).hexdigest()


def sha256_file(path: str | Path) -> str:
    return sha256(Path(path).read_bytes()).hexdigest()


def load_json(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def load_contract(path: str | Path = CONTRACT_PATH) -> dict[str, Any]:
    return load_json(path)


def behavior_labels() -> tuple[str, ...]:
    value = load_json(CODEBOOK_PATH)
    labels = tuple(value.get("dialogue_act_or_action_labels") or ())
    if len(labels) != 13 or len(set(labels)) != len(labels):
        raise PermissionError("M57 requires the frozen 13-label observable behavior taxonomy")
    return labels


LABELS = behavior_labels()


def validate_contract(contract: dict[str, Any] | None = None) -> dict[str, Any]:
    contract = deepcopy(contract or load_contract())
    errors: list[str] = []
    expected = {
        "schema", "version", "status", "single_changed_variable", "frozen_dependencies",
        "stages", "analysis", "formal_execution", "engineering_rehearsal", "claim_boundary",
    }
    if set(contract) != expected:
        errors.append("contract.fields")
    if contract.get("schema") != "uruha_m57_component_error_localization_contract_v1":
        errors.append("contract.schema")
    if contract.get("version") != "1.0.0":
        errors.append("contract.version")
    if contract.get("status") != "prospective_frozen_before_implementation_any_m56_result_and_real_target_outcome_access":
        errors.append("contract.status")
    dependencies = contract.get("frozen_dependencies") or {}
    if len(dependencies) != 5:
        errors.append("dependencies.count")
    for relative, expected_hash in dependencies.items():
        path = ROOT / relative
        if not path.is_file() or sha256_file(path) != expected_hash:
            errors.append(f"dependency:{relative}")
    stages = contract.get("stages") or []
    if [stage.get("id") for stage in stages] != list(STAGE_IDS):
        errors.append("stages.order")
    for stage in stages:
        if set(stage) != {
            "id", "substitution_target", "oracle_kind", "required_provenance",
            "eligible_for_leading_recoverable_stage", "private_mental_truth_claimed",
        }:
            errors.append(f"stage.fields:{stage.get('id')}")
        if stage.get("private_mental_truth_claimed") is not False:
            errors.append(f"stage.private_truth:{stage.get('id')}")
    analysis = contract.get("analysis") or {}
    if analysis.get("sample_count") != 30 or analysis.get("bootstrap_repetitions") != 20000:
        errors.append("analysis.counts")
    if analysis.get("bootstrap_seed") != 570904:
        errors.append("analysis.seed")
    if analysis.get("unique_biological_or_psychological_cause_claim_authorized") is not False:
        errors.append("analysis.causal_claim")
    formal = contract.get("formal_execution") or {}
    if formal.get("entry_function") != "diagnose_formal_m56_components" or formal.get("parameters") != ["run_id"]:
        errors.append("formal.entry")
    if list(inspect.signature(diagnose_formal_m56_components).parameters) != ["run_id"]:
        errors.append("formal.signature")
    if formal.get("retry_count") != 0 or formal.get("fallback_count") != 0:
        errors.append("formal.retry")
    if formal.get("current_formal_execution_authorized") is not False:
        errors.append("formal.current_authority")
    return {
        "valid": not errors,
        "errors": errors,
        "binding_count": len(dependencies),
        "contract_hash": digest(contract),
    }


def _validate_distribution(value: Any, labels: tuple[str, ...]) -> list[str]:
    errors: list[str] = []
    tolerance = float(load_contract()["analysis"]["probability_sum_tolerance"])
    if not isinstance(value, dict) or tuple(value) != labels:
        return ["distribution.labels_or_order"]
    numbers = list(value.values())
    if any(type(number) not in (int, float) or not math.isfinite(float(number)) for number in numbers):
        errors.append("distribution.finite")
    elif any(float(number) < 0.0 or float(number) > 1.0 for number in numbers):
        errors.append("distribution.range")
    elif abs(sum(float(number) for number in numbers) - 1.0) > tolerance:
        errors.append("distribution.sum")
    return errors


def _validate_stage_plan(stage_id: str, plan: Any, frozen: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    expected_fields = {
        "stage_id", "substitution_target", "oracle_kind", "required_provenance",
        "plan_committed_before_outcome", "evidence_timing", "eligibility",
        "private_mental_truth_claimed", "plan_hash",
    }
    if not isinstance(plan, dict) or set(plan) != expected_fields:
        return [f"stage_plan.fields:{stage_id}"]
    unhashed = {key: value for key, value in plan.items() if key != "plan_hash"}
    if plan.get("plan_hash") != digest(unhashed):
        errors.append(f"stage_plan.hash:{stage_id}")
    for name in ("stage_id", "substitution_target", "oracle_kind", "required_provenance"):
        expected = frozen["id"] if name == "stage_id" else frozen[name]
        if plan.get(name) != expected:
            errors.append(f"stage_plan.{name}:{stage_id}")
    if plan.get("plan_committed_before_outcome") is not True:
        errors.append(f"stage_plan.commitment:{stage_id}")
    expected_timing = "post_outcome_upper_bound" if stage_id == "decision" else (
        "human_ratings_required_or_unavailable" if stage_id == "realization" else "pre_outcome_only"
    )
    if plan.get("evidence_timing") != expected_timing:
        errors.append(f"stage_plan.timing:{stage_id}")
    if plan.get("eligibility") is not frozen["eligible_for_leading_recoverable_stage"]:
        errors.append(f"stage_plan.eligibility:{stage_id}")
    if plan.get("private_mental_truth_claimed") is not False:
        errors.append(f"stage_plan.private_truth:{stage_id}")
    return errors


def validate_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    expected_fields = {
        "schema", "version", "status", "data_kind", "fixture_kind", "label_order",
        "sample_count", "prediction_commitment_hash", "stage_plans",
        "substitution_plan_commitment_hash", "outcome_access_after_all_predictions_committed",
        "same_resource_contract", "single_stage_change_verified", "retry_count", "fallback_count",
        "formal_authorization", "rows", "claim_boundary", "bundle_hash",
    }
    if not isinstance(bundle, dict) or set(bundle) != expected_fields:
        return {"valid": False, "errors": ["bundle.fields"]}
    unhashed = {key: value for key, value in bundle.items() if key != "bundle_hash"}
    if bundle.get("bundle_hash") != digest(unhashed):
        errors.append("bundle.hash")
    if bundle.get("schema") != BUNDLE_SCHEMA or bundle.get("version") != "1.0.0":
        errors.append("bundle.schema")
    if bundle.get("status") != "all_predictions_and_stage_plans_committed_before_outcome_scoring":
        errors.append("bundle.status")
    if bundle.get("data_kind") not in {"synthetic_engineering_only", "real_formal_m56_diagnostic"}:
        errors.append("bundle.data_kind")
    if bundle.get("data_kind") == "real_formal_m56_diagnostic":
        if bundle.get("formal_authorization") is not True:
            errors.append("bundle.real_authorization")
        # The readiness contract deliberately has no formal artifact bridge. A caller-supplied
        # boolean must never be enough to mint a result that looks formally authorized.
        errors.append("bundle.real_formal_bridge_unavailable")
    if bundle.get("data_kind") == "synthetic_engineering_only" and bundle.get("formal_authorization") is not False:
        errors.append("bundle.synthetic_authorization")
    labels = tuple(bundle.get("label_order") or ())
    if labels != LABELS:
        errors.append("bundle.labels")
    if bundle.get("sample_count") != 30:
        errors.append("bundle.sample_count")
    if re.fullmatch(r"[0-9a-f]{64}", str(bundle.get("prediction_commitment_hash") or "")) is None:
        errors.append("bundle.prediction_commitment")
    plans = bundle.get("stage_plans") or {}
    if tuple(plans) != STAGE_IDS:
        errors.append("bundle.stage_plans")
    else:
        frozen_stages = {stage["id"]: stage for stage in load_contract()["stages"]}
        for stage_id in STAGE_IDS:
            errors.extend(_validate_stage_plan(stage_id, plans[stage_id], frozen_stages[stage_id]))
        if bundle.get("substitution_plan_commitment_hash") != digest(plans):
            errors.append("bundle.plan_commitment")
    if bundle.get("outcome_access_after_all_predictions_committed") is not True:
        errors.append("bundle.outcome_order")
    if bundle.get("same_resource_contract") is not True or bundle.get("single_stage_change_verified") is not True:
        errors.append("bundle.single_variable_or_resource")
    if bundle.get("retry_count") != 0 or bundle.get("fallback_count") != 0:
        errors.append("bundle.retry")
    rows = bundle.get("rows") or []
    if not isinstance(rows, list) or len(rows) != 30:
        errors.append("rows.count")
    seen: set[str] = set()
    plan_hashes = {stage_id: (plans.get(stage_id) or {}).get("plan_hash") for stage_id in STAGE_IDS}
    for index, row in enumerate(rows if isinstance(rows, list) else []):
        scope = f"row[{index}]"
        expected_row_fields = {
            "sample_id", "observed_label", "original_probabilities", "original_output_hash",
            "substitutions",
        }
        if not isinstance(row, dict) or set(row) != expected_row_fields:
            errors.append(f"{scope}.fields")
            continue
        sample_id = row.get("sample_id")
        if not isinstance(sample_id, str) or not sample_id or sample_id in seen:
            errors.append(f"{scope}.sample_id")
        else:
            seen.add(sample_id)
        if row.get("observed_label") not in labels:
            errors.append(f"{scope}.observed_label")
        errors.extend(f"{scope}.original.{name}" for name in _validate_distribution(row.get("original_probabilities"), labels))
        if row.get("original_output_hash") != digest(row.get("original_probabilities")):
            errors.append(f"{scope}.original_hash")
        substitutions = row.get("substitutions") or {}
        if tuple(substitutions) != STAGE_IDS:
            errors.append(f"{scope}.stages")
            continue
        for stage_id in STAGE_IDS:
            sub = substitutions[stage_id]
            expected_sub_fields = {
                "stage_id", "availability", "changed_component", "plan_hash",
                "downstream_recomputed", "probabilities", "downstream_output_hash",
                "evidence_available_before_outcome", "future_outcome_used",
            }
            if not isinstance(sub, dict) or set(sub) != expected_sub_fields:
                errors.append(f"{scope}.{stage_id}.fields")
                continue
            if sub.get("stage_id") != stage_id or sub.get("changed_component") != stage_id:
                errors.append(f"{scope}.{stage_id}.single_component")
            if sub.get("plan_hash") != plan_hashes.get(stage_id):
                errors.append(f"{scope}.{stage_id}.plan_hash")
            if sub.get("availability") not in {"available", "unavailable"}:
                errors.append(f"{scope}.{stage_id}.availability")
            if sub.get("availability") == "unavailable":
                if sub.get("probabilities") is not None or sub.get("downstream_output_hash") is not None:
                    errors.append(f"{scope}.{stage_id}.unavailable_payload")
                if sub.get("downstream_recomputed") is not False:
                    errors.append(f"{scope}.{stage_id}.unavailable_recompute")
            else:
                errors.extend(f"{scope}.{stage_id}.{name}" for name in _validate_distribution(sub.get("probabilities"), labels))
                if sub.get("downstream_output_hash") != digest(sub.get("probabilities")):
                    errors.append(f"{scope}.{stage_id}.output_hash")
                if sub.get("downstream_recomputed") is not True:
                    errors.append(f"{scope}.{stage_id}.recompute")
            if stage_id == "decision":
                if sub.get("evidence_available_before_outcome") is not False or sub.get("future_outcome_used") is not True:
                    errors.append(f"{scope}.decision.timing")
            elif stage_id == "realization":
                if sub.get("availability") == "unavailable" and sub.get("evidence_available_before_outcome") is not False:
                    errors.append(f"{scope}.realization.timing")
                if sub.get("future_outcome_used") is not False:
                    errors.append(f"{scope}.realization.future")
            elif sub.get("evidence_available_before_outcome") is not True or sub.get("future_outcome_used") is not False:
                errors.append(f"{scope}.{stage_id}.future_leakage")
    return {"valid": not errors, "errors": errors, "bundle_hash": bundle.get("bundle_hash")}


def _brier(probabilities: dict[str, float], observed: str, labels: tuple[str, ...]) -> float:
    return sum((float(probabilities[label]) - (1.0 if label == observed else 0.0)) ** 2 for label in labels)


def _nll(probabilities: dict[str, float], observed: str) -> float:
    return -math.log(max(float(probabilities[observed]), 1e-15))


def _top1(probabilities: dict[str, float], observed: str, labels: tuple[str, ...]) -> float:
    best = max(labels, key=lambda label: (float(probabilities[label]), -labels.index(label)))
    return 1.0 if best == observed else 0.0


def _mean(values: list[float]) -> float:
    return sum(values) / len(values)


def _bootstrap_mean_interval(values: list[float], *, seed: int, repetitions: int) -> list[float]:
    rng = random.Random(seed)
    count = len(values)
    draws = sorted(_mean([values[rng.randrange(count)] for _ in range(count)]) for _ in range(repetitions))
    lower = draws[int(0.025 * repetitions)]
    upper = draws[min(repetitions - 1, int(0.975 * repetitions))]
    return [lower, upper]


def analyze_component_substitution_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    validation = validate_bundle(bundle)
    if not validation["valid"]:
        raise ValueError("invalid M57 component bundle: " + "; ".join(validation["errors"]))
    contract = load_contract()
    settings = contract["analysis"]
    stage_specs = {stage["id"]: stage for stage in contract["stages"]}
    labels = tuple(bundle["label_order"])
    stage_results: dict[str, dict[str, Any]] = {}
    for stage_index, stage_id in enumerate(STAGE_IDS):
        available = [row for row in bundle["rows"] if row["substitutions"][stage_id]["availability"] == "available"]
        if not available:
            stage_results[stage_id] = {
                "availability": "unavailable",
                "available_sample_count": 0,
                "oracle_kind": stage_specs[stage_id]["oracle_kind"],
                "eligible_for_leading_recoverable_stage": stage_specs[stage_id]["eligible_for_leading_recoverable_stage"],
                "attribution_status": "unavailable_required_evidence_missing",
                "original_metrics": None,
                "substitution_metrics": None,
                "deltas_original_minus_substitution": None,
                "bootstrap_95_ci": None,
            }
            continue
        original_brier = [_brier(row["original_probabilities"], row["observed_label"], labels) for row in available]
        sub_brier = [_brier(row["substitutions"][stage_id]["probabilities"], row["observed_label"], labels) for row in available]
        original_nll = [_nll(row["original_probabilities"], row["observed_label"]) for row in available]
        sub_nll = [_nll(row["substitutions"][stage_id]["probabilities"], row["observed_label"]) for row in available]
        original_top1 = [_top1(row["original_probabilities"], row["observed_label"], labels) for row in available]
        sub_top1 = [_top1(row["substitutions"][stage_id]["probabilities"], row["observed_label"], labels) for row in available]
        delta_brier = [before - after for before, after in zip(original_brier, sub_brier)]
        delta_nll = [before - after for before, after in zip(original_nll, sub_nll)]
        delta_top1 = _mean(sub_top1) - _mean(original_top1)
        seed = int(settings["bootstrap_seed"]) + stage_index
        brier_ci = _bootstrap_mean_interval(delta_brier, seed=seed, repetitions=int(settings["bootstrap_repetitions"]))
        nll_ci = _bootstrap_mean_interval(delta_nll, seed=seed + 100, repetitions=int(settings["bootstrap_repetitions"]))
        eligible = bool(stage_specs[stage_id]["eligible_for_leading_recoverable_stage"])
        recoverable = eligible and brier_ci[0] > 0 and nll_ci[0] > 0 and delta_top1 >= 0
        if stage_id == "decision":
            status = "diagnostic_upper_bound_excluded_from_causal_ranking"
        elif stage_id == "realization":
            status = "descriptive_realization_only"
        else:
            status = "recoverable_effect" if recoverable else "no_recoverable_effect"
        stage_results[stage_id] = {
            "availability": "available",
            "available_sample_count": len(available),
            "oracle_kind": stage_specs[stage_id]["oracle_kind"],
            "eligible_for_leading_recoverable_stage": eligible,
            "attribution_status": status,
            "original_metrics": {
                "brier": _mean(original_brier), "negative_log_likelihood": _mean(original_nll),
                "top1_accuracy": _mean(original_top1),
            },
            "substitution_metrics": {
                "brier": _mean(sub_brier), "negative_log_likelihood": _mean(sub_nll),
                "top1_accuracy": _mean(sub_top1),
            },
            "deltas_original_minus_substitution": {
                "brier": _mean(delta_brier), "negative_log_likelihood": _mean(delta_nll),
                "top1_accuracy_substitution_minus_original": delta_top1,
            },
            "bootstrap_95_ci": {"brier": brier_ci, "negative_log_likelihood": nll_ci},
        }
    recoverable_ids = [
        stage_id for stage_id in STAGE_IDS
        if stage_results[stage_id]["attribution_status"] == "recoverable_effect"
    ]
    leading: str | None = None
    if recoverable_ids:
        brier_order = sorted(
            recoverable_ids,
            key=lambda stage_id: stage_results[stage_id]["deltas_original_minus_substitution"]["brier"],
            reverse=True,
        )
        nll_order = sorted(
            recoverable_ids,
            key=lambda stage_id: stage_results[stage_id]["deltas_original_minus_substitution"]["negative_log_likelihood"],
            reverse=True,
        )
        if brier_order[0] == nll_order[0]:
            candidate = brier_order[0]
            margin = float(settings["leading_stage_minimum_runner_up_separation"])
            brier_runner = stage_results[brier_order[1]]["deltas_original_minus_substitution"]["brier"] if len(brier_order) > 1 else 0.0
            nll_runner = stage_results[nll_order[1]]["deltas_original_minus_substitution"]["negative_log_likelihood"] if len(nll_order) > 1 else 0.0
            candidate_delta = stage_results[candidate]["deltas_original_minus_substitution"]
            if candidate_delta["brier"] - brier_runner >= margin and candidate_delta["negative_log_likelihood"] - nll_runner >= margin:
                leading = candidate
    if leading is not None:
        attribution_status = "descriptive_leading_recoverable_stage_not_unique_cause"
    elif recoverable_ids:
        attribution_status = "ambiguous_interacting_or_unresolved"
    else:
        attribution_status = "no_eligible_recoverable_effect"
    result = {
        "schema": RESULT_SCHEMA,
        "version": "1.0.0",
        "status": "synthetic_mechanical_localization_complete" if bundle["data_kind"] == "synthetic_engineering_only" else "formal_localization_complete",
        "contract_hash": validate_contract()["contract_hash"],
        "data_kind": bundle["data_kind"],
        "fixture_kind": bundle["fixture_kind"],
        "sample_count": bundle["sample_count"],
        "label_count": len(labels),
        "prediction_commitment_hash": bundle["prediction_commitment_hash"],
        "substitution_plan_commitment_hash": bundle["substitution_plan_commitment_hash"],
        "stage_results": stage_results,
        "leading_recoverable_stage": leading,
        "attribution_status": attribution_status,
        "unique_biological_or_psychological_cause_claim_authorized": False,
        "retry_count": 0,
        "fallback_count": 0,
        "model_call_count": 0,
        "real_target_outcome_access_count": 0 if bundle["data_kind"] == "synthetic_engineering_only" else 1,
        "formal_result_created": bundle["data_kind"] == "real_formal_m56_diagnostic",
        "claim_boundary": contract["claim_boundary"],
    }
    result["analysis_hash"] = digest(result)
    return result


def validate_result(value: dict[str, Any], *, expected_data_kind: str | None = None) -> dict[str, Any]:
    errors: list[str] = []
    expected = {
        "schema", "version", "status", "contract_hash", "data_kind", "fixture_kind",
        "sample_count", "label_count", "prediction_commitment_hash",
        "substitution_plan_commitment_hash", "stage_results", "leading_recoverable_stage",
        "attribution_status", "unique_biological_or_psychological_cause_claim_authorized",
        "retry_count", "fallback_count", "model_call_count", "real_target_outcome_access_count",
        "formal_result_created", "claim_boundary", "analysis_hash",
    }
    if not isinstance(value, dict) or set(value) != expected:
        return {"valid": False, "errors": ["result.fields"]}
    unhashed = {key: child for key, child in value.items() if key != "analysis_hash"}
    if value.get("analysis_hash") != digest(unhashed):
        errors.append("result.hash")
    data_kind = value.get("data_kind")
    if expected_data_kind is not None and data_kind != expected_data_kind:
        errors.append("result.data_kind")
    if data_kind not in {"synthetic_engineering_only", "real_formal_m56_diagnostic"}:
        errors.append("result.data_kind")
    expected_status = (
        "synthetic_mechanical_localization_complete"
        if data_kind == "synthetic_engineering_only"
        else "formal_localization_complete"
    )
    if value.get("schema") != RESULT_SCHEMA or value.get("version") != "1.0.0" or value.get("status") != expected_status:
        errors.append("result.schema_or_status")
    if value.get("contract_hash") != validate_contract()["contract_hash"]:
        errors.append("result.contract")
    if value.get("sample_count") != 30 or value.get("label_count") != len(LABELS):
        errors.append("result.counts")
    for field in ("prediction_commitment_hash", "substitution_plan_commitment_hash"):
        if re.fullmatch(r"[0-9a-f]{64}", str(value.get(field) or "")) is None:
            errors.append(f"result.{field}")
    stages = value.get("stage_results") or {}
    if tuple(stages) != STAGE_IDS:
        errors.append("result.stages")
    else:
        for stage_id in STAGE_IDS:
            stage = stages[stage_id]
            if not isinstance(stage, dict) or stage.get("oracle_kind") != next(
                spec["oracle_kind"] for spec in load_contract()["stages"] if spec["id"] == stage_id
            ):
                errors.append(f"result.stage:{stage_id}")
        if stages["decision"].get("attribution_status") != "diagnostic_upper_bound_excluded_from_causal_ranking":
            errors.append("result.decision_boundary")
        if stages["realization"].get("availability") == "unavailable" and stages["realization"].get("attribution_status") != "unavailable_required_evidence_missing":
            errors.append("result.realization_boundary")
    eligible = {"perception", "retrieval", "state"}
    leading = value.get("leading_recoverable_stage")
    if leading is not None and leading not in eligible:
        errors.append("result.leading_stage")
    if value.get("unique_biological_or_psychological_cause_claim_authorized") is not False:
        errors.append("result.causal_claim")
    if value.get("retry_count") != 0 or value.get("fallback_count") != 0:
        errors.append("result.retry")
    if data_kind == "synthetic_engineering_only":
        if value.get("model_call_count") != 0 or value.get("real_target_outcome_access_count") != 0:
            errors.append("result.synthetic_access")
        if value.get("formal_result_created") is not False:
            errors.append("result.synthetic_formal")
    elif data_kind == "real_formal_m56_diagnostic":
        errors.append("result.real_formal_bridge_unavailable")
    return {"valid": not errors, "errors": errors, "analysis_hash": value.get("analysis_hash")}


def _distribution(observed: str, correct_probability: float) -> dict[str, float]:
    wrong = LABELS[(LABELS.index(observed) + 1) % len(LABELS)]
    remainder = 1.0 - correct_probability
    small = remainder * 0.08 / (len(LABELS) - 2)
    wrong_probability = remainder - small * (len(LABELS) - 2)
    return {
        label: correct_probability if label == observed else (wrong_probability if label == wrong else small)
        for label in LABELS
    }


def _stage_plans() -> dict[str, dict[str, Any]]:
    value: dict[str, dict[str, Any]] = {}
    for stage in load_contract()["stages"]:
        stage_id = stage["id"]
        plan = {
            "stage_id": stage_id,
            "substitution_target": stage["substitution_target"],
            "oracle_kind": stage["oracle_kind"],
            "required_provenance": stage["required_provenance"],
            "plan_committed_before_outcome": True,
            "evidence_timing": "post_outcome_upper_bound" if stage_id == "decision" else (
                "human_ratings_required_or_unavailable" if stage_id == "realization" else "pre_outcome_only"
            ),
            "eligibility": stage["eligible_for_leading_recoverable_stage"],
            "private_mental_truth_claimed": False,
        }
        plan["plan_hash"] = digest(plan)
        value[stage_id] = plan
    return value


def build_synthetic_bundle(*, ambiguous_tie: bool = False) -> dict[str, Any]:
    plans = _stage_plans()
    rows: list[dict[str, Any]] = []
    for index in range(30):
        observed = LABELS[index % len(LABELS)]
        original = _distribution(observed, 0.20)
        stage_probabilities: dict[str, dict[str, float] | None] = {
            "perception": _distribution(observed, 0.80 if ambiguous_tie else 0.35),
            "retrieval": _distribution(observed, 0.80),
            "state": deepcopy(original),
            "decision": {label: 1.0 if label == observed else 0.0 for label in LABELS},
            "realization": None,
        }
        substitutions: dict[str, dict[str, Any]] = {}
        for stage_id in STAGE_IDS:
            probabilities = stage_probabilities[stage_id]
            available = probabilities is not None
            substitutions[stage_id] = {
                "stage_id": stage_id,
                "availability": "available" if available else "unavailable",
                "changed_component": stage_id,
                "plan_hash": plans[stage_id]["plan_hash"],
                "downstream_recomputed": available,
                "probabilities": probabilities,
                "downstream_output_hash": digest(probabilities) if available else None,
                "evidence_available_before_outcome": False if stage_id in {"decision", "realization"} else True,
                "future_outcome_used": stage_id == "decision",
            }
        rows.append({
            "sample_id": f"synthetic-m57-{index + 1:02d}",
            "observed_label": observed,
            "original_probabilities": original,
            "original_output_hash": digest(original),
            "substitutions": substitutions,
        })
    value = {
        "schema": BUNDLE_SCHEMA,
        "version": "1.0.0",
        "status": "all_predictions_and_stage_plans_committed_before_outcome_scoring",
        "data_kind": "synthetic_engineering_only",
        "fixture_kind": "author_constructed_30_row_ambiguous_tie" if ambiguous_tie else "author_constructed_30_row_clear_retrieval_effect",
        "label_order": list(LABELS),
        "sample_count": 30,
        "prediction_commitment_hash": digest({"fixture": "ambiguous" if ambiguous_tie else "clear", "rows": rows}),
        "stage_plans": plans,
        "substitution_plan_commitment_hash": digest(plans),
        "outcome_access_after_all_predictions_committed": True,
        "same_resource_contract": True,
        "single_stage_change_verified": True,
        "retry_count": 0,
        "fallback_count": 0,
        "formal_authorization": False,
        "rows": rows,
        "claim_boundary": load_contract()["claim_boundary"],
    }
    value["bundle_hash"] = digest(value)
    validation = validate_bundle(value)
    if not validation["valid"]:
        raise AssertionError("invalid synthetic M57 bundle: " + "; ".join(validation["errors"]))
    return value


def build_engineering_rehearsal() -> dict[str, Any]:
    clear = analyze_component_substitution_bundle(build_synthetic_bundle())
    tied = analyze_component_substitution_bundle(build_synthetic_bundle(ambiguous_tie=True))
    value = {
        "schema": REHEARSAL_SCHEMA,
        "version": "1.0.0",
        "status": "clear_effect_localized_and_ambiguous_effect_abstained",
        "contract_hash": validate_contract()["contract_hash"],
        "fixture_kind": "two_author_constructed_30_row_mechanical_diagnostics_only",
        "clear_fixture": clear,
        "ambiguous_fixture": tied,
        "clear_expected_leading_stage": "retrieval",
        "clear_actual_leading_stage": clear["leading_recoverable_stage"],
        "ambiguous_expected_leading_stage": None,
        "ambiguous_actual_leading_stage": tied["leading_recoverable_stage"],
        "formal_model_call_count": 0,
        "real_target_outcome_access_count": 0,
        "formal_m57_result_created": False,
        "claim_boundary": load_contract()["claim_boundary"],
    }
    value["rehearsal_hash"] = digest(value)
    validation = validate_rehearsal(value)
    if not validation["valid"]:
        raise AssertionError("invalid M57 rehearsal: " + "; ".join(validation["errors"]))
    return value


def validate_rehearsal(value: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    expected = {
        "schema", "version", "status", "contract_hash", "fixture_kind", "clear_fixture",
        "ambiguous_fixture", "clear_expected_leading_stage", "clear_actual_leading_stage",
        "ambiguous_expected_leading_stage", "ambiguous_actual_leading_stage",
        "formal_model_call_count", "real_target_outcome_access_count", "formal_m57_result_created",
        "claim_boundary", "rehearsal_hash",
    }
    if not isinstance(value, dict) or set(value) != expected:
        return {"valid": False, "errors": ["rehearsal.fields"]}
    unhashed = {key: child for key, child in value.items() if key != "rehearsal_hash"}
    if value.get("rehearsal_hash") != digest(unhashed):
        errors.append("rehearsal.hash")
    if value.get("schema") != REHEARSAL_SCHEMA or value.get("status") != "clear_effect_localized_and_ambiguous_effect_abstained":
        errors.append("rehearsal.schema_or_status")
    if value.get("contract_hash") != validate_contract()["contract_hash"]:
        errors.append("rehearsal.contract")
    for fixture_name in ("clear_fixture", "ambiguous_fixture"):
        result_validation = validate_result(
            value.get(fixture_name) or {}, expected_data_kind="synthetic_engineering_only"
        )
        errors.extend(f"{fixture_name}.{error}" for error in result_validation["errors"])
    if value.get("clear_actual_leading_stage") != value.get("clear_expected_leading_stage") or value.get("clear_actual_leading_stage") != "retrieval":
        errors.append("rehearsal.clear")
    if value.get("ambiguous_expected_leading_stage") is not None or value.get("ambiguous_actual_leading_stage") is not None:
        errors.append("rehearsal.ambiguous")
    if (value.get("ambiguous_fixture") or {}).get("attribution_status") != "ambiguous_interacting_or_unresolved":
        errors.append("rehearsal.ambiguous_status")
    if value.get("formal_model_call_count") != 0 or value.get("real_target_outcome_access_count") != 0:
        errors.append("rehearsal.real_or_model")
    if value.get("formal_m57_result_created") is not False:
        errors.append("rehearsal.formal")
    return {"valid": not errors, "errors": errors, "rehearsal_hash": value.get("rehearsal_hash")}


def build_live_audit() -> dict[str, Any]:
    upstream = snapshot_m56.build_live_audit()
    value = {
        "schema": AUDIT_SCHEMA,
        "version": "1.0.0",
        "status": "m57_formal_localization_denied_missing_authorized_m56_result",
        "contract_valid": validate_contract()["valid"],
        "contract_hash": validate_contract()["contract_hash"],
        "counts": deepcopy(upstream["counts"]),
        "m56_formal_scoring_authorized": upstream["formal_scoring_authorized"],
        "m56_formal_result_created": upstream["formal_result_created"],
        "m57_formal_execution_authorized": False,
        "m57_formal_result_created": False,
        "target_outcome_access_count": 0,
        "formal_model_call_count": 0,
        "blocking_gates": deepcopy(upstream["blocking_gates"]) + ["authorized_m56_result_required"],
        "claim_boundary": load_contract()["claim_boundary"],
    }
    value["audit_hash"] = digest(value)
    return value


def validate_live_audit(value: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    expected = {
        "schema", "version", "status", "contract_valid", "contract_hash", "counts",
        "m56_formal_scoring_authorized", "m56_formal_result_created",
        "m57_formal_execution_authorized", "m57_formal_result_created",
        "target_outcome_access_count", "formal_model_call_count", "blocking_gates",
        "claim_boundary", "audit_hash",
    }
    if not isinstance(value, dict) or set(value) != expected:
        return {"valid": False, "errors": ["audit.fields"]}
    unhashed = {key: child for key, child in value.items() if key != "audit_hash"}
    if value.get("audit_hash") != digest(unhashed):
        errors.append("audit.hash")
    if value.get("schema") != AUDIT_SCHEMA or value.get("status") != "m57_formal_localization_denied_missing_authorized_m56_result":
        errors.append("audit.schema_or_status")
    if value.get("contract_valid") is not True or value.get("contract_hash") != validate_contract()["contract_hash"]:
        errors.append("audit.contract")
    counts = value.get("counts") or {}
    if counts.get("v7_slots_by_ledger") != [0, 0] or counts.get("real_temporal_rows") != 0:
        errors.append("audit.human_gate")
    for field in (
        "m56_formal_scoring_authorized", "m56_formal_result_created",
        "m57_formal_execution_authorized", "m57_formal_result_created",
    ):
        if value.get(field) is not False:
            errors.append(f"audit.{field}")
    if value.get("target_outcome_access_count") != 0 or value.get("formal_model_call_count") != 0:
        errors.append("audit.access")
    if "authorized_m56_result_required" not in (value.get("blocking_gates") or []):
        errors.append("audit.blocking_gate")
    return {"valid": not errors, "errors": errors, "audit_hash": value.get("audit_hash")}


def diagnose_formal_m56_components(run_id: str) -> dict[str, Any]:
    """Future formal entry; fail closed before outcome access while M56 is unavailable."""

    if not isinstance(run_id, str) or not run_id or "/" in run_id or ".." in run_id:
        raise ValueError("invalid run_id")
    audit = build_live_audit()
    if not audit["m57_formal_execution_authorized"]:
        raise PermissionError("M57 formal localization denied: authorized M56 result is required")
    raise PermissionError("M57 formal artifact bridge is not activated by the frozen readiness contract")


def load_saved_rehearsal(path: str | Path = RESULT_PATH) -> dict[str, Any]:
    value = load_json(path)
    validation = validate_rehearsal(value)
    if not validation["valid"]:
        raise PermissionError("invalid saved M57 rehearsal: " + "; ".join(validation["errors"]))
    return value


def render_dashboard(rehearsal: dict[str, Any] | None = None, audit: dict[str, Any] | None = None) -> str:
    rehearsal = deepcopy(rehearsal or load_saved_rehearsal())
    audit = deepcopy(audit or build_live_audit())
    if not validate_rehearsal(rehearsal)["valid"]:
        raise PermissionError("invalid M57 rehearsal cannot be rendered")
    clear = rehearsal["clear_fixture"]
    tied = rehearsal["ambiguous_fixture"]
    stage_names = {
        "perception": "聽懂當下輸入",
        "retrieval": "找對過去記憶",
        "state": "形成內部狀態",
        "decision": "選擇下一步",
        "realization": "說成自然日文",
    }
    status_names = {
        "recoverable_effect": "替換後有恢復",
        "no_recoverable_effect": "沒有可恢復差異",
        "diagnostic_upper_bound_excluded_from_causal_ranking": "只作上限，不參與判因",
        "unavailable_required_evidence_missing": "缺少獨立人類評分",
    }
    eligible_deltas = [
        max(0.0, clear["stage_results"][stage_id]["deltas_original_minus_substitution"]["brier"])
        for stage_id in ("perception", "retrieval", "state")
    ]
    maximum_delta = max(eligible_deltas) or 1.0
    cards: list[str] = []
    for stage_id in STAGE_IDS:
        stage = clear["stage_results"][stage_id]
        delta = stage["deltas_original_minus_substitution"]
        bar_width = 0.0 if delta is None else min(100.0, max(0.0, delta["brier"]) / maximum_delta * 100.0)
        metric = "無正式評分" if delta is None else (
            "診斷上限（排除）" if stage_id == "decision" else f"Brier 恢復量 {delta['brier']:.3f}"
        )
        cards.append(
            f'<div class="stage {"lead" if stage_id == clear["leading_recoverable_stage"] else ""}">'
            f'<b>{html.escape(stage_id.upper())}</b><em>{html.escape(stage_names[stage_id])}</em>'
            f'<div class="bar"><i style="width:{bar_width:.1f}%"></i></div>'
            f'<small>{html.escape(metric)}</small><span>{html.escape(status_names[stage["attribution_status"]])}</span></div>'
        )
    stage_cards = "".join(cards)
    counts = audit["counts"]
    return f"""<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>M57 元件錯誤定位</title><style>
*{{box-sizing:border-box}}body{{margin:0;background:#07131c;color:#eefbff;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}main{{max-width:1180px;margin:auto;padding:28px}}section{{border:1px solid #31586c;border-radius:20px;background:#0c202c;padding:24px;margin-bottom:18px}}.hero{{background:linear-gradient(135deg,#193c49,#31263e)}}.deny{{display:inline-block;padding:8px 12px;border-radius:999px;background:#672633;color:#ffdae0;font-weight:850}}h1{{font-size:clamp(30px,5vw,44px);margin:14px 0 8px}}p{{color:#c2dce5;line-height:1.62}}.flow{{display:grid;grid-template-columns:1fr auto 1fr;gap:15px;align-items:center}}.box{{border:1px solid #375e73;border-radius:17px;background:#091a25;padding:19px;min-height:130px;min-width:0}}.arrow{{font-size:34px;color:#ffd481;font-weight:900}}.stages{{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px}}.stage{{border:1px solid #3c5e70;border-radius:15px;background:#091a25;padding:15px;min-height:150px;min-width:0}}.stage b,.stage em,.stage span,.stage small{{display:block;overflow-wrap:anywhere}}.stage b{{color:#9dbfce;margin-bottom:4px}}.stage em{{font-style:normal;font-weight:800;margin-bottom:13px}}.stage small{{color:#b9d0d8;margin:7px 0}}.stage span{{font-size:12px;color:#b9d0d8}}.bar{{height:9px;border-radius:999px;background:#233846;overflow:hidden}}.bar i{{display:block;height:100%;background:#6bd9b4;border-radius:inherit}}.stage.lead{{border:2px solid #58d5ac;background:#103129}}.stage.lead b{{color:#76ebc4}}.compare{{display:grid;grid-template-columns:1fr 1fr;gap:14px}}.clear{{border-color:#4fae8f}}.amb{{border-color:#bd8a45}}.metric{{font-size:28px;font-weight:900;color:#75e9c3}}.boundary{{border-left:6px solid #e1a452;background:#272014}}@media(max-width:850px){{.flow,.compare{{grid-template-columns:1fr}}.arrow{{text-align:center;transform:rotate(90deg)}}}}
</style></head><body><main><section class="hero"><span class="deny">FORMAL M57 DENIED · V7 {counts['v7_slots_by_ledger'][0]}/18 + {counts['v7_slots_by_ledger'][1]}/18</span><h1>M57 · 不只問「有沒有比較好」，還要問「錯在哪一層」</h1><p>M56只能給總分；M57先凍結每一層的單一替換，再量測Brier/NLL是否真的恢復。沒有來源的內心狀態不會被假裝成oracle。</p></section><section><h2>從總分到可反駁診斷</h2><div class="flow"><div class="box"><h3>M56 AGGREGATE</h3><p>7 conditions · 30 paired rows · winner/loser</p></div><div class="arrow">→</div><div class="box"><h3>M57 COMPONENT SUBSTITUTION</h3><p>perception → retrieval → state proxy → decision ceiling → realization rating</p></div></div></section><section><h2>作者構造的機械驗證，不是真人結果</h2><div class="stages">{stage_cards}</div></section><section><div class="compare"><div class="box clear"><h3>清楚效果 fixture</h3><div class="metric">leading = {html.escape(str(clear['leading_recoverable_stage']))}</div><p>retrieval替換在Brier與NLL都領先；只證明analyzer能找出預先構造的訊號。</p></div><div class="box amb"><h3>同分／互動 fixture</h3><div class="metric">leading = {html.escape(str(tied['leading_recoverable_stage']))}</div><p>{html.escape(tied['attribution_status'])}；系統必須保留不確定，不能硬選一層。</p></div></div></section><section class="boundary"><h2>現在仍不能說</h2><p>這一頁只證明診斷器能在預先構造的訊號中找出明確差異，並在同分時拒絕亂猜。它還沒有定位任何真實 Uruha 錯誤，也不能證明讀懂私人心理、人類方程式成立，或全面勝過一般 LLM。</p><p>目前真人時間資料 = {counts['real_temporal_rows']}/30，兩位標註者 = {counts['v7_slots_by_ledger'][0]}/18 + {counts['v7_slots_by_ledger'][1]}/18，formal M56 result = 0，因此正式 M57 仍禁止執行。</p></section></main></body></html>"""


def serve_demo(port: int) -> None:
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    page = render_dashboard().encode("utf-8")

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            if self.path not in ("/", "/dashboard"):
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(page)))
            self.end_headers()
            self.wfile.write(page)

        def log_message(self, format: str, *args: Any) -> None:
            del format, args

    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser(description="M57 component error-localization readiness")
    parser.add_argument("--rehearsal", action="store_true")
    parser.add_argument("--audit", action="store_true")
    parser.add_argument("--serve", type=int)
    args = parser.parse_args()
    if args.serve is not None:
        serve_demo(args.serve)
    elif args.rehearsal:
        print(json.dumps(build_engineering_rehearsal(), ensure_ascii=False, indent=2))
    else:
        print(json.dumps(build_live_audit(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
