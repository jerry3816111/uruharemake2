#!/usr/bin/env python3
"""Audit V69 cross-session profile-state cases before implementation."""

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
PREREG_PATH = ROOT / "configs/profile_state_transition_v69_preregistration.json"
DATASET_PATH = ROOT / "datasets/profile_state_transition_v69.json"
REPORT_PATH = ROOT / "reports/profile_state_transition_v69_dataset_audit.json"
CLOSURE_PATH = ROOT / "configs/profile_state_transition_v69_dataset_closure.json"
EXCLUDED = {path.resolve() for path in (PREREG_PATH, DATASET_PATH, REPORT_PATH, CLOSURE_PATH)}


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _normalize(value):
    return re.sub(r"[^0-9a-zぁ-んァ-ヶ一-龠]", "", str(value or "").lower())


def _case_failures(case):
    failures = []
    if set(case) != {"id", "scenario_family", "language", "turns", "expected"}:
        failures.append("case_fields")
    if case.get("language") not in {"en", "zh", "ja"}:
        failures.append("language")
    turns = case.get("turns") or []
    turn_ids = [turn.get("turn_id") for turn in turns]
    if len(turns) != 2 or len(turn_ids) != len(set(turn_ids)) or not all(turn_ids):
        failures.append("turns")
    for turn in turns:
        if set(turn) != {"turn_id", "timestamp", "utterance"} or not turn.get("utterance"):
            failures.append("turn_shape")
        try:
            dt.datetime.fromisoformat(turn.get("timestamp", ""))
        except ValueError:
            failures.append("timestamp")
    expected = case.get("expected") or {}
    if set(expected) != {"written_turn_ids", "active_turn_ids", "historical_turn_ids"}:
        failures.append("expected_fields")
        return sorted(set(failures))
    written = set(expected["written_turn_ids"])
    active = set(expected["active_turn_ids"])
    historical = set(expected["historical_turn_ids"])
    if not written.issubset(set(turn_ids)) or active & historical or active | historical != written:
        failures.append("partition")
    return sorted(set(failures))


def _prior_utterances():
    rows = []
    for path in sorted((ROOT / "datasets").rglob("*.json")):
        if path.resolve() in EXCLUDED:
            continue
        try:
            payload = _load(path)
        except (OSError, json.JSONDecodeError):
            continue
        stack = [payload]
        while stack:
            value = stack.pop()
            if isinstance(value, dict):
                for key, child in value.items():
                    if key in {"utterance", "user_input", "query_text"} and isinstance(child, str):
                        rows.append((child, str(path.relative_to(ROOT))))
                    stack.append(child)
            elif isinstance(value, list):
                stack.extend(value)
    return rows


def build_audit():
    prereg = _load(PREREG_PATH)
    dataset = _load(DATASET_PATH)
    cases = dataset.get("cases") or []
    shape = prereg["dataset"]
    ids = [case.get("id") for case in cases]
    families = Counter(case.get("scenario_family") for case in cases)
    languages = Counter(case.get("language") for case in cases)
    failures = {case.get("id", "missing"): _case_failures(case) for case in cases}
    failures = {key: value for key, value in failures.items() if value}
    utterances = [(case["id"], turn["utterance"]) for case in cases for turn in case["turns"]]
    normalized = [(case_id, _normalize(text)) for case_id, text in utterances]
    internal_near = []
    for left in range(len(normalized)):
        for right in range(left + 1, len(normalized)):
            ratio = SequenceMatcher(None, normalized[left][1], normalized[right][1]).ratio()
            if ratio >= 0.92 and normalized[left][1] != normalized[right][1]:
                internal_near.append({"left": normalized[left][0], "right": normalized[right][0], "similarity": round(ratio, 4)})
    prior = [(_normalize(text), source) for text, source in _prior_utterances() if _normalize(text)]
    exact_prior = []
    near_prior = []
    for case_id, value in normalized:
        for old, source in prior:
            if value == old:
                exact_prior.append({"case_id": case_id, "source": source})
            elif SequenceMatcher(None, value, old).ratio() >= 0.92:
                near_prior.append({"case_id": case_id, "source": source})
    written = sum(len(case["expected"]["written_turn_ids"]) for case in cases)
    active = sum(len(case["expected"]["active_turn_ids"]) for case in cases)
    historical = sum(len(case["expected"]["historical_turn_ids"]) for case in cases)
    checks = {
        "schema_matches": dataset.get("schema") == "uruha_profile_state_transition_v69",
        "frozen_before_audit_harness_or_implementation": dataset.get("status") == "frozen_before_audit_harness_or_candidate_implementation",
        "official_benchmark_items_false": dataset.get("official_benchmark_items") is False,
        "benchmark_answers_present_false": dataset.get("benchmark_answers_present") is False,
        "case_count_exact": len(cases) == shape["case_count"],
        "family_set_exact": set(families) == set(shape["scenario_families"]),
        "cases_per_family_exact": all(families.get(name) == shape["cases_per_family"] for name in shape["scenario_families"]),
        "all_languages_present": set(languages) == set(shape["languages"]),
        "expected_record_counts_exact": written == shape["expected_write_count"] and active == shape["expected_active_record_count"] and historical == shape["expected_historical_record_count"],
        "case_ids_unique": len(ids) == len(set(ids)) and all(ids),
        "case_shapes_and_partitions_valid": not failures,
        "internal_near_duplicate_count_zero": not internal_near,
        "exact_prior_text_overlap_count_zero": not exact_prior,
        "external_near_duplicate_count_zero": not near_prior
    }
    return {
        "schema": "uruha_profile_state_transition_dataset_audit_v69",
        "passed": all(checks.values()),
        "bindings": {"preregistration_path": str(PREREG_PATH.relative_to(ROOT)), "preregistration_sha256": _sha256(PREREG_PATH), "dataset_path": str(DATASET_PATH.relative_to(ROOT)), "dataset_sha256": _sha256(DATASET_PATH)},
        "counts": {"case_count": len(cases), "scenario_family_count": len(families), "utterance_count": len(utterances), "expected_write_count": written, "expected_active_record_count": active, "expected_historical_record_count": historical, "prior_utterance_count_scanned": len(prior), "internal_near_duplicate_count": len(internal_near), "exact_prior_text_overlap_count": len(exact_prior), "external_near_duplicate_count": len(near_prior)},
        "family_counts": dict(sorted(families.items())),
        "language_counts": dict(sorted(languages.items())),
        "checks": checks,
        "failures": {"case_failures": failures, "internal_near_duplicates": internal_near, "exact_prior_text_overlaps": exact_prior, "external_near_duplicates": near_prior},
        "evidence_boundary": "This audit proves only structure, timestamps, record-level partitions, family balance, and no detected prior dataset overlap. It contains no compiler, Chroma run, or state capability result."
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    audit = build_audit()
    if args.write:
        REPORT_PATH.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        closure = {"schema": "uruha_profile_state_transition_dataset_closure_v69", "status": "frozen_after_construction_audit_before_harness_or_candidate_implementation", "audit_passed": audit["passed"], "frozen_artifacts": {"preregistration": audit["bindings"]["preregistration_sha256"], "dataset": audit["bindings"]["dataset_sha256"], "audit": _sha256(REPORT_PATH)}, "authorizations": {"candidate_implementation": audit["passed"], "shadow_execution": False, "temporary_chroma_access": False, "runtime_change": False}}
        CLOSURE_PATH.write_text(json.dumps(closure, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(audit, ensure_ascii=False, indent=2))
    raise SystemExit(0 if audit["passed"] else 1)


if __name__ == "__main__":
    main()
