import copy
import hashlib
from pathlib import Path

import p4_aa_real_product_source_proposition_gate as gate
import p4_aa_safe_isolated_product_launcher as launcher


ROOT = Path(__file__).resolve().parent


def _sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _passing_fixture():
    contract = gate.load_contract()
    dataset = gate.load_dataset(contract)
    turns = []
    for row in dataset["turns"]:
        supported = row["expected_visible_output"] is not None
        turns.append({
            "turn": row["turn"],
            "input": row["input"],
            "visible_output": row["expected_visible_output"] or "頭が止まらなかったのか。そりゃ疲れるだろ。",
            "visible_output_language": "Japanese",
            "episode_id": f"episode-{row['turn']}",
            "graph_visible": True,
            "surface_chain": contract["surface_chain"],
            "logic_p4_t_present": True,
            "logic_p4_v_present": True,
            "logic_p4_w_present": True,
            "logic_p4_z_present": True,
            "graph_p4_t_present": True,
            "graph_p4_v_present": True,
            "graph_p4_w_present": True,
            "graph_p4_z_present": True,
            "exact_logic_to_graph_payload_count": 4,
            "p4_z_status": "repaired_and_verified" if supported else "source_pattern_unavailable",
            "p4_z_violations_after": [] if supported else ["source_pattern_unavailable"],
            "p4_z_changed": supported,
            "p4_i_selected": False,
            "end_to_end_seconds": 1.0,
        })
    return {
        "schema": "uruha_p4_aa_real_product_source_proposition_evidence_v1",
        "case_id": contract["dataset"]["case_id"],
        "dataset_sha256": contract["dataset"]["sha256"],
        "turns": turns,
        "metrics": {**contract["gates"], "maximum_turn_latency_seconds": 1.0, "maximum_total_latency_seconds": 4.0},
        "accounting": dict(contract["accounting"]),
        "safari": {"actual_four_turn_acceptance": True, "runtime_node_graph_observed_after_every_turn": True},
    }


def test_p4_aa_contract_binds_fresh_port_entry_and_no_rerun_policy():
    contract = gate.load_contract()
    assert _sha256(ROOT / contract["dataset"]["path"]) == contract["dataset"]["sha256"]
    assert contract["runtime"]["listener"] == "127.0.0.1:7872"
    assert contract["runtime"]["product_entry"] == "uruha_web_ui_product_p4_z.py"
    assert contract["failure_policy"]["same_case_rerun_allowed"] is False
    assert contract["failure_policy"]["prompt_or_gate_change_after_result_allowed"] is False


def test_p4_aa_dataset_has_four_fresh_cross_language_turns_and_one_unsupported_control():
    dataset = gate.load_dataset(gate.load_contract())
    assert [row["turn"] for row in dataset["turns"]] == [1, 2, 3, 4]
    assert sorted(row["input_language"] for row in dataset["turns"]) == ["en", "ja", "ja", "zh"]
    assert sum(row["expected_visible_output"] is not None for row in dataset["turns"]) == 3
    assert dataset["novelty"]["exact_input_occurrences_before_dataset_creation"] == 0
    assert dataset["novelty"]["p4_z_unit_inputs_reused"] is False


def test_p4_aa_passing_fixture_passes_and_semantic_failures_fail_closed():
    fixture = _passing_fixture()
    assert gate.evaluate_evidence(gate.load_contract(), fixture)["status"] == "pass"
    negative = copy.deepcopy(fixture)
    negative["turns"][0]["visible_output"] = "「別の内容」っていう引用なんだね。"
    negative["turns"][1]["p4_z_violations_after"] = ["source_object_missing"]
    result = gate.evaluate_evidence(gate.load_contract(), negative)
    assert "turn_1_visible_output_mismatch" in result["failed_gates"]
    assert "turn_2_source_proposition_unresolved" in result["failed_gates"]


def test_p4_aa_trace_order_payload_unsupported_noop_and_tab_failures_are_rejected():
    fixture = _passing_fixture()
    fixture["turns"][0]["surface_chain"] = list(reversed(fixture["turns"][0]["surface_chain"]))
    fixture["turns"][1]["exact_logic_to_graph_payload_count"] = 3
    fixture["turns"][3]["p4_z_changed"] = True
    fixture["accounting"]["closed_user_tab_count"] = 1
    result = gate.evaluate_evidence(gate.load_contract(), fixture)
    assert "turn_1_surface_chain_mismatch" in result["failed_gates"]
    assert "turn_2_payload_mismatch" in result["failed_gates"]
    assert "turn_4_unsupported_source_changed" in result["failed_gates"]
    assert "accounting_mismatch:closed_user_tab_count" in result["failed_gates"]


def test_p4_aa_safe_launcher_targets_p4_z_and_preserves_isolation():
    assert launcher.ENTRYPOINT == ROOT / "uruha_web_ui_product_p4_z.py"
    assert launcher._parser().parse_args(["check"]).port == 7872
    source = (ROOT / "p4_aa_safe_isolated_product_launcher.py").read_text(encoding="utf-8")
    assert "v2.preflight_v2" in source
    assert "v2.sandbox_command" in source
    assert "preservation._INSTALLED_P4_Z" in source
