#!/usr/bin/env python3
"""Audit V4 source provenance and separation without classifier inference."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

from build_reflection_hybrid_classifier_v4_independent_holdout import (
    OUTPUT_PATH,
    PREREG_PATH,
    ROOT,
    SOURCE_PATH,
)


PRIOR_SOURCE_PATH = (
    ROOT / "datasets" / "sources" / "tatoeba_reflection_classifier_v1_selected.json"
)
EXISTING_REFLECTION_DATASETS = (
    ROOT / "datasets" / "reflection_causal_pilot_v1.json",
    ROOT / "datasets" / "reflection_classifier_v1_development.json",
    ROOT / "datasets" / "reflection_classifier_v1_external_holdout.json",
    ROOT / "datasets" / "reflection_layer_audit_v1_calibration.json",
    ROOT / "datasets" / "typed_reflection_v3_development_pilot.json",
    ROOT / "datasets" / "typed_reflection_v4_development_pilot.json",
)
AUDIT_JSON_PATH = (
    ROOT / "reports" / "reflection_hybrid_classifier_v4_independent_holdout_audit.json"
)
AUDIT_MD_PATH = (
    ROOT / "reports" / "reflection_hybrid_classifier_v4_independent_holdout_audit.md"
)


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _normalize(text: str):
    return re.sub(r"\s+", " ", text.strip()).casefold()


def _case_texts(payload: dict):
    return {
        _normalize(case["text"])
        for case in payload.get("cases", [])
        if isinstance(case, dict) and isinstance(case.get("text"), str)
    }


def audit():
    preregistration = _load(PREREG_PATH)
    snapshot = _load(SOURCE_PATH)
    dataset = _load(OUTPUT_PATH)
    prior_source = _load(PRIOR_SOURCE_PATH)

    selected = preregistration["selected_cases"]
    selected_ids = [case["sentence_id"] for case in selected]
    source_ids = [item["sentence_id"] for item in snapshot["items"]]
    dataset_ids = [
        case["source_provenance"]["sentence_id"] for case in dataset["cases"]
    ]
    prior_source_ids = {item["sentence_id"] for item in prior_source["items"]}
    prior_id_overlaps = sorted(set(dataset_ids) & prior_source_ids)

    existing_texts = set()
    for path in EXISTING_REFLECTION_DATASETS:
        existing_texts.update(_case_texts(_load(path)))
    text_overlaps = [
        case["id"]
        for case in dataset["cases"]
        if _normalize(case["text"]) in existing_texts
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
    expected_license = preregistration["external_source"]["license_expected"]

    checks = {
        "selected_source_and_dataset_ids_match_in_order": (
            selected_ids == source_ids == dataset_ids
        ),
        "case_ids_are_unique": len({case["id"] for case in dataset["cases"]})
        == len(dataset["cases"]),
        "sentence_ids_are_unique": len(set(dataset_ids)) == len(dataset_ids),
        "no_prior_tatoeba_sentence_id_overlap": not prior_id_overlaps,
        "no_existing_reflection_text_overlap": not text_overlaps,
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
        "all_source_licenses_match_preregistration": licenses
        == Counter({expected_license: len(snapshot["items"])}),
        "dataset_text_is_exact_source_text": not exact_source_mismatches,
        "construction_used_no_evaluated_qwen_inference": not snapshot[
            "evaluated_qwen_model_inference_used"
        ]
        and not dataset["construction"]["evaluated_qwen_model_inference_used"],
    }
    failed = [name for name, passed in checks.items() if not passed]
    return {
        "schema": "uruha_reflection_hybrid_classifier_independent_holdout_audit_v4",
        "passed": not failed,
        "failed_checks": failed,
        "checks": checks,
        "case_count": len(dataset["cases"]),
        "class_counts": dict(sorted(class_counts.items())),
        "language_counts": dict(sorted(language_counts.items())),
        "license_counts": dict(sorted(licenses.items())),
        "prior_tatoeba_sentence_id_overlap_count": len(prior_id_overlaps),
        "prior_tatoeba_sentence_id_overlaps": prior_id_overlaps,
        "existing_reflection_text_overlap_count": len(text_overlaps),
        "existing_reflection_text_overlap_case_ids": text_overlaps,
        "exact_source_text_mismatch_count": len(exact_source_mismatches),
        "exact_source_text_mismatch_case_ids": exact_source_mismatches,
        "constructor_ai_assistance_used": True,
        "evaluated_qwen_model_inference_performed": False,
        "label_provenance": "Project operational labels, not Tatoeba labels.",
        "base_model_pretraining_exclusion_guaranteed": False,
        "evaluation_harness_freeze_authorized": not failed,
        "runtime_change_authorized": False,
        "broad_human_likeness_claim_authorized": False,
    }


def _markdown(report: dict):
    status = "PASS" if report["passed"] else "FAIL"
    rows = "\n".join(
        f"- {name}: {'PASS' if passed else 'FAIL'}"
        for name, passed in report["checks"].items()
    )
    return f"""# Reflection Hybrid Classifier V4 Holdout Construction Audit

Status: **{status}**

- Cases: {report['case_count']}
- Classes: {json.dumps(report['class_counts'], ensure_ascii=False)}
- Languages: {json.dumps(report['language_counts'], ensure_ascii=False)}
- Prior Tatoeba ID overlap: {report['prior_tatoeba_sentence_id_overlap_count']}
- Existing reflection text overlap: {report['existing_reflection_text_overlap_count']}
- Evaluated Qwen calls during construction: 0

## Checks

{rows}

## Evidence boundary

Tatoeba supplies exact sentence text and source metadata. Codex assisted selection and project operational labeling; Tatoeba did not supply the labels. A construction pass authorizes only a separately frozen matched evaluation harness. It is not a model result and does not authorize runtime memory writes or broad human-likeness claims.
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
