#!/usr/bin/env python3
"""Construct raw-text-free evidence for structured prompt allocation parity."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path

import torch
from transformers import AutoTokenizer

import public_persona_contract_v3 as public_contract
import uruha_compute_ledger as ledger_module
import uruha_persona_policy as persona_policy
from persona_surface_provider_migration_v1 import BASE_LOGIC, PSYCHE
from uruha_brain_mac import (
    RIGHT_BRAIN_BASE_MODEL,
    RightBrain,
    StructuredSurfaceUnavailableError,
)


ROOT = Path(__file__).resolve().parent
EXPERIMENT_ID = "persona_policy_token_parity_v1"
DEFAULT_PREREGISTRATION = ROOT / "configs/persona_policy_token_parity_v1_preregistration.json"
DEFAULT_REPORT_JSON = ROOT / "reports/persona_policy_token_parity_v1_construction.json"
DEFAULT_REPORT_MD = ROOT / "reports/persona_policy_token_parity_v1_construction.md"
PASS_DECISION = "authorize_fresh_local_model_target_vs_neutral_surface_pilot_only"
FAIL_DECISION = "repair_prompt_allocation_parity_before_local_model_pilot"


class AppendOnlyFakeModel:
    """Exercise tensor allocation without loading or running language-model weights."""

    def __init__(self, suffix_ids):
        self.suffix_ids = list(suffix_ids)
        self.call_count = 0
        self.observations = []

    def generate(self, input_ids, attention_mask=None, **kwargs):
        self.call_count += 1
        mask = attention_mask if attention_mask is not None else torch.ones_like(input_ids)
        self.observations.append(
            {
                "allocated_tokens": int(input_ids.shape[1]),
                "active_tokens": int(mask.sum().item()),
                "leading_masked_tokens": int((mask[0] == 0).sum().item()),
            }
        )
        suffix = torch.tensor(
            [self.suffix_ids],
            dtype=input_ids.dtype,
            device=input_ids.device,
        )
        return torch.cat([input_ids, suffix], dim=1)


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def binding(path):
    path = Path(path).resolve()
    return {"path": str(path.relative_to(ROOT)), "sha256": sha256_file(path)}


def load_local_tokenizer():
    return AutoTokenizer.from_pretrained(
        RIGHT_BRAIN_BASE_MODEL,
        trust_remote_code=True,
        local_files_only=True,
    )


def context_names():
    return [*public_contract.POLICIES, "unsupported_synthetic_control"]


def build_messages(rightbrain, context):
    logic = copy.deepcopy(BASE_LOGIC)
    logic["public_persona_context"] = context
    payload = rightbrain._build_model_surface_payload(
        logic,
        PSYCHE,
        64,
        memory_data={},
    )
    return [
        {"role": "system", "content": rightbrain._model_surface_system_instruction()},
        {"role": "user", "content": payload},
    ]


def prompt_and_ids(tokenizer, messages):
    prompt = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )
    ids = tokenizer(prompt, return_tensors="pt")["input_ids"]
    return prompt, ids


def build_condition(provider_id, tokenizer, budget, ledger):
    rightbrain = RightBrain(
        load_model=False,
        persona_policy_provider=persona_policy.build_persona_policy_provider(provider_id),
        compute_ledger=ledger,
    )
    rightbrain.tokenizer = tokenizer
    suffix_ids = tokenizer("了解。", add_special_tokens=False)["input_ids"]
    rightbrain.model = AppendOnlyFakeModel(suffix_ids)
    rightbrain.device = "cpu"
    rightbrain.structured_prompt_token_budget = int(budget)
    return rightbrain


def run_condition(provider_id, tokenizer, budget):
    ledger = ledger_module.ComputeLedger()
    rightbrain = build_condition(provider_id, tokenizer, budget, ledger)
    rows = []
    for context in context_names():
        messages = build_messages(rightbrain, context)
        prompt, raw_ids = prompt_and_ids(tokenizer, messages)
        raw_tokens = int(raw_ids.shape[1])
        prepared, trace = rightbrain._prepare_generation_inputs(prompt)
        allocated_ids = prepared["input_ids"].cpu()
        attention_mask = prepared["attention_mask"].cpu()
        tail = allocated_ids[:, -raw_tokens:]
        prefix_tokens = int(allocated_ids.shape[1]) - raw_tokens
        active_sequence_preserved = torch.equal(tail, raw_ids)
        prefix_masked = bool(
            prefix_tokens > 0
            and torch.count_nonzero(attention_mask[:, :prefix_tokens]).item() == 0
            and torch.all(attention_mask[:, prefix_tokens:] == 1).item()
        )
        with ledger.item_scope(context, provider_id):
            rightbrain._run_model_surface_generation(
                messages,
                {"do_sample": False},
            )
        rows.append(
            {
                "context": context,
                "active_prompt_tokens": raw_tokens,
                "allocated_prompt_tokens": int(trace["allocated_prompt_tokens"]),
                "masked_prompt_tokens": int(trace["masked_prompt_tokens"]),
                "left_padding_tokens": int(trace["left_padding_tokens"]),
                "active_sequence_preserved": active_sequence_preserved,
                "prefix_attention_masked": prefix_masked,
            }
        )
    return {
        "provider_id": provider_id,
        "rows": rows,
        "ledger": ledger.snapshot(),
        "synthetic_append_call_count": rightbrain.model.call_count,
        "synthetic_append_observations": rightbrain.model.observations,
    }


def budget_exceeded_check(tokenizer, budget):
    rightbrain = build_condition(
        persona_policy.TARGET_PROVIDER,
        tokenizer,
        budget,
        ledger_module.ComputeLedger(),
    )
    prompt = "長い入力" * (budget + 1)
    caught = None
    try:
        rightbrain._prepare_generation_inputs(prompt)
    except StructuredSurfaceUnavailableError as exc:
        caught = exc
    return {
        "typed_error_raised": caught is not None,
        "error_reason": caught.reason if caught is not None else None,
        "allocation_status": rightbrain.last_prompt_allocation_trace.get("status"),
        "active_prompt_tokens": rightbrain.last_prompt_allocation_trace.get("active_prompt_tokens"),
        "configured_budget_tokens": rightbrain.last_prompt_allocation_trace.get("configured_budget_tokens"),
        "truncation_used": False,
    }


def legacy_unchanged_check(tokenizer, budget):
    rows = []
    providers = [
        ("default", None),
        (
            "explicit_legacy",
            persona_policy.build_persona_policy_provider(persona_policy.LEGACY_PROVIDER),
        ),
    ]
    for condition, provider in providers:
        rightbrain = RightBrain(load_model=False, persona_policy_provider=provider)
        rightbrain.tokenizer = tokenizer
        rightbrain.device = "cpu"
        rightbrain.structured_prompt_token_budget = int(budget)
        messages = build_messages(rightbrain, "fatigue_update_with_near_term_plan")
        prompt, raw_ids = prompt_and_ids(tokenizer, messages)
        prepared, trace = rightbrain._prepare_generation_inputs(prompt)
        rows.append(
            {
                "condition": condition,
                "raw_prompt_tokens": int(raw_ids.shape[1]),
                "allocated_prompt_tokens": int(prepared["input_ids"].shape[1]),
                "mode": trace["mode"],
                "behavior_changed": (
                    trace["mode"] != "unmodified"
                    or int(raw_ids.shape[1]) != int(prepared["input_ids"].shape[1])
                ),
            }
        )
    return rows


def build_report(preregistration):
    budget = int(preregistration["allocation_budget_tokens"])
    tokenizer = load_local_tokenizer()
    target = run_condition(persona_policy.TARGET_PROVIDER, tokenizer, budget)
    neutral = run_condition(persona_policy.NEUTRAL_PROVIDER, tokenizer, budget)
    parity = ledger_module.compare_compute_envelopes(target["ledger"], neutral["ledger"])
    exceeded = budget_exceeded_check(tokenizer, budget)
    legacy_rows = legacy_unchanged_check(tokenizer, budget)

    paired_rows = []
    for target_row, neutral_row in zip(target["rows"], neutral["rows"], strict=True):
        paired_rows.append(
            {
                "context": target_row["context"],
                "target_active_prompt_tokens": target_row["active_prompt_tokens"],
                "neutral_active_prompt_tokens": neutral_row["active_prompt_tokens"],
                "active_token_delta": (
                    target_row["active_prompt_tokens"]
                    - neutral_row["active_prompt_tokens"]
                ),
                "target_allocated_prompt_tokens": target_row["allocated_prompt_tokens"],
                "neutral_allocated_prompt_tokens": neutral_row["allocated_prompt_tokens"],
                "both_active_sequences_preserved": (
                    target_row["active_sequence_preserved"]
                    and neutral_row["active_sequence_preserved"]
                ),
                "both_prefixes_attention_masked": (
                    target_row["prefix_attention_masked"]
                    and neutral_row["prefix_attention_masked"]
                ),
            }
        )

    counts = {
        "context_pair_count": len(paired_rows),
        "allocated_prompt_tokens_each": budget,
        "minimum_masked_padding_tokens": min(
            row["masked_prompt_tokens"]
            for condition in (target, neutral)
            for row in condition["rows"]
        ),
        "legacy_prompt_token_behavior_change_count": sum(
            row["behavior_changed"] for row in legacy_rows
        ),
        "synthetic_append_generate_call_count": (
            target["synthetic_append_call_count"]
            + neutral["synthetic_append_call_count"]
        ),
        "actual_model_weight_load_count": 0,
        "actual_model_generation_call_count": 0,
        "holdout_content_review_count": 0,
        "production_memory_write_count": 0,
        "persona_score_count": 0,
    }
    required = preregistration["construction_success_requires"]
    checks = {
        "active_prompt_tokens_preserved": all(
            row["both_active_sequences_preserved"] for row in paired_rows
        ),
        "padding_attention_mask_zero": all(
            row["both_prefixes_attention_masked"] for row in paired_rows
        ),
        "allocated_prompt_token_schedule_equal": parity["prompt_token_schedule_equal"],
        "model_decoding_and_tool_schedule_equal": parity[
            "model_decoding_and_tool_schedule_equal"
        ],
        "compute_parity": parity["parity_pass"],
        "active_token_difference_remains_visible": (
            parity["active_prompt_tokens_available"]
            and not parity["active_prompt_token_schedule_equal"]
        ),
        "budget_exceeded_fails_closed": (
            exceeded["typed_error_raised"]
            and exceeded["error_reason"] == "prompt_token_budget_exceeded"
            and exceeded["allocation_status"] == "budget_exceeded"
            and exceeded["active_prompt_tokens"] > exceeded["configured_budget_tokens"]
            and not exceeded["truncation_used"]
        ),
        "ledger_contains_no_raw_text": (
            not target["ledger"]["contains_raw_prompt_or_reply"]
            and not neutral["ledger"]["contains_raw_prompt_or_reply"]
        ),
    }
    checks["all_preregistered_counts_match"] = (
        counts["context_pair_count"] == required["context_pair_count_exact"]
        and counts["allocated_prompt_tokens_each"]
        == required["allocated_prompt_tokens_each_exact"]
        and counts["minimum_masked_padding_tokens"]
        >= required["masked_padding_tokens_minimum"]
        and checks["active_prompt_tokens_preserved"]
        is required["active_prompt_tokens_preserved"]
        and checks["allocated_prompt_token_schedule_equal"]
        is required["allocated_prompt_token_schedule_equal"]
        and checks["model_decoding_and_tool_schedule_equal"]
        is required["model_decoding_and_tool_schedule_equal"]
        and checks["compute_parity"] is required["compute_parity_pass"]
        and checks["budget_exceeded_fails_closed"]
        is required["budget_exceeded_fails_closed"]
        and counts["legacy_prompt_token_behavior_change_count"]
        == required["legacy_prompt_token_behavior_change_count_exact"]
        and counts["actual_model_weight_load_count"]
        == required["actual_model_weight_load_count_exact"]
        and counts["actual_model_generation_call_count"]
        == required["actual_model_generation_call_count_exact"]
        and counts["holdout_content_review_count"]
        == required["holdout_content_review_count_exact"]
        and counts["production_memory_write_count"]
        == required["production_memory_write_count_exact"]
        and counts["persona_score_count"] == required["persona_score_count_exact"]
    )
    passed = all(checks.values())

    return {
        "schema": "uruha_persona_policy_token_parity_construction_v1",
        "experiment_id": EXPERIMENT_ID,
        "status": "construction_passed" if passed else "construction_failed",
        "decision": PASS_DECISION if passed else FAIL_DECISION,
        "inputs": {
            "preregistration": binding(DEFAULT_PREREGISTRATION),
            "compute_ledger_source": binding(ROOT / "uruha_compute_ledger.py"),
            "brain_source": binding(ROOT / "uruha_brain_mac.py"),
            "tokenizer": RIGHT_BRAIN_BASE_MODEL,
            "tokenizer_local_files_only": True,
        },
        "paired_contexts": paired_rows,
        "compute_parity": parity,
        "budget_exceeded": exceeded,
        "legacy_checks": legacy_rows,
        "counts": counts,
        "checks": checks,
        "authorizations": {
            "fresh_local_model_target_vs_neutral_surface_pilot": passed,
            "formal_persona_similarity_evaluation": False,
            "sealed_holdout_unsealing": False,
            "human_blind_rating": False,
            "model_training": False,
            "production_default_enablement": False,
            "public_persona_fidelity_claim": False,
        },
        "evidence_boundary": (
            "Actual cached tokenizer and tensor allocation were exercised, but no language-model weights "
            "were loaded or run and no persona output was scored."
        ),
    }


def render_markdown(report):
    counts = report["counts"]
    lines = [
        "# 人格策略 prompt token 公平配置建構報告",
        "",
        f"**{report['status']}**",
        "",
        "| 指標 | 結果 |",
        "|---|---:|",
        f"| 配對情境 | {counts['context_pair_count']} |",
        f"| 每組配置 prompt tokens | {counts['allocated_prompt_tokens_each']} |",
        f"| 最少 masked padding | {counts['minimum_masked_padding_tokens']} |",
        f"| 配置 token 排程一致 | {'通過' if report['compute_parity']['prompt_token_schedule_equal'] else '失敗'} |",
        f"| 有效 token 差異仍可見 | {'是' if not report['compute_parity']['active_prompt_token_schedule_equal'] else '否'} |",
        f"| legacy 行為變更 | {counts['legacy_prompt_token_behavior_change_count']} |",
        f"| 真模型權重載入／生成 | {counts['actual_model_weight_load_count']}/{counts['actual_model_generation_call_count']} |",
        "",
        "較短的 prompt 只在左側補 attention-mask=0 的 tokens；原 token 序列不截斷、不重排。超過 640 tokens 時直接失敗關閉。",
        "",
        "這只證明公平運算配置可用，尚未證明目標人格更相似。下一步才可執行小型實際本機模型 target／neutral pilot。",
    ]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preregistration", default=str(DEFAULT_PREREGISTRATION))
    parser.add_argument("--report-json", default=str(DEFAULT_REPORT_JSON))
    parser.add_argument("--report-md", default=str(DEFAULT_REPORT_MD))
    args = parser.parse_args()
    preregistration = load_json(args.preregistration)
    if preregistration.get("experiment_id") != EXPERIMENT_ID:
        raise SystemExit("wrong preregistration experiment_id")
    report = build_report(preregistration)
    Path(args.report_json).write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    Path(args.report_md).write_text(render_markdown(report), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": report["status"],
                "decision": report["decision"],
                "counts": report["counts"],
            },
            ensure_ascii=False,
        )
    )
    raise SystemExit(0 if report["status"] == "construction_passed" else 1)


if __name__ == "__main__":
    main()
