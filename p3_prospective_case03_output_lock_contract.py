#!/usr/bin/env python3
"""P3-B41 zero-call quotation-aware contract for prospective case03."""

from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
from pathlib import Path
from typing import Any

import p3_case03_dual_condition_output_lock as engine
import p3_case05_dual_condition_output_lock as helper
from p3_direct_baseline_v2_design_review import load_review
from p3_product_comparison import P3ContractError, load_design, write_new_json
from p3_product_worker import LocalOllamaQwenStageCounter, _ollama_model_metadata


SCHEMA = "uruha_p3_prospective_case03_output_lock_v1"
MODEL_DIGEST = engine.MODEL_DIGEST
CASE_ID = "p3-prospective-v2-ambiguity-ja"
TURN_IDS = [f"p3-prospective-v2-03-u{i}" for i in range(1, 5)]
SELECTION = {
    "rule": "third_case_in_immutable_source_order_after_prior_results_retained",
    "case_index_zero_based": 2,
    "quality_based_selection": False,
    "prior_case_regeneration": False,
}
STRICT_REF = {
    "path": "p3_strict_visible_surface_v2.py",
    "sha256": "60dfba159b1f7671c0f18e1f0e76a429bd6821dc48a2a625e860d493a479dd56",
    "freeze_path": "research/p3_b39_quotation_aware_surface_freeze_2026-09-17.json",
    "freeze_sha256": "b5654fcfead50b885284b957f686c7a0a3afb0f90a32f5cf6450b6684917b0e8",
    "required_status": "quotation_aware_surface_gate_frozen",
}


def validate_selection(value: Any) -> None:
    if value != SELECTION:
        raise P3ContractError("p3_b41_selection_drift")


def validate_strict_reference(value: Any) -> None:
    if value != STRICT_REF:
        raise P3ContractError("p3_b41_strict_surface_reference_mismatch")


