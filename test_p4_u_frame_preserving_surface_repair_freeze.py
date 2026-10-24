import copy

import p4_u_frame_preserving_surface_repair_gate as gate


def _passing_fixture():
    contract = gate.load_contract()
    dataset = gate.load_dataset(contract)
    cases = []
    for partition in ("development_failures", "holdout_failures", "faithful_controls"):
        for frozen in dataset[partition]:
            cases.append(
                {
                    "case_id": frozen["case_id"],
                    "partition": partition,
                    "before_violations": frozen["expected_before_violations"],
                    "visible_reply": frozen["expected_reply"],
                    "after_violations": [],
                    "visible_output_language": "Japanese",
                    "changed": partition != "faithful_controls",
                    "trace_contains_raw_source_or_reply": False,
                    "model_call_added": False,
                    "fact_write_count": 0,
                    "profile_write_count": 0,
                    "episode_write_count": 0,
                }
            )
    return {
        "schema": "uruha_p4_u_frame_preserving_surface_repair_evidence_v1",
        "dataset_sha256": contract["dataset"]["sha256"],
        "cases": cases,
        "metrics": copy.deepcopy(contract["gates"]),
        "integration": {
            "additive_product_entry_installs_repair": True,
            "runtime_graph_node_test_passed": True,
            "released_product_entry_hash_preserved": True,
        },
    }


def test_contract_freezes_single_transform_and_forbids_case_specific_routing():
    contract = gate.load_contract()
    dataset = gate.load_dataset(contract)
    assert len(dataset["development_failures"]) == 4
    assert len(dataset["holdout_failures"]) == 12
    assert len(dataset["faithful_controls"]) == 8
    assert {row["language"] for row in dataset["holdout_failures"]} == {"zh", "en", "ja"}
    boundary = contract["implementation_boundary"]
    assert boundary["frame_classifier_change_allowed"] is False
    assert boundary["case_id_or_source_exact_match_routing_allowed"] is False
    assert boundary["model_call_added_allowed"] is False
    assert contract["failure_policy"]["maximum_informed_correction_batches"] == 2


def test_passing_fixture_passes_frozen_gate():
    result = gate.evaluate_evidence(gate.load_contract(), _passing_fixture())
    assert result["status"] == "pass"
    assert result["failed_gates"] == []


def test_gate_fails_closed_on_wrong_reply_unresolved_or_control_change():
    evidence = _passing_fixture()
    evidence["cases"][0]["visible_reply"] = "違う。"
    evidence["cases"][4]["after_violations"] = ["speaker_owner_shift_user_to_agent"]
    evidence["cases"][-1]["changed"] = True
    result = gate.evaluate_evidence(gate.load_contract(), evidence)
    assert "dev_p4s_t4_quote:visible_reply_mismatch" in result["failed_gates"]
    assert "holdout_owner_zh_u01:unresolved_violation" in result["failed_gates"]
    assert "control_hearsay_ja_u01:faithful_control_changed" in result["failed_gates"]


def test_gate_fails_closed_on_model_memory_or_predecessor_integration_failure():
    evidence = _passing_fixture()
    evidence["cases"][8]["model_call_added"] = True
    evidence["cases"][8]["episode_write_count"] = 1
    evidence["integration"]["released_product_entry_hash_preserved"] = False
    result = gate.evaluate_evidence(gate.load_contract(), evidence)
    assert "holdout_quote_en_u01:model_call_added" in result["failed_gates"]
    assert "holdout_quote_en_u01:memory_write_added" in result["failed_gates"]
    assert "released_product_entry_hash_not_preserved" in result["failed_gates"]
