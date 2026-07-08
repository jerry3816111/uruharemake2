#!/usr/bin/env python3
"""Evaluate the learned RightBrain repair reranker on untouched contract groups."""

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from build_rightbrain_repair_curriculum_v1 import _contract_fingerprint, _payload_for_holdout_case, _target_errors
from eval_rightbrain_model_surface_holdout import _case_inputs
from eval_rightbrain_repair_selection_v1 import select_candidate as select_oracle_candidate
from project_paths import (
    RIGHTBRAIN_REPAIR_SELECTION_V1_DATASET_PATH,
    RIGHTBRAIN_REPAIR_SELECTOR_V1_EVAL_REPORT_JSON_PATH,
    RIGHTBRAIN_REPAIR_SELECTOR_V1_EVAL_REPORT_MD_PATH,
    RIGHTBRAIN_REPAIR_SELECTOR_V1_MODEL_PATH,
    RIGHTBRAIN_REPAIR_SELECTOR_V1_NATURAL_HOLDOUT_SOURCE_PATH,
)
from rightbrain_repair_selector import (
    evaluate_baselines,
    evaluate_strategy,
    grouped_contract_split,
    select_learned_candidate,
    split_summary,
)
from uruha_brain_mac import RightBrain


TZ = ZoneInfo("Asia/Tokyo")
MIN_TEST_GOLD_SELECTION_RATE = 0.95
MAX_TEST_INVALID_SELECTION_RATE = 0.05
MIN_GAIN_OVER_FIRST_CANDIDATE = 0.5
DEFAULT_NATURAL_HOLDOUT_REPORT = RIGHTBRAIN_REPAIR_SELECTOR_V1_NATURAL_HOLDOUT_SOURCE_PATH


def _fmt_pct(value):
    return "n/a" if value is None else f"{100 * value:.1f}%"


def _semantic_decoy_metrics(rows, model):
    rows_with_decoy = [
        row
        for row in rows
        if any(candidate.get("source") == "semantic_reference_drift" for candidate in row["candidates"])
    ]
    selected_decoys = 0
    for row in rows_with_decoy:
        selected, _ = select_learned_candidate(model, row)
        selected_decoys += int(selected.get("source") == "semantic_reference_drift")
    return {
        "case_count": len(rows_with_decoy),
        "selected_semantic_decoy_count": selected_decoys,
        "semantic_decoy_rejection_rate": (
            round((len(rows_with_decoy) - selected_decoys) / len(rows_with_decoy), 6)
            if rows_with_decoy
            else None
        ),
    }


def _natural_holdout_candidates(natural_report):
    rightbrain = RightBrain(load_model=False)
    case_inputs = {case["id"]: case for case in _case_inputs()}
    rows = []
    for source_case in natural_report.get("cases") or []:
        case_id = source_case.get("id")
        if case_id not in case_inputs:
            continue
        payload = _payload_for_holdout_case(rightbrain, case_inputs[case_id])
        candidates = []

        def append_candidate(candidate_id, source, text):
            text = str(text or "").strip()
            if not text or any(candidate["text"] == text for candidate in candidates):
                return
            candidates.append(
                {
                    "candidate_id": candidate_id,
                    "source": source,
                    "text": text,
                    "errors": _target_errors(text, payload),
                }
            )

        append_candidate(f"{case_id}:deterministic", "deterministic", source_case.get("deterministic_reply"))
        for index, candidate in enumerate(source_case.get("model_accepted_candidates") or []):
            append_candidate(
                f"{case_id}:accepted:{index}",
                "model_accepted",
                candidate.get("raw_candidate") or candidate.get("candidate"),
            )
        for index, candidate in enumerate(source_case.get("model_initial_rejected_candidates") or []):
            append_candidate(
                f"{case_id}:rejected:{index}",
                "model_rejected",
                candidate.get("raw_candidate") or candidate.get("candidate"),
            )
        if candidates:
            rows.append(
                {
                    "id": case_id,
                    "category": source_case.get("category"),
                    "contract_payload": payload,
                    "source_contract_fingerprint": _contract_fingerprint(payload),
                    "candidates": candidates,
                }
            )
    return rows


def _natural_strategy(rows, selector):
    valid_count = 0
    selected_sources = {}
    failures = []
    for row in rows:
        selected = selector(row)
        valid = not selected["errors"]
        valid_count += int(valid)
        source = selected["source"]
        selected_sources[source] = selected_sources.get(source, 0) + 1
        if not valid:
            failures.append(
                {
                    "id": row["id"],
                    "selected_candidate_id": selected["candidate_id"],
                    "selected_source": source,
                    "errors": selected["errors"],
                }
            )
    return {
        "case_count": len(rows),
        "valid_selection_count": valid_count,
        "valid_selection_rate": round(valid_count / len(rows), 6) if rows else None,
        "invalid_selection_count": len(rows) - valid_count,
        "invalid_selection_rate": round((len(rows) - valid_count) / len(rows), 6) if rows else None,
        "selected_source_counts": dict(sorted(selected_sources.items())),
        "failures": failures,
    }


