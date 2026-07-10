#!/usr/bin/env python3
"""Measure whether V21 on-policy pairs have unseen preference headroom."""

import argparse
import json
import os
import random
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import torch
from transformers import AutoTokenizer

from project_paths import (
    RIGHTBRAIN_ON_POLICY_PREFERENCE_V21_DATASET_PATH,
    RIGHTBRAIN_ON_POLICY_PREFERENCE_V21_PROBE_JSON_PATH,
    RIGHTBRAIN_ON_POLICY_PREFERENCE_V21_PROBE_MD_PATH,
    RIGHTBRAIN_ON_POLICY_PREFERENCE_V21_REPORT_JSON_PATH,
)
from train_uruha_rightbrain_contract_v1 import (
    DEFAULT_BASE_MODEL,
    _sha256,
    build_model,
    init_adapter_report,
    resolve_model_dtype,
)
from train_uruha_rightbrain_dpo_v18 import (
    load_preference_rows,
    split_by_source,
    tokenize_pair,
)
from train_uruha_rightbrain_simpo_v19 import disable_dropout, evaluate_simpo


TZ = ZoneInfo("Asia/Tokyo")
DEFAULT_INIT_ADAPTER = "./uruha_rightbrain_plan_sft_lora_v10_expanded_rejection_v1"


def _completion_length_stats(rows):
    chosen = [row["chosen"]["completion_token_count"] for row in rows]
    rejected = [row["rejected"]["completion_token_count"] for row in rows]
    return {
        "pair_count": len(rows),
        "chosen_token_mean": round(sum(chosen) / len(chosen), 4),
        "rejected_token_mean": round(sum(rejected) / len(rejected), 4),
        "chosen_token_min": min(chosen),
        "chosen_token_max": max(chosen),
        "rejected_token_min": min(rejected),
        "rejected_token_max": max(rejected),
    }


def build_probe_decision(dataset_summary, split_summary, train_metrics, eval_metrics):
    eval_rows = eval_metrics["rows"]
    eval_misranked_count = sum(row["raw_preference_margin"] <= 0 for row in eval_rows)
    eval_below_target_count = sum(row["target_reward_margin"] <= 0 for row in eval_rows)
    gates = {
        "dataset_authorized_for_probe": bool(dataset_summary.get("authorize_preference_probe")),
        "train_eval_source_overlap_is_zero": split_summary["source_overlap_count"] == 0,
        "unseen_source_count_at_least_2": len(split_summary["eval_source_ids"]) >= 2,
        "unseen_pair_count_at_least_4": eval_metrics["pair_count"] >= 4,
        "unseen_preference_is_not_saturated": eval_metrics["chosen_preference_rate"] < 1.0,
        "unseen_target_margin_is_not_saturated": eval_metrics["target_margin_rate"] < 1.0,
        "unseen_contains_model_misranking": eval_misranked_count >= 1,
    }
    authorize_training = all(gates.values())
    return {
        "gates": gates,
        "authorize_training": authorize_training,
        "eval_misranked_pair_count": eval_misranked_count,
        "eval_below_target_margin_pair_count": eval_below_target_count,
        "decision_zh": (
            "未見來源仍有 V10 排錯的真實 pair，可進行一次保守的 on-policy SimPO 訓練。"
            if authorize_training
            else "未見來源沒有足夠可學習空間，禁止訓練，避免只把已會的 pair 背得更熟。"
        ),
        "research_boundary": (
            "This probe measures likelihood ranking under the frozen V10 policy. It can block an uninformative "
            "training run, but it cannot prove that preference training will improve generated replies."
        ),
    }


