#!/usr/bin/env python3
"""P3-B45 immutable, crash-safe execution contract for prospective v3.

This module deliberately does not import or open the v3 annotation file.  It
validates the committed annotation digest through the B44 freeze, builds the
source-only execution schedule, and rehearses no-retry checkpoint mechanics
with a fake transport.  Real generation requires a later release artifact.
"""

from __future__ import annotations

import argparse
import ast
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
from typing import Any, Callable, Mapping

from p3_product_comparison import P3ContractError, canonical_sha256, write_new_json


SCHEMA = "uruha_p3_prospective_v3_execution_contract_v1"
CONFIG_PATH = Path("configs/p3_prospective_v3_execution_contract_v1.json")
PRODUCT_COMMIT = "0cab07b44aa47adb3866a9ba1aa317b71a5d3091"
SOURCE_SHA256 = "8980e85d321d3f3e1997a31be184a47bc4390428f85c92f4a8ef12f266ae011d"
RUBRIC_SHA256 = "c72c648b39a7b149bb75640fea76f1635b248cb6249eb8015d11f9df29e9603f"
MODEL_DIGEST = "2bada8a7450677000f678be90653b85d364de7db25eb5ea54136ada5f3933730"
CASE_IDS = [
    "p3-prospective-v3-growing-comments-zh",
    "p3-prospective-v3-concert-excitement-en",
    "p3-prospective-v3-team-pending-ja",
]
CONDITIONS = ["product_system", "full_history_direct"]


def _read(path: str | Path) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise P3ContractError("p3_b45_invalid_json", str(path)) from exc
    if not isinstance(value, dict):
        raise P3ContractError("p3_b45_invalid_json", str(path))
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


def _ref(repo: Path, value: Any, expected: Mapping[str, Any], code: str) -> Path:
    if value != dict(expected):
        raise P3ContractError(code)
    path = (repo / str(expected["path"])).resolve()
    try:
        path.relative_to(repo)
    except ValueError as exc:
        raise P3ContractError(code) from exc
    if not path.is_file() or _sha(path) != expected["sha256"]:
        raise P3ContractError(code)
    return path


def _git(repo: Path, *args: str) -> bytes:
    try:
        completed = subprocess.run(
            ["git", *args], cwd=repo, check=False, capture_output=True,
        )
    except OSError as exc:
        raise P3ContractError("p3_b45_git_unavailable") from exc
    if completed.returncode != 0:
        raise P3ContractError("p3_b45_git_snapshot_unavailable", completed.stderr.decode("utf-8", "replace"))
    return completed.stdout


def _current_file_bytes(repo: Path, relative: str) -> bytes:
    path = (repo / relative).resolve()
    try:
        path.relative_to(repo)
    except ValueError as exc:
        raise P3ContractError("p3_b45_product_path_escape", relative) from exc
    try:
        return path.read_bytes()
    except OSError as exc:
        raise P3ContractError("p3_b45_product_file_missing", relative) from exc


def validate_product_snapshot(
    repo: Path, commit: str, entrypoints: list[str]
) -> dict[str, Any]:
    """Compare the reachable local-Python product closure with one Git commit."""

    if commit != PRODUCT_COMMIT or entrypoints != ["uruha_web_ui_product.py"]:
        raise P3ContractError("p3_b45_product_snapshot_binding_drift")
    _git(repo, "cat-file", "-e", f"{commit}^{{commit}}")
    tracked = _git(repo, "ls-tree", "-r", "--name-only", commit).decode("utf-8").splitlines()
    root_python = {
        Path(relative).stem: relative
        for relative in tracked
        if relative.endswith(".py") and "/" not in relative
    }
    queue = [Path(relative).stem for relative in entrypoints]
    seen: set[str] = set()
    rows: list[dict[str, str]] = []
    while queue:
        module = queue.pop(0)
        if module in seen or module not in root_python:
            continue
        seen.add(module)
        relative = root_python[module]
        frozen = _git(repo, "show", f"{commit}:{relative}")
        current = _current_file_bytes(repo, relative)
        frozen_sha = hashlib.sha256(frozen).hexdigest()
        if hashlib.sha256(current).hexdigest() != frozen_sha:
            raise P3ContractError("p3_b45_product_snapshot_file_drift", relative)
        rows.append({"path": relative, "sha256": frozen_sha})
        try:
            tree = ast.parse(frozen.decode("utf-8"), filename=relative)
        except (SyntaxError, UnicodeDecodeError) as exc:
            raise P3ContractError("p3_b45_product_snapshot_parse_failure", relative) from exc
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        queue.extend(sorted(imported.intersection(root_python).difference(seen)))
    rows.sort(key=lambda row: row["path"])
    if not rows or rows[0]["path"] == "":
        raise P3ContractError("p3_b45_product_snapshot_empty")
    return {
        "commit": commit,
        "entrypoints": list(entrypoints),
        "reachable_root_python_files": len(rows),
        "manifest_sha256": canonical_sha256(rows),
        "files": rows,
    }


