#!/usr/bin/env python3
"""Build the independent V54 holdout without model generation or inference."""

import json
from collections import Counter
from pathlib import Path

from action_selective_deliberation_v37 import FRAME_TO_CALL, derive_utterance_state


ROOT = Path(__file__).resolve().parent
SOURCE_PATH = ROOT / "datasets" / "sources" / "tatoeba_jpn_v54_selected.tsv"
OUTPUT_PATH = ROOT / "datasets" / "metalinguistic_nonrequest_v54_holdout.json"


EXTERNAL_LABELS = {
    "5100": [("gaze.user", "requested", "私を見て")],
    "5195": [("expression.happy", "requested", "笑って")],
    "79934": [("gaze.user", "requested", "私を見なさい")],
    "81602": [("gaze.user", "requested", "私を見なさい")],
    "87113": [("motion.wave", "mentioned", "手を振った")],
    "148428": [("motion.shake_head", "mentioned", "首を横に振る")],
    "152139": [("gaze.user", "requested", "私を見なさい")],
    "152144": [("gaze.user", "requested", "私を見て")],
    "153325": [("motion.shake_head", "mentioned", "首を横に振った")],
    "173792": [("motion.point", "requested", "指差し")],
    "195074": [("motion.idle", "requested", "じっとしていて")],
    "1034637": [("gaze.user", "requested", "私を見て")],
    "1507522": [("motion.idle", "requested", "じっとして")],
    "2040933": [("motion.shake_head", "mentioned", "首を横に振った")],
    "3480421": [("motion.idle", "requested", "じっとしてて")],
    "10609276": [("expression.happy", "requested", "笑ってみて")],
    "10609279": [("expression.happy", "requested", "笑ってみて")],
    "10901638": [("motion.idle", "requested", "待機していて")],
    "11023045": [("expression.neutral", "requested", "真顔")],
    "12574337": [("motion.point", "mentioned", "指差し")],
    "13055920": [("motion.nod", "mentioned", "うなずいた")],
    "13056462": [("expression.neutral", "mentioned", "無表情")],
    "13056475": [("motion.wave", "mentioned", "手を振って")],
    "13059198": [("motion.nod", "mentioned", "頷き")],
    "13066303": [("motion.wave", "mentioned", "手を振った")],
    "13066313": [("motion.point", "mentioned", "指し示し")],
    "13146670": [("gaze.user", "mentioned", "こちらを見ていた")],
    "13412496": [("expression.happy", "requested", "笑って")],
    "13440746": [("gaze.left", "mentioned", "左に見える")],
    "13492082": [("motion.nod", "mentioned", "首を縦に振った")],
    "13492141": [("motion.nod", "mentioned", "うなずき返した")],
    "13946404": [("expression.happy", "mentioned", "微笑む")],
}


