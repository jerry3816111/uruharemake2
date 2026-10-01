#!/usr/bin/env python3
"""M36 source-disjoint compositional pragmatic remediation evaluator."""

from __future__ import annotations

import argparse
import hashlib
import json
from copy import deepcopy
from pathlib import Path

import uruha_same_model_longitudinal_eval_m35 as m35
from uruha_pragmatic_annotation_integrity_m36 import (
    ALLOWED_POLICIES_M36,
    validate_annotation_rows_m36,
)


ROOT = Path(__file__).resolve().parent
RESERVE_PATH = ROOT / "datasets/m36_compositional_multilingual_pragmatic_reserve_v1.json"
PROTOCOL_PATH = ROOT / "research/m36_compositional_multilingual_pragmatic_protocol.json"
FREEZE_PATH = ROOT / "research/m36_implementation_freeze_2026-08-26.json"
OUTPUT_PATH = ROOT / "analysis/m36_compositional_multilingual_pragmatic_reserve_raw_2026-08-25.json"
M35_RESERVE_PATH = ROOT / "datasets/m35_same_model_longitudinal_pragmatic_reserve_v1.json"


def _sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _rate(numerator, denominator):
    return round(float(numerator) / float(denominator), 4) if denominator else 0.0


def validate_reserve(dataset, protocol):
    cases = list(dataset.get("cases") or [])
    errors = []
    expected_status = "sealed_after_m36_annotation_validator_before_m36_runtime_implementation"
    protocol_status = "sealed_after_annotation_validator_before_m36_runtime_implementation"
    if dataset.get("status") != expected_status:
        errors.append("dataset_not_pre_runtime_sealed")
    if protocol.get("status") != protocol_status:
        errors.append("protocol_not_pre_runtime_sealed")
    reserve = protocol.get("reserve") or {}
    if len(cases) != int(reserve.get("case_count") or 0):
        errors.append("case_count_mismatch")
    if _sha256(RESERVE_PATH) != reserve.get("sha256"):
        errors.append("dataset_hash_mismatch")
    ids = [str(row.get("case_id") or "") for row in cases]
    if len(ids) != len(set(ids)):
        errors.append("duplicate_case_id")
    languages = {
        language: sum(row.get("language") == language for row in cases)
        for language in ("zh", "en", "ja")
    }
    if languages != {"zh": 4, "en": 4, "ja": 4}:
        errors.append(f"language_balance:{languages}")
    pairs = {}
    for row in cases:
        pairs.setdefault(row.get("pair_id"), []).append(row)
        if row.get("expected_current_policy") not in ALLOWED_POLICIES_M36:
            errors.append(f"invalid_current_policy:{row.get('case_id')}")
    for pair_id, group in pairs.items():
        if len(group) != 2:
            errors.append(f"pair_size:{pair_id}:{len(group)}")
            continue
        if len({row.get("current_input") for row in group}) != 1:
            errors.append(f"pair_current_not_identical:{pair_id}")
        if len({row.get("language") for row in group}) != 1:
            errors.append(f"pair_language_not_identical:{pair_id}")
        if len({row.get("expected_current_policy") for row in group}) != 2:
            errors.append(f"pair_policy_not_divergent:{pair_id}")
    annotation = validate_annotation_rows_m36(cases)
    errors.extend(f"annotation:{item}" for item in annotation["errors"])

    if M35_RESERVE_PATH.exists():
        previous = json.loads(M35_RESERVE_PATH.read_text(encoding="utf-8"))
        fields = ("seed_input", "seed_feedback", "current_input", "feedback_input")
        previous_values = {
            str(row.get(field) or "")
            for row in (previous.get("cases") or [])
            for field in fields
            if row.get(field)
        }
        exact_reuse = sorted(
            {
                f"{row.get('case_id')}:{field}"
                for row in cases
                for field in fields
                if row.get(field) and str(row.get(field)) in previous_values
            }
        )
        if exact_reuse:
            errors.append(f"m35_exact_source_reuse:{exact_reuse}")
    return {
        "passed": not errors,
        "errors": errors,
        "case_count": len(cases),
        "pair_count": len(pairs),
        "language_counts": languages,
        "annotation_integrity": annotation,
    }


