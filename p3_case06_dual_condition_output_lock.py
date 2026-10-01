#!/usr/bin/env python3
"""P3-B27 freeze case06 with the existing zero-call-aware comparison contract."""

from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
from pathlib import Path
from typing import Any, Mapping

import p3_case03_dual_condition_output_lock as engine
import p3_case05_dual_condition_output_lock as case05
from p3_direct_baseline_v2_design_review import load_review
from p3_product_comparison import P3ContractError, canonical_sha256, load_design, write_new_json
from p3_product_worker import LocalOllamaQwenStageCounter, _ollama_model_metadata, summarize_checkpoint_evidence


SCHEMA = "uruha_p3_case06_dual_condition_output_lock_v1"
RELEASE_SCHEMA = "uruha_p3_case06_dual_condition_output_lock_release_v1"
MODEL_DIGEST = engine.MODEL_DIGEST


def load_config(path: str | Path) -> dict[str, Any]:
    config_path = Path(path).resolve()
    raw = case05._read(config_path)
    if set(raw) != {
        "schema", "phase", "status", "purpose", "comparison_design", "direct_v2_review",
        "case_source", "judge_conformance", "conditions", "common_history", "session_boundary",
        "direct_instruction", "generation", "execution_boundary", "retention", "success",
    } or raw.get("schema") != SCHEMA or raw.get("phase") != "P3-B27":
        raise P3ContractError("p3_b27_schema_mismatch")
    if raw.get("status") != "preregistered_not_executed" or raw.get("purpose") != (
        "lock_complete_preexisting_case06_product_and_direct_outputs_before_annotation_access_with_zero_call_aware_accounting"
    ):
        raise P3ContractError("p3_b27_status_mismatch")

    repo = config_path.parent.parent
    design_path = case05._ref(repo, raw["comparison_design"], {
        "path": "configs/p3_product_comparison_v1.json",
        "sha256": "1e6d3b0600740b3dee7207ffc5c4f9cc9247a5feba2b967bdab4586522f7b836",
    }, "p3_b27_design_mismatch")
    review_path = case05._ref(repo, raw["direct_v2_review"], {
        "path": "configs/p3_direct_baseline_v2_design_review_v1.json",
        "sha256": "2d0a17759e4daa4f7fd9cc2533cda3d285d5c04bf88c8f7428dc96e194aeed53",
    }, "p3_b27_review_mismatch")
    source_path = case05._ref(repo, raw["case_source"], {
        "path": "datasets/p3_case06_generation_source_v1.json",
        "sha256": "c421f96f811d3eee2da5a05e8753cbb51ea36e1f133dde84cc0d1b5d3b8a13dc",
    }, "p3_b27_source_mismatch")
    judge_path = case05._ref(repo, raw["judge_conformance"], {
        "path": "analysis/p3_b19_native_judge_schema_result_2026-09-15.json",
        "sha256": "5b01e324116123ceacca0f44eb39bac05cae56b595ec953bd25c00e58b4de6d1",
        "required_status": "native_judge_schema_conformance_pass",
    }, "p3_b27_judge_mismatch")
    design = load_design(design_path)
    review = load_review(review_path)
    source = case05._read(source_path)
    judge = case05._read(judge_path)
    if judge.get("status") != "native_judge_schema_conformance_pass":
        raise P3ContractError("p3_b27_judge_status_invalid")

    parent_path = repo / source["parent_source"]["path"]
    if hashlib.sha256(parent_path.read_bytes()).hexdigest() != source["parent_source"]["sha256"]:
        raise P3ContractError("p3_b27_parent_source_mismatch")
    parent = case05._read(parent_path)
    parent_case = next((item for item in parent.get("cases", []) if item.get("case_id") == source.get("case_id")), None)
    if not isinstance(parent_case, Mapping) or source.get("turns") != parent_case.get("turns") or source.get("sessions") != parent_case.get("sessions"):
        raise P3ContractError("p3_b27_source_projection_mismatch")
    if (
        source.get("case_id") != "p3-smoke-unknown-topic-ja"
        or source.get("family") != "unknown_and_topic_change"
        or source.get("language") != "ja"
        or source.get("annotations_included") is not False
    ):
        raise P3ContractError("p3_b27_source_identity_invalid")
    if len(source.get("turns", [])) != 4 or any(
        canonical_sha256(turn["content"]) != turn["content_sha256"] for turn in source["turns"]
    ):
        raise P3ContractError("p3_b27_turns_invalid")

    if raw.get("conditions") != ["product_system", "full_history_direct"]:
        raise P3ContractError("p3_b27_conditions_invalid")
    if raw.get("common_history") != {
        "mode": "system_anchored_prefix_paired", "include_all_prior_sessions": True,
        "include_roles": True, "include_only_past_visible_messages": True,
        "baseline_output_written_back": False, "current_product_reply_visible_to_baseline": False,
        "product_visible_reply_added_after_both_current_views_freeze": True,
        "cross_case_state_shared": False, "truncate_or_summarize": False,
    }:
        raise P3ContractError("p3_b27_history_drift")
    if raw.get("session_boundary") != {
        "restart_product_before_turn_ids": ["p3-smoke-06-u3"],
        "same_case_memory_path_retained": True, "new_brain_instance": True,
    }:
        raise P3ContractError("p3_b27_session_drift")
    if raw.get("direct_instruction") != review["direct_baseline"]["instruction"]:
        raise P3ContractError("p3_b27_direct_instruction_drift")

    model, budget = design["model"], design["budget"]["per_condition_turn"]
    if raw.get("generation") != {
        "model": model["generation_model"], "digest": MODEL_DIGEST,
        "temperature": model["temperature"], "seed": model["seed"], "top_p": model["top_p"],
        "num_ctx": model["num_ctx"], "think": model["think"],
        "aggregate_prompt_tokens_max_per_condition_turn": budget["aggregate_prompt_tokens_max"],
        "aggregate_completion_tokens_max_per_condition_turn": budget["aggregate_completion_tokens_max"],
        "product_calls_max_per_turn": design["budget"]["system_calls_max"],
        "direct_calls_exact_per_turn": design["budget"]["direct_calls_max"],
        "wall_seconds_max_per_condition_turn": budget["wall_seconds_max"],
    }:
        raise P3ContractError("p3_b27_generation_drift")
    if raw.get("execution_boundary") != {
        "source_turns_exact": 4, "visible_outputs_exact": 8,
        "product_provider_calls_min": 0, "product_provider_calls_max": 16,
        "direct_provider_calls_exact": 4, "total_provider_calls_max": 20,
        "automatic_retry": False, "concurrency": 1, "localhost_only": True,
        "prior_case_calls_reused_or_counted": False, "annotation_access": False,
        "confirmation_access": False, "production_database_access": False,
        "external_deployment": False, "remote_paid_calls": False,
        "real_model_calls_authorized_by_this_config": False,
    }:
        raise P3ContractError("p3_b27_boundary_drift")
    if raw.get("retention") != {
        "visible_replies": True, "product_runtime_trace": True, "product_memory_snapshot": True,
        "per_call_usage_and_hashes": True, "raw_provider_payload": False,
        "partial_failure_evidence": True, "ephemeral_workspace_removed": True,
    } or raw.get("success") != {
        "all_eight_visible_outputs_nonempty": True, "all_eight_shared_surface_pass": True,
        "all_four_view_pairs_share_source_and_prefix": True,
        "all_actual_provider_and_network_calls_accounted": True,
        "all_eight_turn_intents_and_completions_accounted": True,
        "all_condition_turn_budgets_valid": True,
        "session_restart_preserves_case_paths": True,
        "product_state_isolated_and_workspace_removed": True,
        "zero_annotation_or_production_access": True,
    }:
        raise P3ContractError("p3_b27_success_drift")

    design = deepcopy(design)
    design["baselines"]["direct_instruction"] = raw["direct_instruction"]
    result = deepcopy(raw)
    result.update({
        "_repo": repo, "_config_path": config_path,
        "_config_sha256": hashlib.sha256(config_path.read_bytes()).hexdigest(),
        "_source": source, "_design": design,
    })
    return result


