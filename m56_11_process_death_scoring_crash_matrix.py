#!/usr/bin/env python3
"""M56.11 actual subprocess-death crash matrix for frozen M56.10.

This is an engineering-validation harness, not a formal scoring entry.  It
creates only temporary forged runs, kills child processes at four frozen
phases with os._exit, and verifies the unchanged M56.10 restart behavior from
a clean parent process.  No fault hook is installed into the runtime module.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from hashlib import sha256
import html
import inspect
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from time import perf_counter
from typing import Any
from unittest import mock

import m56_4_separate_formal_scorer as scorer_m56
import m56_10_crash_safe_outcome_join as crash_safe_m56
from test_m56_9_single_writer_formal_scoring import (
    materialize_scoring_run,
    m569_private_roots,
)


ROOT = Path(__file__).resolve().parent
CONTRACT_PATH = ROOT / "configs/m56_11_process_death_scoring_crash_matrix_v1.json"
RESULT_PATH = ROOT / "analysis/m56_11_process_death_scoring_crash_matrix_result_2026-09-03.json"
MARKER_FILENAME = "m56_11_child_phase_observed.json"
MATRIX_SCHEMA = "uruha_m56_process_death_scoring_crash_matrix_result_v1"
AUDIT_SCHEMA = "uruha_m56_process_death_scoring_crash_matrix_audit_v1"


CHILD_PROGRAM = r'''
import os
from pathlib import Path
import sys
from unittest import mock

import m56_4_separate_formal_scorer as scorer
import m56_7_mac_full_sync_generation as durable
import m56_10_crash_safe_outcome_join as crash_safe
from test_m56_9_single_writer_formal_scoring import m569_private_roots

root = Path(sys.argv[1])
run_id = sys.argv[2]
phase = sys.argv[3]
marker = Path(sys.argv[4])

def mark(name):
    durable._durable_atomic_write_json(
        marker,
        {
            "schema": "uruha_m56_11_temporary_child_phase_marker_v1",
            "phase": name,
            "outcome_loader_returned": name != "after_lock_before_m56_10_state",
            "temporary_forged_fixture_only": True,
        },
        exclusive=True,
    )

with m569_private_roots(root):
    if phase == "after_lock_before_m56_10_state":
        with mock.patch.object(crash_safe, "_execute_under_lock", side_effect=lambda value: os._exit(70)):
            crash_safe.execute_crash_safe_outcome_join_formal_scoring(run_id)
    elif phase == "after_outcome_load_before_checkpoint":
        original_load = scorer.load_outcome_inputs
        def stop_after_load(value):
            result = original_load(value)
            mark(phase)
            os._exit(71)
        with mock.patch.object(scorer, "load_outcome_inputs", side_effect=stop_after_load):
            crash_safe.execute_crash_safe_outcome_join_formal_scoring(run_id)
    elif phase == "after_checkpoint_before_canonical_report":
        def stop_after_checkpoint(*args, **kwargs):
            mark(phase)
            os._exit(72)
        with mock.patch.object(crash_safe, "_finalize_from_checkpoint", side_effect=stop_after_checkpoint):
            crash_safe.execute_crash_safe_outcome_join_formal_scoring(run_id)
    elif phase == "after_canonical_report_before_result_commitment":
        original_write = crash_safe._durable_write_or_validate_identical
        def stop_after_report(path, value):
            result = original_write(path, value)
            if Path(path).name == scorer.SCORE_REPORT_FILENAME:
                mark(phase)
                os._exit(73)
            return result
        with mock.patch.object(crash_safe, "_durable_write_or_validate_identical", side_effect=stop_after_report):
            crash_safe.execute_crash_safe_outcome_join_formal_scoring(run_id)
    else:
        raise ValueError("unknown frozen M56.11 phase")
'''


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


def validate_contract(contract: dict[str, Any] | None = None) -> dict[str, Any]:
    contract = deepcopy(contract or load_contract())
    errors: list[str] = []
    expected_fields = {
        "schema", "version", "status", "single_changed_variable", "public_api",
        "frozen_dependencies", "matrix", "isolation", "unchanged_semantics",
        "authorization", "claim_boundary",
    }
    if set(contract) != expected_fields:
        errors.append("contract.fields")
    if contract.get("schema") != "uruha_m56_process_death_scoring_crash_matrix_contract_v1":
        errors.append("contract.schema")
    if contract.get("version") != "1.0.0":
        errors.append("contract.version")
    if contract.get("status") != "prospective_frozen_before_implementation_and_any_real_m56_target_outcome_access":
        errors.append("contract.status")
    api = contract.get("public_api") or {}
    if api.get("function") != "run_process_death_crash_matrix" or api.get("parameters") != []:
        errors.append("public_api.signature")
    if api.get("run_id_private_root_outcome_result_retry_or_fault_location_injection_allowed") is not False:
        errors.append("public_api.injection")
    dependencies = contract.get("frozen_dependencies") or {}
    if len(dependencies) != 6:
        errors.append("dependencies.count")
    for relative_path, expected_hash in dependencies.items():
        path = ROOT / relative_path
        if not path.is_file() or sha256_file(path) != expected_hash:
            errors.append(f"dependency:{relative_path}")
    matrix = contract.get("matrix") or []
    expected_matrix = [
        ("after_lock_before_m56_10_state", 70, "one_outcome_load_and_complete", 1),
        ("after_outcome_load_before_checkpoint", 71, "zero_load_terminal_failure", 1),
        ("after_checkpoint_before_canonical_report", 72, "zero_load_complete_from_checkpoint", 1),
        ("after_canonical_report_before_result_commitment", 73, "zero_load_complete_from_checkpoint", 1),
    ]
    observed_matrix = [
        (row.get("phase"), row.get("child_exit_code"), row.get("restart"), row.get("total_outcome_loads"))
        for row in matrix if isinstance(row, dict)
    ]
    if observed_matrix != expected_matrix:
        errors.append("matrix.content_or_order")
    isolation = contract.get("isolation") or {}
    if any(isolation.get(name) is not True for name in (
        "temporary_forged_30_row_runs_only", "test_marker_full_sync_and_temporary",
    )):
        errors.append("isolation.required")
    if any(isolation.get(name) is not False for name in (
        "configured_real_private_root_access_allowed", "formal_fault_hook_added_to_runtime",
        "raw_outcome_source_or_model_response_in_matrix_output_allowed",
        "child_processes_left_running_allowed",
    )):
        errors.append("isolation.denials")
    unchanged = contract.get("unchanged_semantics") or {}
    if not unchanged or any(value is not True for value in unchanged.values()):
        errors.append("unchanged_semantics")
    authorization = contract.get("authorization") or {}
    if not authorization or any(value is not False for value in authorization.values()):
        errors.append("authorization.current")
    if list(inspect.signature(run_process_death_crash_matrix).parameters):
        errors.append("implementation.public_signature")
    return {
        "valid": not errors,
        "errors": errors,
        "contract_hash": digest(contract),
        "binding_count": len(dependencies),
        "phase_count": len(matrix),
    }


def _artifact_state(run_root: Path, marker: Path) -> dict[str, Any]:
    return {
        "mode": (run_root / "telemetry" / crash_safe_m56.MODE_FILENAME).exists(),
        "intent": (run_root / "telemetry" / crash_safe_m56.INTENT_FILENAME).exists(),
        "checkpoint": (run_root / "scoring" / crash_safe_m56.CHECKPOINT_FILENAME).exists(),
        "canonical_report": (run_root / "scoring" / scorer_m56.SCORE_REPORT_FILENAME).exists(),
        "result_commitment": (
            run_root / "commitments" / scorer_m56.RESULT_COMMITMENT_FILENAME
        ).exists(),
        "terminal_failure": (
            run_root / "telemetry" / crash_safe_m56.FAILURE_FILENAME
        ).exists(),
        "child_phase_marker": marker.exists(),
    }


def _run_child(root: Path, run_id: str, phase: str, marker: Path) -> tuple[subprocess.CompletedProcess[str], float]:
    started = perf_counter()
    child = subprocess.run(
        [sys.executable, "-c", CHILD_PROGRAM, str(root), run_id, phase, str(marker)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    return child, perf_counter() - started


def _restart_scenario(root: Path, run_id: str, phase: str) -> tuple[dict[str, Any], float]:
    original_load = scorer_m56.load_outcome_inputs
    restart_loads = 0

    def counted_load(value: str):
        nonlocal restart_loads
        restart_loads += 1
        if phase != "after_lock_before_m56_10_state":
            raise AssertionError("post-outcome process-death restart attempted a duplicate load")
        return original_load(value)

    started = perf_counter()
    with m569_private_roots(root), mock.patch.object(
        scorer_m56, "load_outcome_inputs", side_effect=counted_load
    ):
        if phase == "after_outcome_load_before_checkpoint":
            try:
                crash_safe_m56.execute_crash_safe_outcome_join_formal_scoring(run_id)
            except PermissionError as exc:
                result = {
                    "status": "terminal_rejected_without_outcome_reload",
                    "error_class": type(exc).__name__,
                    "error_confirms_reload_forbidden": "outcome reload is forbidden" in str(exc),
                    "formal_result_created": False,
                }
            else:  # pragma: no cover - validator and tests reject this state
                result = {
                    "status": "unexpected_success",
                    "formal_result_created": True,
                }
        else:
            runtime_result = crash_safe_m56.execute_crash_safe_outcome_join_formal_scoring(run_id)
            result = {
                "status": "completed_after_process_death",
                "formal_result_created": runtime_result["formal_result_created"],
                "score_report_hash": runtime_result["score_report_hash"],
                "result_commitment_hash": runtime_result["result_commitment_hash"],
                "m56_10_outcome_load_this_invocation": runtime_result[
                    "m56_10_private_outcome_load_this_invocation"
                ],
            }
    result["restart_outcome_loader_calls"] = restart_loads
    return result, perf_counter() - started


def _run_scenario(root: Path, phase_row: dict[str, Any]) -> dict[str, Any]:
    phase = phase_row["phase"]
    run_id = f"m56-11-{phase.replace('_', '-')}"
    with m569_private_roots(root):
        run_root = materialize_scoring_run(root, run_id)
    marker = run_root / "telemetry" / MARKER_FILENAME
    child, child_seconds = _run_child(root, run_id, phase, marker)
    state_after_child = _artifact_state(run_root, marker)
    report_hash_before_restart = None
    if state_after_child["canonical_report"]:
        report_hash_before_restart = load_json(
            run_root / "scoring" / scorer_m56.SCORE_REPORT_FILENAME
        ).get("score_report_hash")
    restart, restart_seconds = _restart_scenario(root, run_id, phase)
    state_after_restart = _artifact_state(run_root, marker)
    report_hash_after_restart = None
    if state_after_restart["canonical_report"]:
        report_hash_after_restart = load_json(
            run_root / "scoring" / scorer_m56.SCORE_REPORT_FILENAME
        ).get("score_report_hash")
    child_loads = 1 if state_after_child["child_phase_marker"] else 0
    value = {
        "phase": phase,
        "expected_child_exit_code": phase_row["child_exit_code"],
        "observed_child_exit_code": child.returncode,
        "child_stdout_empty": child.stdout == "",
        "child_stderr_empty": child.stderr == "",
        "child_elapsed_seconds": child_seconds,
        "child_outcome_loader_returns_observed": child_loads,
        "state_after_child": state_after_child,
        "restart": restart,
        "restart_elapsed_seconds": restart_seconds,
        "state_after_restart": state_after_restart,
        "total_outcome_loader_returns": child_loads + restart["restart_outcome_loader_calls"],
        "expected_total_outcome_loads": phase_row["total_outcome_loads"],
        "report_hash_before_restart": report_hash_before_restart,
        "report_hash_after_restart": report_hash_after_restart,
        "report_unchanged_when_preexisting": (
            report_hash_before_restart is None
            or report_hash_before_restart == report_hash_after_restart
        ),
        "child_process_left_running": False,
    }
    value["scenario_hash"] = digest(value)
    return value


def _find_forbidden_output_keys(value: Any, prefix: str = "") -> list[str]:
    forbidden = {
        "actual_observed_behavior", "acceptable_behavior_labels", "outcomes",
        "source_text", "raw_response", "reasoning_trace", "private_outcome_key",
    }
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            if key in forbidden:
                found.append(path)
            found.extend(_find_forbidden_output_keys(child, path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_find_forbidden_output_keys(child, f"{prefix}[{index}]"))
    return found


def validate_matrix(result: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if not isinstance(result, dict):
        return {"valid": False, "errors": ["result.object"]}
    expected_fields = {
        "schema", "version", "status", "contract_hash", "fixture_kind",
        "phase_count", "child_process_count", "all_children_reaped",
        "configured_real_private_root_access_count", "real_target_outcome_access_count",
        "scorer_model_call_count", "retry_count", "fallback_count", "scenarios",
        "total_wall_seconds", "claim_boundary", "matrix_hash",
    }
    if set(result) != expected_fields:
        errors.append("result.fields")
    unhashed = {key: value for key, value in result.items() if key != "matrix_hash"}
    if result.get("matrix_hash") != digest(unhashed):
        errors.append("result.hash")
    if result.get("schema") != MATRIX_SCHEMA or result.get("status") != "all_preregistered_process_death_states_passed":
        errors.append("result.schema_or_status")
    contract_report = validate_contract()
    if result.get("contract_hash") != contract_report["contract_hash"]:
        errors.append("result.contract_hash")
    scenarios = result.get("scenarios") or []
    frozen = load_contract()["matrix"]
    if len(scenarios) != 4:
        errors.append("result.scenario_count")
    for expected, observed in zip(frozen, scenarios):
        if observed.get("phase") != expected["phase"]:
            errors.append(f"scenario:{expected['phase']}:order")
            continue
        phase = expected["phase"]
        if observed.get("observed_child_exit_code") != expected["child_exit_code"]:
            errors.append(f"scenario:{phase}:exit_code")
        if observed.get("total_outcome_loader_returns") != expected["total_outcome_loads"]:
            errors.append(f"scenario:{phase}:outcome_load_count")
        if observed.get("child_process_left_running") is not False:
            errors.append(f"scenario:{phase}:child_process")
        if observed.get("scenario_hash") != digest({
            key: value for key, value in observed.items() if key != "scenario_hash"
        }):
            errors.append(f"scenario:{phase}:hash")
        restart = observed.get("restart") or {}
        state_child = observed.get("state_after_child") or {}
        state_restart = observed.get("state_after_restart") or {}
        if phase == "after_lock_before_m56_10_state":
            if state_child.get("mode") is not False or restart.get("restart_outcome_loader_calls") != 1:
                errors.append(f"scenario:{phase}:pre_state")
            if restart.get("formal_result_created") is not True:
                errors.append(f"scenario:{phase}:completion")
        elif phase == "after_outcome_load_before_checkpoint":
            if state_child.get("intent") is not True or state_child.get("checkpoint") is not False:
                errors.append(f"scenario:{phase}:crash_state")
            if restart.get("restart_outcome_loader_calls") != 0:
                errors.append(f"scenario:{phase}:duplicate_load")
            if restart.get("status") != "terminal_rejected_without_outcome_reload":
                errors.append(f"scenario:{phase}:terminal")
            if state_restart.get("terminal_failure") is not True or state_restart.get("result_commitment") is not False:
                errors.append(f"scenario:{phase}:terminal_artifacts")
        elif phase == "after_checkpoint_before_canonical_report":
            if state_child.get("checkpoint") is not True or state_child.get("canonical_report") is not False:
                errors.append(f"scenario:{phase}:crash_state")
            if restart.get("restart_outcome_loader_calls") != 0 or restart.get("formal_result_created") is not True:
                errors.append(f"scenario:{phase}:recovery")
        elif phase == "after_canonical_report_before_result_commitment":
            if state_child.get("canonical_report") is not True or state_child.get("result_commitment") is not False:
                errors.append(f"scenario:{phase}:crash_state")
            if restart.get("restart_outcome_loader_calls") != 0 or restart.get("formal_result_created") is not True:
                errors.append(f"scenario:{phase}:recovery")
            if observed.get("report_unchanged_when_preexisting") is not True:
                errors.append(f"scenario:{phase}:report_mutation")
    if result.get("child_process_count") != 4 or result.get("all_children_reaped") is not True:
        errors.append("result.process_accounting")
    if result.get("configured_real_private_root_access_count") != 0:
        errors.append("result.real_root_access")
    if result.get("real_target_outcome_access_count") != 0:
        errors.append("result.real_outcome_access")
    if result.get("scorer_model_call_count") != 0:
        errors.append("result.model_calls")
    if result.get("retry_count") != 0 or result.get("fallback_count") != 0:
        errors.append("result.retry_or_fallback")
    errors.extend(f"result.forbidden:{name}" for name in _find_forbidden_output_keys(result))
    return {"valid": not errors, "errors": errors, "matrix_hash": result.get("matrix_hash")}


def run_process_death_crash_matrix() -> dict[str, Any]:
    """Run all frozen child-death phases on fresh temporary forged runs."""

    contract_report = validate_contract()
    if not contract_report["valid"]:
        raise PermissionError("M56.11 contract invalid: " + "; ".join(contract_report["errors"]))
    started = perf_counter()
    with TemporaryDirectory(prefix="uruha-m56-11-process-death-") as temp:
        root = Path(temp).resolve()
        if root == scorer_m56.PRIVATE_ROOT.resolve() or scorer_m56.PRIVATE_ROOT.resolve() in root.parents:
            raise PermissionError("M56.11 fixture root must not be the configured real private root")
        scenarios = [_run_scenario(root, row) for row in load_contract()["matrix"]]
    value = {
        "schema": MATRIX_SCHEMA,
        "version": "1.0.0",
        "status": "all_preregistered_process_death_states_passed",
        "contract_hash": contract_report["contract_hash"],
        "fixture_kind": "temporary_forged_30_row_runs_only",
        "phase_count": 4,
        "child_process_count": 4,
        "all_children_reaped": True,
        "configured_real_private_root_access_count": 0,
        "real_target_outcome_access_count": 0,
        "scorer_model_call_count": 0,
        "retry_count": 0,
        "fallback_count": 0,
        "scenarios": scenarios,
        "total_wall_seconds": perf_counter() - started,
        "claim_boundary": load_contract()["claim_boundary"],
    }
    value["matrix_hash"] = digest(value)
    validation = validate_matrix(value)
    if not validation["valid"]:
        raise AssertionError("M56.11 crash matrix invalid: " + "; ".join(validation["errors"]))
    return value


def build_live_audit() -> dict[str, Any]:
    contract_report = validate_contract()
    upstream = crash_safe_m56.build_live_audit()
    value = {
        "schema": AUDIT_SCHEMA,
        "version": "1.0.0",
        "status": "process_death_matrix_engineering_only_formal_scoring_denied",
        "contract_valid": contract_report["valid"],
        "contract_hash": contract_report["contract_hash"],
        "counts": deepcopy(upstream["counts"]),
        "formal_scoring_authorized": False,
        "formal_model_calls": 0,
        "target_outcome_access_count": 0,
        "formal_result_created": False,
        "power_loss_tested": False,
        "blocking_gates": deepcopy(upstream["blocking_gates"]),
        "claim_boundary": load_contract()["claim_boundary"],
    }
    value["audit_hash"] = digest(value)
    return value


def load_saved_matrix(path: str | Path = RESULT_PATH) -> dict[str, Any]:
    matrix = load_json(path)
    validation = validate_matrix(matrix)
    if not validation["valid"]:
        raise PermissionError("M56.11 saved matrix invalid: " + "; ".join(validation["errors"]))
    return matrix


def build_demo_report(matrix: dict[str, Any] | None = None) -> dict[str, Any]:
    matrix = deepcopy(matrix) if matrix is not None else load_saved_matrix()
    validation = validate_matrix(matrix)
    if not validation["valid"]:
        raise PermissionError("M56.11 demo matrix invalid: " + "; ".join(validation["errors"]))
    return {
        "schema": "uruha_m56_process_death_scoring_crash_matrix_demo_v1",
        "audit": build_live_audit(),
        "matrix": matrix,
    }


def render_dashboard(report: dict[str, Any] | None = None) -> str:
    report = deepcopy(report or build_demo_report())
    audit = report["audit"]
    counts = audit["counts"]
    boundary = html.escape(audit["claim_boundary"])
    rows = {row["phase"]: row for row in report["matrix"]["scenarios"]}
    before_state = rows["after_lock_before_m56_10_state"]
    ambiguous = rows["after_outcome_load_before_checkpoint"]
    checkpoint = rows["after_checkpoint_before_canonical_report"]
    report_written = rows["after_canonical_report_before_result_commitment"]
    matching_exits = sum(
        row["observed_child_exit_code"] == row["expected_child_exit_code"]
        for row in rows.values()
    )
    unique_total_reads = sorted({row["total_outcome_loader_returns"] for row in rows.values()})
    total_read_label = str(unique_total_reads[0]) if len(unique_total_reads) == 1 else "不一致"
    reaped_count = sum(not row["child_process_left_running"] for row in rows.values())
    return f"""<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>M56.11 真程序中斷驗證</title><style>
