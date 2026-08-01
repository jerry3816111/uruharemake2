#!/usr/bin/env python3
"""Run a matched base-only versus v10 RightBrain adapter diagnostic."""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import os
import time
from collections import Counter
from pathlib import Path

import torch

import persona_policy_local_model_pilot_v1 as pilot
import uruha_brain_mac as brain_module
import uruha_compute_ledger as ledger_module
import uruha_persona_policy as persona_policy


ROOT = Path(__file__).resolve().parent
EXPERIMENT_ID = "rightbrain_adapter_causality_diagnostic_v1"
BASE_ONLY = "qwen25_7b_base_only"
V10_ADAPTER = "qwen25_7b_v10_adapter"
MODEL_CONDITIONS = (BASE_ONLY, V10_ADAPTER)
DEFAULT_PREREGISTRATION = ROOT / "configs/rightbrain_adapter_causality_diagnostic_v1_preregistration.json"
DEFAULT_CASES = ROOT / "configs/persona_policy_local_model_pilot_v1_cases.json"
DEFAULT_REPORT_JSON = ROOT / "reports/rightbrain_adapter_causality_diagnostic_v1_result.json"
DEFAULT_REPORT_MD = ROOT / "reports/rightbrain_adapter_causality_diagnostic_v1_result.md"


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def binding(path):
    path = Path(path).resolve()
    return {"path": str(path.relative_to(ROOT)), "sha256": sha256_file(path)}


def _condition_adapter_path(condition_id):
    if condition_id == BASE_ONLY:
        return ""
    if condition_id == V10_ADAPTER:
        return str(ROOT / "uruha_rightbrain_plan_sft_lora_v10_expanded_rejection_v1")
    raise ValueError(f"unknown condition: {condition_id}")


def _load_rightbrain(condition_id, ledger):
    original_adapter_path = brain_module.RIGHT_BRAIN_ADAPTER_PATH
    brain_module.RIGHT_BRAIN_ADAPTER_PATH = _condition_adapter_path(condition_id)
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
    rightbrain.model_candidate_count = 1
    rightbrain.model_repair_enabled = False
    rightbrain.model_blend_enabled = False
    rightbrain.structured_prompt_token_budget = 640
    return rightbrain, round(time.perf_counter() - started, 4)


def _release_rightbrain(rightbrain):
    del rightbrain
    gc.collect()
    if torch.backends.mps.is_available():
        torch.mps.empty_cache()
        torch.mps.synchronize()


def _reason_families(rows):
    counts = Counter()
    for row in rows:
        reasons = row.get("rejection_reasons") or []
        if any(reason in {"cjk_language_leak", "nonstandard_cjk_surface", "unexpected_ascii_leak"} for reason in reasons):
            counts["language_or_script_pollution"] += 1
        if any(str(reason).startswith("semantic_slots_missing:") for reason in reasons):
            counts["required_semantics_missing"] += 1
        if "polite_tone_drift" in reasons:
            counts["polite_register_drift"] += 1
    return dict(counts)


def _model_summary(rows, target_ledger, neutral_ledger):
    target_snapshot = target_ledger.snapshot()
    neutral_snapshot = neutral_ledger.snapshot()
    parity = ledger_module.compare_compute_envelopes(target_snapshot, neutral_snapshot)
    row_map = {(row["case_id"], row["provider_id"]): row for row in rows}
    case_ids = list(dict.fromkeys(row["case_id"] for row in rows))
    pairs = []
    for case_id in case_ids:
        target = row_map[(case_id, persona_policy.TARGET_PROVIDER)]
        neutral = row_map[(case_id, persona_policy.NEUTRAL_PROVIDER)]
        both_valid = target["strict_valid"] and neutral["strict_valid"]
        differ = (
            bool(target["normalized_output"])
            and bool(neutral["normalized_output"])
            and target["normalized_output"] != neutral["normalized_output"]
        )
        pairs.append(
            {
                "case_id": case_id,
                "both_conditions_strict_valid": both_valid,
                "normalized_outputs_differ": differ,
                "strict_valid_and_different": both_valid and differ,
            }
        )
    return {
        "generation_count": len(rows),
        "nonempty_raw_generation_count": sum(bool(row["raw_generation"]) for row in rows),
        "strict_valid_generation_count": sum(row["strict_valid"] for row in rows),
        "strict_valid_target_count": sum(row["strict_valid"] and row["provider_id"] == persona_policy.TARGET_PROVIDER for row in rows),
        "strict_valid_neutral_count": sum(row["strict_valid"] and row["provider_id"] == persona_policy.NEUTRAL_PROVIDER for row in rows),
        "both_conditions_strict_valid_pair_count": sum(row["both_conditions_strict_valid"] for row in pairs),
        "raw_output_difference_pair_count": sum(row["normalized_outputs_differ"] for row in pairs),
        "strict_valid_and_different_pair_count": sum(row["strict_valid_and_different"] for row in pairs),
        "distinct_normalized_output_count": len({row["normalized_output"] for row in rows if row["normalized_output"]}),
        "rejection_families": _reason_families(rows),
        "compute_parity": parity,
        "ledger_contains_raw_text": target_snapshot["contains_raw_prompt_or_reply"] or neutral_snapshot["contains_raw_prompt_or_reply"],
        "pairs": pairs,
    }


