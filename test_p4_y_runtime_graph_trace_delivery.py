from copy import deepcopy
from pathlib import Path
import threading
from unittest import mock

import p4_y_runtime_graph_trace_delivery_gate as gate
import uruha_runtime_graph_trace_delivery_p4 as delivery
import uruha_web_ui as web


ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "datasets" / "p4_y_runtime_graph_trace_delivery_fixtures_v1.json"
EVIDENCE = ROOT / "analysis" / "p4_y_runtime_graph_trace_delivery_evidence_2026-09-22.json"
RESULT = ROOT / "analysis" / "p4_y_runtime_graph_trace_delivery_result_2026-09-22.json"


def _complete_result():
    logic = {
        label: {"schema": f"test:{label}", "trace_id": label}
        for label in delivery.TRACE_LABELS
    }
    return {
        "reply": "変更しない。",
        "logic": logic,
        "runtime_trace": {
            "blackboard": [
                {"stage": "observe", "label": "perception", "payload": {}},
                {"stage": "surface", "label": "utterance", "payload": {}},
            ]
        },
    }


def test_delivery_uses_exact_existing_payloads_before_utterance_without_surface_change():
    result = _complete_result()
    before = deepcopy(result)
    delivered = delivery.deliver_existing_surface_traces_p4(result)
    labels = [row["label"] for row in delivered["runtime_trace"]["blackboard"]]
    assert labels == ["perception", *delivery.TRACE_LABELS, "utterance"]
    assert delivered["reply"] == before["reply"]
    assert delivered["logic"] == before["logic"]
    for label in delivery.TRACE_LABELS:
        assert delivered["runtime_trace"][label] == before["logic"][label]
        assert [
            row["payload"]
            for row in delivered["runtime_trace"]["blackboard"]
            if row["label"] == label
        ] == [before["logic"][label]]
    assert delivered["runtime_trace"][delivery.LABEL]["delivery_complete"] is True


def test_delivery_replaces_stale_duplicates_and_does_not_synthesize_missing_trace():
    result = _complete_result()
    missing = delivery.TRACE_LABELS[1]
    result["logic"].pop(missing)
    result["runtime_trace"]["blackboard"] = [
        {"label": delivery.TRACE_LABELS[0], "payload": {"stale": 1}},
        {"label": delivery.TRACE_LABELS[0], "payload": {"stale": 2}},
        {"label": missing, "payload": {"stale": 3}},
        {"label": "utterance", "payload": {}},
    ]
    result["runtime_trace"][missing] = {"stale": True}
    delivered = delivery.deliver_existing_surface_traces_p4(result)
    labels = [row["label"] for row in delivered["runtime_trace"]["blackboard"]]
    assert labels.count(delivery.TRACE_LABELS[0]) == 1
    assert missing not in labels
    assert missing not in delivered["runtime_trace"]
    assert delivered["runtime_trace"][delivery.LABEL]["delivery_complete"] is False
    assert delivered["runtime_trace"][delivery.LABEL]["missing_labels"] == [missing]


def test_frozen_fixture_evidence_passes_acceptance_gate():
    evidence = delivery.build_fixture_evidence_p4_y(DATASET)
    result = gate.evaluate_evidence(gate.load_contract(), evidence)
    assert result["status"] == "pass", result["failed_gates"]
    assert evidence["metrics"] == gate.load_contract()["gates"]


def test_saved_evidence_and_result_are_reproducible():
    import json

    saved_evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    saved_result = json.loads(RESULT.read_text(encoding="utf-8"))
    assert delivery.build_fixture_evidence_p4_y(DATASET) == saved_evidence
    assert gate.evaluate_evidence(gate.load_contract(), saved_evidence) == saved_result


def test_post_run_wrapper_and_web_pipeline_keep_delivered_chain():
    class RuntimeState:
        def __init__(self):
            self.turn_traces = [{"blackboard": [{"label": "pre_refresh"}]}]

    class Brain:
        def __init__(self):
            self.runtime = RuntimeState()

    def final_base_run(brain, _user_text, input_context=None):
        result = _complete_result()
        result["runtime_trace"]["blackboard"] = [
            {"stage": "surface", "label": "utterance", "payload": {}},
            {"stage": "observe", "label": "runtime_latency_m19", "payload": {}},
        ]
        result["memory_data"] = {}
        result["runtime_state"] = {}
        return result

    wrapped = delivery.wrap_run_turn_debug_with_trace_delivery_p4(final_base_run)
    brain = Brain()
    brain.run_turn_debug = wrapped.__get__(brain, Brain)

    class Runtime:
        _lock = threading.Lock()
        _brain = brain
        _brain_load_trace = {"status": "ready", "elapsed_seconds": 0.0}

        def mark_activity(self):
            return None

        def get_brain(self):
            return self._brain

        def scheduler_trace(self):
            return {"schema": "test", "contains_raw_dialogue": False}

    with mock.patch.object(web, "RUNTIME", Runtime()):
        result = web._run_turn("fixture input", auto_tts=False)

    runtime_trace = result["cognition_trace"]["runtime_trace"]
    labels = [row["label"] for row in runtime_trace["blackboard"]]
    positions = [labels.index(label) for label in (*delivery.TRACE_LABELS, "utterance")]
    assert positions == sorted(positions)
    assert runtime_trace[delivery.LABEL]["delivery_complete"] is True
    assert brain.runtime.turn_traces[-1][delivery.LABEL]["delivery_complete"] is True
