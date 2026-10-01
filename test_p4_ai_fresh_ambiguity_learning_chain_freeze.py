import hashlib
from pathlib import Path

import p4_ai_fresh_ambiguity_learning_chain_gate as gate

ROOT = Path(__file__).resolve().parent


def test_contract_binds_new_dataset_and_fixed_predecessors():
    contract = gate.load_contract()
    dataset_path = ROOT / contract["dataset"]["path"]
    assert hashlib.sha256(dataset_path.read_bytes()).hexdigest() == contract["dataset"]["sha256"]
    for path_text, digest in contract["predecessor"].values():
        assert hashlib.sha256((ROOT / path_text).read_bytes()).hexdigest() == digest


def test_dataset_balances_outcomes_and_languages():
    rows = gate.load_dataset(gate.load_contract())["fresh_sequences"]
    assert len(rows) == 9
    assert {row["language"] for row in rows} == {"zh", "en", "ja"}
    assert {status: sum(row["expected_outcome"] == status for row in rows) for status in ("supported", "contradicted", "unknown")} == {
        "supported": 3,
        "contradicted": 3,
        "unknown": 3,
    }
