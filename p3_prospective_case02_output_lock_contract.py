#!/usr/bin/env python3
"""P3-B37 zero-call strict contract for prospective case02 output locking."""

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


SCHEMA = "uruha_p3_prospective_case02_output_lock_v1"
MODEL_DIGEST = engine.MODEL_DIGEST
CASE_ID = "p3-prospective-v2-excitement-en"
TURN_IDS = [f"p3-prospective-v2-02-u{i}" for i in range(1, 5)]
ROOT_KEYS = {
    "schema", "phase", "status", "purpose", "comparison_design",
    "direct_v2_review", "source_freeze", "case_source", "strict_surface_contract",
    "judge_transport", "selection", "conditions", "common_history", "session_boundary",
    "direct_instruction", "generation", "execution_boundary", "retention", "success",
}
EXPECTED_STRICT_REFERENCE = {
    "path": "p3_strict_visible_surface.py",
    "sha256": "90b2b4ee0ad1e4f4d990c0497f08a0841bbdad48cbafa65c1690777d775e3d9f",
    "freeze_path": "research/p3_b36_strict_surface_gate_freeze_2026-09-17.json",
    "required_status": "b35_surface_gate_failure_frozen",
}
EXPECTED_SELECTION = {
    "rule": "second_case_in_immutable_source_order_after_first_case_retained",
    "case_index_zero_based": 1,
    "quality_based_selection": False,
    "prior_case_regeneration": False,
}


def _same_as_case01(raw: dict[str, Any], case01: dict[str, Any], key: str) -> None:
    if raw.get(key) != case01.get(key):
        raise P3ContractError("p3_b37_shared_contract_drift", key)


def validate_strict_reference(value: Any) -> None:
    if value != EXPECTED_STRICT_REFERENCE:
        raise P3ContractError("p3_b37_strict_surface_reference_mismatch")


def validate_selection(value: Any) -> None:
    if value != EXPECTED_SELECTION:
        raise P3ContractError("p3_b37_selection_drift")


