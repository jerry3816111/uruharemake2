#!/usr/bin/env python3
"""Measure V10 group-ranking headroom and cache frozen reference log-probs."""

import argparse
import json
import math
import os
import random
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import torch
from transformers import AutoTokenizer

from project_paths import (
    RIGHTBRAIN_GROUP_PREFERENCE_V26_DATASET_PATH,
    RIGHTBRAIN_GROUP_PREFERENCE_V26_PROBE_JSON_PATH,
    RIGHTBRAIN_GROUP_PREFERENCE_V26_PROBE_MD_PATH,
    RIGHTBRAIN_GROUP_PREFERENCE_V26_REPORT_JSON_PATH,
)
from train_uruha_rightbrain_contract_v1 import (
    DEFAULT_BASE_MODEL,
    _sha256,
    build_model,
    init_adapter_report,
    resolve_model_dtype,
)
from train_uruha_rightbrain_dpo_v18 import _tokenize_completion, split_by_source
from train_uruha_rightbrain_simpo_v19 import (
    completion_average_log_prob,
    disable_dropout,
)


TZ = ZoneInfo("Asia/Tokyo")
DEFAULT_INIT_ADAPTER = "./uruha_rightbrain_plan_sft_lora_v10_expanded_rejection_v1"


def load_groups(path):
    groups = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(groups, list) or not groups:
        raise ValueError("Group preference dataset must be a non-empty JSON list")
    seen_group_ids = set()
    seen_candidate_ids = set()
    for group in groups:
        group_id = str(group.get("id") or "")
        if not group_id or group_id in seen_group_ids:
            raise ValueError(f"Missing or duplicate group id: {group_id!r}")
        if not group.get("source_case_id") or len(group.get("prompt_messages") or []) != 2:
            raise ValueError(f"Invalid group prompt/source: {group_id}")
        positives = group.get("positives") or []
        negatives = group.get("negatives") or []
        if not positives or not negatives:
            raise ValueError(f"Group lacks positive or negative candidates: {group_id}")
        texts = []
        for candidate in [*positives, *negatives]:
            candidate_id = str(candidate.get("id") or "")
            text = str(candidate.get("text") or "").strip()
            if not candidate_id or candidate_id in seen_candidate_ids or not text:
                raise ValueError(f"Invalid candidate in group {group_id}: {candidate_id!r}")
            seen_candidate_ids.add(candidate_id)
            texts.append(text)
        if len(texts) != len(set(texts)):
            raise ValueError(f"Duplicate response text inside group: {group_id}")
        seen_group_ids.add(group_id)
    return groups


def tokenize_group(group, tokenizer, max_length):
    responses = []
    for label, candidates in (
        ("positive", group["positives"]),
        ("negative", group["negatives"]),
    ):
        for candidate in candidates:
            responses.append(
                {
                    "id": candidate["id"],
                    "label": label,
                    "text": candidate["text"],
                    "sequence": _tokenize_completion(
                        group["prompt_messages"],
                        candidate["text"],
                        tokenizer,
                        max_length,
                    ),
                }
            )
    return {
        "id": group["id"],
        "source_case_id": group["source_case_id"],
        "source_prompt_id": group["source_prompt_id"],
        "responses": responses,
    }


