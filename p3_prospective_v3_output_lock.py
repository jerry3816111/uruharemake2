#!/usr/bin/env python3
"""P3-B46 one-time prospective v3 product/direct output lock."""

from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import importlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any, Mapping

from p3_product_comparison import (
    P3ContractError,
    canonical_sha256,
    record_condition_wall,
    run_condition,
    write_new_json,
)
import p3_prospective_v3_execution_contract as execution_contract
from p3_prospective_v3_real_adapter import (
    CheckpointedProductTransportGate,
    ProviderCallJournal,
    install_checkpointed_product_transport_gate,
)
import p3_product_worker as worker
from p3_strict_visible_surface_v2 import strict_japanese_visible_surface_contract


RELEASE_SCHEMA = "uruha_p3_prospective_v3_output_lock_release_v1"
RESULT_SCHEMA = "uruha_p3_prospective_v3_output_lock_result_v1"
B45_FREEZE_PATH = "research/p3_b45_prospective_v3_execution_contract_freeze_2026-09-17.json"
B45_FREEZE_SHA256 = "061044dcbe3cac5e2c6dba0073250dee32fddf1bb7618e823a767213d22c2069"
RUN_ID = "p3-b46-prospective-v3-output-lock-v1"


def _read(path: str | Path) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise P3ContractError("p3_b46_invalid_json", str(path)) from exc
    if not isinstance(value, dict):
        raise P3ContractError("p3_b46_invalid_json", str(path))
    return value


