#!/usr/bin/env python3
"""Rerun V35.1 with a complete, example-free VRM action ontology."""

import argparse
import json
from pathlib import Path

from run_action_semantic_authorization_v35 import run as run_v35
from run_action_semantic_authorization_v35_1 import SYSTEM_PROMPT_V35_1


ROOT = Path(__file__).resolve().parent
DEFAULT_OUTPUT = ROOT / "reports" / "action_semantic_authorization_v35_2_development_raw.json"

ACTION_CATALOG_V35_2 = {
    "set_expression": {
        "description_ja": "アバターの顔の表情だけを変更する。",
        "expression": {
            "neutral": "通常の感情を強く示さない標準表情。",
            "happy": "喜びや親しさを示す明るい表情。",
            "sad": "悲しさを示す表情。",
            "angry": "怒りを示す表情。",
            "surprised": "驚きを示す表情。",
        },
    },
    "play_motion": {
        "description_ja": "アバターの身体または頭の定義済み動作を一つ再生する。",
        "motion": {
            "idle": "能動的な身振りを止め、標準の待機動作へ戻る。",
            "wave": "手を左右に動かす挨拶の身振り。",
            "nod": "頭を縦方向に動かす肯定の身振り。",
            "shake_head": "頭を左右方向に動かす身振り。",
            "point": "腕と指を使って前方の対象を示す身振り。",
        },
    },
    "set_gaze": {
        "description_ja": "頭の身振りではなく、アバターの視線の向きだけを変更する。",
        "target": {
            "left": "アバター基準の左方向。",
            "right": "アバター基準の右方向。",
            "user": "現在の会話相手または正面の対話カメラの方向。",
            "down": "アバター基準の下方向。",
        },
    },
}


def run(output=DEFAULT_OUTPUT):
    return run_v35(
        output,
        system_prompt=SYSTEM_PROMPT_V35_1,
        study_variant="v35_2",
        action_catalog=ACTION_CATALOG_V35_2,
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = run(args.output)
    print(
        json.dumps(
            {"rows": len(report["rows"]), "completed_at": report["completed_at"]},
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