def _expected_generation(design: Mapping[str, Any]) -> dict[str, Any]:
    model = design["model"]
    budget = design["budget"]
    turn = budget["per_condition_turn"]
    return {
        "model": model["generation_model"],
        "digest": MODEL_DIGEST,
        "temperature": model["temperature"],
        "seed": model["seed"],
        "top_p": model["top_p"],
        "num_ctx": model["num_ctx"],
        "think": model["think"],
        "aggregate_prompt_tokens_max_per_condition_turn": turn["aggregate_prompt_tokens_max"],
        "aggregate_completion_tokens_max_per_condition_turn": turn["aggregate_completion_tokens_max"],
        "product_calls_max_per_turn": budget["system_calls_max"],
        "direct_calls_exact_per_turn": budget["direct_calls_max"],
        "wall_seconds_max_per_condition_turn": turn["wall_seconds_max"],
    }


def load_config(path: str | Path) -> dict[str, Any]:
    config_path = Path(path).resolve()
    raw = _read(config_path)
    expected_keys = {
        "schema", "phase", "status", "purpose", "frozen_dependencies",
        "frozen_input_commitments", "selection", "common_history",
        "session_boundary", "generation", "checkpoint_contract",
        "execution_boundary", "retention", "success", "claim_boundary",
    }
    if set(raw) != expected_keys or raw.get("schema") != SCHEMA or raw.get("phase") != "P3-B45":
        raise P3ContractError("p3_b45_schema_mismatch")
    if raw.get("status") != "preregistered_not_executed" or raw.get("purpose") != (
        "freeze_crash_safe_no_retry_dual_condition_execution_before_v3_generation"
    ):
        raise P3ContractError("p3_b45_status_mismatch")
    repo = Path(__file__).resolve().parent
    dependencies = raw.get("frozen_dependencies") or {}
    if set(dependencies) != {"data_and_rubric_freeze", "comparison_design", "direct_v2_review", "strict_surface"}:
        raise P3ContractError("p3_b45_dependencies_mismatch")
    freeze_path = _ref(repo, dependencies["data_and_rubric_freeze"], {
        "path": "research/p3_b44_prospective_v3_data_and_rubric_freeze_2026-09-17.json",
        "sha256": "7f1f10ae17e2284390d190a559657bf3670037d9430fac136440787c59be9e62",
        "required_status": "prospective_v3_data_and_rubric_frozen",
    }, "p3_b45_freeze_mismatch")
    design_path = _ref(repo, dependencies["comparison_design"], {
        "path": "configs/p3_product_comparison_v1.json",
        "sha256": "1e6d3b0600740b3dee7207ffc5c4f9cc9247a5feba2b967bdab4586522f7b836",
    }, "p3_b45_design_mismatch")
    review_path = _ref(repo, dependencies["direct_v2_review"], {
        "path": "configs/p3_direct_baseline_v2_design_review_v1.json",
        "sha256": "2d0a17759e4daa4f7fd9cc2533cda3d285d5c04bf88c8f7428dc96e194aeed53",
    }, "p3_b45_review_mismatch")
    _ref(repo, dependencies["strict_surface"], {
        "path": "p3_strict_visible_surface_v2.py",
        "sha256": "60dfba159b1f7671c0f18e1f0e76a429bd6821dc48a2a625e860d493a479dd56",
    }, "p3_b45_surface_mismatch")
    freeze = _read(freeze_path)
    if freeze.get("status") != "prospective_v3_data_and_rubric_frozen":
        raise P3ContractError("p3_b45_freeze_status_invalid")
    commitments = raw.get("frozen_input_commitments")
    expected_commitments = {
        "source_sha256": SOURCE_SHA256,
        "rubric_sha256_commitment_only": RUBRIC_SHA256,
        "rubric_file_access_during_generation": False,
        "product_snapshot_commit": PRODUCT_COMMIT,
        "product_entrypoints": ["uruha_web_ui_product.py"],
        "product_snapshot_verification": "recursive_root_local_python_import_closure_matches_git_commit",
        "post_source_product_tuning_before_first_run": False,
    }
    if commitments != expected_commitments:
        raise P3ContractError("p3_b45_input_commitment_drift")
    artifacts = freeze.get("artifacts") or {}
    source_ref = artifacts.get("source") or {}
    annotation_ref = artifacts.get("annotations") or {}
    if source_ref.get("sha256") != SOURCE_SHA256 or annotation_ref.get("sha256") != RUBRIC_SHA256:
        raise P3ContractError("p3_b45_freeze_commitment_drift")
    source_path = (repo / str(source_ref.get("path"))).resolve()
    if not source_path.is_file() or _sha(source_path) != SOURCE_SHA256:
        raise P3ContractError("p3_b45_source_drift")
    source = _read(source_path)
    cases = source.get("cases")
    if (
        not isinstance(cases, list) or len(cases) != 3
        or [case.get("case_id") for case in cases] != CASE_IDS
        or any(len(case.get("turns") or []) != 4 for case in cases)
    ):
        raise P3ContractError("p3_b45_source_shape_drift")
    selection = raw.get("selection")
    if selection != {
        "case_order": CASE_IDS,
        "turn_order": "immutable_source_order_within_case",
        "condition_order_per_turn": CONDITIONS,
        "schedule_order": "case_then_turn_then_condition",
        "quality_based_selection": False,
    }:
        raise P3ContractError("p3_b45_selection_drift")
    design = _read(design_path)
    review = _read(review_path)
    if raw.get("generation") != _expected_generation(design):
        raise P3ContractError("p3_b45_generation_drift")
    if raw.get("common_history") != {
        "mode": "system_anchored_prefix_paired", "include_all_prior_sessions": True,
        "include_roles": True, "include_only_past_visible_messages": True,
        "baseline_output_written_back": False, "current_product_reply_visible_to_baseline": False,
        "product_visible_reply_added_after_both_current_views_freeze": True,
        "cross_case_state_shared": False, "truncate_or_summarize": False,
    }:
        raise P3ContractError("p3_b45_history_drift")
    if raw.get("session_boundary") != {
        "restart_product_at_each_case_third_turn": True,
        "same_case_memory_path_retained": True, "new_brain_instance": True,
        "cross_case_workspace_reuse": False,
    }:
        raise P3ContractError("p3_b45_session_drift")
    if raw.get("checkpoint_contract") != {
        "logical_steps_exact": 24,
        "provider_call_intent_before_every_transport": True,
        "complete_checkpoint_combines_output_hash_usage_and_transport_evidence": True,
        "complete_checkpoint_reuse_allowed": True,
        "model_recall_for_complete_checkpoint": False,
        "intent_without_complete_is_terminal": True,
        "failure_record_is_terminal": True,
        "checkpoint_or_manifest_drift_is_terminal": True,
        "out_of_order_execution_allowed": False,
        "automatic_retry_count": 0, "fallback_count": 0, "concurrency": 1,
    }:
        raise P3ContractError("p3_b45_checkpoint_contract_drift")
    if raw.get("execution_boundary") != {
        "source_cases_exact": 3, "source_turns_exact": 12, "visible_outputs_exact": 24,
        "product_provider_calls_min": 0, "product_provider_calls_max": 48,
        "direct_provider_calls_exact": 12, "total_provider_calls_max": 60,
        "localhost_only": True, "annotation_access": False, "confirmation_access": False,
        "production_database_access": False, "external_deployment": False,
        "remote_paid_calls": False, "real_model_calls_authorized_by_this_config": False,
        "separate_release_required": True,
    }:
        raise P3ContractError("p3_b45_execution_boundary_drift")
    if raw.get("retention") != {
        "visible_replies": True, "product_runtime_trace": True,
        "product_memory_snapshot": True, "per_provider_call_intent_usage_and_hashes": True,
        "raw_provider_payload": False, "partial_failure_evidence": True,
        "ephemeral_workspace_removed": True,
    }:
        raise P3ContractError("p3_b45_retention_drift")
    if raw.get("success") != {
        "all_twenty_four_visible_outputs_nonempty": True,
        "all_twenty_four_quotation_aware_japanese_surface_pass": True,
        "all_twelve_view_pairs_share_source_and_prefix": True,
        "all_actual_provider_and_network_calls_accounted_once": True,
        "all_condition_turn_budgets_valid": True,
        "all_session_restarts_preserve_only_same_case_paths": True,
        "all_product_state_isolated_and_workspaces_removed": True,
        "zero_annotation_confirmation_or_production_access": True,
    }:
        raise P3ContractError("p3_b45_success_drift")
    product_manifest = validate_product_snapshot(
        repo, commitments["product_snapshot_commit"], commitments["product_entrypoints"]
    )
    loaded = deepcopy(raw)
    loaded.update({
        "_repo": repo, "_config_path": config_path, "_config_sha256": _sha(config_path),
        "_source": source, "_source_path": source_path, "_freeze": freeze,
        "_design": design, "_direct_instruction": review["direct_baseline"]["instruction"],
        "_product_manifest": product_manifest,
    })
    return loaded


