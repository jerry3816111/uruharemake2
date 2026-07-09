#!/usr/bin/env python3
"""Build a v13 RightBrain SFT supplement from promoted runtime rejections."""

import argparse
import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from build_rightbrain_rejection_curriculum_v1 import (
    _payload_for_case,
    _target_errors,
)
from eval_rightbrain_model_surface_holdout import _case_inputs
from project_paths import (
    REPORTS_DIR,
    RIGHTBRAIN_RUNTIME_REJECTION_CURRICULUM_V13_DATASET_PATH,
    RIGHTBRAIN_RUNTIME_REJECTION_CURRICULUM_V13_REPORT_JSON_PATH,
    RIGHTBRAIN_RUNTIME_REJECTION_CURRICULUM_V13_REPORT_MD_PATH,
)
from uruha_brain_mac import RIGHT_BRAIN_MODEL_SYSTEM_PROMPT, RightBrain


TZ = ZoneInfo("Asia/Tokyo")
POLITE_RE = re.compile(
    r"(?:です|ます|でした|ません|ましょう|ください|ございました|しましょう)"
    r"(?:よね|よ|ね)?(?:[。！？!?、]|$)"
)

DEFAULT_SOURCE_REPORTS = (
    Path(REPORTS_DIR) / "rightbrain_runtime_promoted_adapter_holdout_c3.json",
    Path(REPORTS_DIR) / "rightbrain_runtime_promoted_adapter_holdout_c3_seed20260709.json",
)

TARGET_VARIANTS_BY_CASE = {
    "explicit_stomach_coffee": [
        "最近は胃が弱いんだから、コーヒーは控えめにしとけ。",
        "胃が弱い最近なら、コーヒーは少なめにしとけ。",
        "コーヒー飲むなら少しだけ。最近は胃が弱いんだから無理すんな。",
        "最近は胃が弱いんだし、今日はコーヒーやめとく方が無難だろ。",
    ],
    "explicit_spicy_food_update": [
        "最近は辛いものを控えたいんだから、辛いものは控えめにしとけ。",
        "最近は辛いものを控えたいんだろ。今日は控えめでいい。",
        "胃のこと考えるなら、辛いものは今日は少なめにしとけ。",
        "最近の体調なら、辛いものは控えめにしとけ。",
    ],
    "background_family_pressure": [
        "今やるなら小さく済ませろ。後で戻せる形にしとけ。",
        "今日は負荷を軽くしろ。小さく終わるやつだけでいい。",
        "責める日じゃない。今は小さいこと一個で済ませろ。",
        "休む寄りでいい。やるなら負荷の軽いやつだけにしとけ。",
    ],
    "private_do_not_mention": [
        "まあ、じゃあ軽い話題でいいだろ。最近どうしてたんだよ。",
        "話題なら近況でいい。最近どうしてたんだよ。",
        "重い話じゃなくていい。最近どうしてたかからでいいだろ。",
        "軽い話題にするか。最近どうしてたかだけ聞かせろ。",
    ],
    "no_memory_plain_question": [
        "迷うなら軽い方からでいい。後で足せる形にしとけ。",
        "分かる範囲で言うなら、軽いやつからでいい。",
        "分からない所は決めつけるな。後で足せる形にしとけ。",
        "今は決めつけず、後で変えられる予定にしとけ。",
    ],
    "support_tired_no_closing_template": [
        "今日はもう粘るな。疲れてる時は休む方が先だろ。",
        "そんなに疲れてるなら、今日は無理せず休め。",
        "喋る気力ないなら今日は休め。疲れてる時は寝る方が先だろ。",
        "疲れてるなら短く終わり。今日は休む方に寄せとけ。",
    ],
    "support_read_receipt_self_blame": [
        "既読だけで不安になるよな。理由は分からない。自分が悪いと決めつけず、少し置け。",
        "返事がない理由はまだ分からない。自分が悪いって決めるのは早いだろ。",
        "既読で止まると不安になるけど、理由なしに自分のせいへ持ってくな。",
        "返信がない理由はまだ見えてない。自分が悪いって決めつけるな。",
    ],
    "reference_fragment_probe": [
        "まあ、それ何ネタだよ。歌詞なら曲名まで出せって。",
        "それ何の元ネタだよ。曲名か作品名まで出せって。",
        "断片だけじゃ分からん。元ネタか曲名を出せ。",
        "それ歌詞系なら曲名言え。今のだけじゃ拾えない。",
    ],
    "absurdity_mirror_quantum_police": [
        "てか、は？量子の話どこから来たんだよ。急に暴れるなって。",
        "何その急なノリ。意味分かんなすぎるだろ。",
        "急に何の話だよ。ノリが暴れすぎだろ。",
        "意味分かんないけど、ノリだけは強いな。",
    ],
    "daily_state_answer": [
        "普通に、今はだらっとしてる。話すくらいなら普通にいける。",
        "今はだらっとしてる。話すくらいならできる。",
        "今はぼーっと休んでた。用なら聞く。",
        "今ちょっとだらだらしてた。話すなら普通にいける。",
    ],
}


