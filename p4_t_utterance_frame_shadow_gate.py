#!/usr/bin/env python3
"""Fail-closed gate frozen before the P4-T shadow detector implementation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONTRACT = ROOT / "configs" / "p4_t_utterance_frame_shadow_acceptance_v1.json"


class P4TGateError(RuntimeError):
    pass


def _sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_contract(path=CONTRACT):
    contract = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_contract(contract)
    return contract


def load_dataset(contract):
    return json.loads((ROOT / contract["dataset"]["path"]).read_text(encoding="utf-8"))


def validate_contract(contract):
    if contract.get("schema") != "uruha_p4_t_utterance_frame_shadow_acceptance_v1":
        raise P4TGateError("contract_schema_invalid")
    dataset = contract.get("dataset") or {}
    path = ROOT / str(dataset.get("path") or "")
    if not path.is_file() or _sha256(path) != dataset.get("sha256"):
        raise P4TGateError("dataset_binding_invalid")
    payload = json.loads(path.read_text(encoding="utf-8"))
    counts = {
        "development_case_count": len(payload.get("development_failures") or []),
        "holdout_case_count": len(payload.get("holdout_failures") or []),
        "plain_control_count": len(payload.get("plain_controls") or []),
    }
    for field, observed in counts.items():
        if observed != dataset.get(field):
            raise P4TGateError(f"dataset_{field}_invalid")
    case_ids = [
        row.get("case_id")
        for partition in ("development_failures", "holdout_failures", "plain_controls")
        for row in payload.get(partition) or []
    ]
    if len(case_ids) != len(set(case_ids)) or any(not item for item in case_ids):
        raise P4TGateError("dataset_case_ids_invalid")
    if sorted({row.get("language") for row in payload.get("holdout_failures") or []}) != ["en", "ja", "zh"]:
        raise P4TGateError("holdout_language_coverage_invalid")
    boundary = contract.get("implementation_boundary") or {}
    if boundary.get("visible_reply_change_allowed") is not False:
        raise P4TGateError("shadow_boundary_invalid")
    if (contract.get("failure_policy") or {}).get("dataset_or_expected_label_change_after_implementation") is not False:
        raise P4TGateError("freeze_policy_invalid")


def _expected_rows(dataset):
    result = {}
    for partition in ("development_failures", "holdout_failures", "plain_controls"):
        for row in dataset.get(partition) or []:
            result[row["case_id"]] = (partition, row)
    return result


def evaluate_evidence(contract, evidence):
    validate_contract(contract)
    dataset = load_dataset(contract)
    expected = _expected_rows(dataset)
    failures = []
    if evidence.get("schema") != "uruha_p4_t_utterance_frame_shadow_evidence_v1":
        failures.append("evidence_schema_invalid")
    if evidence.get("dataset_sha256") != contract["dataset"]["sha256"]:
        failures.append("dataset_hash_mismatch")
    rows = evidence.get("cases") or []
    if [row.get("case_id") for row in rows] != list(expected):
        failures.append("case_order_or_count_invalid")
    else:
        for observed in rows:
            case_id = observed["case_id"]
            partition, frozen = expected[case_id]
            if observed.get("partition") != partition:
                failures.append(f"{case_id}:partition_mismatch")
            expected_frame = frozen.get("expected_frame")
            if expected_frame is not None and observed.get("frame") != expected_frame:
                failures.append(f"{case_id}:frame_mismatch")
            if observed.get("violations") != frozen.get("expected_violations"):
                failures.append(f"{case_id}:violation_mismatch")
            if observed.get("candidate_unchanged") is not True:
                failures.append(f"{case_id}:candidate_changed")
            if observed.get("trace_contains_raw_source_or_reply") is not False:
                failures.append(f"{case_id}:raw_trace_present")
            if observed.get("model_call_added") is not False:
                failures.append(f"{case_id}:model_call_added")
            if any(observed.get(field) != 0 for field in ("fact_write_count", "profile_write_count", "episode_write_count")):
                failures.append(f"{case_id}:memory_write_added")
    metrics = evidence.get("metrics") or {}
    for field, target in contract["gates"].items():
        if metrics.get(field) != target:
            failures.append(f"metric_mismatch:{field}")
    integration = evidence.get("integration") or {}
    if integration.get("product_entry_installs_shadow_detector") is not True:
        failures.append("product_install_missing")
    if integration.get("runtime_graph_node_test_passed") is not True:
        failures.append("runtime_graph_node_missing")
    if integration.get("visible_reply_unchanged_test_passed") is not True:
        failures.append("shadow_mutated_visible_reply")
    return {
        "schema": "uruha_p4_t_utterance_frame_shadow_gate_result_v1",
        "status": "pass" if not failures else "fail",
        "failed_gates": failures,
        "claim_boundary": contract["claim_boundary"],
    }


if __name__ == "__main__":
    print(json.dumps(load_contract(), ensure_ascii=False, indent=2))
