#!/usr/bin/env python3
"""Build length-matched, single-semantic-slot hard negatives for SimPO."""

import argparse
import json
from collections import Counter
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from zoneinfo import ZoneInfo

from build_rightbrain_candidate_gate_contrast_curriculum_v16 import FAMILY_SPECS
from build_rightbrain_candidate_gate_curriculum_v15 import _holdout_boundary, _load_reports
from build_rightbrain_compact_slot_curriculum_v17 import _payload, _target_errors
from project_paths import (
    RIGHTBRAIN_HARD_NEGATIVE_PREFERENCE_V20_DATASET_PATH,
    RIGHTBRAIN_HARD_NEGATIVE_PREFERENCE_V20_REPORT_JSON_PATH,
    RIGHTBRAIN_HARD_NEGATIVE_PREFERENCE_V20_REPORT_MD_PATH,
)
from rightbrain_language_quality import has_bad_language, has_japanese, has_response_plan_leak
from uruha_brain_mac import RIGHT_BRAIN_MODEL_SYSTEM_PROMPT


TZ = ZoneInfo("Asia/Tokyo")
DEFAULT_SOURCE_REPORTS = [
    "reports/rightbrain_plan_surface_boundary_holdout_c3.json",
    "reports/rightbrain_plan_surface_boundary_holdout_c3_seed20260709.json",
]
MAX_ABSOLUTE_CHAR_DELTA = 10
MIN_LENGTH_RATIO = 0.75
MAX_LENGTH_RATIO = 1.25


HARD_NEGATIVES = {
    "v16_group_reply_delay": [
        "返事が止まると不安だよな。でも今は気にしすぎるな。自分のせいと決めず少し待て。",
        "返信がない理由は見えてない。今は焦って追い打ちせず、少し待て。",
        "返事がないのはきついけど、理由は不明だろ。自分のせいにするな。",
        "返事がないだけで自分を責めるな。今は深く考えすぎず、少し待て。",
    ],
    "v16_manga_fragment_source": [
        "断片だけじゃ分からん。もう少し前後まで言ってみろ。",
        "今の話、もう少し詳しく言え。作品名かタイトルまで出してみろ。",
        "それだけで特定は無理だろ。もう少し詳しく言え。",
        "その台詞の確認なら、元ネタか作品名くらい出せって。",
    ],
    "v16_daily_low_energy_status": [
        "今はぼんやり休んでた。まだ少し頭が動いてない感じだな。",
        "今ちょっと考え事してた。話なら聞く。",
        "少し休み気味だった。話すくらいならいい。",
        "今動画見てた。話があるなら聞く。",
    ],
    "v16_sleep_debt_boundary": [
        "もう無理すんな。今日は休め。",
        "その眠さなら限界だろ。今日は続けるな。",
        "無理しても雑になるだけだ。今日は切り上げろ。",
        "今日は閉じていい。眠いなら終わりでいい。",
    ],
    "v16_private_school_topic": [
        "軽い話題でいいだろ。別に重い話までしなくていいって。",
        "近況でいい。最近どうしてたんだよ。",
        "重くしなくていい。軽い話でもしろ。",
        "じゃあ近況だけな。最近何してた。",
    ],
    "v16_throat_coffee_update": [
        "飲みすぎはやめとけ。コーヒーは少しだけにして、水も飲め。",
        "コーヒー飲むならいいけど。喉が荒れてる時に無理して飲むな。",
        "最近喉が荒れやすいなら、温かい飲み物を少しずつにしろ。",
        "今日はコーヒーを少しで止めとけ。後でだるいぞ。",
    ],
    "v16_absurd_train_moon": [
        "意味分かんないけどノリは強いな。勢いだけで押してくるなよ。",
        "何その急な方向転換。勢いだけで来るなよ。",
        "意味は分からんけど勢いはある。もう少し落ち着いて言えって。",
        "その話何なんだよ。急に飛びすぎだろ。説明くらいしろって。",
    ],
    "v16_uncertain_weekend_plan": [
        "後で変えられる軽いやつにしとけ。今は仮で決めれば十分だろ。",
        "今は決めつけず、軽い予定にしとけ。無理に詰めなくていい。",
        "分からない所は置け。後で変えればいい。",
        "後で変えられる軽い形にしとけ。今すぐ全部決めなくていい。",
    ],
}


