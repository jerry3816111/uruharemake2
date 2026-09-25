"""Immutable P4-AT offline contract loader and evaluator."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONTRACT = ROOT / "configs" / "p4_at_executed_action_outcome_closure_v1.json"


def _sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_contract():
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def load_dataset(contract=None):
    contract = contract or load_contract()
    path = ROOT / contract["dataset"]["path"]
    expected = contract["dataset"]["sha256"]
    actual = _sha256(path)
    if actual != expected:
        raise ValueError(f"p4_at_dataset_hash_mismatch:{actual}")
    return json.loads(path.read_text(encoding="utf-8"))


def evaluate_offline_evidence(contract, evidence):
    expected = contract["offline_gates"]
    actual = evidence.get("metrics") or {}
    failed = [
        key
        for key, expected_value in expected.items()
        if actual.get(key) != expected_value
    ]
    return {
        "schema": "uruha_p4_at_executed_action_outcome_closure_gate_result_v1",
        "status": "pass" if not failed else "fail",
        "failed_gates": failed,
        "expected": expected,
        "actual": {key: actual.get(key) for key in expected},
        "claim_boundary": contract["claim_boundary"],
    }
