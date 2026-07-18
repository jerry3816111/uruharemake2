#!/usr/bin/env python3
"""Audit and close the fresh V72 grounded profile speech-plan holdout."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PREREG_PATH = ROOT / "configs/profile_grounded_speech_plan_v72_preregistration.json"
DATASET_PATH = ROOT / "datasets/profile_grounded_speech_plan_v72.json"
REPORT_PATH = ROOT / "reports/profile_grounded_speech_plan_v72_dataset_audit.json"
CLOSURE_PATH = ROOT / "configs/profile_grounded_speech_plan_v72_dataset_closure.json"
EXCLUDED = {path.resolve() for path in (PREREG_PATH, DATASET_PATH, REPORT_PATH, CLOSURE_PATH)}
RELATIONS = {
    "name": "preferred_name",
    "like": "likes",
    "dislike": "dislikes",
    "favorite": "favorite",
}


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _normalize(value):
    return re.sub(r"[^0-9a-zぁ-んァ-ヶ一-龠]", "", str(value or "").casefold())


def _walk_prior(field_names):
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
                    if key in field_names and isinstance(child, str):
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
        if row.get("fact_type") not in RELATIONS:
            failures.append("fact_type")
        if not str(row.get("source_utterance") or "").strip():
            failures.append("source_utterance")

    expected = case.get("expected") or {}
    expected_fields = {
        "selected_memory_ids",
        "evidence_contract",
        "required_value_markers",
        "required_relation_markers",
        "forbidden_terms",
        "memory_relevant",
        "abstention_required",
    }
    if set(expected) != expected_fields:
        failures.append("expected_fields")
    selected = expected.get("selected_memory_ids") or []
    if len(selected) > 1 or len(selected) != len(set(selected)) or any(memory_id not in ids for memory_id in selected):
        failures.append("selected_ids")
    relevant = bool(expected.get("memory_relevant"))
    if bool(selected) != relevant:
        failures.append("selection_relevance_mismatch")
    if expected.get("abstention_required") and relevant:
        failures.append("abstention_relevance_conflict")

    contract = expected.get("evidence_contract") or {}
    if set(contract) != {"answerability", "fact_type", "value", "relation"}:
        failures.append("contract_fields")
    if relevant:
        selected_row = next((row for row in history if row.get("memory_id") in selected), {})
        if contract.get("answerability") != "supported":
            failures.append("supported_answerability")
        if contract.get("fact_type") != selected_row.get("fact_type"):
            failures.append("contract_fact_type")
        if contract.get("value") != selected_row.get("value"):
            failures.append("contract_value")
        if contract.get("relation") != RELATIONS.get(selected_row.get("fact_type")):
            failures.append("contract_relation")
        if not expected.get("required_value_markers"):
            failures.append("missing_value_markers")
        if selected_row.get("fact_type") != "name" and not expected.get("required_relation_markers"):
            failures.append("missing_relation_markers")
    else:
        answerability = "unsupported" if expected.get("abstention_required") else "not_requested"
        if contract != {"answerability": answerability, "fact_type": None, "value": None, "relation": None}:
            failures.append("irrelevant_contract")
        if expected.get("required_value_markers") or expected.get("required_relation_markers"):
            failures.append("irrelevant_markers")
    return sorted(set(failures))


def build_audit():
    prereg = _load(PREREG_PATH)
    dataset = _load(DATASET_PATH)
    cases = dataset.get("cases") or []
    shape = prereg["planned_dataset"]
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

    prior_inputs = [
        (_normalize(text), source)
        for text, source in _walk_prior({"utterance", "user_input", "query_text", "input"})
        if _normalize(text)
    ]
    exact_prior = []
    near_prior = []
    for case_id, text in current:
        for old, source in prior_inputs:
            ratio = SequenceMatcher(None, text, old).ratio()
            if text == old:
                exact_prior.append({"case_id": case_id, "source": source})
            elif ratio >= 0.88:
                near_prior.append({"case_id": case_id, "source": source, "similarity": round(ratio, 4)})

    current_values = {row["value"] for case in cases for row in case["profile_history"]}
    prior_value_overlaps = [
        {"value": value, "source": source}
        for value, source in _prior_profile_values()
        if value in current_values
    ]
    checks = {
        "schema_matches": dataset.get("schema") == "uruha_profile_grounded_speech_plan_v72",
        "frozen_before_implementation": dataset.get("status") == "frozen_before_audit_bridge_harness_or_formal_inference",
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
    }
    return {
        "schema": "uruha_profile_grounded_speech_plan_dataset_audit_v72",
        "passed": all(checks.values()),
        "bindings": {
            "preregistration_sha256": _sha256(PREREG_PATH),
            "dataset_sha256": _sha256(DATASET_PATH),
        },
        "counts": {
            "case_count": len(cases),
            "family_count": len(families),
            "relevant_count": relevant,
            "irrelevant_count": len(cases) - relevant,
            "abstention_count": abstention,
            "profile_record_count": sum(len(case["profile_history"]) for case in cases),
            "source_utterance_count": sum(len(case["profile_history"]) for case in cases),
            "prior_input_count_scanned": len(prior_inputs),
            "internal_near_duplicate_count": len(internal_near),
            "exact_prior_overlap_count": len(exact_prior),
            "near_prior_overlap_count": len(near_prior),
            "prior_profile_value_overlap_count": len(prior_value_overlaps),
        },
        "family_counts": dict(sorted(families.items())),
        "checks": checks,
        "failures": {
            "case_failures": failures,
            "internal_near_duplicates": internal_near,
            "exact_prior_overlaps": exact_prior,
            "near_prior_overlaps": near_prior,
            "prior_profile_value_overlaps": prior_value_overlaps,
        },
        "evidence_boundary": "This audit proves only frozen shape, balance, typed expected-contract consistency, provenance presence, and no detected prior input or profile-value overlap. It contains no bridge, model call, answer result, or runtime authorization."
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    audit = build_audit()
    if args.write:
        REPORT_PATH.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        closure = {
            "schema": "uruha_profile_grounded_speech_plan_dataset_closure_v72",
            "status": "frozen_after_audit_before_bridge_harness_or_formal_inference",
            "audit_passed": audit["passed"],
            "frozen_artifacts": {
                "preregistration": audit["bindings"]["preregistration_sha256"],
                "dataset": audit["bindings"]["dataset_sha256"],
                "audit": _sha256(REPORT_PATH),
            },
            "authorizations": {
                "bridge_implementation": audit["passed"],
                "harness_implementation": audit["passed"],
                "formal_inference": False,
                "temporary_chroma_access": False,
                "runtime_change": False,
                "answer_use": False,
            },
        }
        CLOSURE_PATH.write_text(json.dumps(closure, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(audit, ensure_ascii=False, indent=2))
    raise SystemExit(0 if audit["passed"] else 1)


if __name__ == "__main__":
    main()
