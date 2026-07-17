#!/usr/bin/env python3
"""Build the source-separated reflection classifier holdout from a frozen snapshot."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PREREG_PATH = (
    ROOT
    / "configs"
    / "reflection_classifier_v1_external_holdout_construction_preregistration.json"
)
SOURCE_PATH = (
    ROOT
    / "datasets"
    / "sources"
    / "tatoeba_reflection_classifier_v1_selected.json"
)
OUTPUT_PATH = ROOT / "datasets" / "reflection_classifier_v1_external_holdout.json"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def build():
    preregistration = _load(PREREG_PATH)
    snapshot = _load(SOURCE_PATH)
    selected = preregistration["selected_cases"]
    source_by_id = {item["sentence_id"]: item for item in snapshot["items"]}
    selected_ids = [case["sentence_id"] for case in selected]
    if set(source_by_id) != set(selected_ids) or len(source_by_id) != len(selected_ids):
        raise ValueError("Tatoeba snapshot does not exactly match preregistered IDs")

    cases = []
    for frozen in selected:
        source = source_by_id[frozen["sentence_id"]]
        if source["language"] != frozen["language"]:
            raise ValueError(f"language drift: {frozen['id']}")
        cases.append(
            {
                "id": frozen["id"],
                "text": source["text"],
                "expected_type": frozen["expected_type"],
                "language": source["language"],
                "source_provenance": {
                    "source_type": "external_exact",
                    "corpus": "Tatoeba",
                    "sentence_id": source["sentence_id"],
                    "owner": source["owner"],
                    "license": source["license"],
                    "api_url": source["api_url"],
                    "sentence_url": source["sentence_url"],
                    "official_reflection_label": False,
                },
            }
        )

    return {
        "schema": "uruha_reflection_classifier_external_holdout_v1",
        "evidence_status": "built_before_legacy_or_candidate_inference",
        "source_snapshot": str(SOURCE_PATH.relative_to(ROOT)),
        "construction": {
            "sentence_text_modified": False,
            "sentence_text_model_generated": False,
            "reflection_labels_official": False,
            "reflection_labels_research_operational": True,
            "classifier_or_model_inference_used": False,
            "base_model_pretraining_exclusion_guaranteed": False,
        },
        "case_count": len(cases),
        "class_counts": dict(sorted(Counter(c["expected_type"] for c in cases).items())),
        "language_counts": dict(sorted(Counter(c["language"] for c in cases).items())),
        "cases": cases,
    }


def main():
    payload = build()
    OUTPUT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(OUTPUT_PATH)


if __name__ == "__main__":
    main()
