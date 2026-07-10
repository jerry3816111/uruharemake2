#!/usr/bin/env python3
"""Evaluate RightBrain candidate selectors against existing blinded human ratings."""

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from import_human_blind_evidence import S0_SYSTEM_ID, load_blind_evidence
from project_paths import (
    RIGHTBRAIN_REPAIR_SELECTION_V1_DATASET_PATH,
    RIGHTBRAIN_REPAIR_SELECTOR_V1_MODEL_PATH,
    RIGHTBRAIN_SELECTOR_HUMAN_PREFERENCE_V1_REPORT_JSON_PATH,
    RIGHTBRAIN_SELECTOR_HUMAN_PREFERENCE_V1_REPORT_MD_PATH,
)
from rightbrain_repair_selector import load_model_artifact, score_candidate
from uruha_brain_mac import RightBrain


TZ = ZoneInfo("Asia/Tokyo")
MIN_STRICT_TASK_COUNT = 10


def _safe_rate(numerator, denominator):
    return round(numerator / denominator, 6) if denominator else None


def _mean(values):
    values = [float(value) for value in values]
    return round(sum(values) / len(values), 6) if values else None


def _task_groups(rows):
    grouped = defaultdict(list)
    for row in rows:
        grouped[(row["source_id"], row["task_id"])].append(row)
    return [grouped[key] for key in sorted(grouped)]


def _selector_training_texts(selection_rows):
    return {
        str(candidate.get("text") or "").strip()
        for row in selection_rows
        for candidate in row.get("candidates") or []
        if str(candidate.get("text") or "").strip()
    }


def _contract_payload(row):
    return {
        "user_input": row.get("input") or "",
        "leftbrain_plan": {
            "meaning": row.get("required_meaning") or "",
            "content_units": [],
            "grounding_terms": [],
        },
        "required_marker_groups": row.get("required_marker_groups") or [],
        "forbidden_markers": row.get("forbidden_markers") or [],
        "context": {"max_chars": 80},
    }


def _heuristic_logic(row):
    category = str(row.get("category") or "unknown")
    return {
        "scene": category,
        "intent": category,
        "constraints": {"max_chars": 80},
        "must_avoid": row.get("forbidden_markers") or [],
        "core_message_jp": row.get("required_meaning") or "",
        "required_marker_groups": row.get("required_marker_groups") or [],
        "human_speech_plan": {"dialogue_act": category, "grounding_terms": []},
        "grounding": {},
        "payload_level": "medium",
    }


def _pick_learned(task, model):
    ranked = []
    for index, row in enumerate(task):
        probability = score_candidate(
            model,
            {"text": row.get("output_text") or ""},
            _contract_payload(row),
        )
        ranked.append((float(probability), -index, row))
    probability, _, selected = max(ranked, key=lambda item: (item[0], item[1]))
    return selected, probability


def _pick_runtime_heuristic(task, rightbrain):
    ranked = []
    for row in task:
        rightbrain.history = []
        score = rightbrain._score_candidate(row.get("output_text") or "", _heuristic_logic(row))
        ranked.append((float(score), str(row.get("output_text") or ""), row))
    score, _, selected = max(ranked, key=lambda item: (item[0], item[1]))
    return selected, score


def _pick_s0(task):
    return next(row for row in task if row.get("system_id") == S0_SYSTEM_ID), None


def _pick_first(task):
    return task[0], None


def _pick_human_oracle(task):
    return max(enumerate(task), key=lambda item: (item[1]["mean_score_1_5"], -item[0]))[1], None