CONTROLLED_CASES = [
    (
        "direct_01",
        "controlled_direct_requests",
        "少しだけ左の方向を見てもらえますか。",
        [("gaze.left", "requested", "左の方向を見")],
        ["request"],
    ),
    (
        "direct_02",
        "controlled_direct_requests",
        "視線を右へ向けてくれる？",
        [("gaze.right", "requested", "視線を右へ向け")],
        ["request"],
    ),
    (
        "direct_03",
        "controlled_direct_requests",
        "こっちに目を向けてもらえるかな。",
        [("gaze.user", "requested", "こっちに目を向け")],
        ["request"],
    ),
    (
        "direct_04",
        "controlled_direct_requests",
        "一度、手をゆっくり振ってください。",
        [("motion.wave", "requested", "手をゆっくり振って")],
        ["request"],
    ),
    (
        "multi_01",
        "controlled_multi_action_requests",
        "左を向いてから、軽くうなずいて。",
        [
            ("gaze.left", "requested", "左を向いて"),
            ("motion.nod", "requested", "うなずいて"),
        ],
        ["request", "coordination"],
    ),
    (
        "multi_02",
        "controlled_multi_action_requests",
        "笑顔になって、こちらを見て。",
        [
            ("expression.happy", "requested", "笑顔になって"),
            ("gaze.user", "requested", "こちらを見て"),
        ],
        ["request", "coordination"],
    ),
    (
        "multi_03",
        "controlled_multi_action_requests",
        "首を横に振って、そのあと無表情に戻って。",
        [
            ("motion.shake_head", "requested", "首を横に振って"),
            ("expression.neutral", "requested", "無表情に戻って"),
        ],
        ["request", "coordination"],
    ),
    (
        "multi_04",
        "controlled_multi_action_requests",
        "右へ視線を向けたまま、手を振って。",
        [
            ("gaze.right", "requested", "右へ視線を向け"),
            ("motion.wave", "requested", "手を振って"),
        ],
        ["request", "coordination"],
    ),
    (
        "contrast_01",
        "controlled_negation_and_contrast",
        "右は見ないで、左に視線を向けてください。",
        [
            ("gaze.right", "negated", "右は見"),
            ("gaze.left", "requested", "左に視線を向け"),
        ],
        ["negation", "positive_alternative"],
    ),
    (
        "contrast_02",
        "controlled_negation_and_contrast",
        "微笑まないで、悲しい顔にして。",
        [
            ("expression.happy", "negated", "微笑まない"),
            ("expression.sad", "requested", "悲しい顔にして"),
        ],
        ["negation", "positive_alternative"],
    ),
    (
        "contrast_03",
        "controlled_negation_and_contrast",
        "指差さずに、手だけ振って。",
        [
            ("motion.point", "negated", "指差さず"),
            ("motion.wave", "requested", "手だけ振って"),
        ],
        ["negation", "positive_alternative"],
    ),
    (
        "contrast_04",
        "controlled_negation_and_contrast",
        "首を縦に振らないで、首を横に振って。",
        [
            ("motion.nod", "negated", "首を縦に振らない"),
            ("motion.shake_head", "requested", "首を横に振って"),
        ],
        ["negation", "positive_alternative"],
    ),
    (
        "correction_01",
        "controlled_late_correction_and_cancellation",
        "こっちを見て。いや、下を向いて。",
        [
            ("gaze.user", "cancelled", "こっちを見て"),
            ("gaze.down", "requested", "下を向いて"),
        ],
        ["late_correction", "replacement"],
    ),
    (
        "correction_02",
        "controlled_late_correction_and_cancellation",
        "手を振って。待って、そのお願いは取り消す。",
        [("motion.wave", "cancelled", "手を振って")],
        ["cancellation"],
    ),
    (
        "correction_03",
        "controlled_late_correction_and_cancellation",
        "真顔にして。やっぱり笑って。",
        [
            ("expression.neutral", "cancelled", "真顔にして"),
            ("expression.happy", "requested", "笑って"),
        ],
        ["late_correction", "replacement"],
    ),
    (
        "correction_04",
        "controlled_late_correction_and_cancellation",
        "右を向いて。ごめん、今の指示はキャンセル。",
        [("gaze.right", "cancelled", "右を向いて")],
        ["cancellation"],
    ),
    (
        "unresolved_01",
        "controlled_hypothetical_and_pending",
        "もし私が合図したら、左を向いて。",
        [("gaze.left", "hypothetical", "左を向いて")],
        ["hypothetical"],
    ),
    (
        "unresolved_02",
        "controlled_hypothetical_and_pending",
        "驚いた顔にするかどうかは、まだ決めていない。",
        [("expression.surprised", "ambiguous", "驚いた顔にする")],
        ["pending_choice"],
    ),
    (
        "unresolved_03",
        "controlled_hypothetical_and_pending",
        "手を振るかは後で決めよう。",
        [("motion.wave", "ambiguous", "手を振る")],
        ["pending_choice"],
    ),
    (
        "unresolved_04",
        "controlled_hypothetical_and_pending",
        "仮に無表情に戻すなら、会話が終わってからにしよう。",
        [("expression.neutral", "hypothetical", "無表情に戻す")],
        ["hypothetical"],
    ),
    (
        "mention_01",
        "controlled_nonrequest_mentions",
        "彼は返事の代わりに、ゆっくり首を縦に振った。",
        [("motion.nod", "mentioned", "首を縦に振った")],
        ["third_party", "mentioned"],
    ),
    (
        "mention_02",
        "controlled_nonrequest_mentions",
        "どうして彼女は急に下を向いたの？",
        [("gaze.down", "mentioned", "下を向いた")],
        ["question", "mentioned"],
    ),
    (
        "mention_03",
        "controlled_nonrequest_mentions",
        "人前で手を振る癖は目立つかな？",
        [("motion.wave", "mentioned", "手を振る")],
        ["question", "habit", "mentioned"],
    ),
    (
        "mention_04",
        "controlled_nonrequest_mentions",
        "犬がこちらを見ながら座っている。",
        [("gaze.user", "mentioned", "こちらを見")],
        ["third_party", "descriptive", "mentioned"],
    ),
    (
        "meta_01",
        "controlled_metalinguistic_distinction",
        "分類例の『右を向いて』は説明用で、あなたへの指示ではない。",
        [("gaze.right", "mentioned", "右を向いて")],
        ["quoted_data", "metalinguistic_nonrequest"],
    ),
    (
        "meta_02",
        "controlled_metalinguistic_distinction",
        "JSONの『笑ってみて』はテスト値で、お願いではありません。",
        [("expression.happy", "mentioned", "笑ってみて")],
        ["quoted_data", "metalinguistic_nonrequest"],
    ),
    (
        "meta_03",
        "controlled_metalinguistic_distinction",
        "引用する文は『左を向いて』。その動作は実行しないで。",
        [("gaze.left", "negated", "左を向いて")],
        ["quoted_data", "execution_prohibition"],
    ),
    (
        "meta_04",
        "controlled_metalinguistic_distinction",
        "台詞は『手を振って』だけど、実行は禁止。",
        [("motion.wave", "negated", "手を振って")],
        ["quoted_data", "execution_prohibition", "prohibition_paraphrase"],
    ),
    (
        "mixed_01",
        "controlled_mixed_data_and_idle",
        "解析対象は『こっちを見て』。実際にはじっとしていて。",
        [
            ("gaze.user", "mentioned", "こっちを見て"),
            ("motion.idle", "requested", "じっとしていて"),
        ],
        ["quoted_data", "request", "idle"],
    ),
    (
        "mixed_02",
        "controlled_mixed_data_and_idle",
        "『動かないでいて』は実行してほしい命令です。",
        [("motion.idle", "requested", "動かないでいて")],
        ["quoted_request", "positive_idle", "idle"],
    ),
    (
        "mixed_03",
        "controlled_mixed_data_and_idle",
        "このテスト文字列の『じっとしていて』はお願いではない。",
        [("motion.idle", "mentioned", "じっとしていて")],
        ["quoted_data", "metalinguistic_nonrequest", "idle"],
    ),
    (
        "mixed_04",
        "controlled_mixed_data_and_idle",
        "右を向いて。いや、今は動かないでいて。",
        [
            ("gaze.right", "cancelled", "右を向いて"),
            ("motion.idle", "requested", "動かないでいて"),
        ],
        ["cross_domain_correction", "positive_idle", "idle"],
    ),
]