def build_preflight(path: str | Path) -> dict[str, Any]:
    config = load_config(path)
    metadata = _ollama_model_metadata(config["generation"]["model"])
    counter = LocalOllamaQwenStageCounter(merge_adjacent_assistant=True)
    first = config["_source"]["turns"][0]
    messages = [
        {"role": "system", "content": config["_design"]["persona"]["shared_contract"] + "\n" + config["direct_instruction"]},
        {"role": "user", "content": first["content"]},
    ]
    prefix: list[dict[str, str]] = []
    pairs = []
    for turn in config["_source"]["turns"]:
        views = engine.build_views(prefix, turn)
        pairs.append(
            views["product_system"]["source_history_sha256"] == views["full_history_direct"]["source_history_sha256"]
            and views["product_system"]["input_sha256"] == views["full_history_direct"]["input_sha256"]
        )
        engine.append_product_prefix(prefix, turn, f"未生成product-{turn['turn_id']}")
    checks = {
        "config_valid": True,
        "model_digest_matches": metadata["digest"] == MODEL_DIGEST,
        "four_source_turns": len(config["_source"]["turns"]) == 4,
        "all_offline_view_pairs_share_source": all(pairs),
        "first_direct_prompt_count_available": counter(messages) > 0,
        "session_restart_boundary_exact": config["session_boundary"]["restart_product_before_turn_ids"] == ["p3-smoke-06-u3"],
        "zero_call_product_turns_allowed_but_not_required": config["execution_boundary"]["product_provider_calls_min"] == 0,
        "direct_calls_remain_exactly_four": config["execution_boundary"]["direct_provider_calls_exact"] == 4,
        "annotations_closed": config["execution_boundary"]["annotation_access"] is False,
        "config_does_not_self_authorize": config["execution_boundary"]["real_model_calls_authorized_by_this_config"] is False,
        "native_judge_conformance_bound_for_later_grade": config["judge_conformance"]["required_status"] == "native_judge_schema_conformance_pass",
    }
    return {
        "schema": "uruha_p3_case06_output_lock_preflight_v1", "phase": "P3-B27",
        "status": "ready_for_case06_output_lock_review" if all(checks.values()) else "not_ready_for_case06_output_lock_review",
        "config_sha256": config["_config_sha256"], "checks": checks,
        "model_metadata": metadata, "first_direct_prompt_tokens": counter(messages),
        "turn_ids": [turn["turn_id"] for turn in config["_source"]["turns"]],
        "real_model_calls": 0, "network_calls": 0, "paid_calls": 0,
        "annotations_accessed": 0, "confirmation_accessed": 0,
        "claim_boundary": "Preflight only; no case output or quality grade is produced.",
    }


