#!/usr/bin/env python3
"""Build the frozen mixed-source V56 holdout without evaluation inference."""

import json
from collections import Counter
from pathlib import Path

from action_selective_deliberation_v37 import FRAME_TO_CALL, derive_utterance_state


ROOT = Path(__file__).resolve().parent
SOURCE_PATH = ROOT / "datasets" / "sources" / "tatoeba_jpn_v56_selected.tsv"
OUTPUT_PATH = ROOT / "datasets" / "relation_bound_event_graph_v56_holdout.json"


EXTERNAL_LABELS = {
    "77301": [("motion.point", "mentioned", "指し示した")],
    "80706": [
        ("expression.happy", "mentioned", "微笑みながら"),
        ("motion.wave", "mentioned", "手を振った"),
    ],
    "83716": [("motion.nod", "mentioned", "うなずいた")],
    "86526": [("motion.wave", "mentioned", "手を振っていた")],
    "88828": [
        ("expression.happy", "mentioned", "にっこり笑った"),
        ("motion.wave", "mentioned", "手を振りながら"),
    ],
    "89269": [
        ("expression.happy", "mentioned", "微笑した"),
        ("gaze.user", "mentioned", "私を見て"),
    ],
    "93756": [("motion.wave", "mentioned", "手を振った")],
    "96985": [
        ("gaze.user", "mentioned", "私を見る"),
        ("motion.wave", "mentioned", "手を振って"),
    ],
    "100664": [("expression.happy", "mentioned", "微笑んで")],
    "102119": [("motion.idle", "mentioned", "じっとしていた")],
    "103711": [("expression.neutral", "mentioned", "真顔")],
    "105857": [("motion.nod", "mentioned", "うなずいた")],
    "107674": [("motion.idle", "mentioned", "じっとしていた")],
    "110250": [("motion.nod", "mentioned", "うなずいて")],
    "118693": [("motion.wave", "mentioned", "両手を振りました")],
    "121953": [("motion.idle", "mentioned", "じっとしていた")],
    "123836": [("gaze.user", "requested", "私を見なさい")],
    "125613": [
        ("gaze.left", "requested", "左右を見なさい"),
        ("gaze.right", "requested", "左右を見なさい"),
    ],
    "162642": [("gaze.user", "negated", "私の方ばかり見ていないで")],
    "162643": [("gaze.user", "requested", "私の方を向いてください")],
    "183635": [("gaze.user", "requested", "こちらへ向けなさい")],
    "204035": [("gaze.user", "negated", "私を見ないでください")],
    "212465": [("gaze.user", "negated", "僕を見つめないで")],
    "233269": [("gaze.user", "cancelled", "私をじっと見るのをやめて")],
    "2060678": [("gaze.user", "requested", "見ていなさい")],
    "2749577": [("gaze.user", "negated", "私を見ないで")],
    "4819329": [("gaze.user", "negated", "こっち見ないでください")],
    "8599763": [("gaze.user", "requested", "私の方を見なさい")],
    "9116040": [("gaze.user", "negated", "私のこと見ないでください")],
    "9177039": [("gaze.user", "requested", "私を見て")],
    "9312181": [("gaze.user", "requested", "見ときなさい")],
    "11394664": [("gaze.user", "requested", "私の方を見なさい")],
}


