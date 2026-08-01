#!/usr/bin/env python3
"""Audit and freeze the production-equivalent public-persona runtime conditions."""

from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
EXPERIMENT_ID = "public_persona_runtime_manifest_v1"
DEFAULT_PREREGISTRATION = ROOT / "configs/public_persona_runtime_manifest_v1_preregistration.json"
DEFAULT_CONDITION_CONTRACT = ROOT / "configs/public_persona_runtime_condition_contract_v1.json"
DEFAULT_HARNESS_LOCK = ROOT / "configs/public_persona_runtime_manifest_v1_harness_lock.json"
DEFAULT_BRAIN_SOURCE = ROOT / "uruha_brain_mac.py"
DEFAULT_WEB_SOURCE = ROOT / "uruha_web_ui.py"
DEFAULT_REFLECTION_SOURCE = ROOT / "uruha_reflection_runtime.py"
DEFAULT_PERSONA_CONTRACT_SOURCE = ROOT / "public_persona_contract_v3.py"
DEFAULT_ADAPTER_CONFIG = ROOT / "uruha_rightbrain_plan_sft_lora_v10_expanded_rejection_v1/adapter_config.json"
DEFAULT_ADAPTER_WEIGHTS = ROOT / "uruha_rightbrain_plan_sft_lora_v10_expanded_rejection_v1/adapter_model.safetensors"
DEFAULT_ADAPTER_TRAINING_RUN = ROOT / "uruha_rightbrain_plan_sft_lora_v10_expanded_rejection_v1/rightbrain_contract_v1_training_run.json"
DEFAULT_SELECTOR_MODEL = ROOT / "models/rightbrain_repair_selector_v1.json"
DEFAULT_REPORT_JSON = ROOT / "reports/public_persona_runtime_manifest_v1_construction.json"
DEFAULT_REPORT_MD = ROOT / "reports/public_persona_runtime_manifest_v1_construction.md"

PASS_DECISION = "freeze_current_s0_runtime_and_authorize_persona_policy_injection_seam_design_only"
FAIL_DECISION = "repair_runtime_audit_before_any_persona_model_comparison"


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def display_path(path):
    path = Path(path).resolve()
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def binding(path):
    return {"path": display_path(path), "sha256": sha256_file(path)}


def binding_valid(value):
    if not isinstance(value, dict):
        return False
    path = Path(str(value.get("path") or ""))
    if not path.is_absolute():
        path = ROOT / path
    return path.is_file() and str(value.get("sha256") or "") == sha256_file(path)


def parse_source(path):
    return ast.parse(Path(path).read_text(encoding="utf-8"), filename=str(path))


def _class_function(tree, class_name, function_name):
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name == function_name:
                    return child
    raise KeyError(f"{class_name}.{function_name}")


def _module_function(tree, function_name):
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name:
            return node
    raise KeyError(function_name)


def _call_name(call):
    node = call.func if isinstance(call, ast.Call) else call
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
    return ".".join(reversed(parts))


def function_calls(node):
    return sorted({_call_name(call) for call in ast.walk(node) if isinstance(call, ast.Call)})


def _assigned_node(tree, name):
    for node in tree.body:
        if isinstance(node, ast.Assign):
            if any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
                return node.value
    raise KeyError(name)


def _literal_or_default(node):
    try:
        return ast.literal_eval(node)
    except (ValueError, TypeError):
        pass
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in {"strip", "lower", "upper"}
        and not node.args
        and not node.keywords
    ):
        value = _literal_or_default(node.func.value)
        return getattr(str(value), node.func.attr)()
    if isinstance(node, ast.Call) and node.args:
        name = _call_name(node)
        if name in {"os.getenv", "_env_bool", "_env_int", "_env_float"} and len(node.args) >= 2:
            return ast.literal_eval(node.args[1])
        if name in {"_env_csv_floats", "_env_csv_ints"} and len(node.args) >= 2:
            return ast.literal_eval(node.args[1])
    raise ValueError(ast.dump(node, include_attributes=False))


