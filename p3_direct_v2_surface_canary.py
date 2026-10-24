#!/usr/bin/env python3
"""P3-B15 one-call direct-v2 surface canary.

The locked product result is bound by file digest only. Its JSON content is
never loaded, and therefore cannot enter the direct baseline prompt.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from p3_direct_baseline_v2_design_review import load_review
from p3_product_comparison import P3ContractError, canonical_sha256, write_new_json
from p3_product_worker import (
    LocalOllamaQwenStageCounter,
    _local_canary_baseline_transport,
    _ollama_model_metadata,
    execute_canary_baselines,
    localhost_network_only,
    summarize_checkpoint_evidence,
)


SCHEMA = "uruha_p3_direct_v2_surface_canary_v1"
RELEASE_SCHEMA = "uruha_p3_direct_v2_surface_canary_release_v1"
MODEL_DIGEST = "2bada8a7450677000f678be90653b85d364de7db25eb5ea54136ada5f3933730"


def _read(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise P3ContractError("p3_b15_direct_invalid_json", str(path)) from exc
    if not isinstance(value, dict):
        raise P3ContractError("p3_b15_direct_invalid_json", str(path))
    return value


def _ref(repo: Path, value: Any, expected: Mapping[str, Any], code: str) -> Path:
    if value != dict(expected):
        raise P3ContractError(code)
    path = (repo / str(expected["path"])).resolve()
    try:
        path.relative_to(repo)
    except ValueError as exc:
        raise P3ContractError(code) from exc
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected["sha256"]:
        raise P3ContractError(code)
    return path


def load_canary(path: str | Path) -> dict[str, Any]:
    config_path = Path(path)
    raw = _read(config_path)
    if set(raw) != {
        "schema", "status", "purpose", "design_review", "product_canary",
        "source", "locked_product_result", "tokenizer_binding_result",
        "condition", "direct_instruction", "generation", "transport",
        "execution_boundary", "success",
    } or raw.get("schema") != SCHEMA:
        raise P3ContractError("p3_b15_direct_schema_mismatch")
    if raw.get("status") != "preregistered_not_executed" or raw.get("purpose") != (
        "fresh_one_call_direct_candidate_for_locked_product_source"
    ):
        raise P3ContractError("p3_b15_direct_status_mismatch")
    repo = config_path.resolve().parent.parent
    review_path = _ref(repo, raw.get("design_review"), {
        "path": "configs/p3_direct_baseline_v2_design_review_v1.json",
        "sha256": "2d0a17759e4daa4f7fd9cc2533cda3d285d5c04bf88c8f7428dc96e194aeed53",
    }, "p3_b15_direct_review_mismatch")
    product_canary_path = _ref(repo, raw.get("product_canary"), {
        "path": "configs/p3_product_canary_v3.json",
        "sha256": "62b1eb460f137dcaa3d2fda335fa9afcff48de9dc96e327540fc315832e82112",
    }, "p3_b15_direct_product_canary_mismatch")
    source_path = _ref(repo, raw.get("source"), {
        "path": "datasets/p3_product_canary_source_v3.json",
        "sha256": "52c09d8df6ff409d4ae3759ff3d734891cdc63501668b90581a84dd34ee1cb77",
    }, "p3_b15_direct_source_mismatch")
    expected_product_result = {
        "path": "analysis/p3_b15_product_canary_result_2026-09-15.json",
        "sha256": "70cacf554526c3d33cedac7a9b58255c7df3f591a8d84cbaff9c1c0da5d44db4",
        "content_not_loaded_by_runner": True,
    }
    if raw.get("locked_product_result") != expected_product_result:
        raise P3ContractError("p3_b15_direct_product_result_mismatch")
    product_result_path = _ref(
        repo, raw.get("locked_product_result"), expected_product_result,
        "p3_b15_direct_product_result_mismatch",
    )
    binding_path = _ref(repo, raw.get("tokenizer_binding_result"), {
        "path": "analysis/p3_b8_1_stage_tokenizer_binding_confirmation_result_2026-09-15.json",
        "sha256": "e360e626931d40ff52f5a217131541701a1eb69831fa3b249214dbb4fed5774f",
        "required_status": "stage_provider_binding_pass",
    }, "p3_b15_direct_binding_mismatch")
    review = load_review(review_path)
    product_canary = _read(product_canary_path)
    source = _read(source_path)
    binding = _read(binding_path)
    if binding.get("status") != "stage_provider_binding_pass" or binding.get("binding_verified") is not True:
        raise P3ContractError("p3_b15_direct_binding_invalid")
    if product_result_path.name != "p3_b15_product_canary_result_2026-09-15.json":
        raise P3ContractError("p3_b15_direct_product_result_mismatch")
    if product_canary.get("selection") != {
        "rule": source["selection_rule"], "case_id": source["case_id"],
        "turn_id": source["turn_id"], "content_sha256": source["content_sha256"],
    }:
        raise P3ContractError("p3_b15_direct_source_selection_mismatch")
    if source.get("visible_prefix") != [] or source.get("future_turns_included") is not False or source.get("annotations_included") is not False:
        raise P3ContractError("p3_b15_direct_source_boundary_mismatch")
    if raw.get("condition") != "full_history_direct" or raw.get("direct_instruction") != review["direct_baseline"]["instruction"]:
        raise P3ContractError("p3_b15_direct_instruction_mismatch")
    if raw.get("generation") != {
        "model": "qwen2.5:7b", "digest": MODEL_DIGEST,
        "temperature": 0, "seed": 20260909, "top_p": 1,
        "num_ctx": 8192, "think": False, "completion_cap": 768,
    } or raw.get("transport") != {
        "backend": "openai_compatible_local",
        "url": "http://127.0.0.1:11434/v1/chat/completions",
        "per_call_timeout_seconds": 60,
    }:
        raise P3ContractError("p3_b15_direct_generation_mismatch")
    if raw.get("execution_boundary") != {
        "provider_calls_exact": 1, "automatic_retry": False, "concurrency": 1,
        "localhost_only": True, "source_turns_exact": 1,
        "future_turn_access": False, "annotation_access": False,
        "confirmation_access": False, "production_database_access": False,
        "external_deployment": False, "remote_paid_calls": False,
        "real_model_calls_authorized_by_this_config": False,
    } or raw.get("success") != {
        "direct_output_nonempty": True, "direct_output_shared_surface_pass": True,
        "provider_prompt_usage_exact": True, "condition_budget_valid": True,
        "same_source_as_locked_product": True,
        "product_reply_not_loaded_or_sent": True,
        "all_outputs_and_failures_retained": True,
    }:
        raise P3ContractError("p3_b15_direct_boundary_mismatch")
    design = deepcopy(review["_design"])
    design["baselines"]["direct_instruction"] = raw["direct_instruction"]
    frozen = deepcopy(raw)
    frozen["_config_sha256"] = hashlib.sha256(config_path.read_bytes()).hexdigest()
    frozen["_config_path"] = str(config_path.resolve())
    frozen["_source"] = source
    frozen["_design"] = design
    frozen["_phase"] = "P3-B15"
    return frozen


def _runtime_config(canary: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "_canary": {"_source": deepcopy(canary["_source"])},
        "_design": deepcopy(canary["_design"]),
        "_config_sha256": canary["_config_sha256"],
        "_phase": "P3-B15",
        "conditions": ["full_history_direct"],
        "generation": {
            "model": canary["generation"]["model"],
            "temperature": canary["generation"]["temperature"],
            "seed": canary["generation"]["seed"],
            "top_p": canary["generation"]["top_p"],
            "num_ctx": canary["generation"]["num_ctx"],
            "think": canary["generation"]["think"],
        },
        "transport": deepcopy(canary["transport"]),
        "execution_boundary": {"provider_calls_exact": 1},
    }


def build_preflight(path: str | Path) -> dict[str, Any]:
    canary = load_canary(path)
    config = _runtime_config(canary)
    counter = LocalOllamaQwenStageCounter(merge_adjacent_assistant=True)
    messages = [
        {"role": "system", "content": canary["_design"]["persona"]["shared_contract"] + "\n" + canary["direct_instruction"]},
        {"role": "user", "content": canary["_source"]["content"]},
    ]
    checks = {
        "config_valid": True,
        "model_digest_matches": _ollama_model_metadata(canary["generation"]["model"])["digest"] == MODEL_DIGEST,
        "direct_prompt_count_available": counter(messages) > 0,
        "one_source_turn_no_prefix": canary["_source"]["visible_prefix"] == [],
        "locked_product_bound_by_digest_only": canary["locked_product_result"]["content_not_loaded_by_runner"] is True,
        "config_does_not_self_authorize": canary["execution_boundary"]["real_model_calls_authorized_by_this_config"] is False,
        "runtime_condition_is_direct_only": config["conditions"] == ["full_history_direct"],
    }
    return {
        "schema": "uruha_p3_direct_v2_surface_canary_preflight_v1",
        "phase": "P3-B15",
        "status": "ready_for_direct_v2_surface_canary_review" if all(checks.values()) else "not_ready_for_direct_v2_surface_canary_review",
        "config_sha256": canary["_config_sha256"], "checks": checks,
        "offline_prompt_tokens": counter(messages),
        "source_sha256": canonical_sha256(canary["_source"]["content"]),
        "real_model_calls": 0, "network_calls": 0, "paid_calls": 0,
        "future_turns_accessed": 0, "annotations_accessed": 0,
        "product_result_content_loaded": False,
        "claim_boundary": "Preflight only; it does not execute or grade either condition.",
    }


def validate_release(path: str | Path, canary: Mapping[str, Any]) -> dict[str, Any]:
    release_path = Path(path)
    release = _read(release_path)
    if set(release) != {
        "schema", "phase", "status", "review_kind", "config",
        "implementation_sha256", "preflight", "authorization", "claim_boundary",
    } or release.get("schema") != RELEASE_SCHEMA:
        raise P3ContractError("p3_b15_direct_release_schema_mismatch")
    if release.get("phase") != "P3-B15" or release.get("status") != "released_for_single_direct_v2_surface_canary":
        raise P3ContractError("p3_b15_direct_release_status_mismatch")
    if release.get("review_kind") != "same_task_self_review_not_independent":
        raise P3ContractError("p3_b15_direct_release_review_mismatch")
    repo = release_path.resolve().parent.parent
    if release.get("config") != {
        "path": "configs/p3_direct_v2_surface_canary_v1.json",
        "sha256": canary["_config_sha256"],
    }:
        raise P3ContractError("p3_b15_direct_release_config_mismatch")
    implementation = release.get("implementation_sha256")
    required = {"p3_direct_v2_surface_canary.py", "test_p3_direct_v2_surface_canary.py"}
    if not isinstance(implementation, Mapping) or set(implementation) != required:
        raise P3ContractError("p3_b15_direct_release_implementation_invalid")
    for name, sha in implementation.items():
        if hashlib.sha256((repo / name).read_bytes()).hexdigest() != sha:
            raise P3ContractError("p3_b15_direct_release_implementation_mismatch", name)
    preflight = release.get("preflight")
    preflight_path = (repo / str((preflight or {}).get("path"))).resolve()
    if not isinstance(preflight, Mapping) or set(preflight) != {"path", "sha256", "status"} or (
        not preflight_path.is_file()
        or hashlib.sha256(preflight_path.read_bytes()).hexdigest() != preflight.get("sha256")
        or preflight.get("status") != "ready_for_direct_v2_surface_canary_review"
    ):
        raise P3ContractError("p3_b15_direct_release_preflight_mismatch")
    if release.get("authorization") != {
        "run_id": "p3-b15-direct-v2-surface-canary-v1",
        "localhost_only": True, "model": "qwen2.5:7b", "model_digest": MODEL_DIGEST,
        "provider_calls_exact": 1, "automatic_retry": False,
        "checkpoint_root": "analysis/p3_b15_direct_v2_surface_canary_checkpoints_v1",
        "result_path": "analysis/p3_b15_direct_v2_surface_canary_result_2026-09-15.json",
        "future_turn_access": False, "annotation_access": False,
        "confirmation_access": False, "production_database_access": False,
        "external_deployment": False,
    }:
        raise P3ContractError("p3_b15_direct_release_authorization_mismatch")
    return release


def run_canary(config_path: str | Path, release_path: str | Path, checkpoint_root: str | Path) -> dict[str, Any]:
    canary = load_canary(config_path)
    release = validate_release(release_path, canary)
    repo = Path(release_path).resolve().parent.parent
    checkpoint = Path(checkpoint_root).resolve()
    if checkpoint != (repo / release["authorization"]["checkpoint_root"]).resolve():
        raise P3ContractError("p3_b15_direct_checkpoint_path_mismatch")
    if _ollama_model_metadata("qwen2.5:7b")["digest"] != MODEL_DIGEST:
        raise P3ContractError("p3_b15_direct_runtime_model_mismatch")
    config = _runtime_config(canary)
    counter = LocalOllamaQwenStageCounter(merge_adjacent_assistant=True)
    with localhost_network_only() as attempts:
        raw = execute_canary_baselines(
            config=config, token_counter=counter,
            transport=_local_canary_baseline_transport(config),
            checkpoint_root=checkpoint,
            evidence_kind="local_ollama_provider_usage",
        )
    condition = raw["conditions"]["full_history_direct"]
    raw["checks"]["localhost_only"] = all(row["loopback_allowed"] is True for row in attempts)
    checks = {
        "direct_output_nonempty": raw["checks"]["both_condition_outputs_nonempty"],
        "direct_output_shared_surface_pass": raw["checks"]["all_final_replies_meet_shared_surface_contract"],
        "provider_prompt_usage_exact": raw["checks"]["provider_prompt_usage_exact"],
        "condition_budget_valid": raw["checks"]["each_condition_budget_valid"],
        "same_source_as_locked_product": raw["source"]["content_sha256"] == canary["_source"]["content_sha256"],
        "product_reply_not_loaded_or_sent": True,
        "one_provider_call_exact": raw["provider_call_evidence"] == raw["real_model_calls"] == raw["network_calls"] == 1,
        "localhost_only": raw["checks"]["localhost_only"],
    }
    passed = all(checks.values())
    return {
        "schema": "uruha_p3_direct_v2_surface_canary_result_v1",
        "phase": "P3-B15",
        "status": "direct_v2_surface_canary_pass" if passed else "direct_v2_surface_canary_failed_retained",
        "config_sha256": canary["_config_sha256"],
        "release_sha256": hashlib.sha256(Path(release_path).read_bytes()).hexdigest(),
        "source": raw["source"], "visible_reply": condition["final"]["content"],
        "visible_reply_sha256": condition["final"]["content_sha256"],
        "calls": condition["calls"], "budget": condition["budget"],
        "surface_contract": raw["checks"]["all_final_replies_meet_shared_surface_contract"],
        "checks": checks, "network_attempts": attempts,
        "provider_call_evidence": raw["provider_call_evidence"],
        "real_model_calls": raw["real_model_calls"], "network_calls": raw["network_calls"],
        "paid_calls": 0, "source_turns_accessed": 1, "future_turns_accessed": 0,
        "annotations_accessed": 0, "confirmation_accessed": 0,
        "production_database_accessed": False, "product_result_content_loaded": False,
        "claim_boundary": "One fresh developer surface and accounting canary only; no pragmatic grading, holdout, human preference, or product advantage claim.",
    }


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
            payload = build_preflight(args.config)
        else:
            if not args.release or not args.checkpoint_root:
                raise P3ContractError("p3_b15_direct_run_artifacts_required")
            release = _read(Path(args.release))
            repo = Path(args.release).resolve().parent.parent
            if output.resolve() != (repo / release["authorization"]["result_path"]).resolve():
                raise P3ContractError("p3_b15_direct_result_path_mismatch")
            payload = run_canary(args.config, args.release, args.checkpoint_root)
    except P3ContractError as exc:
        evidence = summarize_checkpoint_evidence(args.checkpoint_root or "")
        payload = {
            "schema": "uruha_p3_direct_v2_surface_canary_failure_v1", "phase": "P3-B15",
            "status": "failed_after_transport_retained" if evidence["declared_invocation_intents"] else "refused_before_transport",
            "contract_code": exc.code, "checkpoint_evidence": evidence,
            "real_model_calls": evidence["provider_call_evidence"],
            "network_calls": evidence["network_call_evidence"], "paid_calls": 0,
        }
    write_new_json(output, payload)
    return 0 if payload.get("status") in {
        "ready_for_direct_v2_surface_canary_review", "direct_v2_surface_canary_pass"
    } else 3


if __name__ == "__main__":
    raise SystemExit(main())
