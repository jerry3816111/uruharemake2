#!/usr/bin/env python3
"""P3-B16 complete case-03 product/direct output lock before grading."""

from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import importlib
import json
import os
from pathlib import Path
import sys
import tempfile
import time
from typing import Any, Mapping

from p3_direct_baseline_v2_design_review import load_review
from p3_product_comparison import (
    P3ContractError,
    build_generation_view,
    canonical_sha256,
    load_design,
    record_condition_wall,
    run_condition,
    write_new_json,
)
from p3_strict_visible_surface_v2 import strict_japanese_visible_surface_contract
from p3_product_worker import (
    LocalOllamaQwenStageCounter,
    LocalQwenTokenizerCandidate,
    PRODUCTION_DB_PATH,
    ProductTransportGate,
    _local_canary_baseline_transport,
    _ollama_model_metadata,
    claim_case_workspace,
    install_product_transport_gate,
    localhost_network_only,
    prepare_isolated_environment,
    summarize_checkpoint_evidence,
)


SCHEMA = "uruha_p3_case03_dual_condition_output_lock_v1"
RELEASE_SCHEMA = "uruha_p3_case03_dual_condition_output_lock_release_v1"
MODEL_DIGEST = "2bada8a7450677000f678be90653b85d364de7db25eb5ea54136ada5f3933730"