def build_schedule(config: Mapping[str, Any]) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    index = 0
    for case in config["_source"]["cases"]:
        turns = case["turns"]
        for turn_index, turn in enumerate(turns):
            visible = [row["turn_id"] for row in turns[: turn_index + 1]]
            locked = [row["turn_id"] for row in turns[turn_index + 1 :]]
            for condition in CONDITIONS:
                steps.append({
                    "step_index": index,
                    "case_id": case["case_id"],
                    "turn_id": turn["turn_id"],
                    "session_id": turn["session_id"],
                    "condition": condition,
                    "input_sha256": turn["content_sha256"],
                    "visible_source_turn_ids": visible,
                    "locked_future_turn_ids": locked,
                    "restart_product_before_step": (
                        condition == "product_system" and turn_index == 2
                    ),
                })
                index += 1
    payload = {
        "schema": "uruha_p3_prospective_v3_execution_schedule_v1",
        "config_sha256": config["_config_sha256"],
        "source_sha256": SOURCE_SHA256,
        "product_snapshot_commit": PRODUCT_COMMIT,
        "product_manifest_sha256": config["_product_manifest"]["manifest_sha256"],
        "steps": steps,
    }
    payload["schedule_sha256"] = canonical_sha256(payload)
    return payload


def build_mechanical_call_plan(schedule: Mapping[str, Any]) -> list[dict[str, Any]]:
    """One fake call per logical step, solely to exercise the journal state machine."""

    rows = []
    for step in schedule["steps"]:
        request = {
            "logical_step_index": step["step_index"],
            "case_id": step["case_id"], "turn_id": step["turn_id"],
            "condition": step["condition"], "stage": "mechanical_rehearsal",
            "model": "qwen2.5:7b", "backend": "fake_local_no_network",
        }
        rows.append({
            "call_index": step["step_index"],
            "call_id": f"mechanical-{step['step_index']:02d}",
            "request": request,
            "request_sha256": canonical_sha256(request),
        })
    return rows


