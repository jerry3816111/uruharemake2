import json
import os
from pathlib import Path
import subprocess

import p4_b_safe_isolated_product_launcher as p4b
import uruha_utterance_frame_shadow_p4 as p4t


ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "datasets" / "p4_t_utterance_frame_shadow_v1.json"


def test_all_frozen_frames_and_violations_match_without_surface_mutation():
    dataset = json.loads(DATASET.read_text(encoding="utf-8"))
    for partition in ("development_failures", "holdout_failures", "plain_controls"):
        for frozen in dataset[partition]:
            visible, trace = p4t.shadow_visible_reply_p4(frozen["source"], frozen["candidate"])
            assert visible == frozen["candidate"]
            if "expected_frame" in frozen:
                assert trace["frame"] == frozen["expected_frame"], frozen["case_id"]
            assert trace["violations"] == frozen["expected_violations"], frozen["case_id"]
            assert trace["mode"] == "shadow_only"
            assert trace["model_call_added"] is False
            assert trace["fact_write_count"] == 0
            assert trace["profile_write_count"] == 0
            assert trace["episode_write_count"] == 0
            encoded = json.dumps(trace, ensure_ascii=False)
            assert frozen["source"] not in encoded
            assert frozen["candidate"] not in encoded


def test_runtime_graph_node_is_inserted_once_before_utterance_and_reply_is_untouched():
    reply = "うちは図を確認するんだね。"
    trace = p4t.inspect_utterance_frame_shadow_p4("我先確認圖。", reply)
    result = {
        "reply": reply,
        "logic": {p4t.LABEL: trace},
        "runtime_trace": {
            "blackboard": [
                {"stage": "plan", "label": "existing", "payload": {}},
                {"stage": "surface", "label": "utterance", "payload": {"text": reply}},
            ]
        },
    }
    updated = p4t.append_utterance_frame_node_p4(result)
    labels = [row["label"] for row in updated["runtime_trace"]["blackboard"]]
    assert labels == ["existing", p4t.LABEL, "utterance"]
    assert updated["runtime_trace"][p4t.LABEL] == trace
    assert updated["reply"] == reply
    updated = p4t.append_utterance_frame_node_p4(updated)
    assert [row["label"] for row in updated["runtime_trace"]["blackboard"]].count(p4t.LABEL) == 1


def test_additive_product_entry_installs_p4_t_after_released_p4_o_entry():
    source = (ROOT / "uruha_web_ui_product_p4_t.py").read_text(encoding="utf-8")
    assert "import uruha_web_ui_product_p4_o as _p4_o" in source
    assert "from uruha_utterance_frame_shadow_p4 import install_utterance_frame_shadow_p4" in source
    assert "install_utterance_frame_shadow_p4()" in source
    assert source.index("import uruha_web_ui_product_p4_o as _p4_o") < source.index("install_utterance_frame_shadow_p4()")
    assert "RUNTIME = _p4_o.RUNTIME" in source


def test_additive_product_entry_import_reuses_runtime_without_loading_brain():
    program = r'''
import json
import uruha_web_ui_product_p4_t as entry
import uruha_web_ui_product_p4_o as predecessor
import uruha_utterance_frame_shadow_p4 as p4t
print(json.dumps({
    "entry_imported": True,
    "runtime_reused": entry.RUNTIME is predecessor.RUNTIME,
    "shadow_installed": p4t._INSTALLED_P4_T,
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
    observed = json.loads(completed.stdout.strip().splitlines()[-1])
    assert observed == {
        "brain_loaded": False,
        "entry_imported": True,
        "runtime_reused": True,
        "shadow_installed": True,
    }


def test_builder_reports_exact_frozen_metrics_before_gate_integration_flags():
    evidence = p4t.build_dataset_evidence_p4_t(DATASET)
    metrics = evidence["metrics"]
    assert metrics["development_exact_frame_count"] == 4
    assert metrics["development_exact_violation_count"] == 4
    assert metrics["holdout_exact_frame_count"] == 12
    assert metrics["holdout_exact_violation_count"] == 12
    assert metrics["plain_control_false_positive_count"] == 0
    assert metrics["candidate_unchanged_count"] == 24
    assert metrics["raw_source_or_reply_trace_count"] == 0
    assert metrics["new_model_call_count"] == 0
