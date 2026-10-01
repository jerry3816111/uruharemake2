"""P4-T deterministic utterance-frame shadow verifier.

This module does not change the visible reply.  It projects a bounded source
frame (speaker ownership, embedding, evidential stance and speech act), checks
whether the final Japanese surface preserves that frame, and emits a raw-free
trace for the runtime graph.  The detector is deliberately smaller than an
open-domain semantic parser and adds no model call or memory write.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re


LABEL = "utterance_frame_shadow_p4"
SCHEMA = "uruha_utterance_frame_shadow_p4"
FRAME_SCHEMA = "uruha_utterance_frame_p4"

_FIRST_PERSON_EN = re.compile(r"\b(?:i|i'm|i've|i'd|i'll|my|me)\b", re.I)
_FIRST_PERSON_ZH = re.compile(r"我|我的")
_FIRST_PERSON_JA = re.compile(r"私|わたし|僕|俺|自分")
_THIRD_PARTY_EN = re.compile(
    r"\b(?:friend|roommate|sister|brother|teacher|senior|coworker|classmate|he|she|they)\b",
    re.I,
)
_THIRD_PARTY_ZH = re.compile(r"朋友|室友|妹妹|弟弟|姐姐|哥哥|老師|老师|學長|学长|同事|同學|同学|他|她")
_THIRD_PARTY_JA = re.compile(r"友達|ルームメイト|妹|弟|姉|兄|先生|先輩|同僚|同級生|彼|彼女")

_HYPOTHETICAL = re.compile(
    r"\bif\b[^.!?]{0,80}\b(?:say|said|were\s+to\s+say)\b|\bhypothetical\b"
    r"|如果|假如|假設|假设|只是假設|只是假设"
    r"|もし|仮定|としたら|と言っても",
    re.I,
)
_QUOTE_MARK = re.compile(r"「[^」]+」|『[^』]+』|\"[^\"]+\"")
_META_REPORT = re.compile(
    r"\b(?:wrote|write|draft|quote|quoted|message\s+says?|said)\b"
    r"|引用|寫|写|傳訊息|传讯息|留言|說|说"
    r"|引用|書いた|書いて|と書|と言った|メッセージ",
    re.I,
)
_HEARSAY = re.compile(
    r"\b(?:apparently|reportedly|i\s+heard|heard\s+that|seems?)\b"
    r"|聽說|听说|據說|据说|好像"
    r"|らしい|そうだ|そうです|みたい|と聞いた",
    re.I,
)
_FRAME_INSTRUCTION = re.compile(
    r"\b(?:treat|regard|handle)\b[^.!?]{0,50}\b(?:hypothetical|condition|assumption)\b"
    r"|當成假設|当成假设|只是假設|只是假设|視為假設|视为假设"
    r"|仮定(?:の話)?として扱|仮定として|前提として扱",
    re.I,
)

_AGENT_FIRST_PERSON_ACTION = re.compile(
    r"(?:^|[。！？\s])(?:うち|私は|わたしは|僕は|俺は|うちが|私が|わたしが|僕が|俺が)"
    r"[^。！？]{0,48}(?:確認|点検|取りに行|取って|閉め|開け|行く|来る|見る|買う|書く|休む|辞め|引っ越|必要|遅れ)"
)
_JAPANESE_QUOTE_PRESERVED = re.compile(r"「[^」]+」|『[^』]+』|引用|下書き|メッセージ|って書|と書|と言っ|って言っ")
_JAPANESE_HYPOTHETICAL_PRESERVED = re.compile(r"仮定|前提|(?<!か)もし|として扱|話として")
_JAPANESE_HEARSAY_PRESERVED = re.compile(r"らしい|みたい|そう(?:だ|なん|で)|と聞|って聞|という")
_JAPANESE_QUESTION = re.compile(r"[？?]\s*$|(?:の|か|好き|買った|したい)[？?]\s*$")
_PROMOTED_HYPOTHETICAL_ASSERTION = re.compile(r"(?:たい|必要|辞める|休む|遅れる|かもしれない)んだね[。！？]?$|たいんだ[。！？]?$")


def _digest(value):
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def _third_party_present(text):
    return bool(_THIRD_PARTY_EN.search(text) or _THIRD_PARTY_ZH.search(text) or _THIRD_PARTY_JA.search(text))


def _first_person_present(text):
    return bool(_FIRST_PERSON_EN.search(text) or _FIRST_PERSON_ZH.search(text) or _FIRST_PERSON_JA.search(text))


def extract_utterance_frame_p4(source):
    """Project one bounded, raw-free-comparable frame from an observable utterance."""

    text = str(source or "").strip()
    hypothetical = bool(_HYPOTHETICAL.search(text))
    quoted = bool(_QUOTE_MARK.search(text) and _META_REPORT.search(text))
    third_party = _third_party_present(text)
    first_person = _first_person_present(text)
    hearsay = bool(_HEARSAY.search(text))

    if third_party and not hypothetical:
        ownership = "third_party"
    elif first_person:
        ownership = "user"
    else:
        ownership = "unspecified"

    if hypothetical:
        embedding = "hypothetical"
        stance = "counterfactual"
    elif quoted:
        embedding = "quoted"
        stance = "reported" if third_party else "direct"
    elif hearsay:
        embedding = "reported"
        stance = "hearsay"
    else:
        embedding = "direct"
        stance = "direct"

    if hypothetical and (_FRAME_INSTRUCTION.search(text) or "仮定" in text):
        speech_act = "frame_instruction"
    elif quoted:
        speech_act = "metalinguistic_report"
    elif re.search(r"[？?]\s*$", text):
        speech_act = "question"
    else:
        speech_act = "statement"

    return {
        "speaker_ownership": ownership,
        "embedding_mode": embedding,
        "evidential_stance": stance,
        "speech_act": speech_act,
    }


def frame_violations_p4(frame, reply):
    surface = str(reply or "").strip()
    violations = []
    if frame.get("speaker_ownership") == "user" and _AGENT_FIRST_PERSON_ACTION.search(surface):
        violations.append("speaker_owner_shift_user_to_agent")
    if frame.get("embedding_mode") == "quoted" and not _JAPANESE_QUOTE_PRESERVED.search(surface):
        violations.append("quoted_content_promoted_to_assertion")
    if frame.get("embedding_mode") == "hypothetical":
        preserves_hypothetical = bool(_JAPANESE_HYPOTHETICAL_PRESERVED.search(surface))
        if not preserves_hypothetical and _PROMOTED_HYPOTHETICAL_ASSERTION.search(surface):
            violations.append("hypothetical_content_promoted_to_assertion")
        if frame.get("speech_act") == "frame_instruction" and not preserves_hypothetical:
            violations.append("hypothetical_instruction_dropped")
    if frame.get("evidential_stance") == "hearsay" and not _JAPANESE_HEARSAY_PRESERVED.search(surface):
        violations.append("hearsay_stance_dropped")
    if frame.get("speech_act") == "statement" and _JAPANESE_QUESTION.search(surface):
        violations.append("statement_changed_to_question")
    return sorted(set(violations))


def inspect_utterance_frame_shadow_p4(source, reply):
    frame = extract_utterance_frame_p4(source)
    violations = frame_violations_p4(frame, reply)
    return {
        "schema": SCHEMA,
        "status": "shadow_violation_detected" if violations else "shadow_frame_preserved",
        "mode": "shadow_only",
        "frame": frame,
        "violations": violations,
        "source_digest": _digest(source),
        "reply_digest": _digest(reply),
        "candidate_unchanged": True,
        "raw_source_or_reply_persisted": False,
        "model_call_added": False,
        "fact_write_count": 0,
        "profile_write_count": 0,
        "episode_write_count": 0,
        "claim_boundary": "bounded deterministic utterance-frame shadow audit; not open-domain semantic equivalence or visible repair",
    }


def shadow_visible_reply_p4(source, reply):
    """Return the candidate byte-for-byte unchanged plus the raw-free trace."""

    visible = str(reply or "")
    return visible, inspect_utterance_frame_shadow_p4(source, visible)


def append_utterance_frame_node_p4(result):
    """Insert one trace node immediately before utterance without changing reply."""

    logic = (result or {}).get("logic") or {}
    trace = deepcopy(logic.get(LABEL) or {})
    if not trace:
        return result
    runtime_trace = result.get("runtime_trace") or {}
    blackboard = list(runtime_trace.get("blackboard") or [])
    blackboard = [row for row in blackboard if row.get("label") != LABEL]
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


_INSTALLED_P4_T = False
_ORIGINAL_VISIBLE_GUARD_P4_T = None
_ORIGINAL_EMIT_RESPONSE_P4_T = None


def install_utterance_frame_shadow_p4():
    """Install after M39/P4 surface guards; visible reply remains unchanged."""

    global _INSTALLED_P4_T, _ORIGINAL_VISIBLE_GUARD_P4_T, _ORIGINAL_EMIT_RESPONSE_P4_T
    if _INSTALLED_P4_T:
        return False
    from uruha_brain_mac import RightBrain, UruhaBrainV4_Mac

    _ORIGINAL_VISIBLE_GUARD_P4_T = RightBrain.enforce_user_visible_japanese
    _ORIGINAL_EMIT_RESPONSE_P4_T = UruhaBrainV4_Mac.emit_response_if_ready

    def guarded_with_p4_t(self, reply, logic_data, user_input="", memory_data=None):
        visible = _ORIGINAL_VISIBLE_GUARD_P4_T(
            self,
            reply,
            logic_data,
            user_input=user_input,
            memory_data=memory_data,
        )
        unchanged, trace = shadow_visible_reply_p4(user_input, visible)
        logic_data[LABEL] = trace
        return unchanged

    def emit_with_p4_t_trace(self, event, tick_result):
        result = _ORIGINAL_EMIT_RESPONSE_P4_T(self, event, tick_result)
        result = append_utterance_frame_node_p4(result)
        trace = ((result or {}).get("runtime_trace") or {}).get(LABEL)
        if trace and getattr(self.runtime, "turn_traces", None):
            self.runtime.turn_traces[-1] = deepcopy(result["runtime_trace"])
        return result

    RightBrain.enforce_user_visible_japanese = guarded_with_p4_t
    UruhaBrainV4_Mac.emit_response_if_ready = emit_with_p4_t_trace
    _INSTALLED_P4_T = True
    return True


def build_dataset_evidence_p4_t(dataset_path):
    dataset_path = Path(dataset_path)
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    cases = []
    development_frame = development_violations = 0
    holdout_frame = holdout_violations = 0
    control_false_positives = 0
    for partition in ("development_failures", "holdout_failures", "plain_controls"):
        for frozen in dataset[partition]:
            candidate, trace = shadow_visible_reply_p4(frozen["source"], frozen["candidate"])
            frame_exact = frozen.get("expected_frame") is None or trace["frame"] == frozen["expected_frame"]
            violations_exact = trace["violations"] == frozen["expected_violations"]
            if partition == "development_failures":
                development_frame += int(frame_exact)
                development_violations += int(violations_exact)
            elif partition == "holdout_failures":
                holdout_frame += int(frame_exact)
                holdout_violations += int(violations_exact)
            else:
                control_false_positives += int(bool(trace["violations"]))
            encoded = json.dumps(trace, ensure_ascii=False)
            cases.append(
                {
                    "case_id": frozen["case_id"],
                    "partition": partition,
                    "frame": trace["frame"],
                    "violations": trace["violations"],
                    "candidate_unchanged": candidate == frozen["candidate"],
                    "trace_contains_raw_source_or_reply": frozen["source"] in encoded or frozen["candidate"] in encoded,
                    "model_call_added": trace["model_call_added"],
                    "fact_write_count": trace["fact_write_count"],
                    "profile_write_count": trace["profile_write_count"],
                    "episode_write_count": trace["episode_write_count"],
                }
            )
    count = len(cases)
    product_source = Path(__file__).with_name("uruha_web_ui_product_p4_t.py").read_text(encoding="utf-8")
    product_installs = (
        "from uruha_utterance_frame_shadow_p4 import install_utterance_frame_shadow_p4" in product_source
        and "install_utterance_frame_shadow_p4()" in product_source
        and "import uruha_web_ui_product_p4_o as _p4_o" in product_source
    )
    probe_reply = dataset["development_failures"][0]["candidate"]
    probe_trace = inspect_utterance_frame_shadow_p4(
        dataset["development_failures"][0]["source"],
        probe_reply,
    )
    probe = append_utterance_frame_node_p4(
        {
            "reply": probe_reply,
            "logic": {LABEL: probe_trace},
            "runtime_trace": {"blackboard": [{"stage": "surface", "label": "utterance", "payload": {}}]},
        }
    )
    probe_labels = [row.get("label") for row in probe["runtime_trace"]["blackboard"]]
    graph_node_ready = probe_labels == [LABEL, "utterance"] and probe["runtime_trace"].get(LABEL) == probe_trace
    return {
        "schema": "uruha_p4_t_utterance_frame_shadow_evidence_v1",
        "dataset_sha256": hashlib.sha256(dataset_path.read_bytes()).hexdigest(),
        "cases": cases,
        "metrics": {
            "development_case_count": len(dataset["development_failures"]),
            "development_exact_frame_count": development_frame,
            "development_exact_violation_count": development_violations,
            "holdout_case_count": len(dataset["holdout_failures"]),
            "holdout_exact_frame_count": holdout_frame,
            "holdout_exact_violation_count": holdout_violations,
            "plain_control_count": len(dataset["plain_controls"]),
            "plain_control_false_positive_count": control_false_positives,
            "candidate_unchanged_count": sum(row["candidate_unchanged"] for row in cases),
            "shadow_trace_count": count,
            "raw_source_or_reply_trace_count": sum(row["trace_contains_raw_source_or_reply"] for row in cases),
            "new_model_call_count": sum(row["model_call_added"] for row in cases),
            "fact_write_count": sum(row["fact_write_count"] for row in cases),
            "profile_write_count": sum(row["profile_write_count"] for row in cases),
            "episode_write_count": sum(row["episode_write_count"] for row in cases),
        },
        "integration": {
            "product_entry_installs_shadow_detector": product_installs,
            "runtime_graph_node_test_passed": graph_node_ready,
            "visible_reply_unchanged_test_passed": all(row["candidate_unchanged"] for row in cases),
        },
    }


__all__ = [
    "LABEL",
    "SCHEMA",
    "append_utterance_frame_node_p4",
    "build_dataset_evidence_p4_t",
    "extract_utterance_frame_p4",
    "frame_violations_p4",
    "inspect_utterance_frame_shadow_p4",
    "install_utterance_frame_shadow_p4",
    "shadow_visible_reply_p4",
]
