#!/usr/bin/env python3
"""Train and serialize the RightBrain repair candidate reranker."""

import argparse
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from project_paths import (
    RIGHTBRAIN_REPAIR_SELECTION_V1_DATASET_PATH,
    RIGHTBRAIN_REPAIR_SELECTOR_V1_MODEL_PATH,
    RIGHTBRAIN_REPAIR_SELECTOR_V1_TRAIN_REPORT_JSON_PATH,
    RIGHTBRAIN_REPAIR_SELECTOR_V1_TRAIN_REPORT_MD_PATH,
)
from rightbrain_repair_selector import (
    DEFAULT_SPLIT_SEED,
    DEFAULT_TRAIN_SEED,
    evaluate_baselines,
    grouped_contract_split,
    model_to_json,
    split_summary,
    train_selector,
)


TZ = ZoneInfo("Asia/Tokyo")


def _fmt_pct(value):
    return "n/a" if value is None else f"{100 * value:.1f}%"


def build_training_report(rows, split_seed=DEFAULT_SPLIT_SEED, train_seed=DEFAULT_TRAIN_SEED):
    splits = grouped_contract_split(rows, seed=split_seed)
    model, history = train_selector(splits["train"], splits["validation"], seed=train_seed)
    model["split_seed"] = split_seed
    model["dataset_scope"] = "rightbrain_repair_selection_v1"
    model["research_boundary"] = (
        "This model learns a calibration over general contract-relative surface features. "
        "It does not consume candidate source, detected errors, gold flags, item IDs, or benchmark answers."
    )
    validation = evaluate_baselines(splits["validation"], model, random_seed=split_seed)
    report = {
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "scope": "rightbrain_repair_selector_v1_train",
        "split": split_summary(splits),
        "model": {
            key: model[key]
            for key in (
                "model_type",
                "schema_version",
                "feature_names",
                "best_epoch",
                "training_seed",
                "split_seed",
                "training_row_count",
                "validation_row_count",
                "positive_class_weight",
                "learning_rate",
                "l2",
                "requested_epochs",
                "research_boundary",
            )
        },
        "validation": validation,
        "training_history": [
            row
            for row in history
            if row["epoch"] == 1 or row["epoch"] % 50 == 0 or row["epoch"] == model["best_epoch"]
        ],
        "conclusion_zh": (
            "這是 F 右腦候選排序器的第一個真正學習版本：它只從訓練合約學權重，"
            "並在完全不同合約指紋的 validation 上選候選。"
        ),
    }
    return model, report, splits


def write_markdown(report, path):
    validation = report["validation"]
    split = report["split"]
    lines = [
        "# RightBrain Learned Repair Selector v1 - Training",
        "",
        "## 一句話結論",
        "",
        report["conclusion_zh"],
        "",
        "## 資料隔離",
        "",
        "| split | rows | unique contracts |",
        "|---|---:|---:|",
    ]
    for name in ("train", "validation", "test"):
        lines.append(
            f"| {name} | {split['row_counts'][name]} | {split['contract_fingerprint_counts'][name]} |"
        )
    lines.extend(
        [
            "",
            f"合約指紋跨 split 重疊：`{split['fingerprint_overlap_counts']}`。三項都必須是 0。",
            "",
            "## Validation 選擇結果",
            "",
            "| 方法 | 選中乾淨候選 | 錯選壞候選 |",
            "|---|---:|---:|",
        ]
    )
    for name, metrics in validation.items():
        lines.append(
            f"| {name} | {_fmt_pct(metrics['gold_selection_rate'])} | {_fmt_pct(metrics['invalid_selection_rate'])} |"
        )
    lines.extend(
        [
            "",
            "## 研究邊界",
            "",
            "- 模型沒有讀候選來源、gold 標籤、錯誤標籤、題號或 benchmark 答案。",
            "- 特徵仍是合約導向的表面與語意槽位訊號，因此這是 learned calibration/reranker，不是通用語意模型。",
            "- test split 保留到獨立評測腳本，不能用來挑 epoch。",
            "",
        ]
    )
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default=RIGHTBRAIN_REPAIR_SELECTION_V1_DATASET_PATH)
    parser.add_argument("--model", default=RIGHTBRAIN_REPAIR_SELECTOR_V1_MODEL_PATH)
    parser.add_argument("--report-json", default=RIGHTBRAIN_REPAIR_SELECTOR_V1_TRAIN_REPORT_JSON_PATH)
    parser.add_argument("--report-md", default=RIGHTBRAIN_REPAIR_SELECTOR_V1_TRAIN_REPORT_MD_PATH)
    parser.add_argument("--split-seed", type=int, default=DEFAULT_SPLIT_SEED)
    parser.add_argument("--train-seed", type=int, default=DEFAULT_TRAIN_SEED)
    args = parser.parse_args()

    rows = json.loads(Path(args.dataset).read_text(encoding="utf-8"))
    model, report, _ = build_training_report(rows, split_seed=args.split_seed, train_seed=args.train_seed)
    Path(args.model).parent.mkdir(parents=True, exist_ok=True)
    Path(args.model).write_text(model_to_json(model), encoding="utf-8")
    Path(args.report_json).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_markdown(report, args.report_md)
    print(
        json.dumps(
            {
                "model": args.model,
                "best_epoch": model["best_epoch"],
                "split": report["split"],
                "validation_rates": {
                    name: metrics["gold_selection_rate"]
                    for name, metrics in report["validation"].items()
                },
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
