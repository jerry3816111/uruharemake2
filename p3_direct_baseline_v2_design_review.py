#!/usr/bin/env python3
"""Fail-closed P3-B14 review of the versioned direct-baseline candidate."""

from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from p3_product_comparison import (
    P3ContractError,
    load_design,
    shared_visible_surface_contract,
    write_new_json,
)


SCHEMA = "uruha_p3_direct_baseline_v2_design_review_v1"


def _read(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise P3ContractError("p3_b14_invalid_json", str(path)) from exc
    if not isinstance(value, dict):
        raise P3ContractError("p3_b14_invalid_json", str(path))
    return value


def _ref(repo: Path, value: Any, expected: Mapping[str, str], code: str) -> Path:
    if value != dict(expected):
        raise P3ContractError(code)
    path = (repo / expected["path"]).resolve()
    try:
        path.relative_to(repo)
    except ValueError as exc:
        raise P3ContractError(code) from exc
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected["sha256"]:
        raise P3ContractError(code)
    return path


def load_review(path: str | Path) -> dict[str, Any]:
    review_path = Path(path)
    raw = _read(review_path)
    if set(raw) != {
        "schema", "status", "purpose", "immutable_evidence", "decision",
        "v2_conditions", "direct_baseline", "generation", "fairness",
        "next_canary", "execution_boundary", "claim_boundary",
    } or raw.get("schema") != SCHEMA:
        raise P3ContractError("p3_b14_schema_mismatch")
    if raw.get("status") != "design_reviewed_execution_not_authorized" or raw.get("purpose") != (
        "replace_nonfunctional_three_stage_developer_control_without_rewriting_v1"
    ):
        raise P3ContractError("p3_b14_status_mismatch")
    repo = review_path.resolve().parent.parent
    expected_refs = {
        "comparison_v1": {
            "path": "configs/p3_product_comparison_v1.json",
            "sha256": "1e6d3b0600740b3dee7207ffc5c4f9cc9247a5feba2b967bdab4586522f7b836",
        },
        "b9_baseline_result": {
            "path": "analysis/p3_b9_canary_baselines_result_2026-09-15.json",
            "sha256": "f2976da09f24a718a1a20d680c586008ebcf1cc7266e6c681a7fe1e70defba71",
        },
        "b11_instruction_result": {
            "path": "analysis/p3_b11_instruction_language_probe_result_2026-09-15.json",
            "sha256": "baf6c4c1581dfc1fd2c26e36114791526ed117dd6e13bd4137feb2b84bf6957a",
        },
        "b13_carrier_result": {
            "path": "analysis/p3_b13_private_scratch_carrier_result_2026-09-15.json",
            "sha256": "1a754a028472c51a5c6f7426fb4cb69e7b17e702bdebe50b3028a8df078a61b1",
        },
        "b11_probe_config": {
            "path": "configs/p3_baseline_instruction_language_probe_v1.json",
            "sha256": "dc99af1c2bed92abc11258bd5c3a7949b6f97f7bb47247b1853c7e93c55f12c0",
        },
        "developer_source": {
            "path": "datasets/p3_developer_smoke_source_v1.json",
            "sha256": "3b6d4d77190e15485651af4c708416992214332d6a02288ce27db3f37457be8f",
        },
    }
    if not isinstance(raw.get("immutable_evidence"), Mapping):
        raise P3ContractError("p3_b14_evidence_mismatch")
    paths = {
        name: _ref(repo, raw["immutable_evidence"].get(name), expected, "p3_b14_evidence_mismatch")
        for name, expected in expected_refs.items()
    }
    design = load_design(paths["comparison_v1"])
    b9 = _read(paths["b9_baseline_result"])
    b11 = _read(paths["b11_instruction_result"])
    b13 = _read(paths["b13_carrier_result"])
    b11_config = _read(paths["b11_probe_config"])
    source = _read(paths["developer_source"])

    if b9.get("real_model_calls") != 4 or b11.get("real_model_calls") != 8:
        raise P3ContractError("p3_b14_upstream_call_evidence_mismatch")
    if b13.get("status") != "private_scratch_carrier_failed_retained" or b13.get("real_model_calls") != 2:
        raise P3ContractError("p3_b14_upstream_failure_mismatch")
    japanese = b11["arms"]["japanese_instructions"]["conditions"]
    direct_text = japanese["full_history_direct"]["final"]["content"]
    if not all(shared_visible_surface_contract(direct_text).values()):
        raise P3ContractError("p3_b14_direct_candidate_not_surface_valid")
    if b13["treatment"]["final"] != b13["locked_control"]["draft"]:
        raise P3ContractError("p3_b14_carrier_counterexample_changed")
    if b13["checks"].get("treatment_passes_while_locked_control_fails") is not False:
        raise P3ContractError("p3_b14_carrier_counterexample_changed")

    instruction = b11_config["arms"]["japanese_instructions"]["direct_instruction"]
    if raw.get("decision") != {
        "comparison_v1_immutable": True,
        "retire_from_v2": ["full_history_deliberate"],
        "retirement_reason_codes": [
            "assistant_carrier_critique_empty", "user_carrier_critique_copies_draft",
            "revision_does_not_improve_draft", "two_attributable_repairs_failed",
        ],
        "candidate_control": "full_history_direct",
        "candidate_status": "requires_fresh_surface_and_grounding_canary",
        "not_weaker_rationale": (
            "The retired condition was structurally nonfunctional and never produced a usable deliberate final in the locked evidence. "
            "The direct candidate receives the complete raw visible history, shared persona, the same model and decoding options, and the same aggregate completion ceiling. "
            "Removing a broken chain avoids an artificially weak comparator; it does not establish that the candidate is strong enough."
        ),
    }:
        raise P3ContractError("p3_b14_decision_mismatch")
    if raw.get("v2_conditions") != ["full_history_direct", "product_system"]:
        raise P3ContractError("p3_b14_condition_mismatch")
    if raw.get("direct_baseline") != {
        "instruction": instruction,
        "visible_history": "same_complete_raw_visible_history_as_product",
        "private_product_state": False,
        "output_postprocessing": "none",
        "visible_surface_gate": "shared_visible_surface_contract",
        "completion_tokens_max": 768,
        "calls_max": 1,
    }:
        raise P3ContractError("p3_b14_direct_baseline_mismatch")
    model = design["model"]
    turn_budget = design["budget"]["per_condition_turn"]
    if raw.get("generation") != {
        "model": model["generation_model"],
        "digest": "2bada8a7450677000f678be90653b85d364de7db25eb5ea54136ada5f3933730",
        "temperature": model["temperature"], "seed": model["seed"],
        "top_p": model["top_p"], "num_ctx": model["num_ctx"], "think": model["think"],
        "aggregate_completion_tokens_max_per_condition": turn_budget["aggregate_completion_tokens_max"],
        "aggregate_prompt_tokens_max_per_condition": turn_budget["aggregate_prompt_tokens_max"],
        "wall_seconds_max_per_condition": turn_budget["wall_seconds_max"],
    }:
        raise P3ContractError("p3_b14_generation_mismatch")
    expected_fairness = {
        "same_model_digest": True, "same_raw_visible_history": True,
        "same_shared_persona_contract": True, "same_decoding_options": True,
        "same_hardware_and_local_transport": True,
        "same_aggregate_completion_ceiling": True,
        "actual_prompt_completion_tokens_and_latency_reported_separately": True,
        "product_internal_state_is_the_intervention": True,
        "baseline_output_not_written_back": True,
        "current_product_reply_hidden_from_baseline": True,
        "shared_visible_surface_is_gate_not_quality_score": True,
    }
    if raw.get("fairness") != expected_fairness:
        raise P3ContractError("p3_b14_fairness_mismatch")
    selected = next(
        turn
        for case in source["cases"] if case["case_id"] == "p3-smoke-emotional-bid-ja"
        for turn in case["turns"] if turn["turn_id"] == "p3-smoke-03-u1"
    )
    if raw.get("next_canary") != {
        "selection_rule": "third_developer_case_first_turn_after_case_02_annotations_exposed",
        "case_id": "p3-smoke-emotional-bid-ja", "turn_id": selected["turn_id"],
        "session_id": selected["session_id"], "content_sha256": selected["content_sha256"],
        "future_turn_access_during_canary": False,
        "annotation_access_before_all_case_outputs_locked": False,
    }:
        raise P3ContractError("p3_b14_canary_selection_mismatch")
    if raw.get("execution_boundary") != {
        "real_model_calls_authorized_by_this_review": False, "network_calls": 0,
        "annotation_access": False, "confirmation_access": False,
        "production_database_access": False, "external_deployment": False,
    }:
        raise P3ContractError("p3_b14_boundary_mismatch")
    frozen = deepcopy(raw)
    frozen["_review_sha256"] = hashlib.sha256(review_path.read_bytes()).hexdigest()
    frozen["_design"] = design
    frozen["_direct_candidate_text"] = direct_text
    return frozen


def build_acceptance(path: str | Path) -> dict[str, Any]:
    review = load_review(path)
    checks = {
        "v1_preserved_by_hash": review["decision"]["comparison_v1_immutable"],
        "two_failed_repair_batches_retained": len(review["decision"]["retirement_reason_codes"]) == 4,
        "broken_deliberate_not_in_v2": "full_history_deliberate" not in review["v2_conditions"],
        "direct_candidate_has_locked_surface_pass": all(
            shared_visible_surface_contract(review["_direct_candidate_text"]).values()
        ),
        "raw_information_and_persona_equal": (
            review["fairness"]["same_raw_visible_history"]
            and review["fairness"]["same_shared_persona_contract"]
        ),
        "resource_ceiling_equal_actuals_separate": (
            review["fairness"]["same_aggregate_completion_ceiling"]
            and review["fairness"]["actual_prompt_completion_tokens_and_latency_reported_separately"]
        ),
        "fresh_case_annotation_still_forbidden": review["next_canary"]["annotation_access_before_all_case_outputs_locked"] is False,
        "review_does_not_authorize_calls": review["execution_boundary"]["real_model_calls_authorized_by_this_review"] is False,
    }
    return {
        "schema": "uruha_p3_direct_baseline_v2_design_review_acceptance_v1",
        "phase": "P3-B14",
        "status": "ready_for_direct_v2_canary_implementation" if all(checks.values()) else "review_required",
        "review_sha256": review["_review_sha256"],
        "decision": review["decision"], "checks": checks,
        "next_canary": review["next_canary"],
        "real_model_calls": 0, "network_calls": 0, "paid_calls": 0,
        "annotations_accessed": 0, "confirmation_accessed": 0,
        "production_database_accessed": False,
        "claim_boundary": review["claim_boundary"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--review", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = Path(args.output)
    if output.exists():
        return 2
    try:
        result = build_acceptance(args.review)
    except P3ContractError as exc:
        result = {
            "schema": "uruha_p3_direct_baseline_v2_design_review_acceptance_v1",
            "phase": "P3-B14", "status": "review_required",
            "contract_code": exc.code, "real_model_calls": 0,
            "network_calls": 0, "paid_calls": 0,
        }
    write_new_json(output, result)
    return 0 if result.get("status") == "ready_for_direct_v2_canary_implementation" else 3


if __name__ == "__main__":
    raise SystemExit(main())
