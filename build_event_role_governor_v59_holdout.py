#!/usr/bin/env python3
"""Build the preregistered independent V59 event-role holdout."""

import json
from collections import Counter
from pathlib import Path

from action_selective_deliberation_v37 import FRAME_TO_CALL, derive_utterance_state


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = (
    ROOT
    / "configs"
    / "event_role_governor_v59_holdout_construction_preregistration.json"
)
SOURCE_PATH = ROOT / "datasets" / "sources" / "tatoeba_jpn_v59_selected.tsv"
OUTPUT_PATH = ROOT / "datasets" / "event_role_governor_v59_holdout.json"


EXTERNAL_LABELS = {
    "84201": [("expression.happy", "mentioned", "にっこりと笑")],
    "86703": [("expression.happy", "mentioned", "微笑")],
    "87104": [("expression.happy", "mentioned", "微笑")],
    "89563": [("expression.happy", "mentioned", "微笑")],
    "93275": [("expression.happy", "mentioned", "微笑")],
    "96980": [("expression.happy", "mentioned", "笑顔")],
    "110400": [("expression.happy", "mentioned", "笑って")],
    "114512": [("expression.happy", "mentioned", "笑って")],
    "8672756": [("expression.happy", "mentioned", "微笑")],
    "9099647": [("expression.happy", "mentioned", "笑顔")],
    "10550376": [("expression.happy", "mentioned", "笑って")],
    "13066134": [
        ("expression.surprised", "mentioned", "驚き"),
        ("motion.nod", "mentioned", "頷いて"),
    ],
    "13066287": [("expression.happy", "mentioned", "笑顔")],
    "13066388": [("expression.happy", "mentioned", "微笑")],
    "13070297": [("expression.happy", "mentioned", "笑顔")],
    "13146953": [("expression.happy", "mentioned", "笑顔")],
}


CONTROLLED_CASES = {
    "controlled_embedded_speech_content": [
        ("expression.angry", "彼女がなぜ怒った顔を見せたのか、理由を教えてください。", "怒った顔"),
        ("expression.happy", "あの人がどんな場面で微笑んだのか説明してください。", "微笑"),
        ("expression.neutral", "友人がいつ真顔に戻ったのか教えてください。", "真顔"),
        ("expression.sad", "彼がどうして悲しい顔をしたのか話してください。", "悲しい顔"),
        ("expression.surprised", "彼女が何を見て驚いた顔になったのか説明してください。", "驚いた顔"),
        ("gaze.down", "先生がいつ下を向いたのか教えてください。", "下を向いた"),
        ("gaze.left", "トムがなぜ左を向いたのか説明してください。", "左を向いた"),
        ("gaze.right", "彼女がどの合図で右を向いたのか教えてください。", "右を向いた"),
        ("gaze.user", "友達がいつカメラを見たのか話してください。", "カメラを見た"),
        ("motion.idle", "彼がなぜ長い間じっとしていたのか説明してください。", "じっとしていた"),
        ("motion.nod", "上司が何回うなずいたのか教えてください。", "うなずいた"),
        ("motion.point", "店員がどこを指差したのか説明してください。", "指差した"),
        ("motion.shake_head", "彼女がどうして首を横に振ったのか教えてください。", "首を横に振った"),
        ("motion.wave", "友人が誰に手を振ったのか話してください。", "手を振った"),
    ],
    "controlled_third_party_habitual_description": [
        ("expression.angry", "彼女は毎朝、鏡の前で怒った顔を作る。", "怒った顔"),
        ("expression.happy", "あの人は普段、客に笑顔を見せる。", "笑顔"),
        ("expression.neutral", "トムは毎回、撮影後に真顔へ戻る。", "真顔"),
        ("expression.sad", "彼はよく、演技で悲しい顔を作る。", "悲しい顔"),
        ("expression.surprised", "友人はいつも、小さな音でも驚いた顔になる。", "驚いた顔"),
        ("gaze.down", "先生は毎朝、名簿を見るとき下を向く。", "下を向く"),
        ("gaze.left", "彼女は毎回、合図があると左を向く。", "左を向く"),
        ("gaze.right", "トムは普段、時計を見るため右を向く。", "右を向く"),
        ("gaze.user", "店員はいつも、説明中にカメラを見る。", "カメラを見る"),
        ("motion.idle", "友達はよく、考える間じっとしている。", "じっとしている"),
        ("motion.nod", "上司は毎回、報告を聞くとうなずく。", "うなずく"),
        ("motion.point", "先生は普段、地図を指差して説明する。", "指差して"),
        ("motion.shake_head", "彼はよく、反対するとき首を横に振る。", "首を横に振る"),
        ("motion.wave", "彼女は毎朝、門の前で手を振る。", "手を振る"),
    ],
    "controlled_past_experiential_description": [
        ("expression.angry", "昨日、彼女が怒った顔を見せたので少し怖かった。", "怒った顔"),
        ("expression.happy", "先日、友人が笑顔を見せてくれて嬉しかった。", "笑顔"),
        ("expression.neutral", "昨日、トムがすぐ真顔に戻ったので寂しかった。", "真顔"),
        ("expression.sad", "この前、彼が悲しい顔で別れを告げたので寂しかった。", "悲しい顔"),
        ("expression.surprised", "昨日、友達が驚いた顔を見せたので少し怖かった。", "驚いた顔"),
        ("gaze.down", "先日、先生が急に下を向いたので寂しかった。", "下を向いた"),
        ("gaze.left", "昨日、彼女が合図で左を向いてくれて嬉しかった。", "左を向いて"),
        ("gaze.right", "この前、トムが突然右を向いたので少し怖かった。", "右を向いた"),
        ("gaze.user", "先日、友人がカメラを見てくれて嬉しかった。", "カメラを見て"),
        ("motion.idle", "昨日、彼が静かにじっとしてくれて安心でした。", "じっとして"),
        ("motion.nod", "先日、上司が何度もうなずいてくれて嬉しかった。", "うなずいて"),
        ("motion.point", "昨日、先生が正しい場所を指差してくれて嬉しかった。", "指差して"),
        ("motion.shake_head", "以前、彼女がはっきり首を横に振ったので残念だった。", "首を横に振った"),
        ("motion.wave", "昨日、友人が駅で手を振ってくれて嬉しかった。", "手を振って"),
    ],
    "controlled_direct_focus_request_contrast": [
        ("expression.angry", "昨日みたいに怒った顔を見せてください。", "怒った顔"),
        ("expression.happy", "彼女に向けて、毎回笑ってください。", "笑って"),
        ("expression.neutral", "さっきの表情から真顔に戻してください。", "真顔"),
        ("expression.sad", "演技なので悲しい顔を見せてください。", "悲しい顔"),
        ("expression.surprised", "昨日の場面みたいに驚いた顔をしてください。", "驚いた顔"),
        ("gaze.down", "彼が来たら、合図で下を向いてください。", "下を向いて"),
        ("gaze.left", "説明してから左を向いてください。", "左を向いて"),
        ("gaze.right", "彼女が入ったら右を向いてください。", "右を向いて"),
        ("gaze.user", "昔の写真を持つのでカメラを見てください。", "カメラを見て"),
        ("motion.idle", "彼に話してから、しばらくじっとしていてください。", "じっとして"),
        ("motion.nod", "先生の説明が終わったら毎回うなずいてください。", "うなずいて"),
        ("motion.point", "彼女に場所を教えるため地図を指差してください。", "指差して"),
        ("motion.shake_head", "昨日と同じ合図で首を横に振ってください。", "首を横に振って"),
        ("motion.wave", "説明を終えてから彼に手を振ってください。", "手を振って"),
    ],
}


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
        sentence_id, language, text, username, added, modified = raw.split("\t")
        rows[sentence_id] = {
            "language": language,
            "text": text,
            "username": username,
            "date_added": added,
            "date_modified": modified,
        }
    expected_ids = {str(value) for value in config["external_source"]["selected_sentence_ids"]}
    if set(rows) != expected_ids or set(EXTERNAL_LABELS) != expected_ids:
        raise ValueError("V59 Tatoeba selection, labels, and preregistration differ")
    cases = []
    for sentence_id in sorted(rows, key=int):
        row = rows[sentence_id]
        specs = EXTERNAL_LABELS[sentence_id]
        cases.append(
            _make_case(
                f"v59h_tatoeba_{sentence_id}",
                "external_tatoeba_event_role",
                row["text"],
                specs,
                {
                    "source_type": "external_exact",
                    "corpus": "Tatoeba Japanese detailed sentences export",
                    "sentence_id": int(sentence_id),
                    "username": row["username"],
                    "date_added": row["date_added"],
                    "date_modified": row["date_modified"],
                    "sentence_url": f"https://tatoeba.org/en/sentences/show/{sentence_id}",
                },
                {"external_exact", "mentioned"},
            )
        )
    return cases


