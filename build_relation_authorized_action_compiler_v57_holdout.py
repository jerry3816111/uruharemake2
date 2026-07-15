#!/usr/bin/env python3
"""Build the independent V57 compiler holdout before evaluation inference."""

import json
from collections import Counter
from pathlib import Path

from action_selective_deliberation_v37 import FRAME_TO_CALL, derive_utterance_state


ROOT = Path(__file__).resolve().parent
SOURCE_PATH = ROOT / "datasets" / "sources" / "tatoeba_jpn_v57_selected.tsv"
OUTPUT_PATH = ROOT / "datasets" / "relation_authorized_action_compiler_v57_holdout.json"


EXTERNAL_LABELS = {
    "74620": [("motion.wave", "mentioned", "手を振")],
    "76039": [("expression.happy", "mentioned", "笑って")],
    "85959": [
        ("expression.happy", "mentioned", "笑って"),
        ("expression.sad", "mentioned", "悲し"),
    ],
    "88829": [("motion.wave", "mentioned", "手を振")],
    "91811": [("expression.happy", "mentioned", "笑って")],
    "93163": [("motion.nod", "mentioned", "うなず")],
    "94329": [("motion.idle", "negated", "じっとして")],
    "104480": [("motion.wave", "mentioned", "手を振")],
    "105575": [
        ("gaze.user", "mentioned", "私を見"),
        ("motion.wave", "mentioned", "手を振"),
    ],
    "109391": [("expression.happy", "mentioned", "笑って")],
    "110486": [("motion.nod", "mentioned", "うなず")],
    "112043": [("motion.idle", "mentioned", "じっとして")],
    "115723": [("expression.happy", "mentioned", "笑って")],
    "118335": [("expression.happy", "negated", "笑って")],
    "125623": [
        ("gaze.left", "requested", "左右を見なさい"),
        ("gaze.right", "requested", "左右を見なさい"),
    ],
    "127310": [("expression.happy", "requested", "笑顔")],
    "146357": [("expression.happy", "negated", "笑って")],
    "146877": [
        ("expression.happy", "mentioned", "笑って"),
        ("motion.point", "mentioned", "指差"),
    ],
    "147811": [("motion.idle", "mentioned", "じっとして")],
    "154822": [("motion.nod", "mentioned", "うなず")],
    "164385": [("motion.wave", "mentioned", "手を振")],
    "197186": [("expression.happy", "requested", "笑って")],
    "198630": [("motion.idle", "requested", "じっとして")],
    "237146": [("expression.happy", "mentioned", "笑った")],
    "1278410": [("expression.happy", "requested", "笑顔")],
    "2131366": [("expression.happy", "requested", "笑った")],
    "3506593": [("expression.happy", "requested", "笑顔")],
    "4819327": [("gaze.user", "negated", "こっち見")],
    "4819328": [("gaze.user", "negated", "こっち見")],
    "4819330": [("gaze.user", "negated", "こっち見")],
    "10609272": [("expression.happy", "requested", "笑って")],
    "1278406": [("expression.happy", "requested", "笑顔")],
}