def evaluate_absolute_groups(model, groups, device):
    model.eval()
    output_groups = []
    positive_log_probs = []
    negative_log_probs = []
    total_pairs = correct_pairs = tie_pairs = 0
    top_positive_count = strict_separation_count = 0
    positive_mass_total = mean_margin_total = 0.0
    with torch.no_grad():
        for group in groups:
            rows = []
            for response in group["responses"]:
                value = float(
                    completion_average_log_prob(
                        model,
                        response["sequence"],
                        device,
                    )
                    .detach()
                    .cpu()
                    .item()
                )
                rows.append(
                    {
                        "id": response["id"],
                        "label": response["label"],
                        "average_log_prob": value,
                        "completion_token_count": response["sequence"][
                            "completion_token_count"
                        ],
                    }
                )
                if torch.backends.mps.is_available():
                    torch.mps.empty_cache()

            positives = [row["average_log_prob"] for row in rows if row["label"] == "positive"]
            negatives = [row["average_log_prob"] for row in rows if row["label"] == "negative"]
            scores = torch.tensor([row["average_log_prob"] for row in rows], dtype=torch.float64)
            probability = torch.softmax(scores, dim=0)
            positive_mass = float(
                sum(
                    probability[index]
                    for index, row in enumerate(rows)
                    if row["label"] == "positive"
                )
            )
            pair_count = len(positives) * len(negatives)
            pair_correct = sum(p > n for p in positives for n in negatives)
            pair_ties = sum(p == n for p in positives for n in negatives)
            top_positive = max(positives) > max(negatives)
            strict_separation = min(positives) > max(negatives)
            mean_margin = sum(positives) / len(positives) - sum(negatives) / len(negatives)
            total_pairs += pair_count
            correct_pairs += pair_correct
            tie_pairs += pair_ties
            top_positive_count += int(top_positive)
            strict_separation_count += int(strict_separation)
            positive_mass_total += positive_mass
            mean_margin_total += mean_margin
            positive_log_probs.extend(positives)
            negative_log_probs.extend(negatives)
            output_groups.append(
                {
                    "id": group["id"],
                    "source_case_id": group["source_case_id"],
                    "source_prompt_id": group["source_prompt_id"],
                    "positive_count": len(positives),
                    "negative_count": len(negatives),
                    "pair_count": pair_count,
                    "pairwise_positive_preference_rate": pair_correct / pair_count,
                    "positive_top1": top_positive,
                    "strict_positive_separation": strict_separation,
                    "positive_probability_mass": positive_mass,
                    "mean_positive_negative_margin": mean_margin,
                    "responses": rows,
                }
            )
    group_count = len(output_groups)
    all_values = [*positive_log_probs, *negative_log_probs]
    return {
        "group_count": group_count,
        "candidate_count": len(all_values),
        "positive_candidate_count": len(positive_log_probs),
        "negative_candidate_count": len(negative_log_probs),
        "pair_count": total_pairs,
        "pairwise_positive_preference_rate": correct_pairs / total_pairs,
        "pairwise_tie_rate": tie_pairs / total_pairs,
        "positive_top1_rate": top_positive_count / group_count,
        "strict_positive_separation_rate": strict_separation_count / group_count,
        "mean_positive_probability_mass": positive_mass_total / group_count,
        "mean_positive_negative_margin": mean_margin_total / group_count,
        "mean_positive_average_log_prob": sum(positive_log_probs) / len(positive_log_probs),
        "mean_negative_average_log_prob": sum(negative_log_probs) / len(negative_log_probs),
        "all_log_probs_finite": all(math.isfinite(value) for value in all_values),
        "groups": output_groups,
    }


def build_probe_decision(dataset_summary, split_summary, eval_metrics):
    misranked_pair_count = round(
        eval_metrics["pair_count"]
        * (1.0 - eval_metrics["pairwise_positive_preference_rate"])
    )
    gates = {
        "dataset_authorized_for_group_probe": bool(
            dataset_summary.get("authorize_group_probe")
        ),
        "train_eval_source_overlap_is_zero": split_summary["source_overlap_count"] == 0,
        "unseen_source_count_at_least_2": len(split_summary["eval_source_ids"]) >= 2,
        "train_group_count_at_least_6": split_summary["train_group_count"] >= 6,
        "unseen_group_count_at_least_3": eval_metrics["group_count"] >= 3,
        "unseen_candidate_count_at_least_18": eval_metrics["candidate_count"] >= 18,
        "all_reference_log_probs_are_finite": eval_metrics["all_log_probs_finite"],
        "unseen_pairwise_preference_is_not_saturated": eval_metrics[
            "pairwise_positive_preference_rate"
        ]
        < 1.0,
        "unseen_contains_at_least_3_misranked_pairs": misranked_pair_count >= 3,
    }
    authorize_training = all(gates.values())
    return {
        "gates": gates,
        "authorize_group_training": authorize_training,
        "eval_misranked_pair_count": misranked_pair_count,
        "decision_zh": (
            "未見來源含多個 V10 錯排回答，固定 reference 已建立，可進行一次保守的群組偏好訓練。"
            if authorize_training
            else "未見群組缺乏可學習空間或 reference 證據不完整，禁止訓練。"
        ),
        "research_boundary": (
            "This probe measures frozen V10 likelihood over unordered positive and negative response sets. "
            "It establishes training headroom and reference scores, not generated-response improvement."
        ),
    }


