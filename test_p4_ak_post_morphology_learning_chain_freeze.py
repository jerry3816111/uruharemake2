import hashlib
import json
from pathlib import Path

import p4_ak_post_morphology_learning_chain_gate as gate


ROOT = Path(__file__).resolve().parent


def test_contract_binds_dataset_and_all_causal_predecessors():
    contract = gate.load_contract()
    dataset_path = ROOT / contract["dataset"]["path"]
    assert hashlib.sha256(dataset_path.read_bytes()).hexdigest() == contract["dataset"]["sha256"]
    for path_text, digest in contract["predecessors"].values():
        assert hashlib.sha256((ROOT / path_text).read_bytes()).hexdigest() == digest


def test_dataset_balances_outcomes_and_languages():
    rows = gate.load_dataset(gate.load_contract())["fresh_sequences"]
    assert len(rows) == 9
    assert {row["language"] for row in rows} == {"zh", "en", "ja"}
    assert {
        outcome: sum(row["expected_outcome"] == outcome for row in rows)
        for outcome in ("supported", "contradicted", "unknown")
    } == {"supported": 3, "contradicted": 3, "unknown": 3}
    assert {
        language: sum(row["language"] == language for row in rows)
        for language in ("zh", "en", "ja")
    } == {"zh": 3, "en": 3, "ja": 3}


def test_dataset_turns_are_exactly_disjoint_from_prior_chain_datasets():
    contract = gate.load_contract()
    current = gate.load_dataset(contract)["fresh_sequences"]
    prior_turns = set()
    for path in (
        ROOT / "datasets/p4_ag_multiturn_ambiguity_outcome_v1.json",
        ROOT / "datasets/p4_ai_fresh_ambiguity_learning_chain_v1.json",
        ROOT / "datasets/p4_ah_multilingual_trigger_coverage_v1.json",
        ROOT / "datasets/p4_aj_japanese_morphology_v1.json",
    ):
        payload = json.loads(path.read_text(encoding="utf-8"))
        for section in payload.values():
            if not isinstance(section, list):
                continue
            for row in section:
                if isinstance(row, dict):
                    prior_turns.update(
                        str(row[key])
                        for key in ("input", "turn_1", "turn_2")
                        if row.get(key)
                    )
    current_turns = {row[key] for row in current for key in ("turn_1", "turn_2")}
    assert len(current_turns) == 18
    assert current_turns.isdisjoint(prior_turns)


def test_contract_forbids_post_result_tuning_and_overclaiming():
    contract = gate.load_contract()
    assert contract["gates"]["japanese_morphology_extension_count"] == 3
    assert contract["failure_policy"]["maximum_informed_correction_batches"] == 0
    assert contract["failure_policy"]["failed_result_must_be_preserved"] is True
    assert contract["failure_policy"]["real_product_or_safari_execution_authorized"] is False
    assert "not establish" in contract["claim_boundary"]