def load_config(path: str | Path) -> dict[str, Any]:
    config_path = Path(path).resolve()
    raw = helper._read(config_path)
    if set(raw) != ROOT_KEYS or raw.get("schema") != SCHEMA or raw.get("phase") != "P3-B37":
        raise P3ContractError("p3_b37_schema_mismatch")
    if raw.get("status") != "preregistered_not_executed" or raw.get("purpose") != (
        "freeze_case02_strict_dual_condition_generation_contract_before_output_or_annotation_access"
    ):
        raise P3ContractError("p3_b37_status_mismatch")

    repo = config_path.parent.parent
    design_path = helper._ref(repo, raw["comparison_design"], {
        "path": "configs/p3_product_comparison_v1.json",
        "sha256": "1e6d3b0600740b3dee7207ffc5c4f9cc9247a5feba2b967bdab4586522f7b836",
    }, "p3_b37_design_mismatch")
    review_path = helper._ref(repo, raw["direct_v2_review"], {
        "path": "configs/p3_direct_baseline_v2_design_review_v1.json",
        "sha256": "2d0a17759e4daa4f7fd9cc2533cda3d285d5c04bf88c8f7428dc96e194aeed53",
    }, "p3_b37_review_mismatch")
    freeze_path = helper._ref(repo, raw["source_freeze"], {
        "path": "research/p3_b33_prospective_source_only_freeze_2026-09-17.json",
        "sha256": "c9fb2f5289913e2b460ff01c3650e773c8df0bdd8ff3e03194aab14872e90b90",
        "required_status": "prospective_source_only_frozen",
    }, "p3_b37_source_freeze_mismatch")
    source_path = helper._ref(repo, raw["case_source"], {
        "path": "datasets/p3_prospective_case02_generation_source_v1.json",
        "sha256": "ee9955a6eb0241271233e9a4c326a2d0d64e5c463ba07d7d2e1c63717b87ec96",
    }, "p3_b37_source_mismatch")
    judge_path = helper._ref(repo, raw["judge_transport"], {
        "path": "analysis/p3_b32_exact_evidence_native_conformance_result_2026-09-17.json",
        "sha256": "8d610c380ed96c3f73075f4042a92a75da292418d8d5338da23a4fd6505e975b",
        "required_status": "exact_evidence_native_conformance_pass",
    }, "p3_b37_judge_transport_mismatch")

    strict_ref = raw["strict_surface_contract"]
    validate_strict_reference(strict_ref)
    strict_path = (repo / strict_ref["path"]).resolve()
    strict_freeze_path = (repo / strict_ref["freeze_path"]).resolve()
    if (
        hashlib.sha256(strict_path.read_bytes()).hexdigest() != strict_ref["sha256"]
        or helper._read(strict_freeze_path).get("status") != strict_ref["required_status"]
    ):
        raise P3ContractError("p3_b37_strict_surface_not_frozen")

    source_freeze = helper._read(freeze_path)
    source = helper._read(source_path)
    judge = helper._read(judge_path)
    if source_freeze.get("status") != raw["source_freeze"]["required_status"]:
        raise P3ContractError("p3_b37_source_freeze_status_invalid")
    if judge.get("status") != raw["judge_transport"]["required_status"] or not all(
        (judge.get("checks") or {}).values()
    ):
        raise P3ContractError("p3_b37_judge_transport_status_invalid")
    validate_selection(raw.get("selection"))

    parent_ref = source.get("parent_source") or {}
    parent_path = (repo / str(parent_ref.get("path"))).resolve()
    if (
        not parent_path.is_file()
        or hashlib.sha256(parent_path.read_bytes()).hexdigest() != parent_ref.get("sha256")
    ):
        raise P3ContractError("p3_b37_parent_source_mismatch")
    parent = helper._read(parent_path)
    if len(parent.get("cases") or []) < 2 or parent["cases"][1].get("case_id") != CASE_ID:
        raise P3ContractError("p3_b37_second_case_selection_invalid")
    parent_case = parent["cases"][1]
    if (
        source.get("selection_rule") != "second_case_in_immutable_p3_b33_source_order"
        or source.get("turns") != parent_case.get("turns")
        or source.get("sessions") != parent_case.get("sessions")
    ):
        raise P3ContractError("p3_b37_source_projection_mismatch")
    if (
        source.get("case_id") != CASE_ID
        or source.get("family") != "positive_arousal_not_anxiety"
        or source.get("language") != "en"
        or source.get("annotations_included") is not False
        or source.get("generation_executed") is not False
        or [turn.get("turn_id") for turn in source.get("turns", [])] != TURN_IDS
        or any(
            hashlib.sha256(turn["content"].encode("utf-8")).hexdigest() != turn["content_sha256"]
            for turn in source.get("turns", [])
        )
    ):
        raise P3ContractError("p3_b37_source_identity_invalid")

    case01 = helper._read(repo / "configs/p3_prospective_case01_output_lock_v1.json")
    for key in (
        "conditions", "common_history", "direct_instruction", "generation",
        "execution_boundary", "retention",
    ):
        _same_as_case01(raw, case01, key)
    if raw.get("session_boundary") != {
        "restart_product_before_turn_ids": [TURN_IDS[2]],
        "same_case_memory_path_retained": True,
        "new_brain_instance": True,
    }:
        raise P3ContractError("p3_b37_session_drift")
    expected_success = dict(case01["success"])
    expected_success.pop("all_eight_shared_surface_pass")
    expected_success["all_eight_strict_japanese_surface_pass"] = True
    if raw.get("success") != expected_success:
        raise P3ContractError("p3_b37_success_drift")

    design = load_design(design_path)
    review = load_review(review_path)
    if raw["direct_instruction"] != review["direct_baseline"]["instruction"]:
        raise P3ContractError("p3_b37_direct_instruction_drift")
    design = deepcopy(design)
    design["baselines"]["direct_instruction"] = raw["direct_instruction"]
    result = deepcopy(raw)
    result.update({
        "_repo": repo,
        "_config_path": config_path,
        "_config_sha256": hashlib.sha256(config_path.read_bytes()).hexdigest(),
        "_source": source,
        "_source_freeze": source_freeze,
        "_judge_transport": judge,
        "_design": design,
    })
    return result


