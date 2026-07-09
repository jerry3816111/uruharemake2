#!/usr/bin/env python3
"""Build v15 RightBrain SFT rows from PR66 candidate-gate diagnostics.

The rows intentionally generalize observed failure families into new topics.
They are training material for surface quality, not answers to the holdout.
"""

import argparse
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from build_rightbrain_rejection_curriculum_v1 import _target_errors
from project_paths import (
    RIGHTBRAIN_CANDIDATE_GATE_CURRICULUM_V15_DATASET_PATH,
    RIGHTBRAIN_CANDIDATE_GATE_CURRICULUM_V15_REPORT_JSON_PATH,
    RIGHTBRAIN_CANDIDATE_GATE_CURRICULUM_V15_REPORT_MD_PATH,
)
from rightbrain_language_quality import (
    ASCII_WORD_RE,
    CHINESE_SPECIFIC_RE,
    FOREIGN_SCRIPT_RE,
    NONSTANDARD_CJK_RE,
    POLITE_RE,
    UNICODE_REPLACEMENT_CHAR,
)
from uruha_brain_mac import RIGHT_BRAIN_MODEL_CONTRACT_VERSION, RIGHT_BRAIN_MODEL_SYSTEM_PROMPT


TZ = ZoneInfo("Asia/Tokyo")
DEFAULT_SOURCE_REPORTS = [
    "reports/rightbrain_candidate_gate_observability_holdout_c3.json",
    "reports/rightbrain_candidate_gate_observability_holdout_c3_seed20260709.json",
]
CAREGIVER_OR_SERVICE_RE = re.compile(r"(?:ませんかね|みてはどう|方がいいでしょう|(?:し|て)あげ(?:る|よう|たい|れば))")


