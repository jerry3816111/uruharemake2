#!/usr/bin/env python3
"""Build a targeted RightBrain SFT supplement from rejected model candidates."""

import argparse
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from eval_rightbrain_model_surface_holdout import _case_inputs
from project_paths import (
    RIGHTBRAIN_MODEL_SURFACE_HOLDOUT_REPORT_JSON_PATH,
    RIGHTBRAIN_REJECTION_CURRICULUM_V1_DATASET_PATH,
    RIGHTBRAIN_REJECTION_CURRICULUM_V1_REPORT_JSON_PATH,
    RIGHTBRAIN_REJECTION_CURRICULUM_V1_REPORT_MD_PATH,
)
from uruha_brain_mac import RIGHT_BRAIN_MODEL_SYSTEM_PROMPT, RightBrain


TZ = ZoneInfo("Asia/Tokyo")
JAPANESE_RE = re.compile(r"[ぁ-んァ-ヶー一-龠]")
CHINESE_SPECIFIC_RE = re.compile(r"[这吗么们没还让给说话這嗎麼們沒還讓說泠]|好了|不是|我想|你的|可以|為什麼|为什么")
ASCII_WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9_-]{1,}")

TARGET_VARIANTS_BY_CASE = {
    "explicit_stomach_coffee": [
        "最近は胃が弱いんだから、コーヒーは控えめにしとけ。",
        "最近は胃が弱いなら、コーヒーは少なめにしとけ。",
        "胃が弱い時にコーヒー攻めるな。飲むなら少しだけにしとけ。",
        "最近は胃が弱いんだし、今日はコーヒーやめとく方が無難だろ。",
        "コーヒー飲むなら少しだけ。最近は胃が弱いんだから無理すんな。",
        "胃が弱い最近なら、コーヒーは控えめで止めとけ。",
    ],
    "explicit_spicy_food_update": [
        "最近は辛いものを控えたいんだから、辛いものは控えめにしとけ。",
        "最近は辛いものを控えたいんだろ。今日は控えめでいい。",
        "胃のこと考えるなら、辛いものは今日は少なめにしとけ。",
        "最近の体調なら、辛いものは控えめにしとけ。",
        "辛いもの行きたいのは分かるけど、胃があるなら控えめだろ。",
        "最近は辛いものを控えたいって流れだし、今日は少しだけにしとけ。",
    ],
    "background_family_pressure": [
        "今やるなら小さく済ませろ。後で戻せる形にしとけ。",
        "今日は負荷を軽くしろ。小さく終わるやつだけでいい。",
        "責める日じゃない。今は小さいこと一個で済ませろ。",
        "休む寄りでいい。やるなら負荷の軽いやつだけにしとけ。",
        "今日は軽く流せ。大きいことまで抱えるな。",
        "小さく済ませて休め。今はそれで十分だろ。",
    ],
    "private_do_not_mention": [
        "今は一個だけ決めればいい。全部まとめて抱えるなって。",
        "今は短くでいい。一個だけ話せば十分だろ。",
        "話すなら一個だけにしとけ。今は広げなくていい。",
        "今は一個選べ。話は短くていい。",
        "今日は短くいけ。全部話そうとするな。",
        "今の話だけでいい。一個ずつにしとけ。",
    ],
    "no_memory_plain_question": [
        "迷うなら軽い方からでいい。後で足せる形にしとけ。",
        "分かる範囲で言うなら、軽いやつからでいい。",
        "分からない所は決めつけるな。後で足せる形にしとけ。",
        "今は決めつけず、後で変えられる予定にしとけ。",
        "分かる範囲だけでいい。迷うなら軽い方から行け。",
        "分からない部分は後で詰めればいい。今は軽く決めろ。",
    ],
    "support_read_receipt_self_blame": [
        "既読のまま返事がないと気になるよな。でも理由はまだ分からない。自分のせいと決めず、少し待て。",
        "既読だけだと気になるよな。でも理由はまだ分からないし、自分のせいにするな。",
        "返事がない理由はまだ分からない。自分が悪いって決めるのは早いだろ。",
        "既読で止まると不安になるけど、理由なしに自分のせいへ持ってくな。",
        "返信がない理由はまだ見えてない。自分が悪いって決めつけるな。",
        "既読だけで返事がないのはきついな。でも理由は分からないし、自分を責めるな。",
    ],
}