def write_markdown(report, path):
    decision = report["decision"]
    initial_eval = report["initial_eval_preference"]
    lines = [
        "# RightBrain V21 訓練前偏好難度 Probe",
        "",
        "## 結論",
        "",
        decision["decision_zh"],
        "",
        "| 指標 | 結果 |",
        "|---|---:|",
        f"| train pairs | {report['train_pair_count']} |",
        f"| unseen eval pairs | {report['eval_pair_count']} |",
        f"| source overlap | {report['source_overlap_count']} |",
        f"| unseen chosen preference | {100 * initial_eval['chosen_preference_rate']:.1f}% |",
        f"| unseen target-margin pass | {100 * initial_eval['target_margin_rate']:.1f}% |",
        f"| unseen V10 misranked pairs | {decision['eval_misranked_pair_count']} |",
        f"| authorize training | {'YES' if decision['authorize_training'] else 'NO'} |",
        "",
        "## Gate",
        "",
        "| 條件 | 結果 |",
        "|---|---|",
    ]
    for name, passed in decision["gates"].items():
        lines.append(f"| {name} | {'PASS' if passed else 'FAIL'} |")
    lines.extend(["", f"研究邊界：{decision['research_boundary']}", ""])
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default=RIGHTBRAIN_ON_POLICY_PREFERENCE_V21_DATASET_PATH)
    parser.add_argument("--dataset-report", default=RIGHTBRAIN_ON_POLICY_PREFERENCE_V21_REPORT_JSON_PATH)
    parser.add_argument("--base-model", default=DEFAULT_BASE_MODEL)
    parser.add_argument("--init-adapter", default=DEFAULT_INIT_ADAPTER)
    parser.add_argument("--max-length", type=int, default=720)
    parser.add_argument("--eval-source-count", type=int, default=2)
    parser.add_argument("--beta", type=float, default=2.5)
    parser.add_argument("--gamma-beta-ratio", type=float, default=0.1)
    parser.add_argument("--dtype", choices=["auto", "float16", "bfloat16", "float32"], default="auto")
    parser.add_argument("--seed", type=int, default=20260710)
    parser.add_argument("--output-json", default=RIGHTBRAIN_ON_POLICY_PREFERENCE_V21_PROBE_JSON_PATH)
    parser.add_argument("--output-md", default=RIGHTBRAIN_ON_POLICY_PREFERENCE_V21_PROBE_MD_PATH)
    args = parser.parse_args()

    random.seed(args.seed)
    torch.manual_seed(args.seed)
    if torch.backends.mps.is_available():
        torch.mps.manual_seed(args.seed)

    dataset_summary = json.loads(Path(args.dataset_report).read_text(encoding="utf-8"))
    expected_adapter = str(dataset_summary.get("source_adapter_ref") or "")
    actual_adapter = os.path.basename(os.path.abspath(args.init_adapter))
    if expected_adapter != actual_adapter:
        raise ValueError(
            f"Probe adapter must match the on-policy source adapter: {actual_adapter} != {expected_adapter}"
        )

    rows = load_preference_rows(args.dataset)
    train_rows, eval_rows, train_sources, eval_sources = split_by_source(
        rows,
        args.seed,
        args.eval_source_count,
    )
    tokenizer = AutoTokenizer.from_pretrained(args.base_model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"
    tokenized_train = [tokenize_pair(row, tokenizer, args.max_length) for row in train_rows]
    tokenized_eval = [tokenize_pair(row, tokenizer, args.max_length) for row in eval_rows]
    split_summary = {
        "pair_count": len(rows),
        "train_pair_count": len(train_rows),
        "eval_pair_count": len(eval_rows),
        "train_source_ids": train_sources,
        "eval_source_ids": eval_sources,
        "source_overlap_count": len(set(train_sources) & set(eval_sources)),
    }

    started = time.time()
    model = build_model(
        args.base_model,
        args.init_adapter,
        lora_r=32,
        lora_alpha=24,
        lora_dropout=0.08,
        dtype_name=args.dtype,
    )
    disabled_dropout_count = disable_dropout(model)
    device = next(model.parameters()).device
    gamma = args.beta * args.gamma_beta_ratio
    initial_train = evaluate_simpo(model, tokenized_train, device, args.beta, gamma)
    initial_eval = evaluate_simpo(model, tokenized_eval, device, args.beta, gamma)
    decision = build_probe_decision(dataset_summary, split_summary, initial_train, initial_eval)
    report = {
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "scope": "rightbrain_on_policy_preference_v21_pretraining_probe",
        "method": "frozen_v10_length_normalized_preference_probe",
        "method_reference": "https://arxiv.org/abs/2405.14734",
        "base_model": args.base_model,
        "dataset_ref": Path(args.dataset).name,
        "dataset_sha256": _sha256(args.dataset),
        **init_adapter_report(args.init_adapter),
        **split_summary,
        "beta": args.beta,
        "gamma_beta_ratio": args.gamma_beta_ratio,
        "gamma": gamma,
        "seed": args.seed,
        "dtype": str(
            resolve_model_dtype(
                args.dtype,
                torch.cuda.is_available(),
                torch.backends.mps.is_available(),
            )
        ),
        "disabled_dropout_module_count": disabled_dropout_count,
        "duration_seconds": round(time.time() - started, 3),
        "train_completion_lengths": _completion_length_stats(tokenized_train),
        "eval_completion_lengths": _completion_length_stats(tokenized_eval),
        "initial_train_preference": initial_train,
        "initial_eval_preference": initial_eval,
        "decision": decision,
    }
    Path(args.output_json).write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_markdown(report, args.output_md)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if decision["authorize_training"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