def _terminal(root: Path, code: str, call: Mapping[str, Any]) -> None:
    path = root / "terminal_failure.json"
    value = _signed({
        "schema": "uruha_p3_b45_terminal_no_retry_failure_v1",
        "contract_code": code, "call_index": call["call_index"],
        "call_id": call["call_id"], "request_sha256": call["request_sha256"],
        "retry_authorized": False, "fallback_authorized": False,
    })
    if path.exists():
        existing = _read(path)
        _verify_signed(existing, "p3_b45_terminal_record_drift")
        if existing != value:
            raise P3ContractError("p3_b45_terminal_record_drift")
    else:
        write_new_json(path, value)


def _global_terminal(root: Path, code: str) -> None:
    path = root / "terminal_failure.json"
    value = _signed({
        "schema": "uruha_p3_b45_terminal_no_retry_failure_v1",
        "contract_code": code, "call_index": None, "call_id": None,
        "request_sha256": None, "retry_authorized": False,
        "fallback_authorized": False,
    })
    if path.exists():
        existing = _read(path)
        _verify_signed(existing, "p3_b45_terminal_record_drift")
        if existing != value:
            raise P3ContractError("p3_b45_terminal_record_drift")
    else:
        write_new_json(path, value)


def validate_checkpoint_topology(
    root: Path, plan: list[dict[str, Any]], run_commitment: Mapping[str, Any]
) -> None:
    calls_root = root / "calls"
    if not calls_root.exists():
        return
    expected_names = {f"{call['call_index']:04d}" for call in plan}
    observed_names = {path.name for path in calls_root.iterdir()}
    if not observed_names.issubset(expected_names) or any(
        not path.is_dir() for path in calls_root.iterdir()
    ):
        _global_terminal(root, "p3_b45_unexpected_checkpoint_artifact")
        raise P3ContractError("p3_b45_unexpected_checkpoint_artifact")
    incomplete_seen = False
    for call in plan:
        folder = calls_root / f"{call['call_index']:04d}"
        if not folder.exists():
            incomplete_seen = True
            continue
        names = {path.name for path in folder.iterdir()}
        if not names.issubset({"intent.json", "complete.json", "failure.json"}):
            _global_terminal(root, "p3_b45_unexpected_checkpoint_artifact")
            raise P3ContractError("p3_b45_unexpected_checkpoint_artifact")
        if incomplete_seen:
            _global_terminal(root, "p3_b45_out_of_order_checkpoint")
            raise P3ContractError("p3_b45_out_of_order_checkpoint")
        intent_path, complete_path, failure_path = (
            folder / "intent.json", folder / "complete.json", folder / "failure.json"
        )
        if failure_path.exists():
            failure = _read(failure_path)
            try:
                _verify_signed(failure, "p3_b45_failure_record_drift")
            except P3ContractError:
                _global_terminal(root, "p3_b45_failure_record_drift")
                raise
            incomplete_seen = True
            continue
        if complete_path.exists():
            complete = _read(complete_path)
            try:
                _verify_signed(complete, "p3_b45_complete_record_drift")
            except P3ContractError:
                _global_terminal(root, "p3_b45_complete_record_drift")
                raise
            if (
                complete.get("run_commitment_sha256") != run_commitment["record_sha256"]
                or complete.get("request_sha256") != call["request_sha256"]
            ):
                _global_terminal(root, "p3_b45_complete_checkpoint_drift")
                raise P3ContractError("p3_b45_complete_checkpoint_drift")
            continue
        if intent_path.exists():
            intent = _read(intent_path)
            try:
                _verify_signed(intent, "p3_b45_intent_record_drift")
            except P3ContractError:
                _global_terminal(root, "p3_b45_intent_record_drift")
                raise
            if (
                intent.get("run_commitment_sha256") != run_commitment["record_sha256"]
                or intent.get("request_sha256") != call["request_sha256"]
            ):
                _global_terminal(root, "p3_b45_intent_checkpoint_drift")
                raise P3ContractError("p3_b45_intent_checkpoint_drift")
            incomplete_seen = True
            continue
        _global_terminal(root, "p3_b45_empty_checkpoint_directory")
        raise P3ContractError("p3_b45_empty_checkpoint_directory")