def _load_report(path):
    report = json.loads(Path(path).read_text(encoding="utf-8"))
    report["_source_path"] = str(path)
    return report


def _report_rows_by_id(report):
    return {str(row.get("id")): row for row in report.get("cases") or []}


def _case_report_bundle(source_reports, case_id):
    rows = []
    for report in source_reports:
        row = _report_rows_by_id(report).get(case_id)
        if row:
            rows.append((report, row))
    return rows


def _unique_strings(values):
    output = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in output:
            output.append(text)
    return output


def _aggregated_rejections(bundle):
    examples = []
    reason_counts = Counter()
    for report, row in bundle:
        seed = report.get("seed")
        for reason in row.get("model_rejection_reasons") or []:
            reason_counts[reason] += 1
        for item in row.get("model_rejected_candidates") or []:
            examples.append(
                {
                    "source_report": Path(report["_source_path"]).name,
                    "seed": seed,
                    "candidate_index": item.get("candidate_index"),
                    "raw_candidate": item.get("raw_candidate", ""),
                    "rejection_reasons": item.get("rejection_reasons") or [],
                }
            )
    return examples, reason_counts


def _target_items_for_case(case_id, bundle):
    target_items = []
    for _, row in bundle:
        target_items.append(("runtime_deterministic_pass", row.get("deterministic_reply")))
    target_items.extend(
        ("contract_preserving_variant", target) for target in TARGET_VARIANTS_BY_CASE.get(case_id, [])
    )
    output = []
    seen = set()
    for source, value in target_items:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        output.append((source, text))
    return output


def _target_validation_errors(reply, payload):
    errors = list(_target_errors(reply, payload))
    if POLITE_RE.search(str(reply or "")):
        errors.append("polite_tone_drift")
    return errors


def build_curriculum(source_reports, cases=None):
    cases = list(cases or _case_inputs())
    rightbrain = RightBrain(load_model=False)
    rows = []
    skipped = Counter()
    reason_counts = Counter()
    case_reason_counts = {}
    category_counts = Counter()
    target_source_counts = Counter()
    seen = set()

    for case in cases:
        bundle = _case_report_bundle(source_reports, case["id"])
        if not bundle:
            skipped["missing_report_row"] += 1
            continue
        generated = sum(int((row.get("generated_candidate_count") or 0)) for _, row in bundle)
        if generated <= 0:
            skipped["no_model_generation"] += 1
            continue

        rejection_examples, per_case_reasons = _aggregated_rejections(bundle)
        if not per_case_reasons:
            skipped["no_rejection"] += 1
            continue
        if not all(row.get("deterministic_quality_pass") for _, row in bundle):
            skipped["deterministic_target_failed"] += 1
            continue

        payload = json.loads(_payload_for_case(rightbrain, case))
        target_items = _target_items_for_case(case["id"], bundle)
        if not target_items:
            skipped["empty_target_reply"] += 1
            continue

        kept_for_case = 0
        for target_index, (target_source, target_reply) in enumerate(target_items, start=1):
            target_errors = _target_validation_errors(target_reply, payload)
            if target_errors:
                skipped[f"target_validation_failed:{case['id']}:{','.join(target_errors)}"] += 1
                continue
            row_key = json.dumps([case["id"], payload, target_reply], ensure_ascii=False, sort_keys=True)
            if row_key in seen:
                skipped["duplicate_target"] += 1
                continue
            seen.add(row_key)
            rows.append(
                {
                    "id": f"rb_runtime_rejection_v13_{len(rows) + 1:04d}",
                    "source_case_id": case["id"],
                    "category": case["category"],
                    "training_role": "rightbrain_runtime_rejection_repair_contract_v13_sft",
                    "source_reports": [Path(report["_source_path"]).name for report, _ in bundle],
                    "source_seeds": [report.get("seed") for report, _ in bundle],
                    "failure_reasons": sorted(per_case_reasons),
                    "failure_reason_counts": dict(per_case_reasons),
                    "rejected_candidate_examples": rejection_examples,
                    "target_source": target_source,
                    "target_variant_index": target_index,
                    "messages": [
                        {"role": "system", "content": RIGHT_BRAIN_MODEL_SYSTEM_PROMPT},
                        {"role": "user", "content": json.dumps(payload, ensure_ascii=False, separators=(",", ":"))},
                        {"role": "assistant", "content": target_reply},
                    ],
                }
            )
            kept_for_case += 1
            category_counts[case["category"]] += 1
            target_source_counts[target_source] += 1
        if kept_for_case:
            case_reason_counts[case["id"]] = dict(per_case_reasons)
            reason_counts.update(per_case_reasons)

    summary = {
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "scope": "rightbrain_runtime_rejection_curriculum_v13",
        "source_reports": [Path(report["_source_path"]).name for report in source_reports],
        "source_adapter_refs": sorted({str(report.get("adapter_ref")) for report in source_reports}),
        "source_seeds": [report.get("seed") for report in source_reports],
        "source_candidate_count_per_case": sorted(
            {report.get("candidate_count_per_case") for report in source_reports}
        ),
        "case_count": len(cases),
        "case_count_with_training_rows": len(case_reason_counts),
        "curriculum_row_count": len(rows),
        "skipped_counts": dict(skipped),
        "failure_reason_counts": dict(reason_counts),
        "case_reason_counts": case_reason_counts,
        "category_counts": dict(category_counts),
        "target_source_counts": dict(target_source_counts),
        "training_boundary": (
            "This v13 supplement is mined from promoted runtime holdouts under production candidate_count=3. "
            "Rejected raw candidates are stored only as error metadata; assistant targets are deterministic "
            "quality-pass replies or manually curated Japanese variants that pass the same contract validator. "
            "Accepted model replies are intentionally not fed back as positives, because contract pass does not "
            "guarantee human-like naturalness."
        ),
    }
    return rows, summary


