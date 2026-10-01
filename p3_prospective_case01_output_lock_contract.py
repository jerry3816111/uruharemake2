#!/usr/bin/env python3
"""P3-B34 zero-call contract for prospective case01 dual-condition output lock."""

from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
from pathlib import Path
from typing import Any, Mapping

import p3_case03_dual_condition_output_lock as engine
import p3_case05_dual_condition_output_lock as helper
from p3_direct_baseline_v2_design_review import load_review
from p3_product_comparison import P3ContractError, canonical_sha256, load_design, write_new_json
from p3_product_worker import LocalOllamaQwenStageCounter, _ollama_model_metadata


SCHEMA = "uruha_p3_prospective_case01_output_lock_v1"
MODEL_DIGEST = engine.MODEL_DIGEST
CASE_ID = "p3-prospective-v2-overwhelm-company-zh"
TURN_IDS = [f"p3-prospective-v2-01-u{i}" for i in range(1, 5)]


def load_config(path: str | Path) -> dict[str, Any]:
    config_path = Path(path).resolve()
    raw = helper._read(config_path)
    expected_root = {
        "schema", "phase", "status", "purpose", "comparison_design",
        "direct_v2_review", "source_freeze", "case_source", "judge_transport",
        "selection", "conditions", "common_history", "session_boundary",
        "direct_instruction", "generation", "execution_boundary", "retention", "success",
    }
    if set(raw) != expected_root or raw.get("schema") != SCHEMA or raw.get("phase") != "P3-B34":
        raise P3ContractError("p3_b34_schema_mismatch")
    if raw.get("status") != "preregistered_not_executed" or raw.get("purpose") != (
        "freeze_case01_dual_condition_generation_contract_before_output_or_annotation_access"
    ):
        raise P3ContractError("p3_b34_status_mismatch")
    repo = config_path.parent.parent
    design_path = helper._ref(repo, raw["comparison_design"], {
        "path": "configs/p3_product_comparison_v1.json",
        "sha256": "1e6d3b0600740b3dee7207ffc5c4f9cc9247a5feba2b967bdab4586522f7b836",
    }, "p3_b34_design_mismatch")
    review_path = helper._ref(repo, raw["direct_v2_review"], {
        "path": "configs/p3_direct_baseline_v2_design_review_v1.json",
        "sha256": "2d0a17759e4daa4f7fd9cc2533cda3d285d5c04bf88c8f7428dc96e194aeed53",
    }, "p3_b34_review_mismatch")
    freeze_path = helper._ref(repo, raw["source_freeze"], {
        "path": "research/p3_b33_prospective_source_only_freeze_2026-09-17.json",
        "sha256": "c9fb2f5289913e2b460ff01c3650e773c8df0bdd8ff3e03194aab14872e90b90",
        "required_status": "prospective_source_only_frozen",
    }, "p3_b34_source_freeze_mismatch")
    source_path = helper._ref(repo, raw["case_source"], {
        "path": "datasets/p3_prospective_case01_generation_source_v1.json",
        "sha256": "070c38544eeaa2c3015d9eebe890cf6f8516630a355acbb2b1e8aa2c7e0bcd7f",
    }, "p3_b34_source_mismatch")
    judge_path = helper._ref(repo, raw["judge_transport"], {
        "path": "analysis/p3_b32_exact_evidence_native_conformance_result_2026-09-17.json",
        "sha256": "8d610c380ed96c3f73075f4042a92a75da292418d8d5338da23a4fd6505e975b",
        "required_status": "exact_evidence_native_conformance_pass",
    }, "p3_b34_judge_transport_mismatch")
    design = load_design(design_path)
    review = load_review(review_path)
    freeze = helper._read(freeze_path)
    source = helper._read(source_path)
    judge = helper._read(judge_path)
    if freeze.get("status") != raw["source_freeze"]["required_status"]:
        raise P3ContractError("p3_b34_source_freeze_status_invalid")
    if judge.get("status") != raw["judge_transport"]["required_status"] or not all(
        (judge.get("checks") or {}).values()
    ):
        raise P3ContractError("p3_b34_judge_transport_status_invalid")
    if raw.get("selection") != {
        "rule": "first_case_in_immutable_source_order",
        "case_index_zero_based": 0,
        "quality_based_selection": False,
    }:
        raise P3ContractError("p3_b34_selection_drift")
    parent_ref = source.get("parent_source") or {}
    source_repo = source_path.parent.parent
    parent_path = (source_repo / str(parent_ref.get("path"))).resolve()
    if (
        not parent_path.is_file()
        or hashlib.sha256(parent_path.read_bytes()).hexdigest() != parent_ref.get("sha256")
    ):
        raise P3ContractError("p3_b34_parent_source_mismatch")
    parent = helper._read(parent_path)
    if not parent.get("cases") or parent["cases"][0].get("case_id") != CASE_ID:
        raise P3ContractError("p3_b34_first_case_selection_invalid")
    parent_case = parent["cases"][0]
    freeze_ref = source.get("source_freeze") or {}
    if (
        freeze_ref.get("path") != raw["source_freeze"]["path"]
        or freeze_ref.get("sha256") != raw["source_freeze"]["sha256"]
        or source.get("selection_rule") != "first_case_in_immutable_p3_b33_source_order"
    ):
        raise P3ContractError("p3_b34_projection_freeze_mismatch")
    if source.get("turns") != parent_case.get("turns") or source.get("sessions") != parent_case.get("sessions"):
        raise P3ContractError("p3_b34_source_projection_mismatch")
    if (
        source.get("case_id") != CASE_ID
        or source.get("family") != "solution_rejection_and_co-regulated_complaint"
        or source.get("language") != "zh"
        or source.get("annotations_included") is not False
        or source.get("generation_executed") is not False
    ):
        raise P3ContractError("p3_b34_source_identity_invalid")
    if [turn.get("turn_id") for turn in source.get("turns", [])] != TURN_IDS or any(
        hashlib.sha256(turn["content"].encode("utf-8")).hexdigest() != turn["content_sha256"]
        for turn in source.get("turns", [])
    ):
        raise P3ContractError("p3_b34_turns_invalid")
    if raw.get("conditions") != ["product_system", "full_history_direct"]:
        raise P3ContractError("p3_b34_conditions_invalid")
    if raw.get("common_history") != {
        "mode": "system_anchored_prefix_paired",
        "include_all_prior_sessions": True,
        "include_roles": True,
        "include_only_past_visible_messages": True,
        "baseline_output_written_back": False,
        "current_product_reply_visible_to_baseline": False,
        "product_visible_reply_added_after_both_current_views_freeze": True,
        "cross_case_state_shared": False,
        "truncate_or_summarize": False,
    }:
        raise P3ContractError("p3_b34_history_drift")
    if raw.get("session_boundary") != {
        "restart_product_before_turn_ids": [TURN_IDS[2]],
        "same_case_memory_path_retained": True,
        "new_brain_instance": True,
    }:
        raise P3ContractError("p3_b34_session_drift")
    if raw.get("direct_instruction") != review["direct_baseline"]["instruction"]:
        raise P3ContractError("p3_b34_direct_instruction_drift")
    model = design["model"]
    budget = design["budget"]["per_condition_turn"]
    if raw.get("generation") != {
        "model": model["generation_model"],
        "digest": MODEL_DIGEST,
        "temperature": model["temperature"],
        "seed": model["seed"],
        "top_p": model["top_p"],
        "num_ctx": model["num_ctx"],
        "think": model["think"],
        "aggregate_prompt_tokens_max_per_condition_turn": budget["aggregate_prompt_tokens_max"],
        "aggregate_completion_tokens_max_per_condition_turn": budget["aggregate_completion_tokens_max"],
        "product_calls_max_per_turn": design["budget"]["system_calls_max"],
        "direct_calls_exact_per_turn": design["budget"]["direct_calls_max"],
        "wall_seconds_max_per_condition_turn": budget["wall_seconds_max"],
    }:
        raise P3ContractError("p3_b34_generation_drift")
    if raw.get("execution_boundary") != {
        "source_turns_exact": 4,
        "visible_outputs_exact": 8,
        "product_provider_calls_min": 0,
        "product_provider_calls_max": 16,
        "direct_provider_calls_exact": 4,
        "total_provider_calls_max": 20,
        "turn_intents_exact": 8,
        "completed_turn_records_exact": 8,
        "automatic_retry": False,
        "stop_on_first_transport_or_validation_failure": True,
        "concurrency": 1,
        "localhost_only": True,
        "prior_case_calls_reused_or_counted": False,
        "annotation_access": False,
        "confirmation_access": False,
        "production_database_access": False,
        "external_deployment": False,
        "remote_paid_calls": False,
        "real_model_calls_authorized_by_this_config": False,
        "separate_release_required": True,
    }:
        raise P3ContractError("p3_b34_boundary_drift")
    if raw.get("retention") != {
        "visible_replies": True,
        "product_runtime_trace": True,
        "product_memory_snapshot": True,
        "per_call_usage_and_hashes": True,
        "raw_provider_payload": False,
        "partial_failure_evidence": True,
        "ephemeral_workspace_removed": True,
    }:
        raise P3ContractError("p3_b34_retention_drift")
    if raw.get("success") != {
        "all_eight_visible_outputs_nonempty": True,
        "all_eight_shared_surface_pass": True,
        "all_four_view_pairs_share_source_and_prefix": True,
        "all_actual_provider_and_network_calls_accounted": True,
        "all_eight_turn_intents_and_completions_accounted": True,
        "all_condition_turn_budgets_valid": True,
        "session_restart_preserves_case_paths": True,
        "product_state_isolated_and_workspace_removed": True,
        "zero_annotation_or_production_access": True,
    }:
        raise P3ContractError("p3_b34_success_drift")
    design = deepcopy(design)
    design["baselines"]["direct_instruction"] = raw["direct_instruction"]
    result = deepcopy(raw)
    result.update({
        "_repo": repo,
        "_config_path": config_path,
        "_config_sha256": hashlib.sha256(config_path.read_bytes()).hexdigest(),
        "_source": source,
        "_source_freeze": freeze,
        "_judge_transport": judge,
        "_design": design,
    })
    return result