FAMILY_SPECS = [
    {
        "id": "v15_herbal_tea_throat",
        "category": "explicit_memory_food_generalized",
        "failure_families": ["unexpected_ascii_leak", "semantic_slots_missing", "cjk_language_leak"],
        "meaning": "喉が荒れやすい最近の状態を踏まえて、ハーブティーはぬるめで少しにするよう返す。",
        "scene": "health_food_advice",
        "intent": "practical_action_response",
        "surface_act": "soft_boundary",
        "content_units": ["最近の喉の状態", "ハーブティー", "ぬるめで少し"],
        "grounding_terms": ["喉", "ハーブティー", "ぬるめ", "少し"],
        "required_marker_groups": [["喉"], ["ハーブティー"], ["ぬるめ", "少し", "控えめ"]],
        "max_chars": 74,
        "targets": [
            "喉が荒れ気味なら、ハーブティーはぬるめで少しにしとけ。",
            "ハーブティー飲むなら少しだけ。喉が荒れてる時に攻めるな。",
            "最近喉が荒れやすいなら、ハーブティーも控えめでいい。",
            "喉が気になる日は、ハーブティーはぬるめで止めとけ。",
        ],
    },
    {
        "id": "v15_dairy_update",
        "category": "updated_preference_generalized",
        "failure_families": ["nonstandard_cjk_surface", "semantic_slots_missing", "polite_tone_drift"],
        "meaning": "最近は乳製品を控えたい更新を踏まえて、アイスは少なめにするよう返す。",
        "scene": "updated_preference_advice",
        "intent": "practical_action_response",
        "surface_act": "soft_boundary",
        "content_units": ["最近は乳製品を控えたい", "アイス", "少なめ"],
        "grounding_terms": ["乳製品", "アイス", "少なめ"],
        "required_marker_groups": [["乳製品", "アイス"], ["控え", "少なめ", "少し"], ["最近"]],
        "max_chars": 74,
        "targets": [
            "最近は乳製品控えたいんだろ。アイスは少なめにしとけ。",
            "アイス行くなら少しだけ。最近は乳製品控えめだろ。",
            "最近の流れなら、乳製品は少なめで止めとけ。",
            "アイスは分かるけど、最近は控えめにしとけ。",
        ],
    },
    {
        "id": "v15_background_exam_pressure",
        "category": "background_memory_generalized",
        "failure_families": ["over_max_chars", "polite_tone_drift", "nonstandard_punctuation"],
        "meaning": "背景の試験不安は直接言わず、今日は範囲を小さくして一個だけ進めるよう返す。",
        "scene": "background_only_support",
        "intent": "practical_action_response",
        "surface_act": "low_pressure_guidance",
        "content_units": ["範囲を小さくする", "一個だけ進める", "責めない"],
        "grounding_terms": ["範囲", "小さい", "一個", "責め"],
        "required_marker_groups": [["範囲", "小さ"], ["一個", "一つ"], ["責め", "休"]],
        "max_chars": 74,
        "audited_memory_brief": {
            "policy": "background_only",
            "speakability": "background_only",
            "allowed_memory_cues": [],
            "background_style_cues": [{"kind": "exam_pressure", "style_influence": "soft_context_only"}],
            "forbidden": ["do_not_quote_raw_memory", "do_not_reveal_source_text"],
        },
        "targets": [
            "今日は責めずに範囲を小さくしろ。一個だけでいい。",
            "範囲は小さく。責めずに一つだけ進めろ。",
            "今は責めるな。範囲を小さくして一個だけだろ。",
            "休む寄りでいい。やるなら小さい範囲を一つだけ。",
        ],
    },
    {
        "id": "v15_private_work_topic",
        "category": "private_memory_generalized",
        "failure_families": ["cjk_language_leak", "nonstandard_cjk_surface", "over_max_chars"],
        "meaning": "非公開の仕事事情には触れず、軽い近況の話へ移す。",
        "scene": "private_do_not_mention",
        "intent": "topic_proposal",
        "surface_act": "turn_opening",
        "content_units": ["軽い話題", "最近の近況"],
        "grounding_terms": ["話題", "最近", "近況"],
        "required_marker_groups": [["話題", "話"], ["最近", "近況", "どうしてた"]],
        "max_chars": 72,
        "audited_memory_brief": {
            "policy": "do_not_mention",
            "speakability": "private",
            "allowed_memory_cues": [],
            "background_style_cues": [],
            "forbidden": ["do_not_quote_raw_memory", "do_not_reveal_source_text"],
        },
        "targets": [
            "軽い話題でいいだろ。最近どうしてたんだよ。",
            "話すなら近況でいい。最近どうしてた。",
            "重くしなくていい。最近の話でもしろ。",
            "じゃあ軽い話題な。最近何してたんだよ。",
        ],
    },
    {
        "id": "v15_unknown_trip_choice",
        "category": "no_memory_generalized",
        "failure_families": ["semantic_slots_missing", "unexpected_ascii_leak", "missing_japanese_surface"],
        "meaning": "分からない前提を決めつけず、後で変えられる軽い予定にするよう返す。",
        "scene": "no_memory_plain_question",
        "intent": "practical_action_response",
        "surface_act": "uncertainty_safe_advice",
        "content_units": ["分からない所は決めつけない", "後で変えられる", "軽い予定"],
        "grounding_terms": ["分からない", "後で", "軽い"],
        "required_marker_groups": [["分から", "決めつけ"], ["後で", "変え"], ["軽"]],
        "max_chars": 74,
        "targets": [
            "分からない所は決めつけるな。後で変えられる軽いやつにしとけ。",
            "今は決めつけず、後で変えられる軽い予定にしとけ。",
            "分からない所は置け。軽く行って後で変えろ。",
            "後で変えられる軽い形にしとけ。分からない所は詰めるな。",
        ],
    },
    {
        "id": "v15_sleepy_support",
        "category": "support_generalized",
        "failure_families": ["duplicate_candidate", "polite_tone_drift", "semantic_slots_missing"],
        "meaning": "眠気で限界の相手に、無理に続けず休むよう短く返す。",
        "scene": "support",
        "intent": "fatigue_support",
        "surface_act": "permission_to_stop",
        "content_units": ["眠い", "無理しない", "休む"],
        "grounding_terms": ["眠", "無理", "休"],
        "required_marker_groups": [["眠", "疲"], ["無理", "休", "寝"]],
        "max_chars": 66,
        "targets": [
            "眠いならもう無理すんな。今日は休め。",
            "その眠さなら続けるな。寝る方が先だろ。",
            "無理しても雑になるだけだ。眠いなら休め。",
            "今日は閉じていい。眠い時は寝ろ。",
        ],
    },
    {
        "id": "v15_reference_fragment",
        "category": "repair_generalized",
        "failure_families": ["unexpected_ascii_leak", "polite_tone_drift", "foreign_script_leak"],
        "meaning": "断片だけでは元ネタを特定できないので、曲名か作品名を求める。",
        "scene": "reference_repair",
        "intent": "ask_source",
        "surface_act": "clarify_reference",
        "content_units": ["断片だけでは分からない", "元ネタ", "曲名か作品名"],
        "grounding_terms": ["元ネタ", "曲名", "作品名"],
        "required_marker_groups": [["元ネタ", "曲名", "作品名"]],
        "max_chars": 70,
        "targets": [
            "断片だけじゃ分からん。元ネタか曲名を出せ。",
            "それ何の元ネタだよ。作品名まで出せって。",
            "今のだけじゃ拾えない。曲名か作品名を言え。",
            "元ネタ確認したいなら、曲名くらい出せ。",
        ],
    },
    {
        "id": "v15_absurd_weather_council",
        "category": "tease_generalized",
        "failure_families": ["semantic_slots_missing", "foreign_script_leak", "nonstandard_punctuation"],
        "meaning": "急な意味不明発話に、ノリは拾うが意味は分からないと返す。",
        "scene": "tease",
        "intent": "absurdity_mirror",
        "surface_act": "playful_confusion",
        "content_units": ["急な話", "意味が分からない", "ノリを拾う"],
        "grounding_terms": ["急", "意味", "ノリ"],
        "required_marker_groups": [["急", "何"], ["意味", "分かん", "ノリ"]],
        "max_chars": 70,
        "targets": [
            "急に何の話だよ。意味分かんないけどノリは強いな。",
            "何その急なノリ。意味分かんなすぎるだろ。",
            "急に飛びすぎだろ。意味は分からんけど勢いはある。",
            "そのノリ何なんだよ。意味分かんない方向に強いな。",
        ],
    },
]


