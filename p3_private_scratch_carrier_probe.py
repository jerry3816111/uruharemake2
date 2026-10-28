#!/usr/bin/env python3
"""P3-B13 causal probe for the private-scratch carrier role."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import time
from typing import Any, Mapping

from p3_baseline_instruction_language_probe import load_probe as load_instruction_probe
from p3_product_comparison import (
    P3ContractError,
    canonical_sha256,
    make_request,
    new_budget,
    record_condition_wall,
    run_call_once,
    shared_visible_surface_contract,
    write_new_json,
)
from p3_product_worker import (
    LocalOllamaQwenStageCounter,
    _local_canary_baseline_transport,
    _ollama_model_metadata,
    localhost_network_only,
    summarize_checkpoint_evidence,
)


SCHEMA = "uruha_p3_private_scratch_carrier_probe_v1"
RELEASE_SCHEMA = "uruha_p3_private_scratch_carrier_probe_release_v1"
MODEL_DIGEST = "2bada8a7450677000f678be90653b85d364de7db25eb5ea54136ada5f3933730"


def _read(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise P3ContractError("p3_b13_invalid_json", str(path)) from exc
    if not isinstance(value, dict):
        raise P3ContractError("p3_b13_invalid_json", str(path))
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


def load_probe(path: str | Path) -> dict[str, Any]:
    probe_path = Path(path)
    raw = _read(probe_path)
    if set(raw) != {
        "schema", "status", "purpose", "instruction_probe_config",
        "instruction_probe_result", "scratch_token_binding", "source",
        "locked_control", "treatment", "generation", "execution_boundary", "success",
    } or raw.get("schema") != SCHEMA:
        raise P3ContractError("p3_b13_schema_mismatch")
    if raw.get("status") != "preregistered_not_executed" or raw.get("purpose") != (
        "test_user_role_labeled_scratch_against_locked_assistant_carrier_control"
    ):
        raise P3ContractError("p3_b13_status_mismatch")
    repo = probe_path.resolve().parent.parent
    config_path = _ref(repo, raw.get("instruction_probe_config"), {
        "path": "configs/p3_baseline_instruction_language_probe_v1.json",
        "sha256": "dc99af1c2bed92abc11258bd5c3a7949b6f97f7bb47247b1853c7e93c55f12c0",
    }, "p3_b13_instruction_config_mismatch")
    result_path = _ref(repo, raw.get("instruction_probe_result"), {
        "path": "analysis/p3_b11_instruction_language_probe_result_2026-09-15.json",
        "sha256": "baf6c4c1581dfc1fd2c26e36114791526ed117dd6e13bd4137feb2b84bf6957a",
        "required_status": "instruction_language_probe_pass",
    }, "p3_b13_control_result_mismatch")
    binding_path = _ref(repo, raw.get("scratch_token_binding"), {
        "path": "analysis/p3_b12_private_scratch_binding_result_2026-09-15.json",
        "sha256": "dce18b322d11f80ac3ee0003442da270f366ed8493da112403d9697f970a3631",
        "required_status": "private_scratch_binding_pass",
    }, "p3_b13_binding_result_mismatch")
    instruction = load_instruction_probe(config_path)
    result = _read(result_path)
    binding = _read(binding_path)
    if result.get("status") != "instruction_language_probe_pass" or binding.get("binding_verified") is not True:
        raise P3ContractError("p3_b13_upstream_status_invalid")
    source = raw.get("source")
    if source != {
        "content": "A neighbor asked whether I can join a crowded weekend cleanup. I said I have not decided yet.",
        "content_sha256": "d9ca3ce2a80bd1482f6e9b57328ed9a3ce07e104e5a08613f51034f288c22502",
        "developer_case_source": False, "annotations_exist": False,
    } or canonical_sha256(source["content"]) != source["content_sha256"]:
        raise P3ContractError("p3_b13_source_mismatch")
    control = raw.get("locked_control")
    expected_control = result["arms"]["japanese_instructions"]["conditions"]["full_history_deliberate"]
    expected = {
        "arm": "japanese_instructions",
        "draft": expected_control["calls"][0]["content"],
        "draft_sha256": canonical_sha256(expected_control["calls"][0]["content"]),
        "critique": expected_control["calls"][1]["content"],
        "critique_sha256": canonical_sha256(expected_control["calls"][1]["content"]),
        "final": expected_control["final"]["content"],
        "final_sha256": canonical_sha256(expected_control["final"]["content"]),
        "carrier": "assistant",
    }
    if control != expected:
        raise P3ContractError("p3_b13_locked_control_mismatch")
    if raw.get("treatment") != {
        "carrier": "user_labeled_private_context",
        "new_stages": ["critique", "revise"],
        "completion_caps": [256, 256],
        "uncertainty_anchors_any": ["まだ", "決め", "未定", "迷"],
        "generic_service_markers_forbidden": ["質問", "お手伝い", "教えてください"],
        "polite_register_markers_forbidden": ["です", "ます", "ください"],
    }:
        raise P3ContractError("p3_b13_treatment_mismatch")
    design = instruction["_design"]
    if raw.get("generation") != {
        "model": "qwen2.5:7b", "digest": MODEL_DIGEST,
        "temperature": 0, "seed": 20260909, "top_p": 1,
        "num_ctx": 8192, "think": False,
    }:
        raise P3ContractError("p3_b13_generation_mismatch")
    if raw.get("execution_boundary") != {
        "provider_calls_exact": 2, "automatic_retry": False, "concurrency": 1,
        "localhost_only": True, "developer_case_access": False,
        "annotation_access": False, "confirmation_access": False,
        "production_database_access": False, "external_deployment": False,
        "remote_paid_calls": False,
        "real_model_calls_authorized_by_this_config": False,
    } or raw.get("success") != {
        "critique_nonempty": True, "final_shared_surface_pass": True,
        "final_preserves_uncertainty_anchor": True,
        "final_has_no_generic_service_escape": True,
        "final_has_no_polite_register": True,
        "treatment_passes_while_locked_control_fails": True,
    }:
        raise P3ContractError("p3_b13_boundary_mismatch")
    frozen = json.loads(json.dumps(raw, ensure_ascii=False))
    frozen["_probe_sha256"] = hashlib.sha256(probe_path.read_bytes()).hexdigest()
    frozen["_probe_path"] = str(probe_path.resolve())
    frozen["_design"] = design
    frozen["_japanese_instructions"] = instruction["arms"]["japanese_instructions"]
    return frozen


def _messages(probe: Mapping[str, Any], stage: str, critique: str = "") -> list[dict[str, str]]:
    persona = probe["_design"]["persona"]["shared_contract"]
    instructions = probe["_japanese_instructions"]["deliberate_instructions"]
    scratch = "内部の返答案:\n" + probe["locked_control"]["draft"]
    if stage == "revise":
        scratch += "\n\n内部の修正点:\n" + critique
        instruction = instructions[2]
    else:
        instruction = instructions[1]
    return [
        {"role": "system", "content": persona + "\n" + instruction},
        {"role": "user", "content": probe["source"]["content"]},
        {"role": "user", "content": scratch},
    ]


def build_preflight(path: str | Path) -> dict[str, Any]:
    probe = load_probe(path)
    counter = LocalOllamaQwenStageCounter(
        merge_adjacent_assistant=False, merge_adjacent_same_role=True
    )
    control_final = probe["locked_control"]["final"]
    checks = {
        "probe_valid": True,
        "model_digest_matches": _ollama_model_metadata("qwen2.5:7b")["digest"] == MODEL_DIGEST,
        "locked_control_critique_empty": probe["locked_control"]["critique"] == "",
        "locked_control_has_generic_service_escape": any(
            marker in control_final for marker in probe["treatment"]["generic_service_markers_forbidden"]
        ),
        "critique_shape_count_available": counter(_messages(probe, "critique")) > 0,
        "binding_verified_before_quality_probe": True,
        "config_does_not_self_authorize": probe["execution_boundary"]["real_model_calls_authorized_by_this_config"] is False,
    }
    return {
        "schema": "uruha_p3_private_scratch_carrier_preflight_v1", "phase": "P3-B13",
        "status": "ready_for_private_scratch_carrier_review" if all(checks.values()) else "not_ready_for_private_scratch_carrier_review",
        "probe_sha256": probe["_probe_sha256"], "checks": checks,
        "critique_offline_prompt_tokens": counter(_messages(probe, "critique")),
        "locked_control_final_sha256": probe["locked_control"]["final_sha256"],
        "real_model_calls": 0, "network_calls": 0, "paid_calls": 0,
        "developer_case_accessed": 0, "annotations_accessed": 0,
        "claim_boundary": "Preflight only; it neither executes nor grades pragmatic quality.",
    }


def validate_release(path: str | Path, probe: Mapping[str, Any]) -> dict[str, Any]:
    release_path = Path(path)
    release = _read(release_path)
    if set(release) != {
        "schema", "phase", "status", "review_kind", "probe", "implementation_sha256",
        "preflight", "authorization", "claim_boundary",
    } or release.get("schema") != RELEASE_SCHEMA:
        raise P3ContractError("p3_b13_release_schema_mismatch")
    if release.get("phase") != "P3-B13" or release.get("status") != "released_for_private_scratch_carrier_probe":
        raise P3ContractError("p3_b13_release_status_mismatch")
    if release.get("review_kind") != "same_task_self_review_not_independent":
        raise P3ContractError("p3_b13_release_review_mismatch")
    repo = release_path.resolve().parent.parent
    if release.get("probe") != {
        "path": "configs/p3_private_scratch_carrier_probe_v1.json",
        "sha256": probe["_probe_sha256"],
    }:
        raise P3ContractError("p3_b13_release_probe_mismatch")
    implementation = release.get("implementation_sha256")
    required = {"p3_private_scratch_carrier_probe.py", "test_p3_private_scratch_carrier_probe.py"}
    if not isinstance(implementation, Mapping) or set(implementation) != required:
        raise P3ContractError("p3_b13_release_implementation_invalid")
    for name, sha in implementation.items():
        if hashlib.sha256((repo / name).read_bytes()).hexdigest() != sha:
            raise P3ContractError("p3_b13_release_implementation_mismatch", name)
    preflight = release.get("preflight")
    preflight_path = (repo / str((preflight or {}).get("path"))).resolve()
    if not isinstance(preflight, Mapping) or set(preflight) != {"path", "sha256", "status"} or (
        not preflight_path.is_file()
        or hashlib.sha256(preflight_path.read_bytes()).hexdigest() != preflight.get("sha256")
        or preflight.get("status") != "ready_for_private_scratch_carrier_review"
    ):
        raise P3ContractError("p3_b13_release_preflight_mismatch")
    if release.get("authorization") != {
        "run_id": "p3-b13-private-scratch-carrier-v1", "localhost_only": True,
        "model": "qwen2.5:7b", "model_digest": MODEL_DIGEST,
        "provider_calls_exact": 2, "automatic_retry": False,
        "checkpoint_root": "analysis/p3_b13_private_scratch_carrier_checkpoints_v1",
        "result_path": "analysis/p3_b13_private_scratch_carrier_result_2026-09-15.json",
        "developer_case_access": False, "annotation_access": False,
        "confirmation_access": False, "production_database_access": False,
        "external_deployment": False,
    }:
        raise P3ContractError("p3_b13_release_authorization_mismatch")
    return release


def run_probe(probe_path: str | Path, release_path: str | Path, checkpoint_root: str | Path) -> dict[str, Any]:
    probe = load_probe(probe_path)
    release = validate_release(release_path, probe)
    repo = Path(release_path).resolve().parent.parent
    checkpoint = Path(checkpoint_root).resolve()
    if checkpoint != (repo / release["authorization"]["checkpoint_root"]).resolve():
        raise P3ContractError("p3_b13_checkpoint_path_mismatch")
    if _ollama_model_metadata("qwen2.5:7b")["digest"] != MODEL_DIGEST:
        raise P3ContractError("p3_b13_runtime_model_mismatch")
    design = probe["_design"]
    budget = new_budget(design, "full_history_deliberate")
    counter = LocalOllamaQwenStageCounter(
        merge_adjacent_assistant=False, merge_adjacent_same_role=True
    )
    transport_config = {
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
    transport = _local_canary_baseline_transport(transport_config)
    calls = []
    started = time.monotonic()
    with localhost_network_only() as attempts:
        critique_messages = _messages(probe, "critique")
        critique = run_call_once(
            budget=budget,
            request=make_request(
                design=design, condition="full_history_deliberate", stage="critique",
                messages=critique_messages, prompt_tokens=counter(critique_messages),
                max_completion_tokens=256, backend="openai_compatible_local",
            ),
            transport=transport, checkpoint_root=checkpoint,
            item_id="p3-b13-private-scratch-carrier",
        )
        calls.append({"stage": "critique", **critique})
        revise_messages = _messages(probe, "revise", critique["content"])
        final = run_call_once(
            budget=budget,
            request=make_request(
                design=design, condition="full_history_deliberate", stage="revise",
                messages=revise_messages, prompt_tokens=counter(revise_messages),
                max_completion_tokens=256, backend="openai_compatible_local",
            ),
            transport=transport, checkpoint_root=checkpoint,
            item_id="p3-b13-private-scratch-carrier",
        )
        calls.append({"stage": "revise", **final})
    record_condition_wall(budget, time.monotonic() - started)
    final_text = final["content"]
    surface = shared_visible_surface_contract(final_text)
    treatment_checks = {
        "critique_nonempty": bool(critique["content"].strip()),
        "final_shared_surface_pass": all(surface.values()),
        "final_preserves_uncertainty_anchor": any(
            marker in final_text for marker in probe["treatment"]["uncertainty_anchors_any"]
        ),
        "final_has_no_generic_service_escape": not any(
            marker in final_text for marker in probe["treatment"]["generic_service_markers_forbidden"]
        ),
        "final_has_no_polite_register": not any(
            marker in final_text for marker in probe["treatment"]["polite_register_markers_forbidden"]
        ),
    }
    control_pass = bool(probe["locked_control"]["critique"].strip()) and not any(
        marker in probe["locked_control"]["final"]
        for marker in probe["treatment"]["generic_service_markers_forbidden"]
    )
    checks = {
        **treatment_checks,
        "treatment_passes_while_locked_control_fails": all(treatment_checks.values()) and not control_pass,
        "two_provider_calls_exact": len(calls) == 2 and all(not call["reused"] for call in calls),
        "provider_prompt_usage_exact": all(
            call["usage"]["prompt_tokens"] > 0 for call in calls
        ),
        "localhost_only": all(row["loopback_allowed"] is True for row in attempts),
    }
    passed = all(checks.values())
    return {
        "schema": "uruha_p3_private_scratch_carrier_result_v1", "phase": "P3-B13",
        "status": "private_scratch_carrier_pass" if passed else "private_scratch_carrier_failed_retained",
        "probe_sha256": probe["_probe_sha256"],
        "release_sha256": hashlib.sha256(Path(release_path).read_bytes()).hexdigest(),
        "source_sha256": probe["source"]["content_sha256"],
        "locked_control": probe["locked_control"],
        "treatment": {"critique": critique["content"], "final": final_text, "calls": calls},
        "surface_contract": surface, "checks": checks, "budget": budget.snapshot(),
        "provider_call_evidence": sum(call["real_model_calls"] for call in calls),
        "real_model_calls": sum(call["real_model_calls"] for call in calls),
        "network_calls": sum(call["network_calls"] for call in calls),
        "network_attempts": attempts, "paid_calls": 0,
        "developer_case_accessed": 0, "annotations_accessed": 0,
        "confirmation_accessed": 0, "production_database_accessed": False,
        "claim_boundary": "A pass shows a causal mechanism improvement on one synthetic locked-draft probe only. It is not product, holdout, human-preference, or general understanding evidence.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("preflight", "run"), required=True)
    parser.add_argument("--probe", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--release")
    parser.add_argument("--checkpoint-root")
    args = parser.parse_args()
    output = Path(args.output)
    if output.exists():
        return 2
    try:
        if args.mode == "preflight":
            payload = build_preflight(args.probe)
        else:
            if not args.release or not args.checkpoint_root:
                raise P3ContractError("p3_b13_run_artifacts_required")
            release = _read(Path(args.release))
            repo = Path(args.release).resolve().parent.parent
            if output.resolve() != (repo / release["authorization"]["result_path"]).resolve():
                raise P3ContractError("p3_b13_result_path_mismatch")
            payload = run_probe(args.probe, args.release, args.checkpoint_root)
    except P3ContractError as exc:
        evidence = summarize_checkpoint_evidence(args.checkpoint_root or "")
        payload = {
            "schema": "uruha_p3_private_scratch_carrier_failure_v1", "phase": "P3-B13",
            "status": "failed_after_transport_retained" if evidence["declared_invocation_intents"] else "refused_before_transport",
            "contract_code": exc.code, "checkpoint_evidence": evidence,
            "real_model_calls": evidence["provider_call_evidence"],
            "network_calls": evidence["network_call_evidence"], "paid_calls": 0,
        }
    write_new_json(output, payload)
    return 0 if payload.get("status") in {"ready_for_private_scratch_carrier_review", "private_scratch_carrier_pass"} else 3


if __name__ == "__main__":
    raise SystemExit(main())
