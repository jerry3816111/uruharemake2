#!/usr/bin/env python3
"""Measure frozen V10 agreement with evidence-bound V30 human preferences."""

import argparse
import json
import math
import statistics
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import torch
from scipy.stats import binomtest
from transformers import AutoTokenizer

from build_rightbrain_human_on_policy_preference_v30 import (
    load_authorized_probe_rows,
)
from project_paths import (
    RIGHTBRAIN_HUMAN_ON_POLICY_PREFERENCE_V30_DATASET_PATH,
    RIGHTBRAIN_HUMAN_ON_POLICY_PREFERENCE_V30_REPORT_JSON_PATH,
    RIGHTBRAIN_HUMAN_PREFERENCE_V31_PROBE_JSON_PATH,
    RIGHTBRAIN_HUMAN_PREFERENCE_V31_PROBE_MD_PATH,
    RIGHTBRAIN_ON_POLICY_V29_BLIND_KEY_PATH,
    RIGHTBRAIN_ON_POLICY_V29_BLIND_PACKAGE_PATH,
    RIGHTBRAIN_ON_POLICY_V29_RATINGS_PATH,
)
from train_uruha_rightbrain_contract_v1 import (
    DEFAULT_BASE_MODEL,
    _sha256,
    build_model,
    init_adapter_report,
    resolve_model_dtype,
)
from train_uruha_rightbrain_dpo_v18 import tokenize_pair
from train_uruha_rightbrain_simpo_v19 import (
    completion_average_log_prob,
    disable_dropout,
)


TZ = ZoneInfo("Asia/Tokyo")
FORMAL_V10_ADAPTER = "uruha_rightbrain_plan_sft_lora_v10_expanded_rejection_v1"
DEFAULT_INIT_ADAPTER = f"./{FORMAL_V10_ADAPTER}"
MIN_INDEPENDENT_MISRANKED_SOURCES = 2
METHOD_REFERENCES = (
    "https://arxiv.org/abs/2305.18290",
    "https://arxiv.org/abs/2405.14734",
    "https://arxiv.org/abs/2403.04132",
    "https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.binomtest.html",
)


def _rate(numerator, denominator):
    return numerator / denominator if denominator else None


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


def build_adapter_evidence(rows, init_adapter):
    adapter_path = Path(init_adapter)
    model_path = adapter_path / "adapter_model.safetensors"
    config_path = adapter_path / "adapter_config.json"
    source_refs = sorted({str(row.get("on_policy_adapter_ref") or "") for row in rows})
    source_shas = sorted(
        {str(row.get("on_policy_adapter_sha256") or "") for row in rows}
    )
    local_model_sha = _sha256(model_path) if model_path.is_file() else ""
    local_ref = adapter_path.name
    gates = {
        "all_rows_bind_one_adapter_ref": source_refs == [FORMAL_V10_ADAPTER],
        "all_rows_bind_one_adapter_sha": len(source_shas) == 1
        and bool(source_shas[0]),
        "local_adapter_ref_is_formal_v10": local_ref == FORMAL_V10_ADAPTER,
        "local_adapter_model_exists": model_path.is_file(),
        "local_adapter_config_exists": config_path.is_file(),
        "local_adapter_sha_matches_human_candidates": len(source_shas) == 1
        and local_model_sha == source_shas[0],
    }
    return {
        "source_adapter_refs": source_refs,
        "source_adapter_model_sha256": source_shas,
        "local_adapter_ref": local_ref,
        "local_adapter_model_sha256": local_model_sha,
        "gates": gates,
    }