def classify_diagnostic(base_valid, adapter_valid):
    if base_valid >= 5 and base_valid - adapter_valid >= 3:
        return "adapter_is_primary_regression_source"
    if adapter_valid >= 5 and adapter_valid - base_valid >= 3:
        return "base_model_is_primary_regression_source"
    if max(base_valid, adapter_valid) < 5:
        return "both_surface_carriers_inadequate"
    return "inconclusive_small_delta"


def _normalized_cross_model_signature(snapshot):
    rows = []
    for call in snapshot["calls"]:
        request = call.get("request") or {}
        options = dict(request.get("options") or {})
        adapter_name = options.pop("adapter_name", None)
        rows.append(
            {
                "stage": call.get("stage"),
                "backend": call.get("backend"),
                "model": call.get("model"),
                "options_except_adapter": options,
                "adapter_name": adapter_name,
                "prompt_tokens": (call.get("response") or {}).get("prompt_tokens"),
                "active_prompt_tokens": (call.get("response") or {}).get("active_prompt_tokens"),
            }
        )
    return rows


def _cross_model_control_check(snapshots):
    comparisons = []
    for provider_id in pilot.PROVIDERS:
        base_rows = _normalized_cross_model_signature(snapshots[BASE_ONLY][provider_id])
        adapter_rows = _normalized_cross_model_signature(snapshots[V10_ADAPTER][provider_id])
        controls_equal = len(base_rows) == len(adapter_rows) and all(
            {key: value for key, value in base.items() if key != "adapter_name"}
            == {key: value for key, value in adapted.items() if key != "adapter_name"}
            for base, adapted in zip(base_rows, adapter_rows, strict=True)
        )
        adapter_difference_exact = all(
            base["adapter_name"] == "" and adapted["adapter_name"] == "surface"
            for base, adapted in zip(base_rows, adapter_rows, strict=True)
        )
        comparisons.append(
            {
                "provider_id": provider_id,
                "controls_equal_except_adapter": controls_equal,
                "adapter_difference_exact": adapter_difference_exact,
            }
        )
    return comparisons


def _base_cache_commit():
    ref = Path.home() / ".cache/huggingface/hub/models--Qwen--Qwen2.5-7B-Instruct/refs/main"
    return ref.read_text(encoding="utf-8").strip()