def _controlled_cases(config):
    matrix = config["controlled_matrix"]
    expected_targets = matrix["target_ids_per_family"]
    provenance = {
        "source_type": "controlled_researcher_authored",
        "authoring_method": matrix["authoring_provenance"],
        "model_assistance_used": matrix["model_assistance_used"],
        "human_blind_review_used": matrix["human_blind_review_used"],
        "official_corpus_claimed": matrix["official_corpus_claimed"],
    }
    cases = []
    for family, family_contract in matrix["families"].items():
        rows = CONTROLLED_CASES[family]
        if [row[0] for row in rows] != expected_targets:
            raise ValueError(f"V59 controlled target order drift: {family}")
        for index, (target_id, text, evidence) in enumerate(rows, start=1):
            cases.append(
                _make_case(
                    f"v59h_{family.removeprefix('controlled_')}_{index:02d}",
                    family,
                    text,
                    [(target_id, family_contract["expected_commitment"], evidence)],
                    provenance,
                    {
                        family_contract["expected_relation"],
                        "execute_action" if family_contract["expected_action"] else "withhold_action",
                    },
                )
            )
    return cases


def build():
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    cases = _external_cases(config) + _controlled_cases(config)
    return {
        "schema": "uruha_event_role_governor_independent_holdout_v59",
        "created_at": "2026-07-16T02:04:00+09:00",
        "evidence_status": "frozen_before_any_v58_or_v59_holdout_evaluation",
        "construction": {
            "external_exact_model_generation_used": False,
            "controlled_model_assistance_used": False,
            "controlled_human_blind_review_used": False,
            "evaluation_model_inference_used": False,
            "v58_state_evaluation_used": False,
            "v59_state_evaluation_used": False,
            "compiler_evaluation_used": False,
            "gold_visible_to_future_model_state_or_compiler": False,
            "base_model_pretraining_exclusion_guaranteed": False,
        },
        "external_source": {
            **config["external_source"],
            "selected_snapshot": str(SOURCE_PATH.relative_to(ROOT)),
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