def _selection_record(task, selected, selector_score):
    task_scores = [float(row["mean_score_1_5"]) for row in task]
    top_score = max(task_scores)
    bottom_score = min(task_scores)
    score = float(selected["mean_score_1_5"])
    naturalness = float(selected["scores"][selected["naturalness_field"]])
    semantic = float(selected["scores"][selected["semantic_field"]])
    return {
        "source_id": selected["source_id"],
        "task_id": selected["task_id"],
        "category": selected.get("category") or "unknown",
        "input": selected.get("input") or "",
        "selected_review_id": selected["review_id"],
        "selected_output_label": selected["output_label"],
        "selected_system_id": selected.get("system_id") or "unknown",
        "selected_output_text": selected.get("output_text") or "",
        "selector_score": round(float(selector_score), 6) if selector_score is not None else None,
        "human_mean_score_1_5": score,
        "human_naturalness_1_5": naturalness,
        "human_semantic_1_5": semantic,
        "decision": selected["decision"],
        "top_human_score_1_5": top_score,
        "bottom_human_score_1_5": bottom_score,
        "top_score_hit": abs(score - top_score) < 1e-9,
        "bottom_score_selected": bottom_score < top_score and abs(score - bottom_score) < 1e-9,
    }


def _strategy_metrics(tasks, picker):
    selections = []
    for task in tasks:
        selected, selector_score = picker(task)
        selections.append(_selection_record(task, selected, selector_score))
    decisions = Counter(row["decision"] for row in selections)
    systems = Counter(row["selected_system_id"] for row in selections)
    return {
        "task_count": len(tasks),
        "top_score_hit_count": sum(row["top_score_hit"] for row in selections),
        "top_score_hit_rate": _safe_rate(sum(row["top_score_hit"] for row in selections), len(selections)),
        "bottom_score_selection_count": sum(row["bottom_score_selected"] for row in selections),
        "bottom_score_selection_rate": _safe_rate(
            sum(row["bottom_score_selected"] for row in selections),
            len(selections),
        ),
        "selected_mean_human_score_1_5": _mean(row["human_mean_score_1_5"] for row in selections),
        "selected_mean_naturalness_1_5": _mean(row["human_naturalness_1_5"] for row in selections),
        "selected_mean_semantic_1_5": _mean(row["human_semantic_1_5"] for row in selections),
        "chat_ready_yes_rate": _safe_rate(decisions.get("yes", 0), len(selections)),
        "chat_ready_acceptable_rate": _safe_rate(
            decisions.get("yes", 0) + decisions.get("borderline", 0),
            len(selections),
        ),
        "selected_system_counts": dict(sorted(systems.items())),
        "selections": selections,
    }


def _paired_comparison(first, second):
    second_by_task = {row["task_id"]: row for row in second["selections"]}
    wins = ties = losses = 0
    for row in first["selections"]:
        delta = row["human_mean_score_1_5"] - second_by_task[row["task_id"]]["human_mean_score_1_5"]
        wins += int(delta > 1e-9)
        losses += int(delta < -1e-9)
        ties += int(abs(delta) <= 1e-9)
    return {"first_wins": wins, "ties": ties, "first_losses": losses}


def _evaluate(tasks, model):
    rightbrain = RightBrain(load_model=False)
    strategies = {
        "first_blinded_candidate": _strategy_metrics(tasks, _pick_first),
        "learned_selector_v1": _strategy_metrics(tasks, lambda task: _pick_learned(task, model)),
        "current_runtime_heuristic_proxy": _strategy_metrics(
            tasks,
            lambda task: _pick_runtime_heuristic(task, rightbrain),
        ),
        "s0_full_system_candidate": _strategy_metrics(tasks, _pick_s0),
        "human_score_oracle": _strategy_metrics(tasks, _pick_human_oracle),
    }
    return {
        "strategies": strategies,
        "learned_vs_runtime_heuristic": _paired_comparison(
            strategies["learned_selector_v1"],
            strategies["current_runtime_heuristic_proxy"],
        ),
        "learned_vs_s0": _paired_comparison(
            strategies["learned_selector_v1"],
            strategies["s0_full_system_candidate"],
        ),
    }


def _source_breakdown(tasks, model):
    by_source = defaultdict(list)
    for task in tasks:
        by_source[task[0]["source_id"]].append(task)
    return {
        source_id: _compact_evaluation(_evaluate(source_tasks, model))
        for source_id, source_tasks in sorted(by_source.items())
    }