def load_config(path: str | Path) -> dict[str, Any]:
    config_path = Path(path).resolve()
    raw = helper._read(config_path)
    required = {
        "schema", "phase", "status", "purpose", "comparison_design", "direct_v2_review",
        "source_freeze", "case_source", "strict_surface_contract", "judge_transport",
        "selection", "conditions", "common_history", "session_boundary", "direct_instruction",
        "generation", "execution_boundary", "retention", "success",
    }
    if set(raw) != required or raw.get("schema") != SCHEMA or raw.get("phase") != "P3-B41":
        raise P3ContractError("p3_b41_schema_mismatch")
    if raw.get("status") != "preregistered_not_executed" or raw.get("purpose") != (
        "freeze_case03_quotation_aware_dual_condition_contract_before_output_or_annotation_access"
    ):
        raise P3ContractError("p3_b41_status_mismatch")
    validate_selection(raw.get("selection"))
    validate_strict_reference(raw.get("strict_surface_contract"))
    repo = config_path.parent.parent
    design_path = helper._ref(repo, raw["comparison_design"], {
        "path": "configs/p3_product_comparison_v1.json",
        "sha256": "1e6d3b0600740b3dee7207ffc5c4f9cc9247a5feba2b967bdab4586522f7b836",
    }, "p3_b41_design_mismatch")
    review_path = helper._ref(repo, raw["direct_v2_review"], {
        "path": "configs/p3_direct_baseline_v2_design_review_v1.json",
        "sha256": "2d0a17759e4daa4f7fd9cc2533cda3d285d5c04bf88c8f7428dc96e194aeed53",
    }, "p3_b41_review_mismatch")
    freeze_path = helper._ref(repo, raw["source_freeze"], {
        "path": "research/p3_b33_prospective_source_only_freeze_2026-09-17.json",
        "sha256": "c9fb2f5289913e2b460ff01c3650e773c8df0bdd8ff3e03194aab14872e90b90",
        "required_status": "prospective_source_only_frozen",
    }, "p3_b41_source_freeze_mismatch")
    source_path = helper._ref(repo, raw["case_source"], {
        "path": "datasets/p3_prospective_case03_generation_source_v1.json",
        "sha256": "f8ebbeaadd685dd3e8cd342f200e7387582ad1f8e296b88a2b89540af067845f",
    }, "p3_b41_source_mismatch")
    judge_path = helper._ref(repo, raw["judge_transport"], {
        "path": "analysis/p3_b32_exact_evidence_native_conformance_result_2026-09-17.json",
        "sha256": "8d610c380ed96c3f73075f4042a92a75da292418d8d5338da23a4fd6505e975b",
        "required_status": "exact_evidence_native_conformance_pass",
    }, "p3_b41_judge_mismatch")
    strict_path = repo / STRICT_REF["path"]
    strict_freeze_path = repo / STRICT_REF["freeze_path"]
    if (
        hashlib.sha256(strict_path.read_bytes()).hexdigest() != STRICT_REF["sha256"]
        or hashlib.sha256(strict_freeze_path.read_bytes()).hexdigest() != STRICT_REF["freeze_sha256"]
        or helper._read(strict_freeze_path).get("status") != STRICT_REF["required_status"]
    ):
        raise P3ContractError("p3_b41_strict_surface_not_frozen")
    source_freeze = helper._read(freeze_path)
    source = helper._read(source_path)
    judge = helper._read(judge_path)
    if source_freeze.get("status") != raw["source_freeze"]["required_status"]:
        raise P3ContractError("p3_b41_source_freeze_status_invalid")
    if judge.get("status") != raw["judge_transport"]["required_status"] or not all((judge.get("checks") or {}).values()):
        raise P3ContractError("p3_b41_judge_status_invalid")
    parent_path = repo / source["parent_source"]["path"]
    if hashlib.sha256(parent_path.read_bytes()).hexdigest() != source["parent_source"]["sha256"]:
        raise P3ContractError("p3_b41_parent_source_mismatch")
    parent = helper._read(parent_path)
    if len(parent.get("cases") or []) != 3 or parent["cases"][2].get("case_id") != CASE_ID:
        raise P3ContractError("p3_b41_third_case_selection_invalid")
    parent_case = parent["cases"][2]
    if (
        source.get("selection_rule") != "third_case_in_immutable_p3_b33_source_order"
        or source.get("sessions") != parent_case.get("sessions")
        or source.get("turns") != parent_case.get("turns")
        or source.get("case_id") != CASE_ID
        or source.get("family") != "relational_ambiguity_without_false_reassurance"
        or source.get("language") != "ja"
        or source.get("annotations_included") is not False
        or source.get("generation_executed") is not False
        or [turn.get("turn_id") for turn in source.get("turns", [])] != TURN_IDS
    ):
        raise P3ContractError("p3_b41_source_projection_mismatch")
    case02 = helper._read(repo / "configs/p3_prospective_case02_output_lock_v1.json")
    for key in ("conditions", "common_history", "direct_instruction", "generation", "execution_boundary", "retention"):
        if raw.get(key) != case02.get(key):
            raise P3ContractError("p3_b41_shared_contract_drift", key)
    if raw.get("session_boundary") != {
        "restart_product_before_turn_ids": [TURN_IDS[2]],
        "same_case_memory_path_retained": True,
        "new_brain_instance": True,
    }:
        raise P3ContractError("p3_b41_session_drift")
    expected_success = dict(case02["success"])
    expected_success.pop("all_eight_strict_japanese_surface_pass")
    expected_success["all_eight_quotation_aware_japanese_surface_pass"] = True
    if raw.get("success") != expected_success:
        raise P3ContractError("p3_b41_success_drift")
    design = load_design(design_path)
    review = load_review(review_path)
    if raw["direct_instruction"] != review["direct_baseline"]["instruction"]:
        raise P3ContractError("p3_b41_direct_instruction_drift")
    design = deepcopy(design)
    design["baselines"]["direct_instruction"] = raw["direct_instruction"]
    result = deepcopy(raw)
    result.update({
        "_repo": repo, "_config_path": config_path,
        "_config_sha256": hashlib.sha256(config_path.read_bytes()).hexdigest(),
        "_source": source, "_source_freeze": source_freeze,
        "_judge_transport": judge, "_design": design,
    })
    return result