def write_markdown(summary, rows, path):
    lines = [
        "# RightBrain Runtime Rejection Curriculum v13",
        "",
        "## 一句話結論",
        "",
        "這份資料把 promoted v10 右腦在真實 runtime holdout 中失敗的候選，轉成下一輪 v13 LoRA 的補強資料。",
        "",
        "## 這次補的是什麼",
        "",
        "| 項目 | 內容 |",
        "|---|---|",
        f"| source reports | {', '.join(summary['source_reports'])} |",
        f"| source adapter | {', '.join(summary['source_adapter_refs'])} |",
        f"| seeds | {', '.join(str(seed) for seed in summary['source_seeds'])} |",
        f"| runtime candidates per case | {', '.join(str(item) for item in summary['source_candidate_count_per_case'])} |",
        f"| training cases | {summary['case_count_with_training_rows']} / {summary['case_count']} |",
        f"| curriculum rows | {summary['curriculum_row_count']} |",
        "",
        "## 失敗原因分布",
        "",
        "| failure reason | count |",
        "|---|---:|",
    ]
    for reason, count in sorted(summary["failure_reason_counts"].items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"| {reason} | {count} |")
    lines.extend(
        [
            "",
            "## Case 覆蓋",
            "",
            "| case | main reasons | target rows |",
            "|---|---|---:|",
        ]
    )
    row_counts = Counter(row["source_case_id"] for row in rows)
    for case_id, reasons in sorted(summary["case_reason_counts"].items()):
        reason_text = ", ".join(f"{name}={count}" for name, count in sorted(reasons.items()))
        lines.append(f"| {case_id} | {reason_text} | {row_counts[case_id]} |")
    lines.extend(
        [
            "",
            "## 訓練樣本",
            "",
            "| case | target source | target reply |",
            "|---|---|---|",
        ]
    )
    for row in rows:
        target = row["messages"][-1]["content"]
        lines.append(f"| {row['source_case_id']} | {row['target_source']} | {target} |")
    lines.extend(["", "## 研究邊界", "", f"- {summary['training_boundary']}", ""])
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-report", action="append", default=[])
    parser.add_argument("--output", default=RIGHTBRAIN_RUNTIME_REJECTION_CURRICULUM_V13_DATASET_PATH)
    parser.add_argument("--summary-json", default=RIGHTBRAIN_RUNTIME_REJECTION_CURRICULUM_V13_REPORT_JSON_PATH)
    parser.add_argument("--summary-md", default=RIGHTBRAIN_RUNTIME_REJECTION_CURRICULUM_V13_REPORT_MD_PATH)
    args = parser.parse_args()

    report_paths = [Path(path) for path in args.source_report] or list(DEFAULT_SOURCE_REPORTS)
    source_reports = [_load_report(path) for path in report_paths]
    rows, summary = build_curriculum(source_reports)
    if not rows:
        raise RuntimeError("No runtime rejections were converted into curriculum rows.")

    Path(args.output).write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    Path(args.summary_json).write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_markdown(summary, rows, args.summary_md)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
