"""P4-W deterministic visible Japanese repair driven only by P4-V violations."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re

import uruha_utterance_frame_shadow_extension_p4 as p4v
import uruha_utterance_frame_shadow_p4 as p4t


LABEL = "frame_preserving_visible_repair_p4"
SCHEMA = "uruha_frame_preserving_visible_repair_p4"

_AGENT_PREFIX = re.compile(r"^(?:うちは|うちが|私は|私が|わたしは|わたしが|僕は|僕が|俺は|俺が)")
_TERMINAL = re.compile(r"[。！？?]+$")
_ASSERTIVE_SUFFIX = re.compile(r"(?:なんだね|んだね|なんだ|んだ)$")
_JAPANESE_SCRIPT = re.compile(r"[ぁ-んァ-ン一-龯]")


def _digest(value):
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def _stem(candidate):
    value = _TERMINAL.sub("", str(candidate or "").strip())
    return _ASSERTIVE_SUFFIX.sub("", value).strip()


def _repair_owner(candidate):
    value = _AGENT_PREFIX.sub("そっちは", str(candidate or "").strip(), count=1)
    value = _TERMINAL.sub("", value)
    if value.endswith("んだね"):
        return value + "。"
    return value + "んだね。"


def _repair_quote(candidate):
    return f"「{_stem(candidate)}」っていう記載なんだね。"


def _repair_hypothetical(candidate, violations):
    if "hypothetical_content_promoted_to_assertion" in violations:
        return f"「{_stem(candidate)}」っていう仮定の話ね。"
    return "その内容は仮定として扱う。"


def _repair_hearsay(candidate):
    value = _TERMINAL.sub("", str(candidate or "").strip())
    if "、" in value:
        subject, predicate = value.split("、", 1)
        return f"{subject}が{predicate}らしいって話ね。"
    return f"{value}らしいって話ね。"


def _transform(candidate, violations):
    violation_set = set(violations or [])
    if "hypothetical_instruction_dropped" in violation_set:
        return _repair_hypothetical(candidate, violation_set), "hypothetical_frame_restore"
    if "quoted_content_promoted_to_assertion" in violation_set:
        return _repair_quote(candidate), "quote_embedding_restore"
    if "hearsay_stance_dropped" in violation_set:
        return _repair_hearsay(candidate), "hearsay_statement_restore"
    if "speaker_owner_shift_user_to_agent" in violation_set:
        return _repair_owner(candidate), "speaker_owner_restore"
    return str(candidate or ""), "unsupported_or_no_violation"


def repair_visible_reply_p4(source, candidate, effective_trace=None):
    """Repair only from a supplied P4-V effective violation trace."""

    visible_before = str(candidate or "")
    trace_before = deepcopy(
        effective_trace or p4v.inspect_utterance_frame_coverage_extension_p4(source, visible_before)
    )
    before_violations = list(trace_before.get("violations") or [])
    if before_violations:
        visible_after, strategy = _transform(visible_before, before_violations)
    else:
        visible_after, strategy = visible_before, "no_violation_noop"
    after_trace = p4v.inspect_utterance_frame_coverage_extension_p4(source, visible_after)
    after_violations = list(after_trace.get("violations") or [])
    repair_trace = {
        "schema": SCHEMA,
        "status": "repaired" if visible_after != visible_before and not after_violations else (
            "unchanged_preserved" if not before_violations and visible_after == visible_before else "unresolved"
        ),
        "strategy": strategy,
        "before_violations": before_violations,
        "after_violations": after_violations,
        "before_digest": _digest(visible_before),
        "after_digest": _digest(visible_after),
        "changed": visible_after != visible_before,
        "visible_output_language": "Japanese" if _JAPANESE_SCRIPT.search(visible_after) else "Unknown",
        "raw_source_or_reply_persisted": False,
        "model_call_added": False,
        "fact_write_count": 0,
        "profile_write_count": 0,
        "episode_write_count": 0,
        "claim_boundary": "bounded deterministic visible Japanese frame repair driven by an existing P4-V trace; not open-domain semantic generation",
    }
    return visible_after, repair_trace


def append_frame_preserving_repair_node_p4(result):
    logic = (result or {}).get("logic") or {}
    trace = deepcopy(logic.get(LABEL) or {})
    if not trace:
        return result
    runtime_trace = result.get("runtime_trace") or {}
    blackboard = [row for row in list(runtime_trace.get("blackboard") or []) if row.get("label") != LABEL]
    insert_at = next(
        (index for index, item in enumerate(blackboard) if item.get("label") == "utterance"),
        len(blackboard),
    )
    blackboard.insert(
        insert_at,
        {
            "stage": "surface",
            "label": LABEL,
            "payload": trace,
            "salience": 1.0 if trace.get("changed") else 0.84,
        },
    )
    runtime_trace["blackboard"] = blackboard
    runtime_trace[LABEL] = trace
    result["runtime_trace"] = runtime_trace
    return result


_INSTALLED_P4_W = False
_ORIGINAL_VISIBLE_GUARD_P4_W = None
_ORIGINAL_EMIT_RESPONSE_P4_W = None


def install_frame_preserving_visible_repair_p4():
    global _INSTALLED_P4_W, _ORIGINAL_VISIBLE_GUARD_P4_W, _ORIGINAL_EMIT_RESPONSE_P4_W
    if _INSTALLED_P4_W:
        return False
    from uruha_brain_mac import RightBrain, UruhaBrainV4_Mac

    _ORIGINAL_VISIBLE_GUARD_P4_W = RightBrain.enforce_user_visible_japanese
    _ORIGINAL_EMIT_RESPONSE_P4_W = UruhaBrainV4_Mac.emit_response_if_ready

    def guarded_with_p4_w(self, reply, logic_data, user_input="", memory_data=None):
        visible = _ORIGINAL_VISIBLE_GUARD_P4_W(
            self,
            reply,
            logic_data,
            user_input=user_input,
            memory_data=memory_data,
        )
        repaired, trace = repair_visible_reply_p4(
            user_input,
            visible,
            effective_trace=logic_data.get(p4v.LABEL),
        )
        logic_data[LABEL] = trace
        return repaired

    def emit_with_p4_w_trace(self, event, tick_result):
        result = _ORIGINAL_EMIT_RESPONSE_P4_W(self, event, tick_result)
        result = append_frame_preserving_repair_node_p4(result)
        trace = ((result or {}).get("runtime_trace") or {}).get(LABEL)
        if trace and getattr(self.runtime, "turn_traces", None):
            self.runtime.turn_traces[-1] = deepcopy(result["runtime_trace"])
        return result

    RightBrain.enforce_user_visible_japanese = guarded_with_p4_w
    UruhaBrainV4_Mac.emit_response_if_ready = emit_with_p4_w_trace
    _INSTALLED_P4_W = True
    return True


def build_dataset_evidence_p4_w(dataset_path):
    dataset_path = Path(dataset_path)
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    cases = []
    metrics = {
        "development_case_count": len(dataset["development_failures"]),
        "development_exact_before_violation_count": 0,
        "development_exact_reply_count": 0,
        "development_zero_unresolved_count": 0,
        "holdout_case_count": len(dataset["holdout_failures"]),
        "holdout_exact_before_violation_count": 0,
        "holdout_exact_reply_count": 0,
        "holdout_zero_unresolved_count": 0,
        "faithful_control_count": len(dataset["faithful_controls"]),
        "faithful_control_unchanged_count": 0,
        "visible_japanese_count": 0,
        "trace_count": 0,
        "raw_source_or_reply_trace_count": 0,
        "new_model_call_count": 0,
        "fact_write_count": 0,
        "profile_write_count": 0,
        "episode_write_count": 0,
    }
    for partition in ("development_failures", "holdout_failures", "faithful_controls"):
        for frozen in dataset[partition]:
            before = p4v.inspect_utterance_frame_coverage_extension_p4(frozen["source"], frozen["candidate"])
            visible, trace = repair_visible_reply_p4(frozen["source"], frozen["candidate"], effective_trace=before)
            if partition == "development_failures":
                prefix = "development"
                metrics[f"{prefix}_exact_before_violation_count"] += int(
                    trace["before_violations"] == frozen["expected_before_violations"]
                )
                metrics[f"{prefix}_exact_reply_count"] += int(visible == frozen["expected_reply"])
                metrics[f"{prefix}_zero_unresolved_count"] += int(trace["after_violations"] == [])
            elif partition == "holdout_failures":
                prefix = "holdout"
                metrics[f"{prefix}_exact_before_violation_count"] += int(
                    trace["before_violations"] == frozen["expected_before_violations"]
                )
                metrics[f"{prefix}_exact_reply_count"] += int(visible == frozen["expected_reply"])
                metrics[f"{prefix}_zero_unresolved_count"] += int(trace["after_violations"] == [])
            else:
                metrics["faithful_control_unchanged_count"] += int(not trace["changed"] and visible == frozen["candidate"])
            encoded = json.dumps(trace, ensure_ascii=False)
            row = {
                "case_id": frozen["case_id"],
                "partition": partition,
                "before_violations": trace["before_violations"],
                "visible_reply": visible,
                "after_violations": trace["after_violations"],
                "changed": trace["changed"],
                "visible_output_language": trace["visible_output_language"],
                "trace_contains_raw_source_or_reply": frozen["source"] in encoded or visible in encoded,
                "model_call_added": trace["model_call_added"],
                "fact_write_count": trace["fact_write_count"],
                "profile_write_count": trace["profile_write_count"],
                "episode_write_count": trace["episode_write_count"],
            }
            cases.append(row)
            metrics["visible_japanese_count"] += int(trace["visible_output_language"] == "Japanese")
            metrics["trace_count"] += 1
            metrics["raw_source_or_reply_trace_count"] += int(row["trace_contains_raw_source_or_reply"])
            metrics["new_model_call_count"] += int(trace["model_call_added"])
            metrics["fact_write_count"] += trace["fact_write_count"]
            metrics["profile_write_count"] += trace["profile_write_count"]
            metrics["episode_write_count"] += trace["episode_write_count"]

    product_source = Path(__file__).with_name("uruha_web_ui_product_p4_w.py").read_text(encoding="utf-8")
    product_installs = (
        "import uruha_web_ui_product_p4_v as _p4_v" in product_source
        and "install_frame_preserving_visible_repair_p4()" in product_source
        and "RUNTIME = _p4_v.RUNTIME" in product_source
    )
    probe_trace = repair_visible_reply_p4(
        dataset["development_failures"][0]["source"],
        dataset["development_failures"][0]["candidate"],
    )[1]
    probe = append_frame_preserving_repair_node_p4(
        {
            "logic": {LABEL: probe_trace},
            "runtime_trace": {
                "blackboard": [
                    {"stage": "surface", "label": p4t.LABEL, "payload": {}},
                    {"stage": "surface", "label": p4v.LABEL, "payload": {}},
                    {"stage": "surface", "label": "utterance", "payload": {}},
                ]
            },
        }
    )
    labels = [row.get("label") for row in probe["runtime_trace"]["blackboard"]]
    graph_ready = labels == [p4t.LABEL, p4v.LABEL, LABEL, "utterance"]

    contract = json.loads(
        Path(__file__).with_name("configs").joinpath(
            "p4_w_frame_preserving_visible_repair_acceptance_v1.json"
        ).read_text(encoding="utf-8")
    )
    predecessor = contract["predecessor"]
    hashes_preserved = all(
        hashlib.sha256(Path(__file__).with_name(predecessor[field]).read_bytes()).hexdigest()
        == predecessor[hash_field]
        for field, hash_field in (
            ("module", "module_sha256"),
            ("entry", "entry_sha256"),
            ("released_product_entry", "released_product_entry_sha256"),
        )
    )
    return {
        "schema": "uruha_p4_w_frame_preserving_visible_repair_evidence_v1",
        "dataset_sha256": hashlib.sha256(dataset_path.read_bytes()).hexdigest(),
        "cases": cases,
        "metrics": metrics,
        "integration": {
            "additive_product_entry_installs_repair": product_installs,
            "runtime_graph_node_test_passed": graph_ready,
            "predecessor_hashes_preserved": hashes_preserved,
        },
    }


__all__ = [
    "LABEL",
    "SCHEMA",
    "append_frame_preserving_repair_node_p4",
    "build_dataset_evidence_p4_w",
    "install_frame_preserving_visible_repair_p4",
    "repair_visible_reply_p4",
]