def execute_provider_call_once(
    *, root: Path, run_commitment: Mapping[str, Any], call: Mapping[str, Any],
    transport: Callable[[Mapping[str, Any]], Mapping[str, Any]],
    after_intent_hook: Callable[[int], None] | None = None,
    after_complete_hook: Callable[[int], None] | None = None,
) -> dict[str, Any]:
    """Execute or reuse one provider call; an intent-only state is terminal."""

    call_index = call["call_index"]
    folder = root / "calls" / f"{call_index:04d}"
    intent_path, complete_path, failure_path = (
        folder / "intent.json", folder / "complete.json", folder / "failure.json"
    )
    if failure_path.exists():
        failure = _read(failure_path)
        try:
            _verify_signed(failure, "p3_b45_failure_record_drift")
        except P3ContractError:
            _terminal(root, "p3_b45_failure_record_drift", call)
            raise
        _terminal(root, failure["contract_code"], call)
        raise P3ContractError("p3_b45_terminal_failure_no_retry", call["call_id"])
    if complete_path.exists():
        complete = _read(complete_path)
        try:
            _verify_signed(complete, "p3_b45_complete_record_drift")
        except P3ContractError:
            _terminal(root, "p3_b45_complete_record_drift", call)
            raise
        result = complete.get("result")
        if (
            complete.get("run_commitment_sha256") != run_commitment["record_sha256"]
            or complete.get("request_sha256") != call["request_sha256"]
            or not isinstance(result, Mapping)
            or result.get("content_sha256") != canonical_sha256(result.get("content"))
        ):
            _terminal(root, "p3_b45_complete_checkpoint_drift", call)
            raise P3ContractError("p3_b45_complete_checkpoint_drift", call["call_id"])
        return {"reused": True, **dict(result)}
    if intent_path.exists():
        intent = _read(intent_path)
        try:
            _verify_signed(intent, "p3_b45_intent_record_drift")
        except P3ContractError:
            _terminal(root, "p3_b45_intent_record_drift", call)
            raise
        if (
            intent.get("run_commitment_sha256") != run_commitment["record_sha256"]
            or intent.get("request_sha256") != call["request_sha256"]
        ):
            _terminal(root, "p3_b45_intent_checkpoint_drift", call)
            raise P3ContractError("p3_b45_intent_checkpoint_drift", call["call_id"])
        _terminal(root, "p3_b45_intent_without_complete_no_retry", call)
        raise P3ContractError("p3_b45_intent_without_complete_no_retry", call["call_id"])
    intent = _signed({
        "schema": "uruha_p3_b45_provider_invocation_intent_v1",
        "run_commitment_sha256": run_commitment["record_sha256"],
        "call_index": call_index, "call_id": call["call_id"],
        "request_sha256": call["request_sha256"],
        "transport_attempt_authorized": 1, "retry_count": 0, "fallback_count": 0,
    })
    write_new_json(intent_path, intent)
    if after_intent_hook is not None:
        after_intent_hook(call_index)
    try:
        response = transport(call["request"])
    except Exception as exc:
        failure = _signed({
            "schema": "uruha_p3_b45_provider_failure_v1",
            "run_commitment_sha256": run_commitment["record_sha256"],
            "call_index": call_index, "call_id": call["call_id"],
            "request_sha256": call["request_sha256"],
            "contract_code": "p3_b45_transport_failure_no_retry",
            "error_type": type(exc).__name__,
            "error_sha256": canonical_sha256(str(exc)),
            "transport_attempted": True, "response_received": False,
        })
        write_new_json(failure_path, failure)
        _terminal(root, "p3_b45_transport_failure_no_retry", call)
        raise P3ContractError("p3_b45_transport_failure_no_retry", type(exc).__name__) from exc
    if not isinstance(response, Mapping):
        _terminal(root, "p3_b45_invalid_transport_response", call)
        raise P3ContractError("p3_b45_invalid_transport_response")
    usage = response.get("usage")
    content = response.get("content")
    if (
        not isinstance(content, str) or not content
        or not isinstance(usage, Mapping)
        or response.get("model") != "qwen2.5:7b"
        or response.get("backend") != "fake_local_no_network"
        or response.get("real_model_calls") != 0
        or response.get("network_calls") != 0
    ):
        _terminal(root, "p3_b45_invalid_transport_response", call)
        raise P3ContractError("p3_b45_invalid_transport_response")
    result = {
        "content": content, "content_sha256": canonical_sha256(content),
        "usage": dict(usage), "model": response["model"], "backend": response["backend"],
        "real_model_calls": 0, "network_calls": 0,
    }
    complete = _signed({
        "schema": "uruha_p3_b45_provider_complete_v1",
        "run_commitment_sha256": run_commitment["record_sha256"],
        "call_index": call_index, "call_id": call["call_id"],
        "request_sha256": call["request_sha256"], "result": result,
    })
    write_new_json(complete_path, complete)
    if after_complete_hook is not None:
        after_complete_hook(call_index)
    return {"reused": False, **result}


