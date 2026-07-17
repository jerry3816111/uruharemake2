#!/usr/bin/env python3
"""Build the V6 procedural-admission near-miss development dataset."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parent
PREREG_PATH = (
    ROOT
    / "configs"
    / "reflection_admission_v6_nearmiss_construction_preregistration.json"
)
SOURCE_PATH = (
    ROOT / "datasets" / "sources" / "tatoeba_reflection_admission_v6_selected.json"
)
DEFAULT_OUTPUT = ROOT / "datasets" / "reflection_admission_v6_nearmiss_development.json"
TZ = ZoneInfo("Asia/Tokyo")


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def build_dataset(preregistration, source):
    source_by_id = {row["sentence_id"]: row for row in source["items"]}
    selected_ids = {row["sentence_id"] for row in preregistration["selected_cases"]}
    if set(source_by_id) != selected_ids:
        raise ValueError("source snapshot does not exactly match selected IDs")
    cases = []
    for selected in preregistration["selected_cases"]:
        source_row = source_by_id[selected["sentence_id"]]
        cases.append(
            {
                "id": selected["id"],
                "language": selected["language"],
                "text": source_row["text"],
                "proposed_reflection_type": "procedural",
                "expected_admission": selected["expected_admission"],
                "gold_reason": selected["gold_reason"],
                "source_provenance": {
                    key: source_row[key]
                    for key in (
                        "sentence_id",
                        "owner",
                        "license",
                        "is_unapproved",
                        "api_url",
                        "sentence_url",
                    )
                },
            }
        )
    return {
        "schema": "uruha_reflection_admission_nearmiss_development_dataset_v6",
        "created_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "evidence_role": "development_only_not_holdout",
        "source": source["source"],
        "reflection_admission_labels_provided_by_source": False,
        "constructor_ai_assistance_used": True,
        "independent_human_label_validation": False,
        "evaluated_qwen_model_inference_used": False,
        "proposal_under_review": preregistration["proposal_under_review"],
        "case_count": len(cases),
        "cases": cases,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f"refusing to overwrite dataset: {args.output}")
    dataset = build_dataset(_load(PREREG_PATH), _load(SOURCE_PATH))
    args.output.write_text(
        json.dumps(dataset, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(args.output)


if __name__ == "__main__":
    main()
