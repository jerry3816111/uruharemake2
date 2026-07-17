#!/usr/bin/env python3
"""Audit V6 admission data provenance and overlap before model inference."""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from collections import Counter
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
DATASET_PATH = ROOT / "datasets" / "reflection_admission_v6_nearmiss_development.json"
JSON_OUTPUT = ROOT / "reports" / "reflection_admission_v6_nearmiss_audit.json"
MD_OUTPUT = ROOT / "reports" / "reflection_admission_v6_nearmiss_audit.md"
TZ = ZoneInfo("Asia/Tokyo")


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _normalize(text):
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", text)).strip().casefold()


def _walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _prior_reflection_evidence():
    excluded = {SOURCE_PATH.resolve(), DATASET_PATH.resolve()}
    sentence_ids = set()
    normalized_texts = set()
    paths = []
    for path in sorted((ROOT / "datasets").rglob("*reflection*.json")):
        if path.resolve() in excluded:
            continue
        payload = _load(path)
        paths.append(str(path.relative_to(ROOT)))
        for row in _walk(payload):
            sentence_id = row.get("sentence_id")
            if isinstance(sentence_id, int):
                sentence_ids.add(sentence_id)
            text = row.get("text")
            if isinstance(text, str) and text.strip():
                normalized_texts.add(_normalize(text))
    return sentence_ids, normalized_texts, paths


def audit():
    prereg = _load(PREREG_PATH)
    source = _load(SOURCE_PATH)
    dataset = _load(DATASET_PATH)
    selected = prereg["selected_cases"]
    source_by_id = {row["sentence_id"]: row for row in source["items"]}
    dataset_by_id = {row["id"]: row for row in dataset["cases"]}
    prior_ids, prior_texts, prior_paths = _prior_reflection_evidence()

    selected_sentence_ids = [row["sentence_id"] for row in selected]
    duplicate_sentence_count = len(selected_sentence_ids) - len(
        set(selected_sentence_ids)
    )
    source_mismatch_ids = []
    label_mismatch_ids = []
    unapproved_ids = []
    missing_license_ids = []
    for selected_row in selected:
        source_row = source_by_id.get(selected_row["sentence_id"])
        dataset_row = dataset_by_id.get(selected_row["id"])
        if source_row is None or dataset_row is None:
            source_mismatch_ids.append(selected_row["id"])
            continue
        if (
            source_row["language"] != selected_row["language"]
            or dataset_row["language"] != selected_row["language"]
            or dataset_row["text"] != source_row["text"]
            or dataset_row["source_provenance"]["sentence_id"]
            != selected_row["sentence_id"]
        ):
            source_mismatch_ids.append(selected_row["id"])
        if (
            dataset_row["expected_admission"] != selected_row["expected_admission"]
            or dataset_row["gold_reason"] != selected_row["gold_reason"]
            or dataset_row["proposed_reflection_type"] != "procedural"
        ):
            label_mismatch_ids.append(selected_row["id"])
        if source_row["is_unapproved"]:
            unapproved_ids.append(selected_row["id"])
        if not source_row["license"]:
            missing_license_ids.append(selected_row["id"])

    overlap_ids = sorted(set(selected_sentence_ids) & prior_ids)
    overlap_text_ids = sorted(
        row["id"]
        for row in dataset["cases"]
        if _normalize(row["text"]) in prior_texts
    )
    counts = Counter(row["expected_admission"] for row in dataset["cases"])
    language_counts = Counter(row["language"] for row in dataset["cases"])
    gates = prereg["construction_gates"]
    checks = {
        "exact_case_count": len(dataset["cases"]) == gates["exact_case_count"],
        "exact_admit_count": counts["admit"] == gates["exact_admit_count"],
        "exact_reject_count": counts["reject"] == gates["exact_reject_count"],
        "duplicate_sentence_id_count_max": duplicate_sentence_count
        <= gates["duplicate_sentence_id_count_max"],
        "existing_reflection_sentence_id_overlap_max": len(overlap_ids)
        <= gates["existing_reflection_sentence_id_overlap_max"],
        "existing_reflection_normalized_text_overlap_max": len(overlap_text_ids)
        <= gates["existing_reflection_normalized_text_overlap_max"],
        "source_text_mismatch_max": len(source_mismatch_ids)
        <= gates["source_text_mismatch_max"],
        "unapproved_source_count_max": len(unapproved_ids)
        <= gates["unapproved_source_count_max"],
        "missing_license_count_max": len(missing_license_ids)
        <= gates["missing_license_count_max"],
        "evaluated_qwen_model_calls_exact": 0
        == gates["evaluated_qwen_model_calls_exact"],
        "label_mismatch_count_exact": len(label_mismatch_ids) == 0,
        "source_selection_exact": set(source_by_id) == set(selected_sentence_ids),
        "language_distribution_exact": dict(sorted(language_counts.items()))
        == dict(sorted(prereg["frozen_distribution"]["language_counts"].items())),
    }
    return {
        "schema": "uruha_reflection_admission_nearmiss_audit_v6",
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "dataset_role": dataset["evidence_role"],
        "case_count": len(dataset["cases"]),
        "admission_counts": dict(sorted(counts.items())),
        "language_counts": dict(sorted(language_counts.items())),
        "prior_reflection_paths_checked": prior_paths,
        "duplicate_sentence_id_count": duplicate_sentence_count,
        "existing_reflection_sentence_id_overlap": overlap_ids,
        "existing_reflection_normalized_text_overlap_case_ids": overlap_text_ids,
        "source_text_mismatch_case_ids": source_mismatch_ids,
        "label_mismatch_case_ids": label_mismatch_ids,
        "unapproved_source_case_ids": unapproved_ids,
        "missing_license_case_ids": missing_license_ids,
        "evaluated_qwen_model_calls": 0,
        "gate_checks": checks,
        "all_gates_pass": all(checks.values()),
    }


def _markdown(report):
    return "\n".join(
        [
            "# Reflection Admission V6 Near-Miss Data Audit",
            "",
            f"- Cases: {report['case_count']}",
            f"- Admission balance: {report['admission_counts']}",
            f"- Languages: {report['language_counts']}",
            f"- Prior sentence-ID overlap: {len(report['existing_reflection_sentence_id_overlap'])}",
            f"- Prior normalized-text overlap: {len(report['existing_reflection_normalized_text_overlap_case_ids'])}",
            f"- Source mismatches: {len(report['source_text_mismatch_case_ids'])}",
            f"- Evaluated Qwen calls: {report['evaluated_qwen_model_calls']}",
            f"- All construction gates: **{'PASS' if report['all_gates_pass'] else 'FAIL'}**",
            "",
            "Tatoeba supplies sentence text and license metadata, not reflection-admission labels.",
            "",
        ]
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-output", type=Path, default=JSON_OUTPUT)
    parser.add_argument("--md-output", type=Path, default=MD_OUTPUT)
    args = parser.parse_args()
    report = audit()
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    args.md_output.write_text(_markdown(report), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
