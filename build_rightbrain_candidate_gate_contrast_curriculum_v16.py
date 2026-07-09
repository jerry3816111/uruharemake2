#!/usr/bin/env python3
"""Build v16 RightBrain rows aligned with the runtime failure watchlist.

v15 showed that adding clean SFT variants was not enough: the trained adapter
accepted fewer candidates and missed semantic slots more often. v16 keeps the
topics holdout-separated, but trains against the same abstract failure watchlist
that the runtime payload now exposes.
"""

import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from build_rightbrain_candidate_gate_curriculum_v15 import (
    _default_memory_brief,
    _holdout_boundary,
    _load_reports,
    _target_validation_errors,
)
from project_paths import (
    RIGHTBRAIN_CANDIDATE_GATE_CONTRAST_CURRICULUM_V16_DATASET_PATH,
    RIGHTBRAIN_CANDIDATE_GATE_CONTRAST_CURRICULUM_V16_REPORT_JSON_PATH,
    RIGHTBRAIN_CANDIDATE_GATE_CONTRAST_CURRICULUM_V16_REPORT_MD_PATH,
)
from rightbrain_language_quality import (
    ASCII_WORD_RE,
    FOREIGN_SCRIPT_RE,
    NONSTANDARD_CJK_RE,
    POLITE_RE,
)
from uruha_brain_mac import RIGHT_BRAIN_MODEL_CONTRACT_VERSION, RIGHT_BRAIN_MODEL_SYSTEM_PROMPT, RightBrain


TZ = ZoneInfo("Asia/Tokyo")
DEFAULT_SOURCE_REPORTS = [
    "reports/rightbrain_v15_candidate_gate_holdout_c3.json",
    "reports/rightbrain_v15_candidate_gate_holdout_c3_seed20260709.json",
]
DEFAULT_COMPARE_REPORT = "reports/rightbrain_v15_candidate_gate_compare_report.json"