def run_mechanical_rehearsal(
    config_path: str | Path, checkpoint_root: str | Path,
    transport: Callable[[Mapping[str, Any]], Mapping[str, Any]],
    *, after_intent_hook: Callable[[int], None] | None = None,
    after_complete_hook: Callable[[int], None] | None = None,
) -> dict[str, Any]:
    config = load_config(config_path)
    schedule = build_schedule(config)
    plan = build_mechanical_call_plan(schedule)
    root = Path(checkpoint_root)
    root.mkdir(parents=True, exist_ok=True)
    run_commitment = _signed({
        "schema": "uruha_p3_b45_mechanical_run_commitment_v1",
        "config_sha256": config["_config_sha256"],
        "source_sha256": SOURCE_SHA256,
        "rubric_sha256_commitment_only": RUBRIC_SHA256,
        "product_snapshot_commit": PRODUCT_COMMIT,
        "product_manifest_sha256": config["_product_manifest"]["manifest_sha256"],
        "schedule_sha256": schedule["schedule_sha256"],
        "call_plan_sha256": canonical_sha256(plan),
        "real_generation_authorized": False,
    })
    commitment_path = root / "run_commitment.json"
    if commitment_path.exists():
        existing = _read(commitment_path)
        try:
            _verify_signed(existing, "p3_b45_run_commitment_drift")
        except P3ContractError:
            _global_terminal(root, "p3_b45_run_commitment_drift")
            raise
        if existing != run_commitment:
            _global_terminal(root, "p3_b45_run_commitment_drift")
            raise P3ContractError("p3_b45_run_commitment_drift")
    else:
        write_new_json(commitment_path, run_commitment)
    terminal_path = root / "terminal_failure.json"
    if terminal_path.exists():
        terminal = _read(terminal_path)
        _verify_signed(terminal, "p3_b45_terminal_record_drift")
        raise P3ContractError("p3_b45_terminal_failure_no_retry", str(terminal.get("contract_code")))
    validate_checkpoint_topology(root, plan, run_commitment)
    reused = 0
    completed = 0
    for call in plan:
        row = execute_provider_call_once(
            root=root, run_commitment=run_commitment, call=call, transport=transport,
            after_intent_hook=after_intent_hook, after_complete_hook=after_complete_hook,
        )
        reused += int(row["reused"])
        completed += 1
    return {
        "schema": "uruha_p3_b45_mechanical_rehearsal_result_v1",
        "phase": "P3-B45", "status": "mechanical_rehearsal_pass",
        "schedule_sha256": schedule["schedule_sha256"],
        "logical_steps": len(schedule["steps"]), "fake_transport_calls_planned": len(plan),
        "completed_checkpoints": completed, "reused_complete_checkpoints": reused,
        "new_fake_transport_calls": completed - reused,
        "real_model_calls": 0, "network_calls": 0, "paid_calls": 0,
        "annotations_accessed": 0, "real_generation_authorized": False,
        "claim_boundary": "Fake transport rehearsal of checkpoint mechanics only; no product or baseline output was generated.",
    }


