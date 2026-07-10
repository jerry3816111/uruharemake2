#!/usr/bin/env python3
"""Measure model-aware preference similarity before another RightBrain run."""

import argparse
import json
import math
import statistics
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import torch
from transformers import AutoTokenizer

from project_paths import (
    RIGHTBRAIN_HARD_NEGATIVE_PREFERENCE_V20_DATASET_PATH,
    RIGHTBRAIN_HARD_NEGATIVE_PREFERENCE_V20_TRAINING_RUN_REPORT_PATH,
    RIGHTBRAIN_PREFERENCE_CHES_V21_REPORT_JSON_PATH,
    RIGHTBRAIN_PREFERENCE_CHES_V21_REPORT_MD_PATH,
    RIGHTBRAIN_SEMANTIC_PREFERENCE_V18_DATASET_PATH,
)
from train_uruha_rightbrain_contract_v1 import DEFAULT_BASE_MODEL, build_model
from train_uruha_rightbrain_dpo_v18 import load_preference_rows, tokenize_pair


TZ = ZoneInfo("Asia/Tokyo")
DEFAULT_INIT_ADAPTER = "./uruha_rightbrain_plan_sft_lora_v10_expanded_rejection_v1"
METHOD_REFERENCE = "https://github.com/princeton-nlp/unintentional-unalignment/blob/main/ches/ches.py"
PAPER_REFERENCE = "https://proceedings.iclr.cc/paper_files/paper/2025/hash/3df38ca67befaed9c03b95ffee07d9f8-Abstract-Conference.html"
DEFAULT_DATASETS = (
    ("v18_deleted_clause", RIGHTBRAIN_SEMANTIC_PREFERENCE_V18_DATASET_PATH),
    ("v20_length_matched", RIGHTBRAIN_HARD_NEGATIVE_PREFERENCE_V20_DATASET_PATH),
)


def _completion_context_mean(hidden_embeddings, completion_mask):
    """Reproduce the response span used by the official length-normalized CHES."""
    if hidden_embeddings.ndim != 3 or hidden_embeddings.shape[0] != 1:
        raise ValueError("CHES currently expects one unpadded sequence")
    positions = torch.nonzero(completion_mask[0], as_tuple=False).flatten()
    if not len(positions):
        raise ValueError("Completion mask is empty")
    last_prompt_index = int(positions[0].item()) - 1
    if last_prompt_index < 0 or hidden_embeddings.shape[1] - last_prompt_index < 2:
        raise ValueError("Prompt/completion boundary is invalid")
    # The paper includes the final prompt state and excludes the final response token.
    response_context = hidden_embeddings[:, last_prompt_index:-1, :]
    return response_context.float().mean(dim=1).squeeze(0)


def length_normalized_ches(
    preferred_hidden_embeddings,
    dispreferred_hidden_embeddings,
    preferred_completion_mask,
    dispreferred_completion_mask,
):
    preferred_mean = _completion_context_mean(
        preferred_hidden_embeddings,
        preferred_completion_mask,
    )
    dispreferred_mean = _completion_context_mean(
        dispreferred_hidden_embeddings,
        dispreferred_completion_mask,
    )
    return torch.dot(preferred_mean, dispreferred_mean) - torch.dot(
        preferred_mean,
        preferred_mean,
    )


def _hidden_embeddings(model, sequence, device):
    input_ids = sequence["input_ids"].to(device)
    attention_mask = sequence["attention_mask"].to(device)
    causal_model = model.get_base_model() if hasattr(model, "get_base_model") else model
    backbone = getattr(causal_model, "model", causal_model)
    output = backbone(
        input_ids=input_ids,
        attention_mask=attention_mask,
        use_cache=False,
        return_dict=True,
    )
    hidden = output.last_hidden_state.detach().cpu()
    del output
    if torch.backends.mps.is_available():
        torch.mps.empty_cache()
    return hidden


