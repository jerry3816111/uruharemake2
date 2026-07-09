#!/usr/bin/env python3
"""Build holdout-separated RightBrain SFT rows from v13 failure families."""

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from build_rightbrain_rejection_curriculum_v1 import _target_errors
from build_rightbrain_runtime_rejection_curriculum_v13 import DEFAULT_SOURCE_REPORTS
from project_paths import (
    RIGHTBRAIN_HOLDOUT_SEPARATED_CURRICULUM_V14_DATASET_PATH,
    RIGHTBRAIN_HOLDOUT_SEPARATED_CURRICULUM_V14_REPORT_JSON_PATH,
    RIGHTBRAIN_HOLDOUT_SEPARATED_CURRICULUM_V14_REPORT_MD_PATH,
)
from uruha_brain_mac import (
    RIGHT_BRAIN_MODEL_CONTRACT_VERSION,
    RIGHT_BRAIN_MODEL_SYSTEM_PROMPT,
)


TZ = ZoneInfo("Asia/Tokyo")
POLITE_RE = re.compile(
    r"(?:です|ます|でした|ません|ましょう|ください|ございました|しましょう)"
    r"(?:よね|よ|ね)?(?:[。！？!?、]|$)"
)


FAMILY_SPECS = [
    {
        "id": "v14_barley_tea_stomach",
        "category": "audited_memory_generalized",
        "failure_families": ["unexpected_ascii_leak", "semantic_slots_missing", "cjk_language_leak"],
        "meaning": "最近は胃が重い流れを踏まえて、玄米茶を飲むなら薄めで少しにするよう返す。",
        "scene": "health_food_advice",
        "intent": "practical_action_response",
        "surface_act": "soft_boundary",
        "content_units": ["最近の胃の状態", "玄米茶", "少量にする"],
        "grounding_terms": ["胃", "玄米茶", "少し"],
        "required_marker_groups": [["胃", "重"], ["玄米茶"], ["少し", "薄め", "控えめ"]],
        "max_chars": 74,
        "targets": [
            "胃が重いなら、玄米茶は薄めで少しにしとけ。",
            "最近胃が重いなら、玄米茶は控えめでいい。",
            "玄米茶いくなら少しだけ。胃が重い時に攻めるな。",
            "胃が重い日は、玄米茶も薄めで止めとけ。",
        ],
    },
    {
        "id": "v14_fried_food_update",
        "category": "audited_memory_generalized",
        "failure_families": ["nonstandard_cjk_surface", "semantic_slots_missing"],
        "meaning": "最近は揚げ物を控えたい更新を踏まえて、唐揚げは少なめにするよう返す。",
        "scene": "updated_preference_advice",
        "intent": "practical_action_response",
        "surface_act": "soft_boundary",
        "content_units": ["最近は揚げ物を控えたい", "唐揚げ", "少なめ"],
        "grounding_terms": ["揚げ物", "唐揚げ", "少なめ"],
        "required_marker_groups": [["揚げ物", "唐揚げ"], ["控え", "少なめ", "少し"], ["最近"]],
        "max_chars": 74,
        "targets": [
            "最近は揚げ物控えたいんだろ。唐揚げは少なめにしとけ。",
            "唐揚げ行くなら少しだけ。最近は揚げ物控えめだろ。",
            "最近の流れなら、揚げ物は少なめで止めとけ。",
            "唐揚げは分かるけど、最近は控えめにしとけ。",
        ],
    },
    {
        "id": "v14_background_deadline_pressure",
        "category": "background_memory_generalized",
        "failure_families": ["semantic_slots_missing", "over_max_chars"],
        "meaning": "背景事情は直接言わず、今日は負荷を下げて小さい作業だけにするよう返す。",
        "scene": "background_only_support",
        "intent": "practical_action_response",
        "surface_act": "low_pressure_guidance",
        "content_units": ["負荷を下げる", "小さい作業だけ", "責めない"],
        "grounding_terms": ["負荷", "小さい", "責め"],
        "required_marker_groups": [["負荷", "軽"], ["小さ", "一個"], ["責め", "休"]],
        "max_chars": 72,
        "audited_memory_brief": {
            "policy": "background_only",
            "speakability": "background_only",
            "allowed_memory_cues": [],
            "background_style_cues": [{"kind": "deadline_pressure", "style_influence": "soft_context_only"}],
            "forbidden": ["do_not_quote_raw_memory", "do_not_reveal_source_text"],
        },
        "targets": [
            "今日は責めずに負荷を軽くしろ。小さいの一個でいい。",
            "負荷は軽く。責めずに小さい作業だけで済ませろ。",
            "今は責めずに負荷下げろ。一個だけでいい。",
            "休む寄りでいい。負荷は軽く、小さいの一個だろ。",
        ],
    },
    {
        "id": "v14_private_health_topic",
        "category": "private_memory_generalized",
        "failure_families": ["cjk_language_leak", "polite_tone_drift", "over_max_chars"],
        "meaning": "非公開の体調情報には触れず、軽い話題として最近の過ごし方を聞く。",
        "scene": "private_do_not_mention",
        "intent": "topic_proposal",
        "surface_act": "turn_opening",
        "content_units": ["軽い話題", "最近の過ごし方"],
        "grounding_terms": ["話題", "最近"],
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
        "id": "v14_unknown_plan_choice",
        "category": "no_memory_generalized",
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
    {
        "id": "v14_sleep_debt_support",
        "category": "support_generalized",
        "failure_families": ["duplicate_candidate", "semantic_slots_missing", "polite_tone_drift"],
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
        "id": "v14_reply_delay_anxiety",
        "category": "support_generalized",
        "failure_families": ["semantic_slots_missing", "over_max_chars"],
        "meaning": "返信が遅い理由はまだ不明で、自分のせいと決めつけないよう返す。",
        "scene": "support",
        "intent": "reply_anxiety_support",
        "surface_act": "stop_self_blame",
        "content_units": ["返信が遅い", "理由は分からない", "自分のせいと決めつけない"],
        "grounding_terms": ["返信", "理由", "自分"],
        "required_marker_groups": [["返信", "返事"], ["理由", "分から"], ["自分", "せい", "悪い"]],
        "max_chars": 92,
        "targets": [
            "返信が遅い理由はまだ分からない。自分のせいって決めるな。",
            "返事が遅いと不安だよな。でも理由なしに自分を責めるな。",
            "返信がない理由は見えてない。自分が悪いって決めつけるな。",
            "返事待ちはきついけど、理由はまだ分からない。自分のせいにするな。",
        ],
    },
    {
        "id": "v14_fragment_source_probe",
        "category": "repair_generalized",
        "failure_families": ["unexpected_ascii_leak", "over_max_chars", "duplicate_candidate"],
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
        "id": "v14_absurd_cloud_court",
        "category": "tease_generalized",
        "failure_families": ["semantic_slots_missing", "duplicate_candidate"],
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
        "id": "v14_current_state_idle",
        "category": "daily_generalized",
        "failure_families": ["duplicate_candidate", "semantic_slots_missing"],
        "meaning": "今はぼんやり休んでいたが、話すくらいならできると返す。",
        "scene": "daily_state",
        "intent": "state_answer",
        "surface_act": "casual_status",
        "content_units": ["今", "ぼんやり休んでいた", "話せる"],
        "grounding_terms": ["今", "ぼんやり", "休"],
        "required_marker_groups": [["今"], ["ぼんやり", "だら", "休"], ["話", "聞く"]],
        "max_chars": 70,
        "targets": [
            "今はぼんやり休んでた。話すくらいならいける。",
            "今ちょっとだらっとしてた。話なら聞く。",
            "今は休み気味。話すくらいなら別にいい。",
            "今ぼーっと休んでた。話があるなら聞く。",
        ],
    },
]


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _persona_expression_brief(mood=0, trust=58):
    return {
        "role": "surface_style_only",
        "state": "neutral_energy" if mood >= -20 else "low_energy",
        "relationship_distance": "moderate" if trust < 72 else "familiar",
        "stable_traits": ["lazy_short", "slightly_bratty", "not_customer_service"],
        "must_not_override": ["leftbrain_plan", "required_marker_groups", "audited_memory_policy"],
    }


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
    mood = spec.get("mood", -5 if spec["category"].startswith("support") else 0)
    trust = spec.get("trust", 58)
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
            "persona_expression_brief": _persona_expression_brief(mood=mood, trust=trust),
            "mood": mood,
            "trust": trust,
            "max_chars": int(spec["max_chars"]),
        },
        "required_marker_groups": list(spec["required_marker_groups"]),
        "forbidden_markers": list(spec.get("forbidden_markers") or []),
        "reply_requirements": [
            "one sentence or short chat reply",
            "natural casual Japanese",
            "no labels or JSON",
            "no Chinese or English",
            "no first person 私",
        ],
    }


