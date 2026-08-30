#!/usr/bin/env python3
"""Build the source-disjoint M10.2 synthetic register fixture."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DEFAULT_OUTPUT = ROOT / "datasets/m10_2_behavior_preserving_register_synthetic_fixture_v1.json"

LABELS = [
    "accept_support_and_continue",
    "acknowledge_then_continue",
    "ask_clarification",
    "defer_commitment",
    "direct_rejection",
    "pause_and_reassess",
]

CASES = [
    ("R-ZH-01", "zh", "熟悉的隊友主動說可以幫忙整理今晚的遊戲素材。", "familiar_teammate", "accept_support_and_continue"),
    ("R-EN-01", "en", "A regular collaborator offers to watch the queue while the speaker fixes audio.", "familiar_collaborator", "accept_support_and_continue"),
    ("R-JA-01", "ja", "いつもの仲間が、残りの確認作業を半分引き受けると言った。", "familiar_teammate", "accept_support_and_continue"),
    ("R-ZH-02", "zh", "小問題已經排除，大家正在等她繼續下一場。", "familiar_group", "acknowledge_then_continue"),
    ("R-EN-02", "en", "The temporary delay is cleared and the group is ready to continue.", "familiar_group", "acknowledge_then_continue"),
    ("R-JA-02", "ja", "接続が戻り、次の試合を始められる状態になった。", "familiar_group", "acknowledge_then_continue"),
    ("R-ZH-03", "zh", "朋友只說把那個放到後面，但沒有說是影片還是遊戲。", "familiar_friend", "ask_clarification"),
    ("R-EN-03", "en", "A teammate says to use the other setup without naming which of two setups.", "familiar_teammate", "ask_clarification"),
    ("R-JA-03", "ja", "相手が「あっちでいい」とだけ言い、二つの候補のどちらか分からない。", "familiar_friend", "ask_clarification"),
    ("R-ZH-04", "zh", "臨時邀約剛送來，但明天的安排還沒有確定。", "acquaintance", "defer_commitment"),
    ("R-EN-04", "en", "A new collaborator asks for a firm weekend commitment before the schedule is known.", "new_collaborator", "defer_commitment"),
    ("R-JA-04", "ja", "来週の予定がまだ出ていないのに、今すぐ参加を確約してほしいと言われた。", "acquaintance", "defer_commitment"),
    ("R-ZH-05", "zh", "不熟的人要求她公開朋友私下傳來的語音內容。", "unfamiliar_person", "direct_rejection"),
    ("R-EN-05", "en", "A stranger asks her to share a private message from a friend on stream.", "unfamiliar_person", "direct_rejection"),
    ("R-JA-05", "ja", "初対面の相手が、友人との非公開メッセージを配信で見せてほしいと言った。", "unfamiliar_person", "direct_rejection"),
    ("R-ZH-06", "zh", "同一個音訊問題連續出現三次，再開始前需要重新檢查。", "familiar_group", "pause_and_reassess"),
    ("R-EN-06", "en", "The same controller fault appears for a third time just before the next match.", "familiar_group", "pause_and_reassess"),
    ("R-JA-06", "ja", "次のゲームを始める直前に、同じ入力不具合が三回目も起きた。", "familiar_group", "pause_and_reassess"),
]


def build_fixture():
    return {
        "schema": "ilhdt_m10_2_behavior_preserving_register_fixture_v1",
        "dataset_id": "m10_2_register_source_disjoint_synthetic_v1",
        "status": "synthetic_frozen_before_first_model_output",
        "formal_target_claim": False,
        "target": {
            "target_id": "synthetic_surface_speaker",
            "persona_role": "public-evidence development expression carrier only",
            "not_real_person": True,
        },
        "taxonomy": {"labels": LABELS},
        "source_disjointness": {
            "m9_m10_event_overlap_count": 0,
            "created_after_m10_failure_type_known": True,
            "m10_outputs_used_as_cases_or_demonstrations": False,
        },
        "cases": [
            {
                "case_id": case_id,
                "language": language,
                "event_context": event_context,
                "relationship_context": relationship,
                "authoritative_behavior": behavior,
            }
            for case_id, language, event_context, relationship, behavior in CASES
        ],
    }


def validate_fixture(fixture):
    cases = fixture["cases"]
    language_counts = {language: sum(row["language"] == language for row in cases) for language in ("zh", "en", "ja")}
    label_counts = {label: sum(row["authoritative_behavior"] == label for row in cases) for label in LABELS}
    errors = []
    if len(cases) != 18:
        errors.append("case count must be 18")
    if language_counts != {"zh": 6, "en": 6, "ja": 6}:
        errors.append(f"language imbalance: {language_counts}")
    if any(count != 3 for count in label_counts.values()):
        errors.append(f"label imbalance: {label_counts}")
    if len({row["event_context"] for row in cases}) != len(cases):
        errors.append("event texts must be unique")
    return {"valid": not errors, "errors": errors, "language_counts": language_counts, "label_counts": label_counts}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()
    fixture = build_fixture()
    validation = validate_fixture(fixture)
    if not validation["valid"]:
        raise SystemExit("; ".join(validation["errors"]))
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(fixture, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(path), **validation}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