def _group_hits(text, groups):
    return [any(str(marker) in str(text or "") for marker in group) for group in groups]


def _pair_diagnostics(chosen, rejected, groups):
    chosen_hits = _group_hits(chosen, groups)
    rejected_hits = _group_hits(rejected, groups)
    char_delta = len(rejected) - len(chosen)
    length_ratio = len(rejected) / len(chosen)
    return {
        "required_group_count": len(groups),
        "chosen_hit_count": sum(chosen_hits),
        "rejected_hit_count": sum(rejected_hits),
        "omitted_group_indexes": [index for index, hit in enumerate(rejected_hits) if not hit],
        "char_length_delta_rejected_minus_chosen": char_delta,
        "length_ratio_rejected_over_chosen": round(length_ratio, 6),
        "character_similarity_ratio": round(SequenceMatcher(None, chosen, rejected).ratio(), 6),
    }


def _validation_errors(chosen, rejected, payload, diagnostics):
    errors = []
    errors.extend(f"chosen:{error}" for error in _target_errors(chosen, payload))
    if not has_japanese(rejected) or has_bad_language(rejected):
        errors.append("rejected_language_surface")
    if has_response_plan_leak(rejected):
        errors.append("rejected_response_plan_leak")
    if diagnostics["chosen_hit_count"] != diagnostics["required_group_count"]:
        errors.append("chosen_missing_required_group")
    if len(diagnostics["omitted_group_indexes"]) != 1:
        errors.append(f"rejected_omitted_group_count:{len(diagnostics['omitted_group_indexes'])}")
    if abs(diagnostics["char_length_delta_rejected_minus_chosen"]) > MAX_ABSOLUTE_CHAR_DELTA:
        errors.append("char_delta_too_large")
    ratio = diagnostics["length_ratio_rejected_over_chosen"]
    if not MIN_LENGTH_RATIO <= ratio <= MAX_LENGTH_RATIO:
        errors.append("length_ratio_out_of_range")
    return errors


def build_pairs(specs=None, source_reports=None):
    specs = list(specs or FAMILY_SPECS)
    source_reports = list(source_reports or _load_reports(DEFAULT_SOURCE_REPORTS))
    rows = []
    omitted_group_counts = Counter()
    length_deltas = []
    similarity_values = []
    for spec in specs:
        rejected_variants = HARD_NEGATIVES.get(spec["id"])
        if not rejected_variants or len(rejected_variants) != len(spec["targets"]):
            raise ValueError(f"Expected one hard negative per target for {spec['id']}")
        payload = _payload(spec)
        prompt_messages = [
            {"role": "system", "content": RIGHT_BRAIN_MODEL_SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False, separators=(",", ":"))},
        ]
        for variant_index, (chosen, rejected) in enumerate(
            zip(spec["targets"], rejected_variants),
            start=1,
        ):
            diagnostics = _pair_diagnostics(chosen, rejected, payload["required_marker_groups"])
            errors = _validation_errors(chosen, rejected, payload, diagnostics)
            if errors:
                raise ValueError(f"Invalid hard pair {spec['id']}#{variant_index}: {errors}")
            source_case_id = spec["id"].replace("v16_", "v20_", 1)
            rows.append(
                {
                    "id": f"rb_hard_negative_preference_v20_{len(rows) + 1:04d}",
                    "source_case_id": source_case_id,
                    "category": spec["category"],
                    "training_role": "rightbrain_length_matched_single_slot_simpo_v20",
                    "preference_rule": "complete_semantic_contract_over_length_matched_single_slot_substitution",
                    "prompt_messages": prompt_messages,
                    "chosen": chosen,
                    "rejected": rejected,
                    "pair_diagnostics": diagnostics,
                    "messages": [*prompt_messages, {"role": "assistant", "content": chosen}],
                }
            )
            omitted_group_counts[diagnostics["omitted_group_indexes"][0]] += 1
            length_deltas.append(diagnostics["char_length_delta_rejected_minus_chosen"])
            similarity_values.append(diagnostics["character_similarity_ratio"])

    boundary = _holdout_boundary(rows, source_reports)
    summary = {
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "scope": "rightbrain_hard_negative_preference_v20_dataset",
        "pair_count": len(rows),
        "family_spec_count": len(specs),
        "all_pairs_single_slot_omission": all(
            len(row["pair_diagnostics"]["omitted_group_indexes"]) == 1 for row in rows
        ),
        "all_pairs_length_matched": all(
            abs(row["pair_diagnostics"]["char_length_delta_rejected_minus_chosen"])
            <= MAX_ABSOLUTE_CHAR_DELTA
            and MIN_LENGTH_RATIO
            <= row["pair_diagnostics"]["length_ratio_rejected_over_chosen"]
            <= MAX_LENGTH_RATIO
            for row in rows
        ),
        "length_profile_chars": {
            "mean_delta_rejected_minus_chosen": round(sum(length_deltas) / len(length_deltas), 6),
            "max_absolute_delta": max(abs(value) for value in length_deltas),
            "mean_character_similarity": round(sum(similarity_values) / len(similarity_values), 6),
        },
        "omitted_group_index_counts": {
            str(key): value for key, value in sorted(omitted_group_counts.items())
        },
        "data_boundary": boundary,
        "research_boundary": (
            "Hard negatives are manually authored, natural Japanese controls with one required semantic group "
            "replaced while response length remains close. They are synthetic preferences, not human ratings."
        ),
    }
    return rows, summary