def evaluate_natural_holdout(selection_rows, model, natural_report):
    rows = _natural_holdout_candidates(natural_report)
    training_fingerprints = {row["source_contract_fingerprint"] for row in selection_rows}

    def learned(row):
        return select_learned_candidate(model, row)[0]

    def deterministic(row):
        return next(candidate for candidate in row["candidates"] if candidate["source"] == "deterministic")

    def seeded_random(row):
        digest = hashlib.sha256(f"{model['split_seed']}:{row['id']}".encode("utf-8")).digest()
        return row["candidates"][int.from_bytes(digest[:8], "big") % len(row["candidates"])]

    def contract_oracle(row):
        return next((candidate for candidate in row["candidates"] if not candidate["errors"]), row["candidates"][0])

    invalid_candidates = sum(bool(candidate["errors"]) for row in rows for candidate in row["candidates"])
    return {
        "source_scope": natural_report.get("scope"),
        "case_count": len(rows),
        "candidate_count": sum(len(row["candidates"]) for row in rows),
        "invalid_candidate_count": invalid_candidates,
        "contract_overlap_with_selection_dataset": sum(
            row["source_contract_fingerprint"] in training_fingerprints for row in rows
        ),
        "strategies": {
            "seeded_random": _natural_strategy(rows, seeded_random),
            "deterministic_fallback": _natural_strategy(rows, deterministic),
            "learned_selector": _natural_strategy(rows, learned),
            "deterministic_contract_oracle": _natural_strategy(rows, contract_oracle),
        },
        "boundary": (
            "These are previously generated model candidates from the excluded runtime holdout. "
            "Validity is contract-based; this small set measures transfer to natural model errors, not naturalness preference."
        ),
    }


def build_evaluation_report(rows, model, natural_report=None):
    split_seed = int(model["split_seed"])
    splits = grouped_contract_split(rows, seed=split_seed)
    test_rows = splits["test"]
    strategies = evaluate_baselines(test_rows, model, random_seed=split_seed)
    strategies["deterministic_contract_oracle"] = evaluate_strategy(test_rows, select_oracle_candidate)
    learned_rate = strategies["learned_selector"]["gold_selection_rate"]
    first_rate = strategies["first_candidate"]["gold_selection_rate"]
    semantic_decoys = _semantic_decoy_metrics(test_rows, model)
    natural_holdout = evaluate_natural_holdout(rows, model, natural_report) if natural_report else None
    gate = {
        "no_contract_fingerprint_overlap": all(
            count == 0 for count in split_summary(splits)["fingerprint_overlap_counts"].values()
        ),
        "test_gold_selection_rate_at_least_95pct": learned_rate >= MIN_TEST_GOLD_SELECTION_RATE,
        "test_invalid_selection_rate_at_most_5pct": (
            strategies["learned_selector"]["invalid_selection_rate"] <= MAX_TEST_INVALID_SELECTION_RATE
        ),
        "gain_over_first_candidate_at_least_50pp": (
            learned_rate - first_rate >= MIN_GAIN_OVER_FIRST_CANDIDATE
        ),
        "test_contains_semantic_drift_decoys": semantic_decoys["case_count"] > 0,
        "test_semantic_drift_decoy_rejection_rate_is_100pct": (
            semantic_decoys["semantic_decoy_rejection_rate"] == 1.0
        ),
    }
    if natural_holdout:
        gate.update(
            {
                "natural_holdout_contract_overlap_is_zero": (
                    natural_holdout["contract_overlap_with_selection_dataset"] == 0
                ),
                "natural_holdout_valid_selection_rate_is_100pct": (
                    natural_holdout["strategies"]["learned_selector"]["valid_selection_rate"] == 1.0
                ),
            }
        )
    return {
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "scope": "rightbrain_repair_selector_v1_eval",
        "dataset_scope": model.get("dataset_scope"),
        "model_type": model.get("model_type"),
        "best_epoch": model.get("best_epoch"),
        "split": split_summary(splits),
        "test_strategies": strategies,
        "test_semantic_drift_decoys": semantic_decoys,
        "natural_generated_holdout": natural_holdout,
        "gate": gate,
        "gate_passed": all(gate.values()),
        "research_boundary": (
            "The untouched test set contains source contracts never used for training or epoch selection. "
            "The learned selector is compared with weak baselines and the deterministic contract oracle. "
            "Synthetic semantic decoys are constructed from cross-contract replies with low character overlap; "
            "their rejection does not prove open-world natural-language understanding."
        ),
        "conclusion_zh": (
            "測試的是 F 右腦能否在未見過的輸出合約中，從多個回答候選挑出保留左腦語意且無污染的版本；"
            "這不會讓 ToMBench 推理本身變強，但可降低正確答案在最終表達時消失的風險。"
        ),
    }


