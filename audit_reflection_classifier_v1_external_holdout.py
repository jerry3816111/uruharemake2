#!/usr/bin/env python3
"""Audit source provenance and development separation without classifier inference."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

from build_reflection_classifier_v1_external_holdout import (
    OUTPUT_PATH,
    PREREG_PATH,
    ROOT,
    SOURCE_PATH,
)


DEVELOPMENT_PATH = ROOT / "datasets" / "reflection_classifier_v1_development.json"
AUDIT_JSON_PATH = ROOT / "reports" / "reflection_classifier_v1_external_holdout_audit.json"
AUDIT_MD_PATH = ROOT / "reports" / "reflection_classifier_v1_external_holdout_audit.md"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _normalize(text: str):
    return re.sub(r"\s+", " ", text.strip()).casefold()


def audit():
    preregistration = _load(PREREG_PATH)
    snapshot = _load(SOURCE_PATH)
    dataset = _load(OUTPUT_PATH)
    development = _load(DEVELOPMENT_PATH)

    selected = preregistration["selected_cases"]
    selected_ids = [case["sentence_id"] for case in selected]
    source_ids = [item["sentence_id"] for item in snapshot["items"]]
    dataset_ids = [
        case["source_provenance"]["sentence_id"] for case in dataset["cases"]
    ]
    dev_texts = {_normalize(case["text"]) for case in development["cases"]}
    overlaps = [
        case["id"] for case in dataset["cases"] if _normalize(case["text"]) in dev_texts
    ]
    source_by_id = {item["sentence_id"]: item for item in snapshot["items"]}
    exact_source_mismatches = [
        case["id"]
        for case in dataset["cases"]
        if case["text"]
        != source_by_id[case["source_provenance"]["sentence_id"]]["text"]
    ]
    class_counts = Counter(case["expected_type"] for case in dataset["cases"])
    language_counts = Counter(case["language"] for case in dataset["cases"])
    licenses = Counter(item["license"] for item in snapshot["items"])

    checks = {
        "selected_source_and_dataset_ids_match_in_order": selected_ids
        == source_ids
        == dataset_ids,
        "case_ids_are_unique": len({case["id"] for case in dataset["cases"]})
        == len(dataset["cases"]),
        "sentence_ids_are_unique": len(set(dataset_ids)) == len(dataset_ids),
        "case_count_matches_preregistration": len(dataset["cases"])
        == preregistration["fixed_counts"]["case_count"],
        "class_balance_matches_preregistration": dict(class_counts)
        == preregistration["fixed_counts"]["per_class"],
        "language_balance_matches_preregistration": dict(language_counts)
        == preregistration["fixed_counts"]["per_language"],
        "all_source_rows_approved": all(
            not item["is_unapproved"] for item in snapshot["items"]
        ),
        "all_source_rows_have_provenance": all(
            item["text"] and "owner" in item and item["license"]
            for item in snapshot["items"]
        ),
        "dataset_text_is_exact_source_text": not exact_source_mismatches,
        "no_exact_development_text_overlap": not overlaps,
        "construction_used_no_classifier_or_model": not snapshot[
            "classifier_or_model_inference_used"
        ]
        and not dataset["construction"]["classifier_or_model_inference_used"],
    }
    failed = [name for name, passed in checks.items() if not passed]
    return {
        "schema": "uruha_reflection_classifier_external_holdout_audit_v1",
        "passed": not failed,
        "failed_checks": failed,
        "checks": checks,
        "case_count": len(dataset["cases"]),
        "class_counts": dict(sorted(class_counts.items())),
        "language_counts": dict(sorted(language_counts.items())),
        "license_counts": dict(sorted(licenses.items())),
        "exact_development_text_overlap_count": len(overlaps),
        "exact_development_text_overlap_case_ids": overlaps,
        "exact_source_text_mismatch_count": len(exact_source_mismatches),
        "exact_source_text_mismatch_case_ids": exact_source_mismatches,
        "label_provenance": "Research operational labels, not Tatoeba labels.",
        "base_model_pretraining_exclusion_guaranteed": False,
        "classifier_or_model_inference_performed": False,
        "evaluation_authorized": not failed,
        "runtime_change_authorized": False,
        "broad_human_likeness_claim_authorized": False,
    }


def _markdown(report: dict):
    status = "PASS" if report["passed"] else "FAIL"
    rows = "\n".join(
        f"- {name}: {'PASS' if passed else 'FAIL'}"
        for name, passed in report["checks"].items()
    )
    return f"""# Reflection Classifier V1 External Holdout Construction Audit

Status: **{status}**

- Cases: {report['case_count']}
- Classes: {json.dumps(report['class_counts'], ensure_ascii=False)}
- Languages: {json.dumps(report['language_counts'], ensure_ascii=False)}
- Licenses: {json.dumps(report['license_counts'], ensure_ascii=False)}
- Exact authored-development overlap: {report['exact_development_text_overlap_count']}
- Classifier/model calls during construction: 0

## Checks

{rows}

## Evidence boundary

Tatoeba supplies exact sentence text and source metadata only. Reflection labels are project operational labels. A construction pass authorizes a separately frozen matched evaluation only; it is not a classifier result and does not authorize runtime memory writes or broad human-likeness claims.
"""


def main():
    report = audit()
    AUDIT_JSON_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    AUDIT_MD_PATH.write_text(_markdown(report), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
