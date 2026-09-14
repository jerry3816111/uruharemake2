#!/usr/bin/env python3
"""P3-B11 one-shot instruction-language isolation probe.

The probe uses a synthetic English input that is not part of any developer or
holdout dataset. It changes only the language of the baseline stage
instructions. No annotation or product state is loaded.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from p3_product_comparison import (
    P3ContractError,
    canonical_sha256,
    load_design,
    shared_visible_surface_contract,
    write_new_json,
)
from p3_product_worker import (
    LocalOllamaQwenStageCounter,
    _local_canary_baseline_transport,
    _ollama_model_metadata,
    execute_canary_baselines,
    localhost_network_only,
    summarize_checkpoint_evidence,
)


ROOT = Path(__file__).resolve().parent
PROBE_SCHEMA = "uruha_p3_baseline_instruction_language_probe_v1"
RELEASE_SCHEMA = "uruha_p3_baseline_instruction_language_probe_release_v1"
ARMS = ("english_instructions", "japanese_instructions")
CONDITIONS = ("full_history_direct", "full_history_deliberate")
EXPECTED_DESIGN = {
    "path": "configs/p3_product_comparison_v1.json",
    "sha256": "1e6d3b0600740b3dee7207ffc5c4f9cc9247a5feba2b967bdab4586522f7b836",
}
EXPECTED_BINDING = {
    "path": "analysis/p3_b8_1_stage_tokenizer_binding_confirmation_result_2026-09-15.json",
    "sha256": "e360e626931d40ff52f5a217131541701a1eb69831fa3b249214dbb4fed5774f",
    "required_status": "stage_provider_binding_pass",
}
EXPECTED_SOURCE = {
    "source_id": "p3-b11-synthetic-en-001",
    "case_id": "p3-b11-synthetic-instruction-language",
    "turn_id": "p3-b11-synthetic-u1",
    "session_id": "p3-b11-synthetic-s1",
    "language": "en",
    "content": "A neighbor asked whether I can join a crowded weekend cleanup. I said I have not decided yet.",
    "content_sha256": "d9ca3ce2a80bd1482f6e9b57328ed9a3ce07e104e5a08613f51034f288c22502",
    "visible_prefix": [],
    "developer_case_source": False,
    "annotations_exist": False,
}


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise P3ContractError("p3_b11_invalid_json", str(path)) from exc
    if not isinstance(value, dict):
        raise P3ContractError("p3_b11_invalid_json", str(path))
    return value


def _verify_ref(repo: Path, value: Any, expected: Mapping[str, Any], code: str) -> Path:
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
    probe = _read_json(probe_path)
    expected_keys = {
        "schema", "status", "purpose", "comparison_design",
        "stage_tokenizer_binding", "source", "arms", "generation",
        "transport", "execution_boundary", "success",
    }
    if set(probe) != expected_keys or probe.get("schema") != PROBE_SCHEMA:
        raise P3ContractError("p3_b11_probe_schema_mismatch")
    if probe.get("status") != "preregistered_not_executed" or probe.get("purpose") != (
        "isolate_baseline_instruction_language_effect_on_shared_japanese_surface"
    ):
        raise P3ContractError("p3_b11_probe_status_mismatch")
    repo = probe_path.resolve().parent.parent
    design_path = _verify_ref(
        repo, probe.get("comparison_design"), EXPECTED_DESIGN,
        "p3_b11_design_reference_mismatch",
    )
    binding_path = _verify_ref(
        repo, probe.get("stage_tokenizer_binding"), EXPECTED_BINDING,
        "p3_b11_binding_reference_mismatch",
    )
    binding = _read_json(binding_path)
    if binding.get("status") != "stage_provider_binding_pass" or binding.get("binding_verified") is not True:
        raise P3ContractError("p3_b11_binding_not_verified")
    if probe.get("source") != EXPECTED_SOURCE or canonical_sha256(EXPECTED_SOURCE["content"]) != EXPECTED_SOURCE["content_sha256"]:
        raise P3ContractError("p3_b11_source_mismatch")
    design = load_design(design_path)
    arms = probe.get("arms")
    if not isinstance(arms, Mapping) or tuple(arms) != ARMS:
        raise P3ContractError("p3_b11_arm_set_mismatch")
    if arms["english_instructions"] != design["baselines"]:
        raise P3ContractError("p3_b11_english_arm_drift")
    for arm in ARMS:
        value = arms[arm]
        if not isinstance(value, Mapping) or set(value) != {
            "direct_instruction", "deliberate_instructions"
        }:
            raise P3ContractError("p3_b11_arm_shape_mismatch", arm)
        if not isinstance(value["direct_instruction"], str) or not value["direct_instruction"].strip():
            raise P3ContractError("p3_b11_arm_instruction_invalid", arm)
        deliberate = value["deliberate_instructions"]
        if not isinstance(deliberate, list) or len(deliberate) != 3 or not all(
            isinstance(item, str) and item.strip() for item in deliberate
        ):
            raise P3ContractError("p3_b11_arm_instruction_invalid", arm)
    if probe.get("generation") != {
        "model": "qwen2.5:7b",
        "digest": "2bada8a7450677000f678be90653b85d364de7db25eb5ea54136ada5f3933730",
        "temperature": 0,
        "seed": 20260909,
        "top_p": 1,
        "num_ctx": 8192,
        "think": False,
        "direct_completion_cap": 768,
        "deliberate_completion_caps": [256, 256, 256],
    }:
        raise P3ContractError("p3_b11_generation_mismatch")
    if probe.get("transport") != {
        "backend": "openai_compatible_local",
        "url": "http://127.0.0.1:11434/v1/chat/completions",
        "per_call_timeout_seconds": 60,
    }:
        raise P3ContractError("p3_b11_transport_mismatch")
    if probe.get("execution_boundary") != {
        "provider_calls_exact": 8,
        "calls_per_arm_exact": 4,
        "automatic_retry": False,
        "concurrency": 1,
        "localhost_only": True,
        "developer_case_access": False,
        "annotation_access": False,
        "confirmation_access": False,
        "production_database_access": False,
        "external_deployment": False,
        "remote_paid_calls": False,
        "real_model_calls_authorized_by_this_config": False,
    }:
        raise P3ContractError("p3_b11_execution_boundary_mismatch")
    if probe.get("success") != {
        "all_eight_calls_exact": True,
        "both_arms_have_direct_and_deliberate_finals": True,
        "japanese_instruction_surface_pass_count_greater_than_english": True,
        "all_outputs_and_failures_retained": True,
    }:
        raise P3ContractError("p3_b11_success_mismatch")
    frozen = deepcopy(probe)
    frozen["_probe_sha256"] = hashlib.sha256(probe_path.read_bytes()).hexdigest()
    frozen["_probe_path"] = str(probe_path.resolve())
    frozen["_design"] = design
    return frozen


def _arm_config(probe: Mapping[str, Any], arm: str) -> dict[str, Any]:
    design = deepcopy(probe["_design"])
    design["baselines"] = deepcopy(probe["arms"][arm])
    return {
        "_canary": {"_source": deepcopy(probe["source"])},
        "_design": design,
        "_config_sha256": canonical_sha256({"probe": probe["_probe_sha256"], "arm": arm}),
        "_phase": "P3-B11",
        "conditions": list(CONDITIONS),
        "generation": deepcopy(probe["generation"]),
        "transport": deepcopy(probe["transport"]),
        "execution_boundary": {
            "provider_calls_exact": probe["execution_boundary"]["calls_per_arm_exact"]
        },
    }


def build_preflight(path: str | Path) -> dict[str, Any]:
    probe = load_probe(path)
    metadata = _ollama_model_metadata(probe["generation"]["model"])
    counter = LocalOllamaQwenStageCounter(merge_adjacent_assistant=True)
    source = probe["source"]
    prompt_counts = {}
    for arm in ARMS:
        design = _arm_config(probe, arm)["_design"]
        persona = design["persona"]["shared_contract"]
        prompt_counts[arm] = {
            "direct": counter([
                {"role": "system", "content": persona + "\n" + design["baselines"]["direct_instruction"]},
                {"role": "user", "content": source["content"]},
            ]),
            "draft": counter([
                {"role": "system", "content": persona + "\n" + design["baselines"]["deliberate_instructions"][0]},
                {"role": "user", "content": source["content"]},
            ]),
        }
    checks = {
        "probe_valid": True,
        "model_digest_matches": metadata["digest"] == probe["generation"]["digest"],
        "source_is_synthetic_not_developer_case": source["developer_case_source"] is False,
        "annotations_do_not_exist_for_source": source["annotations_exist"] is False,
        "english_arm_matches_frozen_v1": probe["arms"]["english_instructions"] == probe["_design"]["baselines"],
        "instruction_text_is_only_planned_difference": all(
            prompt_counts[arm][stage] > 0 for arm in ARMS for stage in ("direct", "draft")
        ),
        "config_does_not_self_authorize": probe["execution_boundary"]["real_model_calls_authorized_by_this_config"] is False,
    }
    return {
        "schema": "uruha_p3_baseline_instruction_language_probe_preflight_v1",
        "phase": "P3-B11",
        "status": "ready_for_instruction_language_probe_review" if all(checks.values()) else "not_ready_for_instruction_language_probe_review",
        "probe_sha256": probe["_probe_sha256"],
        "source_sha256": source["content_sha256"],
        "offline_prompt_counts": prompt_counts,
        "model_metadata": metadata,
        "checks": checks,
        "real_model_calls": 0,
        "network_calls": 0,
        "paid_calls": 0,
        "developer_case_accessed": 0,
        "annotations_accessed": 0,
        "claim_boundary": "Preflight only. It does not authorize generation or test pragmatic quality.",
    }


def validate_release(path: str | Path, probe: Mapping[str, Any]) -> dict[str, Any]:
    release_path = Path(path)
    release = _read_json(release_path)
    if set(release) != {
        "schema", "phase", "status", "review_kind", "probe",
        "implementation_sha256", "preflight", "authorization", "claim_boundary",
    } or release.get("schema") != RELEASE_SCHEMA:
        raise P3ContractError("p3_b11_release_schema_mismatch")
    if release.get("phase") != "P3-B11" or release.get("status") != "released_for_single_instruction_language_probe":
        raise P3ContractError("p3_b11_release_status_mismatch")
    if release.get("review_kind") != "same_task_self_review_not_independent":
        raise P3ContractError("p3_b11_release_review_mismatch")
    repo = release_path.resolve().parent.parent
    if release.get("probe") != {
        "path": "configs/p3_baseline_instruction_language_probe_v1.json",
        "sha256": probe["_probe_sha256"],
    }:
        raise P3ContractError("p3_b11_release_probe_mismatch")
    implementation = release.get("implementation_sha256")
    required = {
        "p3_product_comparison.py", "p3_product_worker.py",
        "p3_baseline_instruction_language_probe.py",
        "test_p3_baseline_instruction_language_probe.py",
    }
    if not isinstance(implementation, Mapping) or set(implementation) != required:
        raise P3ContractError("p3_b11_release_implementation_invalid")
    for name, sha in implementation.items():
        if hashlib.sha256((repo / name).read_bytes()).hexdigest() != sha:
            raise P3ContractError("p3_b11_release_implementation_mismatch", name)
    preflight = release.get("preflight")
    preflight_path = (repo / str((preflight or {}).get("path"))).resolve()
    if not isinstance(preflight, Mapping) or set(preflight) != {"path", "sha256", "status"} or (
        not preflight_path.is_file()
        or hashlib.sha256(preflight_path.read_bytes()).hexdigest() != preflight.get("sha256")
        or preflight.get("status") != "ready_for_instruction_language_probe_review"
    ):
        raise P3ContractError("p3_b11_release_preflight_mismatch")
    if release.get("authorization") != {
        "run_id": "p3-b11-instruction-language-probe-v1",
        "localhost_only": True,
        "model": "qwen2.5:7b",
        "model_digest": "2bada8a7450677000f678be90653b85d364de7db25eb5ea54136ada5f3933730",
        "provider_calls_exact": 8,
        "automatic_retry": False,
        "checkpoint_root": "analysis/p3_b11_instruction_language_probe_checkpoints_v1",
        "result_path": "analysis/p3_b11_instruction_language_probe_result_2026-09-15.json",
        "developer_case_access": False,
        "annotation_access": False,
        "confirmation_access": False,
        "production_database_access": False,
        "external_deployment": False,
    }:
        raise P3ContractError("p3_b11_release_authorization_mismatch")
    return release


def run_probe(probe_path: str | Path, release_path: str | Path, checkpoint_root: str | Path) -> dict[str, Any]:
    probe = load_probe(probe_path)
    release = validate_release(release_path, probe)
    repo = Path(release_path).resolve().parent.parent
    checkpoint = Path(checkpoint_root).resolve()
    if checkpoint != (repo / release["authorization"]["checkpoint_root"]).resolve():
        raise P3ContractError("p3_b11_checkpoint_path_mismatch")
    metadata = _ollama_model_metadata(probe["generation"]["model"])
    if metadata["digest"] != probe["generation"]["digest"]:
        raise P3ContractError("p3_b11_runtime_model_digest_mismatch")
    counter = LocalOllamaQwenStageCounter(merge_adjacent_assistant=True)
    arm_results = {}
    with localhost_network_only() as network_attempts:
        for arm in ARMS:
            config = _arm_config(probe, arm)
            arm_results[arm] = execute_canary_baselines(
                config=config,
                token_counter=counter,
                transport=_local_canary_baseline_transport(config),
                checkpoint_root=checkpoint / arm,
                evidence_kind="local_ollama_provider_usage",
            )
    surface = {}
    for arm, result in arm_results.items():
        surface[arm] = {
            name: shared_visible_surface_contract(result["conditions"][name]["final"]["content"])
            for name in CONDITIONS
        }
    pass_counts = {
        arm: sum(all(row.values()) for row in audits.values())
        for arm, audits in surface.items()
    }
    total_calls = sum(result["provider_call_evidence"] for result in arm_results.values())
    checks = {
        "all_eight_calls_exact": total_calls == 8 and all(
            result["checks"]["provider_prompt_usage_exact"]
            and result["checks"]["provider_calls_exact"]
            and result["checks"]["each_condition_budget_valid"]
            for result in arm_results.values()
        ),
        "both_arms_have_direct_and_deliberate_finals": all(
            all(bool(result["conditions"][name]["final"]["content"].strip()) for name in CONDITIONS)
            for result in arm_results.values()
        ),
        "japanese_instruction_surface_pass_count_greater_than_english": (
            pass_counts["japanese_instructions"] > pass_counts["english_instructions"]
        ),
        "localhost_only": all(row["loopback_allowed"] is True for row in network_attempts),
        "no_developer_or_annotation_access": True,
    }
    return {
        "schema": "uruha_p3_baseline_instruction_language_probe_result_v1",
        "phase": "P3-B11",
        "status": "instruction_language_probe_pass" if all(checks.values()) else "instruction_language_probe_failed_retained",
        "probe_sha256": probe["_probe_sha256"],
        "release_sha256": hashlib.sha256(Path(release_path).read_bytes()).hexdigest(),
        "source": deepcopy(probe["source"]),
        "arms": arm_results,
        "surface_contracts": surface,
        "surface_pass_counts": pass_counts,
        "checks": checks,
        "provider_call_evidence": total_calls,
        "real_model_calls": sum(result["real_model_calls"] for result in arm_results.values()),
        "network_calls": sum(result["network_calls"] for result in arm_results.values()),
        "network_attempts": network_attempts,
        "paid_calls": 0,
        "developer_case_accessed": 0,
        "annotations_accessed": 0,
        "confirmation_accessed": 0,
        "production_database_accessed": False,
        "claim_boundary": "A pass attributes an obvious Japanese surface difference to instruction language on one synthetic input only. It is not pragmatic-quality, product-advantage, holdout, or human-preference evidence.",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("preflight", "run"), required=True)
    parser.add_argument("--probe", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--release")
    parser.add_argument("--checkpoint-root")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output = Path(args.output)
    if output.exists():
        return 2
    try:
        if args.mode == "preflight":
            payload = build_preflight(args.probe)
        else:
            if not args.release or not args.checkpoint_root:
                raise P3ContractError("p3_b11_run_artifacts_required")
            release = _read_json(Path(args.release))
            repo = Path(args.release).resolve().parent.parent
            expected_output = (repo / str((release.get("authorization") or {}).get("result_path"))).resolve()
            if output.resolve() != expected_output:
                raise P3ContractError("p3_b11_result_path_mismatch")
            payload = run_probe(args.probe, args.release, args.checkpoint_root)
    except P3ContractError as exc:
        evidence = summarize_checkpoint_evidence(args.checkpoint_root or "")
        payload = {
            "schema": "uruha_p3_baseline_instruction_language_probe_failure_v1",
            "phase": "P3-B11",
            "status": "failed_after_transport_retained" if evidence["declared_invocation_intents"] else "refused_before_transport",
            "contract_code": exc.code,
            "checkpoint_evidence": evidence,
            "real_model_calls": evidence["provider_call_evidence"],
            "network_calls": evidence["network_call_evidence"],
            "paid_calls": 0,
        }
    write_new_json(output, payload)
    return 0 if payload.get("status") in {
        "ready_for_instruction_language_probe_review",
        "instruction_language_probe_pass",
    } else 3


if __name__ == "__main__":
    raise SystemExit(main())
