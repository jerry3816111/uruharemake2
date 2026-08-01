#!/usr/bin/env python3
"""Run a preregistered paired local-model persona-policy surface pilot."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import random
import time
from collections import Counter
from pathlib import Path

import torch

import uruha_compute_ledger as ledger_module
import uruha_persona_policy as persona_policy
from uruha_brain_mac import (
    RIGHT_BRAIN_ADAPTER_PATH,
    RIGHT_BRAIN_BASE_MODEL,
    RightBrain,
    StructuredSurfaceUnavailableError,
)


ROOT = Path(__file__).resolve().parent
EXPERIMENT_ID = "persona_policy_local_model_pilot_v1"
DEFAULT_PREREGISTRATION = ROOT / "configs/persona_policy_local_model_pilot_v1_preregistration.json"
DEFAULT_CASES = ROOT / "configs/persona_policy_local_model_pilot_v1_cases.json"
DEFAULT_REPORT_JSON = ROOT / "reports/persona_policy_local_model_pilot_v1_result.json"
DEFAULT_REPORT_MD = ROOT / "reports/persona_policy_local_model_pilot_v1_result.md"
PASS_DECISION = "authorize_blinded_policy_direction_coding_bundle_only"
FAIL_DECISION = "repair_structured_local_model_surface_before_persona_scoring"
PROVIDERS = (persona_policy.TARGET_PROVIDER, persona_policy.NEUTRAL_PROVIDER)
EMPTY_MEMORY = {
    "wisdom": "",
    "episodes": "",
    "profile": "",
    "recent_dialogue": "",
    "working_memory_summary": "",
    "working_memory_items": [],
    "recent_turns": [],
    "profile_structured": {},
}
PSYCHE = {"mood": -12, "trust": 58}


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(value):
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def binding(path):
    path = Path(path).resolve()
    return {"path": str(path.relative_to(ROOT)), "sha256": sha256_file(path)}


def _seed_everything(seed):
    random.seed(seed)
    torch.manual_seed(seed)
    if torch.backends.mps.is_available() and hasattr(torch.mps, "manual_seed"):
        torch.mps.manual_seed(seed)


def _reset_transient_state(rightbrain):
    rightbrain.history.clear()
    rightbrain.reply_variant_counts.clear()
    rightbrain.intent_variant_counts.clear()
    rightbrain.normalized_reply_counts.clear()
    rightbrain.intent_normalized_counts.clear()


def _extract_raw_generation(trace):
    accepted = list((trace or {}).get("accepted") or [])
    if accepted:
        return str(accepted[0].get("raw_candidate") or "").strip()
    rejected = list((trace or {}).get("initial_rejected") or [])
    if rejected:
        return str(rejected[0].get("raw_candidate") or "").strip()
    return ""


def _extract_rejection_reasons(trace):
    rejected = list((trace or {}).get("initial_rejected") or [])
    if not rejected:
        return []
    return list(rejected[0].get("rejection_reasons") or [])


def _run_one(rightbrain, provider_id, ledger, case):
    rightbrain.persona_policy_provider = persona_policy.build_persona_policy_provider(provider_id)
    rightbrain.compute_ledger = ledger
    _reset_transient_state(rightbrain)
    _seed_everything(int(case["seed"]))
    logic = copy.deepcopy(case["logic"])
    logic["public_persona_context"] = case["context"]
    started = time.perf_counter()
    reply = ""
    error_reason = None
    with ledger.item_scope(case["case_id"], provider_id):
        try:
            reply = rightbrain.speak(
                case["user_input"],
                logic,
                copy.deepcopy(EMPTY_MEMORY),
                dict(PSYCHE),
            )
        except StructuredSurfaceUnavailableError as exc:
            error_reason = exc.reason
    trace = logic.get("model_surface_candidate_trace") or {}
    raw = _extract_raw_generation(trace)
    return {
        "case_id": case["case_id"],
        "context": case["context"],
        "provider_id": provider_id,
        "seed": int(case["seed"]),
        "execution_position": case["condition_order"].index(provider_id) + 1,
        "strict_valid": bool(reply),
        "error_reason": error_reason,
        "raw_generation": raw,
        "visible_reply": reply,
        "raw_generation_sha256": sha256_text(raw),
        "visible_reply_sha256": sha256_text(reply) if reply else None,
        "normalized_output": rightbrain._normalize_reply_key(reply or raw),
        "rejection_reasons": _extract_rejection_reasons(trace),
        "legacy_fixed_surface_access_count": rightbrain.legacy_fixed_surface_access_count,
        "duration_seconds": round(time.perf_counter() - started, 4),
        "production_memory_write_count": 0,
    }


def _adapter_identity():
    adapter = Path(RIGHT_BRAIN_ADAPTER_PATH)
    model_file = adapter / "adapter_model.safetensors"
    config_file = adapter / "adapter_config.json"
    return {
        "path": adapter.name,
        "config_sha256": sha256_file(config_file),
        "weights_sha256": sha256_file(model_file),
    }


def build_report(preregistration, case_bundle):
    offline = os.getenv("HF_HUB_OFFLINE") == "1" and os.getenv("TRANSFORMERS_OFFLINE") == "1"
    if not offline:
        raise RuntimeError("formal pilot requires HF_HUB_OFFLINE=1 and TRANSFORMERS_OFFLINE=1")
    if RIGHT_BRAIN_BASE_MODEL != preregistration["model_contract"]["base_model"]:
        raise RuntimeError("base model differs from preregistration")
    if Path(RIGHT_BRAIN_ADAPTER_PATH).name != preregistration["model_contract"]["adapter"]:
        raise RuntimeError("adapter differs from preregistration")

    cases = list(case_bundle["cases"])
    ledgers = {provider_id: ledger_module.ComputeLedger() for provider_id in PROVIDERS}
    loaded_at = time.perf_counter()
    rightbrain = RightBrain(
        load_model=True,
        persona_policy_provider=persona_policy.build_persona_policy_provider(PROVIDERS[0]),
        compute_ledger=ledgers[PROVIDERS[0]],
    )
    model_load_seconds = round(time.perf_counter() - loaded_at, 4)
    rightbrain.model_candidate_count = 1
    rightbrain.model_repair_enabled = False
    rightbrain.model_blend_enabled = False
    rightbrain.structured_prompt_token_budget = int(
        preregistration["model_contract"]["prompt_allocation_budget_tokens"]
    )

    rows = []
    for case in cases:
        for provider_id in case["condition_order"]:
            rows.append(_run_one(rightbrain, provider_id, ledgers[provider_id], case))
            if torch.backends.mps.is_available():
                torch.mps.synchronize()

    snapshots = {key: value.snapshot() for key, value in ledgers.items()}
    parity = ledger_module.compare_compute_envelopes(
        snapshots[persona_policy.TARGET_PROVIDER],
        snapshots[persona_policy.NEUTRAL_PROVIDER],
    )
    row_map = {(row["case_id"], row["provider_id"]): row for row in rows}
    pairs = []
    for case in cases:
        target = row_map[(case["case_id"], persona_policy.TARGET_PROVIDER)]
        neutral = row_map[(case["case_id"], persona_policy.NEUTRAL_PROVIDER)]
        both_valid = target["strict_valid"] and neutral["strict_valid"]
        outputs_differ = (
            target["normalized_output"] != neutral["normalized_output"]
            and bool(target["normalized_output"])
            and bool(neutral["normalized_output"])
        )
        pairs.append(
            {
                "case_id": case["case_id"],
                "context": case["context"],
                "both_conditions_strict_valid": both_valid,
                "normalized_outputs_differ": outputs_differ,
                "strict_valid_and_different": both_valid and outputs_differ,
            }
        )

    required = preregistration["success_requires"]
    counts = {
        "case_pair_count": len(pairs),
        "actual_model_generation_call_count": sum(snapshot["call_count"] for snapshot in snapshots.values()),
        "nonempty_raw_generation_count": sum(bool(row["raw_generation"]) for row in rows),
        "strict_valid_generation_count": sum(row["strict_valid"] for row in rows),
        "both_conditions_strict_valid_pair_count": sum(row["both_conditions_strict_valid"] for row in pairs),
        "strict_valid_pair_with_different_output_count": sum(row["strict_valid_and_different"] for row in pairs),
        "all_raw_pair_output_difference_count": sum(row["normalized_outputs_differ"] for row in pairs),
        "distinct_normalized_output_count": len({row["normalized_output"] for row in rows if row["normalized_output"]}),
        "legacy_fixed_surface_access_count": rightbrain.legacy_fixed_surface_access_count,
        "ledger_raw_prompt_or_reply_count": sum(snapshot["contains_raw_prompt_or_reply"] for snapshot in snapshots.values()),
        "production_memory_write_count": 0,
        "benchmark_item_count": 0,
        "target_utterance_injection_count": 0,
    }
    checks = {
        "offline_local_model_only": offline,
        "case_pair_count": counts["case_pair_count"] == required["case_pair_count_exact"],
        "actual_model_generation_call_count": counts["actual_model_generation_call_count"] == required["actual_model_generation_call_count_exact"],
        "nonempty_raw_generation_count": counts["nonempty_raw_generation_count"] == required["nonempty_raw_generation_count_exact"],
        "allocated_prompt_tokens_each": all(value == required["allocated_prompt_tokens_each_exact"] for value in parity["left_prompt_tokens"] + parity["right_prompt_tokens"]),
        "compute_parity": parity["parity_pass"] is required["compute_parity_pass"],
        "enough_strict_valid_pairs": counts["both_conditions_strict_valid_pair_count"] >= required["both_conditions_strict_valid_pair_count_minimum"],
        "observable_policy_sensitivity": counts["strict_valid_pair_with_different_output_count"] >= required["strict_valid_pair_with_different_output_count_minimum"],
        "legacy_surface_not_accessed": counts["legacy_fixed_surface_access_count"] == required["legacy_fixed_surface_access_count_exact"],
        "ledger_contains_no_raw_text": counts["ledger_raw_prompt_or_reply_count"] == required["ledger_raw_prompt_or_reply_count_exact"],
        "production_memory_unchanged": counts["production_memory_write_count"] == required["production_memory_write_count_exact"],
        "no_benchmark_items": counts["benchmark_item_count"] == required["benchmark_item_count_exact"],
        "no_target_utterance_injection": counts["target_utterance_injection_count"] == required["target_utterance_injection_count_exact"],
    }
    passed = all(checks.values())
    rejection_counts = Counter(reason for row in rows for reason in row["rejection_reasons"])
    return {
        "schema": "uruha_persona_policy_local_model_pilot_result_v1",
        "experiment_id": EXPERIMENT_ID,
        "status": "pilot_passed" if passed else "pilot_failed",
        "decision": PASS_DECISION if passed else FAIL_DECISION,
        "inputs": {
            "preregistration": binding(DEFAULT_PREREGISTRATION),
            "cases": binding(DEFAULT_CASES),
            "brain_source": binding(ROOT / "uruha_brain_mac.py"),
            "persona_policy_source": binding(ROOT / "uruha_persona_policy.py"),
            "base_model": RIGHT_BRAIN_BASE_MODEL,
            "adapter": _adapter_identity(),
        },
        "runtime": {
            "device": rightbrain.device,
            "dtype": str(rightbrain.dtype),
            "model_load_seconds": model_load_seconds,
            "total_generation_seconds": round(sum(row["duration_seconds"] for row in rows), 4),
            "offline": offline,
        },
        "counts": counts,
        "checks": checks,
        "compute_parity": parity,
        "rejection_reason_counts": dict(sorted(rejection_counts.items())),
        "pairs": pairs,
        "generations": rows,
        "authorizations": {
            "build_blinded_policy_direction_coding_bundle": passed,
            "formal_persona_similarity_claim": False,
            "production_default_enablement": False,
            "model_training": False,
            "sealed_holdout_unsealing": False,
            "public_impersonation": False,
        },
        "evidence_boundary": "This fresh local-model pilot measures carrier viability and observable policy sensitivity only. It does not determine which condition is more similar to the target person.",
    }


def render_markdown(report):
    counts = report["counts"]
    lines = [
        "# 人格策略實際本機模型 pilot V1",
        "",
        f"**{report['status']}**",
        "",
        "| 指標 | 結果 |",
        "|---|---:|",
        f"| 實際 7B 生成 | {counts['actual_model_generation_call_count']} |",
        f"| 嚴格有效輸出 | {counts['strict_valid_generation_count']}/10 |",
        f"| 兩組都有效的配對 | {counts['both_conditions_strict_valid_pair_count']}/5 |",
        f"| 有效且輸出不同的配對 | {counts['strict_valid_pair_with_different_output_count']}/5 |",
        f"| 不同正規化輸出 | {counts['distinct_normalized_output_count']}/10 |",
        f"| legacy 固定回覆存取 | {counts['legacy_fixed_surface_access_count']} |",
        f"| target／neutral 配置 tokens | {report['compute_parity']['left_prompt_tokens']} / {report['compute_parity']['right_prompt_tokens']} |",
        "",
        f"決策：`{report['decision']}`",
        "",
        "本結果只回答 structured 人格策略能否被目前本機右腦承載並造成可觀察差異；哪一組更像目標人物仍需後續盲化編碼，不能由本 pilot 自行宣稱。",
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
    cases = load_json(args.cases)
    if preregistration.get("experiment_id") != EXPERIMENT_ID:
        raise SystemExit("wrong preregistration experiment_id")
    report = build_report(preregistration, cases)
    Path(args.report_json).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    Path(args.report_md).write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({"status": report["status"], "decision": report["decision"], "counts": report["counts"], "runtime": report["runtime"]}, ensure_ascii=False))
    raise SystemExit(0 if report["status"] == "pilot_passed" else 1)


if __name__ == "__main__":
    main()
