import json
import os
from pathlib import Path
import subprocess

import p4_b_safe_isolated_product_launcher as p4b
import p4_w_frame_preserving_visible_repair_gate as gate
import uruha_frame_preserving_visible_repair_p4 as p4w
import uruha_utterance_frame_shadow_extension_p4 as p4v
import uruha_utterance_frame_shadow_p4 as p4t


ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "datasets" / "p4_w_frame_preserving_visible_repair_v1.json"


def test_all_frozen_repairs_and_controls_match_without_unresolved_violations():
    dataset = json.loads(DATASET.read_text(encoding="utf-8"))
    for partition in ("development_failures", "holdout_failures", "faithful_controls"):
        for frozen in dataset[partition]:
            before = p4v.inspect_utterance_frame_coverage_extension_p4(frozen["source"], frozen["candidate"])
            visible, trace = p4w.repair_visible_reply_p4(frozen["source"], frozen["candidate"], effective_trace=before)
            assert trace["before_violations"] == frozen["expected_before_violations"], frozen["case_id"]
            assert visible == frozen["expected_reply"], frozen["case_id"]
            assert trace["after_violations"] == [], frozen["case_id"]
            assert trace["visible_output_language"] == "Japanese"
            assert trace["model_call_added"] is False
            assert trace["fact_write_count"] == trace["profile_write_count"] == trace["episode_write_count"] == 0
            if partition == "faithful_controls":
                assert trace["changed"] is False
            encoded = json.dumps(trace, ensure_ascii=False)
            assert frozen["source"] not in encoded
            assert visible not in encoded


def test_no_violation_is_a_strict_noop_even_for_agent_first_person_surface():
    source = "我明天要整理灰色工具箱。"
    candidate = "うちは明日ここで待ってる。"
    before = p4v.inspect_utterance_frame_coverage_extension_p4(source, candidate)
    visible, trace = p4w.repair_visible_reply_p4(source, candidate, effective_trace=before)
    assert before["violations"] == []
    assert visible == candidate
    assert trace["strategy"] == "no_violation_noop"
    assert trace["changed"] is False


def test_runtime_graph_node_is_inserted_after_p4_v_and_once_before_utterance():
    source = "我明天要整理灰色工具箱。"
    candidate = "うちは明日、灰色の工具箱を整理する。"
    visible, trace = p4w.repair_visible_reply_p4(source, candidate)
    result = {
        "reply": visible,
        "logic": {p4w.LABEL: trace},
        "runtime_trace": {
            "blackboard": [
                {"stage": "surface", "label": p4t.LABEL, "payload": {}},
                {"stage": "surface", "label": p4v.LABEL, "payload": {}},
                {"stage": "surface", "label": "utterance", "payload": {"text": visible}},
            ]
        },
    }
    updated = p4w.append_frame_preserving_repair_node_p4(result)
    assert [row["label"] for row in updated["runtime_trace"]["blackboard"]] == [
        p4t.LABEL,
        p4v.LABEL,
        p4w.LABEL,
        "utterance",
    ]
    updated = p4w.append_frame_preserving_repair_node_p4(updated)
    assert [row["label"] for row in updated["runtime_trace"]["blackboard"]].count(p4w.LABEL) == 1


def test_additive_product_entry_import_reuses_runtime_and_installs_full_surface_chain_without_loading_brain():
    program = r'''
import json
import uruha_web_ui_product_p4_w as entry
import uruha_web_ui_product_p4_v as predecessor
import uruha_utterance_frame_shadow_p4 as p4t
import uruha_utterance_frame_shadow_extension_p4 as p4v
import uruha_frame_preserving_visible_repair_p4 as p4w
print(json.dumps({
    "runtime_reused": entry.RUNTIME is predecessor.RUNTIME,
    "p4_t_installed": p4t._INSTALLED_P4_T,
    "p4_v_installed": p4v._INSTALLED_P4_V,
    "p4_w_installed": p4w._INSTALLED_P4_W,
    "brain_loaded": entry.RUNTIME._brain is not None,
}, sort_keys=True))
'''
    completed = subprocess.run(
        [str(p4b.resolve_python(None, os.environ, root=ROOT)), "-c", program],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert json.loads(completed.stdout.strip().splitlines()[-1]) == {
        "brain_loaded": False,
        "p4_t_installed": True,
        "p4_v_installed": True,
        "p4_w_installed": True,
        "runtime_reused": True,
    }


def test_builder_passes_the_frozen_gate():
    evidence = p4w.build_dataset_evidence_p4_w(DATASET)
    result = gate.evaluate_evidence(gate.load_contract(), evidence)
    assert result["status"] == "pass", result["failed_gates"]
    metrics = evidence["metrics"]
    assert metrics["development_exact_reply_count"] == 4
    assert metrics["holdout_exact_reply_count"] == 12
    assert metrics["faithful_control_unchanged_count"] == 8
    assert metrics["new_model_call_count"] == 0