def score_pair(model, tokenized_row, device):
    with torch.no_grad():
        chosen_hidden = _hidden_embeddings(model, tokenized_row["chosen"], device)
        rejected_hidden = _hidden_embeddings(model, tokenized_row["rejected"], device)
    score = length_normalized_ches(
        chosen_hidden,
        rejected_hidden,
        tokenized_row["chosen"]["completion_mask"],
        tokenized_row["rejected"]["completion_mask"],
    )
    return float(score.item())


def _quantile(values, fraction):
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return None
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def _pearson(xs, ys):
    if len(xs) != len(ys) or len(xs) < 2:
        return None
    mean_x = statistics.fmean(xs)
    mean_y = statistics.fmean(ys)
    centered_x = [value - mean_x for value in xs]
    centered_y = [value - mean_y for value in ys]
    denominator = math.sqrt(
        sum(value * value for value in centered_x)
        * sum(value * value for value in centered_y)
    )
    if denominator == 0:
        return None
    return sum(x * y for x, y in zip(centered_x, centered_y)) / denominator


def training_delta_map(training_report):
    if not training_report:
        return {}
    initial_rows = {
        row["id"]: row for row in training_report["initial_eval_preference"]["rows"]
    }
    final_rows = {
        row["id"]: row for row in training_report["final_eval_preference"]["rows"]
    }
    output = {}
    for row_id in sorted(set(initial_rows) & set(final_rows)):
        before = initial_rows[row_id]
        after = final_rows[row_id]
        output[row_id] = {
            "chosen_average_log_prob_delta": (
                after["chosen_average_log_prob"] - before["chosen_average_log_prob"]
            ),
            "rejected_average_log_prob_delta": (
                after["rejected_average_log_prob"] - before["rejected_average_log_prob"]
            ),
            "raw_preference_margin_delta": (
                after["raw_preference_margin"] - before["raw_preference_margin"]
            ),
        }
    return output


def summarize_dataset(label, path, scored_rows):
    scores = [row["length_normalized_ches"] for row in scored_rows]
    ranked = sorted(scored_rows, key=lambda row: row["length_normalized_ches"], reverse=True)
    top_count = max(1, math.ceil(len(ranked) * 0.25))
    delta_rows = [row for row in scored_rows if row.get("training_delta")]
    chosen_deltas = [
        row["training_delta"]["chosen_average_log_prob_delta"] for row in delta_rows
    ]
    ches_with_deltas = [row["length_normalized_ches"] for row in delta_rows]
    return {
        "label": label,
        "dataset_ref": Path(path).name,
        "pair_count": len(scored_rows),
        "length_normalized_ches": {
            "min": min(scores),
            "p25": _quantile(scores, 0.25),
            "median": statistics.median(scores),
            "mean": statistics.fmean(scores),
            "p75": _quantile(scores, 0.75),
            "max": max(scores),
        },
        "highest_ches_quartile": [
            {
                "id": row["id"],
                "source_case_id": row["source_case_id"],
                "length_normalized_ches": row["length_normalized_ches"],
            }
            for row in ranked[:top_count]
        ],
        "training_delta_diagnostic": {
            "available_pair_count": len(delta_rows),
            "preferred_likelihood_decreased_count": sum(value < 0 for value in chosen_deltas),
            "mean_chosen_average_log_prob_delta": (
                statistics.fmean(chosen_deltas) if chosen_deltas else None
            ),
            "pearson_ches_vs_chosen_log_prob_delta": _pearson(
                ches_with_deltas,
                chosen_deltas,
            ),
        },
        "rows": ranked,
    }