def build_preflight(path: str | Path) -> dict[str, Any]:
    config = load_config(path)
    schedule = build_schedule(config)
    steps = schedule["steps"]
    pairs = [steps[index : index + 2] for index in range(0, len(steps), 2)]
    checks = {
        "config_and_frozen_dependencies_valid": True,
        "source_hash_bound_without_annotation_file_access": True,
        "rubric_hash_committed_without_annotation_file_access": True,
        "product_recursive_import_closure_matches_snapshot": config["_product_manifest"]["reachable_root_python_files"] > 0,
        "three_cases_twelve_turns_twenty_four_condition_steps": len(steps) == 24,
        "case_turn_condition_order_exact": all(
            pair[0]["condition"] == "product_system"
            and pair[1]["condition"] == "full_history_direct"
            and pair[0]["case_id"] == pair[1]["case_id"]
            and pair[0]["turn_id"] == pair[1]["turn_id"]
            for pair in pairs
        ),
        "future_turns_locked_per_step": all(
            len(step["visible_source_turn_ids"]) + len(step["locked_future_turn_ids"]) == 4
            for step in steps
        ),
        "third_turn_product_restarts_exact": sum(step["restart_product_before_step"] for step in steps) == 3,
        "no_retry_checkpoint_policy_frozen": config["checkpoint_contract"]["automatic_retry_count"] == 0,
        "config_does_not_authorize_generation": config["execution_boundary"]["real_model_calls_authorized_by_this_config"] is False,
    }
    return {
        "schema": "uruha_p3_prospective_v3_execution_contract_preflight_v1",
        "phase": "P3-B45",
        "status": "ready_for_fake_checkpoint_rehearsal" if all(checks.values()) else "not_ready_for_fake_checkpoint_rehearsal",
        "config_sha256": config["_config_sha256"],
        "source_sha256": SOURCE_SHA256,
        "rubric_sha256_commitment_only": RUBRIC_SHA256,
        "product_snapshot_commit": PRODUCT_COMMIT,
        "product_manifest_sha256": config["_product_manifest"]["manifest_sha256"],
        "product_reachable_root_python_files": config["_product_manifest"]["reachable_root_python_files"],
        "schedule_sha256": schedule["schedule_sha256"],
        "checks": checks,
        "logical_steps": len(steps), "real_model_calls": 0, "network_calls": 0,
        "paid_calls": 0, "annotations_accessed": 0, "production_database_accessed": False,
        "claim_boundary": "Zero-call contract preflight only; generation remains unauthorized and no quality result exists.",
    }


class _SimulatedPowerLoss(BaseException):
    pass


class _MechanicalTransport:
    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, request: Mapping[str, Any]) -> dict[str, Any]:
        self.calls += 1
        return {
            "content": f"fake-result-{request['logical_step_index']}",
            "model": "qwen2.5:7b", "backend": "fake_local_no_network",
            "usage": {"prompt_tokens": 10, "completion_tokens": 2, "wall_seconds": 0.001},
            "real_model_calls": 0, "network_calls": 0,
        }


