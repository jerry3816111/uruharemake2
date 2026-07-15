#!/usr/bin/env python3
"""Build the preregistered second independent V60 holdout."""

import json
from collections import Counter
from pathlib import Path

from action_selective_deliberation_v37 import FRAME_TO_CALL, derive_utterance_state


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = (
    ROOT
    / "configs"
    / "predicate_morphology_v60_independent_holdout_construction_preregistration.json"
)
SOURCE_PATH = ROOT / "datasets" / "sources" / "tatoeba_jpn_v60_selected.tsv"
OUTPUT_PATH = ROOT / "datasets" / "predicate_morphology_v60_independent_holdout.json"


EXTERNAL_LABELS = {
    "77061": [("motion.nod", "mentioned", "頷いたり")],
    "89262": [
        ("gaze.user", "mentioned", "私を見ると"),
        ("motion.wave", "mentioned", "手を振った"),
    ],
    "89236": [("motion.wave", "mentioned", "手を振った")],
    "89369": [("motion.nod", "mentioned", "うなずいた")],
    "105809": [("motion.nod", "mentioned", "うなずいた")],
    "106208": [("motion.nod", "mentioned", "うなずいた")],
    "140700": [
        ("motion.nod", "mentioned", "うなずき"),
        ("expression.happy", "mentioned", "微笑みかけた"),
        ("gaze.user", "mentioned", "私に向かって"),
    ],
    "141579": [("motion.point", "mentioned", "指差し")],
    "147040": [("gaze.user", "mentioned", "こちらを見て")],
    "187634": [("motion.shake_head", "mentioned", "首を横に振った")],
    "226224": [("gaze.user", "requested", "カメラのほうを見て")],
    "1487199": [("motion.nod", "mentioned", "うなずきました")],
    "7422030": [("motion.wave", "mentioned", "手を振った")],
    "9510760": [("expression.happy", "negated", "笑ってくれない")],
    "9824718": [("expression.happy", "mentioned", "笑顔")],
    "11578540": [("expression.happy", "mentioned", "笑ってた")],
    "13038799": [("expression.happy", "mentioned", "微笑みながら")],
    "13146797": [("expression.happy", "mentioned", "笑顔")],
    "13176060": [("expression.happy", "mentioned", "笑顔")],
}


TARGET_SPECS = [
    ("expression.angry", "姉", "怒った顔を見せて", "怒った顔を見せた", "怒った顔"),
    ("expression.happy", "友達", "笑顔を見せて", "笑顔を見せた", "笑顔"),
    ("expression.neutral", "同僚", "真顔に戻って", "真顔に戻った", "真顔"),
    ("expression.sad", "妹", "悲しい顔を見せて", "悲しい顔を見せた", "悲しい顔"),
    ("expression.surprised", "先生", "驚いた顔をして", "驚いた顔をした", "驚いた顔"),
    ("gaze.down", "兄", "下を向いて", "下を向いた", "下を向"),
    ("gaze.left", "母", "左を向いて", "左を向いた", "左を向"),
    ("gaze.right", "父", "右を向いて", "右を向いた", "右を向"),
    ("gaze.user", "店員", "カメラを見て", "カメラを見た", "カメラを見"),
    ("motion.idle", "上司", "じっとしていて", "じっとしていた", "じっとして"),
    ("motion.nod", "教師", "うなずいて", "うなずいた", "うなず"),
    ("motion.point", "女性", "案内板を指差して", "案内板を指差した", "指差"),
    ("motion.shake_head", "男性", "首を横に振って", "首を横に振った", "首を横に振"),
    ("motion.wave", "弟", "手を振って", "手を振った", "手を振"),
]

CONTEXTS = [
    "舞台袖で",
    "集合写真の前で",
    "会議が終わると",
    "短い芝居の中で",
    "合図を聞くと",
    "名前を呼ばれると",
    "入口の印を見て",
    "時計の音に合わせて",
    "撮影が始まると",
    "考えをまとめる間",
    "説明を聞いた後",
    "道順を示すため",
    "質問への返事として",
    "駅のホームから",
]
REQUEST_ENDINGS = ["くれますか", "くれるかな", "くれませんか", "くれ"]


def _frame(target_id, commitment, evidence):
    domain, value = target_id.split(".", 1)
    return {
        "domain": domain,
        "value": value,
        "commitment": commitment,
        "evidence_options": [evidence],
    }


def _make_case(case_id, family, text, frame_specs, provenance, tags):
    frames = [_frame(*spec) for spec in frame_specs]
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