def _target_validation_errors(reply, payload):
    errors = list(_target_errors(reply, payload))
    if POLITE_RE.search(str(reply or "")):
        errors.append("polite_tone_drift")
    return errors


def _load_holdout_reports(paths):
    reports = []
    for path in paths:
        report = json.loads(Path(path).read_text(encoding="utf-8"))
        report["_source_path"] = str(path)
        reports.append(report)
    return reports


def _holdout_boundary(rows, holdout_reports):
    holdout_case_ids = set()
    holdout_targets = set()
    for report in holdout_reports:
        for case in report.get("cases") or []:
            case_id = str(case.get("id") or "")
            if not case_id:
                continue
            holdout_case_ids.add(case_id)
            for key in ("deterministic_reply", "final_reply"):
                target = str(case.get(key) or "").strip()
                if target:
                    holdout_targets.add((case_id, target))

    training_case_ids = {str(row.get("source_case_id") or "") for row in rows}
    training_targets = {
        (str(row.get("source_case_id") or ""), str(row["messages"][-1].get("content") or "").strip())
        for row in rows
    }
    return {
        "holdout_case_count": len(holdout_case_ids),
        "training_source_case_count": len(training_case_ids),
        "holdout_case_overlap_count": len(training_case_ids & holdout_case_ids),
        "holdout_case_overlap_ids": sorted(training_case_ids & holdout_case_ids),
        "holdout_target_overlap_count": len(training_targets & holdout_targets),
        "holdout_target_overlap_examples": [
            {"case_id": case_id, "target": target}
            for case_id, target in sorted(training_targets & holdout_targets)[:8]
        ],
        "diagnostic_only": bool((training_case_ids & holdout_case_ids) or (training_targets & holdout_targets)),
    }