def build_preflight(path: str | Path) -> dict[str, Any]:
    config = load_config(path)
    metadata = _ollama_model_metadata(config["generation"]["model"])
    counter = LocalOllamaQwenStageCounter(merge_adjacent_assistant=True)
    first = config["_source"]["turns"][0]
    messages = [{
        "role": "system",
        "content": config["_design"]["persona"]["shared_contract"] + "\n" + config["direct_instruction"],
    }, {"role": "user", "content": first["content"]}]
    prefix: list[dict[str, str]] = []
    paired_views: list[bool] = []
    future_locks: list[bool] = []
    turns = config["_source"]["turns"]
    validation = helper._read(
        config["_repo"] / config["_source_freeze"]["artifacts"]["validation"]["path"]
    )
    manifest = {
        row["turn_id"]: row for row in validation.get("turn_visibility_manifest", [])
        if row.get("case_id") == CASE_ID
    }
    for index, turn in enumerate(turns):
        views = engine.build_views(prefix, turn)
        product, direct = views["product_system"], views["full_history_direct"]
        paired_views.append(
            product["source_history_sha256"] == direct["source_history_sha256"]
            and product["input_sha256"] == direct["input_sha256"]
            and len(product["visible_prefix"]) == len(direct["visible_prefix"]) == index * 2
        )
        visibility = manifest.get(turn["turn_id"]) or {}
        future_locks.append(
            visibility.get("visible_turn_ids") == [item["turn_id"] for item in turns[:index + 1]]
            and visibility.get("locked_future_turn_ids") == [item["turn_id"] for item in turns[index + 1:]]
        )
        engine.append_product_prefix(prefix, turn, f"未生成product-{turn['turn_id']}")
    checks = {
        "config_valid": True,
        "model_digest_matches": metadata["digest"] == MODEL_DIGEST,
        "second_case_selected_by_immutable_order_not_quality": (
            config["selection"]["case_index_zero_based"] == 1
            and config["selection"]["quality_based_selection"] is False
        ),
        "prior_failed_case_not_regenerated": config["selection"]["prior_case_regeneration"] is False,
        "strict_surface_contract_frozen": config["strict_surface_contract"]["required_status"]
        == "b35_surface_gate_failure_frozen",
        "four_source_turns": len(turns) == 4,
        "all_offline_view_pairs_share_source": all(paired_views),
        "all_future_turns_locked_by_b33_manifest": all(future_locks),
        "first_direct_prompt_count_available": counter(messages) > 0,
        "session_restart_boundary_exact": config["session_boundary"]["restart_product_before_turn_ids"]
        == [TURN_IDS[2]],
        "zero_call_product_turns_allowed_but_not_required": config["execution_boundary"]["product_provider_calls_min"] == 0,
        "direct_calls_remain_exactly_four": config["execution_boundary"]["direct_provider_calls_exact"] == 4,
        "turn_intents_and_records_exactly_eight": config["execution_boundary"]["turn_intents_exact"]
        == config["execution_boundary"]["completed_turn_records_exact"] == 8,
        "annotations_closed": config["execution_boundary"]["annotation_access"] is False,
        "config_does_not_self_authorize": config["execution_boundary"]["real_model_calls_authorized_by_this_config"] is False,
    }
    return {
        "schema": "uruha_p3_prospective_case02_output_lock_preflight_v1",
        "phase": "P3-B37",
        "status": "ready_for_prospective_case02_output_lock_review" if all(checks.values())
        else "not_ready_for_prospective_case02_output_lock_review",
        "config_sha256": config["_config_sha256"],
        "checks": checks,
        "model_metadata": metadata,
        "first_direct_prompt_tokens": counter(messages),
        "case_id": CASE_ID,
        "turn_ids": TURN_IDS,
        "source_sha256": config["case_source"]["sha256"],
        "strict_surface_sha256": config["strict_surface_contract"]["sha256"],
        "real_model_calls": 0,
        "network_calls": 0,
        "paid_calls": 0,
        "annotations_accessed": 0,
        "confirmation_accessed": 0,
        "production_database_accessed": False,
        "claim_boundary": (
            "Zero-call preflight for the second source-order prospective case. It freezes the strict "
            "surface and paired-view contract but creates no output, score, preference or advantage result."
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
            "schema": "uruha_p3_prospective_case02_output_lock_preflight_refusal_v1",
            "phase": "P3-B37",
            "status": "prospective_case02_output_lock_refused",
            "contract_code": exc.code,
            "real_model_calls": 0,
            "network_calls": 0,
            "annotations_accessed": 0,
            "claim_boundary": "No generation or quality claim is authorized.",
        }
    write_new_json(output, payload)
    return 0 if payload.get("status") == "ready_for_prospective_case02_output_lock_review" else 1


if __name__ == "__main__":
    raise SystemExit(main())