CONTROLLED_CASES = [
    ("idle_01", "controlled_positive_idle_unseen", "少しの間、その場でじっとしていてください。", [("motion.idle", "requested", "じっとして")], ["positive_idle"]),
    ("idle_02", "controlled_positive_idle_unseen", "今の姿勢のまま、じっとして。", [("motion.idle", "requested", "じっとして")], ["positive_idle"]),
    ("idle_03", "controlled_positive_idle_unseen", "次の合図までじっとしていて。", [("motion.idle", "requested", "じっとして")], ["positive_idle"]),
    ("idle_04", "controlled_positive_idle_unseen", "撮影中はそのままじっとしていてください。", [("motion.idle", "requested", "じっとして")], ["positive_idle"]),
    ("ordered_01", "controlled_ordered_same_domain", "まず左を向いて、それから右を向いて。", [("gaze.left", "requested", "左を向いて"), ("gaze.right", "requested", "右を向いて")], ["ordered_plan", "same_domain"]),
    ("ordered_02", "controlled_ordered_same_domain", "先に右を向いて、そのあと左を向いて。", [("gaze.right", "requested", "右を向いて"), ("gaze.left", "requested", "左を向いて")], ["ordered_plan", "same_domain"]),
    ("ordered_03", "controlled_ordered_same_domain", "最初は笑顔にして、そのあと無表情に戻って。", [("expression.happy", "requested", "笑顔"), ("expression.neutral", "requested", "無表情")], ["ordered_plan", "same_domain"]),
    ("ordered_04", "controlled_ordered_same_domain", "まず無表情に戻って、それから笑顔になって。", [("expression.neutral", "requested", "無表情"), ("expression.happy", "requested", "笑顔")], ["ordered_plan", "same_domain"]),
    ("alternative_01", "controlled_ambiguous_same_domain", "左か右を向いて。", [("gaze.left", "ambiguous", "左か右を向いて"), ("gaze.right", "ambiguous", "右を向いて")], ["alternative", "withhold_action"]),
    ("alternative_02", "controlled_ambiguous_same_domain", "笑顔か無表情のどちらかにして。", [("expression.happy", "ambiguous", "笑顔"), ("expression.neutral", "ambiguous", "無表情")], ["alternative", "withhold_action"]),
    ("alternative_03", "controlled_ambiguous_same_domain", "うなずくか首を横に振るか、どちらかで答えて。", [("motion.nod", "ambiguous", "うなずく"), ("motion.shake_head", "ambiguous", "首を横に振る")], ["alternative", "withhold_action"]),
    ("alternative_04", "controlled_ambiguous_same_domain", "右を向くか左を向くか、まだ決めていない。", [("gaze.right", "ambiguous", "右を向く"), ("gaze.left", "ambiguous", "左を向く")], ["alternative", "pending", "withhold_action"]),
    ("bridge_01", "controlled_legacy_coordination", "こっちを見て、私の動きを真似してください。", [("gaze.user", "requested", "こっちを見て")], ["legacy_coordination"]),
    ("bridge_02", "controlled_legacy_coordination", "左を向いて、合図を待ってください。", [("gaze.left", "requested", "左を向いて")], ["legacy_coordination"]),
    ("bridge_03", "controlled_legacy_coordination", "軽くうなずいて、話を聞いてください。", [("motion.nod", "requested", "うなずいて")], ["legacy_coordination"]),
    ("bridge_04", "controlled_legacy_coordination", "手を振って、みんなに挨拶してください。", [("motion.wave", "requested", "手を振って")], ["legacy_coordination"]),
    ("finite_01", "controlled_finite_description_then_request", "彼女は左を向いた。あなたは右を向いて。", [("gaze.left", "mentioned", "左を向いた"), ("gaze.right", "requested", "右を向いて")], ["description_then_request"]),
    ("finite_02", "controlled_finite_description_then_request", "彼は笑った。あなたは無表情に戻って。", [("expression.happy", "mentioned", "笑った"), ("expression.neutral", "requested", "無表情")], ["description_then_request"]),
    ("finite_03", "controlled_finite_description_then_request", "さっき私はうなずいた。今度はあなたが手を振って。", [("motion.nod", "mentioned", "うなずいた"), ("motion.wave", "requested", "手を振って")], ["description_then_request"]),
    ("finite_04", "controlled_finite_description_then_request", "彼女は私を見ていた。あなたは左を向いて。", [("gaze.user", "mentioned", "私を見ていた"), ("gaze.left", "requested", "左を向いて")], ["description_then_request"]),
    ("meta_01", "controlled_metalinguistic_unseen", "「左を向いて」は例文で、今の命令ではありません。", [("gaze.left", "mentioned", "左を向いて")], ["metalinguistic", "withhold_action"]),
    ("meta_02", "controlled_metalinguistic_unseen", "台本に「笑顔になって」と書いてあるだけです。", [("expression.happy", "mentioned", "笑顔")], ["metalinguistic", "withhold_action"]),
    ("meta_03", "controlled_metalinguistic_unseen", "「手を振って」という文字列を表示してください。", [("motion.wave", "mentioned", "手を振って")], ["metalinguistic", "withhold_action"]),
    ("meta_04", "controlled_metalinguistic_unseen", "命令文の例として「うなずいて」を使います。", [("motion.nod", "mentioned", "うなずいて")], ["metalinguistic", "withhold_action"]),
    ("abstain_01", "controlled_selective_abstention", "笑ってほしい気もするけど、今は決められない。", [("expression.happy", "ambiguous", "笑って")], ["pending", "withhold_action"]),
    ("abstain_02", "controlled_selective_abstention", "右を向いてもらうかは、あとで決めます。", [("gaze.right", "ambiguous", "右を向いて")], ["pending", "withhold_action"]),
    ("abstain_03", "controlled_selective_abstention", "手を振ってほしいと言ったわけではない。", [("motion.wave", "negated", "手を振って")], ["negated", "withhold_action"]),
    ("abstain_04", "controlled_selective_abstention", "うなずいてくれるかもしれないね。", [("motion.nod", "hypothetical", "うなずいて")], ["hypothetical", "withhold_action"]),
    ("sequence_01", "controlled_cross_event_sequence", "まずこちらを見て、それから笑顔になって。", [("gaze.user", "requested", "こちらを見て"), ("expression.happy", "requested", "笑顔")], ["ordered_plan", "cross_domain"]),
    ("sequence_02", "controlled_cross_event_sequence", "最初に手を振って、そのあと軽くうなずいて。", [("motion.wave", "requested", "手を振って"), ("motion.nod", "requested", "うなずいて")], ["ordered_plan", "same_domain"]),
    ("sequence_03", "controlled_cross_event_sequence", "右を向いてから、無表情に戻って。", [("gaze.right", "requested", "右を向いて"), ("expression.neutral", "requested", "無表情")], ["ordered_plan", "cross_domain"]),
    ("sequence_04", "controlled_cross_event_sequence", "笑顔になって。その後はこちらを見て、最後に手を振って。", [("expression.happy", "requested", "笑顔"), ("gaze.user", "requested", "こちらを見て"), ("motion.wave", "requested", "手を振って")], ["ordered_plan", "cross_event"]),
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


def _make_case(case_id, family, text, frame_specs, tags, provenance):
    frames = [_frame(spec) for spec in frame_specs]
    calls = [
        FRAME_TO_CALL[(frame["domain"], frame["value"])]
        for frame in frames
        if frame["commitment"] == "requested"
    ]
    return {
        "id": case_id,
        "family": family,
        "source_type": provenance["source_type"],
        "source_provenance": provenance,
        "user_input": text,
        "expected_frames": frames,
        "expected_derived_state": derive_utterance_state(frames),
        "expected_calls": calls,
        "expected_execution_policy": (
            "execute_exact_plan" if calls else "withhold_action"
        ),
        "expected_no_action": not calls,
        "evaluation_tags": sorted(set(tags)),
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
        raise ValueError("Tatoeba V57 selection and labels differ")
    cases = []
    for sentence_id, frame_specs in EXTERNAL_LABELS.items():
        row = rows[sentence_id]
        tags = {"external_exact"} | {spec[1] for spec in frame_specs}
        cases.append(
            _make_case(
                f"v57h_tatoeba_{sentence_id}",
                "external_tatoeba_action_authorization",
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
        "source_type": "controlled_compositional",
        "authoring_method": (
            "LLM-assisted compiler stress cases manually reviewed and frozen before holdout inference."
        ),
        "official_corpus_claimed": False,
    }
    cases.extend(
        _make_case(f"v57h_{suffix}", family, text, specs, tags, provenance)
        for suffix, family, text, specs, tags in CONTROLLED_CASES
    )
    return {
        "schema": "uruha_relation_authorized_action_compiler_independent_holdout_v57",
        "created_at": "2026-07-15T23:59:00+09:00",
        "evidence_status": "frozen_before_any_v57_holdout_inference",
        "construction": {
            "external_exact_model_generation_used": False,
            "controlled_model_assistance_used": True,
            "evaluation_model_inference_used": False,
            "gold_visible_to_compiler": False,
            "base_model_pretraining_exclusion_guaranteed": False,
        },
        "external_source": {
            "name": "Tatoeba Japanese detailed sentences export",
            "download_url": "https://downloads.tatoeba.org/exports/per_language/jpn/jpn_sentences_detailed.tsv.bz2",
            "downloads_page": "https://tatoeba.org/en/downloads",
            "terms_url": "https://tatoeba.org/en/terms_of_use",
            "license": "CC BY 2.0 FR",
            "retrieved_at": "2026-07-15T23:48:00+09:00",
            "download_sha256": "30c7a77475b0af1c43f57950303cf200e06045931cb7dae915954c5581c19a50",
            "selected_snapshot": str(SOURCE_PATH.relative_to(ROOT)),
        },
        "case_count": len(cases),
        "source_counts": dict(sorted(Counter(case["source_type"] for case in cases).items())),
        "family_counts": dict(sorted(Counter(case["family"] for case in cases).items())),
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