FAMILY_SPECS = [
    {
        "id": "v16_group_reply_delay",
        "category": "support_contrast",
        "failure_families": ["semantic_slots_missing", "polite_tone_drift"],
        "meaning": "グループチャットで返事が止まって不安だが、理由は不明で自分のせいと決めないよう返す。",
        "scene": "support",
        "intent": "reply_anxiety_support",
        "surface_act": "stop_self_blame",
        "content_units": ["返事が止まっている", "理由は分からない", "自分のせいと決めない", "少し待つ"],
        "grounding_terms": ["返事", "理由", "自分", "待つ"],
        "required_marker_groups": [["返事", "返信"], ["理由", "分から"], ["自分", "せい", "悪い"], ["待"]],
        "max_chars": 92,
        "targets": [
            "返事が止まると不安だよな。でも理由はまだ分からない。自分のせいと決めず少し待て。",
            "返信がない理由は見えてない。自分が悪いって決めつけず、少し待て。",
            "返事待ちはきついけど、理由は不明だろ。自分のせいにするな。",
            "返事がないだけで自分を責めるな。理由はまだ分からないし、少し待て。",
        ],
    },
    {
        "id": "v16_manga_fragment_source",
        "category": "repair_contrast",
        "failure_families": ["unexpected_ascii_leak", "semantic_slots_missing"],
        "meaning": "断片的な台詞だけでは元ネタを特定できないので、作品名かタイトルを求める。",
        "scene": "reference_repair",
        "intent": "ask_source",
        "surface_act": "clarify_reference",
        "content_units": ["断片だけでは分からない", "元ネタ", "作品名かタイトル"],
        "grounding_terms": ["断片", "元ネタ", "作品名", "タイトル"],
        "required_marker_groups": [["断片", "今のだけ", "それだけ"], ["元ネタ", "作品名", "タイトル"]],
        "max_chars": 72,
        "targets": [
            "断片だけじゃ分からん。元ネタか作品名を出せ。",
            "今のだけじゃ拾えない。作品名かタイトルまで言え。",
            "それだけで特定は無理だろ。元ネタを出せ。",
            "その断片の元ネタ確認なら、作品名くらい出せって。",
        ],
    },
    {
        "id": "v16_daily_low_energy_status",
        "category": "daily_contrast",
        "failure_families": ["cjk_language_leak", "unicode_replacement_character", "unexpected_ascii_leak"],
        "meaning": "今はぼんやり休んでいるが、話すくらいならできると短く返す。",
        "scene": "daily_state",
        "intent": "state_answer",
        "surface_act": "casual_status",
        "content_units": ["今", "ぼんやり休んでいる", "話せる"],
        "grounding_terms": ["今", "ぼんやり", "休", "話"],
        "required_marker_groups": [["今"], ["ぼんやり", "だら", "休"], ["話", "聞く"]],
        "max_chars": 70,
        "targets": [
            "今はぼんやり休んでた。話すくらいならいける。",
            "今ちょっとだらっとしてた。話なら聞く。",
            "今は休み気味。話すくらいなら別にいい。",
            "今ぼーっと休んでた。話があるなら聞く。",
        ],
    },
    {
        "id": "v16_sleep_debt_boundary",
        "category": "support_contrast",
        "failure_families": ["polite_tone_drift", "duplicate_candidate"],
        "meaning": "眠気で限界の相手に、無理に続けず寝るよう短く返す。",
        "scene": "support",
        "intent": "fatigue_support",
        "surface_act": "permission_to_stop",
        "content_units": ["眠い", "無理しない", "寝る"],
        "grounding_terms": ["眠", "無理", "寝"],
        "required_marker_groups": [["眠", "疲"], ["無理", "休", "寝"]],
        "max_chars": 66,
        "targets": [
            "眠いならもう無理すんな。今日は寝ろ。",
            "その眠さなら続けるな。寝る方が先だろ。",
            "無理しても雑になるだけだ。眠いなら休め。",
            "今日は閉じていい。眠い時は寝ろ。",
        ],
    },
    {
        "id": "v16_private_school_topic",
        "category": "private_memory_contrast",
        "failure_families": ["cjk_language_leak", "nonstandard_cjk_surface", "over_max_chars"],
        "meaning": "非公開の学校事情には触れず、軽い近況の話へ移す。",
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
        "id": "v16_throat_coffee_update",
        "category": "updated_preference_contrast",
        "failure_families": ["semantic_slots_missing", "nonstandard_cjk_surface"],
        "meaning": "最近は喉が荒れやすいので、コーヒーを飲むなら少しだけにするよう返す。",
        "scene": "health_food_advice",
        "intent": "practical_action_response",
        "surface_act": "soft_boundary",
        "content_units": ["最近の喉", "コーヒー", "少しだけ"],
        "grounding_terms": ["喉", "コーヒー", "少し"],
        "required_marker_groups": [["喉"], ["コーヒー"], ["少し", "控えめ", "薄め"]],
        "max_chars": 74,
        "targets": [
            "喉が荒れ気味なら、コーヒーは少しだけにしとけ。",
            "コーヒー飲むなら少しだけ。喉が荒れてる時に攻めるな。",
            "最近喉が荒れやすいなら、コーヒーも控えめでいい。",
            "喉が気になる日は、コーヒーは少しで止めとけ。",
        ],
    },
    {
        "id": "v16_absurd_train_moon",
        "category": "tease_contrast",
        "failure_families": ["unexpected_ascii_leak", "cjk_language_leak", "nonstandard_punctuation"],
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
    {
        "id": "v16_uncertain_weekend_plan",
        "category": "no_memory_contrast",
        "failure_families": ["semantic_slots_missing", "polite_tone_drift"],
        "meaning": "分からない前提を決めつけず、後から変えられる軽い予定にするよう返す。",
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
]


def _source_failure_family_counts(compare_report_path=DEFAULT_COMPARE_REPORT):
    path = Path(compare_report_path)
    if not path.exists():
        return {}
    report = json.loads(path.read_text(encoding="utf-8"))
    return {
        row["reason"]: int(row.get("candidate_count") or 0)
        for row in report.get("rejection_reason_deltas", {}).get("family", [])
    }


def _persona_expression_brief(mood=0, trust=58):
    return {
        "role": "surface_style_only",
        "state": "neutral_energy" if mood >= -20 else "low_energy",
        "relationship_distance": "moderate" if trust < 72 else "familiar",
        "stable_traits": ["lazy_short", "slightly_bratty", "not_customer_service"],
        "must_not_override": ["leftbrain_plan", "required_marker_groups", "audited_memory_policy"],
    }


def _watchlist(required_marker_groups):
    rightbrain = RightBrain(load_model=False)
    return rightbrain._model_surface_failure_watchlist({"required_marker_groups": required_marker_groups})


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
            "persona_expression_brief": _persona_expression_brief(),
            "mood": -5 if spec["category"].startswith("support") else 0,
            "trust": 58,
            "max_chars": int(spec["max_chars"]),
        },
        "required_marker_groups": list(spec["required_marker_groups"]),
        "forbidden_markers": list(spec.get("forbidden_markers") or []),
        "surface_failure_watchlist": _watchlist(spec["required_marker_groups"]),
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


def _target_errors_v16(reply, payload):
    errors = list(_target_validation_errors(reply, payload))
    if POLITE_RE.search(str(reply or "")):
        errors.append("polite_tone_drift")
    return list(dict.fromkeys(errors))


def _diagnostic_family_counts(reports):
    counts = Counter()
    for report in reports:
        for case in report.get("cases") or []:
            for reason in case.get("model_rejection_reasons") or []:
                counts[str(reason).split(":", 1)[0]] += 1
    return counts


def build_curriculum(specs=None, source_reports=None, compare_report_path=DEFAULT_COMPARE_REPORT):
    specs = list(specs or FAMILY_SPECS)
    source_reports = list(source_reports or _load_reports(DEFAULT_SOURCE_REPORTS))
    diagnostic_counts = _diagnostic_family_counts(source_reports)
    compare_family_counts = _source_failure_family_counts(compare_report_path)
    rows = []
    skipped = Counter()
    family_counts = Counter()
    category_counts = Counter()
    seen = set()

    for spec in specs:
        payload = _payload(spec)
        for target_index, target in enumerate(spec["targets"], start=1):
            errors = _target_errors_v16(target, payload)
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
                    "id": f"rb_candidate_gate_contrast_v16_{len(rows) + 1:04d}",
                    "source_case_id": spec["id"],
                    "category": spec["category"],
                    "training_role": "rightbrain_candidate_gate_failure_watchlist_v16_sft",
                    "failure_families": list(spec["failure_families"]),
                    "target_variant_index": target_index,
                    "contrast_focus": {
                        "positive_rule": "cover every required_marker_group before optimizing style",
                        "bad_candidate_failure_families": list(spec["failure_families"]),
                    },
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
        "scope": "rightbrain_candidate_gate_contrast_curriculum_v16",
        "source_diagnostic_reports": [Path(report["_source_path"]).name for report in source_reports],
        "source_compare_report": Path(compare_report_path).name,
        "design": (
            "v16 aligns supplemental SFT rows with the runtime surface_failure_watchlist. "
            "It targets PR68 regressions without reusing holdout case IDs or target replies."
        ),
        "curriculum_row_count": len(rows),
        "family_spec_count": len(specs),
        "category_counts": dict(category_counts),
        "failure_family_counts": dict(family_counts),
        "source_diagnostic_family_counts": dict(diagnostic_counts),
        "source_compare_family_counts": compare_family_counts,
        "skipped_counts": dict(skipped),
        "data_boundary": boundary,
        "promotion_boundary": (
            "這是補充訓練資料與 runtime prompt contract 的實驗準備，不是升版證據。任何用它訓練出的 adapter，"
            "都必須先通過 matched-seed model-loaded holdout，才能成為預設 RightBrain adapter。"
        ),
    }
    return rows, summary