def _run_case(case, protocol, tokenizer, case_index):
    row = m35._run_case(case, protocol, tokenizer, case_index)
    row["feedback_policy_scoring"] = case["feedback_policy_scoring"]
    scored = case["feedback_policy_scoring"] == "scored"
    for condition in m35.CONDITIONS:
        row["feedback"][condition]["surface_proxy_match"] = (
            m35.policy_surface_proxy(
                case["expected_feedback_policy"],
                row["feedback"][condition].get("reply"),
            )
            if scored
            else None
        )
    return row


def summarize(rows, gates, annotation_integrity):
    inherited_gate_names = {
        key
        for key in gates
        if key
        not in {
            "annotation_integrity_pass_rate_min",
            "annotation_integrity_error_count_max",
            "system_feedback_surface_proxy_match_rate_min",
        }
    }
    inherited_gates = {key: gates[key] for key in inherited_gate_names}
    metrics, gate_results = m35.summarize(rows, inherited_gates)
    scored_feedback = [
        row for row in rows if row.get("feedback_policy_scoring") == "scored"
    ]
    metrics.update(
        {
            "annotation_integrity_pass_rate": (
                1.0 if annotation_integrity.get("passed") else 0.0
            ),
            "annotation_integrity_error_count": int(
                annotation_integrity.get("error_count") or 0
            ),
            "feedback_policy_scored_case_count": len(scored_feedback),
            "system_feedback_surface_proxy_match_rate": _rate(
                sum(
                    bool(row["feedback"]["system"].get("surface_proxy_match"))
                    for row in scored_feedback
                ),
                len(scored_feedback),
            ),
            "baseline_feedback_surface_proxy_match_rate": _rate(
                sum(
                    bool(row["feedback"]["baseline"].get("surface_proxy_match"))
                    for row in scored_feedback
                ),
                len(scored_feedback),
            ),
        }
    )
    gate_results.update(
        {
            "annotation_integrity_pass_rate_min": (
                metrics["annotation_integrity_pass_rate"]
                >= gates["annotation_integrity_pass_rate_min"]
            ),
            "annotation_integrity_error_count_max": (
                metrics["annotation_integrity_error_count"]
                <= gates["annotation_integrity_error_count_max"]
            ),
            "system_feedback_surface_proxy_match_rate_min": (
                metrics["system_feedback_surface_proxy_match_rate"]
                >= gates["system_feedback_surface_proxy_match_rate_min"]
            ),
        }
    )
    return metrics, gate_results


def run_reserve():
    dataset = json.loads(RESERVE_PATH.read_text(encoding="utf-8"))
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    validation = validate_reserve(dataset, protocol)
    if not validation["passed"]:
        raise ValueError(validation["errors"])
    rows = [
        _run_case(case, protocol, None, index)
        for index, case in enumerate(dataset["cases"], start=1)
    ]
    metrics, gate_results = summarize(
        rows,
        protocol["frozen_success_gates"],
        validation["annotation_integrity"],
    )
    payload = {
        "schema": "uruha_compositional_multilingual_pragmatic_evaluation_m36_v1",
        "mode": "reserve",
        "dataset_path": str(RESERVE_PATH.relative_to(ROOT)),
        "dataset_sha256": _sha256(RESERVE_PATH),
        "protocol_path": str(PROTOCOL_PATH.relative_to(ROOT)),
        "protocol_sha256": _sha256(PROTOCOL_PATH),
        "implementation_freeze_sha256": (
            _sha256(FREEZE_PATH) if FREEZE_PATH.exists() else None
        ),
        "annotation_integrity": {
            "passed": validation["annotation_integrity"]["passed"],
            "case_count": validation["annotation_integrity"]["case_count"],
            "error_count": validation["annotation_integrity"]["error_count"],
            "audits": deepcopy(validation["annotation_integrity"]["audits"]),
            "raw_feedback_persisted": False,
        },
        "model_contract": protocol["model_contract"],
        "decision": (
            "pass_all_frozen_gates"
            if gate_results and all(gate_results.values())
            else "fail_one_or_more_frozen_gates"
        ),
        "metrics": metrics,
        "gate_results": gate_results,
        "rows": rows,
        "claim_boundary": protocol["claim_boundary"],
        "human_felt_understanding_evidence_available": False,
    }
    OUTPUT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return payload


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("reserve",), required=True)
    parser.parse_args()
    payload = run_reserve()
    print(
        json.dumps(
            {"decision": payload["decision"], **payload["metrics"]},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