def score_frozen_pairs(model, tokenized_rows, source_rows, device):
    source_map = {row["id"]: row for row in source_rows}
    model.eval()
    output = []
    with torch.inference_mode():
        for tokenized in tokenized_rows:
            source = source_map[tokenized["id"]]
            chosen = completion_average_log_prob(model, tokenized["chosen"], device)
            rejected = completion_average_log_prob(
                model,
                tokenized["rejected"],
                device,
            )
            chosen_score = float(chosen.detach().cpu().item())
            rejected_score = float(rejected.detach().cpu().item())
            margin = chosen_score - rejected_score
            if margin > 0:
                status = "v10_agrees_with_human"
            elif margin < 0:
                status = "v10_misranks_human_choice"
            else:
                status = "v10_exact_tie"
            evidence = source["human_preference_evidence"]
            output.append(
                {
                    "id": source["id"],
                    "source_case_id": source["source_case_id"],
                    "source_family": source["source_family"],
                    "category": source["category"],
                    "comparison_id": evidence["comparison_id"],
                    "chosen_candidate_id": evidence["chosen_candidate_id"],
                    "rejected_candidate_id": evidence["rejected_candidate_id"],
                    "chosen_average_log_prob": chosen_score,
                    "rejected_average_log_prob": rejected_score,
                    "raw_preference_margin": margin,
                    "chosen_completion_token_count": tokenized["chosen"][
                        "completion_token_count"
                    ],
                    "rejected_completion_token_count": tokenized["rejected"][
                        "completion_token_count"
                    ],
                    "signed_completion_token_gap": tokenized["chosen"][
                        "completion_token_count"
                    ]
                    - tokenized["rejected"]["completion_token_count"],
                    "status": status,
                }
            )
            if torch.backends.mps.is_available():
                torch.mps.empty_cache()
    return output


def preference_statistics(scored_rows, confidence_level=0.95):
    if not scored_rows:
        raise ValueError("Frozen preference probe requires at least one scored pair")
    margins = [float(row["raw_preference_margin"]) for row in scored_rows]
    if not all(math.isfinite(value) for value in margins):
        raise ValueError("Frozen preference probe contains a non-finite margin")
    positive_count = sum(value > 0 for value in margins)
    negative_count = sum(value < 0 for value in margins)
    tie_count = len(margins) - positive_count - negative_count
    decisive_count = positive_count + negative_count
    if decisive_count:
        exact_greater = binomtest(
            positive_count,
            decisive_count,
            p=0.5,
            alternative="greater",
        )
        exact_two_sided = binomtest(
            positive_count,
            decisive_count,
            p=0.5,
            alternative="two-sided",
        )
        interval = exact_two_sided.proportion_ci(
            confidence_level=confidence_level,
            method="exact",
        )
        exact_pvalue = float(exact_greater.pvalue)
        exact_ci = [float(interval.low), float(interval.high)]
    else:
        exact_pvalue = 1.0
        exact_ci = [0.0, 1.0]
    token_gaps = [float(row["signed_completion_token_gap"]) for row in scored_rows]
    return {
        "pair_count": len(scored_rows),
        "v10_agrees_with_human_count": positive_count,
        "v10_misranked_count": negative_count,
        "v10_exact_tie_count": tie_count,
        "decisive_model_pair_count": decisive_count,
        "v10_human_agreement_rate_all_pairs": _rate(
            positive_count,
            len(scored_rows),
        ),
        "v10_human_agreement_rate_decisive_pairs": _rate(
            positive_count,
            decisive_count,
        ),
        "agreement_rate_exact_ci": exact_ci,
        "agreement_rate_ci_alternative": "two-sided",
        "agreement_greater_than_chance_exact_pvalue": exact_pvalue,
        "confidence_level": confidence_level,
        "mean_raw_preference_margin": statistics.fmean(margins),
        "median_raw_preference_margin": statistics.median(margins),
        "min_raw_preference_margin": min(margins),
        "max_raw_preference_margin": max(margins),
        "mean_signed_completion_token_gap": statistics.fmean(token_gaps),
        "pearson_margin_vs_signed_token_gap": _pearson(margins, token_gaps),
    }