def _external_cases(config):
    rows = {}
    for raw in SOURCE_PATH.read_text(encoding="utf-8").splitlines():
        sentence_id, language, text, owner, added, modified = raw.split("\t")
        rows[sentence_id] = {
            "language": language,
            "text": text,
            "owner": owner,
            "date_added": added,
            "date_modified": modified,
        }
    expected_ids = {
        str(value) for value in config["external_source"]["selected_sentence_ids"]
    }
    if set(rows) != expected_ids or set(EXTERNAL_LABELS) != expected_ids:
        raise ValueError("V60 Tatoeba selection, labels, and preregistration differ")

    cases = []
    for sentence_id in sorted(rows, key=int):
        row = rows[sentence_id]
        specs = EXTERNAL_LABELS[sentence_id]
        cases.append(
            _make_case(
                f"v60h_tatoeba_{sentence_id}",
                "external_tatoeba_predicate_morphology",
                row["text"],
                specs,
                {
                    "source_type": "external_exact",
                    "corpus": config["external_source"]["source_name"],
                    "sentence_id": int(sentence_id),
                    "owner": row["owner"],
                    "date_added": row["date_added"],
                    "date_modified": row["date_modified"],
                    "sentence_url": f"https://tatoeba.org/en/sentences/show/{sentence_id}",
                    "snapshot_download_sha256": config["external_source"][
                        "download_sha256"
                    ],
                },
                {"external_exact", *(spec[1] for spec in specs)},
            )
        )
    return cases


def _controlled_text(family, index, subject, action_te, action_past):
    context = CONTEXTS[index]
    if family == "controlled_completed_benefactive_without_time_adverb":
        return f"{subject}が{context}、{action_te}くれた。"
    if family == "controlled_explicit_third_party_polite_benefactive":
        return f"{subject}は{context}、{action_te}くれます。"
    if family == "controlled_omitted_subject_current_request":
        ending = REQUEST_ENDINGS[index % len(REQUEST_ENDINGS)]
        return f"{context}、{action_te}{ending}。"
    if family == "controlled_negative_benefactive_or_focus_event":
        return f"{subject}は{context}、{action_te}くれなかった。"
    if family == "controlled_embedded_speech_request":
        return f"{subject}が{context}{action_past}のか、教えてくれませんか。"
    if family == "controlled_full_predicate_direct_request":
        return f"{context}、{action_te}ください。"
    if family == "controlled_nonbenefactive_third_party_declarative":
        return f"{subject}は{context}、{action_past}。"
    raise ValueError(f"unknown V60 family: {family}")


def _controlled_cases(config):
    matrix = config["controlled_matrix"]
    provenance = {
        "source_type": matrix["source_type"],
        "authoring_method": "fixed morphology contrast crossed with fourteen preregistered embodied targets",
        "model_assistance_used": matrix["model_assistance_used"],
        "human_blind_review_used": matrix["human_blind_review_used"],
        "official_corpus_claimed": matrix["official_corpus_claimed"],
    }
    cases = []
    for family, contract in matrix["families"].items():
        for index, (target_id, subject, action_te, action_past, evidence) in enumerate(
            TARGET_SPECS
        ):
            text = _controlled_text(
                family, index, subject, action_te, action_past
            )
            cases.append(
                _make_case(
                    f"v60h_{family.removeprefix('controlled_')}_{index + 1:02d}",
                    family,
                    text,
                    [(target_id, contract["expected_commitment"], evidence)],
                    provenance,
                    {
                        contract["expected_predicate_force"],
                        contract["expected_relation"] or "no_relation",
                        "execute_action"
                        if contract["expected_action"]
                        else "withhold_action",
                    },
                )
            )
    return cases


def build():
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    cases = _external_cases(config) + _controlled_cases(config)
    return {
        "schema": "uruha_predicate_morphology_independent_holdout_v60",
        "created_at": "2026-07-16T03:08:00+09:00",
        "evidence_status": "frozen_before_any_v59_or_v60_independent_evaluation",
        "construction": {
            "external_exact_model_generation_used": False,
            "controlled_model_assistance_used": False,
            "controlled_human_blind_review_used": False,
            "evaluation_model_inference_used": False,
            "v59_state_evaluation_used": False,
            "v60_state_evaluation_used": False,
            "compiler_evaluation_used": False,
            "gold_visible_to_future_model_state_or_compiler": False,
            "base_model_pretraining_exclusion_guaranteed": False,
        },
        "external_source": {
            **config["external_source"],
            "selected_snapshot": str(SOURCE_PATH.relative_to(ROOT)),
        },
        "case_count": len(cases),
        "grounded_target_count": sum(
            len(case["expected_frames"]) for case in cases
        ),
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
                "grounded_target_count": payload["grounded_target_count"],
                "source_counts": payload["source_counts"],
                "family_counts": payload["family_counts"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