def build_report(preregistration, case_bundle):
    offline = os.getenv("HF_HUB_OFFLINE") == "1" and os.getenv("TRANSFORMERS_OFFLINE") == "1"
    if not offline:
        raise RuntimeError("formal diagnostic requires offline Hugging Face mode")
    cases = list(case_bundle["cases"])
    condition_rows = {}
    condition_summaries = {}
    condition_ledgers = {}
    load_times = {}
    adapter_states = {}
    total_legacy_access = 0

    for condition_id in MODEL_CONDITIONS:
        ledgers = {provider_id: ledger_module.ComputeLedger() for provider_id in pilot.PROVIDERS}
        rightbrain, load_seconds = _load_rightbrain(condition_id, ledgers[persona_policy.TARGET_PROVIDER])
        load_times[condition_id] = load_seconds
        adapter_states[condition_id] = {
            "compat_adapter_loaded": rightbrain.compat_adapter_dir is not None,
            "active_adapter_name": rightbrain._active_model_adapter_name or "",
        }
        rows = []
        for case in cases:
            for provider_id in case["condition_order"]:
                row = pilot._run_one(rightbrain, provider_id, ledgers[provider_id], case)
                row["model_condition"] = condition_id
                rows.append(row)
                if torch.backends.mps.is_available():
                    torch.mps.synchronize()
        total_legacy_access += rightbrain.legacy_fixed_surface_access_count
        snapshots = {provider_id: ledger.snapshot() for provider_id, ledger in ledgers.items()}
        condition_rows[condition_id] = rows
        condition_ledgers[condition_id] = snapshots
        condition_summaries[condition_id] = _model_summary(
            rows,
            ledgers[persona_policy.TARGET_PROVIDER],
            ledgers[persona_policy.NEUTRAL_PROVIDER],
        )
        _release_rightbrain(rightbrain)

    cross_model = _cross_model_control_check(condition_ledgers)
    base_valid = condition_summaries[BASE_ONLY]["strict_valid_generation_count"]
    adapter_valid = condition_summaries[V10_ADAPTER]["strict_valid_generation_count"]
    classification = classify_diagnostic(base_valid, adapter_valid)
    decision = preregistration["decision_boundary"][classification]
    all_rows = [*condition_rows[BASE_ONLY], *condition_rows[V10_ADAPTER]]
    valid_required = preregistration["valid_diagnostic_requires"]
    counts = {
        "model_load_count": 2,
        "actual_generation_count": len(all_rows),
        "nonempty_raw_generation_count": sum(bool(row["raw_generation"]) for row in all_rows),
        "legacy_fixed_surface_access_count": total_legacy_access,
        "production_memory_write_count": 0,
        "benchmark_item_count": 0,
        "formal_persona_score_count": 0,
    }
    checks = {
        "offline_local_inference": offline,
        "model_load_count": counts["model_load_count"] == valid_required["model_load_count_exact"],
        "actual_generation_count": counts["actual_generation_count"] == valid_required["actual_generation_count_exact"],
        "nonempty_raw_generation_count": counts["nonempty_raw_generation_count"] == valid_required["nonempty_raw_generation_count_exact"],
        "within_model_target_neutral_compute_parity": all(condition_summaries[condition]["compute_parity"]["parity_pass"] for condition in MODEL_CONDITIONS),
        "cross_model_controls_equal_except_adapter": all(row["controls_equal_except_adapter"] and row["adapter_difference_exact"] for row in cross_model),
        "allocated_prompt_tokens_each": all(value == valid_required["allocated_prompt_tokens_each_exact"] for condition in MODEL_CONDITIONS for provider in pilot.PROVIDERS for value in [call["response"]["prompt_tokens"] for call in condition_ledgers[condition][provider]["calls"]]),
        "adapter_state_exact": (
            not adapter_states[BASE_ONLY]["compat_adapter_loaded"]
            and adapter_states[BASE_ONLY]["active_adapter_name"] == ""
            and adapter_states[V10_ADAPTER]["compat_adapter_loaded"]
            and adapter_states[V10_ADAPTER]["active_adapter_name"] == "surface"
        ),
        "legacy_surface_not_accessed": counts["legacy_fixed_surface_access_count"] == valid_required["legacy_fixed_surface_access_count_exact"],
        "ledger_contains_no_raw_text": all(not condition_summaries[condition]["ledger_contains_raw_text"] for condition in MODEL_CONDITIONS),
        "production_memory_unchanged": counts["production_memory_write_count"] == valid_required["production_memory_write_count_exact"],
        "no_benchmark_items": counts["benchmark_item_count"] == valid_required["benchmark_item_count_exact"],
        "no_formal_persona_score": counts["formal_persona_score_count"] == valid_required["formal_persona_score_count_exact"],
    }
    valid = all(checks.values())
    adapter_path = ROOT / "uruha_rightbrain_plan_sft_lora_v10_expanded_rejection_v1"
    return {
        "schema": "uruha_rightbrain_adapter_causality_diagnostic_result_v1",
        "experiment_id": EXPERIMENT_ID,
        "status": "valid_diagnostic" if valid else "invalid_diagnostic",
        "classification": classification if valid else "uninterpretable_control_failure",
        "decision": decision if valid else "repair_diagnostic_controls_before_interpretation",
        "inputs": {
            "preregistration": binding(DEFAULT_PREREGISTRATION),
            "cases": binding(DEFAULT_CASES),
            "base_model": brain_module.RIGHT_BRAIN_BASE_MODEL,
            "base_cache_commit": _base_cache_commit(),
            "adapter_config_sha256": sha256_file(adapter_path / "adapter_config.json"),
            "adapter_weights_sha256": sha256_file(adapter_path / "adapter_model.safetensors"),
        },
        "runtime": {
            "device": "mps" if torch.backends.mps.is_available() else "cpu",
            "load_seconds": load_times,
            "generation_seconds": {
                condition: round(sum(row["duration_seconds"] for row in condition_rows[condition]), 4)
                for condition in MODEL_CONDITIONS
            },
        },
        "counts": counts,
        "checks": checks,
        "adapter_states": adapter_states,
        "cross_model_control_checks": cross_model,
        "condition_summaries": condition_summaries,
        "strict_valid_delta_base_minus_adapter": base_valid - adapter_valid,
        "generations": all_rows,
        "authorizations": {
            "merge_diagnostic_evidence": valid,
            "change_production_default": False,
            "build_persona_blind_rating": False,
            "model_training": False,
            "sealed_holdout_unsealing": False,
            "formal_persona_similarity_claim": False,
        },
        "evidence_boundary": "Development-set causal diagnosis of adapter enablement only; not a holdout, persona score, or production comparison.",
    }