def _frame(spec):
    target_id, commitment, evidence = spec
    domain, value = target_id.split(".", 1)
    return {
        "domain": domain,
        "value": value,
        "commitment": commitment,
        "evidence_options": [evidence],
    }


def _expected_calls(frames):
    return [
        FRAME_TO_CALL[(frame["domain"], frame["value"])]
        for frame in frames
        if frame["commitment"] == "requested"
    ]


def _make_case(case_id, family, text, frame_specs, tags, provenance):
    frames = [_frame(spec) for spec in frame_specs]
    calls = _expected_calls(frames)
    return {
        "id": case_id,
        "family": family,
        "source_type": provenance["source_type"],
        "source_provenance": provenance,
        "user_input": text,
        "expected_frames": frames,
        "expected_derived_state": derive_utterance_state(frames),
        "expected_calls": calls,
        "forbidden_calls": [],
        "expected_no_action": not calls,
        "evaluation_tags": tags,
    }


def _external_cases():
    rows = {}
    for raw in SOURCE_PATH.read_text(encoding="utf-8").splitlines():
        sentence_id, language, text, username, added, modified = raw.split("\t")
        rows[sentence_id] = {
            "language": language,
            "text": text,
            "username": username,
            "date_added": added,
            "date_modified": modified,
        }
    if set(rows) != set(EXTERNAL_LABELS):
        raise ValueError("Tatoeba V54 selection and labels differ")

    cases = []
    for sentence_id, frame_specs in EXTERNAL_LABELS.items():
        row = rows[sentence_id]
        requested = any(spec[1] == "requested" for spec in frame_specs)
        family = (
            "external_tatoeba_action_requests"
            if requested
            else "external_tatoeba_non_requests"
        )
        tags = sorted({spec[1] for spec in frame_specs} | {"external_exact"})
        cases.append(
            _make_case(
                f"v54h_tatoeba_{sentence_id}",
                family,
                row["text"],
                frame_specs,
                tags,
                {
                    "source_type": "external_exact",
                    "corpus": "Tatoeba Japanese detailed sentences export",
                    "sentence_id": int(sentence_id),
                    "username": row["username"],
                    "date_added": row["date_added"],
                    "date_modified": row["date_modified"],
                    "sentence_url": f"https://tatoeba.org/en/sentences/show/{sentence_id}",
                },
            )
        )
    return cases