def _default_memory_brief():
    return {
        "policy": "no_memory",
        "speakability": "no_memory",
        "allowed_memory_cues": [],
        "background_style_cues": [],
        "forbidden": [
            "do_not_quote_raw_memory",
            "do_not_reveal_source_text",
            "do_not_invent_unprovided_profile",
        ],
    }


def _payload(spec):
    return {
        "contract_version": RIGHT_BRAIN_MODEL_CONTRACT_VERSION,
        "task": "write_one_user_facing_japanese_reply",
        "contract_rule": (
            "required_marker_groups is the semantic contract. Include at least one phrase from every "
            "inner list naturally and avoid every forbidden marker."
        ),
        "user_input": spec["meaning"],
        "leftbrain_plan": {
            "scene": spec["scene"],
            "intent": spec["intent"],
            "surface_act": spec["surface_act"],
            "dialogue_act": spec.get("dialogue_act", spec["intent"]),
            "meaning": spec["meaning"],
            "content_units": list(spec["content_units"]),
            "style_operators": ["casual", "short", "no_polite_register"],
            "grounding_terms": list(spec["grounding_terms"]),
        },
        "context": {
            "memory_summary": "左脳が選択した作業記憶は発話計画に統合済み。",
            "audited_memory_brief": spec.get("audited_memory_brief") or _default_memory_brief(),
            "persona_expression_brief": {
                "role": "surface_style_only",
                "state": "neutral_energy",
                "relationship_distance": "moderate",
                "stable_traits": ["lazy_short", "slightly_bratty", "not_customer_service"],
                "must_not_override": ["leftbrain_plan", "required_marker_groups", "audited_memory_policy"],
            },
            "mood": -5 if spec["category"].startswith("support") else 0,
            "trust": 58,
            "max_chars": int(spec["max_chars"]),
        },
        "required_marker_groups": list(spec["required_marker_groups"]),
        "forbidden_markers": list(spec.get("forbidden_markers") or []),
        "reply_requirements": [
            "one sentence or short chat reply",
            "natural casual Japanese",
            "no labels or JSON",
            "no Chinese or English",
            "no foreign scripts",
            "no customer-service or caregiver tone",
            "no first person 私",
        ],
    }


