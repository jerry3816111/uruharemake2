"""P4-V additive utterance-frame coverage extension.

The released P4-T trace remains intact.  This layer adds bounded abstractions
for cross-lingual action/time alignment, explicit report sources and explicit
hypothetical framing.  It never changes the visible candidate or writes memory.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re

import uruha_utterance_frame_shadow_p4 as p4t


LABEL = "utterance_frame_coverage_extension_p4"
SCHEMA = "uruha_utterance_frame_coverage_extension_p4"

_AGENT_FIRST_PERSON = re.compile(
    r"(?:^|[。！？\s])(?:うち|私は|わたしは|僕は|俺は|うちが|私が|わたしが|僕が|俺が)"
)
_QUOTE_MARK = re.compile(r"「[^」]+」|『[^』]+』|\"[^\"]+\"")
_REPORT_SOURCE = re.compile(
    r"\b(?:memo|notice|note|article|manual|script)\b[^.!?]{0,48}"
    r"\b(?:says?|reads?|states?|reports?)\b"
    r"|(?:公告|文章|備忘錄|备忘录|通知|手冊|手册|腳本|脚本)[^。！？]{0,32}"
    r"(?:顯示|显示|記載|记载|寫著|写着|寫|写)"
    r"|(?:説明書|告知|メモ|記事|台本)[^。！？]{0,32}(?:記載|書いて|書かれ|とある)",
    re.I,
)
_HYPOTHETICAL_FRAME = re.compile(
    r"\b(?:suppose|assuming)\b|\bonly\s+be\s+hypothetical\b|\bkeep\s+that\s+as\s+an\s+assumption\b"
    r"|(?:假如|假設|假设)[^。！？]{0,100}(?:只是(?:個|个)?假設|只是(?:個|个)?假设|不要把[^。！？]{0,32}當成現在的決定|不要把[^。！？]{0,32}当成现在的决定)"
    r"|(?:もし[^。！？]{0,100}仮定として(?:聞|扱)|単なる仮の話として(?:聞|扱)|仮の話として(?:聞|扱))",
    re.I,
)
_CANDIDATE_HYPOTHETICAL = re.compile(r"仮定|仮の話|想定|前提|として扱")
_CANDIDATE_ASSERTIVE_PROMOTION = re.compile(r"んだね[。！？]?$|んだ[。！？]?$")
_CANDIDATE_QUOTE_PRESERVED = re.compile(
    r"「[^」]+」|『[^』]+』|引用|下書き|告知|公告|説明書|って書|と書|ってある|とある"
)

_ACTION_CONCEPTS = (
    ("organize", re.compile(r"整理|\b(?:organize|sort)\b", re.I), re.compile(r"整理")),
    ("water", re.compile(r"澆水|浇水|\bwater\b", re.I), re.compile(r"水をや|水やり")),
    ("repair", re.compile(r"修理|修好|直す|\b(?:fix|repair)\b", re.I), re.compile(r"直す|修理")),
    ("wipe", re.compile(r"擦乾|擦干|擦拭|\b(?:wipe|dry)\b", re.I), re.compile(r"拭く|拭い|乾か")),
    ("pack", re.compile(r"裝箱|装箱|\bpack\b", re.I), re.compile(r"箱に詰め|梱包")),
    ("sew", re.compile(r"縫|\b(?:sew|mend)\b", re.I), re.compile(r"縫")),
)
_TIME_ANCHORS = (
    ("tomorrow_morning", re.compile(r"tomorrow morning|明天早上|明日の朝", re.I)),
    ("day_after_tomorrow", re.compile(r"day after tomorrow|後天|后天|明後日", re.I)),
    ("this_weekend", re.compile(r"this weekend|這週末|这周末|今週末", re.I)),
    ("tonight", re.compile(r"tonight|今晚|今夜", re.I)),
    ("tomorrow", re.compile(r"tomorrow|明天|明日", re.I)),
)


def _digest(value):
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def _concepts(text, patterns, reply=False):
    value = str(text or "")
    found = []
    for name, source_pattern, reply_pattern in patterns:
        pattern = reply_pattern if reply else source_pattern
        if pattern.search(value):
            found.append(name)
    return found


def _time_anchors(text):
    value = str(text or "")
    return [name for name, pattern in _TIME_ANCHORS if pattern.search(value)]


def inspect_utterance_frame_coverage_extension_p4(source, reply, base_trace=None):
    """Return a raw-free effective trace while preserving the P4-T base trace."""

    source_text = str(source or "").strip()
    reply_text = str(reply or "").strip()
    base = deepcopy(base_trace or p4t.inspect_utterance_frame_shadow_p4(source_text, reply_text))
    base_violations = list(base.get("violations") or [])
    effective = set(base_violations)
    evidence = []

    source_actions = _concepts(source_text, _ACTION_CONCEPTS)
    reply_actions = _concepts(reply_text, _ACTION_CONCEPTS, reply=True)
    shared_actions = sorted(set(source_actions) & set(reply_actions))
    source_times = _time_anchors(source_text)
    reply_times = _time_anchors(reply_text)
    shared_times = sorted(set(source_times) & set(reply_times))
    if shared_actions:
        evidence.append("crosslingual_action_alignment")
    if shared_times:
        evidence.append("temporal_alignment")
    frame = base.get("frame") or {}
    if (
        frame.get("speaker_ownership") == "user"
        and frame.get("embedding_mode") == "direct"
        and shared_actions
        and shared_times
        and _AGENT_FIRST_PERSON.search(reply_text)
    ):
        effective.add("speaker_owner_shift_user_to_agent")

    quoted_span = bool(_QUOTE_MARK.search(source_text))
    report_source = bool(_REPORT_SOURCE.search(source_text))
    if quoted_span and report_source:
        evidence.extend(["quoted_span", "report_source_marker"])
        if not _CANDIDATE_QUOTE_PRESERVED.search(reply_text):
            effective.add("quoted_content_promoted_to_assertion")

    hypothetical_frame = bool(_HYPOTHETICAL_FRAME.search(source_text))
    if hypothetical_frame:
        evidence.append("hypothetical_frame_marker")
        # "Suppose I said ..." is hypothetical, not a metalinguistic report.
        effective.discard("quoted_content_promoted_to_assertion")
        preserves = bool(_CANDIDATE_HYPOTHETICAL.search(reply_text))
        promotes = bool(_CANDIDATE_ASSERTIVE_PROMOTION.search(reply_text))
        if preserves:
            evidence.append("candidate_hypothetical_preserved")
        elif promotes:
            evidence.append("candidate_assertive_promotion")
            effective.add("hypothetical_content_promoted_to_assertion")
        if not preserves:
            effective.add("hypothetical_instruction_dropped")

    return {
        "schema": SCHEMA,
        "status": "shadow_violation_detected" if effective else "shadow_frame_preserved",
        "mode": "shadow_only",
        "base_schema": base.get("schema"),
        "base_violations": base_violations,
        "extension_evidence": evidence,
        "abstract_alignment": {
            "shared_action_concepts": shared_actions,
            "shared_time_anchors": shared_times,
            "quoted_report": quoted_span and report_source,
            "hypothetical_frame": hypothetical_frame,
        },
        "violations": sorted(effective),
        "source_digest": _digest(source_text),
        "reply_digest": _digest(reply_text),
        "candidate_unchanged": True,
        "raw_source_or_reply_persisted": False,
        "model_call_added": False,
        "fact_write_count": 0,
        "profile_write_count": 0,
        "episode_write_count": 0,
        "claim_boundary": "bounded deterministic shadow coverage extension; not open-domain semantic equivalence or visible repair",
    }


def shadow_visible_reply_extension_p4(source, reply, base_trace=None):
    visible = str(reply or "")
    return visible, inspect_utterance_frame_coverage_extension_p4(source, visible, base_trace=base_trace)


def append_utterance_frame_extension_node_p4(result):
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
            "salience": 1.0 if trace.get("violations") else 0.88,
        },
    )
    runtime_trace["blackboard"] = blackboard
    runtime_trace[LABEL] = trace
    result["runtime_trace"] = runtime_trace
    return result


_INSTALLED_P4_V = False
_ORIGINAL_VISIBLE_GUARD_P4_V = None
_ORIGINAL_EMIT_RESPONSE_P4_V = None


def install_utterance_frame_coverage_extension_p4():
    global _INSTALLED_P4_V, _ORIGINAL_VISIBLE_GUARD_P4_V, _ORIGINAL_EMIT_RESPONSE_P4_V
    if _INSTALLED_P4_V:
        return False
    from uruha_brain_mac import RightBrain, UruhaBrainV4_Mac

    _ORIGINAL_VISIBLE_GUARD_P4_V = RightBrain.enforce_user_visible_japanese
    _ORIGINAL_EMIT_RESPONSE_P4_V = UruhaBrainV4_Mac.emit_response_if_ready

    def guarded_with_p4_v(self, reply, logic_data, user_input="", memory_data=None):
        visible = _ORIGINAL_VISIBLE_GUARD_P4_V(
            self,
            reply,
            logic_data,
            user_input=user_input,
            memory_data=memory_data,
        )
        unchanged, trace = shadow_visible_reply_extension_p4(
            user_input,
            visible,
            base_trace=logic_data.get(p4t.LABEL),
        )
        logic_data[LABEL] = trace
        return unchanged

    def emit_with_p4_v_trace(self, event, tick_result):
        result = _ORIGINAL_EMIT_RESPONSE_P4_V(self, event, tick_result)
        result = append_utterance_frame_extension_node_p4(result)
        trace = ((result or {}).get("runtime_trace") or {}).get(LABEL)
        if trace and getattr(self.runtime, "turn_traces", None):
            self.runtime.turn_traces[-1] = deepcopy(result["runtime_trace"])
        return result

    RightBrain.enforce_user_visible_japanese = guarded_with_p4_v
    UruhaBrainV4_Mac.emit_response_if_ready = emit_with_p4_v_trace
    _INSTALLED_P4_V = True
    return True


def build_dataset_evidence_p4_v(dataset_path):
    dataset_path = Path(dataset_path)
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    cases = []
    counters = {
        "development_exact_base_violation_count": 0,
        "development_exact_extension_evidence_count": 0,
        "development_exact_violation_count": 0,
        "holdout_exact_base_violation_count": 0,
        "holdout_exact_extension_evidence_count": 0,
        "holdout_exact_violation_count": 0,
        "faithful_control_exact_base_violation_count": 0,
        "faithful_control_exact_extension_evidence_count": 0,
        "faithful_control_false_positive_count": 0,
    }
    for partition in ("development_failures", "holdout_failures", "faithful_controls"):
        for frozen in dataset[partition]:
            candidate, trace = shadow_visible_reply_extension_p4(frozen["source"], frozen["candidate"])
            prefix = {
                "development_failures": "development",
                "holdout_failures": "holdout",
                "faithful_controls": "faithful_control",
            }[partition]
            counters[f"{prefix}_exact_base_violation_count"] += int(
                trace["base_violations"] == frozen["expected_base_violations"]
            )
            counters[f"{prefix}_exact_extension_evidence_count"] += int(
                trace["extension_evidence"] == frozen["expected_extension_evidence"]
            )
            if partition == "faithful_controls":
                counters["faithful_control_false_positive_count"] += int(bool(trace["violations"]))
            else:
                counters[f"{prefix}_exact_violation_count"] += int(
                    trace["violations"] == frozen["expected_violations"]
                )
            encoded = json.dumps(trace, ensure_ascii=False)
            cases.append(
                {
                    "case_id": frozen["case_id"],
                    "partition": partition,
                    "base_violations": trace["base_violations"],
                    "extension_evidence": trace["extension_evidence"],
                    "violations": trace["violations"],
                    "candidate_unchanged": candidate == frozen["candidate"],
                    "trace_contains_raw_source_or_reply": frozen["source"] in encoded or frozen["candidate"] in encoded,
                    "model_call_added": trace["model_call_added"],
                    "fact_write_count": trace["fact_write_count"],
                    "profile_write_count": trace["profile_write_count"],
                    "episode_write_count": trace["episode_write_count"],
                }
            )

    product_source = Path(__file__).with_name("uruha_web_ui_product_p4_v.py").read_text(encoding="utf-8")
    product_installs = (
        "import uruha_web_ui_product_p4_t as _p4_t" in product_source
        and "install_utterance_frame_coverage_extension_p4()" in product_source
        and "RUNTIME = _p4_t.RUNTIME" in product_source
    )
    probe_reply = dataset["development_failures"][0]["candidate"]
    probe_trace = inspect_utterance_frame_coverage_extension_p4(
        dataset["development_failures"][0]["source"],
        probe_reply,
    )
    probe = append_utterance_frame_extension_node_p4(
        {
            "reply": probe_reply,
            "logic": {LABEL: probe_trace},
            "runtime_trace": {
                "blackboard": [
                    {"stage": "surface", "label": p4t.LABEL, "payload": {}},
                    {"stage": "surface", "label": "utterance", "payload": {}},
                ]
            },
        }
    )
    labels = [row.get("label") for row in probe["runtime_trace"]["blackboard"]]
    graph_ready = labels == [p4t.LABEL, LABEL, "utterance"]

    contract = json.loads(
        Path(__file__).with_name("configs").joinpath(
            "p4_v_utterance_frame_coverage_extension_acceptance_v1.json"
        ).read_text(encoding="utf-8")
    )
    predecessor = contract["predecessor"]
    predecessor_hashes_preserved = all(
        hashlib.sha256(Path(__file__).with_name(predecessor[field]).read_bytes()).hexdigest()
        == predecessor[hash_field]
        for field, hash_field in (
            ("module", "module_sha256"),
            ("entry", "entry_sha256"),
            ("released_product_entry", "released_product_entry_sha256"),
        )
    )
    count = len(cases)
    metrics = {
        "development_case_count": len(dataset["development_failures"]),
        "holdout_case_count": len(dataset["holdout_failures"]),
        "faithful_control_count": len(dataset["faithful_controls"]),
        **counters,
        "candidate_unchanged_count": sum(row["candidate_unchanged"] for row in cases),
        "shadow_trace_count": count,
        "raw_source_or_reply_trace_count": sum(row["trace_contains_raw_source_or_reply"] for row in cases),
        "new_model_call_count": sum(row["model_call_added"] for row in cases),
        "fact_write_count": sum(row["fact_write_count"] for row in cases),
        "profile_write_count": sum(row["profile_write_count"] for row in cases),
        "episode_write_count": sum(row["episode_write_count"] for row in cases),
    }
    return {
        "schema": "uruha_p4_v_utterance_frame_coverage_extension_evidence_v1",
        "dataset_sha256": hashlib.sha256(dataset_path.read_bytes()).hexdigest(),
        "cases": cases,
        "metrics": metrics,
        "integration": {
            "additive_product_entry_installs_extension": product_installs,
            "runtime_graph_node_test_passed": graph_ready,
            "predecessor_hashes_preserved": predecessor_hashes_preserved,
        },
    }


__all__ = [
    "LABEL",
    "SCHEMA",
    "append_utterance_frame_extension_node_p4",
    "build_dataset_evidence_p4_v",
    "inspect_utterance_frame_coverage_extension_p4",
    "install_utterance_frame_coverage_extension_p4",
    "shadow_visible_reply_extension_p4",
]