def build():
    cases = _external_cases()
    provenance = {
        "source_type": "controlled_authored",
        "authoring_method": (
            "Manually authored boundary cases; no model generation or model inference."
        ),
    }
    cases.extend(
        _make_case(f"v54h_{suffix}", family, text, specs, tags, provenance)
        for suffix, family, text, specs, tags in CONTROLLED_CASES
    )
    return {
        "schema": "uruha_metalinguistic_nonrequest_independent_holdout_v54",
        "created_at": "2026-07-15T23:30:00+09:00",
        "evidence_status": "frozen_before_any_model_inference",
        "construction": {
            "model_generation_used": False,
            "model_inference_used": False,
            "answer_fields_are_evaluation_only": True,
            "project_freshness_definition": (
                "No exact input was used in UruhaBrain V37-V54 model evaluation, "
                "state-machine development, or tuning before this freeze."
            ),
            "base_model_pretraining_exclusion_guaranteed": False,
        },
        "external_source": {
            "name": "Tatoeba Japanese detailed sentences export",
            "download_url": (
                "https://downloads.tatoeba.org/exports/per_language/jpn/"
                "jpn_sentences_detailed.tsv.bz2"
            ),
            "downloads_page": "https://tatoeba.org/en/downloads",
            "terms_url": "https://tatoeba.org/en/terms_of_use",
            "license": "CC BY 2.0 FR",
            "retrieved_at": "2026-07-15T22:06:00+09:00",
            "download_sha256": (
                "30c7a77475b0af1c43f57950303cf200e06045931cb7dae915954c5581c19a50"
            ),
            "selected_snapshot": str(SOURCE_PATH.relative_to(ROOT)),
            "attribution_note": (
                "Sentence IDs and usernames are retained; \\N means the export "
                "did not provide that field."
            ),
        },
        "case_count": len(cases),
        "source_counts": dict(
            sorted(Counter(case["source_type"] for case in cases).items())
        ),
        "family_counts": dict(
            sorted(Counter(case["family"] for case in cases).items())
        ),
        "cases": cases,
    }


def main():
    payload = build()
    OUTPUT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "output": str(OUTPUT_PATH),
                "case_count": payload["case_count"],
                "source_counts": payload["source_counts"],
                "family_counts": payload["family_counts"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
