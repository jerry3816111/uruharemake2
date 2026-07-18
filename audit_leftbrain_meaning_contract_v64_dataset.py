#!/usr/bin/env python3
"""Audit V64 construction before any prompt or model output exists."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PREREG_PATH = ROOT / "configs/leftbrain_meaning_contract_v64_preregistration.json"
DATASET_PATH = ROOT / "datasets/leftbrain_meaning_contract_v64.json"
REPORT_PATH = ROOT / "reports/leftbrain_meaning_contract_v64_dataset_audit.json"
CLOSURE_PATH = ROOT / "configs/leftbrain_meaning_contract_v64_dataset_closure.json"
EXCLUDED = {PREREG_PATH.resolve(), DATASET_PATH.resolve(), REPORT_PATH.resolve(), CLOSURE_PATH.resolve()}
TEXT_KEYS = {"user_input", "input", "question", "prompt", "utterance", "query"}


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _normalize(value):
    return re.sub(r"[^0-9a-zぁ-んァ-ヶ一-龠]", "", str(value or "").lower())


def _extract_texts(value, source, output):
    if isinstance(value, dict):
        for key, child in value.items():
            if key in TEXT_KEYS and isinstance(child, str) and len(_normalize(child)) >= 8:
                output.append({"text": child, "source": source})
            _extract_texts(child, source, output)
    elif isinstance(value, list):
        for child in value:
            _extract_texts(child, source, output)


def _prior_texts():
    rows = []
    for directory in ("datasets", "configs", "reports"):
        for path in sorted((ROOT / directory).rglob("*.json")):
            if path.resolve() in EXCLUDED:
                continue
            try:
                payload = _load(path)
            except (OSError, json.JSONDecodeError):
                continue
            _extract_texts(payload, str(path.relative_to(ROOT)), rows)
        for path in sorted((ROOT / directory).rglob("*.jsonl")):
            if path.resolve() in EXCLUDED:
                continue
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except OSError:
                continue
            for line in lines:
                try:
                    _extract_texts(json.loads(line), str(path.relative_to(ROOT)), rows)
                except json.JSONDecodeError:
                    continue
    return rows


def build_audit():
    prereg = _load(PREREG_PATH)
    dataset = _load(DATASET_PATH)
    expected = prereg["fresh_dataset"]
    cases = dataset.get("cases") or []
    ids = [case.get("id") for case in cases]
    normalized_inputs = [_normalize(case.get("user_input")) for case in cases]
    families = Counter(case.get("scenario_family") for case in cases)
    threshold = 0.92
    required_fields = {
        "id",
        "scenario_family",
        "user_input",
        "memory_fixture",
        "expected_response_act",
        "required_commitments",
        "forbidden_commitments",
        "required_frame_relations",
    }

    missing_fields = {
        case.get("id", f"row_{index}"): sorted(required_fields - set(case))
        for index, case in enumerate(cases)
        if required_fields - set(case)
    }
    malformed_commitments = []
    malformed_relations = []
    commitment_ids = []
    relation_ids = []
    for case in cases:
        for field in ("required_commitments", "forbidden_commitments"):
            for item in case.get(field) or []:
                valid = (
                    isinstance(item, dict)
                    and item.get("id")
                    and isinstance(item.get("accepted_surfaces"), list)
                    and item.get("accepted_surfaces")
                )
                if not valid:
                    malformed_commitments.append({"case_id": case.get("id"), "field": field})
                else:
                    commitment_ids.append(f"{case.get('id')}::{field}::{item['id']}")
        for item in case.get("required_frame_relations") or []:
            valid = (
                isinstance(item, dict)
                and item.get("id")
                and all(isinstance(item.get(key), list) and item.get(key) for key in ("subject_any", "predicate_any", "object_any"))
            )
            if not valid:
                malformed_relations.append({"case_id": case.get("id")})
            else:
                relation_ids.append(f"{case.get('id')}::{item['id']}")

    internal_near_duplicates = []
    for left in range(len(cases)):
        for right in range(left + 1, len(cases)):
            ratio = SequenceMatcher(None, normalized_inputs[left], normalized_inputs[right]).ratio()
            if ratio >= threshold:
                internal_near_duplicates.append({"left": ids[left], "right": ids[right], "similarity": round(ratio, 4)})

    prior = _prior_texts()
    prior_normalized = [(_normalize(row["text"]), row) for row in prior if _normalize(row["text"])]
    exact_overlaps = []
    external_near_duplicates = []
    for case, normalized in zip(cases, normalized_inputs):
        for old_normalized, old in prior_normalized:
            if normalized == old_normalized:
                exact_overlaps.append({"case_id": case["id"], "source": old["source"]})
                continue
            ratio = SequenceMatcher(None, normalized, old_normalized).ratio()
            if ratio >= threshold:
                external_near_duplicates.append({"case_id": case["id"], "source": old["source"], "similarity": round(ratio, 4)})

    memory_cases = [case for case in cases if case.get("scenario_family") == "temporal_memory_update"]
    checks = {
        "schema_matches": dataset.get("schema") == "uruha_leftbrain_meaning_contract_pilot_v64",
        "status_frozen_before_audit_harness_or_inference": dataset.get("status") == "frozen_before_audit_harness_or_model_inference",
        "official_benchmark_items_false": dataset.get("official_benchmark_items") is False,
        "benchmark_answers_present_false": dataset.get("benchmark_answers_present") is False,
        "case_count_exact": len(cases) == expected["case_count"],
        "family_count_exact": len(families) == expected["scenario_family_count"],
        "family_set_exact": set(families) == set(expected["scenario_families"]),
        "cases_per_family_exact": all(families.get(family) == expected["cases_per_family"] for family in expected["scenario_families"]),
        "case_ids_unique": len(ids) == len(set(ids)) and all(ids),
        "user_inputs_unique": len(normalized_inputs) == len(set(normalized_inputs)) and all(normalized_inputs),
        "required_fields_complete": not missing_fields,
        "required_commitments_nonempty": all(case.get("required_commitments") for case in cases),
        "frame_relations_nonempty": all(case.get("required_frame_relations") for case in cases),
        "commitments_well_formed": not malformed_commitments,
        "relations_well_formed": not malformed_relations,
        "commitment_ids_unique": len(commitment_ids) == len(set(commitment_ids)),
        "relation_ids_unique": len(relation_ids) == len(set(relation_ids)),
        "memory_fixture_shape_valid": all(isinstance(case.get("memory_fixture"), list) for case in cases),
        "temporal_memory_cases_exact": len(memory_cases) == 2,
        "memory_current_and_superseded_present": all({row.get("status") for row in case["memory_fixture"]} == {"current", "superseded"} for case in memory_cases),
        "internal_near_duplicate_count_zero": not internal_near_duplicates,
        "exact_prior_text_overlap_count_zero": not exact_overlaps,
        "external_near_duplicate_count_zero": not external_near_duplicates,
    }
    return {
        "schema": "uruha_leftbrain_meaning_contract_dataset_audit_v64",
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
            "required_commitment_count": sum(len(case["required_commitments"]) for case in cases),
            "forbidden_commitment_count": sum(len(case["forbidden_commitments"]) for case in cases),
            "required_frame_relation_count": sum(len(case["required_frame_relations"]) for case in cases),
            "prior_text_count_scanned": len(prior),
            "internal_near_duplicate_count": len(internal_near_duplicates),
            "exact_prior_text_overlap_count": len(exact_overlaps),
            "external_near_duplicate_count": len(external_near_duplicates),
        },
        "family_counts": dict(sorted(families.items())),
        "checks": checks,
        "failures": {
            "missing_fields": missing_fields,
            "malformed_commitments": malformed_commitments,
            "malformed_relations": malformed_relations,
            "internal_near_duplicates": internal_near_duplicates,
            "exact_prior_text_overlaps": exact_overlaps,
            "external_near_duplicates": external_near_duplicates,
        },
        "evidence_boundary": "This audit proves only dataset shape and no detected overlap in scanned JSON/JSONL sources. It contains no model output or ability evidence.",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    audit = build_audit()
    if args.write:
        REPORT_PATH.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        closure = {
            "schema": "uruha_leftbrain_meaning_contract_dataset_closure_v64",
            "status": "frozen_after_construction_audit_before_harness_or_inference",
            "audit_passed": audit["passed"],
            "frozen_artifacts": {
                "preregistration": audit["bindings"]["preregistration_sha256"],
                "dataset": audit["bindings"]["dataset_sha256"],
                "audit": _sha256(REPORT_PATH),
            },
            "authorizations": {"harness_implementation": True, "model_inference": False, "runtime_change": False},
        }
        CLOSURE_PATH.write_text(json.dumps(closure, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(audit, ensure_ascii=False, indent=2))
    raise SystemExit(0 if audit["passed"] else 1)


if __name__ == "__main__":
    main()