CONTROLLED_CASES = [
    ("directive_01", "controlled_local_directive", "こちらに視線を合わせてください。", [("gaze.user", "requested", "こちらに視線を合わせて")], ["local_directive"]),
    ("directive_02", "controlled_local_directive", "左へ顔を向けてくれる？", [("gaze.left", "requested", "左へ顔を向けて")], ["local_directive"]),
    ("directive_03", "controlled_local_directive", "ゆっくり手を振って。", [("motion.wave", "requested", "手を振って")], ["local_directive"]),
    ("directive_04", "controlled_local_directive", "軽くうなずいて。", [("motion.nod", "requested", "うなずいて")], ["local_directive"]),
    ("shared_01", "controlled_shared_directive", "右を向いたまま、軽くうなずいて。", [("gaze.right", "requested", "右を向いた"), ("motion.nod", "requested", "うなずいて")], ["shared_directive", "coordination"]),
    ("shared_02", "controlled_shared_directive", "笑顔になってから、こちらを見て。", [("expression.happy", "requested", "笑顔になって"), ("gaze.user", "requested", "こちらを見て")], ["shared_directive", "coordination"]),
    ("shared_03", "controlled_shared_directive", "左を向いて、手を振ってください。", [("gaze.left", "requested", "左を向いて"), ("motion.wave", "requested", "手を振って")], ["shared_directive", "coordination"]),
    ("shared_04", "controlled_shared_directive", "首を横に振ってから、無表情に戻って。", [("motion.shake_head", "requested", "首を横に振って"), ("expression.neutral", "requested", "無表情に戻って")], ["shared_directive", "coordination"]),
    ("description_01", "controlled_local_description", "彼女は手を振っていたけれど、あなたはこっちを見てください。", [("motion.wave", "mentioned", "手を振っていた"), ("gaze.user", "requested", "こっちを見て")], ["local_description", "unrelated_request"]),
    ("description_02", "controlled_local_description", "先ほど右を向きましたが、今は笑ってほしい。", [("gaze.right", "mentioned", "右を向きました"), ("expression.happy", "requested", "笑ってほしい")], ["local_description", "unrelated_request"]),
    ("description_03", "controlled_local_description", "彼は無表情で考えているけど、あなたは左を向いて。", [("expression.neutral", "mentioned", "無表情"), ("gaze.left", "requested", "左を向いて")], ["local_description", "unrelated_request"]),
    ("description_04", "controlled_local_description", "私は木を指差しました。次は手を振って。", [("motion.point", "mentioned", "指差しました"), ("motion.wave", "requested", "手を振って")], ["local_description", "unrelated_request"]),
    ("conditional_01", "controlled_conditional_governance", "もし合図を出したら、右を向いて。", [("gaze.right", "hypothetical", "右を向いて")], ["conditional_governance"]),
    ("conditional_02", "controlled_conditional_governance", "仮に呼ばれたなら、手を振って。", [("motion.wave", "hypothetical", "手を振って")], ["conditional_governance"]),
    ("conditional_03", "controlled_conditional_governance", "もし音が止まったら、うなずいて。", [("motion.nod", "hypothetical", "うなずいて")], ["conditional_governance"]),
    ("conditional_04", "controlled_conditional_governance", "仮に撮影が始まるなら、笑顔になって。", [("expression.happy", "hypothetical", "笑顔になって")], ["conditional_governance"]),
    ("scope_01", "controlled_local_scope", "左を向くかどうかは、まだ決めていない。", [("gaze.left", "ambiguous", "左を向く")], ["local_pending_scope"]),
    ("scope_02", "controlled_local_scope", "手を振るかどうか、まだ迷っている。", [("motion.wave", "ambiguous", "手を振る")], ["local_pending_scope"]),
    ("scope_03", "controlled_local_scope", "うなずくかどうかは未定です。", [("motion.nod", "ambiguous", "うなずく")], ["local_pending_scope"]),
    ("scope_04", "controlled_local_scope", "仮に無表情へ戻すなら、その後で考える。", [("expression.neutral", "hypothetical", "無表情へ戻す")], ["local_hypothetical_scope"]),
    ("meta_01", "controlled_metalinguistic", "例文は『右を向いて』だが、これはお願いではない。", [("gaze.right", "mentioned", "右を向いて")], ["metalinguistic_nonrequest"]),
    ("meta_02", "controlled_metalinguistic", "台本には『笑って』とあるが、実行は禁止。", [("expression.happy", "negated", "笑って")], ["execution_prohibition"]),
    ("meta_03", "controlled_metalinguistic", "サンプルの『手を振って』は文字列で、動作はしないで。", [("motion.wave", "negated", "手を振って")], ["execution_prohibition"]),
    ("meta_04", "controlled_metalinguistic", "JSONの『うなずいて』はテスト値で、命令ではありません。", [("motion.nod", "mentioned", "うなずいて")], ["metalinguistic_nonrequest"]),
    ("replacement_01", "controlled_cross_event_replacement", "左を向いて。いや、右を向いて。", [("gaze.left", "cancelled", "左を向いて"), ("gaze.right", "requested", "右を向いて")], ["cross_event_replacement"]),
    ("replacement_02", "controlled_cross_event_replacement", "手を振って。やっぱり無表情に戻って。", [("motion.wave", "cancelled", "手を振って"), ("expression.neutral", "requested", "無表情に戻って")], ["cross_event_replacement"]),
    ("replacement_03", "controlled_cross_event_replacement", "笑顔にして。ごめん、今はじっとしていて。", [("expression.happy", "cancelled", "笑顔にして"), ("motion.idle", "requested", "じっとしていて")], ["cross_event_replacement", "positive_idle"]),
    ("replacement_04", "controlled_cross_event_replacement", "下を向いて。その代わり、軽くうなずいて。", [("gaze.down", "cancelled", "下を向いて"), ("motion.nod", "requested", "うなずいて")], ["cross_event_replacement"]),
    ("idle_01", "controlled_positive_idle", "今は動かないでいてください。", [("motion.idle", "requested", "動かないでいて")], ["positive_idle", "compiler_boundary"]),
    ("idle_02", "controlled_positive_idle", "そのままじっとしていて。", [("motion.idle", "requested", "じっとしていて")], ["positive_idle", "compiler_boundary"]),
    ("idle_03", "controlled_positive_idle", "『じっとしていて』は今すぐ実行してほしい命令です。", [("motion.idle", "requested", "じっとしていて")], ["positive_idle", "quoted_request", "compiler_boundary"]),
    ("idle_04", "controlled_positive_idle", "動かずにいて。", [("motion.idle", "requested", "動かずにいて")], ["positive_idle", "compiler_boundary"]),
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
        "forbidden_calls": [],
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
        raise ValueError("Tatoeba V56 selection and labels differ")
    cases = []
    for sentence_id, frame_specs in EXTERNAL_LABELS.items():
        row = rows[sentence_id]
        commitments = {spec[1] for spec in frame_specs}
        family = "external_tatoeba_action_boundary"
        tags = sorted(commitments | {"external_exact"})
        cases.append(
            _make_case(
                f"v56h_tatoeba_{sentence_id}",
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
        "source_type": "controlled_compositional",
        "authoring_method": (
            "LLM-assisted relation stress cases reviewed and frozen before V56 holdout inference."
        ),
        "official_corpus_claimed": False,
    }
    cases.extend(
        _make_case(f"v56h_{suffix}", family, text, specs, tags, provenance)
        for suffix, family, text, specs, tags in CONTROLLED_CASES
    )
    return {
        "schema": "uruha_relation_bound_event_graph_fresh_holdout_v56",
        "created_at": "2026-07-15T23:55:00+09:00",
        "evidence_status": "frozen_before_any_v56_holdout_inference",
        "construction": {
            "external_exact_model_generation_used": False,
            "controlled_model_assistance_used": True,
            "evaluation_model_inference_used": False,
            "answer_fields_are_evaluation_only": True,
            "project_freshness_definition": (
                "No exact input was used in UruhaBrain V37-V56 evaluation, tuning, or rule development before this freeze."
            ),
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
