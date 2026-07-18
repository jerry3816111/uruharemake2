#!/usr/bin/env python3
"""Audit V65 exact-plan cases before harness construction or inference."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PREREG_PATH = ROOT / "configs/cognitive_plan_model_screen_v65_preregistration.json"
DATASET_PATH = ROOT / "datasets/cognitive_plan_model_screen_v65.json"
REPORT_PATH = ROOT / "reports/cognitive_plan_model_screen_v65_dataset_audit.json"
CLOSURE_PATH = ROOT / "configs/cognitive_plan_model_screen_v65_dataset_closure.json"
EXCLUDED = {path.resolve() for path in (PREREG_PATH, DATASET_PATH, REPORT_PATH, CLOSURE_PATH)}
TEXT_KEYS = {"user_input", "input", "question", "prompt", "utterance", "query"}


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


def _case_shape_failures(case, prereg):
    failures = []
    packet = case.get("planning_packet") or {}
    expected = case.get("expected") or {}
    packet_fields = {"user_input", "actors", "evidence", "memory_records", "decision_targets"}
    expected_fields = set(prereg["tool_contract"]["required_fields"])
    if set(packet) != packet_fields:
        failures.append("planning_packet_fields")
    if set(expected) != expected_fields:
        failures.append("expected_fields")
    actor_ids = {row.get("id") for row in packet.get("actors") or []}
    evidence_ids = {row.get("id") for row in packet.get("evidence") or []}
    memory_ids = {row.get("id") for row in packet.get("memory_records") or []}
    target_ids = {row.get("id") for row in packet.get("decision_targets") or []}
    if expected.get("response_act") not in prereg["tool_contract"]["response_act_enum"]:
        failures.append("response_act")
    if expected.get("epistemic_policy") not in prereg["tool_contract"]["epistemic_policy_enum"]:
        failures.append("epistemic_policy")
    if expected.get("primary_actor_id") not in actor_ids:
        failures.append("primary_actor_id")
    if expected.get("decision_target_id") not in target_ids:
        failures.append("decision_target_id")
    if not set(expected.get("selected_evidence_ids") or []).issubset(evidence_ids):
        failures.append("selected_evidence_ids")
    active = set(expected.get("active_memory_ids") or [])
    suppressed = set(expected.get("suppressed_memory_ids") or [])
    if not active.issubset(memory_ids) or not suppressed.issubset(memory_ids) or active.intersection(suppressed):
        failures.append("memory_ids")
    if not isinstance(expected.get("nonliteral"), bool):
        failures.append("nonliteral")
    for key in ("actors", "evidence", "memory_records", "decision_targets"):
        rows = packet.get(key)
        if not isinstance(rows, list) or (key != "memory_records" and not rows):
            failures.append(f"{key}_shape")
            continue
        ids = [row.get("id") for row in rows]
        if not all(isinstance(row, dict) and row.get("id") for row in rows) or len(ids) != len(set(ids)):
            failures.append(f"{key}_ids")
    return failures


def build_audit():
    prereg = _load(PREREG_PATH)
    dataset = _load(DATASET_PATH)
    expected = prereg["dataset"]
    cases = dataset.get("cases") or []
    ids = [case.get("id") for case in cases]
    inputs = [_normalize((case.get("planning_packet") or {}).get("user_input")) for case in cases]
    families = Counter(case.get("scenario_family") for case in cases)
    shape_failures = {case.get("id", "missing"): _case_shape_failures(case, prereg) for case in cases}
    shape_failures = {key: value for key, value in shape_failures.items() if value}
    threshold = 0.92
    internal = []
    for left in range(len(cases)):
        for right in range(left + 1, len(cases)):
            ratio = SequenceMatcher(None, inputs[left], inputs[right]).ratio()
            if ratio >= threshold:
                internal.append({"left": ids[left], "right": ids[right], "similarity": round(ratio, 4)})
    prior = _prior_texts()
    normalized_prior = [(_normalize(row["text"]), row) for row in prior if _normalize(row["text"])]
    exact = []
    near = []
    for case, value in zip(cases, inputs):
        for old_value, old in normalized_prior:
            if value == old_value:
                exact.append({"case_id": case["id"], "source": old["source"]})
            else:
                ratio = SequenceMatcher(None, value, old_value).ratio()
                if ratio >= threshold:
                    near.append({"case_id": case["id"], "source": old["source"], "similarity": round(ratio, 4)})
    checks = {
        "schema_matches": dataset.get("schema") == "uruha_cognitive_plan_model_screen_v65",
        "status_frozen_before_audit_harness_or_inference": dataset.get("status") == "frozen_before_audit_harness_or_model_inference",
        "official_benchmark_items_false": dataset.get("official_benchmark_items") is False,
        "benchmark_answers_present_false": dataset.get("benchmark_answers_present") is False,
        "case_count_exact": len(cases) == expected["case_count"],
        "family_count_exact": len(families) == expected["scenario_family_count"],
        "family_set_exact": set(families) == set(expected["scenario_families"]),
        "cases_per_family_exact": all(families.get(family) == expected["cases_per_family"] for family in expected["scenario_families"]),
        "case_ids_unique": len(ids) == len(set(ids)) and all(ids),
        "user_inputs_unique": len(inputs) == len(set(inputs)) and all(inputs),
        "case_shapes_and_references_valid": not shape_failures,
        "internal_near_duplicate_count_zero": not internal,
        "exact_prior_text_overlap_count_zero": not exact,
        "external_near_duplicate_count_zero": not near,
    }
    return {
        "schema": "uruha_cognitive_plan_model_screen_dataset_audit_v65",
        "passed": all(checks.values()),
        "bindings": {"preregistration_path": str(PREREG_PATH.relative_to(ROOT)), "preregistration_sha256": _sha256(PREREG_PATH), "dataset_path": str(DATASET_PATH.relative_to(ROOT)), "dataset_sha256": _sha256(DATASET_PATH)},
        "counts": {"case_count": len(cases), "scenario_family_count": len(families), "exact_scored_field_count": len(cases) * len(prereg["tool_contract"]["required_fields"]), "prior_text_count_scanned": len(prior), "internal_near_duplicate_count": len(internal), "exact_prior_text_overlap_count": len(exact), "external_near_duplicate_count": len(near)},
        "family_counts": dict(sorted(families.items())),
        "checks": checks,
        "failures": {"shape_failures": shape_failures, "internal_near_duplicates": internal, "exact_prior_text_overlaps": exact, "external_near_duplicates": near},
        "evidence_boundary": "This audit proves only structural validity, referential integrity, and no detected overlap in scanned JSON/JSONL sources. It contains no model output or capacity evidence."
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    audit = build_audit()
    if args.write:
        REPORT_PATH.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        closure = {
            "schema": "uruha_cognitive_plan_model_screen_dataset_closure_v65",
            "status": "frozen_after_construction_audit_before_harness_or_inference",
            "audit_passed": audit["passed"],
            "frozen_artifacts": {"preregistration": audit["bindings"]["preregistration_sha256"], "dataset": audit["bindings"]["dataset_sha256"], "audit": _sha256(REPORT_PATH)},
            "authorizations": {"harness_implementation": True, "model_inference": False, "runtime_change": False}
        }
        CLOSURE_PATH.write_text(json.dumps(closure, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(audit, ensure_ascii=False, indent=2))
    raise SystemExit(0 if audit["passed"] else 1)


if __name__ == "__main__":
    main()