def write_markdown(summary, rows, path):
    lines = [
        "# RightBrain Candidate Gate Contrast Curriculum v16",
        "",
        "## 一句話結論",
        "",
        "v16 把 PR68 中 v15 退步的錯誤族群，轉成和 runtime payload 相同的 watchlist 訓練資料；它不是 holdout 小抄。",
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
        "## PR68 退步族群與 v16 覆蓋",
        "",
        "| failure family | PR68 candidate count | v16 rows covering family |",
        "|---|---:|---:|",
    ]
    families = sorted(
        set(summary["source_compare_family_counts"]) | set(summary["failure_family_counts"]),
        key=lambda family: (-summary["source_compare_family_counts"].get(family, 0), family),
    )
    for family in families:
        lines.append(
            f"| {family} | {summary['source_compare_family_counts'].get(family, 0)} | "
            f"{summary['failure_family_counts'].get(family, 0)} |"
        )
    lines.extend(
        [
            "",
            "## 訓練樣本",
            "",
            "| source case | category | families | target reply |",
            "|---|---|---|---|",
        ]
    )
    for row in rows:
        lines.append(
            f"| {row['source_case_id']} | {row['category']} | {', '.join(row['failure_families'])} | "
            f"{row['messages'][-1]['content']} |"
        )
    lines.extend(["", "## 邊界", "", f"- {summary['promotion_boundary']}", ""])
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=RIGHTBRAIN_CANDIDATE_GATE_CONTRAST_CURRICULUM_V16_DATASET_PATH)
    parser.add_argument("--summary-json", default=RIGHTBRAIN_CANDIDATE_GATE_CONTRAST_CURRICULUM_V16_REPORT_JSON_PATH)
    parser.add_argument("--summary-md", default=RIGHTBRAIN_CANDIDATE_GATE_CONTRAST_CURRICULUM_V16_REPORT_MD_PATH)
    args = parser.parse_args()

    rows, summary = build_curriculum()
    if not rows:
        raise RuntimeError("No v16 candidate-gate contrast rows were generated.")
    if summary["data_boundary"]["diagnostic_only"]:
        raise RuntimeError("Generated v16 curriculum overlaps source holdout; refusing to write dataset.")
    Path(args.output).write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    Path(args.summary_json).write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_markdown(summary, rows, args.summary_md)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
