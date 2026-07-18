#!/usr/bin/env python3
"""Audit the fresh V70 answer-level profile holdout before implementation."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PREREG_PATH = ROOT / "configs/profile_answer_generalization_v70_preregistration.json"
DATASET_PATH = ROOT / "datasets/profile_answer_generalization_v70.json"
REPORT_PATH = ROOT / "reports/profile_answer_generalization_v70_dataset_audit.json"
CLOSURE_PATH = ROOT / "configs/profile_answer_generalization_v70_dataset_closure.json"
EXCLUDED = {path.resolve() for path in (PREREG_PATH, DATASET_PATH, REPORT_PATH, CLOSURE_PATH)}


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _normalize(value):
    return re.sub(r"[^0-9a-zぁ-んァ-ヶ一-龠]", "", str(value or "").casefold())


def _prior_inputs():
    rows = []
    for path in sorted((ROOT / "datasets").rglob("*.json")):
        if path.resolve() in EXCLUDED:
            continue
        try:
            stack = [_load(path)]
        except (OSError, json.JSONDecodeError):
            continue
        while stack:
            value = stack.pop()
            if isinstance(value, dict):
                for key, child in value.items():
                    if key in {"utterance", "user_input", "query_text", "input"} and isinstance(child, str):
                        rows.append((child, str(path.relative_to(ROOT))))
                    stack.append(child)
            elif isinstance(value, list):
                stack.extend(value)
    return rows


def _case_failures(case):
    failures = []
    if set(case) != {"id", "scenario_family", "user_input", "profile_history", "expected"}:
        failures.append("case_fields")
    history = case.get("profile_history") or []
    if not history or len({row.get("memory_id") for row in history}) != len(history):
        failures.append("profile_history")
    for row in history:
        if set(row) != {"memory_id", "fact_type", "value", "timestamp"}:
            failures.append("history_fields")
        if row.get("fact_type") not in {"name", "like", "dislike", "favorite"}:
            failures.append("fact_type")
    expected = case.get("expected") or {}
    if set(expected) != {"required_marker_groups", "forbidden_terms", "memory_relevant", "abstention_required"}:
        failures.append("expected_fields")
    if expected.get("abstention_required") and expected.get("memory_relevant"):
        failures.append("abstention_relevance_conflict")
    return sorted(set(failures))


def build_audit():
    prereg = _load(PREREG_PATH)
    dataset = _load(DATASET_PATH)
    cases = dataset.get("cases") or []
    shape = prereg["dataset"]
    failures = {case.get("id", "missing"): _case_failures(case) for case in cases}
    failures = {key: value for key, value in failures.items() if value}
    ids = [case.get("id") for case in cases]
    families = Counter(case.get("scenario_family") for case in cases)
    relevant = sum(bool(case["expected"]["memory_relevant"]) for case in cases)
    abstention = sum(bool(case["expected"]["abstention_required"]) for case in cases)
    current = [(case["id"], _normalize(case["user_input"])) for case in cases]
    internal_near = []
    for left in range(len(current)):
        for right in range(left + 1, len(current)):
            ratio = SequenceMatcher(None, current[left][1], current[right][1]).ratio()
            if ratio >= 0.88:
                internal_near.append({"left": current[left][0], "right": current[right][0], "similarity": round(ratio, 4)})
    prior = [(_normalize(text), source) for text, source in _prior_inputs() if _normalize(text)]
    exact_prior, near_prior = [], []
    for case_id, text in current:
        for old, source in prior:
            ratio = SequenceMatcher(None, text, old).ratio()
            if text == old:
                exact_prior.append({"case_id": case_id, "source": source})
            elif ratio >= 0.88:
                near_prior.append({"case_id": case_id, "source": source, "similarity": round(ratio, 4)})
    checks = {
        "schema_matches": dataset.get("schema") == "uruha_profile_answer_generalization_v70",
        "frozen_before_implementation": dataset.get("status") == "frozen_before_audit_harness_projection_or_formal_inference",
        "official_items_false": dataset.get("official_benchmark_items") is False,
        "benchmark_answers_false": dataset.get("benchmark_answers_present") is False,
        "case_count_exact": len(cases) == shape["case_count"],
        "families_exact": set(families) == set(shape["scenario_families"]),
        "cases_per_family_exact": all(families.get(name) == shape["cases_per_family"] for name in shape["scenario_families"]),
        "relevant_count_exact": relevant == shape["memory_relevant_case_count"],
        "irrelevant_count_exact": len(cases) - relevant == shape["memory_irrelevant_case_count"],
        "abstention_count_exact": abstention == shape["abstention_case_count"],
        "case_ids_unique": len(ids) == len(set(ids)) and all(ids),
        "case_shapes_valid": not failures,
        "internal_near_duplicate_zero": not internal_near,
        "exact_prior_overlap_zero": not exact_prior,
        "near_prior_overlap_zero": not near_prior,
    }
    return {
        "schema": "uruha_profile_answer_generalization_dataset_audit_v70",
        "passed": all(checks.values()),
        "bindings": {"preregistration_sha256": _sha256(PREREG_PATH), "dataset_sha256": _sha256(DATASET_PATH)},
        "counts": {"case_count": len(cases), "family_count": len(families), "relevant_count": relevant, "irrelevant_count": len(cases) - relevant, "abstention_count": abstention, "profile_record_count": sum(len(case["profile_history"]) for case in cases), "prior_input_count_scanned": len(prior), "internal_near_duplicate_count": len(internal_near), "exact_prior_overlap_count": len(exact_prior), "near_prior_overlap_count": len(near_prior)},
        "family_counts": dict(sorted(families.items())),
        "checks": checks,
        "failures": {"case_failures": failures, "internal_near_duplicates": internal_near, "exact_prior_overlaps": exact_prior, "near_prior_overlaps": near_prior},
        "evidence_boundary": "This audit proves only dataset shape, balance, marker separation, and no detected prior-input overlap. It contains no projector, model call, answer result, or runtime authorization."
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    audit = build_audit()
    if args.write:
        REPORT_PATH.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        closure = {"schema": "uruha_profile_answer_generalization_dataset_closure_v70", "status": "frozen_after_audit_before_harness_projection_or_formal_inference", "audit_passed": audit["passed"], "frozen_artifacts": {"preregistration": audit["bindings"]["preregistration_sha256"], "dataset": audit["bindings"]["dataset_sha256"], "audit": _sha256(REPORT_PATH)}, "authorizations": {"harness_implementation": audit["passed"], "formal_inference": False, "temporary_chroma_access": False, "runtime_change": False, "answer_use": False}}
        CLOSURE_PATH.write_text(json.dumps(closure, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(audit, ensure_ascii=False, indent=2))
    raise SystemExit(0 if audit["passed"] else 1)


if __name__ == "__main__":
    main()