def _compact_evaluation(evaluation):
    return {
        "strategies": {
            name: {key: value for key, value in metrics.items() if key != "selections"}
            for name, metrics in evaluation["strategies"].items()
        },
        "learned_vs_runtime_heuristic": evaluation["learned_vs_runtime_heuristic"],
        "learned_vs_s0": evaluation["learned_vs_s0"],
    }


def build_report(blind_rows, source_summaries, selection_rows, model):
    tasks = _task_groups(blind_rows)
    training_texts = _selector_training_texts(selection_rows)
    overlapping_tasks = [
        task
        for task in tasks
        if any(str(row.get("output_text") or "").strip() in training_texts for row in task)
    ]
    overlapping_task_keys = {
        (task[0]["source_id"], task[0]["task_id"])
        for task in overlapping_tasks
    }
    strict_tasks = [
        task
        for task in tasks
        if (task[0]["source_id"], task[0]["task_id"]) not in overlapping_task_keys
    ]
    strict_eval = _evaluate(strict_tasks, model)
    learned = strict_eval["strategies"]["learned_selector_v1"]
    heuristic = strict_eval["strategies"]["current_runtime_heuristic_proxy"]
    s0 = strict_eval["strategies"]["s0_full_system_candidate"]
    gate = {
        "strict_task_count_at_least_10": len(strict_tasks) >= MIN_STRICT_TASK_COUNT,
        "strict_candidate_text_overlap_is_zero": all(
            str(row.get("output_text") or "").strip() not in training_texts
            for task in strict_tasks
            for row in task
        ),
        "learned_top_score_hit_rate_not_below_runtime_heuristic": (
            learned["top_score_hit_rate"] >= heuristic["top_score_hit_rate"]
        ),
        "learned_mean_naturalness_not_below_runtime_heuristic": (
            learned["selected_mean_naturalness_1_5"] >= heuristic["selected_mean_naturalness_1_5"]
        ),
        "learned_top_score_hit_rate_not_below_s0_candidate": (
            learned["top_score_hit_rate"] >= s0["top_score_hit_rate"]
        ),
        "learned_mean_naturalness_not_below_s0_candidate": (
            learned["selected_mean_naturalness_1_5"] >= s0["selected_mean_naturalness_1_5"]
        ),
    }
    takeover_recommended = all(gate.values())
    return {
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "scope": "rightbrain_selector_human_preference_v1",
        "selector_model": model.get("model_type"),
        "selector_schema_version": model.get("schema_version"),
        "data": {
            "completed_task_count": len(tasks),
            "completed_candidate_count": len(blind_rows),
            "selector_training_candidate_text_count": len(training_texts),
            "overlapping_task_count": len(overlapping_tasks),
            "overlapping_task_ids": [task[0]["task_id"] for task in overlapping_tasks],
            "strict_task_count": len(strict_tasks),
            "strict_candidate_count": sum(len(task) for task in strict_tasks),
            "source_summaries": source_summaries,
        },
        "all_completed_diagnostic": _compact_evaluation(_evaluate(tasks, model)),
        "strict_no_exact_text_overlap": {
            **strict_eval,
            "source_breakdown": _source_breakdown(strict_tasks, model),
        },
        "gate": gate,
        "takeover_recommended": takeover_recommended,
        "decision_zh": (
            "可進入受保護接管實驗：learned selector 在零文字重疊人類盲評中沒有落後現行方法。"
            if takeover_recommended
            else "不可接管：learned selector 在零文字重疊人類盲評中仍落後現行 heuristic 或完整 S0 候選，維持 observe-only。"
        ),
        "method_references": [
            {
                "title": "Twenty Years of Confusion in Human Evaluation",
                "url": "https://aclanthology.org/2020.inlg-1.23/",
                "use": "分開報告自然度、語意與整體分數，避免未定義的單一品質分數。",
            },
            {
                "title": "Disentangling the Properties of Human Evaluation Methods",
                "url": "https://aclanthology.org/2020.inlg-1.24/",
                "use": "明確區分評估對象、評估方式與實驗設計。",
            },
            {
                "title": "Perturbation CheckLists for Evaluating NLG Evaluation Metrics",
                "url": "https://aclanthology.org/2021.emnlp-main.575/",
                "use": "不假設單一自動指標能同時代表流暢度、內容覆蓋與整體品質。",
            },
        ],
        "research_boundary": (
            "Ratings come from two partial blind-rating packages completed by one rater on the same date, so there is no "
            "inter-rater reliability estimate and this is not an official benchmark. The packages use different overall "
            "rubrics; cross-package promotion therefore relies on their shared naturalness dimension and within-task top-score "
            "hits, while the overall mean is descriptive only. Exact selector-training candidate text overlaps are removed "
            "for the strict result, but semantic-family overlap may remain. The runtime heuristic is reconstructed from stored "
            "contract fields and is a proxy, not a replay of hidden runtime state. This gate can block takeover, not prove "
            "broad human naturalness. The four candidates per task are blinded system/control outputs rather than the current "
            "v10 model's runtime candidate distribution; actual-model shadow evidence remains a separate requirement."
        ),
    }


