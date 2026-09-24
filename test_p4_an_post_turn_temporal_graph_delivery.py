import json
from pathlib import Path

import p4_an_post_turn_temporal_graph_gate as gate
import uruha_post_turn_temporal_graph_delivery_p4 as post
import uruha_runtime_temporal_graph_delivery_p4 as p4_am


ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "datasets" / "p4_an_post_turn_temporal_graph_v1.json"


def test_post_turn_delivery_uses_existing_payload_without_synthesis():
    payload = {
        "schema": p4_am.SCHEMA,
        "summary": "過去 0｜現在 6候選｜本輪未來 已封存",
    }
    result = {
        "reply": "unchanged",
        "logic": {p4_am.LABEL: payload},
        "runtime_trace": {
            p4_am.LABEL: payload,
            "blackboard": [{"stage": "surface", "label": "utterance", "payload": {}}],
        },
    }
    delivered = post.deliver_existing_temporal_payload_after_turn_p4(result)
    labels = [row["label"] for row in delivered["runtime_trace"]["blackboard"]]
    assert labels == [p4_am.LABEL, "utterance"]
    assert delivered["reply"] == "unchanged"
    missing = post.deliver_existing_temporal_payload_after_turn_p4(
        {"logic": {}, "runtime_trace": {"blackboard": []}}
    )
    assert missing["runtime_trace"]["blackboard"] == []


def test_offline_fresh_three_turn_delivery_passes_frozen_gate():
    evidence = post.build_offline_evidence_p4_an(DATASET)
    assert [row["past_record_count"] for row in evidence["turns"]] == [0, 0, 1]
    assert all(row["final_blackboard_contains_node"] for row in evidence["turns"])
    assert evidence["metrics"]["same_turn_outcome_promoted_to_past_count"] == 0
    assert gate.evaluate_offline_evidence(gate.load_contract(), evidence)["status"] == "pass"


def test_offline_evidence_contains_no_frozen_dialogue_or_reply_change():
    dataset = json.loads(DATASET.read_text(encoding="utf-8"))
    evidence = post.build_offline_evidence_p4_an(DATASET)
    serialized = json.dumps(evidence, ensure_ascii=False, sort_keys=True)
    assert all(row["input"] not in serialized for row in dataset["turns"])
    assert evidence["metrics"]["raw_or_private_payload_leak_count"] == 0
    assert evidence["metrics"]["visible_reply_changed_count"] == 0


def test_product_and_launcher_install_only_post_turn_delivery():
    entry = (ROOT / "uruha_web_ui_product_p4_an.py").read_text(encoding="utf-8")
    launcher = (ROOT / "p4_an_safe_isolated_product_launcher.py").read_text(encoding="utf-8")
    assert "import uruha_web_ui_product_p4_am as _p4_am" in entry
    assert "install_post_turn_temporal_graph_delivery_p4()" in entry
    assert 'ENTRYPOINT = ROOT / "uruha_web_ui_product_p4_an.py"' in launcher
    assert "sandboxed_p4_an_probe" in launcher