def build_probe_report(
    dataset_report,
    adapter_evidence,
    scored_rows,
    *,
    model_metadata=None,
    duration_seconds=0.0,
):
    model_metadata = model_metadata or {}
    statistics_summary = preference_statistics(scored_rows)
    source_ids = [row["source_case_id"] for row in scored_rows]
    source_families = {row["source_family"] for row in scored_rows}
    categories = {row["category"] for row in scored_rows}
    misranked_rows = [
        row for row in scored_rows if row["raw_preference_margin"] < 0
    ]
    misranked_sources = {row["source_case_id"] for row in misranked_rows}
    misranked_categories = {row["category"] for row in misranked_rows}
    gates = {
        "v30_report_authorizes_only_probe": bool(
            dataset_report.get("authorize_preference_probe")
        )
        and not dataset_report.get("authorize_training")
        and not dataset_report.get("authorize_runtime_promotion"),
        "all_v30_dataset_gates_pass": bool(dataset_report.get("gates"))
        and all(dataset_report["gates"].values()),
        "pair_count_matches_v30_report": len(scored_rows)
        == dataset_report.get("pair_count"),
        "source_family_count_matches_v30_report": len(source_families)
        == dataset_report.get("source_family_count"),
        "source_case_ids_are_unique": len(source_ids) == len(set(source_ids)),
        "all_scores_are_finite": all(
            math.isfinite(row["raw_preference_margin"]) for row in scored_rows
        ),
        "model_is_fully_frozen": model_metadata.get(
            "trainable_parameter_count_after_freeze"
        )
        == 0,
        **adapter_evidence["gates"],
    }
    evidence_valid = all(gates.values())
    headroom_detected = bool(misranked_rows)
    authorize_ablation = (
        evidence_valid
        and len(misranked_sources) >= MIN_INDEPENDENT_MISRANKED_SOURCES
    )
    if not evidence_valid:
        status = "invalid_evidence"
        decision_zh = "V30 或正式 V10 證據不一致；停止，不得使用這份 probe。"
    elif not headroom_detected:
        status = "development_pairs_saturated"
        decision_zh = (
            "正式 V10 已在全部真人 development pairs 上給人選答案較高平均機率；"
            "這批資料沒有可見 headroom，不應直接重訓，應先收集更難的新來源。"
        )
    elif not authorize_ablation:
        status = "isolated_preference_conflict"
        decision_zh = (
            "只觀察到單一獨立來源的 V10 排錯；可能是個案或標註波動，"
            "先補獨立來源，不啟動訓練。"
        )
    else:
        status = "controlled_ablation_candidate"
        decision_zh = (
            "至少兩個獨立來源顯示正式 V10 把真人偏好的回答排得較低；"
            "可設計一次小型、可回退的訓練 ablation，但仍不得升級 runtime。"
        )
    return {
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "scope": "rightbrain_human_preference_v31_frozen_v10_probe",
        "method": "frozen_v10_length_normalized_pairwise_log_probability",
        "method_references": list(METHOD_REFERENCES),
        "training_performed": False,
        "optimizer_updates": 0,
        "model_parameter_updates": 0,
        "dataset_evidence": {
            "pair_count": dataset_report.get("pair_count"),
            "source_family_count": dataset_report.get("source_family_count"),
            "dataset_file_sha256": dataset_report.get("dataset_file_sha256"),
            "dataset_canonical_sha256": dataset_report.get(
                "dataset_canonical_sha256"
            ),
            "v30_source_evidence": dataset_report.get("source_evidence") or {},
        },
        "adapter_evidence": adapter_evidence,
        "model_metadata": model_metadata,
        "duration_seconds": round(duration_seconds, 3),
        "coverage": {
            "source_family_count": len(source_families),
            "category_count": len(categories),
            "misranked_source_count": len(misranked_sources),
            "misranked_category_count": len(misranked_categories),
            "misranked_source_ids": sorted(misranked_sources),
            "misranked_categories": sorted(misranked_categories),
        },
        "statistics": statistics_summary,
        "gates": gates,
        "decision": {
            "status": status,
            "headroom_detected": headroom_detected,
            "authorize_controlled_training_ablation": authorize_ablation,
            "authorize_training": False,
            "authorize_runtime_promotion": False,
            "decision_zh": decision_zh,
        },
        "controlled_ablation_policy": {
            "minimum_independent_misranked_sources": MIN_INDEPENDENT_MISRANKED_SOURCES,
            "rationale": (
                "A single disagreement may be an annotation or sampling anomaly. Requiring two "
                "independent source cases is a local fail-closed replication safeguard."
            ),
            "official_benchmark_threshold": False,
        },
        "rows": sorted(
            scored_rows,
            key=lambda row: row["raw_preference_margin"],
        ),
        "research_boundary": (
            "These are single-rater development pairs selected from one frozen V10 policy. "
            "The exact interval describes this small set under Bernoulli assumptions; it does not "
            "establish population-level human preference or generated-response improvement. "
            "Any candidate training run still requires a matched-seed unseen generation holdout."
        ),
    }


