#!/usr/bin/env python3
"""Prospective fail-closed gate for P4-AW CJK subject ellipsis authority."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONTRACT = ROOT / "configs/p4_aw_cjk_subject_ellipsis_action_authority_v1.json"


class P4AWGateError(RuntimeError):
    pass


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_contract(contract):
    if contract.get("schema") != "uruha_p4_aw_cjk_subject_ellipsis_action_authority_contract_v1":
        raise P4AWGateError("contract_schema_invalid")
    binding = contract.get("dataset") or {}
    path = ROOT / str(binding.get("path") or "")
    if not path.is_file() or _sha(path) != binding.get("sha256"):
        raise P4AWGateError("dataset_hash_mismatch")
    dataset = json.loads(path.read_text(encoding="utf-8"))
    cases = dataset.get("cases") or []
    if len(cases) != binding.get("case_count"):
        raise P4AWGateError("case_count_mismatch")
    expected_splits = {
        "exposed_development": binding.get("exposed_development_count"),
        "fresh_positive": binding.get("fresh_positive_count"),
        "fresh_control": binding.get("fresh_control_count"),
        "predecessor_control": binding.get("predecessor_control_count"),
    }
    for split, expected in expected_splits.items():
        if sum(row.get("split") == split for row in cases) != expected:
            raise P4AWGateError(f"split_count_mismatch:{split}")
    for name, predecessor in (contract.get("predecessors") or {}).items():
        source_path, expected_sha = predecessor
        if _sha(ROOT / source_path) != expected_sha:
            raise P4AWGateError(f"predecessor_changed:{name}")
    failure = contract.get("failure_policy") or {}
    forbidden_true = (
        "same_fresh_case_retry_allowed",
        "post_result_gate_or_dataset_change_allowed",
        "provisional_ellipsis_without_final_exact_chain_may_authorize",
        "third_party_quote_report_hypothetical_resolved_or_physical_control_may_authorize",
        "offline_pass_may_rewrite_p4_av_real_failure",
        "offline_pass_may_authorize_p4_av_real_product_claim",
    )
    if any(failure.get(key) is not False for key in forbidden_true):
        raise P4AWGateError("failure_policy_invalid")
    if failure.get("fresh_safari_case_required_after_offline_pass") is not True:
        raise P4AWGateError("fresh_safari_requirement_missing")


def load_contract(path=CONTRACT):
    contract = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_contract(contract)
    return contract


def load_dataset(contract):
    return json.loads((ROOT / contract["dataset"]["path"]).read_text(encoding="utf-8"))


def evaluate_offline_evidence(contract, evidence):
    validate_contract(contract)
    failures = []
    if evidence.get("schema") != "uruha_p4_aw_cjk_subject_ellipsis_action_authority_evidence_v1":
        failures.append("evidence_schema_invalid")
    if evidence.get("dataset_sha256") != contract["dataset"]["sha256"]:
        failures.append("dataset_hash_mismatch")
    for key, expected in (contract.get("offline_gates") or {}).items():
        if (evidence.get("metrics") or {}).get(key) != expected:
            failures.append(f"metric_mismatch:{key}")
    return {
        "schema": "uruha_p4_aw_cjk_subject_ellipsis_action_authority_result_v1",
        "status": "pass" if not failures else "fail",
        "failed_gates": failures,
        "claim_boundary": contract.get("claim_boundary"),
    }


__all__ = [
    "P4AWGateError",
    "evaluate_offline_evidence",
    "load_contract",
    "load_dataset",
    "validate_contract",
]