def validate_release(path: str | Path, config: Mapping[str, Any]) -> dict[str, Any]:
    release_path, release = Path(path), case05._read(Path(path))
    if (
        release.get("schema") != RELEASE_SCHEMA
        or release.get("phase") != "P3-B27"
        or release.get("status") != "released_for_case06_output_lock"
    ):
        raise P3ContractError("p3_b27_release_invalid")
    expected = {
        "config": "configs/p3_case06_dual_condition_output_lock_v1.json",
        "wrapper": "p3_case06_dual_condition_output_lock.py",
        "engine": "p3_case03_dual_condition_output_lock.py",
        "accounting_helper": "p3_case05_dual_condition_output_lock.py",
        "tests": "test_p3_case06_dual_condition_output_lock.py",
        "preflight": "analysis/p3_b27_case06_output_lock_preflight_2026-09-16.json",
    }
    if set(release.get("artifacts", {})) != set(expected):
        raise P3ContractError("p3_b27_release_artifacts_invalid")
    repo = release_path.resolve().parent.parent
    for name, relative in expected.items():
        actual = {"path": relative, "sha256": hashlib.sha256((repo / relative).read_bytes()).hexdigest()}
        if release["artifacts"][name] != actual:
            raise P3ContractError("p3_b27_release_artifact_mismatch", name)
    if release.get("authorization") != {
        "run_id": "p3-b28-case06-output-lock-v1", "localhost_only": True,
        "model": "qwen2.5:7b", "model_digest": MODEL_DIGEST,
        "case_id": "p3-smoke-unknown-topic-ja",
        "turn_ids": ["p3-smoke-06-u1", "p3-smoke-06-u2", "p3-smoke-06-u3", "p3-smoke-06-u4"],
        "product_provider_calls_min": 0, "product_provider_calls_max": 16,
        "direct_provider_calls_exact": 4, "total_provider_calls_max": 20,
        "turn_intents_exact": 8, "completed_turn_records_exact": 8,
        "automatic_retry": False,
        "checkpoint_root": "analysis/p3_b28_case06_output_lock_checkpoints_v1",
        "result_path": "analysis/p3_b28_case06_output_lock_result_2026-09-16.json",
        "annotation_access": False, "confirmation_access": False,
        "production_database_access": False, "external_deployment": False,
    }:
        raise P3ContractError("p3_b27_release_authorization_invalid")
    if case05._read(repo / release["artifacts"]["preflight"]["path"]).get("status") != "ready_for_case06_output_lock_review":
        raise P3ContractError("p3_b27_release_preflight_invalid")
    return release