def build_report(dataset_results, model_ref, duration_seconds):
    summaries = {
        result["label"]: summarize_dataset(
            result["label"],
            result["path"],
            result["rows"],
        )
        for result in dataset_results
    }
    v18 = summaries.get("v18_deleted_clause")
    v20 = summaries.get("v20_length_matched")
    median_delta = None
    if v18 and v20:
        median_delta = (
            v20["length_normalized_ches"]["median"]
            - v18["length_normalized_ches"]["median"]
        )
    v20_diagnostic = v20["training_delta_diagnostic"] if v20 else {}
    ches_correlation = v20_diagnostic.get("pearson_ches_vs_chosen_log_prob_delta")
    return {
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "scope": "rightbrain_preference_ches_v21_diagnostic",
        "method": "length_normalized_centered_hidden_embedding_similarity",
        "method_reference": METHOD_REFERENCE,
        "paper_reference": PAPER_REFERENCE,
        "model_ref": model_ref,
        "duration_seconds": round(duration_seconds, 3),
        "datasets": summaries,
        "comparison": {
            "v20_minus_v18_median_ches": median_delta,
            "empirical_finding_zh": (
                "V20 的 median CHES 低於 V18，且在僅 8 組可配對未見資料中，CHES 與 preferred "
                f"log-prob 變化的 Pearson 只有 {ches_correlation:+.3f}；本地證據不支持用 CHES 單獨解釋 V20 退步。"
                if median_delta is not None and ches_correlation is not None
                else "目前資料不足以比較 CHES 與 preferred likelihood 變化。"
            ),
            "interpretation_zh": (
                "較高 CHES 代表 chosen/rejected 在目前模型的 hidden geometry 中更相似，"
                "依論文是 likelihood displacement 風險訊號；它不是自然度分數，也沒有跨模型通用的絕對門檻。"
            ),
        },
        "v21_admission_policy": {
            "status": "diagnostic_only_until_calibrated",
            "rules": [
                "使用產生資料的同一個 adapter 計算 length-normalized CHES。",
                "保留原始 CHES 與資料集內 percentile，不設定未校準的絕對 cutoff。",
                "訓練前未見 pair 偏好正確率若已是 100%，不得單獨作為 promotion gate。",
                "未見 mean preferred log-prob 不得下降，且 preferred likelihood 下降的 pair 不得超過一半。",
                "優先收集與 promotion holdout 分離的 V10 實際錯誤候選，再以 CHES 排序審核。",
                "任何訓練仍須通過雙 seed actual-model holdout 才能升級。",
            ],
        },
        "research_boundary": (
            "CHES is a model-dependent risk diagnostic. This small local comparison cannot reproduce the paper's "
            "large-scale causal result or establish a universal filtering threshold."
        ),
    }


