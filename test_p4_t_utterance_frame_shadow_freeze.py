import copy
import json

import p4_t_utterance_frame_shadow_gate as gate


def _passing_fixture():
    contract = gate.load_contract()
    dataset = gate.load_dataset(contract)
    cases = []
    for partition in ("development_failures", "holdout_failures", "plain_controls"):
        for frozen in dataset[partition]:
            cases.append(
                {
                    "case_id": frozen["case_id"],
                    "partition": partition,
                    "frame": frozen.get("expected_frame"),
                    "violations": frozen["expected_violations"],
                    "candidate_unchanged": True,
                    "trace_contains_raw_source_or_reply": False,
                    "model_call_added": False,
                    "fact_write_count": 0,
                    "profile_write_count": 0,
                    "episode_write_count": 0,
                }
            )
    return {
        "schema": "uruha_p4_t_utterance_frame_shadow_evidence_v1",
        "dataset_sha256": contract["dataset"]["sha256"],
        "cases": cases,
        "metrics": copy.deepcopy(contract["gates"]),
        "integration": {
            "product_entry_installs_shadow_detector": True,
            "runtime_graph_node_test_passed": True,
            "visible_reply_unchanged_test_passed": True,
        },
    }


def test_contract_freezes_partitions_languages_and_shadow_only_boundary():
    contract = gate.load_contract()
    dataset = gate.load_dataset(contract)
    assert len(dataset["development_failures"]) == 4
    assert len(dataset["holdout_failures"]) == 12
    assert len(dataset["plain_controls"]) == 8
    assert {row["language"] for row in dataset["holdout_failures"]} == {"zh", "en", "ja"}
    assert contract["implementation_boundary"]["visible_reply_change_allowed"] is False
    assert contract["implementation_boundary"]["existing_m39_file_change_allowed"] is False
    assert contract["failure_policy"]["maximum_informed_correction_batches"] == 2


def test_passing_fixture_passes_frozen_gate():
    result = gate.evaluate_evidence(gate.load_contract(), _passing_fixture())
    assert result["status"] == "pass"
    assert result["failed_gates"] == []


def test_gate_fails_closed_on_missed_failure_false_positive_and_visible_mutation():
    evidence = _passing_fixture()
    evidence["cases"][0]["violations"] = []
    evidence["cases"][-1]["violations"] = ["spurious"]
    evidence["cases"][4]["candidate_unchanged"] = False
    evidence["integration"]["visible_reply_unchanged_test_passed"] = False
    result = gate.evaluate_evidence(gate.load_contract(), evidence)
    assert "dev_p4s_t4_quotation_ja:violation_mismatch" in result["failed_gates"]
    assert "control_hearsay_ja_01:violation_mismatch" in result["failed_gates"]
    assert "holdout_owner_zh_01:candidate_changed" in result["failed_gates"]
    assert "shadow_mutated_visible_reply" in result["failed_gates"]


def test_gate_fails_closed_on_model_or_memory_side_effect():
    evidence = _passing_fixture()
    evidence["cases"][6]["model_call_added"] = True
    evidence["cases"][6]["profile_write_count"] = 1
    result = gate.evaluate_evidence(gate.load_contract(), evidence)
    assert "holdout_owner_ja_01:model_call_added" in result["failed_gates"]
    assert "holdout_owner_ja_01:memory_write_added" in result["failed_gates"]


def test_dataset_contains_no_duplicate_case_ids():
    dataset = gate.load_dataset(gate.load_contract())
    ids = [
        row["case_id"]
        for partition in ("development_failures", "holdout_failures", "plain_controls")
        for row in dataset[partition]
    ]
    assert len(ids) == 24
    assert len(ids) == len(set(ids))