def transform_result(result: Mapping[str, Any], evidence: Mapping[str, Any]) -> dict[str, Any]:
    transformed = deepcopy(dict(result))
    checks = dict(transformed.get("checks", {}))
    checks.pop("all_provider_calls_accounted", None)
    calls_ok, records_ok, product_count, direct_count = case05._actual_call_accounting(transformed, evidence)
    checks["all_actual_provider_and_network_calls_accounted"] = calls_ok
    checks["all_eight_turn_intents_and_completions_accounted"] = records_ok
    transformed.update({
        "schema": "uruha_p3_case06_dual_condition_output_lock_result_v1",
        "phase": "P3-B28",
        "status": "case06_outputs_locked" if all(checks.values()) else "case06_output_lock_failed_retained",
        "checks": checks, "checkpoint_evidence": dict(evidence),
        "product_provider_calls": product_count, "direct_provider_calls": direct_count,
        "provider_call_evidence": product_count + direct_count,
        "real_model_calls": product_count + direct_count,
        "network_calls": product_count + direct_count,
        "prior_case_calls_reused_or_counted": False,
        "claim_boundary": "Pre-existing developer-smoke case06 outputs are locked before annotation access. This is generation evidence only, not a B24 generalization, formal holdout, human preference, or advantage result.",
    })
    transformed.pop("b15_calls_reused_or_counted", None)
    return transformed


def run_case(
    config_path: str | Path,
    release_path: str | Path,
    checkpoint_root: str | Path,
    result_path: str | Path | None = None,
) -> dict[str, Any]:
    config = load_config(config_path)
    release = validate_release(release_path, config)
    repo = Path(release_path).resolve().parent.parent
    if result_path is not None and Path(result_path).resolve() != (repo / release["authorization"]["result_path"]).resolve():
        raise P3ContractError("p3_b28_result_path_mismatch")
    original_load, original_validate = engine.load_config, engine.validate_release
    engine.load_config = lambda unused: config
    engine.validate_release = lambda unused, loaded: release
    try:
        result = engine.run_case(config_path, release_path, checkpoint_root)
    finally:
        engine.load_config, engine.validate_release = original_load, original_validate
    return transform_result(result, summarize_checkpoint_evidence(checkpoint_root))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("preflight", "run"), required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--release")
    parser.add_argument("--checkpoint-root")
    args = parser.parse_args()
    output = Path(args.output)
    if output.exists():
        return 2
    try:
        if args.mode == "preflight":
            result = build_preflight(args.config)
        else:
            if not args.release or not args.checkpoint_root:
                raise P3ContractError("p3_b28_run_artifacts_required")
            result = run_case(args.config, args.release, args.checkpoint_root, output)
    except P3ContractError as exc:
        evidence = summarize_checkpoint_evidence(args.checkpoint_root or "")
        result = {
            "schema": "uruha_p3_case06_output_lock_failure_v1", "phase": "P3-B28",
            "status": "failed_after_transport_retained" if evidence["declared_invocation_intents"] else "refused_before_transport",
            "contract_code": exc.code, "checkpoint_evidence": evidence,
            "automatic_retry": False,
            "claim_boundary": "Failure retained; no quality or advantage claim is authorized.",
        }
    write_new_json(output, result)
    return 0 if result.get("status") in {"ready_for_case06_output_lock_review", "case06_outputs_locked"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
