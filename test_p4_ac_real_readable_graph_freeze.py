import copy
import hashlib
from pathlib import Path

import p4_ac_real_readable_graph_gate as gate
import p4_ac_safe_isolated_product_launcher as launcher


ROOT = Path(__file__).resolve().parent


def _sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _passing_fixture():
    contract = gate.load_contract()
    dataset = gate.load_dataset(contract)
    rows = []
    summaries = [
        "引用｜引文命題｜主體/動作/時間｜修正 4→0",
        "未支援來源｜歸屬未知｜欄位無｜保留原文 1→1",
    ]
    for case, summary in zip(dataset["turns"], summaries):
        supported = case["expected_visible_output"] is not None
        rows.append(
            {
                "turn": case["turn"],
                "input": case["input"],
                "visible_output": case["expected_visible_output"] or "今日は設計を見直してたんだね。",
                "visible_output_language": "Japanese",
                "episode_id": f"episode-{case['turn']}",
                "graph_visible": True,
                "p4_z_node_visible": True,
                "surface_chain": contract["surface_chain"],
                "graph_summary": summary,
                "logic_derived_summary": summary,
                "p4_z_violations_after": [] if supported else ["source_pattern_unavailable"],
                "p4_z_changed": supported,
                "end_to_end_seconds": 1.0,
            }
        )
    return {
        "schema": "uruha_p4_ac_real_readable_graph_evidence_v1",
        "case_id": dataset["case_id"],
        "dataset_sha256": contract["dataset"]["sha256"],
        "turns": rows,
        "metrics": {**contract["gates"], "maximum_turn_latency_seconds": 1.0, "maximum_total_latency_seconds": 2.0},
        "accounting": dict(contract["accounting"]),
        "safari": {"actual_two_turn_acceptance": True, "graph_summary_visually_observed_each_turn": True},
    }


def test_p4_ac_contract_binds_new_inputs_canonical_chain_and_no_rerun():
    contract = gate.load_contract()
    dataset = gate.load_dataset(contract)
    assert _sha256(ROOT / contract["dataset"]["path"]) == contract["dataset"]["sha256"]
    assert dataset["novelty"]["p4_aa_inputs_reused"] is False
    assert contract["surface_chain"] == [
        "utterance_frame_shadow_p4",
        "utterance_frame_coverage_extension_p4",
        "frame_preserving_visible_repair_p4",
        "source_bound_proposition_preservation_p4",
        "utterance",
    ]
    assert contract["failure_policy"]["same_case_rerun_allowed"] is False


def test_p4_ac_gate_accepts_readable_fixture_and_rejects_generic_or_mismatched_summary():
    fixture = _passing_fixture()
    assert gate.evaluate_evidence(gate.load_contract(), fixture)["status"] == "pass"
    broken = copy.deepcopy(fixture)
    broken["turns"][0]["graph_summary"] = "18 fields"
    broken["turns"][1]["surface_chain"][1] = "wrong_node"
    failures = gate.evaluate_evidence(gate.load_contract(), broken)["failed_gates"]
    assert "turn_1_summary_logic_mismatch" in failures
    assert "turn_1_generic_summary_not_replaced" in failures
    assert "turn_2_surface_chain_mismatch" in failures


def test_p4_ac_launcher_targets_additive_entry_and_private_runtime():
    assert launcher.ENTRYPOINT == ROOT / "uruha_web_ui_product_p4_ab.py"
    assert launcher._parser().parse_args(["check"]).port == 7873
    source = (ROOT / "p4_ac_safe_isolated_product_launcher.py").read_text(encoding="utf-8")
    assert "v2.preflight_v2" in source
    assert "v2.sandbox_command" in source
    assert "summary._INSTALLED_P4_AB" in source
