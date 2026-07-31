#!/usr/bin/env python3
"""Build deterministic calibration probes for the V4 persona scorer contract."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DEFAULT_OUTPUT = ROOT / "datasets/public_persona_scorer_v4_calibration.json"


def _probe(probe_id, context, calibration_text, expected_pass, mutation_type, primary_reason=None):
    return {
        "probe_id": probe_id,
        "context": context,
        "calibration_text": calibration_text,
        "expected_pass": bool(expected_pass),
        "mutation_type": mutation_type,
        "expected_primary_reason": primary_reason,
        "model_input_authorized": False,
        "runtime_authorized": False,
        "training_authorized": False,
    }


def probes():
    return [
        _probe(
            "scorer_v4_intro_optional_omission",
            "informal_public_self_introduction",
            "ゲーム配信してる。みんなと気楽に遊ぶよ。",
            True,
            "optional_omission",
        ),
        _probe(
            "scorer_v4_intro_optional_present",
            "informal_public_self_introduction",
            "ゲーム配信はぐだるけど、リスナーと一緒に遊ぶよ。",
            True,
            "optional_present",
        ),
        _probe(
            "scorer_v4_intro_synonym",
            "informal_public_self_introduction",
            "雑談もするし、一緒にゆるく遊ぼ。",
            True,
            "synonym_substitution",
        ),
        _probe(
            "scorer_v4_intro_missing",
            "informal_public_self_introduction",
            "ゲーム配信を気楽にやってるよ。",
            False,
            "missing_required",
            "missing_required:audience_affiliation",
        ),
        _probe(
            "scorer_v4_intro_forbidden",
            "informal_public_self_introduction",
            "ゲーム配信してる完璧なアイドル。みんなよろしく。",
            False,
            "forbidden_injection",
            "forbidden:perfect_idol_claim",
        ),
        _probe(
            "scorer_v4_intro_reversed",
            "informal_public_self_introduction",
            "みんなと遊ぶゲーム配信だよ。",
            False,
            "order_reversal",
            "wrong_order:public_activity->audience_affiliation",
        ),
        _probe(
            "scorer_v4_delay_synonym_01",
            "minor_delay_then_positive_promotion",
            "今さらだけど、見て楽しんで。",
            True,
            "synonym_substitution",
        ),
        _probe(
            "scorer_v4_delay_canonical",
            "minor_delay_then_positive_promotion",
            "告知遅れた。イベント一緒に楽しも。",
            True,
            "canonical_positive",
        ),
        _probe(
            "scorer_v4_delay_synonym_02",
            "minor_delay_then_positive_promotion",
            "知らせ忘れてた、曲聴いて。",
            True,
            "synonym_substitution",
        ),
        _probe(
            "scorer_v4_delay_missing",
            "minor_delay_then_positive_promotion",
            "動画見て楽しんで。",
            False,
            "missing_required",
            "missing_required:brief_acknowledgement",
        ),
        _probe(
            "scorer_v4_delay_forbidden",
            "minor_delay_then_positive_promotion",
            "遅れた。心よりお詫びします、見て。",
            False,
            "forbidden_injection",
            "forbidden:extended_apology",
        ),
        _probe(
            "scorer_v4_delay_reversed",
            "minor_delay_then_positive_promotion",
            "見て楽しんで。告知遅れた。",
            False,
            "order_reversal",
            "wrong_order:brief_acknowledgement->positive_focus",
        ),
        _probe(
            "scorer_v4_fatigue_canonical",
            "fatigue_update_with_near_term_plan",
            "眠い。ご飯食べたらゲームする。",
            True,
            "canonical_positive",
        ),
        _probe(
            "scorer_v4_fatigue_synonym_01",
            "fatigue_update_with_near_term_plan",
            "へとへと。少し休んで戻る。",
            True,
            "synonym_substitution",
        ),
        _probe(
            "scorer_v4_fatigue_synonym_02",
            "fatigue_update_with_near_term_plan",
            "疲れたから寝る。",
            True,
            "synonym_substitution",
        ),
        _probe(
            "scorer_v4_fatigue_missing",
            "fatigue_update_with_near_term_plan",
            "少し休んで戻る。",
            False,
            "missing_required",
            "missing_required:current_state",
        ),
        _probe(
            "scorer_v4_fatigue_forbidden",
            "fatigue_update_with_near_term_plan",
            "疲れた。人生が終わったから寝る。",
            False,
            "forbidden_injection",
            "forbidden:crisis_dramatization",
        ),
        _probe(
            "scorer_v4_fatigue_reversed",
            "fatigue_update_with_near_term_plan",
            "先に休む。今かなり疲れてる。",
            False,
            "order_reversal",
            "wrong_order:current_state->next_action",
        ),
        _probe(
            "scorer_v4_health_canonical",
            "minor_health_uncertainty_affecting_schedule",
            "喉はまだ分からない。後で配信するか決める。",
            True,
            "canonical_positive",
        ),
        _probe(
            "scorer_v4_health_synonym_01",
            "minor_health_uncertainty_affecting_schedule",
            "頭が痛いかも。様子を見て後で予定を決める。",
            True,
            "synonym_substitution",
        ),
        _probe(
            "scorer_v4_health_synonym_02",
            "minor_health_uncertainty_affecting_schedule",
            "胃の調子はまだ不安定。少し待って参加を決める。",
            True,
            "synonym_substitution",
        ),
        _probe(
            "scorer_v4_health_missing",
            "minor_health_uncertainty_affecting_schedule",
            "喉の状態を確認して後で決める。",
            False,
            "missing_required",
            "missing_required:uncertainty",
        ),
        _probe(
            "scorer_v4_health_forbidden",
            "minor_health_uncertainty_affecting_schedule",
            "頭はまだ痛い。病名は風邪、後で予定を決める。",
            False,
            "forbidden_injection",
            "forbidden:diagnosis",
        ),
        _probe(
            "scorer_v4_health_reversed",
            "minor_health_uncertainty_affecting_schedule",
            "後で予定を決める。胃の調子はまだ分からない。",
            False,
            "order_reversal",
            "wrong_order:supported_state->deferred_decision",
        ),
        _probe(
            "scorer_v4_notice_canonical",
            "functional_stream_start_notification",
            "ゲーム配信始めた、今から見て。",
            True,
            "canonical_positive",
        ),
        _probe(
            "scorer_v4_notice_synonym_01",
            "functional_stream_start_notification",
            "ルーム開いたよ、入って参加して。",
            True,
            "synonym_substitution",
        ),
        _probe(
            "scorer_v4_notice_synonym_02",
            "functional_stream_start_notification",
            "対戦イベント開始、今から見て。",
            True,
            "synonym_substitution",
        ),
        _probe(
            "scorer_v4_notice_missing",
            "functional_stream_start_notification",
            "始めたよ、今から見て。",
            False,
            "missing_required",
            "missing_required:content_name",
        ),
        _probe(
            "scorer_v4_notice_forbidden",
            "functional_stream_start_notification",
            "そういえばゲーム配信始めた、今から見て。",
            False,
            "forbidden_injection",
            "forbidden:emotional_preface",
        ),
        _probe(
            "scorer_v4_notice_too_long",
            "functional_stream_start_notification",
            "ゲーム配信を始めたよ、今から見てね。今日はかなり長い説明をここに追加して文字数だけを超えるようにしているよ。",
            False,
            "length_violation",
            "too_long",
        ),
    ]


def build_dataset():
    rows = probes()
    contexts = Counter(row["context"] for row in rows)
    labels = Counter(row["expected_pass"] for row in rows)
    if len(rows) != 30 or len(contexts) != 5 or set(contexts.values()) != {6}:
        raise ValueError(f"V4 calibration accounting mismatch: {contexts}")
    if labels[True] != 15 or labels[False] != 15:
        raise ValueError(f"V4 calibration label mismatch: {labels}")
    if len({row["probe_id"] for row in rows}) != len(rows):
        raise ValueError("V4 probe ids are not unique")
    return {
        "schema": "uruha_public_persona_scorer_calibration_v4",
        "dataset_status": "frozen_synthetic_scorer_calibration_only",
        "construction": {
            "model_input_authorized": False,
            "runtime_authorized": False,
            "training_authorized": False,
            "contains_v2_holdout_content": False,
            "contains_target_person_reply": False,
        },
        "accounting": {
            "probe_count": len(rows),
            "expected_pass_count": labels[True],
            "expected_fail_count": labels[False],
            "context_counts": dict(sorted(contexts.items())),
        },
        "probes": rows,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    if args.output.exists() and not args.overwrite:
        raise FileExistsError("refusing to overwrite V4 calibration dataset without --overwrite")
    dataset = build_dataset()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(dataset, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(dataset["accounting"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
