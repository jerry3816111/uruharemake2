#!/usr/bin/env python3
"""Run the preregistered legacy versus compact RightBrain payload experiment."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from pathlib import Path

import torch

import persona_policy_local_model_pilot_v1 as pilot
import rightbrain_adapter_causality_diagnostic_v1 as diagnostic
import uruha_brain_mac as brain_module
import uruha_compute_ledger as ledger_module
import uruha_persona_policy as persona_policy
import uruha_surface_payload_v2 as surface_payload


ROOT = Path(__file__).resolve().parent
EXPERIMENT_ID = "rightbrain_compact_japanese_payload_v1"
SERIALIZERS = (
    surface_payload.LEGACY_JSON_V1,
    surface_payload.COMPACT_JAPANESE_V2,
)
DEFAULT_PREREGISTRATION = ROOT / "configs/rightbrain_compact_japanese_payload_v1_preregistration.json"
DEFAULT_CONSTRUCTION = ROOT / "reports/rightbrain_compact_japanese_payload_v1_construction.json"
DEFAULT_CASES = ROOT / "configs/persona_policy_local_model_pilot_v1_cases.json"
DEFAULT_LEGACY_ARTIFACT = ROOT / "reports/rightbrain_compact_japanese_payload_v1_legacy_condition.json"
DEFAULT_COMPACT_ARTIFACT = ROOT / "reports/rightbrain_compact_japanese_payload_v1_compact_condition.json"
DEFAULT_REPORT_JSON = ROOT / "reports/rightbrain_compact_japanese_payload_v1_result.json"
DEFAULT_REPORT_MD = ROOT / "reports/rightbrain_compact_japanese_payload_v1_result.md"


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def sha256_text(value):
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()


def binding(path):
    path = Path(path).resolve()
    return {"path": str(path.relative_to(ROOT)), "sha256": sha256_file(path)}


def _load_base_rightbrain(serializer_id, ledger):
    original_adapter_path = brain_module.RIGHT_BRAIN_ADAPTER_PATH
    brain_module.RIGHT_BRAIN_ADAPTER_PATH = ""
    started = time.perf_counter()
    try:
        rightbrain = brain_module.RightBrain(
            load_model=True,
            persona_policy_provider=persona_policy.build_persona_policy_provider(
                persona_policy.TARGET_PROVIDER
            ),
            compute_ledger=ledger,
        )
    finally:
        brain_module.RIGHT_BRAIN_ADAPTER_PATH = original_adapter_path
    rightbrain.structured_payload_mode = surface_payload.normalize_mode(serializer_id)
    rightbrain.model_candidate_count = 1
    rightbrain.model_repair_enabled = False
    rightbrain.model_blend_enabled = False
    rightbrain.structured_prompt_token_budget = 640
    return rightbrain, round(time.perf_counter() - started, 4)


def _condition_checks(rightbrain, serializer_id, rows, snapshots, summary, offline):
    calls = [
        call
        for snapshot in snapshots.values()
        for call in snapshot["calls"]
    ]
    return {
        "offline_local_inference": offline,
        "generation_count": len(rows) == 10,
        "nonempty_raw_generation_count": sum(bool(row["raw_generation"]) for row in rows)
        == 10,
        "target_neutral_compute_parity": summary["compute_parity"]["parity_pass"],
        "allocated_prompt_tokens_each": all(
            (call.get("response") or {}).get("prompt_tokens") == 640
            for call in calls
        ),
        "serializer_mode_exact": rightbrain.structured_payload_mode == serializer_id,
        "base_model_only": (
            rightbrain.compat_adapter_dir is None
            and not rightbrain._active_model_adapter_name
        ),
        "legacy_surface_not_accessed": rightbrain.legacy_fixed_surface_access_count
        == 0,
        "ledger_contains_no_raw_text": not summary["ledger_contains_raw_text"],
    }


def run_condition(preregistration, construction, case_bundle, serializer_id):
    offline = (
        os.getenv("HF_HUB_OFFLINE") == "1"
        and os.getenv("TRANSFORMERS_OFFLINE") == "1"
    )
    if not offline:
        raise RuntimeError("formal condition run requires offline Hugging Face mode")
    if serializer_id not in SERIALIZERS:
        raise ValueError(f"unknown serializer: {serializer_id}")
    if construction.get("status") != "construction_passed":
        raise RuntimeError("serializer construction has not passed")
    if brain_module.RIGHT_BRAIN_BASE_MODEL != preregistration["frozen_model_and_runtime"][
        "base_model"
    ]:
        raise RuntimeError("base model differs from preregistration")

    ledgers = {
        provider_id: ledger_module.ComputeLedger()
        for provider_id in pilot.PROVIDERS
    }
    rightbrain, load_seconds = _load_base_rightbrain(
        serializer_id,
        ledgers[persona_policy.TARGET_PROVIDER],
    )
    rows = []
    for case in case_bundle["cases"]:
        for provider_id in case["condition_order"]:
            row = pilot._run_one(
                rightbrain,
                provider_id,
                ledgers[provider_id],
                case,
            )
            row["serializer_id"] = serializer_id
            rows.append(row)
            if torch.backends.mps.is_available():
                torch.mps.synchronize()

    snapshots = {
        provider_id: ledger.snapshot()
        for provider_id, ledger in ledgers.items()
    }
    summary = diagnostic._model_summary(
        rows,
        ledgers[persona_policy.TARGET_PROVIDER],
        ledgers[persona_policy.NEUTRAL_PROVIDER],
    )
    checks = _condition_checks(
        rightbrain,
        serializer_id,
        rows,
        snapshots,
        summary,
        offline,
    )
    return {
        "schema": "uruha_rightbrain_payload_serializer_condition_v1",
        "experiment_id": EXPERIMENT_ID,
        "serializer_id": serializer_id,
        "status": "condition_complete" if all(checks.values()) else "condition_invalid",
        "inputs": {
            "preregistration": binding(DEFAULT_PREREGISTRATION),
            "construction": binding(DEFAULT_CONSTRUCTION),
            "cases": binding(DEFAULT_CASES),
            "harness": binding(ROOT / "run_rightbrain_compact_japanese_payload_v1.py"),
            "brain_source": binding(ROOT / "uruha_brain_mac.py"),
            "serializer_source": binding(ROOT / "uruha_surface_payload_v2.py"),
            "base_cache_commit": diagnostic._base_cache_commit(),
        },
        "runtime": {
            "device": rightbrain.device,
            "dtype": str(rightbrain.dtype),
            "load_seconds": load_seconds,
            "generation_seconds": round(
                sum(row["duration_seconds"] for row in rows),
                4,
            ),
            "fresh_process_required": True,
        },
        "model_state": {
            "base_model": brain_module.RIGHT_BRAIN_BASE_MODEL,
            "adapter_loaded": rightbrain.compat_adapter_dir is not None,
            "active_adapter_name": rightbrain._active_model_adapter_name or "",
        },
        "serializer": {
            "id": serializer_id,
            "system_instruction_sha256": sha256_text(
                rightbrain._model_surface_system_instruction()
            ),
        },
        "checks": checks,
        "summary": summary,
        "ledger_snapshots": snapshots,
        "legacy_fixed_surface_access_count": rightbrain.legacy_fixed_surface_access_count,
        "generations": rows,
        "production_memory_write_count": 0,
        "formal_persona_score_count": 0,
    }


def _validate_condition_artifact(artifact, serializer_id):
    return bool(
        artifact.get("experiment_id") == EXPERIMENT_ID
        and artifact.get("serializer_id") == serializer_id
        and artifact.get("status") == "condition_complete"
        and all((artifact.get("checks") or {}).values())
        and (artifact.get("inputs") or {}).get("preregistration")
        == binding(DEFAULT_PREREGISTRATION)
        and (artifact.get("inputs") or {}).get("construction")
        == binding(DEFAULT_CONSTRUCTION)
        and (artifact.get("inputs") or {}).get("cases") == binding(DEFAULT_CASES)
        and (artifact.get("inputs") or {}).get("harness")
        == binding(ROOT / "run_rightbrain_compact_japanese_payload_v1.py")
        and (artifact.get("inputs") or {}).get("brain_source")
        == binding(ROOT / "uruha_brain_mac.py")
        and (artifact.get("inputs") or {}).get("serializer_source")
        == binding(ROOT / "uruha_surface_payload_v2.py")
    )


def _normalized_call(call):
    request = call.get("request") or {}
    response = call.get("response") or {}
    allocation = request.get("allocation") or {}
    return {
        "item_id": call.get("item_id"),
        "condition_id": call.get("condition_id"),
        "stage": call.get("stage"),
        "backend": call.get("backend"),
        "model": call.get("model"),
        "options": request.get("options") or {},
        "allocated_prompt_tokens": allocation.get("allocated_prompt_tokens"),
        "response_prompt_tokens": response.get("prompt_tokens"),
        "prompt_sha256": request.get("prompt_sha256"),
        "active_prompt_tokens": allocation.get("active_prompt_tokens"),
    }


def _cross_serializer_control_checks(artifacts):
    rows = []
    for provider_id in pilot.PROVIDERS:
        legacy_calls = [
            _normalized_call(call)
            for call in artifacts[surface_payload.LEGACY_JSON_V1]["ledger_snapshots"][
                provider_id
            ]["calls"]
        ]
        compact_calls = [
            _normalized_call(call)
            for call in artifacts[surface_payload.COMPACT_JAPANESE_V2]["ledger_snapshots"][
                provider_id
            ]["calls"]
        ]
        controls_equal = len(legacy_calls) == len(compact_calls) and all(
            {
                key: value
                for key, value in legacy.items()
                if key not in {"prompt_sha256", "active_prompt_tokens"}
            }
            == {
                key: value
                for key, value in compact.items()
                if key not in {"prompt_sha256", "active_prompt_tokens"}
            }
            for legacy, compact in zip(legacy_calls, compact_calls, strict=True)
        )
        prompt_difference_exact = all(
            legacy["prompt_sha256"] != compact["prompt_sha256"]
            for legacy, compact in zip(legacy_calls, compact_calls, strict=True)
        )
        active_tokens_reduced = all(
            compact["active_prompt_tokens"] < legacy["active_prompt_tokens"]
            for legacy, compact in zip(legacy_calls, compact_calls, strict=True)
        )
        rows.append(
            {
                "provider_id": provider_id,
                "controls_equal_except_serialization": controls_equal,
                "prompt_hash_difference_exact": prompt_difference_exact,
                "compact_active_tokens_lower_each": active_tokens_reduced,
                "legacy_active_prompt_tokens": [
                    call["active_prompt_tokens"] for call in legacy_calls
                ],
                "compact_active_prompt_tokens": [
                    call["active_prompt_tokens"] for call in compact_calls
                ],
            }
        )
    return rows


def classify_result(legacy_summary, compact_summary):
    legacy_valid = legacy_summary["strict_valid_generation_count"]
    compact_valid = compact_summary["strict_valid_generation_count"]
    delta = compact_valid - legacy_valid
    legacy_reasons = legacy_summary["rejection_families"]
    compact_reasons = compact_summary["rejection_families"]
    supported = (
        compact_valid >= 5
        and delta >= 3
        and compact_reasons.get("language_or_script_pollution", 0)
        <= legacy_reasons.get("language_or_script_pollution", 0) - 2
        and compact_reasons.get("required_semantics_missing", 0)
        <= legacy_reasons.get("required_semantics_missing", 0) - 3
    )
    if supported:
        return "compact_payload_supported"
    if delta < 0:
        return "compact_payload_regression"
    if delta >= 2:
        return "compact_payload_partial_gain"
    return "compact_payload_no_gain"


def build_report(preregistration, artifacts):
    summaries = {
        serializer_id: artifacts[serializer_id]["summary"]
        for serializer_id in SERIALIZERS
    }
    artifact_validity = {
        serializer_id: _validate_condition_artifact(
            artifacts[serializer_id],
            serializer_id,
        )
        for serializer_id in SERIALIZERS
    }
    cross_checks = _cross_serializer_control_checks(artifacts)
    all_rows = [
        row
        for serializer_id in SERIALIZERS
        for row in artifacts[serializer_id]["generations"]
    ]
    required = preregistration["valid_experiment_requires"]
    counts = {
        "model_load_count": 2,
        "actual_generation_count": len(all_rows),
        "nonempty_raw_generation_count": sum(
            bool(row["raw_generation"]) for row in all_rows
        ),
        "legacy_fixed_surface_access_count": sum(
            artifacts[serializer_id]["legacy_fixed_surface_access_count"]
            for serializer_id in SERIALIZERS
        ),
        "production_memory_write_count": 0,
        "formal_persona_score_count": 0,
    }
    checks = {
        "condition_artifacts_valid": all(artifact_validity.values()),
        "model_load_count": counts["model_load_count"]
        == required["model_load_count_exact"],
        "actual_generation_count": counts["actual_generation_count"]
        == required["actual_generation_count_exact"],
        "nonempty_raw_generation_count": counts["nonempty_raw_generation_count"]
        == required["nonempty_raw_generation_count_exact"],
        "within_serializer_target_neutral_compute_parity": all(
            summaries[serializer_id]["compute_parity"]["parity_pass"]
            for serializer_id in SERIALIZERS
        )
        is required["within_serializer_target_neutral_compute_parity"],
        "cross_serializer_controls_equal_except_serialization": all(
            row["controls_equal_except_serialization"]
            and row["prompt_hash_difference_exact"]
            and row["compact_active_tokens_lower_each"]
            for row in cross_checks
        )
        is required["cross_serializer_controls_equal_except_serialization"],
        "allocated_prompt_tokens_each": all(
            (call.get("response") or {}).get("prompt_tokens")
            == required["allocated_prompt_tokens_each_exact"]
            for serializer_id in SERIALIZERS
            for snapshot in artifacts[serializer_id]["ledger_snapshots"].values()
            for call in snapshot["calls"]
        ),
        "legacy_surface_not_accessed": counts["legacy_fixed_surface_access_count"]
        == required["legacy_fixed_surface_access_count_exact"],
        "production_memory_unchanged": counts["production_memory_write_count"]
        == required["production_memory_write_count_exact"],
        "no_formal_persona_score": counts["formal_persona_score_count"]
        == required["formal_persona_score_count_exact"],
        "base_model_only_both": all(
            not artifacts[serializer_id]["model_state"]["adapter_loaded"]
            and not artifacts[serializer_id]["model_state"]["active_adapter_name"]
            for serializer_id in SERIALIZERS
        ),
    }
    valid = all(checks.values())
    classification = (
        classify_result(
            summaries[surface_payload.LEGACY_JSON_V1],
            summaries[surface_payload.COMPACT_JAPANESE_V2],
        )
        if valid
        else "uninterpretable_control_failure"
    )
    decision = (
        preregistration["decision_boundary"][classification]
        if valid
        else "repair_experiment_controls_before_interpretation"
    )
    legacy_valid = summaries[surface_payload.LEGACY_JSON_V1][
        "strict_valid_generation_count"
    ]
    compact_valid = summaries[surface_payload.COMPACT_JAPANESE_V2][
        "strict_valid_generation_count"
    ]
    return {
        "schema": "uruha_rightbrain_compact_japanese_payload_result_v1",
        "experiment_id": EXPERIMENT_ID,
        "status": "valid_experiment" if valid else "invalid_experiment",
        "classification": classification,
        "decision": decision,
        "inputs": {
            "preregistration": binding(DEFAULT_PREREGISTRATION),
            "construction": binding(DEFAULT_CONSTRUCTION),
            "cases": binding(DEFAULT_CASES),
            "condition_artifacts": {
                surface_payload.LEGACY_JSON_V1: binding(DEFAULT_LEGACY_ARTIFACT),
                surface_payload.COMPACT_JAPANESE_V2: binding(DEFAULT_COMPACT_ARTIFACT),
            },
            "base_model": brain_module.RIGHT_BRAIN_BASE_MODEL,
            "base_cache_commit": diagnostic._base_cache_commit(),
        },
        "runtime": {
            serializer_id: artifacts[serializer_id]["runtime"]
            for serializer_id in SERIALIZERS
        },
        "counts": counts,
        "checks": checks,
        "artifact_validity": artifact_validity,
        "cross_serializer_control_checks": cross_checks,
        "condition_summaries": summaries,
        "strict_valid_delta_compact_minus_legacy": compact_valid - legacy_valid,
        "generations": all_rows,
        "authorizations": {
            "merge_experiment_evidence": valid,
            "disjoint_open_ended_surface_carrier_holdout": valid
            and classification == "compact_payload_supported",
            "repair_compact_serializer_on_development_cases": valid
            and classification == "compact_payload_partial_gain",
            "screen_local_model_instruction_capacity": valid
            and classification == "compact_payload_no_gain",
            "revert_compact_serializer_experiment": valid
            and classification == "compact_payload_regression",
            "production_default_enablement": False,
            "persona_similarity_claim": False,
            "human_blind_rating": False,
            "model_training": False,
            "sealed_holdout_unsealing": False,
        },
        "evidence_boundary": (
            "Development-set base-model serializer experiment only. It measures reliable semantic "
            "realization under the unchanged strict gate, not persona similarity or production readiness."
        ),
    }


def render_markdown(report):
    legacy = report["condition_summaries"][surface_payload.LEGACY_JSON_V1]
    compact = report["condition_summaries"][surface_payload.COMPACT_JAPANESE_V2]
    legacy_reasons = legacy["rejection_families"]
    compact_reasons = compact["rejection_families"]
    return "\n".join(
        [
            "# 右腦精簡日文載荷 V1 實際模型結果",
            "",
            f"**{report['status']} / {report['classification']}**",
            "",
            "| 指標 | 舊格式 | 精簡日文 | 差異（新－舊） |",
            "|---|---:|---:|---:|",
            f"| 嚴格有效輸出 | {legacy['strict_valid_generation_count']}/10 | {compact['strict_valid_generation_count']}/10 | {report['strict_valid_delta_compact_minus_legacy']:+d} |",
            f"| 兩種人格策略都有效 | {legacy['both_conditions_strict_valid_pair_count']}/5 | {compact['both_conditions_strict_valid_pair_count']}/5 | {compact['both_conditions_strict_valid_pair_count'] - legacy['both_conditions_strict_valid_pair_count']:+d} |",
            f"| 語言／文字污染 | {legacy_reasons.get('language_or_script_pollution', 0)}/10 | {compact_reasons.get('language_or_script_pollution', 0)}/10 | {compact_reasons.get('language_or_script_pollution', 0) - legacy_reasons.get('language_or_script_pollution', 0):+d} |",
            f"| 必要語意缺失 | {legacy_reasons.get('required_semantics_missing', 0)}/10 | {compact_reasons.get('required_semantics_missing', 0)}/10 | {compact_reasons.get('required_semantics_missing', 0) - legacy_reasons.get('required_semantics_missing', 0):+d} |",
            f"| 過度禮貌 | {legacy_reasons.get('polite_register_drift', 0)}/10 | {compact_reasons.get('polite_register_drift', 0)}/10 | {compact_reasons.get('polite_register_drift', 0) - legacy_reasons.get('polite_register_drift', 0):+d} |",
            "",
            f"決策：`{report['decision']}`",
            "",
            "此開發集結果不授權上線、人格相似度主張、盲評或訓練。",
            "",
        ]
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["run-condition", "combine"])
    parser.add_argument("--preregistration", default=str(DEFAULT_PREREGISTRATION))
    parser.add_argument("--construction", default=str(DEFAULT_CONSTRUCTION))
    parser.add_argument("--cases", default=str(DEFAULT_CASES))
    parser.add_argument("--serializer", choices=list(SERIALIZERS))
    parser.add_argument("--condition-output")
    parser.add_argument("--legacy-artifact", default=str(DEFAULT_LEGACY_ARTIFACT))
    parser.add_argument("--compact-artifact", default=str(DEFAULT_COMPACT_ARTIFACT))
    parser.add_argument("--report-json", default=str(DEFAULT_REPORT_JSON))
    parser.add_argument("--report-md", default=str(DEFAULT_REPORT_MD))
    args = parser.parse_args()
    preregistration = load_json(args.preregistration)
    if preregistration.get("experiment_id") != EXPERIMENT_ID:
        raise SystemExit("wrong preregistration experiment_id")
    if args.command == "run-condition":
        if not args.serializer or not args.condition_output:
            raise SystemExit("run-condition requires --serializer and --condition-output")
        artifact = run_condition(
            preregistration,
            load_json(args.construction),
            load_json(args.cases),
            args.serializer,
        )
        Path(args.condition_output).write_text(
            json.dumps(artifact, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(
            json.dumps(
                {
                    "status": artifact["status"],
                    "serializer": artifact["serializer_id"],
                    "strict_valid": artifact["summary"]["strict_valid_generation_count"],
                    "generation_seconds": artifact["runtime"]["generation_seconds"],
                },
                ensure_ascii=False,
            )
        )
        raise SystemExit(0 if artifact["status"] == "condition_complete" else 1)

    artifacts = {
        surface_payload.LEGACY_JSON_V1: load_json(args.legacy_artifact),
        surface_payload.COMPACT_JAPANESE_V2: load_json(args.compact_artifact),
    }
    report = build_report(preregistration, artifacts)
    Path(args.report_json).write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    Path(args.report_md).write_text(render_markdown(report), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": report["status"],
                "classification": report["classification"],
                "decision": report["decision"],
                "delta": report["strict_valid_delta_compact_minus_legacy"],
            },
            ensure_ascii=False,
        )
    )
    raise SystemExit(0 if report["status"] == "valid_experiment" else 1)


if __name__ == "__main__":
    main()
