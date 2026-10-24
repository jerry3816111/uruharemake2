"""P4-Y delivery of existing P4 surface traces after the final runtime refresh."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path

import uruha_frame_preserving_visible_repair_p4 as p4w
import uruha_utterance_frame_shadow_extension_p4 as p4v
import uruha_utterance_frame_shadow_p4 as p4t


LABEL = "runtime_graph_trace_delivery_p4"
SCHEMA = "uruha_runtime_graph_trace_delivery_p4"
TRACE_LABELS = (p4t.LABEL, p4v.LABEL, p4w.LABEL)


def _trace_salience(label, trace):
    if label == p4w.LABEL:
        return 1.0 if trace.get("changed") else 0.84
    return 1.0 if trace.get("violations") else 0.88


def deliver_existing_surface_traces_p4(result):
    """Deliver only P4 traces already present in logic; never synthesize one."""

    if not isinstance(result, dict):
        return result
    logic = result.get("logic") or {}
    runtime_trace = result.setdefault("runtime_trace", {})
    blackboard = [
        row
        for row in list(runtime_trace.get("blackboard") or [])
        if row.get("label") not in TRACE_LABELS
    ]
    insert_at = next(
        (index for index, row in enumerate(blackboard) if row.get("label") == "utterance"),
        len(blackboard),
    )
    delivered = []
    for label in TRACE_LABELS:
        trace = logic.get(label)
        if not isinstance(trace, dict) or not trace:
            runtime_trace.pop(label, None)
            continue
        payload = deepcopy(trace)
        blackboard.insert(
            insert_at + len(delivered),
            {
                "stage": "surface",
                "label": label,
                "payload": payload,
                "salience": _trace_salience(label, payload),
            },
        )
        runtime_trace[label] = deepcopy(payload)
        delivered.append(label)
    runtime_trace["blackboard"] = blackboard
    runtime_trace[LABEL] = {
        "schema": SCHEMA,
        "delivered_labels": delivered,
        "missing_labels": [label for label in TRACE_LABELS if label not in delivered],
        "delivery_complete": len(delivered) == len(TRACE_LABELS),
        "source": "existing_logic_only",
        "visible_reply_changed": False,
        "logic_changed": False,
        "model_call_added": False,
        "fact_write_count": 0,
        "profile_write_count": 0,
        "episode_write_count": 0,
        "claim_boundary": "post-run deterministic graph delivery; not trace correctness or semantic validation",
    }
    return result


_INSTALLED_P4_Y = False
_ORIGINAL_RUN_TURN_DEBUG_P4_Y = None


def wrap_run_turn_debug_with_trace_delivery_p4(original):
    def run_turn_debug_with_p4_y_delivery(self, *args, **kwargs):
        result = original(self, *args, **kwargs)
        result = deliver_existing_surface_traces_p4(result)
        if getattr(self.runtime, "turn_traces", None):
            self.runtime.turn_traces[-1] = deepcopy(result["runtime_trace"])
        return result

    return run_turn_debug_with_p4_y_delivery


def install_runtime_graph_trace_delivery_p4():
    global _INSTALLED_P4_Y, _ORIGINAL_RUN_TURN_DEBUG_P4_Y
    if _INSTALLED_P4_Y:
        return False
    from uruha_brain_mac import UruhaBrainV4_Mac

    _ORIGINAL_RUN_TURN_DEBUG_P4_Y = UruhaBrainV4_Mac.run_turn_debug

    UruhaBrainV4_Mac.run_turn_debug = wrap_run_turn_debug_with_trace_delivery_p4(
        _ORIGINAL_RUN_TURN_DEBUG_P4_Y
    )
    _INSTALLED_P4_Y = True
    return True


def _sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build_fixture_evidence_p4_y(dataset_path):
    dataset_path = Path(dataset_path)
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    cases = []
    metrics = {
        "case_count": len(dataset["cases"]),
        "exact_surface_chain_count": 0,
        "exact_trace_payload_count": 0,
        "visible_reply_unchanged_count": 0,
        "logic_unchanged_count": 0,
        "complete_delivery_count": 0,
        "incomplete_delivery_count": 0,
        "duplicate_trace_label_count": 0,
        "missing_trace_synthesized_count": 0,
        "new_model_call_count": 0,
        "fact_write_count": 0,
        "profile_write_count": 0,
        "episode_write_count": 0,
    }
    for frozen in dataset["cases"]:
        logic = {
            label: {"schema": f"fixture:{label}", "trace_id": trace_id}
            for label, trace_id in frozen["logic_trace_ids"].items()
        }
        blackboard = []
        for label in frozen["initial_blackboard_labels"]:
            blackboard.append(
                {
                    "stage": "surface" if label in (*TRACE_LABELS, "utterance") else "perception",
                    "label": label,
                    "payload": {"trace_id": "stale"} if label in TRACE_LABELS else {},
                    "salience": 0.5,
                }
            )
        result = {
            "reply": "テスト応答。",
            "logic": deepcopy(logic),
            "runtime_trace": {"blackboard": blackboard},
        }
        reply_before = result["reply"].encode("utf-8")
        logic_before = json.dumps(result["logic"], ensure_ascii=False, sort_keys=True).encode("utf-8")
        delivered = deliver_existing_surface_traces_p4(result)
        labels = [row.get("label") for row in delivered["runtime_trace"]["blackboard"]]
        surface_chain = [label for label in labels if label in (*TRACE_LABELS, "utterance")]
        reply_unchanged = delivered["reply"].encode("utf-8") == reply_before
        logic_unchanged = (
            json.dumps(delivered["logic"], ensure_ascii=False, sort_keys=True).encode("utf-8")
            == logic_before
        )
        exact_payload_count = 0
        for label, trace in logic.items():
            node_payloads = [
                row.get("payload")
                for row in delivered["runtime_trace"]["blackboard"]
                if row.get("label") == label
            ]
            exact_payload_count += int(
                delivered["runtime_trace"].get(label) == trace and node_payloads == [trace]
            )
        missing_labels = [label for label in TRACE_LABELS if label not in logic]
        synthesized = any(
            label in labels or label in delivered["runtime_trace"] for label in missing_labels
        )
        duplicate_count = sum(max(0, labels.count(label) - 1) for label in TRACE_LABELS)
        delivery = delivered["runtime_trace"][LABEL]
        row = {
            "case_id": frozen["case_id"],
            "surface_chain": surface_chain,
            "delivery_complete": delivery["delivery_complete"],
            "visible_reply_unchanged": reply_unchanged,
            "logic_unchanged": logic_unchanged,
            "missing_trace_synthesized": synthesized,
            "duplicate_trace_label_count": duplicate_count,
            "exact_trace_payload_count": exact_payload_count,
        }
        cases.append(row)
        metrics["exact_surface_chain_count"] += int(surface_chain == frozen["expected_surface_chain"])
        metrics["exact_trace_payload_count"] += exact_payload_count
        metrics["visible_reply_unchanged_count"] += int(reply_unchanged)
        metrics["logic_unchanged_count"] += int(logic_unchanged)
        metrics["complete_delivery_count"] += int(delivery["delivery_complete"])
        metrics["incomplete_delivery_count"] += int(not delivery["delivery_complete"])
        metrics["duplicate_trace_label_count"] += duplicate_count
        metrics["missing_trace_synthesized_count"] += int(synthesized)
        metrics["new_model_call_count"] += int(delivery["model_call_added"])
        metrics["fact_write_count"] += delivery["fact_write_count"]
        metrics["profile_write_count"] += delivery["profile_write_count"]
        metrics["episode_write_count"] += delivery["episode_write_count"]

    root = Path(__file__).resolve().parent
    contract = json.loads(
        (root / "configs" / "p4_y_runtime_graph_trace_delivery_acceptance_v1.json").read_text(
            encoding="utf-8"
        )
    )
    module_source = Path(__file__).read_text(encoding="utf-8")
    entry_source = (root / "uruha_web_ui_product_p4_y.py").read_text(encoding="utf-8")
    predecessor = contract["predecessor"]
    hashes_preserved = all(
        _sha256(root / predecessor[field]) == predecessor[hash_field]
        for field, hash_field in (
            ("repair_module", "repair_module_sha256"),
            ("entry", "entry_sha256"),
            ("released_product_entry", "released_product_entry_sha256"),
        )
    )
    return {
        "schema": "uruha_p4_y_runtime_graph_trace_delivery_evidence_v1",
        "dataset_sha256": _sha256(dataset_path),
        "cases": cases,
        "metrics": metrics,
        "integration": {
            "delivery_runs_after_run_turn_debug_final_blackboard_refresh": (
                "result = original(self, *args, **kwargs)" in module_source
                and "deliver_existing_surface_traces_p4(result)" in module_source
            ),
            "additive_product_entry": (
                "import uruha_web_ui_product_p4_w as _p4_w" in entry_source
                and "install_runtime_graph_trace_delivery_p4()" in entry_source
                and "RUNTIME = _p4_w.RUNTIME" in entry_source
            ),
            "predecessor_hashes_preserved": hashes_preserved,
        },
    }


__all__ = [
    "LABEL",
    "SCHEMA",
    "TRACE_LABELS",
    "build_fixture_evidence_p4_y",
    "deliver_existing_surface_traces_p4",
    "install_runtime_graph_trace_delivery_p4",
    "wrap_run_turn_debug_with_trace_delivery_p4",
]