def write_markdown(report, path):
    strict = report["strict_no_exact_text_overlap"]
    strategies = strict["strategies"]
    labels = {
        "first_blinded_candidate": "盲化順序第一個",
        "learned_selector_v1": "目前 learned selector v1",
        "current_runtime_heuristic_proxy": "目前 runtime heuristic（重建）",
        "s0_full_system_candidate": "完整 S0 系統候選",
        "human_score_oracle": "人類分數上限",
    }
    lines = [
        "# 右腦 Selector 人類偏好 Gate v1",
        "",
        "## 結論",
        "",
        report["decision_zh"],
        "",
        "## 資料隔離",
        "",
        f"- 已完成人類盲評：{report['data']['completed_task_count']} 題 / {report['data']['completed_candidate_count']} 候選",
        f"- 因 selector 訓練文字重疊而排除：{report['data']['overlapping_task_count']} 題",
        f"- 嚴格評測：{report['data']['strict_task_count']} 題 / {report['data']['strict_candidate_count']} 候選",
        "",
        "## 嚴格零文字重疊結果",
        "",
        "| 方法 | 命中該題最高人類分數 | 選中平均分 | 自然度 | 語意 | 可直接聊天 |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for name in (
        "first_blinded_candidate",
        "learned_selector_v1",
        "current_runtime_heuristic_proxy",
        "s0_full_system_candidate",
        "human_score_oracle",
    ):
        metrics = strategies[name]
        lines.append(
            f"| {labels[name]} | {metrics['top_score_hit_count']}/{metrics['task_count']} "
            f"({metrics['top_score_hit_rate']:.1%}) | {metrics['selected_mean_human_score_1_5']:.3f}/5 | "
            f"{metrics['selected_mean_naturalness_1_5']:.3f}/5 | "
            f"{metrics['selected_mean_semantic_1_5']:.3f}/5 | {metrics['chat_ready_yes_rate']:.1%} |"
        )
    lines.extend(
        [
            "",
            "## Learned Selector 對照",
            "",
            f"- 對 runtime heuristic：`{strict['learned_vs_runtime_heuristic']}`",
            f"- 對完整 S0 候選：`{strict['learned_vs_s0']}`",
            "",
            "## 接管門檻",
            "",
            "| 條件 | 結果 |",
            "|---|---|",
        ]
    )
    for name, passed in report["gate"].items():
        lines.append(f"| {name} | {'PASS' if passed else 'FAIL'} |")
    lines.extend(
        [
            "",
            "## 來源分開結果",
            "",
            "| 盲評來源 | 題數 | learned 自然度 | heuristic 自然度 | S0 自然度 |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for source_id, source_result in strict["source_breakdown"].items():
        source_strategies = source_result["strategies"]
        source_learned = source_strategies["learned_selector_v1"]
        source_heuristic = source_strategies["current_runtime_heuristic_proxy"]
        source_s0 = source_strategies["s0_full_system_candidate"]
        lines.append(
            f"| {source_id} | {source_learned['task_count']} | "
            f"{source_learned['selected_mean_naturalness_1_5']:.3f}/5 | "
            f"{source_heuristic['selected_mean_naturalness_1_5']:.3f}/5 | "
            f"{source_s0['selected_mean_naturalness_1_5']:.3f}/5 |"
        )
    learned_by_task = {
        row["task_id"]: row for row in strategies["learned_selector_v1"]["selections"]
    }
    heuristic_by_task = {
        row["task_id"]: row
        for row in strategies["current_runtime_heuristic_proxy"]["selections"]
    }
    losses = [
        (learned_by_task[task_id], heuristic_by_task[task_id])
        for task_id in learned_by_task
        if learned_by_task[task_id]["human_mean_score_1_5"]
        < heuristic_by_task[task_id]["human_mean_score_1_5"]
    ]
    if losses:
        lines.extend(
            [
                "",
                "## Learned Selector 實際落後案例",
                "",
                "| task | learned 選擇 | 人類分數 | heuristic 選擇 | 人類分數 |",
                "|---|---|---:|---|---:|",
            ]
        )
        for learned_row, heuristic_row in losses:
            lines.append(
                f"| {learned_row['task_id']} | {learned_row['selected_output_text']} | "
                f"{learned_row['human_mean_score_1_5']:.2f} | {heuristic_row['selected_output_text']} | "
                f"{heuristic_row['human_mean_score_1_5']:.2f} |"
            )
    lines.extend(
        [
            "",
            "## 方法與邊界",
            "",
            "- 同時保留整體分數、自然度、語意完整度與可直接聊天率，不把它們混成單一自動指標。",
            "- v15 與 v16 的整體量表不同；跨來源接管判斷只使用共同的自然度欄位與逐題最高分命中。",
            "- learned selector 的候選順序保持原始盲化順序；runtime heuristic 使用正式程式的分數與 tie-break。",
            "- 這批只有單一評分者，沒有評分者間一致度，因此只足以阻止接管，不能證明廣泛的人類自然度。",
            "- 每題四個候選來自完整系統與控制組，不等同目前 v10 的即時抽樣分布；仍需獨立 actual-model shadow。",
            "",
            f"研究邊界：{report['research_boundary']}",
            "",
            "## 方法來源",
            "",
        ]
    )
    for reference in report["method_references"]:
        lines.append(f"- [{reference['title']}]({reference['url']}): {reference['use']}")
    lines.append("")
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--selection-dataset", default=RIGHTBRAIN_REPAIR_SELECTION_V1_DATASET_PATH)
    parser.add_argument("--selector-model", default=RIGHTBRAIN_REPAIR_SELECTOR_V1_MODEL_PATH)
    parser.add_argument("--output-json", default=RIGHTBRAIN_SELECTOR_HUMAN_PREFERENCE_V1_REPORT_JSON_PATH)
    parser.add_argument("--output-md", default=RIGHTBRAIN_SELECTOR_HUMAN_PREFERENCE_V1_REPORT_MD_PATH)
    args = parser.parse_args()

    blind_rows, _, source_summaries = load_blind_evidence()
    selection_rows = json.loads(Path(args.selection_dataset).read_text(encoding="utf-8"))
    model = load_model_artifact(args.selector_model)
    report = build_report(blind_rows, source_summaries, selection_rows, model)
    Path(args.output_json).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_markdown(report, args.output_md)
    print(
        json.dumps(
            {
                "strict_task_count": report["data"]["strict_task_count"],
                "gate": report["gate"],
                "takeover_recommended": report["takeover_recommended"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
