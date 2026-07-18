#!/usr/bin/env python3
"""Audit and close the fresh V71 profile relevance holdout."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PREREG_PATH = ROOT / "configs/profile_relevance_speakability_v71_preregistration.json"
DATASET_PATH = ROOT / "datasets/profile_relevance_speakability_v71.json"
REPORT_PATH = ROOT / "reports/profile_relevance_speakability_v71_dataset_audit.json"
CLOSURE_PATH = ROOT / "configs/profile_relevance_speakability_v71_dataset_closure.json"
EXCLUDED = {path.resolve() for path in (PREREG_PATH, DATASET_PATH, REPORT_PATH, CLOSURE_PATH)}
DEVELOPMENT_LITERALS = {
    "抹茶ラテ",
    "青い帽子",
    "ユウト",
    "前に好きって言ってた飲み物、何だっけ？",
    "前に好きって言ってた楽器、何だっけ？",
    "今日は何して遊ぶ？",
    "前に何て呼んでって言ったっけ？",
}


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


def _prior_profile_values():
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
                if value.get("fact_type") and isinstance(value.get("value"), str):
                    rows.append((value["value"], str(path.relative_to(ROOT))))
                stack.extend(value.values())
            elif isinstance(value, list):
                stack.extend(value)
    return rows


def _case_failures(case):
    failures = []
    if set(case) != {"id", "scenario_family", "user_input", "profile_history", "expected"}:
        failures.append("case_fields")
    history = case.get("profile_history") or []
    ids = [row.get("memory_id") for row in history]
    if not history or len(ids) != len(set(ids)) or not all(ids):
        failures.append("profile_history")
    for row in history:
        if set(row) != {"memory_id", "fact_type", "value", "timestamp", "source_utterance"}:
            failures.append("history_fields")
        if row.get("fact_type") not in {"name", "like", "dislike", "favorite"}:
            failures.append("fact_type")
        if not str(row.get("source_utterance") or "").strip():
            failures.append("source_utterance")
    expected = case.get("expected") or {}
    expected_fields = {"selected_memory_ids", "required_marker_groups", "forbidden_terms", "memory_relevant", "abstention_required"}
    if set(expected) != expected_fields:
        failures.append("expected_fields")
    selected = expected.get("selected_memory_ids") or []
    if len(selected) != len(set(selected)) or any(memory_id not in ids for memory_id in selected):
        failures.append("selected_ids")
    if bool(selected) != bool(expected.get("memory_relevant")):
        failures.append("selection_relevance_mismatch")
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
    prior_values = _prior_profile_values()
    current_values = {
        row["value"]
        for case in cases
        for row in case["profile_history"]
    }
    prior_value_overlaps = [
        {"value": value, "source": source}
        for value, source in prior_values
        if value in current_values
    ]
    serialized_dataset = DATASET_PATH.read_text(encoding="utf-8")
    development_literal_overlaps = sorted(
        literal for literal in DEVELOPMENT_LITERALS if literal in serialized_dataset
    )
    exact_prior = []
    near_prior = []
    for case_id, text in current:
        for old, source in prior:
            ratio = SequenceMatcher(None, text, old).ratio()
            if text == old:
                exact_prior.append({"case_id": case_id, "source": source})
            elif ratio >= 0.88:
                near_prior.append({"case_id": case_id, "source": source, "similarity": round(ratio, 4)})
    checks = {
        "schema_matches": dataset.get("schema") == "uruha_profile_relevance_speakability_v71",
        "frozen_before_implementation": dataset.get("status") == "frozen_before_audit_selector_harness_or_formal_inference",
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
        "prior_profile_value_overlap_zero": not prior_value_overlaps,
        "development_literal_overlap_zero": not development_literal_overlaps,
    }
    return {
        "schema": "uruha_profile_relevance_speakability_dataset_audit_v71",
        "passed": all(checks.values()),
        "bindings": {"preregistration_sha256": _sha256(PREREG_PATH), "dataset_sha256": _sha256(DATASET_PATH)},
        "counts": {
            "case_count": len(cases),
            "family_count": len(families),
            "relevant_count": relevant,
            "irrelevant_count": len(cases) - relevant,
            "abstention_count": abstention,
            "profile_record_count": sum(len(case["profile_history"]) for case in cases),
            "source_utterance_count": sum(len(case["profile_history"]) for case in cases),
            "prior_input_count_scanned": len(prior),
            "internal_near_duplicate_count": len(internal_near),
            "exact_prior_overlap_count": len(exact_prior),
            "near_prior_overlap_count": len(near_prior),
            "prior_profile_value_overlap_count": len(prior_value_overlaps),
            "development_literal_overlap_count": len(development_literal_overlaps),
        },
        "family_counts": dict(sorted(families.items())),
        "checks": checks,
        "failures": {
            "case_failures": failures,
            "internal_near_duplicates": internal_near,
            "exact_prior_overlaps": exact_prior,
            "near_prior_overlaps": near_prior,
            "prior_profile_value_overlaps": prior_value_overlaps,
            "development_literal_overlaps": development_literal_overlaps,
        },
        "evidence_boundary": "This audit proves only frozen shape, balance, provenance presence, expected-selection consistency, and no detected prior-input overlap. It contains no selector, model call, answer result, or runtime authorization."
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    audit = build_audit()
    if args.write:
        REPORT_PATH.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        closure = {
            "schema": "uruha_profile_relevance_speakability_dataset_closure_v71",
            "status": "frozen_after_audit_before_selector_harness_or_formal_inference",
            "audit_passed": audit["passed"],
            "frozen_artifacts": {
                "preregistration": audit["bindings"]["preregistration_sha256"],
                "dataset": audit["bindings"]["dataset_sha256"],
                "audit": _sha256(REPORT_PATH)
            },
            "authorizations": {
                "selector_implementation": audit["passed"],
                "harness_implementation": audit["passed"],
                "formal_inference": False,
                "temporary_chroma_access": False,
                "runtime_change": False,
                "answer_use": False
            }
        }
        CLOSURE_PATH.write_text(json.dumps(closure, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(audit, ensure_ascii=False, indent=2))
    raise SystemExit(0 if audit["passed"] else 1)


if __name__ == "__main__":
    main()
