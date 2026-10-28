"""Immutable P4-AU source-bound current-action delivery contract."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONTRACT = ROOT / "configs" / "p4_au_source_bound_current_action_delivery_v1.json"


def _sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_contract():
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def load_dataset(contract=None):
    contract = contract or load_contract()
    path = ROOT / contract["dataset"]["path"]
    actual = _sha256(path)
    expected = contract["dataset"]["sha256"]
    if actual != expected:
        raise ValueError(f"p4_au_dataset_hash_mismatch:{actual}")
    return json.loads(path.read_text(encoding="utf-8"))


def assert_predecessors_unchanged(contract=None):
    contract = contract or load_contract()
    mismatches = {}
    for relative, expected in contract["predecessor_hashes"].items():
        actual = _sha256(ROOT / relative)
        if actual != expected:
            mismatches[relative] = {"expected": expected, "actual": actual}
    if mismatches:
        raise ValueError(f"p4_au_predecessor_hash_mismatch:{mismatches}")
    return True


def evaluate_offline_evidence(contract, evidence):
    expected = contract["offline_gates"]
    actual = evidence.get("metrics") or {}
    failed = [
        key
        for key, expected_value in expected.items()
        if actual.get(key) != expected_value
    ]
    return {
        "schema": "uruha_p4_au_source_bound_current_action_delivery_gate_result_v1",
        "status": "pass" if not failed else "fail",
        "failed_gates": failed,
        "expected": expected,
        "actual": {key: actual.get(key) for key in expected},
        "claim_boundary": contract["claim_boundary"],
    }
