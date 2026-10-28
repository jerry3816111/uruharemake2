import copy
import hashlib
from pathlib import Path

import p4_y_runtime_graph_trace_delivery_gate as gate


ROOT = Path(__file__).resolve().parent


def _sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _passing_fixture():
    contract = gate.load_contract()
    dataset = gate.load_dataset(contract)
    cases = []
    for row in dataset["cases"]:
        cases.append(
            {
                "case_id": row["case_id"],
                "surface_chain": row["expected_surface_chain"],
                "delivery_complete": row["expected_complete"],
                "visible_reply_unchanged": True,
                "logic_unchanged": True,
                "missing_trace_synthesized": False,
                "duplicate_trace_label_count": 0,
                "exact_trace_payload_count": len(row["logic_trace_ids"]),
            }
        )
    return {
        "schema": "uruha_p4_y_runtime_graph_trace_delivery_evidence_v1",
        "dataset_sha256": contract["dataset"]["sha256"],
        "cases": cases,
        "metrics": dict(contract["gates"]),
        "integration": dict(contract["integration"]),
    }


def test_contract_binds_fixtures_predecessors_and_no_rerun_policy():
    contract = gate.load_contract()
    assert _sha256(ROOT / contract["dataset"]["path"]) == contract["dataset"]["sha256"]
    assert contract["surface_chain"][-1] == "utterance"
    assert contract["failure_policy"]["missing_trace_may_be_synthesized"] is False
    assert contract["failure_policy"]["p4_x_same_case_rerun_allowed"] is False


def test_fixture_has_complete_duplicate_and_missing_trace_cases():
    dataset = gate.load_dataset(gate.load_contract())
    assert [row["case_id"] for row in dataset["cases"]] == [
        "complete_clean",
        "complete_stale_duplicates",
        "missing_extension_trace",
    ]
    assert [row["expected_complete"] for row in dataset["cases"]] == [True, True, False]
    assert len(dataset["cases"][1]["initial_blackboard_labels"]) != len(
        set(dataset["cases"][1]["initial_blackboard_labels"])
    )
    assert "utterance_frame_coverage_extension_p4" not in dataset["cases"][2]["logic_trace_ids"]


def test_passing_fixture_passes_and_trace_synthesis_fails_closed():
    fixture = _passing_fixture()
    assert gate.evaluate_evidence(gate.load_contract(), fixture)["status"] == "pass"
    negative = copy.deepcopy(fixture)
    negative["cases"][2]["missing_trace_synthesized"] = True
    negative["metrics"]["missing_trace_synthesized_count"] = 1
    result = gate.evaluate_evidence(gate.load_contract(), negative)
    assert "case_missing_extension_trace_trace_synthesized" in result["failed_gates"]
    assert "metric_mismatch:missing_trace_synthesized_count" in result["failed_gates"]


def test_reply_logic_order_and_integration_failures_are_rejected():
    fixture = _passing_fixture()
    fixture["cases"][0]["visible_reply_unchanged"] = False
    fixture["cases"][1]["surface_chain"] = list(reversed(fixture["cases"][1]["surface_chain"]))
    fixture["integration"]["delivery_runs_after_run_turn_debug_final_blackboard_refresh"] = False
    result = gate.evaluate_evidence(gate.load_contract(), fixture)
    assert "case_complete_clean_visible_changed" in result["failed_gates"]
    assert "case_complete_stale_duplicates_surface_chain_mismatch" in result["failed_gates"]
    assert (
        "integration_mismatch:delivery_runs_after_run_turn_debug_final_blackboard_refresh"
        in result["failed_gates"]
    )