def _payload_for_case(rightbrain, case):
    logic = case["logic"]
    max_chars = (logic.get("constraints") or {}).get("max_chars", 80)
    return rightbrain._build_model_surface_payload(
        logic,
        case.get("psyche") or {},
        max_chars,
        memory_data=case.get("memory_data") or {},
    )


def _report_rows_by_id(report):
    return {str(row.get("id")): row for row in report.get("cases") or []}


def _required_groups_hit(reply, groups):
    return all(any(str(marker) and str(marker) in reply for marker in group) for group in groups)


def _target_errors(reply, payload):
    errors = []
    if not reply or not JAPANESE_RE.search(reply):
        errors.append("not_japanese")
    if CHINESE_SPECIFIC_RE.search(reply):
        errors.append("chinese_leak")
    if ASCII_WORD_RE.search(reply):
        errors.append("ascii_leak")
    if "私" in reply:
        errors.append("first_person")
    required = payload.get("required_marker_groups") or []
    if required and not _required_groups_hit(reply, required):
        errors.append("required_marker_missing")
    forbidden = [str(item) for item in payload.get("forbidden_markers") or [] if str(item).strip()]
    if any(marker in reply for marker in forbidden):
        errors.append("forbidden_marker")
    max_chars = int((payload.get("context") or {}).get("max_chars") or 80)
    if len(reply) > max_chars + 2:
        errors.append("over_max_chars")
    return errors


def _target_variants(case_id, deterministic_reply):
    variants = []
    for text in TARGET_VARIANTS_BY_CASE.get(case_id, []):
        text = str(text or "").strip()
        if text and text not in variants:
            variants.append(text)
    deterministic_reply = str(deterministic_reply or "").strip()
    if deterministic_reply and deterministic_reply not in variants:
        variants.insert(0, deterministic_reply)
    return variants