def write_markdown(report, path):
    stats = report["statistics"]
    decision = report["decision"]
    ci_low, ci_high = stats["agreement_rate_exact_ci"]
    lines = [
        "# RightBrain V31 真人偏好 Frozen-V10 Probe",
        "",
        "## 結論",
        "",
        decision["decision_zh"],
        "",
        "| 指標 | 結果 |",
        "|---|---:|",
        f"| 真人明確偏好 pairs | {stats['pair_count']} |",
        f"| V10 與人類一致 | {stats['v10_agrees_with_human_count']} |",
        f"| V10 排錯 | {stats['v10_misranked_count']} |",
        f"| V10 精確同分 | {stats['v10_exact_tie_count']} |",
        f"| 一致率（decisive） | {100 * (stats['v10_human_agreement_rate_decisive_pairs'] or 0):.1f}% |",
        f"| 95% exact CI | {100 * ci_low:.1f}%–{100 * ci_high:.1f}% |",
        f"| mean 平均 log-prob margin | {stats['mean_raw_preference_margin']:+.6f} |",
        f"| 可做小型訓練 ablation | {'YES' if decision['authorize_controlled_training_ablation'] else 'NO'} |",
        f"| 可升級 runtime | {'YES' if decision['authorize_runtime_promotion'] else 'NO'} |",
        "",
        "## 計算流程",
        "",
        "`同一 V10 + 同一 prompt → 人選回答平均 log-prob − 另一回答平均 log-prob`",
        "",
        "margin > 0 表示 V10 本來較偏好人選回答；margin < 0 才是可學習的排錯證據。",
        "至少兩個獨立來源都排錯才允許小型 ablation；這是防止單一異常觸發訓練的本研究安全規則，不是論文官方門檻。",
        "",
        "## Pair 明細",
        "",
        "| source | 類別 | margin | chosen tokens | rejected tokens | 判定 |",
        "|---|---|---:|---:|---:|---|",
    ]
    for row in report["rows"]:
        lines.append(
            f"| {row['source_case_id']} | {row['category']} | "
            f"{row['raw_preference_margin']:+.6f} | "
            f"{row['chosen_completion_token_count']} | "
            f"{row['rejected_completion_token_count']} | {row['status']} |"
        )
    lines.extend(
        [
            "",
            "## Gate",
            "",
            "| 條件 | 結果 |",
            "|---|---:|",
        ]
    )
    for name, passed in report["gates"].items():
        lines.append(f"| {name} | {'PASS' if passed else 'FAIL'} |")
    lines.extend(
        [
            "",
            "## 證據邊界",
            "",
            "這是單一評分者的小型 development 診斷，不是母體人類偏好正確率。即使允許訓練 ablation，也必須另做未見生成 holdout 才能談上線。",
            "",
        ]
    )
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def _remove_stale_outputs(paths):
    for path in paths:
        Path(path).unlink(missing_ok=True)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dataset",
        default=RIGHTBRAIN_HUMAN_ON_POLICY_PREFERENCE_V30_DATASET_PATH,
    )
    parser.add_argument(
        "--dataset-report",
        default=RIGHTBRAIN_HUMAN_ON_POLICY_PREFERENCE_V30_REPORT_JSON_PATH,
    )
    parser.add_argument("--package", default=RIGHTBRAIN_ON_POLICY_V29_BLIND_PACKAGE_PATH)
    parser.add_argument("--key", default=RIGHTBRAIN_ON_POLICY_V29_BLIND_KEY_PATH)
    parser.add_argument("--ratings", default=RIGHTBRAIN_ON_POLICY_V29_RATINGS_PATH)
    parser.add_argument("--base-model", default=DEFAULT_BASE_MODEL)
    parser.add_argument("--init-adapter", default=DEFAULT_INIT_ADAPTER)
    parser.add_argument("--max-length", type=int, default=720)
    parser.add_argument(
        "--dtype",
        choices=["auto", "float16", "bfloat16", "float32"],
        default="auto",
    )
    parser.add_argument(
        "--output-json",
        default=RIGHTBRAIN_HUMAN_PREFERENCE_V31_PROBE_JSON_PATH,
    )
    parser.add_argument(
        "--output-md",
        default=RIGHTBRAIN_HUMAN_PREFERENCE_V31_PROBE_MD_PATH,
    )
    args = parser.parse_args(argv)
    _remove_stale_outputs((args.output_json, args.output_md))

    required_paths = {
        "dataset": args.dataset,
        "dataset_report": args.dataset_report,
        "package": args.package,
        "key": args.key,
        "ratings": args.ratings,
    }
    missing = [name for name, path in required_paths.items() if not Path(path).is_file()]
    if missing:
        print(
            json.dumps(
                {"status": "waiting_for_v30_human_evidence", "missing": missing},
                ensure_ascii=False,
                indent=2,
            )
        )
        return 2

    rows = load_authorized_probe_rows(
        args.dataset,
        args.dataset_report,
        package_path=args.package,
        key_path=args.key,
        ratings_path=args.ratings,
    )
    dataset_report = json.loads(Path(args.dataset_report).read_text(encoding="utf-8"))
    adapter_evidence = build_adapter_evidence(rows, args.init_adapter)
    if not all(adapter_evidence["gates"].values()):
        raise ValueError("Frozen V31 probe adapter evidence does not match formal V10")

    tokenizer = AutoTokenizer.from_pretrained(args.base_model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"
    tokenized_rows = [tokenize_pair(row, tokenizer, args.max_length) for row in rows]

    started = time.time()
    model = build_model(
        args.base_model,
        args.init_adapter,
        lora_r=32,
        lora_alpha=24,
        lora_dropout=0.08,
        dtype_name=args.dtype,
    )
    trainable_before_freeze = sum(
        parameter.numel() for parameter in model.parameters() if parameter.requires_grad
    )
    for parameter in model.parameters():
        parameter.requires_grad_(False)
    trainable_after_freeze = sum(
        parameter.numel() for parameter in model.parameters() if parameter.requires_grad
    )
    disabled_dropout_count = disable_dropout(model)
    device = next(model.parameters()).device
    scored_rows = score_frozen_pairs(model, tokenized_rows, rows, device)
    metadata = {
        "base_model": args.base_model,
        **init_adapter_report(args.init_adapter),
        "init_adapter_model_sha256": adapter_evidence[
            "local_adapter_model_sha256"
        ],
        "dataset_sha256": _sha256(args.dataset),
        "dataset_report_sha256": _sha256(args.dataset_report),
        "dtype": str(
            resolve_model_dtype(
                args.dtype,
                torch.cuda.is_available(),
                torch.backends.mps.is_available(),
            )
        ),
        "max_length": args.max_length,
        "trainable_parameter_count_before_freeze": trainable_before_freeze,
        "trainable_parameter_count_after_freeze": trainable_after_freeze,
        "disabled_dropout_module_count": disabled_dropout_count,
    }
    report = build_probe_report(
        dataset_report,
        adapter_evidence,
        scored_rows,
        model_metadata=metadata,
        duration_seconds=time.time() - started,
    )
    if not all(report["gates"].values()):
        _remove_stale_outputs((args.output_json, args.output_md))
        raise ValueError("Frozen V31 probe failed an evidence gate")
    Path(args.output_json).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output_md).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output_json).write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_markdown(report, args.output_md)
    print(
        json.dumps(
            {
                "status": report["decision"]["status"],
                "pair_count": report["statistics"]["pair_count"],
                "v10_human_agreement_rate": report["statistics"][
                    "v10_human_agreement_rate_decisive_pairs"
                ],
                "v10_misranked_count": report["statistics"][
                    "v10_misranked_count"
                ],
                "authorize_controlled_training_ablation": report["decision"][
                    "authorize_controlled_training_ablation"
                ],
                "authorize_runtime_promotion": False,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