def write_markdown(report, path):
    lines = [
        "# RightBrain Learned Repair Selector v1 - Held-out Eval",
        "",
        "## 一句話結論",
        "",
        report["conclusion_zh"],
        "",
        "## 未見合約測試結果",
        "",
        "| 方法 | 選中乾淨候選 | 錯選壞候選 | 定位 |",
        "|---|---:|---:|---|",
    ]
    labels = {
        "first_candidate": "不判斷，取第一個",
        "seeded_random": "固定種子隨機",
        "length_only": "只看長度",
        "learned_selector": "本次學習式排序器",
        "deterministic_contract_oracle": "規則 oracle 上限",
    }
    for name, metrics in report["test_strategies"].items():
        lines.append(
            f"| {name} | {_fmt_pct(metrics['gold_selection_rate'])} | "
            f"{_fmt_pct(metrics['invalid_selection_rate'])} | {labels[name]} |"
        )
    learned = report["test_strategies"]["learned_selector"]
    binary = learned["candidate_metrics"]
    semantic_decoys = report["test_semantic_drift_decoys"]
    lines.extend(
        [
            "",
            "## 模型可信度檢查",
            "",
            f"- test contracts: {report['split']['contract_fingerprint_counts']['test']}",
            f"- candidate Brier score: {binary['brier_score']}",
            f"- candidate log loss: {binary['log_loss']}",
            f"- semantic drift decoys: {semantic_decoys['case_count']}",
            f"- semantic drift decoy rejection: {_fmt_pct(semantic_decoys['semantic_decoy_rejection_rate'])}",
            f"- gate passed: `{report['gate_passed']}`",
            "",
            "| 門檻 | 結果 |",
            "|---|---|",
        ]
    )
    for name, passed in report["gate"].items():
        lines.append(f"| {name} | {'PASS' if passed else 'FAIL'} |")
    natural = report.get("natural_generated_holdout")
    if natural:
        lines.extend(
            [
                "",
                "## 先前模型真實生成候選",
                "",
                (
                    f"這批包含 {natural['case_count']} 個未參與 curriculum 的合約、"
                    f"{natural['candidate_count']} 個真實候選，其中 {natural['invalid_candidate_count']} 個違反合約。"
                ),
                "",
                "| 方法 | 選到有效候選 | 選到無效候選 |",
                "|---|---:|---:|",
            ]
        )
        for name, metrics in natural["strategies"].items():
            lines.append(
                f"| {name} | {_fmt_pct(metrics['valid_selection_rate'])} | "
                f"{_fmt_pct(metrics['invalid_selection_rate'])} |"
            )
    lines.extend(
        [
            "",
            "## 重要邊界",
            "",
            "- 這是未見合約的 held-out 評測，不是把同一題換順序再測。",
            "- 這是合約特徵的學習式校準器；規則 oracle 仍保留為安全上限與比較基準。",
            "- 語意誘餌由跨合約、低文字重疊方式建立；22/22 是受控測試結果，仍需真實模型候選驗證。",
            "- 通過後只代表值得進入 runtime shadow mode，不代表應立即取代正式回答。",
            "",
        ]
    )
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default=RIGHTBRAIN_REPAIR_SELECTION_V1_DATASET_PATH)
    parser.add_argument("--model", default=RIGHTBRAIN_REPAIR_SELECTOR_V1_MODEL_PATH)
    parser.add_argument("--output-json", default=RIGHTBRAIN_REPAIR_SELECTOR_V1_EVAL_REPORT_JSON_PATH)
    parser.add_argument("--output-md", default=RIGHTBRAIN_REPAIR_SELECTOR_V1_EVAL_REPORT_MD_PATH)
    parser.add_argument("--natural-holdout-report", default=DEFAULT_NATURAL_HOLDOUT_REPORT)
    args = parser.parse_args()

    rows = json.loads(Path(args.dataset).read_text(encoding="utf-8"))
    model = json.loads(Path(args.model).read_text(encoding="utf-8"))
    natural_report_path = Path(args.natural_holdout_report)
    natural_report = json.loads(natural_report_path.read_text(encoding="utf-8")) if natural_report_path.exists() else None
    report = build_evaluation_report(rows, model, natural_report=natural_report)
    Path(args.output_json).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_markdown(report, args.output_md)
    print(
        json.dumps(
            {
                "gate": report["gate"],
                "test_rates": {
                    name: metrics["gold_selection_rate"]
                    for name, metrics in report["test_strategies"].items()
                },
                "natural_holdout_rates": {
                    name: metrics["valid_selection_rate"]
                    for name, metrics in (report.get("natural_generated_holdout") or {}).get("strategies", {}).items()
                },
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if report["gate_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
