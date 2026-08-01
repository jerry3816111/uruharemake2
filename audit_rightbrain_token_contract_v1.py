#!/usr/bin/env python3
"""Audit whether the fixed 800-token training allocation is materially oversized."""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

from transformers import AutoTokenizer

import build_rightbrain_gradient_checkpoint_repro_v1 as common
import build_rightbrain_role_curriculum_training_pilot_v1 as curriculum


ROOT = Path(__file__).resolve().parent
EXPERIMENT_ID = "rightbrain_token_contract_audit_v1"
PREREGISTRATION = ROOT / "configs/rightbrain_role_curriculum_training_pilot_v1_preregistration.json"
TREATMENT = curriculum.DEFAULT_TREATMENT
CONTROL = curriculum.DEFAULT_CONTROL
RESULT_JSON = ROOT / "reports/rightbrain_token_contract_audit_v1_result.json"
RESULT_MD = ROOT / "reports/rightbrain_token_contract_audit_v1_result.md"


def _percentile(sorted_values, fraction):
    return sorted_values[int(fraction * (len(sorted_values) - 1))]


def _row_length(tokenizer, row):
    prompt = tokenizer.apply_chat_template(
        row["messages"][:-1], tokenize=False, add_generation_prompt=True
    )
    answer = f"{curriculum.assistant_target(row)}<|im_end|>"
    prompt_tokens = len(tokenizer(prompt, add_special_tokens=False).input_ids)
    answer_tokens = len(tokenizer(answer, add_special_tokens=False).input_ids)
    return {
        "id": row["id"],
        "prompt_tokens": prompt_tokens,
        "answer_tokens": answer_tokens,
        "active_tokens": prompt_tokens + answer_tokens,
    }


def _summarize(rows, allocation):
    lengths = sorted(row["active_tokens"] for row in rows)
    active_total = sum(lengths)
    return {
        "row_count": len(rows),
        "minimum_active_tokens": min(lengths),
        "median_active_tokens": statistics.median(lengths),
        "p90_active_tokens": _percentile(lengths, 0.90),
        "p95_active_tokens": _percentile(lengths, 0.95),
        "maximum_active_tokens": max(lengths),
        "mean_active_tokens": active_total / len(lengths),
        "active_token_total": active_total,
        "padding_token_slots_at_current_allocation": allocation * len(lengths) - active_total,
        "current_allocation_utilization": active_total / (allocation * len(lengths)),
        "rows_exceeding_current_allocation": sum(length > allocation for length in lengths),
    }


def audit():
    preregistration = common.load_json(PREREGISTRATION)
    allocation = int(preregistration["training_schedule"]["fixed_allocated_sequence_length"])
    tokenizer = AutoTokenizer.from_pretrained(
        preregistration["local_model_contract"]["snapshot_root"],
        trust_remote_code=True,
        local_files_only=True,
    )
    treatment_source = common.load_json(TREATMENT)
    control_source = common.load_json(CONTROL)
    treatment_rows = [_row_length(tokenizer, row) for row in treatment_source]
    control_rows = [_row_length(tokenizer, row) for row in control_source]
    treatment_summary = _summarize(treatment_rows, allocation)
    control_summary = _summarize(control_rows, allocation)
    lossless_fixed_allocation = max(
        treatment_summary["maximum_active_tokens"],
        control_summary["maximum_active_tokens"],
    )
    lossless_slot_reduction = (allocation - lossless_fixed_allocation) / allocation
    probe_indices = [63, 50, 60, 77, 2, 59, 78, 36]
    probe_rows = [
        {"row_index": index, **treatment_rows[index]}
        for index in probe_indices
    ]
    checks = {
        "matched_row_counts": len(treatment_rows) == len(control_rows) == 80,
        "no_current_truncation": treatment_summary["rows_exceeding_current_allocation"] == 0
        and control_summary["rows_exceeding_current_allocation"] == 0,
        "lossless_fixed_allocation_is_772": lossless_fixed_allocation == 772,
        "matched_active_token_totals": treatment_summary["active_token_total"]
        == control_summary["active_token_total"],
        "probe_contains_long_row": max(row["active_tokens"] for row in probe_rows) == 771,
    }
    return {
        "schema": "uruha_rightbrain_token_contract_audit_v1",
        "experiment_id": EXPERIMENT_ID,
        "evidence_class": "exploratory_deterministic_data_audit_not_causal_training_evidence",
        "inputs": {
            "preregistration": common.file_binding(PREREGISTRATION),
            "treatment": common.file_binding(TREATMENT),
            "control": common.file_binding(CONTROL),
            "tokenizer_snapshot": preregistration["local_model_contract"]["snapshot_root"],
        },
        "current_fixed_allocation": allocation,
        "treatment": treatment_summary,
        "control": control_summary,
        "exact_gradient_probe_rows": probe_rows,
        "lossless_fixed_allocation": {
            "tokens": lossless_fixed_allocation,
            "token_slots_reduced_per_row": allocation - lossless_fixed_allocation,
            "relative_slot_reduction": lossless_slot_reduction,
        },
        "checks": checks,
        "decision": {
            "passed": all(checks.values()),
            "outcome": "fixed_800_contract_is_not_materially_oversized",
            "reason": (
                "A lossless fixed allocation can only fall from 800 to 772 tokens "
                f"({lossless_slot_reduction:.1%}); this audit does not support "
                "prioritizing that small change as a gradient-stability intervention."
            ),
            "authorized_next_step": "evaluate_local_training_backend_or_shape_contract_redesign",
            "authorize_training": False,
            "authorize_runtime_change": False,
            "authorize_persona_claim": False,
        },
    }


def render_markdown(result):
    treatment = result["treatment"]
    lossless = result["lossless_fixed_allocation"]
    return "\n".join(
        [
            "# RightBrain token contract 探索性稽核",
            "",
            f"- 現行固定長度：`{result['current_fixed_allocation']}` tokens",
            f"- 80 筆資料平均實際長度：`{treatment['mean_active_tokens']:.4f}` tokens",
            f"- 最長資料：`{treatment['maximum_active_tokens']}` tokens",
            f"- 現行槽位利用率：`{treatment['current_allocation_utilization']:.4%}`",
            f"- 無損固定長度下限：`{lossless['tokens']}` tokens",
            f"- 最多只減少：`{lossless['relative_slot_reduction']:.2%}`",
            "",
            f"結論：`{result['decision']['outcome']}`。",
            "此結果是資料長度稽核，不是梯度穩定性或人格能力證據。",
        ]
    ) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    result = audit()
    print(json.dumps(result["decision"], ensure_ascii=False, indent=2))
    if not result["decision"]["passed"]:
        raise SystemExit(1)
    if args.write:
        common.atomic_json(RESULT_JSON, result)
        common.atomic_text(RESULT_MD, render_markdown(result))


if __name__ == "__main__":
    main()