def assignment_default(tree, name):
    return _literal_or_default(_assigned_node(tree, name))


def _has_call(calls, suffix):
    return any(name == suffix or name.endswith(f".{suffix}") for name in calls)


def _constructor_calls_without_arguments(node, name):
    return any(
        isinstance(call, ast.Call)
        and _call_name(call) == name
        and not call.args
        and not call.keywords
        for call in ast.walk(node)
    )


def _self_attribute_value(node, attribute_name):
    for child in ast.walk(node):
        if not isinstance(child, ast.Assign):
            continue
        for target in child.targets:
            if (
                isinstance(target, ast.Attribute)
                and isinstance(target.value, ast.Name)
                and target.value.id == "self"
                and target.attr == attribute_name
            ):
                return child.value
    raise KeyError(attribute_name)


def string_literals(node):
    return [
        child.value
        for child in ast.walk(node)
        if isinstance(child, ast.Constant) and isinstance(child.value, str)
    ]


def nested_string_value_count(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return 1
    if isinstance(node, ast.Dict):
        return sum(nested_string_value_count(value) for value in node.values)
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        return sum(nested_string_value_count(value) for value in node.elts)
    return 0


def source_audit():
    brain = parse_source(DEFAULT_BRAIN_SOURCE)
    web = parse_source(DEFAULT_WEB_SOURCE)
    reflection = parse_source(DEFAULT_REFLECTION_SOURCE)

    get_brain = _class_function(web, "RuntimeManager", "get_brain")
    controller_init = _class_function(brain, "UruhaBrainV4_Mac", "__init__")
    leftbrain_think = _class_function(brain, "LeftBrain", "think")
    rightbrain_init = _class_function(brain, "RightBrain", "__init__")
    run_turn = _class_function(brain, "UruhaBrainV4_Mac", "run_turn_debug")
    ingest = _class_function(brain, "UruhaBrainV4_Mac", "ingest_event")
    tick = _class_function(brain, "UruhaBrainV4_Mac", "cognitive_tick")
    emit = _class_function(brain, "UruhaBrainV4_Mac", "emit_response_if_ready")
    speak = _class_function(brain, "RightBrain", "speak")
    disabled = _class_function(brain, "RightBrain", "_model_surface_disabled_reason")
    resolve_load = _module_function(brain, "_resolve_right_brain_model_loading")
    reflection_enabled = _module_function(reflection, "typed_reflection_runtime_enabled")

    calls = {
        "web_get_brain": function_calls(get_brain),
        "controller_init": function_calls(controller_init),
        "run_turn_debug": function_calls(run_turn),
        "ingest_event": function_calls(ingest),
        "cognitive_tick": function_calls(tick),
        "emit_response_if_ready": function_calls(emit),
        "rightbrain_speak": function_calls(speak),
        "rightbrain_disable_gate": function_calls(disabled),
    }

    defaults = {
        "ollama_url": assignment_default(brain, "OLLAMA_URL"),
        "rightbrain_base_model": assignment_default(brain, "RIGHT_BRAIN_BASE_MODEL"),
        "working_memory_limit": assignment_default(brain, "WORKING_MEMORY_LIMIT"),
        "working_memory_retrieval_limit": assignment_default(brain, "WORKING_MEMORY_RETRIEVAL_LIMIT"),
        "working_memory_scoring_profile": assignment_default(brain, "WORKING_MEMORY_SCORING_PROFILE"),
        "planner_max_ticks": assignment_default(brain, "PLANNER_MAX_TICKS"),
        "rightbrain_model_blend_enabled": assignment_default(brain, "RIGHT_BRAIN_MODEL_BLEND_ENABLED"),
        "rightbrain_candidate_count": assignment_default(brain, "RIGHT_BRAIN_MODEL_CANDIDATE_COUNT"),
        "rightbrain_model_repair_enabled": assignment_default(brain, "RIGHT_BRAIN_MODEL_REPAIR_ENABLED"),
        "rightbrain_forbidden_projection_enabled": assignment_default(brain, "RIGHT_BRAIN_FORBIDDEN_CONFLICT_PROJECTION_ENABLED"),
        "rightbrain_forbidden_projection_shadow_enabled": assignment_default(brain, "RIGHT_BRAIN_FORBIDDEN_PROJECTION_SHADOW_ENABLED"),
        "rightbrain_selector_shadow_enabled": assignment_default(brain, "RIGHT_BRAIN_SELECTOR_SHADOW_ENABLED"),
        "public_persona_conditional_brief_enabled": assignment_default(brain, "PUBLIC_PERSONA_CONDITIONAL_BRIEF_ENABLED"),
    }

    resolve_text = ast.unparse(resolve_load)
    reflection_text = ast.unparse(reflection_enabled)
    fixed_family_nodes = {
        name: _self_attribute_value(rightbrain_init, name)
        for name in ("scene_fallbacks", "intent_reply_families")
    }
    fixed_reply_literal_count = sum(
        nested_string_value_count(node) for node in fixed_family_nodes.values()
    )
    leftbrain_target_instruction_present = any(
        "Ichinose Uruha" in text for text in string_literals(leftbrain_think)
    )
    checks = [
        ("web_uses_default_brain_constructor", _constructor_calls_without_arguments(get_brain, "UruhaBrainV4_Mac")),
        ("controller_constructs_memory", _has_call(calls["controller_init"], "MemoryManager")),
        ("controller_constructs_leftbrain", _has_call(calls["controller_init"], "LeftBrain")),
        ("controller_constructs_rightbrain_through_load_resolver", "_resolve_right_brain_model_loading" in calls["controller_init"]),
        ("run_turn_has_three_stage_pipeline", all(_has_call(calls["run_turn_debug"], name) for name in ("ingest_event", "cognitive_tick", "emit_response_if_ready"))),
        ("ingest_queries_memory", _has_call(calls["ingest_event"], "query_all_layers")),
        ("tick_classifies_signal", _has_call(calls["cognitive_tick"], "classify_user_signal")),
        ("tick_computes_prediction_error", _has_call(calls["cognitive_tick"], "_compute_prediction_error")),
        ("tick_appraises_input", _has_call(calls["cognitive_tick"], "_appraise_user_input")),
        ("tick_routes_high_or_low", _has_call(calls["cognitive_tick"], "_high_low_road_route")),
        ("tick_invokes_leftbrain_plan_path", _has_call(calls["cognitive_tick"], "think")),
        ("emit_invokes_rightbrain", _has_call(calls["emit_response_if_ready"], "speak")),
        ("emit_self_monitors_and_can_repair", all(_has_call(calls["emit_response_if_ready"], name) for name in ("_self_monitor_reply", "_repair_reply_from_self_monitor"))),
        ("emit_writes_episode_after_reply", _has_call(calls["emit_response_if_ready"], "save_episode")),
        ("sync_turn_does_not_call_background_cycle", not _has_call(calls["run_turn_debug"], "run_background_cycle")),
        ("rightbrain_model_default_is_off", defaults["rightbrain_model_blend_enabled"] is False),
        ("rightbrain_generation_is_gated", "model_blend_disabled" in ast.unparse(disabled) and "self.model_blend_enabled" in ast.unparse(disabled)),
        ("default_load_resolves_to_model_blend_flag", "RIGHT_BRAIN_MODEL_BLEND_ENABLED" in resolve_text),
        ("typed_reflection_requires_explicit_env_opt_in", "URUHA_ENABLE_TYPED_REFLECTION" in reflection_text and "os.environ" in reflection_text),
        ("persona_conditional_brief_default_is_off", defaults["public_persona_conditional_brief_enabled"] is False),
        ("leftbrain_contains_target_persona_instruction", leftbrain_target_instruction_present),
        ("rightbrain_contains_fixed_surface_families", fixed_reply_literal_count > 0),
    ]
    return {
        "defaults": defaults,
        "persona_crosscut_evidence": {
            "leftbrain_target_instruction_present": leftbrain_target_instruction_present,
            "rightbrain_fixed_family_attributes": sorted(fixed_family_nodes),
            "rightbrain_fixed_reply_literal_count": fixed_reply_literal_count,
            "interpretation": "These literals establish current cross-cutting persona and surface policy, not public-persona fidelity or lawful target evidence.",
        },
        "function_call_evidence": calls,
        "checks": [
            {"check_id": check_id, "passed": bool(passed)}
            for check_id, passed in checks
        ],
    }


def _run_command(args):
    try:
        completed = subprocess.run(
            args,
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"available": False, "error": f"{type(exc).__name__}: {exc}"}
    return {
        "available": completed.returncode == 0,
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def _parse_ollama_list(output, model_name):
    for line in str(output or "").splitlines()[1:]:
        fields = line.split()
        if fields and fields[0] == model_name:
            return {
                "name": fields[0],
                "artifact_id": fields[1] if len(fields) > 1 else "",
                "reported_size": " ".join(fields[2:4]) if len(fields) > 3 else "",
            }
    return {"name": model_name, "artifact_id": "", "reported_size": ""}


def local_artifact_snapshot():
    selector = load_json(DEFAULT_SELECTOR_MODEL)
    ollama_list = _run_command(["ollama", "list"])
    ollama_model = _parse_ollama_list(ollama_list.get("stdout"), "qwen2.5:7b")
    ollama_show = _run_command(["ollama", "show", "qwen2.5:7b", "--modelfile"])
    adapter_files_available = all(
        path.is_file()
        for path in (
            DEFAULT_ADAPTER_CONFIG,
            DEFAULT_ADAPTER_WEIGHTS,
            DEFAULT_ADAPTER_TRAINING_RUN,
        )
    )
    if adapter_files_available:
        adapter = load_json(DEFAULT_ADAPTER_CONFIG)
        training = load_json(DEFAULT_ADAPTER_TRAINING_RUN)
        adapter_snapshot = {
            "available_on_audited_machine": True,
            "base_model": adapter.get("base_model_name_or_path"),
            "adapter_config": binding(DEFAULT_ADAPTER_CONFIG),
            "adapter_weights": binding(DEFAULT_ADAPTER_WEIGHTS),
            "training_run": binding(DEFAULT_ADAPTER_TRAINING_RUN),
            "recorded_adapter_weights_sha256": training.get("output_adapter_model_sha256"),
            "weights_match_training_record": sha256_file(DEFAULT_ADAPTER_WEIGHTS) == training.get("output_adapter_model_sha256"),
            "active_by_default": False,
            "required_for_frozen_s0": False,
        }
    else:
        adapter_snapshot = {
            "available_on_audited_machine": False,
            "base_model": "Qwen/Qwen2.5-7B-Instruct",
            "weights_match_training_record": None,
            "active_by_default": False,
            "required_for_frozen_s0": False,
        }
    return {
        "leftbrain_local_model": {
            **ollama_model,
            "available": bool(ollama_list.get("available") and ollama_model["artifact_id"]),
            "modelfile_sha256": hashlib.sha256(ollama_show.get("stdout", "").encode("utf-8")).hexdigest() if ollama_show.get("available") else "",
        },
        "rightbrain_candidate_model": adapter_snapshot,
        "selector_shadow": {
            "model_type": selector.get("model_type"),
            "schema_version": selector.get("schema_version"),
            "artifact": binding(DEFAULT_SELECTOR_MODEL),
            "active_by_default": True,
            "changes_output_by_default": False,
        },
    }


def _package_version(name):
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "not_installed"


def environment_snapshot():
    hardware_model = _run_command(["sysctl", "-n", "hw.model"])
    memory_bytes = _run_command(["sysctl", "-n", "hw.memsize"])
    cpu_count = _run_command(["sysctl", "-n", "hw.ncpu"])
    try:
        import torch
        mps_available = bool(torch.backends.mps.is_available())
    except ImportError:
        mps_available = False
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "hardware_model": hardware_model.get("stdout", ""),
        "memory_bytes": int(memory_bytes.get("stdout", "0") or 0),
        "logical_cpu_count": int(cpu_count.get("stdout", "0") or 0),
        "mps_available": mps_available,
        "packages": {
            name: _package_version(name)
            for name in ("torch", "transformers", "peft", "openai", "chromadb", "gradio")
        },
    }


def validate_contract(preregistration, condition_contract):
    errors = []
    if preregistration.get("schema") != "uruha_public_persona_runtime_manifest_preregistration_v1":
        errors.append("preregistration_schema")
    if condition_contract.get("schema") != "uruha_public_persona_runtime_condition_contract_v1":
        errors.append("condition_contract_schema")
    for dependency_name, dependency in (preregistration.get("depends_on") or {}).items():
        if not binding_valid(dependency):
            errors.append(f"dependency_binding:{dependency_name}")
    conditions = condition_contract.get("conditions") or []
    required = set(preregistration["condition_contract"]["required_condition_ids"])
    actual = {row.get("condition_id") for row in conditions}
    if actual != required:
        errors.append("condition_ids")
    statuses = {row.get("condition_id"): row.get("implementation_status") for row in conditions}
    if statuses.get("s0_current_full_cognitive_persona") != "executable_now":
        errors.append("s0_status")
    if not str(statuses.get("c1_matched_direct_control", "")).startswith("blocked_"):
        errors.append("c1_must_be_blocked")
    if not str(statuses.get("c2_matched_persona_disabled", "")).startswith("blocked_"):
        errors.append("c2_must_be_blocked")
    if any(row.get("execution_authorized") is True for row in conditions if row.get("condition_id") != "s0_current_full_cognitive_persona"):
        errors.append("blocked_condition_execution_authorized")
    return errors


def validate_harness_lock(harness_lock):
    errors = []
    if harness_lock.get("schema") != "uruha_public_persona_runtime_manifest_harness_lock_v1":
        errors.append("harness_schema")
    if harness_lock.get("experiment_id") != EXPERIMENT_ID:
        errors.append("harness_experiment_id")
    for artifact_name, artifact in (harness_lock.get("frozen_artifacts") or {}).items():
        if not binding_valid(artifact):
            errors.append(f"harness_binding:{artifact_name}")
    return errors


def build_report(preregistration, condition_contract):
    audit = source_audit()
    artifacts = local_artifact_snapshot()
    environment = environment_snapshot()
    contract_errors = validate_contract(preregistration, condition_contract)
    harness_errors = validate_harness_lock(load_json(DEFAULT_HARNESS_LOCK))
    checks = list(audit["checks"])
    checks.extend(
        [
            {"check_id": "condition_contract_valid", "passed": not contract_errors},
            {"check_id": "harness_lock_valid", "passed": not harness_errors},
            {"check_id": "ollama_qwen2_5_7b_available", "passed": artifacts["leftbrain_local_model"]["available"]},
            {
                "check_id": "inactive_rightbrain_adapter_consistent_if_present",
                "passed": (
                    not artifacts["rightbrain_candidate_model"]["available_on_audited_machine"]
                    or artifacts["rightbrain_candidate_model"]["weights_match_training_record"] is True
                ),
            },
        ]
    )
    passed = all(row["passed"] for row in checks)
    conditions = condition_contract["conditions"]
    executable = [row["condition_id"] for row in conditions if row.get("implementation_status") == "executable_now"]
    blocked = [row["condition_id"] for row in conditions if str(row.get("implementation_status", "")).startswith("blocked_")]
    return {
        "schema": "uruha_public_persona_runtime_manifest_construction_v1",
        "experiment_id": EXPERIMENT_ID,
        "status": "construction_passed" if passed else "construction_failed",
        "generated_at": "2026-08-01",
        "decision": PASS_DECISION if passed else FAIL_DECISION,
        "inputs": {
            "preregistration": binding(DEFAULT_PREREGISTRATION),
            "condition_contract": binding(DEFAULT_CONDITION_CONTRACT),
            "brain_source": binding(DEFAULT_BRAIN_SOURCE),
            "web_source": binding(DEFAULT_WEB_SOURCE),
            "reflection_source": binding(DEFAULT_REFLECTION_SOURCE),
            "persona_contract_source": binding(DEFAULT_PERSONA_CONTRACT_SOURCE),
            "harness_lock": binding(DEFAULT_HARNESS_LOCK),
        },
        "source_audit": audit,
        "local_artifacts": artifacts,
        "environment": environment,
        "formal_runtime": {
            "current_system_id": "s0_current_full_cognitive_persona",
            "constructor": "UruhaBrainV4_Mac(load_right_brain_model=False)",
            "turn_method": "run_turn_debug",
            "rightbrain_output_mode": "deterministic_surface",
            "fixed_reply_family_present": True,
            "meets_no_fixed_reply_long_term_goal": False,
            "rightbrain_qwen_lora_generation_active": False,
            "typed_reflection_active": False,
            "async_background_runtime_active": False,
            "production_memory_path_allowed": False,
            "tts_vrm_or_function_call_execution": False,
        },
        "condition_readiness": {
            "condition_count": len(conditions),
            "executable_condition_ids": executable,
            "blocked_condition_ids": blocked,
            "primary_matched_control_executable": False,
            "persona_disabled_control_executable": False,
            "formal_comparative_execution_ready": False,
        },
        "checks": checks,
        "contract_errors": contract_errors,
        "harness_errors": harness_errors,
        "counts": {
            "check_count": len(checks),
            "check_pass_count": sum(row["passed"] for row in checks),
            "condition_count": len(conditions),
            "executable_condition_count": len(executable),
            "blocked_condition_count": len(blocked),
            "model_call_count": 0,
            "holdout_content_review_count": 0,
            "production_memory_write_count": 0,
            "runtime_change_count": 0,
            "prompt_change_count": 0,
            "model_weight_change_count": 0,
            "persona_score_count": 0,
        },
        "authorizations": {
            "current_s0_runtime_manifest_frozen": passed,
            "persona_policy_injection_seam_design": passed,
            "matched_control_execution": False,
            "model_execution": False,
            "runtime_change": False,
            "prompt_change": False,
            "memory_change": False,
            "model_training": False,
            "sealed_holdout_unsealing": False,
            "formal_persona_scoring": False,
            "public_persona_fidelity_claim": False,
        },
        "next_required_evidence": "Introduce a structured persona-policy provider that emits behavior constraints rather than fixed replies, plus a neutral matched provider and per-item compute ledger. Then verify C1/C2 parity on synthetic scenarios before any human or holdout evaluation.",
        "evidence_boundary": "This construction freezes the current synchronous S0 runtime and proves which comparison conditions remain unimplementable. It contains no generated replies, human ratings, holdout content, persona score, capability gain, model training or production behavior change.",
    }


def validate_report(report, preregistration):
    errors = []
    for row in report.get("checks") or []:
        if not row.get("passed"):
            errors.append(f"check:{row.get('check_id')}")
    for value in (report.get("inputs") or {}).values():
        if not binding_valid(value):
            errors.append(f"binding:{value.get('path')}")
    expected = preregistration["construction_success_requires"]
    counts = report.get("counts") or {}
    if counts.get("check_count", 0) < expected["source_check_count_min"]:
        errors.append("check_count")
    for name in (
        "model_call_count",
        "holdout_content_review_count",
        "production_memory_write_count",
        "runtime_change_count",
        "prompt_change_count",
        "model_weight_change_count",
        "persona_score_count",
    ):
        if counts.get(name) != expected[f"{name}_exact"]:
            errors.append(name)
    if counts.get("condition_count") != expected["condition_count_exact"]:
        errors.append("condition_count")
    if report.get("condition_readiness", {}).get("formal_comparative_execution_ready"):
        errors.append("formal_comparative_execution_must_remain_blocked")
    return errors


def render_markdown(report):
    defaults = report["source_audit"]["defaults"]
    crosscut = report["source_audit"]["persona_crosscut_evidence"]
    readiness = report["condition_readiness"]
    counts = report["counts"]
    status = "通過" if report["status"] == "construction_passed" else "失敗"
    return f"""# 公開人格正式執行條件 V1

## 結論

**建構檢查：{counts['check_pass_count']}/{counts['check_count']}，{status}。**

本輪只凍結目前聊天系統真正怎麼執行；沒有產生回答、沒有看 holdout、沒有改聊天行為。

## 目前完整系統 S0

`Web UI -> UruhaBrainV4_Mac() -> run_turn_debug()`

1. 檢索多層記憶，工作記憶上限 {defaults['working_memory_limit']} 條。
2. 分類訊號、計算預測誤差、心理評估並選擇高／低路線。
3. 左腦以規則或本機 `qwen2.5:7b` 建立計畫，最多 {defaults['planner_max_ticks']} 個規劃 tick。
4. 右腦目前預設使用含 {crosscut['rightbrain_fixed_reply_literal_count']} 個固定回覆字串的確定式表面化；微調 7B 候選生成為關閉。
5. 自我檢查後才寫入情節記憶；typed reflection 預設關閉。

## 公平對照狀態

| 條件 | 現況 | 原因 |
|---|---|---|
| S0 完整系統 | 可執行並已凍結 | 與目前 Web 預設一致 |
| C1 同資源直接回答 | 阻擋 | 模型呼叫數依輸入改變，且 persona 資訊尚未集中 |
| C2 關閉人格、架構相同 | 阻擋 | persona 規則橫跨左腦與右腦，沒有單一替換介面 |
| C3 prompt-only 下限 | 僅規格 | 可作描述下限，但不能當唯一公平對照 |

目前可執行條件：{len(readiness['executable_condition_ids'])}/{readiness['condition_count']}；正式比較仍未就緒。S0 是目前 runtime 基準，不代表已符合「不能靠固定回答」的長期目標。

## 為什麼現在不能直接算人格分數

如果現在硬跑 C1 或 C2，除了待測變因之外，模型呼叫、persona 資訊與確定式規則也會一起改變。分數即使不同，也不能判斷是認知架構、人格層或單純資源差造成。

## 下一個必要工程

建立只輸出行為限制、不輸出固定句的 persona-policy provider、中性 matched provider 與逐題 compute ledger。只有它們能讓 C1/C2 在每次只改一個變因的前提下真正執行。

## 證據邊界

本結果沒有證明人格相似度提高，也不授權正式 holdout、模型訓練或 production 行為修改。
"""


def write_text(path, text, overwrite=False):
    path = Path(path)
    if path.exists() and not overwrite:
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("build", nargs="?")
    parser.add_argument("--output-json", default=str(DEFAULT_REPORT_JSON))
    parser.add_argument("--output-md", default=str(DEFAULT_REPORT_MD))
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--require-pass", action="store_true")
    args = parser.parse_args(argv)

    preregistration = load_json(DEFAULT_PREREGISTRATION)
    condition_contract = load_json(DEFAULT_CONDITION_CONTRACT)
    report = build_report(preregistration, condition_contract)
    errors = validate_report(report, preregistration)
    if errors:
        report["status"] = "construction_failed"
        report["decision"] = FAIL_DECISION
        report["validation_errors"] = errors
    write_text(args.output_json, json.dumps(report, ensure_ascii=False, indent=2) + "\n", args.overwrite)
    write_text(args.output_md, render_markdown(report), args.overwrite)
    print(json.dumps({"status": report["status"], "decision": report["decision"], "errors": errors}, ensure_ascii=False))
    if args.require_pass and errors:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