def write_markdown(report, path):
    decision = report["decision"]
    evaluation = report["initial_eval_absolute_group_metrics"]
    lines = [
        "# RightBrain V26 群組訓練前 Probe",
        "",
        "## 結論",
        "",
        decision["decision_zh"],
        "",
        "| 未見指標 | 結果 |",
        "|---|---:|",
        f"| 群組 | {evaluation['group_count']} |",
        f"| 回答 | {evaluation['candidate_count']} |",
        f"| 正負配對 | {evaluation['pair_count']} |",
        f"| V10 正回答勝率 | {evaluation['pairwise_positive_preference_rate']:.1%} |",
        f"| V10 錯排 pair | {decision['eval_misranked_pair_count']} |",
        f"| 正回答為組內最高 | {evaluation['positive_top1_rate']:.1%} |",
        f"| authorize training | {'YES' if decision['authorize_group_training'] else 'NO'} |",
        "",
        "## Gate",
        "",
        "| 條件 | 結果 |",
        "|---|---|",
    ]
    for name, passed in decision["gates"].items():
        lines.append(f"| {name} | {'PASS' if passed else 'FAIL'} |")
    lines.extend(["", "研究邊界：" + decision["research_boundary"], ""])
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default=RIGHTBRAIN_GROUP_PREFERENCE_V26_DATASET_PATH)
    parser.add_argument("--dataset-report", default=RIGHTBRAIN_GROUP_PREFERENCE_V26_REPORT_JSON_PATH)
    parser.add_argument("--base-model", default=DEFAULT_BASE_MODEL)
    parser.add_argument("--init-adapter", default=DEFAULT_INIT_ADAPTER)
    parser.add_argument("--max-length", type=int, default=720)
    parser.add_argument("--eval-source-count", type=int, default=2)
    parser.add_argument("--dtype", choices=["auto", "float16", "bfloat16", "float32"], default="auto")
    parser.add_argument("--seed", type=int, default=20260710)
    parser.add_argument("--output-json", default=RIGHTBRAIN_GROUP_PREFERENCE_V26_PROBE_JSON_PATH)
    parser.add_argument("--output-md", default=RIGHTBRAIN_GROUP_PREFERENCE_V26_PROBE_MD_PATH)
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

    groups = load_groups(args.dataset)
    train_groups, eval_groups, train_sources, eval_sources = split_by_source(
        groups,
        args.seed,
        args.eval_source_count,
    )
    tokenizer = AutoTokenizer.from_pretrained(args.base_model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"
    tokenized_train = [tokenize_group(group, tokenizer, args.max_length) for group in train_groups]
    tokenized_eval = [tokenize_group(group, tokenizer, args.max_length) for group in eval_groups]
    split_summary = {
        "group_count": len(groups),
        "train_group_count": len(train_groups),
        "eval_group_count": len(eval_groups),
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
    initial_train = evaluate_absolute_groups(model, tokenized_train, device)
    initial_eval = evaluate_absolute_groups(model, tokenized_eval, device)
    decision = build_probe_decision(dataset_summary, split_summary, initial_eval)
    report = {
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "scope": "rightbrain_group_preference_v26_pretraining_probe",
        "method": "frozen_v10_length_normalized_group_reference_probe",
        "method_references": [
            "https://arxiv.org/abs/2604.15602",
            "https://proceedings.mlr.press/v267/gupta25c.html",
        ],
        "base_model": args.base_model,
        "dataset_ref": Path(args.dataset).name,
        "dataset_sha256": _sha256(args.dataset),
        "dataset_report_ref": Path(args.dataset_report).name,
        "dataset_report_sha256": _sha256(args.dataset_report),
        **init_adapter_report(args.init_adapter),
        "init_adapter_model_sha256": _sha256(
            Path(args.init_adapter) / "adapter_model.safetensors"
        ),
        **split_summary,
        "seed": args.seed,
        "max_length": args.max_length,
        "dtype": str(
            resolve_model_dtype(
                args.dtype,
                torch.cuda.is_available(),
                torch.backends.mps.is_available(),
            )
        ),
        "disabled_dropout_module_count": disabled_dropout_count,
        "duration_seconds": round(time.time() - started, 3),
        "initial_train_absolute_group_metrics": initial_train,
        "initial_eval_absolute_group_metrics": initial_eval,
        "decision": decision,
    }
    Path(args.output_json).write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_markdown(report, args.output_md)
    print(
        json.dumps(
            {
                "train_group_count": len(train_groups),
                "eval_group_count": len(eval_groups),
                "eval_candidate_count": initial_eval["candidate_count"],
                "eval_pairwise_positive_preference_rate": initial_eval[
                    "pairwise_positive_preference_rate"
                ],
                "eval_misranked_pair_count": decision["eval_misranked_pair_count"],
                "authorize_group_training": decision["authorize_group_training"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if decision["authorize_group_training"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