def _sha(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _signed(payload: Mapping[str, Any]) -> dict[str, Any]:
    value = dict(payload)
    value["record_sha256"] = canonical_sha256(value)
    return value


def _verify_signed(value: Mapping[str, Any], code: str) -> None:
    expected = value.get("record_sha256")
    payload = dict(value)
    payload.pop("record_sha256", None)
    if not isinstance(expected, str) or expected != canonical_sha256(payload):
        raise P3ContractError(code)


def build_run_commitment(
    config: Mapping[str, Any], release_path: str | Path, schedule: Mapping[str, Any]
) -> dict[str, Any]:
    return _signed({
        "schema": "uruha_p3_b46_output_lock_run_commitment_v1",
        "run_id": RUN_ID,
        "config_sha256": config["_config_sha256"],
        "release_sha256": _sha(release_path),
        "source_sha256": execution_contract.SOURCE_SHA256,
        "rubric_sha256_commitment_only": execution_contract.RUBRIC_SHA256,
        "product_snapshot_commit": execution_contract.PRODUCT_COMMIT,
        "product_manifest_sha256": config["_product_manifest"]["manifest_sha256"],
        "schedule_sha256": schedule["schedule_sha256"],
        "automatic_retry": False, "fallback": False,
        "annotation_access": False, "production_database_access": False,
    })


def _write_or_validate(path: Path, value: Mapping[str, Any], code: str) -> None:
    if path.exists():
        existing = _read(path)
        _verify_signed(existing, code)
        if existing != dict(value):
            raise P3ContractError(code)
    else:
        write_new_json(path, dict(value))


def validate_release(path: str | Path, config: Mapping[str, Any]) -> dict[str, Any]:
    release_path = Path(path).resolve()
    release = _read(release_path)
    if (
        release.get("schema") != RELEASE_SCHEMA
        or release.get("phase") != "P3-B46"
        or release.get("status") != "released_for_single_prospective_v3_output_lock"
        or release.get("review_kind") != "same_task_design_review_not_independent"
    ):
        raise P3ContractError("p3_b46_release_invalid")
    expected_paths = {
        "config": "configs/p3_prospective_v3_execution_contract_v1.json",
        "b45_contract_freeze": B45_FREEZE_PATH,
        "adapter": "p3_prospective_v3_real_adapter.py",
        "runner": "p3_prospective_v3_output_lock.py",
        "adapter_tests": "test_p3_prospective_v3_real_adapter.py",
        "runner_tests": "test_p3_prospective_v3_output_lock.py",
        "preflight": "analysis/p3_b46_prospective_v3_output_lock_preflight_2026-09-17.json",
        "implementation_freeze": "research/p3_b46_prospective_v3_output_lock_implementation_freeze_2026-09-17.json"
    }
    artifacts = release.get("artifacts")
    if not isinstance(artifacts, Mapping) or set(artifacts) != set(expected_paths):
        raise P3ContractError("p3_b46_release_artifacts_invalid")
    repo = Path(__file__).resolve().parent
    for name, relative in expected_paths.items():
        expected = {"path": relative, "sha256": _sha(repo / relative)}
        if artifacts.get(name) != expected:
            raise P3ContractError("p3_b46_release_artifact_mismatch", name)
    authorization = release.get("authorization")
    if authorization != {
        "run_id": RUN_ID,
        "localhost_only": True,
        "model": "qwen2.5:7b",
        "model_digest": execution_contract.MODEL_DIGEST,
        "case_ids": execution_contract.CASE_IDS,
        "condition_order_per_turn": execution_contract.CONDITIONS,
        "logical_condition_steps_exact": 24,
        "visible_outputs_exact": 24,
        "product_provider_calls_min": 0,
        "product_provider_calls_max": 48,
        "direct_provider_calls_exact": 12,
        "total_provider_calls_max": 60,
        "automatic_retry": False,
        "fallback": False,
        "checkpoint_root": "analysis/p3_b46_prospective_v3_output_lock_checkpoints_v1",
        "workspace_root_basename": "uruha-p3-b46-prospective-v3-workspace-v1",
        "result_path": "analysis/p3_b46_prospective_v3_output_lock_result_2026-09-17.json",
        "annotation_access": False,
        "confirmation_access": False,
        "production_database_access": False,
        "external_deployment": False,
    }:
        raise P3ContractError("p3_b46_release_authorization_invalid")
    preflight = _read(repo / expected_paths["preflight"])
    freeze = _read(repo / expected_paths["implementation_freeze"])
    b45 = _read(repo / B45_FREEZE_PATH)
    if (
        preflight.get("status") != "ready_for_real_adapter_release_review"
        or not all((preflight.get("checks") or {}).values())
        or freeze.get("status") != "prospective_v3_real_adapter_implementation_frozen"
        or b45.get("status") != "prospective_v3_execution_contract_frozen"
        or config["execution_boundary"]["real_model_calls_authorized_by_this_config"] is not False
    ):
        raise P3ContractError("p3_b46_release_preflight_invalid")
    return release


def build_preflight(config_path: str | Path) -> dict[str, Any]:
    config = execution_contract.load_config(config_path)
    repo = Path(__file__).resolve().parent
    b45_path = repo / B45_FREEZE_PATH
    if _sha(b45_path) != B45_FREEZE_SHA256:
        raise P3ContractError("p3_b46_b45_freeze_drift")
    b45 = _read(b45_path)
    schedule = execution_contract.build_schedule(config)
    metadata = worker._ollama_model_metadata(config["generation"]["model"])
    checks = {
        "b45_contract_freeze_valid": b45.get("status") == "prospective_v3_execution_contract_frozen",
        "source_rubric_and_product_commitments_unchanged": (
            b45["bindings"]["source_sha256"] == execution_contract.SOURCE_SHA256
            and b45["bindings"]["rubric_sha256_commitment_only"] == execution_contract.RUBRIC_SHA256
            and b45["bindings"]["product_snapshot_commit"] == execution_contract.PRODUCT_COMMIT
        ),
        "runtime_model_digest_matches": metadata["digest"] == execution_contract.MODEL_DIGEST,
        "schedule_has_twenty_four_steps": len(schedule["steps"]) == 24,
        "adapter_and_runner_present": (repo / "p3_prospective_v3_real_adapter.py").is_file()
        and (repo / "p3_prospective_v3_output_lock.py").is_file(),
        "annotations_closed": config["execution_boundary"]["annotation_access"] is False,
        "config_does_not_self_authorize": config["execution_boundary"]["real_model_calls_authorized_by_this_config"] is False,
        "separate_release_required": config["execution_boundary"]["separate_release_required"] is True,
    }
    return {
        "schema": "uruha_p3_b46_prospective_v3_output_lock_preflight_v1",
        "phase": "P3-B46",
        "status": "ready_for_real_adapter_release_review" if all(checks.values()) else "not_ready_for_real_adapter_release_review",
        "config_sha256": config["_config_sha256"],
        "schedule_sha256": schedule["schedule_sha256"],
        "model_metadata": metadata,
        "checks": checks,
        "real_model_calls": 0, "network_calls": 0, "paid_calls": 0,
        "annotations_accessed": 0, "production_database_accessed": False,
        "claim_boundary": "Zero-generation real-adapter preflight only; a separate signed release is still required.",
    }


def _logical_paths(root: Path, case_id: str, turn_id: str) -> dict[str, Path]:
    folder = root / "logical_product_turns" / hashlib.sha256(case_id.encode()).hexdigest()[:16] / hashlib.sha256(turn_id.encode()).hexdigest()[:16]
    return {name: folder / f"{name}.json" for name in ("intent", "complete", "failure")}


def _read_product_complete(
    paths: Mapping[str, Path], run_sha: str, turn_id: str, product_view_sha: str
) -> dict[str, Any] | None:
    if paths["failure"].exists():
        failure = _read(paths["failure"])
        _verify_signed(failure, "p3_b46_logical_failure_drift")
        raise P3ContractError("p3_b46_logical_product_turn_terminal", turn_id)
    if paths["complete"].exists():
        complete = _read(paths["complete"])
        _verify_signed(complete, "p3_b46_logical_complete_drift")
        if (
            complete.get("run_commitment_sha256") != run_sha
            or complete.get("turn_id") != turn_id
            or complete.get("product_view_sha256") != product_view_sha
            or not isinstance(complete.get("result"), Mapping)
        ):
            raise P3ContractError("p3_b46_logical_complete_source_mismatch", turn_id)
        return dict(complete["result"])
    if paths["intent"].exists():
        intent = _read(paths["intent"])
        _verify_signed(intent, "p3_b46_logical_intent_drift")
        raise P3ContractError("p3_b46_logical_intent_without_complete_terminal", turn_id)
    return None


def _write_product_intent(
    paths: Mapping[str, Path], run_sha: str, turn: Mapping[str, Any], views: Mapping[str, Any]
) -> None:
    write_new_json(paths["intent"], _signed({
        "schema": "uruha_p3_b46_logical_product_turn_intent_v1",
        "run_commitment_sha256": run_sha,
        "turn_id": turn["turn_id"], "session_id": turn["session_id"],
        "product_view_sha256": views["product_system"]["view_sha256"],
        "direct_view_sha256": views["full_history_direct"]["view_sha256"],
        "automatic_retry": False,
    }))


def _case_result_path(root: Path, case_id: str) -> Path:
    return root / "case_results" / f"{hashlib.sha256(case_id.encode()).hexdigest()[:20]}.json"


def _direct_transport_config() -> dict[str, Any]:
    return {
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


def run_case_worker(
    config_path: str | Path, release_path: str | Path, checkpoint_root: str | Path,
    workspace_root: str | Path, case_index: int,
) -> dict[str, Any]:
    config = execution_contract.load_config(config_path)
    validate_release(release_path, config)
    schedule = execution_contract.build_schedule(config)
    root = Path(checkpoint_root).resolve()
    commitment = _read(root / "run_commitment.json")
    _verify_signed(commitment, "p3_b46_run_commitment_drift")
    expected_commitment = build_run_commitment(config, release_path, schedule)
    if commitment != expected_commitment:
        raise P3ContractError("p3_b46_run_commitment_drift")
    if case_index not in range(3):
        raise P3ContractError("p3_b46_case_index_invalid")
    case = config["_source"]["cases"][case_index]
    design = deepcopy(config["_design"])
    design["baselines"]["direct_instruction"] = config["_direct_instruction"]
    case_workspace = worker.claim_case_workspace(workspace_root, case["case_id"])
    environment = worker.prepare_isolated_environment(case_workspace, design)
    forbidden = {"uruha_brain_mac", "uruha_web_ui", "uruha_web_ui_product"}.intersection(sys.modules)
    if forbidden:
        raise P3ContractError("p3_b46_product_import_not_fresh", ",".join(sorted(forbidden)))
    paths = case_workspace["paths"]
    product_rows: list[dict[str, Any]] = []
    direct_rows: list[dict[str, Any]] = []
    prefix: list[dict[str, str]] = []
    direct_transport = worker._local_canary_baseline_transport(_direct_transport_config())
    direct_counter = worker.LocalOllamaQwenStageCounter(merge_adjacent_assistant=True)
    started = time.monotonic()
    with worker.localhost_network_only() as network_attempts:
        import project_paths

        project_paths.WEB_LOG_DIR = str(paths["web_logs"])
        project_paths.WEB_CONVERSATION_LOG_JSONL_PATH = environment["URUHA_WEB_LOG_JSONL_PATH"]
        project_paths.WEB_CONVERSATION_LOG_TXT_PATH = environment["URUHA_WEB_LOG_TXT_PATH"]
        product = importlib.import_module("uruha_web_ui_product")
        brain_module = product._brain
        original_openai = brain_module.OpenAI
        original_urlopen = brain_module.urllib.request.urlopen
        brain_instance = product.RUNTIME.get_brain()
        tokenizer = worker.LocalQwenTokenizerCandidate()
        current_session = None
        session_instance_ids: dict[str, int] = {}
        try:
            for turn_index, turn in enumerate(case["turns"]):
                import p3_case03_dual_condition_output_lock as view_engine

                views = view_engine.build_views(prefix, turn)
                product_view, direct_view = views["product_system"], views["full_history_direct"]
                if (
                    product_view["source_history_sha256"] != direct_view["source_history_sha256"]
                    or product_view["input_sha256"] != direct_view["input_sha256"]
                ):
                    raise P3ContractError("p3_b46_view_pair_mismatch", turn["turn_id"])
                restart = current_session is not None and turn["session_id"] != current_session
                if restart:
                    brain_module.OpenAI = original_openai
                    brain_module.urllib.request.urlopen = original_urlopen
                    brain_instance = brain_module.UruhaBrainV4_Mac()
                current_session = turn["session_id"]
                session_instance_ids.setdefault(current_session, id(brain_instance))
                logical = _logical_paths(root, case["case_id"], turn["turn_id"])
                product_row = _read_product_complete(
                    logical, commitment["record_sha256"], turn["turn_id"], product_view["view_sha256"]
                )
                if product_row is None:
                    _write_product_intent(logical, commitment["record_sha256"], turn, views)
                    journal = ProviderCallJournal(
                        root / "product_provider_calls",
                        commitment["record_sha256"],
                    )
                    gate = CheckpointedProductTransportGate(
                        design, tokenizer,
                        allow_real_transport=True, provider_binding_verified=True,
                        journal=journal,
                        logical_step_id=f"{case['case_id']}:{turn['turn_id']}:product_system",
                    )
                    brain_module.OpenAI = original_openai
                    brain_module.urllib.request.urlopen = original_urlopen
                    install_checkpointed_product_transport_gate(brain_module, gate)
                    turn_started = time.monotonic()
                    try:
                        product_turn = brain_instance.run_turn_debug(
                            turn["content"],
                            input_context={"input_mode": "text", "acoustic_summary": None},
                        )
                        elapsed = time.monotonic() - turn_started
                        record_condition_wall(gate.budget, elapsed)
                        reply = product_turn.get("reply") if isinstance(product_turn, Mapping) else None
                        product_row = {
                            "turn_id": turn["turn_id"], "session_id": turn["session_id"],
                            "session_restart_before_turn": restart,
                            "turn_wall_seconds": round(elapsed, 6),
                            "view_sha256": product_view["view_sha256"],
                            "source_history_sha256": product_view["source_history_sha256"],
                            "input_sha256": product_view["input_sha256"],
                            "visible_reply": reply,
                            "visible_reply_sha256": canonical_sha256(reply),
                            "surface_contract": strict_japanese_visible_surface_contract(reply),
                            "logic": product_turn.get("logic") if isinstance(product_turn, Mapping) else None,
                            "runtime_trace": product_turn.get("runtime_trace") if isinstance(product_turn, Mapping) else None,
                            "memory_snapshot": brain_instance.memory.get_runtime_snapshot(),
                            "calls": list(gate.interceptions),
                            "budget": gate.budget.snapshot(), "rejections": list(gate.rejections),
                            "memory_path_sha256": canonical_sha256(str(paths["memory"].resolve())),
                            "real_model_calls": sum(row["real_model_calls"] for row in gate.interceptions),
                            "network_calls": sum(row["network_calls"] for row in gate.interceptions),
                            "actual_prompt_tokens": sum(row["usage"]["prompt_tokens"] for row in gate.interceptions),
                            "actual_completion_tokens": sum(row["usage"]["completion_tokens"] for row in gate.interceptions),
                        }
                        write_new_json(logical["complete"], _signed({
                            "schema": "uruha_p3_b46_logical_product_turn_complete_v1",
                            "run_commitment_sha256": commitment["record_sha256"],
                            "turn_id": turn["turn_id"],
                            "product_view_sha256": product_view["view_sha256"],
                            "result": product_row,
                        }))
                    except Exception as exc:
                        if not logical["failure"].exists():
                            write_new_json(logical["failure"], _signed({
                                "schema": "uruha_p3_b46_logical_product_turn_failure_v1",
                                "run_commitment_sha256": commitment["record_sha256"],
                                "turn_id": turn["turn_id"],
                                "contract_code": exc.code if isinstance(exc, P3ContractError) else "p3_b46_product_turn_failure_no_retry",
                                "error_type": type(exc).__name__, "error_sha256": canonical_sha256(str(exc)),
                                "retry_authorized": False,
                            }))
                        raise
                    finally:
                        brain_module.OpenAI = original_openai
                        brain_module.urllib.request.urlopen = original_urlopen
                product_rows.append(product_row)
                direct_result = run_condition(
                    condition="full_history_direct", view=direct_view,
                    design=design, transport=direct_transport,
                    checkpoint_root=root / "direct_provider_calls",
                    item_id=f"{case['case_id']}:{turn['turn_id']}:full_history_direct",
                    token_counter=direct_counter, backend="openai_compatible_local",
                )
                direct_result.update({
                    "turn_id": turn["turn_id"], "session_id": turn["session_id"],
                    "view_sha256": direct_view["view_sha256"],
                    "surface_contract": strict_japanese_visible_surface_contract(direct_result["final"]["content"]),
                })
                direct_rows.append(direct_result)
                view_engine.append_product_prefix(prefix, turn, str(product_row["visible_reply"] or ""))
        finally:
            brain_module.OpenAI = original_openai
            brain_module.urllib.request.urlopen = original_urlopen
        production_db_unreachable = (
            Path(brain_module.DB_PATH).resolve() == paths["memory"].resolve()
            and Path(brain_module.DB_PATH).resolve() != worker.PRODUCTION_DB_PATH
        )
    surfaces = [row["surface_contract"] for row in product_rows + direct_rows]
    checks = {
        "eight_nonempty_outputs": len(product_rows) == len(direct_rows) == 4
        and all(str(row["visible_reply"] or "").strip() for row in product_rows)
        and all(str(row["final"]["content"] or "").strip() for row in direct_rows),
        "eight_quotation_aware_japanese_surfaces": len(surfaces) == 8
        and all(all(surface.values()) for surface in surfaces),
        "four_paired_views_match": all(
            product_rows[index]["source_history_sha256"] == direct_rows[index]["source_history_sha256"]
            and product_rows[index]["input_sha256"] == direct_rows[index]["input_sha256"]
            for index in range(4)
        ),
        "session_boundary_and_memory_path_preserved": product_rows[2]["session_restart_before_turn"] is True
        and len({row["memory_path_sha256"] for row in product_rows}) == 1
        and len(session_instance_ids) == 2,
        "production_database_unreachable": production_db_unreachable,
        "localhost_only": all(row["loopback_allowed"] is True for row in network_attempts),
        "zero_annotation_access": True,
    }
    product_calls = [call for row in product_rows for call in row["calls"]]
    direct_calls = [call for row in direct_rows for call in row["calls"]]
    return {
        "schema": "uruha_p3_b46_prospective_v3_case_output_lock_v1",
        "phase": "P3-B46", "status": "case_outputs_locked" if all(checks.values()) else "case_output_lock_failed_retained",
        "case_id": case["case_id"], "case_index": case_index,
        "run_commitment_sha256": commitment["record_sha256"],
        "product_turns": product_rows, "direct_turns": direct_rows,
        "checks": checks, "network_attempts": network_attempts,
        "provider_call_evidence": sum(row["real_model_calls"] for row in product_calls + direct_calls),
        "network_call_evidence": sum(row["network_calls"] for row in product_calls + direct_calls),
        "actual_prompt_tokens": sum(row["usage"]["prompt_tokens"] for row in product_calls + direct_calls),
        "actual_completion_tokens": sum(row["usage"]["completion_tokens"] for row in product_calls + direct_calls),
        "total_wall_seconds": round(time.monotonic() - started, 6),
        "annotations_accessed": 0, "production_database_accessed": False,
        "claim_boundary": "One developer case output lock only; no rubric access, grade, preference or advantage conclusion.",
    }


def _workspace_path(release: Mapping[str, Any]) -> Path:
    basename = release["authorization"]["workspace_root_basename"]
    if basename != "uruha-p3-b46-prospective-v3-workspace-v1":
        raise P3ContractError("p3_b46_workspace_name_invalid")
    root = (Path(tempfile.gettempdir()) / basename).resolve()
    if root.parent != Path(tempfile.gettempdir()).resolve() or root.is_symlink():
        raise P3ContractError("p3_b46_workspace_path_invalid")
    return root


def _safe_remove_workspace(path: Path) -> None:
    expected = (Path(tempfile.gettempdir()) / "uruha-p3-b46-prospective-v3-workspace-v1").resolve()
    sentinel = path / ".p3_ephemeral_workspace.json"
    if path.resolve() != expected or path.is_symlink() or not sentinel.is_file():
        raise P3ContractError("p3_b46_workspace_cleanup_refused")
    sentinel_value = _read(sentinel)
    _verify_signed(sentinel_value, "p3_b46_workspace_sentinel_drift")
    if sentinel_value.get("schema") != worker.WORKSPACE_SCHEMA:
        raise P3ContractError("p3_b46_workspace_sentinel_drift")
    shutil.rmtree(path)


def aggregate_result(
    config: Mapping[str, Any], release_path: str | Path, commitment: Mapping[str, Any],
    cases: list[Mapping[str, Any]], workspace_removed: bool,
) -> dict[str, Any]:
    product_rows = [row for case in cases for row in case["product_turns"]]
    direct_rows = [row for case in cases for row in case["direct_turns"]]
    all_calls = [call for row in product_rows for call in row["calls"]] + [
        call for row in direct_rows for call in row["calls"]
    ]
    checks = {
        "three_cases_locked": len(cases) == 3 and all(case["status"] == "case_outputs_locked" for case in cases),
        "twenty_four_nonempty_outputs": len(product_rows) == len(direct_rows) == 12
        and all(str(row["visible_reply"] or "").strip() for row in product_rows)
        and all(str(row["final"]["content"] or "").strip() for row in direct_rows),
        "twenty_four_surfaces_pass": all(
            all(row["surface_contract"].values()) for row in product_rows + direct_rows
        ),
        "twelve_paired_views_match": all(
            product_rows[index]["source_history_sha256"] == direct_rows[index]["source_history_sha256"]
            and product_rows[index]["input_sha256"] == direct_rows[index]["input_sha256"]
            for index in range(12)
        ),
        "provider_call_count_within_release": 12 <= len(all_calls) <= 60,
        "direct_calls_exactly_twelve": sum(len(row["calls"]) for row in direct_rows) == 12,
        "all_cases_isolated_and_local": all(
            case["checks"]["production_database_unreachable"] and case["checks"]["localhost_only"]
            for case in cases
        ),
        "workspace_removed_after_complete": workspace_removed,
        "zero_annotation_confirmation_or_production_access": True,
    }
    return {
        "schema": RESULT_SCHEMA, "phase": "P3-B46",
        "status": "prospective_v3_outputs_locked" if all(checks.values()) else "prospective_v3_output_lock_failed_retained",
        "run_commitment_sha256": commitment["record_sha256"],
        "config_sha256": config["_config_sha256"], "release_sha256": _sha(release_path),
        "case_ids": [case["case_id"] for case in cases], "cases": cases,
        "checks": checks,
        "provider_call_evidence": sum(call["real_model_calls"] for call in all_calls),
        "network_call_evidence": sum(call["network_calls"] for call in all_calls),
        "actual_prompt_tokens": sum(call["usage"]["prompt_tokens"] for call in all_calls),
        "actual_completion_tokens": sum(call["usage"]["completion_tokens"] for call in all_calls),
        "total_wall_seconds": round(sum(float(case["total_wall_seconds"]) for case in cases), 6),
        "real_model_calls": sum(call["real_model_calls"] for call in all_calls),
        "network_calls": sum(call["network_calls"] for call in all_calls), "paid_calls": 0,
        "annotations_accessed": 0, "confirmation_accessed": 0,
        "production_database_accessed": False, "ephemeral_workspace_removed": workspace_removed,
        "formal_holdout": False, "quality_result": "not_yet_scored_against_predeclared_rubric",
        "claim_boundary": "Prospective developer outputs locked before rubric access. This is generation evidence, not a grade, human preference result or general product advantage.",
    }


def run_batch(
    config_path: str | Path, release_path: str | Path, checkpoint_root: str | Path
) -> dict[str, Any]:
    config = execution_contract.load_config(config_path)
    release = validate_release(release_path, config)
    repo = Path(__file__).resolve().parent
    root = Path(checkpoint_root).resolve()
    expected_root = (repo / release["authorization"]["checkpoint_root"]).resolve()
    if root != expected_root:
        raise P3ContractError("p3_b46_checkpoint_root_mismatch")
    schedule = execution_contract.build_schedule(config)
    root.mkdir(parents=True, exist_ok=True)
    commitment = build_run_commitment(config, release_path, schedule)
    _write_or_validate(root / "run_commitment.json", commitment, "p3_b46_run_commitment_drift")
    workspace = _workspace_path(release)
    cases: list[dict[str, Any]] = []
    for case_index, case in enumerate(config["_source"]["cases"]):
        output = _case_result_path(root, case["case_id"])
        if output.exists():
            value = _read(output)
            if value.get("status") != "case_outputs_locked" or value.get("case_id") != case["case_id"]:
                raise P3ContractError("p3_b46_existing_case_result_terminal", case["case_id"])
            cases.append(value)
            continue
        command = [
            sys.executable, str(Path(__file__).resolve()), "--mode", "case-worker",
            "--config", str(Path(config_path).resolve()), "--release", str(Path(release_path).resolve()),
            "--checkpoint-root", str(root), "--workspace-root", str(workspace),
            "--case-index", str(case_index), "--output", str(output),
        ]
        completed = subprocess.run(command, cwd=repo, capture_output=True, text=True, check=False)
        if completed.returncode != 0:
            raise P3ContractError("p3_b46_case_worker_failed_no_retry", f"{case['case_id']}:{completed.returncode}")
        value = _read(output)
        if value.get("status") != "case_outputs_locked":
            raise P3ContractError("p3_b46_case_worker_result_failed", case["case_id"])
        cases.append(value)
    if workspace.exists():
        _safe_remove_workspace(workspace)
    return aggregate_result(config, release_path, commitment, cases, not workspace.exists())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode", choices=("preflight", "release-check", "case-worker", "run"), required=True
    )
    parser.add_argument("--config", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--release")
    parser.add_argument("--checkpoint-root")
    parser.add_argument("--workspace-root")
    parser.add_argument("--case-index", type=int)
    args = parser.parse_args()
    output = Path(args.output)
    if output.exists():
        return 2
    try:
        if args.mode == "preflight":
            payload = build_preflight(args.config)
        elif args.mode == "release-check":
            if args.release is None:
                raise P3ContractError("p3_b46_release_check_args_missing")
            config = execution_contract.load_config(args.config)
            release = validate_release(args.release, config)
            payload = {
                "schema": "uruha_p3_b46_release_check_v1",
                "phase": "P3-B46", "status": "real_adapter_release_valid",
                "release_sha256": _sha(args.release),
                "run_id": release["authorization"]["run_id"],
                "real_model_calls": 0, "network_calls": 0,
                "annotations_accessed": 0,
                "claim_boundary": "Release validation only; no generation or quality result.",
            }
        elif args.mode == "case-worker":
            if args.release is None or args.checkpoint_root is None or args.workspace_root is None or args.case_index is None:
                raise P3ContractError("p3_b46_case_worker_args_missing")
            payload = run_case_worker(
                args.config, args.release, args.checkpoint_root, args.workspace_root, args.case_index
            )
        else:
            if args.release is None or args.checkpoint_root is None:
                raise P3ContractError("p3_b46_run_args_missing")
            release = _read(args.release)
            repo = Path(__file__).resolve().parent
            if output.resolve() != (repo / release["authorization"]["result_path"]).resolve():
                raise P3ContractError("p3_b46_result_path_mismatch")
            payload = run_batch(args.config, args.release, args.checkpoint_root)
    except P3ContractError as exc:
        payload = {
            "schema": "uruha_p3_b46_prospective_v3_output_lock_failure_v1",
            "phase": "P3-B46", "status": "failed_retained_no_retry",
            "contract_code": exc.code, "error_detail_sha256": canonical_sha256(exc.detail),
            "automatic_retry": False, "annotations_accessed": 0,
            "claim_boundary": "Failure retained; no quality, preference or advantage claim is authorized.",
        }
    except Exception as exc:
        payload = {
            "schema": "uruha_p3_b46_prospective_v3_output_lock_failure_v1",
            "phase": "P3-B46", "status": "failed_retained_no_retry",
            "contract_code": "p3_b46_unexpected_execution_failure_no_retry",
            "error_type": type(exc).__name__, "error_detail_sha256": canonical_sha256(str(exc)),
            "automatic_retry": False, "annotations_accessed": 0,
            "claim_boundary": "Unexpected failure retained; no quality, preference or advantage claim is authorized.",
        }
    write_new_json(output, payload)
    return 0 if payload.get("status") in {
        "ready_for_real_adapter_release_review", "real_adapter_release_valid",
        "case_outputs_locked", "prospective_v3_outputs_locked",
    } else 1


if __name__ == "__main__":
    raise SystemExit(main())