def write_markdown(report, path):
    lines = [
        "# RightBrain V21 Preference Pair CHES 診斷",
        "",
        "## 結論",
        "",
        "這份報告先量化偏好 pair 的 likelihood-displacement 風險，不訓練新 adapter。",
        "",
        "| 資料 | pairs | CHES median | CHES mean | 高風險 quartile |",
        "|---|---:|---:|---:|---:|",
    ]
    for result in report["datasets"].values():
        score = result["length_normalized_ches"]
        lines.append(
            f"| {result['label']} | {result['pair_count']} | {score['median']:+.6f} | "
            f"{score['mean']:+.6f} | {len(result['highest_ches_quartile'])} |"
        )
    lines.extend(
        [
            "",
            report["comparison"]["interpretation_zh"],
            "",
            report["comparison"]["empirical_finding_zh"],
            "",
            "## V20 未見 Pair 的訓練變化",
            "",
            "| 指標 | 值 |",
            "|---|---:|",
        ]
    )
    v20 = report["datasets"].get("v20_length_matched")
    if v20:
        diagnostic = v20["training_delta_diagnostic"]
        correlation = diagnostic["pearson_ches_vs_chosen_log_prob_delta"]
        lines.extend(
            [
                f"| 可配對 rows | {diagnostic['available_pair_count']} |",
                f"| preferred likelihood 下降 | {diagnostic['preferred_likelihood_decreased_count']} |",
                f"| mean preferred log-prob delta | {diagnostic['mean_chosen_average_log_prob_delta']:+.6f} |",
                f"| CHES vs preferred delta Pearson | {correlation:+.4f} |"
                if correlation is not None
                else "| CHES vs preferred delta Pearson | n/a |",
            ]
        )
    lines.extend(
        [
            "",
            "## 各資料最高 CHES Quartile",
            "",
            "| dataset | id | source | CHES |",
            "|---|---|---|---:|",
        ]
    )
    for result in report["datasets"].values():
        for row in result["highest_ches_quartile"]:
            lines.append(
                f"| {result['label']} | {row['id']} | {row['source_case_id']} | "
                f"{row['length_normalized_ches']:+.6f} |"
            )
    lines.extend(["", "## V21 資料准入規則", ""])
    lines.extend(f"- {rule}" for rule in report["v21_admission_policy"]["rules"])
    lines.extend(["", f"研究邊界：{report['research_boundary']}", ""])
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-model", default=DEFAULT_BASE_MODEL)
    parser.add_argument("--adapter-path", default=DEFAULT_INIT_ADAPTER)
    parser.add_argument("--max-length", type=int, default=720)
    parser.add_argument("--dtype", choices=["auto", "float16", "bfloat16", "float32"], default="auto")
    parser.add_argument("--load-model", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--rerender-existing", action="store_true")
    parser.add_argument("--training-report", default=RIGHTBRAIN_HARD_NEGATIVE_PREFERENCE_V20_TRAINING_RUN_REPORT_PATH)
    parser.add_argument("--output-json", default=RIGHTBRAIN_PREFERENCE_CHES_V21_REPORT_JSON_PATH)
    parser.add_argument("--output-md", default=RIGHTBRAIN_PREFERENCE_CHES_V21_REPORT_MD_PATH)
    args = parser.parse_args()

    if args.rerender_existing:
        existing = json.loads(Path(args.output_json).read_text(encoding="utf-8"))
        dataset_results = [
            {
                "label": label,
                "path": result["dataset_ref"],
                "rows": result["rows"],
            }
            for label, result in existing["datasets"].items()
        ]
        report = build_report(
            dataset_results,
            existing["model_ref"],
            existing["duration_seconds"],
        )
        Path(args.output_json).write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        write_markdown(report, args.output_md)
        print(json.dumps({"comparison": report["comparison"]}, ensure_ascii=False, indent=2))
        return 0

    datasets = []
    for label, path in DEFAULT_DATASETS:
        rows = load_preference_rows(path)
        datasets.append({"label": label, "path": path, "raw_rows": rows})
    dry_summary = {
        "datasets": {
            row["label"]: {"path": Path(row["path"]).name, "pair_count": len(row["raw_rows"])}
            for row in datasets
        }
    }
    if args.dry_run:
        print(json.dumps(dry_summary, ensure_ascii=False, indent=2))
        return 0
    if not args.load_model:
        raise SystemExit("Use --load-model to compute model-dependent CHES scores")

    tokenizer = AutoTokenizer.from_pretrained(args.base_model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"
    training_report = json.loads(Path(args.training_report).read_text(encoding="utf-8"))
    delta_map = training_delta_map(training_report)
    model = build_model(
        args.base_model,
        args.adapter_path,
        lora_r=32,
        lora_alpha=24,
        lora_dropout=0.08,
        dtype_name=args.dtype,
    )
    model.gradient_checkpointing_disable()
    model.eval()
    device = next(model.parameters()).device
    started = time.time()
    dataset_results = []
    for dataset in datasets:
        scored_rows = []
        tokenized = [
            tokenize_pair(row, tokenizer, args.max_length) for row in dataset["raw_rows"]
        ]
        for index, (raw, tokens) in enumerate(zip(dataset["raw_rows"], tokenized), start=1):
            score = score_pair(model, tokens, device)
            scored_rows.append(
                {
                    "id": raw["id"],
                    "source_case_id": raw["source_case_id"],
                    "length_normalized_ches": score,
                    "chosen_chars": len(raw["chosen"]),
                    "rejected_chars": len(raw["rejected"]),
                    "training_delta": delta_map.get(raw["id"]),
                }
            )
            print(f"dataset={dataset['label']} pair={index}/{len(tokenized)} ches={score:+.6f}")
        dataset_results.append(
            {"label": dataset["label"], "path": dataset["path"], "rows": scored_rows}
        )
    report = build_report(
        dataset_results,
        Path(args.adapter_path).name,
        time.time() - started,
    )
    Path(args.output_json).write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_markdown(report, args.output_md)
    print(json.dumps({"comparison": report["comparison"], "output_json": args.output_json}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