def build_mechanical_audit(path: str | Path) -> dict[str, Any]:
    checks: dict[str, bool] = {}
    evidence: dict[str, Any] = {}
    with tempfile.TemporaryDirectory(prefix="uruha-p3b45-rehearsal-") as temporary:
        root = Path(temporary)

        transport = _MechanicalTransport()
        first = run_mechanical_rehearsal(path, root / "complete-reuse", transport)
        second = run_mechanical_rehearsal(path, root / "complete-reuse", transport)
        checks["fresh_run_then_complete_reuse_without_recall"] = (
            first["new_fake_transport_calls"] == 24
            and second["reused_complete_checkpoints"] == 24
            and second["new_fake_transport_calls"] == 0
            and transport.calls == 24
        )
        evidence["complete_reuse"] = {
            "first_new_calls": first["new_fake_transport_calls"],
            "second_reused": second["reused_complete_checkpoints"],
            "transport_calls_total": transport.calls,
        }

        transport = _MechanicalTransport()
        intent_root = root / "intent-only"
        try:
            run_mechanical_rehearsal(
                path, intent_root, transport,
                after_intent_hook=lambda index: (_ for _ in ()).throw(_SimulatedPowerLoss())
                if index == 4 else None,
            )
        except _SimulatedPowerLoss:
            pass
        intent_code = None
        try:
            run_mechanical_rehearsal(path, intent_root, transport)
        except P3ContractError as exc:
            intent_code = exc.code
        checks["intent_only_is_terminal_without_recall"] = (
            transport.calls == 4 and intent_code == "p3_b45_intent_without_complete_no_retry"
        )
        evidence["intent_only"] = {
            "transport_calls_before_crash": transport.calls,
            "resume_contract_code": intent_code,
        }

        transport = _MechanicalTransport()
        complete_root = root / "complete-after-crash"
        try:
            run_mechanical_rehearsal(
                path, complete_root, transport,
                after_complete_hook=lambda index: (_ for _ in ()).throw(_SimulatedPowerLoss())
                if index == 4 else None,
            )
        except _SimulatedPowerLoss:
            pass
        resumed = run_mechanical_rehearsal(path, complete_root, transport)
        checks["checkpoint_written_before_crash_is_reused"] = (
            resumed["reused_complete_checkpoints"] == 5
            and resumed["new_fake_transport_calls"] == 19
            and transport.calls == 24
        )
        evidence["post_complete_crash"] = {
            "resume_reused": resumed["reused_complete_checkpoints"],
            "resume_new_calls": resumed["new_fake_transport_calls"],
            "transport_calls_total": transport.calls,
        }

        failed_calls = {"count": 0}

        def fail_transport(_request: Mapping[str, Any]) -> Mapping[str, Any]:
            failed_calls["count"] += 1
            raise RuntimeError("simulated transport failure")

        failure_root = root / "transport-failure"
        first_code = second_code = None
        try:
            run_mechanical_rehearsal(path, failure_root, fail_transport)
        except P3ContractError as exc:
            first_code = exc.code
        try:
            run_mechanical_rehearsal(path, failure_root, fail_transport)
        except P3ContractError as exc:
            second_code = exc.code
        checks["transport_failure_is_terminal_without_retry"] = (
            failed_calls["count"] == 1
            and first_code == "p3_b45_transport_failure_no_retry"
            and second_code == "p3_b45_terminal_failure_no_retry"
        )
        evidence["transport_failure"] = {
            "transport_calls_total": failed_calls["count"],
            "first_contract_code": first_code, "resume_contract_code": second_code,
        }
    return {
        "schema": "uruha_p3_b45_checkpoint_mechanical_audit_v1",
        "phase": "P3-B45",
        "status": "checkpoint_mechanical_audit_pass" if all(checks.values()) else "checkpoint_mechanical_audit_failed",
        "checks": checks, "evidence": evidence,
        "real_model_calls": 0, "network_calls": 0, "paid_calls": 0,
        "annotations_accessed": 0, "production_database_accessed": False,
        "temporary_checkpoint_roots_removed": True,
        "claim_boundary": "Deterministic fake-transport checkpoint audit only; no product or direct-baseline generation and no quality evidence.",
    }
def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("preflight", "mechanical-audit"), default="preflight")
    parser.add_argument("--config", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = Path(args.output)
    if output.exists():
        return 2
    try:
        payload = (
            build_preflight(args.config)
            if args.mode == "preflight"
            else build_mechanical_audit(args.config)
        )
    except P3ContractError as exc:
        payload = {
            "schema": "uruha_p3_prospective_v3_execution_contract_refusal_v1",
            "phase": "P3-B45", "status": "execution_contract_refused",
            "contract_code": exc.code, "real_model_calls": 0, "network_calls": 0,
            "annotations_accessed": 0,
            "claim_boundary": "No generation or quality claim is authorized.",
        }
    write_new_json(output, payload)
    return 0 if payload.get("status") in {
        "ready_for_fake_checkpoint_rehearsal", "checkpoint_mechanical_audit_pass"
    } else 1


if __name__ == "__main__":
    raise SystemExit(main())