def build_curriculum(report, cases=None):
    cases = list(cases or _case_inputs())
    report_rows = _report_rows_by_id(report)
    rightbrain = RightBrain(load_model=False)
    rows = []
    reason_counts = Counter()
    category_counts = Counter()
    skipped = Counter()

    for case in cases:
        report_row = report_rows.get(case["id"])
        if not report_row:
            skipped["missing_report_row"] += 1
            continue
        reasons = list(dict.fromkeys(report_row.get("model_rejection_reasons") or []))
        if not reasons:
            skipped["no_rejection"] += 1
            continue
        if not report_row.get("deterministic_quality_pass"):
            skipped["deterministic_target_failed"] += 1
            continue
        target_variants = _target_variants(case["id"], report_row.get("deterministic_reply"))
        if not target_variants:
            skipped["empty_target_reply"] += 1
            continue

        payload = _payload_for_case(rightbrain, case)
        payload_obj = json.loads(payload)
        if not payload_obj.get("required_marker_groups"):
            skipped["missing_payload_contract"] += 1
            continue

        rejection_examples = [
            {
                "raw_candidate": item.get("raw_candidate", ""),
                "rejection_reasons": item.get("rejection_reasons") or [],
            }
            for item in report_row.get("model_rejected_candidates") or []
        ]
        for target_index, target_reply in enumerate(target_variants, start=1):
            target_errors = _target_errors(target_reply, payload_obj)
            if target_errors:
                skipped[f"target_validation_failed:{case['id']}:{','.join(target_errors)}"] += 1
                continue
            row = {
                "id": f"rb_rejection_curriculum_v1_{len(rows) + 1:04d}",
                "source_case_id": case["id"],
                "category": case["category"],
                "training_role": "rightbrain_rejection_repair_contract_v1_sft",
                "failure_reasons": reasons,
                "rejected_candidate_examples": rejection_examples,
                "target_source": "deterministic_final_surface_pass" if target_index == 1 else "contract_preserving_variant",
                "target_variant_index": target_index,
                "messages": [
                    {"role": "system", "content": RIGHT_BRAIN_MODEL_SYSTEM_PROMPT},
                    {"role": "user", "content": json.dumps(payload_obj, ensure_ascii=False, separators=(",", ":"))},
                    {"role": "assistant", "content": target_reply},
                ],
            }
            rows.append(row)
            category_counts[case["category"]] += 1
            for reason in reasons:
                reason_counts[reason] += 1

    summary = {
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "scope": "rightbrain_rejection_curriculum_v1",
        "source_report": Path(RIGHTBRAIN_MODEL_SURFACE_HOLDOUT_REPORT_JSON_PATH).name,
        "case_count": len(cases),
        "curriculum_row_count": len(rows),
        "variant_cases": len(TARGET_VARIANTS_BY_CASE),
        "skipped_counts": dict(skipped),
        "failure_reason_counts": dict(reason_counts),
        "category_counts": dict(category_counts),
        "training_boundary": (
            "Rejected raw model candidates are metadata only. The assistant targets are deterministic "
            "final-surface replies plus validated contract-preserving variants, so the model learns "
            "correct outputs instead of leaked ASCII, Chinese, or missing-slot replies."
        ),
    }
    return rows, summary


def write_markdown(summary, rows, path):
    lines = [
        "# RightBrain Rejection Curriculum v1",
        "",
        "這份資料把右腦模型在 holdout 中被 gate 拒絕的案例，轉成下一輪 LoRA 的補強樣本。",
        "",
        "## 一句話結論",
        "",
        (
            "被拒絕的 raw candidate 只作為錯誤 metadata；真正訓練目標使用已通過 final-surface "
            "gate 的 deterministic 合格答案，以及同樣通過契約檢查的自然日文變體。"
        ),
        "",
        "## 總表",
        "",
        "| 指標 | 數值 |",
        "|---|---:|",
        f"| source case count | {summary['case_count']} |",
        f"| curriculum row count | {summary['curriculum_row_count']} |",
        "",
        "## 失敗原因分布",
        "",
    ]
    for reason, count in sorted(summary["failure_reason_counts"].items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"- {reason}: {count}")
    lines.extend(["", "## 補強樣本", "", "| case | category | reasons | target reply |", "|---|---|---|---|"])
    for row in rows:
        reasons = ", ".join(row["failure_reasons"])
        target = row["messages"][-1]["content"]
        lines.append(f"| {row['source_case_id']} | {row['category']} | {reasons} | {target} |")
    lines.extend(["", "## 研究邊界", "", f"- {summary['training_boundary']}", ""])
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-report", default=RIGHTBRAIN_MODEL_SURFACE_HOLDOUT_REPORT_JSON_PATH)
    parser.add_argument("--output", default=RIGHTBRAIN_REJECTION_CURRICULUM_V1_DATASET_PATH)
    parser.add_argument("--summary-json", default=RIGHTBRAIN_REJECTION_CURRICULUM_V1_REPORT_JSON_PATH)
    parser.add_argument("--summary-md", default=RIGHTBRAIN_REJECTION_CURRICULUM_V1_REPORT_MD_PATH)
    args = parser.parse_args()

    report = json.loads(Path(args.source_report).read_text(encoding="utf-8"))
    rows, summary = build_curriculum(report)
    if not rows:
        raise RuntimeError("No rejected model candidates were converted into curriculum rows.")

    Path(args.output).write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    Path(args.summary_json).write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_markdown(summary, rows, args.summary_md)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
