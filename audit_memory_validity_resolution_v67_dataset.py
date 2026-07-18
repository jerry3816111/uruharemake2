#!/usr/bin/env python3
"""Audit fresh V67 memory-validity cases before implementation."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PREREG_PATH = ROOT / "configs/memory_validity_resolution_v67_preregistration.json"
DATASET_PATH = ROOT / "datasets/memory_validity_resolution_v67.json"
REPORT_PATH = ROOT / "reports/memory_validity_resolution_v67_dataset_audit.json"
CLOSURE_PATH = ROOT / "configs/memory_validity_resolution_v67_dataset_closure.json"
EXCLUDED = {path.resolve() for path in (PREREG_PATH, DATASET_PATH, REPORT_PATH, CLOSURE_PATH)}
VALIDITY_FIELDS = {
    "subject",
    "predicate",
    "fact_cardinality",
    "memory_state",
    "valid_from",
    "valid_until",
    "supersedes_ids",
    "condition_tags",
}
TEXT_KEYS = {"query_text", "user_input", "question", "prompt", "utterance", "query"}


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _normalize(value):
    return re.sub(r"[^0-9a-zぁ-んァ-ヶ一-龠]", "", str(value or "").lower())


def _parse_iso(value):
    try:
        return dt.datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


def _collect(value, source, rows):
    if isinstance(value, dict):
        for key, child in value.items():
            if key in TEXT_KEYS and isinstance(child, str) and len(_normalize(child)) >= 8:
                rows.append({"text": child, "source": source})
            _collect(child, source, rows)
    elif isinstance(value, list):
        for child in value:
            _collect(child, source, rows)


def _prior_texts():
    rows = []
    for directory in ("datasets", "configs", "reports"):
        for path in sorted((ROOT / directory).rglob("*.json")):
            if path.resolve() in EXCLUDED:
                continue
            try:
                _collect(_load(path), str(path.relative_to(ROOT)), rows)
            except (OSError, json.JSONDecodeError):
                continue
        for path in sorted((ROOT / directory).rglob("*.jsonl")):
            if path.resolve() in EXCLUDED:
                continue
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except OSError:
                continue
            for line in lines:
                try:
                    _collect(json.loads(line), str(path.relative_to(ROOT)), rows)
                except json.JSONDecodeError:
                    continue
    return rows


def _case_failures(case):
    failures = []
    if set(case) != {"id", "scenario_family", "query_context", "working_memory_limit", "candidates", "expected"}:
        failures.append("case_fields")
    context = case.get("query_context") or {}
    if set(context) != {"query_text", "reference_time", "condition_tags"}:
        failures.append("query_context_fields")
    if _parse_iso(context.get("reference_time")) is None:
        failures.append("reference_time")
    if not isinstance(context.get("condition_tags"), list):
        failures.append("query_condition_tags")
    if case.get("working_memory_limit") != 5:
        failures.append("working_memory_limit")

    candidates = case.get("candidates") or []
    ids = [row.get("memory_id") for row in candidates]
    if not candidates or not all(ids) or len(ids) != len(set(ids)):
        failures.append("candidate_ids")
    for row in candidates:
        if set(row) != {"memory_id", "source", "text", "distance", "metadata"}:
            failures.append("candidate_fields")
            continue
        metadata = row.get("metadata")
        if not isinstance(metadata, dict):
            failures.append("candidate_metadata")
            continue
        state = metadata.get("memory_state", "active")
        if state not in {"active", "retracted"}:
            failures.append("memory_state")
        cardinality = metadata.get("fact_cardinality")
        if cardinality is not None and cardinality not in {"single", "multi"}:
            failures.append("fact_cardinality")
        for key in ("valid_from", "valid_until"):
            if key in metadata and _parse_iso(metadata[key]) is None:
                failures.append(key)
        for key in ("supersedes_ids", "condition_tags"):
            if key in metadata and not isinstance(metadata[key], list):
                failures.append(key)
        if any(key in metadata for key in VALIDITY_FIELDS):
            if not metadata.get("subject") or not metadata.get("predicate"):
                failures.append("typed_identity")
        if not set(metadata.get("supersedes_ids") or []).issubset(set(ids)):
            failures.append("supersedes_reference")

    expected = case.get("expected") or {}
    if set(expected) != {"eligible_ids", "historical_ids", "inapplicable_ids", "working_memory_ids"}:
        failures.append("expected_fields")
    partitions = [set(expected.get(key) or []) for key in ("eligible_ids", "historical_ids", "inapplicable_ids")]
    if any(partitions[left] & partitions[right] for left in range(3) for right in range(left + 1, 3)):
        failures.append("partition_overlap")
    if set().union(*partitions) != set(ids):
        failures.append("partition_coverage")
    if set(expected.get("working_memory_ids") or []) != partitions[0]:
        failures.append("working_memory_ids")
    return sorted(set(failures))


def build_audit():
    prereg = _load(PREREG_PATH)
    dataset = _load(DATASET_PATH)
    cases = dataset.get("cases") or []
    expected_shape = prereg["dataset"]
    ids = [case.get("id") for case in cases]
    inputs = [_normalize((case.get("query_context") or {}).get("query_text")) for case in cases]
    families = Counter(case.get("scenario_family") for case in cases)
    failures = {case.get("id", "missing"): _case_failures(case) for case in cases}
    failures = {key: value for key, value in failures.items() if value}

    threshold = 0.92
    internal_near = []
    for left in range(len(cases)):
        for right in range(left + 1, len(cases)):
            ratio = SequenceMatcher(None, inputs[left], inputs[right]).ratio()
            if ratio >= threshold:
                internal_near.append({"left": ids[left], "right": ids[right], "similarity": round(ratio, 4)})

    prior = _prior_texts()
    normalized_prior = [(_normalize(row["text"]), row) for row in prior if _normalize(row["text"])]
    exact_prior = []
    near_prior = []
    for case, value in zip(cases, inputs):
        for old_value, old in normalized_prior:
            if value == old_value:
                exact_prior.append({"case_id": case["id"], "source": old["source"]})
                continue
            ratio = SequenceMatcher(None, value, old_value).ratio()
            if ratio >= threshold:
                near_prior.append({"case_id": case["id"], "source": old["source"], "similarity": round(ratio, 4)})

    checks = {
        "schema_matches": dataset.get("schema") == "uruha_memory_validity_resolution_v67",
        "frozen_before_audit_harness_or_implementation": dataset.get("status") == "frozen_before_audit_harness_or_candidate_implementation",
        "official_benchmark_items_false": dataset.get("official_benchmark_items") is False,
        "benchmark_answers_present_false": dataset.get("benchmark_answers_present") is False,
        "case_count_exact": len(cases) == expected_shape["case_count"],
        "family_set_exact": set(families) == set(expected_shape["scenario_families"]),
        "cases_per_family_exact": all(families.get(name) == expected_shape["cases_per_family"] for name in expected_shape["scenario_families"]),
        "case_ids_unique": len(ids) == len(set(ids)) and all(ids),
        "query_texts_unique": len(inputs) == len(set(inputs)) and all(inputs),
        "case_shapes_references_and_partitions_valid": not failures,
        "internal_near_duplicate_count_zero": not internal_near,
        "exact_prior_text_overlap_count_zero": not exact_prior,
        "external_near_duplicate_count_zero": not near_prior,
    }
    return {
        "schema": "uruha_memory_validity_resolution_dataset_audit_v67",
        "passed": all(checks.values()),
        "bindings": {
            "preregistration_path": str(PREREG_PATH.relative_to(ROOT)),
            "preregistration_sha256": _sha256(PREREG_PATH),
            "dataset_path": str(DATASET_PATH.relative_to(ROOT)),
            "dataset_sha256": _sha256(DATASET_PATH),
        },
        "counts": {
            "case_count": len(cases),
            "scenario_family_count": len(families),
            "candidate_count": sum(len(case.get("candidates") or []) for case in cases),
            "prior_text_count_scanned": len(prior),
            "internal_near_duplicate_count": len(internal_near),
            "exact_prior_text_overlap_count": len(exact_prior),
            "external_near_duplicate_count": len(near_prior),
        },
        "family_counts": dict(sorted(families.items())),
        "checks": checks,
        "failures": {
            "case_failures": failures,
            "internal_near_duplicates": internal_near,
            "exact_prior_text_overlaps": exact_prior,
            "external_near_duplicates": near_prior,
        },
        "evidence_boundary": "This audit proves only dataset structure, referential integrity, exact partition coverage, timestamp syntax, family balance, and no detected text overlap in scanned artifacts. It contains no resolver implementation or capability result.",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    audit = build_audit()
    if args.write:
        REPORT_PATH.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        closure = {
            "schema": "uruha_memory_validity_resolution_dataset_closure_v67",
            "status": "frozen_after_construction_audit_before_harness_or_candidate_implementation",
            "audit_passed": audit["passed"],
            "frozen_artifacts": {
                "preregistration": audit["bindings"]["preregistration_sha256"],
                "dataset": audit["bindings"]["dataset_sha256"],
                "audit": _sha256(REPORT_PATH),
            },
            "authorizations": {
                "candidate_implementation": audit["passed"],
                "pilot_execution": False,
                "runtime_change": False,
            },
        }
        CLOSURE_PATH.write_text(json.dumps(closure, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(audit, ensure_ascii=False, indent=2))
    raise SystemExit(0 if audit["passed"] else 1)


if __name__ == "__main__":
    main()