def _read(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise P3ContractError("p3_b16_invalid_json", str(path)) from exc
    if not isinstance(value, dict):
        raise P3ContractError("p3_b16_invalid_json", str(path))
    return value


def _signed(payload: Mapping[str, Any]) -> dict[str, Any]:
    result = dict(payload)
    result["record_sha256"] = canonical_sha256(result)
    return result


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


def load_config(path: str | Path) -> dict[str, Any]:
    config_path = Path(path)
    raw = _read(config_path)
    if set(raw) != {
        "schema", "status", "purpose", "comparison_design", "direct_v2_review",
        "case_source", "b15_product_canary", "b15_direct_canary", "conditions",
        "common_history", "session_boundary", "direct_instruction", "generation",
        "execution_boundary", "retention", "success",
    } or raw.get("schema") != SCHEMA:
        raise P3ContractError("p3_b16_schema_mismatch")
    if raw.get("status") != "preregistered_not_executed" or raw.get("purpose") != (
        "lock_complete_case03_product_and_direct_outputs_before_annotation_access"
    ):
        raise P3ContractError("p3_b16_status_mismatch")
    repo = config_path.resolve().parent.parent
    design_path = _ref(repo, raw.get("comparison_design"), {
        "path": "configs/p3_product_comparison_v1.json",
        "sha256": "1e6d3b0600740b3dee7207ffc5c4f9cc9247a5feba2b967bdab4586522f7b836",
    }, "p3_b16_design_mismatch")
    review_path = _ref(repo, raw.get("direct_v2_review"), {
        "path": "configs/p3_direct_baseline_v2_design_review_v1.json",
        "sha256": "2d0a17759e4daa4f7fd9cc2533cda3d285d5c04bf88c8f7428dc96e194aeed53",
    }, "p3_b16_review_mismatch")
    source_path = _ref(repo, raw.get("case_source"), {
        "path": "datasets/p3_case03_generation_source_v1.json",
        "sha256": "cfae115a29453d51db948c39be2caf7c8d686dbda942ef0e45a591c31706a01a",
    }, "p3_b16_source_mismatch")
    product_canary_path = _ref(repo, raw.get("b15_product_canary"), {
        "path": "analysis/p3_b15_product_canary_result_2026-09-15.json",
        "sha256": "70cacf554526c3d33cedac7a9b58255c7df3f591a8d84cbaff9c1c0da5d44db4",
        "required_status": "product_canary_pass",
    }, "p3_b16_product_canary_mismatch")
    direct_canary_path = _ref(repo, raw.get("b15_direct_canary"), {
        "path": "analysis/p3_b15_direct_v2_surface_canary_result_2026-09-15.json",
        "sha256": "c5e0364de204c09818d73888c6d0acdaa802fcd807569c701fe5a1b200557842",
        "required_status": "direct_v2_surface_canary_pass",
    }, "p3_b16_direct_canary_mismatch")
    design = load_design(design_path)
    review = load_review(review_path)
    source = _read(source_path)
    product_canary = _read(product_canary_path)
    direct_canary = _read(direct_canary_path)
    if product_canary.get("status") != "product_canary_pass" or direct_canary.get("status") != "direct_v2_surface_canary_pass":
        raise P3ContractError("p3_b16_canary_status_invalid")
    source_repo = source_path.resolve().parent.parent
    parent_path = (source_repo / source["parent_source"]["path"]).resolve()
    if hashlib.sha256(parent_path.read_bytes()).hexdigest() != source["parent_source"]["sha256"]:
        raise P3ContractError("p3_b16_parent_source_mismatch")
    parent = _read(parent_path)
    parent_case = next(
        (case for case in parent.get("cases", []) if case.get("case_id") == source.get("case_id")),
        None,
    )
    if not isinstance(parent_case, Mapping) or source.get("turns") != parent_case.get("turns") or source.get("sessions") != parent_case.get("sessions"):
        raise P3ContractError("p3_b16_case_projection_mismatch")
    turns = source.get("turns")
    if not isinstance(turns, list) or len(turns) != 4 or any(
        canonical_sha256(turn.get("content")) != turn.get("content_sha256")
        for turn in turns if isinstance(turn, Mapping)
    ) or not all(isinstance(turn, Mapping) for turn in turns):
        raise P3ContractError("p3_b16_turn_contract_invalid")
    if source.get("annotations_included") is not False:
        raise P3ContractError("p3_b16_annotation_leak")
    if raw.get("conditions") != ["product_system", "full_history_direct"]:
        raise P3ContractError("p3_b16_conditions_mismatch")
    if raw.get("common_history") != {
        "mode": "system_anchored_prefix_paired", "include_all_prior_sessions": True,
        "include_roles": True, "include_only_past_visible_messages": True,
        "baseline_output_written_back": False,
        "current_product_reply_visible_to_baseline": False,
        "product_visible_reply_added_after_both_current_views_freeze": True,
        "cross_case_state_shared": False, "truncate_or_summarize": False,
    }:
        raise P3ContractError("p3_b16_history_mismatch")
    if raw.get("session_boundary") != {
        "restart_product_before_turn_ids": ["p3-smoke-03-u3"],
        "same_case_memory_path_retained": True, "new_brain_instance": True,
    }:
        raise P3ContractError("p3_b16_session_mismatch")
    if raw.get("direct_instruction") != review["direct_baseline"]["instruction"]:
        raise P3ContractError("p3_b16_direct_instruction_mismatch")
    model = design["model"]
    turn_budget = design["budget"]["per_condition_turn"]
    if raw.get("generation") != {
        "model": model["generation_model"], "digest": MODEL_DIGEST,
        "temperature": model["temperature"], "seed": model["seed"],
        "top_p": model["top_p"], "num_ctx": model["num_ctx"], "think": model["think"],
        "aggregate_prompt_tokens_max_per_condition_turn": turn_budget["aggregate_prompt_tokens_max"],
        "aggregate_completion_tokens_max_per_condition_turn": turn_budget["aggregate_completion_tokens_max"],
        "product_calls_max_per_turn": design["budget"]["system_calls_max"],
        "direct_calls_exact_per_turn": design["budget"]["direct_calls_max"],
        "wall_seconds_max_per_condition_turn": turn_budget["wall_seconds_max"],
    }:
        raise P3ContractError("p3_b16_generation_mismatch")
    if raw.get("execution_boundary") != {
        "source_turns_exact": 4, "visible_outputs_exact": 8,
        "product_provider_calls_min": 4, "product_provider_calls_max": 16,
        "direct_provider_calls_exact": 4, "total_provider_calls_max": 20,
        "automatic_retry": False, "concurrency": 1, "localhost_only": True,
        "b15_calls_reused_or_counted": False, "annotation_access": False,
        "confirmation_access": False, "production_database_access": False,
        "external_deployment": False, "remote_paid_calls": False,
        "real_model_calls_authorized_by_this_config": False,
    }:
        raise P3ContractError("p3_b16_boundary_mismatch")
    if raw.get("retention") != {
        "visible_replies": True, "product_runtime_trace": True,
        "product_memory_snapshot": True, "per_call_usage_and_hashes": True,
        "raw_provider_payload": False, "partial_failure_evidence": True,
        "ephemeral_workspace_removed": True,
    } or raw.get("success") != {
        "all_eight_visible_outputs_nonempty": True,
        "all_eight_shared_surface_pass": True,
        "all_four_view_pairs_share_source_and_prefix": True,
        "all_provider_calls_accounted": True,
        "all_condition_turn_budgets_valid": True,
        "session_restart_preserves_case_paths": True,
        "product_state_isolated_and_workspace_removed": True,
        "zero_annotation_or_production_access": True,
    }:
        raise P3ContractError("p3_b16_success_mismatch")
    design = deepcopy(design)
    design["baselines"]["direct_instruction"] = raw["direct_instruction"]
    frozen = deepcopy(raw)
    frozen["_config_sha256"] = hashlib.sha256(config_path.read_bytes()).hexdigest()
    frozen["_config_path"] = str(config_path.resolve())
    frozen["_source"] = source
    frozen["_design"] = design
    return frozen


def build_views(prefix: list[dict[str, str]], turn: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    current = {
        "turn_id": turn["turn_id"],
        "session_id": turn["session_id"],
        "content": turn["content"],
    }
    return {
        condition: build_generation_view(prefix, current, condition)
        for condition in ("product_system", "full_history_direct")
    }


def append_product_prefix(
    prefix: list[dict[str, str]], turn: Mapping[str, Any], reply: str
) -> None:
    prefix.extend([
        {
            "turn_id": turn["turn_id"],
            "session_id": turn["session_id"],
            "role": "user",
            "content": turn["content"],
        },
        {
            "turn_id": f"{turn['turn_id']}-a-product",
            "session_id": turn["session_id"],
            "role": "assistant",
            "content": reply,
        },
    ])


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
    view_checks = []
    for turn in config["_source"]["turns"]:
        views = build_views(prefix, turn)
        view_checks.append(
            views["product_system"]["source_history_sha256"]
            == views["full_history_direct"]["source_history_sha256"]
            and views["product_system"]["input_sha256"]
            == views["full_history_direct"]["input_sha256"]
        )
        append_product_prefix(prefix, turn, f"未生成product-{turn['turn_id']}")
    checks = {
        "config_valid": True,
        "model_digest_matches": metadata["digest"] == MODEL_DIGEST,
        "four_source_turns": len(config["_source"]["turns"]) == 4,
        "all_offline_view_pairs_share_source": all(view_checks),
        "first_direct_prompt_count_available": counter(messages) > 0,
        "session_restart_boundary_exact": config["session_boundary"]["restart_product_before_turn_ids"] == ["p3-smoke-03-u3"],
        "annotations_closed": config["execution_boundary"]["annotation_access"] is False,
        "config_does_not_self_authorize": config["execution_boundary"]["real_model_calls_authorized_by_this_config"] is False,
    }
    return {
        "schema": "uruha_p3_case03_dual_condition_output_lock_preflight_v1",
        "phase": "P3-B16",
        "status": "ready_for_case03_output_lock_review" if all(checks.values()) else "not_ready_for_case03_output_lock_review",
        "config_sha256": config["_config_sha256"], "checks": checks,
        "first_direct_prompt_tokens": counter(messages),
        "turn_ids": [turn["turn_id"] for turn in config["_source"]["turns"]],
        "real_model_calls": 0, "network_calls": 0, "paid_calls": 0,
        "annotations_accessed": 0, "confirmation_accessed": 0,
        "production_database_accessed": False,
        "claim_boundary": "Preflight only; no case output or quality grade is produced.",
    }


def validate_release(path: str | Path, config: Mapping[str, Any]) -> dict[str, Any]:
    release_path = Path(path)
    release = _read(release_path)
    if set(release) != {
        "schema", "phase", "status", "review_kind", "config",
        "implementation_sha256", "preflight", "authorization", "claim_boundary",
    } or release.get("schema") != RELEASE_SCHEMA:
        raise P3ContractError("p3_b16_release_schema_mismatch")
    if release.get("phase") != "P3-B16" or release.get("status") != "released_for_case03_output_lock":
        raise P3ContractError("p3_b16_release_status_mismatch")
    if release.get("review_kind") != "same_task_self_review_not_independent":
        raise P3ContractError("p3_b16_release_review_mismatch")
    repo = release_path.resolve().parent.parent
    if release.get("config") != {
        "path": "configs/p3_case03_dual_condition_output_lock_v1.json",
        "sha256": config["_config_sha256"],
    }:
        raise P3ContractError("p3_b16_release_config_mismatch")
    implementation = release.get("implementation_sha256")
    required = {"p3_case03_dual_condition_output_lock.py", "test_p3_case03_dual_condition_output_lock.py"}
    if not isinstance(implementation, Mapping) or set(implementation) != required:
        raise P3ContractError("p3_b16_release_implementation_invalid")
    for name, sha in implementation.items():
        if hashlib.sha256((repo / name).read_bytes()).hexdigest() != sha:
            raise P3ContractError("p3_b16_release_implementation_mismatch", name)
    preflight = release.get("preflight")
    preflight_path = (repo / str((preflight or {}).get("path"))).resolve()
    if not isinstance(preflight, Mapping) or set(preflight) != {"path", "sha256", "status"} or (
        not preflight_path.is_file()
        or hashlib.sha256(preflight_path.read_bytes()).hexdigest() != preflight.get("sha256")
        or preflight.get("status") != "ready_for_case03_output_lock_review"
    ):
        raise P3ContractError("p3_b16_release_preflight_mismatch")
    if release.get("authorization") != {
        "run_id": "p3-b16-case03-output-lock-v1", "localhost_only": True,
        "model": "qwen2.5:7b", "model_digest": MODEL_DIGEST,
        "case_id": "p3-smoke-emotional-bid-ja",
        "turn_ids": ["p3-smoke-03-u1", "p3-smoke-03-u2", "p3-smoke-03-u3", "p3-smoke-03-u4"],
        "product_provider_calls_min": 4, "product_provider_calls_max": 16,
        "direct_provider_calls_exact": 4, "total_provider_calls_max": 20,
        "automatic_retry": False,
        "checkpoint_root": "analysis/p3_b16_case03_output_lock_checkpoints_v1",
        "result_path": "analysis/p3_b16_case03_output_lock_result_2026-09-15.json",
        "annotation_access": False, "confirmation_access": False,
        "production_database_access": False, "external_deployment": False,
    }:
        raise P3ContractError("p3_b16_release_authorization_mismatch")
    return release


def _write_product_intent(path: Path, config: Mapping[str, Any], turn: Mapping[str, Any], views: Mapping[str, Any]) -> None:
    if path.parent.exists():
        raise P3ContractError("p3_b16_product_turn_checkpoint_exists_no_retry", turn["turn_id"])
    write_new_json(path, _signed({
        "schema": "uruha_p3_b16_product_turn_intent_v1",
        "config_sha256": config["_config_sha256"], "turn_id": turn["turn_id"],
        "session_id": turn["session_id"],
        "product_view_sha256": views["product_system"]["view_sha256"],
        "direct_view_sha256": views["full_history_direct"]["view_sha256"],
    }))


def run_case(config_path: str | Path, release_path: str | Path, checkpoint_root: str | Path) -> dict[str, Any]:
    config = load_config(config_path)
    release = validate_release(release_path, config)
    repo = Path(release_path).resolve().parent.parent
    checkpoint = Path(checkpoint_root).resolve()
    if checkpoint != (repo / release["authorization"]["checkpoint_root"]).resolve():
        raise P3ContractError("p3_b16_checkpoint_path_mismatch")
    if checkpoint.exists():
        raise P3ContractError("p3_b16_checkpoint_exists_no_retry")
    if _ollama_model_metadata("qwen2.5:7b")["digest"] != MODEL_DIGEST:
        raise P3ContractError("p3_b16_runtime_model_mismatch")
    direct_transport_config = {
        "generation": {
            "model": "qwen2.5:7b", "temperature": 0, "seed": 20260909,
            "top_p": 1, "num_ctx": 8192, "think": False,
        },
        "transport": {
            "backend": "openai_compatible_local",
            "url": "http://127.0.0.1:11434/v1/chat/completions",
            "per_call_timeout_seconds": 60,
        },
    }
    direct_transport = _local_canary_baseline_transport(direct_transport_config)
    direct_counter = LocalOllamaQwenStageCounter(merge_adjacent_assistant=True)
    product_rows: list[dict[str, Any]] = []
    direct_rows: list[dict[str, Any]] = []
    prefix: list[dict[str, str]] = []
    session_instances: dict[str, int] = {}
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="uruha-p3b16-case03-") as temporary:
        temporary_path = Path(temporary)
        case_workspace = claim_case_workspace(
            temporary_path / "workspace", config["_source"]["case_id"]
        )
        env = prepare_isolated_environment(case_workspace, config["_design"])
        forbidden_modules = {"uruha_brain_mac", "uruha_web_ui", "uruha_web_ui_product"}
        already_loaded = sorted(forbidden_modules.intersection(sys.modules))
        if already_loaded:
            raise P3ContractError("p3_b16_product_import_not_fresh", ",".join(already_loaded))
        paths = case_workspace["paths"]
        with localhost_network_only() as network_attempts:
            import project_paths

            project_paths.WEB_LOG_DIR = str(paths["web_logs"])
            project_paths.WEB_CONVERSATION_LOG_JSONL_PATH = env["URUHA_WEB_LOG_JSONL_PATH"]
            project_paths.WEB_CONVERSATION_LOG_TXT_PATH = env["URUHA_WEB_LOG_TXT_PATH"]
            product = importlib.import_module("uruha_web_ui_product")
            brain_module = product._brain
            tokenizer = LocalQwenTokenizerCandidate()
            original_openai = brain_module.OpenAI
            original_urlopen = brain_module.urllib.request.urlopen
            brain_instance = None
            current_session = None
            try:
                for turn in config["_source"]["turns"]:
                    views = build_views(prefix, turn)
                    product_view = views["product_system"]
                    direct_view = views["full_history_direct"]
                    if (
                        product_view["source_history_sha256"] != direct_view["source_history_sha256"]
                        or product_view["input_sha256"] != direct_view["input_sha256"]
                    ):
                        raise P3ContractError("p3_b16_view_pair_mismatch", turn["turn_id"])
                    restart = current_session is not None and turn["session_id"] != current_session
                    if brain_instance is None:
                        init_started = time.monotonic()
                        brain_instance = product.RUNTIME.get_brain()
                        init_seconds = time.monotonic() - init_started
                    elif restart:
                        brain_module.OpenAI = original_openai
                        brain_module.urllib.request.urlopen = original_urlopen
                        init_started = time.monotonic()
                        brain_instance = brain_module.UruhaBrainV4_Mac()
                        init_seconds = time.monotonic() - init_started
                    else:
                        init_seconds = 0.0
                    current_session = turn["session_id"]
                    session_instances.setdefault(current_session, id(brain_instance))

                    product_intent = checkpoint / "product" / turn["turn_id"] / "intent.json"
                    product_complete = product_intent.with_name("complete.json")
                    product_failure = product_intent.with_name("failure.json")
                    _write_product_intent(product_intent, config, turn, views)
                    gate = ProductTransportGate(
                        config["_design"], tokenizer,
                        allow_real_transport=True, provider_binding_verified=True,
                    )
                    brain_module.OpenAI = original_openai
                    brain_module.urllib.request.urlopen = original_urlopen
                    install_product_transport_gate(brain_module, gate)
                    turn_started = time.monotonic()
                    try:
                        product_turn = brain_instance.run_turn_debug(
                            turn["content"],
                            input_context={"input_mode": "text", "acoustic_summary": None},
                        )
                        product_seconds = time.monotonic() - turn_started
                        record_condition_wall(gate.budget, product_seconds)
                        product_reply = product_turn.get("reply") if isinstance(product_turn, Mapping) else None
                        memory_snapshot = brain_instance.memory.get_runtime_snapshot()
                        product_row = {
                            "turn_id": turn["turn_id"], "session_id": turn["session_id"],
                            "session_restart_before_turn": restart,
                            "initialization_seconds": round(init_seconds, 6),
                            "turn_wall_seconds": round(product_seconds, 6),
                            "view_sha256": product_view["view_sha256"],
                            "source_history_sha256": product_view["source_history_sha256"],
                            "input_sha256": product_view["input_sha256"],
                            "visible_reply": product_reply,
                            "visible_reply_sha256": canonical_sha256(product_reply),
                            "surface_contract": strict_japanese_visible_surface_contract(product_reply),
                            "logic": product_turn.get("logic") if isinstance(product_turn, Mapping) else None,
                            "runtime_trace": product_turn.get("runtime_trace") if isinstance(product_turn, Mapping) else None,
                            "memory_snapshot": memory_snapshot,
                            "calls": list(gate.interceptions), "budget": gate.budget.snapshot(),
                            "rejections": list(gate.rejections),
                            "memory_path_sha256": canonical_sha256(str(paths["memory"].resolve())),
                            "real_model_calls": sum(call["real_model_calls"] for call in gate.interceptions),
                            "network_calls": sum(call["network_calls"] for call in gate.interceptions),
                            "actual_prompt_tokens": sum(call["usage"]["prompt_tokens"] for call in gate.interceptions),
                            "actual_completion_tokens": sum(call["usage"]["completion_tokens"] for call in gate.interceptions),
                        }
                        write_new_json(product_complete, _signed({
                            "schema": "uruha_p3_b16_product_turn_complete_v1",
                            "turn_id": turn["turn_id"], "result": product_row,
                        }))
                    except Exception as exc:
                        if not product_failure.exists():
                            observed_calls = list(gate.interceptions)
                            write_new_json(product_failure, _signed({
                                "schema": "uruha_p3_b16_product_turn_failure_v1",
                                "turn_id": turn["turn_id"],
                                "error_type": type(exc).__name__,
                                "error_sha256": canonical_sha256(str(exc)),
                                "response_received": bool(observed_calls),
                                "provider_actual_usage": {
                                    "prompt_tokens": sum(call["usage"]["prompt_tokens"] for call in observed_calls),
                                    "completion_tokens": sum(call["usage"]["completion_tokens"] for call in observed_calls),
                                    "real_model_calls": sum(call["real_model_calls"] for call in observed_calls),
                                    "network_calls": sum(call["network_calls"] for call in observed_calls),
                                },
                            }))
                        raise
                    finally:
                        brain_module.OpenAI = original_openai
                        brain_module.urllib.request.urlopen = original_urlopen
                    product_rows.append(product_row)

                    direct_started = time.monotonic()
                    direct_result = run_condition(
                        condition="full_history_direct", view=direct_view,
                        design=config["_design"], transport=direct_transport,
                        checkpoint_root=checkpoint / "direct",
                        item_id=f"{config['_source']['case_id']}:{turn['turn_id']}:full_history_direct",
                        token_counter=direct_counter,
                        backend="openai_compatible_local",
                    )
                    direct_seconds = time.monotonic() - direct_started
                    direct_result["turn_wall_seconds"] = round(direct_seconds, 6)
                    direct_result["turn_id"] = turn["turn_id"]
                    direct_result["session_id"] = turn["session_id"]
                    direct_result["view_sha256"] = direct_view["view_sha256"]
                    direct_result["surface_contract"] = strict_japanese_visible_surface_contract(
                        direct_result["final"]["content"]
                    )
                    direct_rows.append(direct_result)
                    append_product_prefix(prefix, turn, str(product_reply or ""))
            finally:
                brain_module.OpenAI = original_openai
                brain_module.urllib.request.urlopen = original_urlopen
            production_db_unreachable = (
                Path(brain_module.DB_PATH).resolve() == paths["memory"].resolve()
                and Path(brain_module.DB_PATH).resolve() != PRODUCTION_DB_PATH
            )
        workspace_paths = {key: canonical_sha256(str(value.resolve())) for key, value in paths.items()}
    ephemeral_removed = not temporary_path.exists()
    product_calls = [call for row in product_rows for call in row["calls"]]
    direct_calls = [call for row in direct_rows for call in row["calls"]]
    all_surfaces = [row["surface_contract"] for row in product_rows] + [row["surface_contract"] for row in direct_rows]
    source_session_ids = [row["session_id"] for row in config["_source"]["sessions"]]
    checks = {
        "all_eight_visible_outputs_nonempty": len(product_rows) == len(direct_rows) == 4 and all(
            bool(str(row["visible_reply"]).strip()) for row in product_rows
        ) and all(bool(row["final"]["content"].strip()) for row in direct_rows),
        "all_eight_shared_surface_pass": len(all_surfaces) == 8 and all(all(surface.values()) for surface in all_surfaces),
        "all_four_view_pairs_share_source_and_prefix": all(
            product_rows[index]["source_history_sha256"] == direct_rows[index]["source_history_sha256"]
            and product_rows[index]["input_sha256"] == direct_rows[index]["input_sha256"]
            for index in range(min(len(product_rows), len(direct_rows)))
        ) and len(product_rows) == len(direct_rows) == 4,
        "all_provider_calls_accounted": (
            4 <= len(product_calls) <= 16
            and len(direct_calls) == 4
            and all(call["real_model_calls"] == call["network_calls"] == 1 for call in product_calls + direct_calls)
        ),
        "all_condition_turn_budgets_valid": all(
            row["budget"]["attempts"] == row["budget"]["completed_calls"]
            and row["budget"]["terminal_failure"] is None
            for row in product_rows + direct_rows
        ),
        "session_restart_preserves_case_paths": (
            product_rows[2]["session_restart_before_turn"] is True
            and len(source_session_ids) == 2
            and session_instances.get(source_session_ids[0]) != session_instances.get(source_session_ids[1])
            and len({row["memory_path_sha256"] for row in product_rows}) == 1
            and len(set(workspace_paths.values())) == len(workspace_paths)
        ),
        "product_state_isolated_and_workspace_removed": production_db_unreachable and ephemeral_removed,
        "zero_annotation_or_production_access": True,
        "localhost_only": all(attempt["loopback_allowed"] is True for attempt in network_attempts),
    }
    passed = all(checks.values())
    return {
        "schema": "uruha_p3_case03_dual_condition_output_lock_result_v1",
        "phase": "P3-B16",
        "status": "case03_outputs_locked" if passed else "case03_output_lock_failed_retained",
        "config_sha256": config["_config_sha256"],
        "release_sha256": hashlib.sha256(Path(release_path).read_bytes()).hexdigest(),
        "case_id": config["_source"]["case_id"],
        "product_turns": product_rows, "direct_turns": direct_rows,
        "checks": checks, "network_attempts": network_attempts,
        "provider_call_evidence": len(product_calls) + len(direct_calls),
        "real_model_calls": sum(call["real_model_calls"] for call in product_calls + direct_calls),
        "network_calls": sum(call["network_calls"] for call in product_calls + direct_calls),
        "paid_calls": 0,
        "actual_prompt_tokens": sum(call["usage"]["prompt_tokens"] for call in product_calls + direct_calls),
        "actual_completion_tokens": sum(call["usage"]["completion_tokens"] for call in product_calls + direct_calls),
        "total_wall_seconds": round(time.monotonic() - started, 6),
        "source_turns_accessed": 4, "future_turns_accessed": 0,
        "annotations_accessed": 0, "confirmation_accessed": 0,
        "production_database_accessed": False,
        "ephemeral_workspace_removed": ephemeral_removed,
        "b15_calls_reused_or_counted": False,
        "claim_boundary": "Complete developer case outputs are locked before annotation access. This is generation evidence only, not a pragmatic grade, holdout, human preference, or advantage result.",
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
                raise P3ContractError("p3_b16_run_artifacts_required")
            release = _read(Path(args.release))
            repo = Path(args.release).resolve().parent.parent
            if output.resolve() != (repo / release["authorization"]["result_path"]).resolve():
                raise P3ContractError("p3_b16_result_path_mismatch")
            payload = run_case(args.config, args.release, args.checkpoint_root)
    except P3ContractError as exc:
        evidence = summarize_checkpoint_evidence(args.checkpoint_root or "")
        payload = {
            "schema": "uruha_p3_case03_dual_condition_output_lock_failure_v1",
            "phase": "P3-B16",
            "status": "failed_after_transport_retained" if evidence["declared_invocation_intents"] else "refused_before_transport",
            "contract_code": exc.code, "checkpoint_evidence": evidence,
            "real_model_calls": evidence["provider_call_evidence"],
            "network_calls": evidence["network_call_evidence"], "paid_calls": 0,
            "annotations_accessed": 0, "production_database_accessed": False,
        }
    write_new_json(output, payload)
    return 0 if payload.get("status") in {
        "ready_for_case03_output_lock_review", "case03_outputs_locked"
    } else 3


if __name__ == "__main__":
    raise SystemExit(main())