def _target_validation_errors(reply, payload):
    errors = list(_target_errors(reply, payload))
    reply = str(reply or "")
    if POLITE_RE.search(reply) or CAREGIVER_OR_SERVICE_RE.search(reply):
        errors.append("polite_tone_drift")
    if ASCII_WORD_RE.search(reply):
        errors.append("unexpected_ascii_leak")
    if CHINESE_SPECIFIC_RE.search(reply):
        errors.append("cjk_language_leak")
    if NONSTANDARD_CJK_RE.search(reply):
        errors.append("nonstandard_cjk_surface")
    if FOREIGN_SCRIPT_RE.search(reply):
        errors.append("foreign_script_leak")
    if UNICODE_REPLACEMENT_CHAR in reply:
        errors.append("unicode_replacement_character")
    if any(marker in reply for marker in ["．", "｡"]):
        errors.append("nonstandard_punctuation")
    return list(dict.fromkeys(errors))


def _load_reports(paths):
    reports = []
    for path in paths:
        report = json.loads(Path(path).read_text(encoding="utf-8"))
        report["_source_path"] = str(path)
        reports.append(report)
    return reports


def _diagnostic_family_counts(reports):
    counts = Counter()
    for report in reports:
        for case in report.get("cases") or []:
            for reason in case.get("model_rejection_reasons") or []:
                counts[str(reason).split(":", 1)[0]] += 1
    return counts


def _holdout_boundary(rows, reports):
    holdout_case_ids = set()
    holdout_targets = set()
    for report in reports:
        for case in report.get("cases") or []:
            case_id = str(case.get("id") or "")
            if case_id:
                holdout_case_ids.add(case_id)
            for key in ("deterministic_reply", "final_reply"):
                target = str(case.get(key) or "").strip()
                if target:
                    holdout_targets.add(target)

    training_case_ids = {str(row.get("source_case_id") or "") for row in rows}
    training_targets = {str(row["messages"][-1].get("content") or "").strip() for row in rows}
    return {
        "holdout_case_count": len(holdout_case_ids),
        "training_source_case_count": len(training_case_ids),
        "holdout_case_overlap_count": len(training_case_ids & holdout_case_ids),
        "holdout_case_overlap_ids": sorted(training_case_ids & holdout_case_ids),
        "holdout_target_overlap_count": len(training_targets & holdout_targets),
        "holdout_target_overlap_examples": sorted(training_targets & holdout_targets)[:8],
        "diagnostic_only": bool((training_case_ids & holdout_case_ids) or (training_targets & holdout_targets)),
    }


