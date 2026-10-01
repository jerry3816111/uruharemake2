import copy
import hashlib
from pathlib import Path

import p4_y_real_product_graph_delivery_gate as gate
import p4_y_safe_isolated_product_launcher as launcher


ROOT = Path(__file__).resolve().parent


def _sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _passing_fixture():
    contract = gate.load_contract()
    dataset = gate.load_dataset(contract)
    turns = []
    for row in dataset["turns"]:
        turns.append(
            {
                "turn": row["turn"],
                "input": row["input"],
                "visible_output_language": "Japanese",
                "episode_id": f"episode-{row['turn']}",
                "graph_visible": True,
                "surface_chain": contract["surface_chain"],
                "logic_p4_t_present": True,
                "logic_p4_v_present": True,
                "logic_p4_w_present": True,
                "graph_p4_t_present": True,
                "graph_p4_v_present": True,
                "graph_p4_w_present": True,
                "exact_logic_to_graph_payload_count": 3,
                "delivery_complete": True,
                "p4_i_selected": False,
                "end_to_end_seconds": 1.0,
            }
        )
    return {
        "schema": "uruha_p4_y_real_product_graph_delivery_evidence_v1",
        "case_id": contract["dataset"]["case_id"],
        "dataset_sha256": contract["dataset"]["sha256"],
        "turns": turns,
        "metrics": {
            **contract["gates"],
            "maximum_turn_latency_seconds": 1.0,
            "maximum_total_latency_seconds": 2.0,
        },
        "accounting": dict(contract["accounting"]),
        "safari": {
            "actual_two_turn_acceptance": True,
            "runtime_node_graph_observed_after_every_turn": True,
        },
    }


def test_contract_binds_new_prompts_entry_port_and_no_rerun_policy():
    contract = gate.load_contract()
    assert _sha256(ROOT / contract["dataset"]["path"]) == contract["dataset"]["sha256"]
    assert contract["runtime"]["listener"] == "127.0.0.1:7871"
    assert contract["runtime"]["product_entry"] == "uruha_web_ui_product_p4_y.py"
    assert contract["failure_policy"]["same_case_rerun_allowed"] is False
    assert contract["failure_policy"]["manual_trace_injection_allowed"] is False


def test_dataset_has_two_fresh_non_p4_x_prompts():
    dataset = gate.load_dataset(gate.load_contract())
    assert [row["turn"] for row in dataset["turns"]] == [1, 2]
    assert sorted(row["input_language"] for row in dataset["turns"]) == ["en", "ja"]
    assert dataset["novelty"]["input_occurrences_before_dataset_creation"] == 0
    assert dataset["novelty"]["p4_x_inputs_reused"] is False


def test_passing_fixture_passes_and_missing_graph_trace_fails_closed():
    fixture = _passing_fixture()
    assert gate.evaluate_evidence(gate.load_contract(), fixture)["status"] == "pass"
    negative = copy.deepcopy(fixture)
    negative["turns"][0]["graph_p4_v_present"] = False
    negative["metrics"]["p4_v_trace_count"] = 1
    result = gate.evaluate_evidence(gate.load_contract(), negative)
    assert "turn_1_trace_missing" in result["failed_gates"]
    assert "metric_mismatch:p4_v_trace_count" in result["failed_gates"]


def test_order_payload_and_tab_failures_are_rejected():
    fixture = _passing_fixture()
    fixture["turns"][0]["surface_chain"] = list(reversed(fixture["turns"][0]["surface_chain"]))
    fixture["turns"][1]["exact_logic_to_graph_payload_count"] = 2
    fixture["accounting"]["closed_user_tab_count"] = 1
    result = gate.evaluate_evidence(gate.load_contract(), fixture)
    assert "turn_1_surface_chain_mismatch" in result["failed_gates"]
    assert "turn_2_payload_mismatch" in result["failed_gates"]
    assert "accounting_mismatch:closed_user_tab_count" in result["failed_gates"]


def test_safe_launcher_targets_p4_y_and_preserves_isolation():
    assert launcher.ENTRYPOINT == ROOT / "uruha_web_ui_product_p4_y.py"
    assert launcher._parser().parse_args(["check"]).port == 7871
    source = (ROOT / "p4_y_safe_isolated_product_launcher.py").read_text(encoding="utf-8")
    assert "v2.preflight_v2" in source
    assert "v2.sandbox_command" in source
    assert "delivery._INSTALLED_P4_Y" in source