def build_preflight(path: str | Path) -> dict[str, Any]:
    config = load_config(path)
    metadata = _ollama_model_metadata(config["generation"]["model"])
    counter = LocalOllamaQwenStageCounter(merge_adjacent_assistant=True)
    first = config["_source"]["turns"][0]
    messages = [
        {
            "role": "system",
            "content": config["_design"]["persona"]["shared_contract"]
            + "\n"
            + config["direct_instruction"],
        },
        {"role": "user", "content": first["content"]},
    ]
    prefix: list[dict[str, str]] = []
    paired_views = []
    future_locks = []
    turns = config["_source"]["turns"]
    validation_path = config["_repo"] / config["_source_freeze"]["artifacts"]["validation"]["path"]
    validation = helper._read(validation_path)
    manifest = {
        row["turn_id"]: row
        for row in validation.get("turn_visibility_manifest", [])
        if row.get("case_id") == CASE_ID
    }
    for index, turn in enumerate(turns):
        views = engine.build_views(prefix, turn)
        product = views["product_system"]
        direct = views["full_history_direct"]
        paired_views.append(
            product["source_history_sha256"] == direct["source_history_sha256"]
            and product["input_sha256"] == direct["input_sha256"]
            and len(product["visible_prefix"]) == len(direct["visible_prefix"]) == index * 2
        )
        row = manifest.get(turn["turn_id"]) or {}
        future_locks.append(
            row.get("visible_turn_ids") == [item["turn_id"] for item in turns[: index + 1]]
            and row.get("locked_future_turn_ids") == [item["turn_id"] for item in turns[index + 1 :]]
        )
        engine.append_product_prefix(prefix, turn, f"未生成product-{turn['turn_id']}")
    checks = {
        "config_valid": True,
        "model_digest_matches": metadata["digest"] == MODEL_DIGEST,
        "first_case_selected_by_immutable_order_not_quality": config["selection"]["case_index_zero_based"] == 0
        and config["selection"]["quality_based_selection"] is False,
        "four_source_turns": len(turns) == 4,
        "all_offline_view_pairs_share_source": all(paired_views),
        "all_future_turns_locked_by_b33_manifest": all(future_locks),
        "first_direct_prompt_count_available": counter(messages) > 0,
        "session_restart_boundary_exact": config["session_boundary"]["restart_product_before_turn_ids"] == [TURN_IDS[2]],
        "zero_call_product_turns_allowed_but_not_required": config["execution_boundary"]["product_provider_calls_min"] == 0,
        "direct_calls_remain_exactly_four": config["execution_boundary"]["direct_provider_calls_exact"] == 4,
        "turn_intents_and_records_exactly_eight": config["execution_boundary"]["turn_intents_exact"]
        == config["execution_boundary"]["completed_turn_records_exact"]
        == 8,
        "annotations_closed": config["execution_boundary"]["annotation_access"] is False,
        "config_does_not_self_authorize": config["execution_boundary"]["real_model_calls_authorized_by_this_config"] is False,
        "b32_exact_evidence_transport_bound_for_later_grade": config["judge_transport"]["required_status"]
        == "exact_evidence_native_conformance_pass",
    }
    return {
        "schema": "uruha_p3_prospective_case01_output_lock_preflight_v1",
        "phase": "P3-B34",
        "status": "ready_for_prospective_case01_output_lock_review" if all(checks.values())
        else "not_ready_for_prospective_case01_output_lock_review",
        "config_sha256": config["_config_sha256"],
        "checks": checks,
        "model_metadata": metadata,
        "first_direct_prompt_tokens": counter(messages),
        "case_id": CASE_ID,
        "turn_ids": TURN_IDS,
        "source_sha256": config["case_source"]["sha256"],
        "source_freeze_sha256": config["source_freeze"]["sha256"],
        "judge_transport_sha256": config["judge_transport"]["sha256"],
        "real_model_calls": 0,
        "network_calls": 0,
        "paid_calls": 0,
        "annotations_accessed": 0,
        "confirmation_accessed": 0,
        "production_database_accessed": False,
        "claim_boundary": (
            "Preflight only. The first prospective developer case is selected by immutable order; "
            "no output, annotation, quality grade, holdout, human preference, or advantage result exists."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = Path(args.output)
    if output.exists():
        return 2
    try:
        payload = build_preflight(args.config)
    except P3ContractError as exc:
        payload = {
            "schema": "uruha_p3_prospective_case01_output_lock_preflight_refusal_v1",
            "phase": "P3-B34",
            "status": "prospective_case01_output_lock_refused",
            "contract_code": exc.code,
            "real_model_calls": 0,
            "network_calls": 0,
            "claim_boundary": "No output lock or quality claim is authorized.",
        }
    write_new_json(output, payload)
    return 0 if payload.get("status") == "ready_for_prospective_case01_output_lock_review" else 1


if __name__ == "__main__":
    raise SystemExit(main())
