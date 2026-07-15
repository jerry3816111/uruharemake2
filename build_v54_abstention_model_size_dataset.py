#!/usr/bin/env python3
"""Freeze the V54 abstention subset before any new model-size inference."""

import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent
V54_DATASET_PATH = ROOT / "datasets" / "metalinguistic_nonrequest_v54_holdout.json"
V54_RAW_PATH = ROOT / "reports" / "metalinguistic_nonrequest_v54_holdout_raw.json"
OUTPUT_PATH = ROOT / "datasets" / "v54_abstention_model_size_holdout.json"


def build():
    dataset = json.loads(V54_DATASET_PATH.read_text(encoding="utf-8"))
    raw = json.loads(V54_RAW_PATH.read_text(encoding="utf-8"))
    cases = {case["id"]: case for case in dataset["cases"]}
    gold = {
        (case["id"], f"{frame['domain']}.{frame['value']}"): frame["commitment"]
        for case in dataset["cases"]
        for frame in case["expected_frames"]
    }
    candidate_rows = {row["case_id"]: row for row in raw["candidate_rows"]}

    items = []
    for row in raw["target_rows"]:
        if row["state_machine"]["resolved"]:
            continue
        case = cases[row["case_id"]]
        target_id = row["target_id"]
        candidate = next(
            candidate
            for candidate in candidate_rows[row["case_id"]]["candidates"]
            if candidate["target_id"] == target_id
        )
        parsed = row["fresh_v51_result"]["parsed"]
        items.append(
            {
                "id": f"{row['case_id']}::{target_id}",
                "case_id": row["case_id"],
                "target_id": target_id,
                "input_text": case["user_input"],
                "source_type": case["source_type"],
                "family": case["family"],
                "candidate": candidate,
                "all_candidates": candidate_rows[row["case_id"]]["candidates"],
                "expected_commitment": gold[(row["case_id"], target_id)],
                "selection_reason": "v54_no_high_confidence_transition",
                "frozen_v54_resolution_rule": row["state_machine"]["resolution_rule"],
                "frozen_qwen35_4b_commitment": (
                    parsed.get("commitment") if parsed.get("parse_success") else None
                ),
                "frozen_qwen35_4b_parse_success": bool(parsed.get("parse_success")),
            }
        )

    return {
        "schema": "uruha_v54_abstention_model_size_holdout",
        "created_at": "2026-07-15T23:25:00+09:00",
        "evidence_status": "frozen_before_any_new_model_size_inference",
        "construction": {
            "selection_is_mechanical": True,
            "selection_rule": "Every and only V54 independent-holdout target with resolved=false.",
            "new_model_generation_used": False,
            "new_model_inference_used": False,
            "source_holdout_is_consumed": True,
            "claim_scope": "Diagnostic comparison on frozen abstentions only; not a new generalization holdout.",
        },
        "item_count": len(items),
        "source_counts": dict(
            sorted(Counter(item["source_type"] for item in items).items())
        ),
        "gold_commitment_counts": dict(
            sorted(Counter(item["expected_commitment"] for item in items).items())
        ),
        "frozen_4b_correct_count": sum(
            item["frozen_qwen35_4b_parse_success"]
            and item["frozen_qwen35_4b_commitment"] == item["expected_commitment"]
            for item in items
        ),
        "items": items,
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
                "item_count": payload["item_count"],
                "source_counts": payload["source_counts"],
                "gold_commitment_counts": payload["gold_commitment_counts"],
                "frozen_4b_correct_count": payload["frozen_4b_correct_count"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
