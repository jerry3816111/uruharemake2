#!/usr/bin/env python3
"""Audit fresh V68 profile assertion-boundary cases before implementation."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PREREG_PATH = ROOT / "configs/profile_assertion_boundary_v68_preregistration.json"
DATASET_PATH = ROOT / "datasets/profile_assertion_boundary_v68.json"
REPORT_PATH = ROOT / "reports/profile_assertion_boundary_v68_dataset_audit.json"
CLOSURE_PATH = ROOT / "configs/profile_assertion_boundary_v68_dataset_closure.json"
EXCLUDED = {path.resolve() for path in (PREREG_PATH, DATASET_PATH, REPORT_PATH, CLOSURE_PATH)}
TEXT_KEYS = {"utterance", "user_input", "question", "prompt", "query_text"}


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _normalize(value):
    return re.sub(r"[^0-9a-zぁ-んァ-ヶ一-龠]", "", str(value or "").lower())


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
        for suffix in ("*.json", "*.jsonl"):
            for path in sorted((ROOT / directory).rglob(suffix)):
                if path.resolve() in EXCLUDED:
                    continue
                try:
                    values = [_load(path)] if suffix == "*.json" else [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
                except (OSError, json.JSONDecodeError):
                    continue
                for value in values:
                    _collect(value, str(path.relative_to(ROOT)), rows)
    return rows


def _case_failures(case):
    failures = []
    if set(case) != {"id", "scenario_family", "language", "utterance", "expected_facts"}:
        failures.append("case_fields")
    if case.get("language") not in {"en", "zh", "ja"}:
        failures.append("language")
    if not isinstance(case.get("utterance"), str) or not case["utterance"].strip():
        failures.append("utterance")
    facts = case.get("expected_facts")
    if not isinstance(facts, list):
        failures.append("expected_facts")
        return failures
    normalized = []
    for fact in facts:
        if set(fact) != {"fact_type", "value"} or fact.get("fact_type") not in {"name", "favorite", "like", "dislike"} or not fact.get("value"):
            failures.append("fact_shape")
            continue
        normalized.append((fact["fact_type"], str(fact["value"]).casefold()))
    if len(normalized) != len(set(normalized)):
        failures.append("duplicate_fact")
    return sorted(set(failures))


def build_audit():
    prereg = _load(PREREG_PATH)
    dataset = _load(DATASET_PATH)
    cases = dataset.get("cases") or []
    shape = prereg["dataset"]
    ids = [case.get("id") for case in cases]
    utterances = [_normalize(case.get("utterance")) for case in cases]
    families = Counter(case.get("scenario_family") for case in cases)
    languages = Counter(case.get("language") for case in cases)
    failures = {case.get("id", "missing"): _case_failures(case) for case in cases}
    failures = {key: value for key, value in failures.items() if value}

    threshold = 0.92
    internal_near = []
    for left in range(len(cases)):
        for right in range(left + 1, len(cases)):
            ratio = SequenceMatcher(None, utterances[left], utterances[right]).ratio()
            if ratio >= threshold:
                internal_near.append({"left": ids[left], "right": ids[right], "similarity": round(ratio, 4)})

    prior = _prior_texts()
    normalized_prior = [(_normalize(row["text"]), row) for row in prior if _normalize(row["text"])]
    exact_prior = []
    near_prior = []
    for case, value in zip(cases, utterances):
        for old_value, old in normalized_prior:
            if value == old_value:
                exact_prior.append({"case_id": case["id"], "source": old["source"]})
            elif SequenceMatcher(None, value, old_value).ratio() >= threshold:
                near_prior.append({"case_id": case["id"], "source": old["source"]})

    positive = sum(bool(case["expected_facts"]) for case in cases)
    checks = {
        "schema_matches": dataset.get("schema") == "uruha_profile_assertion_boundary_v68",
        "frozen_before_audit_harness_or_implementation": dataset.get("status") == "frozen_before_audit_harness_or_candidate_implementation",
        "official_benchmark_items_false": dataset.get("official_benchmark_items") is False,
        "benchmark_answers_present_false": dataset.get("benchmark_answers_present") is False,
        "case_count_exact": len(cases) == shape["case_count"],
        "family_set_exact": set(families) == set(shape["scenario_families"]),
        "cases_per_family_exact": all(families.get(name) == shape["cases_per_family"] for name in shape["scenario_families"]),
        "positive_and_non_assertion_counts_exact": positive == shape["positive_assertion_case_count"] and len(cases) - positive == shape["non_assertion_case_count"],
        "all_languages_present": set(languages) == set(shape["languages"]),
        "case_ids_unique": len(ids) == len(set(ids)) and all(ids),
        "utterances_unique": len(utterances) == len(set(utterances)) and all(utterances),
        "case_shapes_valid": not failures,
        "internal_near_duplicate_count_zero": not internal_near,
        "exact_prior_text_overlap_count_zero": not exact_prior,
        "external_near_duplicate_count_zero": not near_prior,
    }
    return {
        "schema": "uruha_profile_assertion_boundary_dataset_audit_v68",
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
            "positive_assertion_count": positive,
            "non_assertion_count": len(cases) - positive,
            "prior_text_count_scanned": len(prior),
            "internal_near_duplicate_count": len(internal_near),
            "exact_prior_text_overlap_count": len(exact_prior),
            "external_near_duplicate_count": len(near_prior),
        },
        "family_counts": dict(sorted(families.items())),
        "language_counts": dict(sorted(languages.items())),
        "checks": checks,
        "failures": {"case_failures": failures, "internal_near_duplicates": internal_near, "exact_prior_text_overlaps": exact_prior, "external_near_duplicates": near_prior},
        "evidence_boundary": "This audit proves only case structure, family balance, multilingual presence, expected-fact shape, and no detected overlap in scanned artifacts. It contains no guard implementation or capability result."
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    audit = build_audit()
    if args.write:
        REPORT_PATH.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        closure = {
            "schema": "uruha_profile_assertion_boundary_dataset_closure_v68",
            "status": "frozen_after_construction_audit_before_harness_or_candidate_implementation",
            "audit_passed": audit["passed"],
            "frozen_artifacts": {
                "preregistration": audit["bindings"]["preregistration_sha256"],
                "dataset": audit["bindings"]["dataset_sha256"],
                "audit": _sha256(REPORT_PATH)
            },
            "authorizations": {"candidate_implementation": audit["passed"], "pilot_execution": False, "runtime_change": False}
        }
        CLOSURE_PATH.write_text(json.dumps(closure, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(audit, ensure_ascii=False, indent=2))
    raise SystemExit(0 if audit["passed"] else 1)


if __name__ == "__main__":
    main()
