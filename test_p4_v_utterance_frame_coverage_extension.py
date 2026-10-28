import json
import os
from pathlib import Path
import subprocess

import p4_b_safe_isolated_product_launcher as p4b
import p4_v_utterance_frame_coverage_extension_gate as gate
import uruha_utterance_frame_shadow_extension_p4 as p4v
import uruha_utterance_frame_shadow_p4 as p4t


ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "datasets" / "p4_v_utterance_frame_coverage_extension_v1.json"


def test_all_frozen_base_extension_and_effective_violations_match_without_surface_mutation():
    dataset = json.loads(DATASET.read_text(encoding="utf-8"))
    for partition in ("development_failures", "holdout_failures", "faithful_controls"):
        for frozen in dataset[partition]:
            visible, trace = p4v.shadow_visible_reply_extension_p4(frozen["source"], frozen["candidate"])
            assert visible == frozen["candidate"]
            assert trace["base_violations"] == frozen["expected_base_violations"], frozen["case_id"]
            assert trace["extension_evidence"] == frozen["expected_extension_evidence"], frozen["case_id"]
            assert trace["violations"] == frozen["expected_violations"], frozen["case_id"]
            assert trace["candidate_unchanged"] is True
            assert trace["model_call_added"] is False
            assert trace["fact_write_count"] == trace["profile_write_count"] == trace["episode_write_count"] == 0
            encoded = json.dumps(trace, ensure_ascii=False)
            assert frozen["source"] not in encoded
            assert frozen["candidate"] not in encoded


def test_same_time_but_different_agent_action_is_not_a_speaker_shift():
    source = "我後天要擦乾紫色滑板。"
    reply = "うちは明後日ここで待ってる。"
    trace = p4v.inspect_utterance_frame_coverage_extension_p4(source, reply)
    assert trace["abstract_alignment"]["shared_time_anchors"] == ["day_after_tomorrow"]
    assert trace["abstract_alignment"]["shared_action_concepts"] == []
    assert trace["violations"] == []


def test_hypothetical_extension_supersedes_base_quote_false_positive_without_changing_base_trace():
    source = 'Suppose I said "I would cancel the red ticket"; keep that as an assumption.'
    reply = "赤いチケットの話は仮定として扱う。"
    base = p4t.inspect_utterance_frame_shadow_p4(source, reply)
    trace = p4v.inspect_utterance_frame_coverage_extension_p4(source, reply, base_trace=base)
    assert base["violations"] == ["quoted_content_promoted_to_assertion"]
    assert trace["base_violations"] == base["violations"]
    assert trace["violations"] == []


def test_runtime_graph_node_is_inserted_after_p4_t_and_once_before_utterance():
    reply = "うちは今夜オレンジのフォルダを整理する。"
    trace = p4v.inspect_utterance_frame_coverage_extension_p4("我今晚要整理橘色資料夾。", reply)
    result = {
        "reply": reply,
        "logic": {p4v.LABEL: trace},
        "runtime_trace": {
            "blackboard": [
                {"stage": "surface", "label": p4t.LABEL, "payload": {}},
                {"stage": "surface", "label": "utterance", "payload": {"text": reply}},
            ]
        },
    }
    updated = p4v.append_utterance_frame_extension_node_p4(result)
    assert [row["label"] for row in updated["runtime_trace"]["blackboard"]] == [p4t.LABEL, p4v.LABEL, "utterance"]
    assert updated["reply"] == reply
    updated = p4v.append_utterance_frame_extension_node_p4(updated)
    assert [row["label"] for row in updated["runtime_trace"]["blackboard"]].count(p4v.LABEL) == 1


def test_additive_product_entry_import_reuses_runtime_and_installs_both_shadows_without_loading_brain():
    program = r'''
import json
import uruha_web_ui_product_p4_v as entry
import uruha_web_ui_product_p4_t as predecessor
import uruha_utterance_frame_shadow_p4 as p4t
import uruha_utterance_frame_shadow_extension_p4 as p4v
print(json.dumps({
    "runtime_reused": entry.RUNTIME is predecessor.RUNTIME,
    "p4_t_installed": p4t._INSTALLED_P4_T,
    "p4_v_installed": p4v._INSTALLED_P4_V,
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
        "runtime_reused": True,
    }


def test_builder_passes_the_frozen_gate():
    evidence = p4v.build_dataset_evidence_p4_v(DATASET)
    result = gate.evaluate_evidence(gate.load_contract(), evidence)
    assert result["status"] == "pass", result["failed_gates"]
    metrics = evidence["metrics"]
    assert metrics["development_exact_violation_count"] == 7
    assert metrics["holdout_exact_violation_count"] == 9
    assert metrics["faithful_control_false_positive_count"] == 0
    assert metrics["candidate_unchanged_count"] == 25
    assert metrics["new_model_call_count"] == 0