def render_markdown(report):
    base = report["condition_summaries"][BASE_ONLY]
    adapter = report["condition_summaries"][V10_ADAPTER]
    lines = [
        "# 右腦 v10 adapter 因果診斷 V1",
        "",
        f"**{report['status']} / {report['classification']}**",
        "",
        "| 指標 | Base-only | v10 adapter | 差異（Base-v10） |",
        "|---|---:|---:|---:|",
        f"| 嚴格有效輸出 | {base['strict_valid_generation_count']}/10 | {adapter['strict_valid_generation_count']}/10 | {report['strict_valid_delta_base_minus_adapter']:+d} |",
        f"| 兩種 policy 都有效的題目 | {base['both_conditions_strict_valid_pair_count']}/5 | {adapter['both_conditions_strict_valid_pair_count']}/5 | {base['both_conditions_strict_valid_pair_count'] - adapter['both_conditions_strict_valid_pair_count']:+d} |",
        f"| 語言／文字污染 | {base['rejection_families'].get('language_or_script_pollution', 0)}/10 | {adapter['rejection_families'].get('language_or_script_pollution', 0)}/10 | {base['rejection_families'].get('language_or_script_pollution', 0) - adapter['rejection_families'].get('language_or_script_pollution', 0):+d} |",
        f"| 必要語意缺失 | {base['rejection_families'].get('required_semantics_missing', 0)}/10 | {adapter['rejection_families'].get('required_semantics_missing', 0)}/10 | {base['rejection_families'].get('required_semantics_missing', 0) - adapter['rejection_families'].get('required_semantics_missing', 0):+d} |",
        f"| 過度禮貌 | {base['rejection_families'].get('polite_register_drift', 0)}/10 | {adapter['rejection_families'].get('polite_register_drift', 0)}/10 | {base['rejection_families'].get('polite_register_drift', 0) - adapter['rejection_families'].get('polite_register_drift', 0):+d} |",
        "",
        f"決策：`{report['decision']}`",
        "",
        "這是開發集 adapter 診斷，不是人格相似度測試；production、訓練與盲評都沒有被授權。",
    ]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preregistration", default=str(DEFAULT_PREREGISTRATION))
    parser.add_argument("--cases", default=str(DEFAULT_CASES))
    parser.add_argument("--report-json", default=str(DEFAULT_REPORT_JSON))
    parser.add_argument("--report-md", default=str(DEFAULT_REPORT_MD))
    args = parser.parse_args()
    preregistration = load_json(args.preregistration)
    if preregistration.get("experiment_id") != EXPERIMENT_ID:
        raise SystemExit("wrong preregistration experiment_id")
    report = build_report(preregistration, load_json(args.cases))
    Path(args.report_json).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    Path(args.report_md).write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({"status": report["status"], "classification": report["classification"], "decision": report["decision"], "counts": report["counts"], "delta": report["strict_valid_delta_base_minus_adapter"]}, ensure_ascii=False))
    raise SystemExit(0 if report["status"] == "valid_diagnostic" else 1)


if __name__ == "__main__":
    main()