def build_curriculum(specs=None, source_reports=None):
    specs = list(specs or FAMILY_SPECS)
    source_reports = list(source_reports or _load_reports(DEFAULT_SOURCE_REPORTS))
    diagnostic_counts = _diagnostic_family_counts(source_reports)
    rows = []
    skipped = Counter()
    family_counts = Counter()
    category_counts = Counter()
    seen = set()

    for spec in specs:
        payload = _payload(spec)
        for target_index, target in enumerate(spec["targets"], start=1):
            errors = _target_validation_errors(target, payload)
            if errors:
                skipped[f"target_validation_failed:{spec['id']}:{','.join(errors)}"] += 1
                continue
            row_key = json.dumps([spec["id"], payload, target], ensure_ascii=False, sort_keys=True)
            if row_key in seen:
                skipped["duplicate_target"] += 1
                continue
            seen.add(row_key)
            rows.append(
                {
                    "id": f"rb_candidate_gate_v15_{len(rows) + 1:04d}",
                    "source_case_id": spec["id"],
                    "category": spec["category"],
                    "training_role": "rightbrain_candidate_gate_failure_family_v15_sft",
                    "failure_families": list(spec["failure_families"]),
                    "target_variant_index": target_index,
                    "messages": [
                        {"role": "system", "content": RIGHT_BRAIN_MODEL_SYSTEM_PROMPT},
                        {"role": "user", "content": json.dumps(payload, ensure_ascii=False, separators=(",", ":"))},
                        {"role": "assistant", "content": target},
                    ],
                }
            )
            category_counts[spec["category"]] += 1
            family_counts.update(spec["failure_families"])

    boundary = _holdout_boundary(rows, source_reports)
    summary = {
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "scope": "rightbrain_candidate_gate_curriculum_v15",
        "source_diagnostic_reports": [Path(report["_source_path"]).name for report in source_reports],
        "design": (
            "Use PR66 gate/selector diagnostics only to identify failure families. "
            "Generated rows use new source_case_id values, new topics, and clean target replies."
        ),
        "curriculum_row_count": len(rows),
        "family_spec_count": len(specs),
        "category_counts": dict(category_counts),
        "failure_family_counts": dict(family_counts),
        "source_diagnostic_family_counts": dict(diagnostic_counts),
        "skipped_counts": dict(skipped),
        "data_boundary": boundary,
        "promotion_boundary": (
            "This is supplemental training data, not promotion evidence. Any adapter trained from it still needs "
            "fresh model-loaded holdout and selector diagnostics before becoming the default RightBrain adapter."
        ),
    }
    return rows, summary


def write_markdown(summary, rows, path):
    lines = [
        "# RightBrain Candidate Gate Curriculum v15",
        "",
        "## 一句話結論",
        "",
        "這份資料把 PR66 暴露出的右腦候選錯誤族群，改寫成新題材的 SFT 補強資料；它不是 holdout 小抄。",
        "",
        "## 總表",
        "",
        "| 指標 | 值 |",
        "|---|---:|",
        f"| curriculum rows | {summary['curriculum_row_count']} |",
        f"| family specs | {summary['family_spec_count']} |",
        f"| holdout case overlap | {summary['data_boundary']['holdout_case_overlap_count']} |",
        f"| holdout target overlap | {summary['data_boundary']['holdout_target_overlap_count']} |",
        f"| diagnostic only | {summary['data_boundary']['diagnostic_only']} |",
        "",
        "## 診斷來源中的錯誤族群",
        "",
        "| source failure family | observed count | training rows covering family |",
        "|---|---:|---:|",
    ]
    for family, observed in sorted(
        summary["source_diagnostic_family_counts"].items(), key=lambda item: (-item[1], item[0])
    ):
        lines.append(f"| {family} | {observed} | {summary['failure_family_counts'].get(family, 0)} |")
    lines.extend(["", "## 訓練樣本", "", "| source case | category | families | target reply |", "|---|---|---|---|"])
    for row in rows:
        lines.append(
            f"| {row['source_case_id']} | {row['category']} | {', '.join(row['failure_families'])} | {row['messages'][-1]['content']} |"
        )
    lines.extend(["", "## 邊界", "", f"- {summary['promotion_boundary']}", ""])
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=RIGHTBRAIN_CANDIDATE_GATE_CURRICULUM_V15_DATASET_PATH)
    parser.add_argument("--summary-json", default=RIGHTBRAIN_CANDIDATE_GATE_CURRICULUM_V15_REPORT_JSON_PATH)
    parser.add_argument("--summary-md", default=RIGHTBRAIN_CANDIDATE_GATE_CURRICULUM_V15_REPORT_MD_PATH)
    args = parser.parse_args()

    rows, summary = build_curriculum()
    if not rows:
        raise RuntimeError("No v15 candidate-gate curriculum rows were generated.")
    if summary["data_boundary"]["diagnostic_only"]:
        raise RuntimeError("Generated v15 curriculum overlaps source holdout; refusing to write dataset.")
    Path(args.output).write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    Path(args.summary_json).write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_markdown(summary, rows, args.summary_md)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