def build_preflight(path: str | Path) -> dict[str, Any]:
    config = load_config(path)
    metadata = _ollama_model_metadata(config["generation"]["model"])
    counter = LocalOllamaQwenStageCounter(merge_adjacent_assistant=True)
    turns = config["_source"]["turns"]
    messages = [{
        "role": "system",
        "content": config["_design"]["persona"]["shared_contract"] + "\n" + config["direct_instruction"],
    }, {"role": "user", "content": turns[0]["content"]}]
    validation = helper._read(config["_repo"] / config["_source_freeze"]["artifacts"]["validation"]["path"])
    manifest = {row["turn_id"]: row for row in validation["turn_visibility_manifest"] if row["case_id"] == CASE_ID}
    prefix: list[dict[str, str]] = []
    pairs, futures = [], []
    for index, turn in enumerate(turns):
        views = engine.build_views(prefix, turn)
        product, direct = views["product_system"], views["full_history_direct"]
        pairs.append(
            product["source_history_sha256"] == direct["source_history_sha256"]
            and product["input_sha256"] == direct["input_sha256"]
            and len(product["visible_prefix"]) == len(direct["visible_prefix"]) == index * 2
        )
        row = manifest[turn["turn_id"]]
        futures.append(
            row["visible_turn_ids"] == [item["turn_id"] for item in turns[:index + 1]]
            and row["locked_future_turn_ids"] == [item["turn_id"] for item in turns[index + 1:]]
        )
        engine.append_product_prefix(prefix, turn, f"未生成product-{turn['turn_id']}")
    checks = {
        "config_valid": True,
        "model_digest_matches": metadata["digest"] == MODEL_DIGEST,
        "third_case_selected_by_immutable_order_not_quality": config["selection"] == SELECTION,
        "prior_cases_not_regenerated": config["selection"]["prior_case_regeneration"] is False,
        "quotation_aware_surface_contract_frozen": config["strict_surface_contract"] == STRICT_REF,
        "four_source_turns": len(turns) == 4,
        "all_offline_view_pairs_share_source": all(pairs),
        "all_future_turns_locked_by_b33_manifest": all(futures),
        "first_direct_prompt_count_available": counter(messages) > 0,
        "session_restart_boundary_exact": config["session_boundary"]["restart_product_before_turn_ids"] == [TURN_IDS[2]],
        "direct_calls_remain_exactly_four": config["execution_boundary"]["direct_provider_calls_exact"] == 4,
        "turn_intents_and_records_exactly_eight": config["execution_boundary"]["turn_intents_exact"] == config["execution_boundary"]["completed_turn_records_exact"] == 8,
        "annotations_closed": config["execution_boundary"]["annotation_access"] is False,
        "config_does_not_self_authorize": config["execution_boundary"]["real_model_calls_authorized_by_this_config"] is False,
    }
    return {
        "schema": "uruha_p3_prospective_case03_output_lock_preflight_v1",
        "phase": "P3-B41",
        "status": "ready_for_prospective_case03_output_lock_review" if all(checks.values()) else "not_ready_for_prospective_case03_output_lock_review",
        "config_sha256": config["_config_sha256"], "checks": checks,
        "model_metadata": metadata, "first_direct_prompt_tokens": counter(messages),
        "case_id": CASE_ID, "turn_ids": TURN_IDS,
        "source_sha256": config["case_source"]["sha256"],
        "strict_surface_sha256": STRICT_REF["sha256"],
        "real_model_calls": 0, "network_calls": 0, "paid_calls": 0,
        "annotations_accessed": 0, "confirmation_accessed": 0,
        "production_database_accessed": False,
        "claim_boundary": "Zero-call third source-order case preflight only; no output, score, preference or advantage result exists.",
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
            "schema": "uruha_p3_prospective_case03_output_lock_preflight_refusal_v1",
            "phase": "P3-B41", "status": "prospective_case03_output_lock_refused",
            "contract_code": exc.code, "real_model_calls": 0, "network_calls": 0,
            "annotations_accessed": 0, "claim_boundary": "No generation or quality claim is authorized.",
        }
    write_new_json(output, payload)
    return 0 if payload.get("status") == "ready_for_prospective_case03_output_lock_review" else 1


if __name__ == "__main__":
    raise SystemExit(main())