def build_curriculum(specs=None, holdout_reports=None):
    specs = list(specs or FAMILY_SPECS)
    holdout_reports = list(holdout_reports or _load_holdout_reports(DEFAULT_SOURCE_REPORTS))
    rows = []
    skipped = Counter()
    category_counts = Counter()
    family_counts = Counter()
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
                    "id": f"rb_holdout_separated_v14_{len(rows) + 1:04d}",
                    "source_case_id": spec["id"],
                    "category": spec["category"],
                    "training_role": "rightbrain_holdout_separated_failure_family_v14_sft",
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

    boundary = _holdout_boundary(rows, holdout_reports)
    summary = {
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "scope": "rightbrain_holdout_separated_curriculum_v14",
        "source_failure_report": "rightbrain_v13_runtime_rejection_multiseed_report.json",
        "source_holdout_reports": [Path(report["_source_path"]).name for report in holdout_reports],
        "design": (
            "Generalize v13 failure families into new topics and source_case_ids. "
            "Rows must not reuse runtime holdout case IDs or exact target replies."
        ),
        "curriculum_row_count": len(rows),
        "family_spec_count": len(specs),
        "category_counts": dict(category_counts),
        "failure_family_counts": dict(family_counts),
        "skipped_counts": dict(skipped),
        "data_boundary": boundary,
        "promotion_boundary": (
            "This is training data only. It is safe to use as a supplemental SFT curriculum, but any adapter "
            "trained from it still needs a fresh model-loaded holdout before promotion."
        ),
    }
    return rows, summary


def write_markdown(summary, rows, path):
    lines = [
        "# RightBrain Holdout-separated Curriculum v14",
        "",
        "## 一句話結論",
        "",
        "這份資料把 v13 看到的右腦失敗族群改寫成新題材，不重用 runtime holdout 的 case id 或 target reply。",
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
        "## 覆蓋的失敗族群",
        "",
        "| failure family | rows |",
        "|---|---:|",
    ]
    for family, count in sorted(summary["failure_family_counts"].items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"| {family} | {count} |")
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
        target = row["messages"][-1]["content"]
        lines.append(
            f"| {row['source_case_id']} | {row['category']} | {', '.join(row['failure_families'])} | {target} |"
        )
    lines.extend(["", "## 邊界", "", f"- {summary['promotion_boundary']}", ""])
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=RIGHTBRAIN_HOLDOUT_SEPARATED_CURRICULUM_V14_DATASET_PATH)
    parser.add_argument("--summary-json", default=RIGHTBRAIN_HOLDOUT_SEPARATED_CURRICULUM_V14_REPORT_JSON_PATH)
    parser.add_argument("--summary-md", default=RIGHTBRAIN_HOLDOUT_SEPARATED_CURRICULUM_V14_REPORT_MD_PATH)
    args = parser.parse_args()

    rows, summary = build_curriculum()
    if not rows:
        raise RuntimeError("No holdout-separated curriculum rows were generated.")
    if summary["data_boundary"]["diagnostic_only"]:
        raise RuntimeError("Generated curriculum overlaps runtime holdout; refusing to write v14 dataset.")

    Path(args.output).write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    Path(args.summary_json).write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_markdown(summary, rows, args.summary_md)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
