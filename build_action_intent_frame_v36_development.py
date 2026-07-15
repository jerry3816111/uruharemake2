#!/usr/bin/env python3
"""Build the frozen V36 development annotations from retired V34 cases."""

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SOURCE_PATH = ROOT / "datasets" / "rightbrain_role_specialization_v34_confirmation.json"
DEFAULT_OUTPUT = ROOT / "datasets" / "action_intent_frame_v36_development.json"
SOURCE_SHA256 = "a45919164c9416622b6f582d9f85ad163878127057743fe4935ea343008f7a14"
PREREGISTRATION_COMMIT = "b89e8fa"


def frame(frame_name, value, commitment, *evidence_options):
    return {
        "frame": frame_name,
        "value": value,
        "commitment": commitment,
        "evidence_options": list(evidence_options),
    }


ANNOTATIONS = {
    "v34c_action_single_wave": (
        "explicit_current_request",
        [frame("motion", "wave", "requested", "手を振ってくれる？")],
    ),
    "v34c_action_single_nod_colloquial": (
        "explicit_current_request",
        [frame("motion", "nod", "requested", "首を縦に動かして")],
    ),
    "v34c_action_single_point": (
        "explicit_current_request",
        [frame("motion", "point", "requested", "指で示してくれる？")],
    ),
    "v34c_action_single_smile_colloquial": (
        "explicit_current_request",
        [frame("expression", "happy", "requested", "にこっとして")],
    ),
    "v34c_action_single_eyes_colloquial": (
        "explicit_current_request",
        [frame("gaze", "user", "requested", "目線をこっちにちょうだい")],
    ),
    "v34c_action_single_neutral": (
        "explicit_current_request",
        [frame("expression", "neutral", "requested", "普通の表情へ戻して")],
    ),
    "v34c_action_multi_happy_user": (
        "explicit_current_request",
        [
            frame("expression", "happy", "requested", "笑った顔で"),
            frame("gaze", "user", "requested", "こちらを見て"),
        ],
    ),
    "v34c_action_multi_surprised_right": (
        "explicit_current_request",
        [
            frame("expression", "surprised", "requested", "驚いた表情"),
            frame("gaze", "right", "requested", "右へ視線を向けて"),
        ],
    ),
    "v34c_action_multi_sad_down": (
        "explicit_current_request",
        [
            frame("expression", "sad", "requested", "悲しい顔で"),
            frame("gaze", "down", "requested", "下を見て"),
        ],
    ),
    "v34c_action_multi_neutral_idle": (
        "explicit_current_request",
        [
            frame("expression", "neutral", "requested", "表情を普通に戻して"),
            frame("motion", "idle", "requested", "待機姿勢にして"),
        ],
    ),
    "v34c_action_multi_angry_shake": (
        "explicit_current_request",
        [
            frame("expression", "angry", "requested", "怒った顔"),
            frame("motion", "shake_head", "requested", "首を横に振って"),
        ],
    ),
    "v34c_action_multi_wave_user": (
        "explicit_current_request",
        [
            frame("gaze", "user", "requested", "こっちを見ながら"),
            frame("motion", "wave", "requested", "手を振って"),
        ],
    ),
    "v34c_action_none_gesture": (
        "no_current_action",
        [frame("motion", "wave", "mentioned", "手を振る仕草")],
    ),
    "v34c_action_none_expression": ("no_current_action", []),
    "v34c_action_none_direction": (
        "no_current_action",
        [
            frame("gaze", "left", "mentioned", "左"),
            frame("gaze", "right", "mentioned", "右"),
        ],
    ),
    "v34c_action_none_music": ("no_current_action", []),
    "v34c_action_none_hypothetical": (
        "no_current_action",
        [frame("expression", "happy", "hypothetical", "もし笑顔だったら")],
    ),
    "v34c_action_none_explicit_none": ("no_current_action", []),
    "v34c_action_negated_wave": (
        "no_current_action",
        [frame("motion", "wave", "cancelled", "手を振るのをやめて")],
    ),
    "v34c_action_negated_happy": (
        "no_current_action",
        [frame("expression", "happy", "negated", "笑顔には変えないで")],
    ),
    "v34c_action_negated_down_user": (
        "explicit_current_request",
        [
            frame("gaze", "down", "negated", "下は見ず"),
            frame("gaze", "user", "requested", "こっちだけ見て"),
        ],
    ),
    "v34c_action_negated_nod_shake": (
        "explicit_current_request",
        [
            frame("motion", "nod", "negated", "うなずかないで"),
            frame("motion", "shake_head", "requested", "首を横に振って"),
        ],
    ),
    "v34c_action_negated_angry_neutral": (
        "explicit_current_request",
        [
            frame("expression", "angry", "negated", "怒った顔じゃなく"),
            frame("expression", "neutral", "requested", "普通の表情へ戻して"),
        ],
    ),
    "v34c_action_negated_point_wave": (
        "explicit_current_request",
        [
            frame("motion", "point", "negated", "指差しはなしで"),
            frame("motion", "wave", "requested", "手を振って"),
        ],
    ),
    "v34c_action_ambiguous_wave": (
        "ambiguous_or_cancelled",
        [frame("motion", "wave", "ambiguous", "手を振るか")],
    ),
    "v34c_action_ambiguous_smile": (
        "ambiguous_or_cancelled",
        [frame("expression", "happy", "ambiguous", "笑顔にするか")],
    ),
    "v34c_action_ambiguous_direction": (
        "ambiguous_or_cancelled",
        [
            frame("gaze", "left", "ambiguous", "左を見るか"),
            frame("gaze", "right", "ambiguous", "右を見るか"),
        ],
    ),
    "v34c_action_ambiguous_cancel": (
        "ambiguous_or_cancelled",
        [
            frame(
                "motion",
                "nod",
                "cancelled",
                "うなずいて。いや、今の頼みは取り消し",
            )
        ],
    ),
    "v34c_action_ambiguous_if": (
        "ambiguous_or_cancelled",
        [frame("gaze", "down", "hypothetical", "もし下を向いてって頼んだら")],
    ),
    "v34c_action_ambiguous_expression": ("ambiguous_or_cancelled", []),
    "v34c_action_invalid_crouch": (
        "unsupported_or_unsafe",
        [frame("unsupported", "unsupported", "unsupported", "その場でしゃがんで")],
    ),
    "v34c_action_invalid_arms": (
        "unsupported_or_unsafe",
        [
            frame(
                "unsupported",
                "unsupported",
                "unsupported",
                "両腕を頭の上まで上げて",
            )
        ],
    ),
    "v34c_action_invalid_screen": (
        "unsupported_or_unsafe",
        [frame("unsupported", "unsupported", "unsupported", "画面を閉じて")],
    ),
    "v34c_action_invalid_mail": (
        "unsupported_or_unsafe",
        [frame("unsupported", "unsupported", "unsupported", "メールを送って")],
    ),
    "v34c_action_invalid_camera": (
        "unsupported_or_unsafe",
        [frame("unsupported", "unsupported", "unsupported", "カメラを一周回して")],
    ),
    "v34c_action_invalid_kick": (
        "unsupported_or_unsafe",
        [frame("unsupported", "unsupported", "unsupported", "相手を蹴る動作をして")],
    ),
}


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build():
    if _sha256(SOURCE_PATH) != SOURCE_SHA256:
        raise ValueError("V34 source dataset hash mismatch")
    source = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))
    source_cases = source["action_cases"]
    source_ids = {case["id"] for case in source_cases}
    if source_ids != set(ANNOTATIONS):
        missing = sorted(source_ids - set(ANNOTATIONS))
        extra = sorted(set(ANNOTATIONS) - source_ids)
        raise ValueError(f"Annotation IDs differ: missing={missing}, extra={extra}")

    cases = []
    for source_case in source_cases:
        expected_state, expected_frames = ANNOTATIONS[source_case["id"]]
        cases.append(
            {
                "id": source_case["id"],
                "family": source_case["family"],
                "user_input": source_case["user_input"],
                "expected_state": expected_state,
                "expected_frames": expected_frames,
                "expected_calls": source_case["expected_calls"],
                "forbidden_calls": source_case["forbidden_calls"],
                "expected_no_action": source_case["expected_no_action"],
            }
        )

    family_counts = Counter(case["family"] for case in cases)
    state_counts = Counter(case["expected_state"] for case in cases)
    commitment_counts = Counter(
        frame_row["commitment"]
        for case in cases
        for frame_row in case["expected_frames"]
    )
    return {
        "schema": "uruha_action_intent_frame_development_v36",
        "evidence_status": "development_only_from_retired_v34_confirmation",
        "annotation_parent_commit": PREREGISTRATION_COMMIT,
        "source_dataset": str(SOURCE_PATH.relative_to(ROOT)),
        "source_dataset_sha256": SOURCE_SHA256,
        "annotation_method": "Manually specified utterance state and frame commitments after V36 preregistration and before any V36 model inference.",
        "cases": cases,
        "accounting": {
            "case_count": len(cases),
            "family_counts": dict(sorted(family_counts.items())),
            "state_counts": dict(sorted(state_counts.items())),
            "commitment_counts": dict(sorted(commitment_counts.items())),
            "frame_count": sum(len(case["expected_frames"]) for case in cases),
            "requested_frame_count": sum(
                frame_row["commitment"] == "requested"
                for case in cases
                for frame_row in case["expected_frames"]
            ),
            "expected_call_count": sum(len(case["expected_calls"]) for case in cases),
        },
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    payload = build()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload["accounting"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