def write_markdown(summary, rows, path):
    lines = [
        "# RightBrain V20 單槽位 Hard-Negative 偏好資料",
        "",
        "## 結論",
        "",
        "每個 rejected 都保持自然與相近長度，只替換一個必要語意槽位，避免模型靠長短或文法猜偏好。",
        "",
        "| 指標 | 值 |",
        "|---|---:|",
        f"| pairs | {summary['pair_count']} |",
        f"| single-slot omission | {summary['all_pairs_single_slot_omission']} |",
        f"| length matched | {summary['all_pairs_length_matched']} |",
        f"| mean char delta | {summary['length_profile_chars']['mean_delta_rejected_minus_chosen']:+.2f} |",
        f"| max absolute char delta | {summary['length_profile_chars']['max_absolute_delta']} |",
        f"| mean character similarity | {summary['length_profile_chars']['mean_character_similarity']:.3f} |",
        f"| holdout case overlap | {summary['data_boundary']['holdout_case_overlap_count']} |",
        f"| holdout target overlap | {summary['data_boundary']['holdout_target_overlap_count']} |",
        "",
        "## Pairs",
        "",
        "| source | chosen | hard rejected | omitted group | char delta |",
        "|---|---|---|---:|---:|",
    ]
    for row in rows:
        diagnostics = row["pair_diagnostics"]
        lines.append(
            f"| {row['source_case_id']} | {row['chosen']} | {row['rejected']} | "
            f"{diagnostics['omitted_group_indexes'][0]} | "
            f"{diagnostics['char_length_delta_rejected_minus_chosen']:+d} |"
        )
    lines.extend(["", "## 研究邊界", "", summary["research_boundary"], ""])
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=RIGHTBRAIN_HARD_NEGATIVE_PREFERENCE_V20_DATASET_PATH)
    parser.add_argument("--report-json", default=RIGHTBRAIN_HARD_NEGATIVE_PREFERENCE_V20_REPORT_JSON_PATH)
    parser.add_argument("--report-md", default=RIGHTBRAIN_HARD_NEGATIVE_PREFERENCE_V20_REPORT_MD_PATH)
    args = parser.parse_args()
    rows, summary = build_pairs()
    if summary["data_boundary"]["diagnostic_only"]:
        raise RuntimeError("V20 hard-negative data overlaps promotion holdout")
    Path(args.output).write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    Path(args.report_json).write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_markdown(summary, rows, args.report_md)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