*{{box-sizing:border-box}}body{{margin:0;background:#07131c;color:#eefaff;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}main{{max-width:1240px;margin:auto;padding:28px}}section{{border:1px solid #31586c;border-radius:20px;background:#0b202d;padding:24px;margin-bottom:18px}}.hero{{background:linear-gradient(135deg,#173c48,#3a233e)}}.deny{{display:inline-block;background:#672633;color:#ffdae0;border-radius:999px;padding:8px 12px;font-weight:850}}h1{{font-size:clamp(30px,5vw,45px);margin:14px 0 8px}}p{{color:#bfdbe4;line-height:1.62}}.metrics{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;border:0;background:none;padding:0}}.metric,.step,.result{{border:1px solid #31586c;border-radius:16px;background:#0a1b27;padding:17px}}.metric strong{{display:block;color:#7ce2c4;font-size:28px}}.flow{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}}.step b{{display:grid;place-items:center;width:40px;height:40px;border-radius:50%;background:#265f6b;color:#8af0d3}}.recover{{border-color:#2b806a}}.terminal{{border-color:#b76f3c;background:#281b13}}.result{{margin-top:12px;color:#8be8ce;font-weight:750}}.boundary{{border-left:6px solid #e1a452;background:#272014}}.legend{{display:flex;gap:14px;flex-wrap:wrap}}.legend span{{padding:7px 11px;border-radius:999px;background:#16313e}}@media(max-width:900px){{.metrics,.flow{{grid-template-columns:1fr}}}}
</style></head><body><main>
<section class="hero"><span class="deny">DENIED NOW · 0 REAL OUTCOME READS</span><h1>M56.11 · 真的讓程序死亡，再看新程序會不會偷讀第二次</h1><p>M56.10 的例外測試可能執行清理程式；這次用四個獨立 child process 與 <code>os._exit</code>，讓它們在不同落盤位置直接死亡，再由全新的程序接手。</p></section>
<section class="metrics"><div class="metric"><strong>{counts['v7_slots_by_ledger'][0]}/18</strong><small>真人 A</small></div><div class="metric"><strong>{counts['v7_slots_by_ledger'][1]}/18</strong><small>真人 B</small></div><div class="metric"><strong>{counts['real_temporal_rows']}/30</strong><small>正式時間列</small></div><div class="metric"><strong>0</strong><small>正式答案／結果</small></div></section>
<section><h2>四個真正的程序死亡位置</h2><div class="flow"><div class="step recover"><b>{before_state['observed_child_exit_code']}</b><h3>鎖後、狀態前</h3><p>死亡後 OS 釋放鎖；新程序正常讀一次並完成。</p><div class="result">總讀取 {before_state['total_outcome_loader_returns']}</div></div><div class="step terminal"><b>{ambiguous['observed_child_exit_code']}</b><h3>答案後、checkpoint 前</h3><p>只剩 intent；新程序 {ambiguous['restart']['restart_outcome_loader_calls']} 重讀、寫 terminal failure。</p><div class="result">總讀取 {ambiguous['total_outcome_loader_returns']} · 不完成</div></div><div class="step recover"><b>{checkpoint['observed_child_exit_code']}</b><h3>checkpoint 後、report 前</h3><p>新程序直接使用 checkpoint；{checkpoint['restart']['restart_outcome_loader_calls']} 重讀完成。</p><div class="result">總讀取 {checkpoint['total_outcome_loader_returns']} · 完成</div></div><div class="step recover"><b>{report_written['observed_child_exit_code']}</b><h3>report 後、result 前</h3><p>既有 report hash 不變；{report_written['restart']['restart_outcome_loader_calls']} 重讀補完 commitment。</p><div class="result">總讀取 {report_written['total_outcome_loader_returns']} · 完成</div></div></div></section>
<section><h2>這次真正驗證了什麼</h2><div class="legend"><span>{reaped_count} 個 child 都被回收</span><span>{matching_exits}/4 exit code 符合</span><span>每條路徑總讀取都是 {total_read_label}</span><span>retry {report['matrix']['retry_count']}</span><span>scorer model call {report['matrix']['scorer_model_call_count']}</span></div><p>這把 M56.10 從「同一程序裡丟例外」推進到「程序真的消失、OS 鎖真的釋放、新程序真的接手」。頁面數字直接來自已驗證的封存矩陣，不是手寫結果。</p></section>
<section class="boundary"><h2>仍然不能說的事</h2><p>這不是拔電、kernel crash、壞硬碟或多機交易測試；也沒有使用真人資料或正式答案。intent-only 路徑仍刻意犧牲可用性，不能假稱所有中斷都能完成。</p></section>
<section><h2>證據邊界</h2><p>{boundary}</p></section>
</main></body></html>"""


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
    parser = argparse.ArgumentParser(description="M56.11 actual process-death scoring crash matrix")
    parser.add_argument("--matrix", action="store_true")
    parser.add_argument("--audit", action="store_true")
    parser.add_argument("--serve", type=int)
    args = parser.parse_args()
    if args.serve is not None:
        serve_demo(args.serve)
    elif args.matrix:
        print(json.dumps(run_process_death_crash_matrix(), ensure_ascii=False, indent=2))
    else:
        print(json.dumps(build_live_audit(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
