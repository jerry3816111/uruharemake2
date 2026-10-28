"""P4-Z bounded source proposition preservation after P4-W.

P4-W repairs quotation/hearsay/hypothetical *frames*, but its transformed
surface can still preserve the wrong proposition.  P4-Z independently parses
three narrow source grammars, verifies the final visible candidate against the
source-derived fields, and renders a bounded Japanese surface when required.
Unsupported sources are left unchanged.  Candidate text never supplies a
missing source field.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re

import uruha_runtime_graph_trace_delivery_p4 as p4y
import uruha_frame_preserving_visible_repair_p4 as p4w
import uruha_utterance_frame_shadow_extension_p4 as p4v
import uruha_utterance_frame_shadow_p4 as p4t


LABEL = "source_bound_proposition_preservation_p4"
SCHEMA = "uruha_source_bound_proposition_preservation_p4"
REQUIRED_FIELDS = (
    "family",
    "embedding_stance",
    "speaker_owner",
    "subject_jp",
    "predicate_jp",
    "object_jp",
    "time_jp",
    "location_jp",
)

_ZH_NUMBERS = {
    "一": "一",
    "二": "二",
    "兩": "二",
    "三": "三",
    "四": "四",
    "五": "五",
    "六": "六",
    "七": "七",
    "八": "八",
    "九": "九",
    "十": "十",
}
_EN_NUMBERS = {
    "one": "一",
    "two": "二",
    "three": "三",
    "four": "四",
    "five": "五",
    "six": "六",
    "seven": "七",
    "eight": "八",
    "nine": "九",
    "ten": "十",
}
_ZH_QUOTE_SUBJECT = {
    "冬季入口": "冬季入口",
    "北側窗口": "北側の窓口",
    "東側入口": "東側入口",
}
_EN_QUOTE_SUBJECT = {
    "east gate": "東門",
    "north window": "北側の窓口",
}
_ZH_SUBJECT = {"林小姐": "林さん", "陳先生": "陳さん"}
_EN_SUBJECT = {"maya": "マヤ"}
_ZH_OBJECT = {
    "紅色雨傘": "赤い傘",
    "黑色外套": "黒いコート",
    "晚上的會議": "夜の会議",
}
_EN_OBJECT = {
    "green folder": "緑のフォルダー",
    "blue key": "青い鍵",
    "red chair": "赤い椅子",
}
_ZH_LOCATION = {"公車": "バス", "火車": "電車"}
_EN_LOCATION = {"taxi": "タクシー"}
_AGENT_OWNER = re.compile(r"(?:^|[「『（(])\s*(?:うち|私|わたし|僕|俺)(?:は|が)")


def _digest(value):
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def _language(text):
    value = str(text or "")
    if re.search(r"[ぁ-んァ-ヶー]", value):
        return "ja"
    if re.search(r"[一-龠]", value):
        return "zh"
    return "en"


def _number_jp(raw, language):
    value = str(raw or "").strip().lower()
    if language == "zh":
        normalized = _ZH_NUMBERS.get(value)
    elif language == "en":
        normalized = _EN_NUMBERS.get(value)
    else:
        normalized = value if re.fullmatch(r"[一二三四五六七八九十]", value) else None
    return f"{normalized}時" if normalized else None


def _contract(language, family, stance, owner, subject, predicate, obj=None, time=None, location=None, rule_id=None):
    return {
        "source_language": language,
        "family": family,
        "embedding_stance": stance,
        "speaker_owner": owner,
        "subject_jp": subject,
        "predicate_jp": predicate,
        "object_jp": obj,
        "time_jp": time,
        "location_jp": location,
        "rule_id": rule_id,
        "field_status": {
            key: "known_from_bounded_source_rule" if value is not None else "unknown_not_in_source_rule"
            for key, value in {
                "subject_jp": subject,
                "predicate_jp": predicate,
                "object_jp": obj,
                "time_jp": time,
                "location_jp": location,
            }.items()
        },
    }


def _parse_quote_zh(text):
    outer = re.search(r"(?:引用|記載)[：:]?\s*[「“\"](.+?)[」”\"]", text)
    if not outer:
        return None
    inner = outer.group(1).strip(" ，,")
    match = re.fullmatch(r"(.+?)([一二兩三四五六七八九十])點(關門|停止受理)", inner)
    if not match:
        return None
    subject = _ZH_QUOTE_SUBJECT.get(match.group(1))
    predicate = {"關門": "閉まる", "停止受理": "受付を終了する"}.get(match.group(3))
    time = _number_jp(match.group(2), "zh")
    if not all((subject, predicate, time)):
        return None
    return _contract("zh", "quoted_report", "quotation", "quoted_proposition", subject, predicate, time=time, rule_id="p4_z_zh_quote_v1")


def _parse_quote_en(text):
    outer = re.search(r"only a quote:\s*[\"](.+?)[\"]", text, re.IGNORECASE)
    if not outer:
        return None
    inner = outer.group(1).strip(" ,")
    match = re.fullmatch(r"the (.+?) (closes|stops accepting) at ([a-z]+)", inner, re.IGNORECASE)
    if not match:
        return None
    subject = _EN_QUOTE_SUBJECT.get(match.group(1).lower())
    predicate = {"closes": "閉まる", "stops accepting": "受付を終了する"}.get(match.group(2).lower())
    time = _number_jp(match.group(3), "en")
    if not all((subject, predicate, time)):
        return None
    return _contract("en", "quoted_report", "quotation", "quoted_proposition", subject, predicate, time=time, rule_id="p4_z_en_quote_v1")


def _parse_quote_ja(text):
    if not re.search(r"引用|記載", text):
        return None
    outer = re.search(r"「(.+?)」", text)
    if not outer:
        return None
    inner = outer.group(1).strip()
    match = re.fullmatch(r"(.+?)は([一二三四五六七八九十])時に(閉まる|受付を終了する)", inner)
    if not match:
        return None
    return _contract("ja", "quoted_report", "quotation", "quoted_proposition", match.group(1), match.group(3), time=f"{match.group(2)}時", rule_id="p4_z_ja_quote_identity_v1")


def _parse_hearsay_zh(text):
    match = re.fullmatch(r"(?:聽說|听说)(.+?)把(.+?)忘在(.+?)(?:上)?[。.]?", text.strip())
    if not match:
        return None
    subject = _ZH_SUBJECT.get(match.group(1))
    obj = _ZH_OBJECT.get(match.group(2))
    location = _ZH_LOCATION.get(match.group(3))
    if not all((subject, obj, location)):
        return None
    return _contract("zh", "hearsay_statement", "hearsay", "third_party", subject, "置き忘れた", obj=obj, location=location, rule_id="p4_z_zh_hearsay_v1")


def _parse_hearsay_en(text):
    match = re.fullmatch(r"Apparently (.+?) left the (.+?) in the (.+?)[.]?", text.strip(), re.IGNORECASE)
    if not match:
        return None
    subject = _EN_SUBJECT.get(match.group(1).lower())
    obj = _EN_OBJECT.get(match.group(2).lower())
    location = _EN_LOCATION.get(match.group(3).lower())
    if not all((subject, obj, location)):
        return None
    return _contract("en", "hearsay_statement", "hearsay", "third_party", subject, "置き忘れた", obj=obj, location=location, rule_id="p4_z_en_hearsay_v1")


def _parse_hearsay_ja(text):
    match = re.fullmatch(r"(.+?)は(.+?)を(?:(.+?)に)?(置き忘れた|なくした)らしい[。.]?", text.strip())
    if not match:
        return None
    return _contract("ja", "hearsay_statement", "hearsay", "third_party", match.group(1), match.group(4), obj=match.group(2), location=match.group(3), rule_id="p4_z_ja_hearsay_identity_v1")


def _parse_hypothetical_zh(text):
    if not re.search(r"(?:假設|假设)", text) or not re.search(r"如果我說|如果我说", text):
        return None
    quoted = re.search(r"「(.+?)」", text)
    if not quoted:
        return None
    match = re.fullmatch(r"我會把(.+?)(取消|移動|归还|歸還)", quoted.group(1))
    if not match:
        return None
    obj = _ZH_OBJECT.get(match.group(1))
    predicate = {"取消": "キャンセルする", "移動": "動かす", "归还": "返す", "歸還": "返す"}.get(match.group(2))
    if not all((obj, predicate)):
        return None
    return _contract("zh", "hypothetical_instruction", "hypothetical", "user_first_person", "そっち", predicate, obj=obj, rule_id="p4_z_zh_hypothetical_v1")


def _parse_hypothetical_en(text):
    if not re.search(r"\bhypothetical\b", text, re.IGNORECASE):
        return None
    quoted = re.search(r"If I said\s*[\"](.+?)[\"]", text, re.IGNORECASE)
    if not quoted:
        return None
    inner = quoted.group(1).strip(" ,")
    match = re.fullmatch(r"I will (cancel|return|move) (?:the )?(.+?)(?: (tomorrow))?", inner, re.IGNORECASE)
    if not match:
        return None
    predicate = {"cancel": "キャンセルする", "return": "返す", "move": "動かす"}.get(match.group(1).lower())
    obj = _EN_OBJECT.get(match.group(2).lower())
    if match.group(2).lower() == "morning train":
        obj = "朝の電車"
    time = "明日" if match.group(3) else None
    if not all((predicate, obj)):
        return None
    return _contract("en", "hypothetical_instruction", "hypothetical", "user_first_person", "そっち", predicate, obj=obj, time=time, rule_id="p4_z_en_hypothetical_v1")


def _parse_hypothetical_ja(text):
    if "仮定" not in text or not re.search(r"私が言った", text):
        return None
    quoted = re.search(r"「(.+?)」", text)
    if not quoted:
        return None
    inner = quoted.group(1).replace("、", "").strip()
    match = re.fullmatch(r"(?:(明日|来週))?(.+?)を(片づける|返す|動かす)", inner)
    if not match:
        return None
    return _contract("ja", "hypothetical_instruction", "hypothetical", "user_first_person", "そっち", match.group(3), obj=match.group(2), time=match.group(1), rule_id="p4_z_ja_hypothetical_identity_v1")


def extract_source_bound_proposition_p4(source):
    """Return a bounded source-only proposition, or ``None`` when unsupported."""

    text = str(source or "").strip()
    language = _language(text)
    parsers = {
        "zh": (_parse_quote_zh, _parse_hearsay_zh, _parse_hypothetical_zh),
        "en": (_parse_quote_en, _parse_hearsay_en, _parse_hypothetical_en),
        "ja": (_parse_quote_ja, _parse_hearsay_ja, _parse_hypothetical_ja),
    }[language]
    for parser in parsers:
        contract = parser(text)
        if contract:
            return contract
    return None


def _field_values(contract):
    return {
        key: contract.get(key)
        for key in ("subject_jp", "predicate_jp", "object_jp", "time_jp", "location_jp")
        if contract.get(key)
    }


def inspect_visible_proposition_p4(contract, candidate):
    if not contract:
        return {"supported": False, "violations": ["source_pattern_unavailable"]}
    visible = str(candidate or "")
    violations = []
    for field, value in _field_values(contract).items():
        if str(value) not in visible:
            violations.append(f"source_{field.removesuffix('_jp')}_missing")
    stance = contract.get("embedding_stance")
    if stance == "quotation" and "引用" not in visible:
        violations.append("quotation_stance_missing_or_changed")
    elif stance == "hearsay" and not ("らしい" in visible and "話" in visible):
        violations.append("hearsay_stance_missing_or_changed")
    elif stance == "hypothetical" and "仮定" not in visible:
        violations.append("hypothetical_stance_missing_or_changed")
    if contract.get("speaker_owner") == "user_first_person":
        if "そっち" not in visible:
            violations.append("user_speaker_owner_missing")
        if _AGENT_OWNER.search(visible):
            violations.append("user_speaker_owner_shifted_to_agent")
    return {"supported": True, "violations": sorted(set(violations))}


def _render(contract):
    family = contract["family"]
    subject = contract["subject_jp"]
    predicate = contract["predicate_jp"]
    obj = contract.get("object_jp")
    time = contract.get("time_jp")
    location = contract.get("location_jp")
    if family == "quoted_report":
        proposition = f"{subject}は{time}に{predicate}"
        return f"「{proposition}」っていう引用なんだね。"
    if family == "hearsay_statement":
        destination = f"{location}に" if location else ""
        return f"{subject}が{obj}を{destination}{predicate}らしいって話ね。"
    if family == "hypothetical_instruction":
        temporal = str(time or "")
        return f"「{subject}が{temporal}{obj}を{predicate}」っていう仮定の話ね。"
    return ""


def _trace_contract(contract):
    fields = _field_values(contract)
    return {
        "source_language": contract.get("source_language"),
        "family": contract.get("family"),
        "embedding_stance": contract.get("embedding_stance"),
        "speaker_owner": contract.get("speaker_owner"),
        "rule_id": contract.get("rule_id"),
        "known_field_types": sorted(fields),
        "unknown_field_types": sorted(
            key for key in ("subject_jp", "predicate_jp", "object_jp", "time_jp", "location_jp") if not contract.get(key)
        ),
        "source_anchor_digests": {key: _digest(value) for key, value in sorted(fields.items())},
    }


def preserve_source_bound_proposition_p4(source, candidate):
    """Verify and, only for a complete bounded source parse, repair the surface."""

    before = str(candidate or "")
    contract = extract_source_bound_proposition_p4(source)
    if not contract:
        trace = {
            "schema": SCHEMA,
            "status": "source_pattern_unavailable",
            "action": "abstain_unchanged",
            "source_language": _language(source),
            "family": None,
            "embedding_stance": None,
            "speaker_owner": None,
            "known_field_types": [],
            "unknown_field_types": ["subject_jp", "predicate_jp", "object_jp", "time_jp", "location_jp"],
            "source_anchor_digests": {},
            "violations_before": ["source_pattern_unavailable"],
            "violations_after": ["source_pattern_unavailable"],
            "changed": False,
            "before_digest": _digest(before),
            "after_digest": _digest(before),
            "raw_source_or_reply_persisted": False,
            "model_call_added": False,
            "fact_write_count": 0,
            "profile_write_count": 0,
            "episode_write_count": 0,
            "claim_boundary": "bounded source-only proposition preservation; unsupported sources are unchanged",
        }
        return before, trace

    before_audit = inspect_visible_proposition_p4(contract, before)
    if before_audit["violations"]:
        after = _render(contract)
        action = "source_bound_repair"
    else:
        after = before
        action = "verified_noop"
    after_audit = inspect_visible_proposition_p4(contract, after)
    trace = {
        "schema": SCHEMA,
        "status": "repaired_and_verified" if action == "source_bound_repair" and not after_audit["violations"] else (
            "accepted_verified" if action == "verified_noop" and not after_audit["violations"] else "repair_failed_closed"
        ),
        "action": action,
        **_trace_contract(contract),
        "violations_before": before_audit["violations"],
        "violations_after": after_audit["violations"],
        "changed": after != before,
        "before_digest": _digest(before),
        "after_digest": _digest(after),
        "raw_source_or_reply_persisted": False,
        "model_call_added": False,
        "fact_write_count": 0,
        "profile_write_count": 0,
        "episode_write_count": 0,
        "claim_boundary": "bounded source-only proposition preservation in quotation, hearsay and hypothetical grammars; not open-domain semantics",
    }
    return after, trace


def append_source_bound_proposition_node_p4(result):
    if not isinstance(result, dict):
        return result
    trace = deepcopy(((result.get("logic") or {}).get(LABEL)) or {})
    if not trace:
        return result
    runtime_trace = result.setdefault("runtime_trace", {})
    blackboard = [row for row in list(runtime_trace.get("blackboard") or []) if row.get("label") != LABEL]
    insert_at = next((index for index, row in enumerate(blackboard) if row.get("label") == "utterance"), len(blackboard))
    blackboard.insert(
        insert_at,
        {
            "stage": "surface",
            "label": LABEL,
            "payload": deepcopy(trace),
            "salience": 1.0 if trace.get("changed") else 0.86,
        },
    )
    runtime_trace["blackboard"] = blackboard
    runtime_trace[LABEL] = deepcopy(trace)
    result["runtime_trace"] = runtime_trace
    return result


_INSTALLED_P4_Z = False
_ORIGINAL_VISIBLE_GUARD_P4_Z = None
_ORIGINAL_RUN_TURN_DEBUG_P4_Z = None


def install_source_bound_proposition_preservation_p4():
    global _INSTALLED_P4_Z, _ORIGINAL_VISIBLE_GUARD_P4_Z, _ORIGINAL_RUN_TURN_DEBUG_P4_Z
    if _INSTALLED_P4_Z:
        return False
    from uruha_brain_mac import RightBrain, UruhaBrainV4_Mac

    _ORIGINAL_VISIBLE_GUARD_P4_Z = RightBrain.enforce_user_visible_japanese
    _ORIGINAL_RUN_TURN_DEBUG_P4_Z = UruhaBrainV4_Mac.run_turn_debug

    def guarded_with_p4_z(self, reply, logic_data, user_input="", memory_data=None):
        visible = _ORIGINAL_VISIBLE_GUARD_P4_Z(
            self,
            reply,
            logic_data,
            user_input=user_input,
            memory_data=memory_data,
        )
        preserved, trace = preserve_source_bound_proposition_p4(user_input, visible)
        logic_data[LABEL] = trace
        return preserved

    def run_turn_debug_with_p4_z(self, *args, **kwargs):
        result = _ORIGINAL_RUN_TURN_DEBUG_P4_Z(self, *args, **kwargs)
        result = append_source_bound_proposition_node_p4(result)
        if getattr(self.runtime, "turn_traces", None):
            self.runtime.turn_traces[-1] = deepcopy(result["runtime_trace"])
        return result

    RightBrain.enforce_user_visible_japanese = guarded_with_p4_z
    UruhaBrainV4_Mac.run_turn_debug = run_turn_debug_with_p4_z
    _INSTALLED_P4_Z = True
    return True


def _contract_subset(contract):
    return {key: contract.get(key) for key in REQUIRED_FIELDS}


def build_dataset_evidence_p4_z(dataset_path):
    dataset_path = Path(dataset_path)
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    metrics = {
        "development_exact_contract_count": 0,
        "development_exact_reply_count": 0,
        "development_verified_after_count": 0,
        "holdout_exact_contract_count": 0,
        "holdout_exact_reply_count": 0,
        "holdout_verified_after_count": 0,
        "faithful_control_unchanged_count": 0,
        "unsupported_control_abstained_count": 0,
        "unsupported_control_unchanged_count": 0,
        "trace_raw_source_or_reply_count": 0,
        "new_model_call_count": 0,
        "fact_write_count": 0,
        "profile_write_count": 0,
        "episode_write_count": 0,
    }
    cases = []
    for partition in ("development_failures", "holdout_failures"):
        prefix = "development" if partition.startswith("development") else "holdout"
        for frozen in dataset[partition]:
            contract = extract_source_bound_proposition_p4(frozen["source"])
            visible, trace = preserve_source_bound_proposition_p4(frozen["source"], frozen["candidate"])
            exact_contract = _contract_subset(contract or {}) == frozen["expected_contract"]
            exact_reply = visible == frozen["expected_reply"]
            verified = trace["violations_after"] == [] and trace["status"] == "repaired_and_verified"
            metrics[f"{prefix}_exact_contract_count"] += int(exact_contract)
            metrics[f"{prefix}_exact_reply_count"] += int(exact_reply)
            metrics[f"{prefix}_verified_after_count"] += int(verified)
            encoded = json.dumps(trace, ensure_ascii=False)
            metrics["trace_raw_source_or_reply_count"] += int(frozen["source"] in encoded or visible in encoded)
            cases.append({
                "case_id": frozen["case_id"],
                "partition": partition,
                "exact_contract": exact_contract,
                "exact_reply": exact_reply,
                "status": trace["status"],
                "action": trace["action"],
                "violations_before": trace["violations_before"],
                "violations_after": trace["violations_after"],
                "changed": trace["changed"],
            })
    for frozen in dataset["faithful_controls"]:
        visible, trace = preserve_source_bound_proposition_p4(frozen["source"], frozen["candidate"])
        metrics["faithful_control_unchanged_count"] += int(visible == frozen["candidate"] and trace["status"] == "accepted_verified" and not trace["changed"])
        encoded = json.dumps(trace, ensure_ascii=False)
        metrics["trace_raw_source_or_reply_count"] += int(frozen["source"] in encoded or visible in encoded)
        cases.append({"case_id": frozen["case_id"], "partition": "faithful_controls", "status": trace["status"], "changed": trace["changed"]})
    for frozen in dataset["unsupported_controls"]:
        visible, trace = preserve_source_bound_proposition_p4(frozen["source"], frozen["candidate"])
        metrics["unsupported_control_abstained_count"] += int(trace["status"] == "source_pattern_unavailable")
        metrics["unsupported_control_unchanged_count"] += int(visible == frozen["candidate"] and not trace["changed"])
        encoded = json.dumps(trace, ensure_ascii=False)
        metrics["trace_raw_source_or_reply_count"] += int(frozen["source"] in encoded or visible in encoded)
        cases.append({"case_id": frozen["case_id"], "partition": "unsupported_controls", "status": trace["status"], "changed": trace["changed"]})

    integration_metrics = {
        "graph_trace_exact_payload_count": 0,
        "graph_surface_chain_exact_count": 0,
        "visible_reply_exact_count": 0,
        "logic_trace_exact_count": 0,
    }
    required_chain = [p4t.LABEL, p4v.LABEL, p4w.LABEL, LABEL, "utterance"]
    for frozen in dataset["holdout_failures"][:3]:
        visible, trace = preserve_source_bound_proposition_p4(frozen["source"], frozen["candidate"])
        logic = {
            p4t.LABEL: {"schema": "fixture:p4t"},
            p4v.LABEL: {"schema": "fixture:p4v"},
            p4w.LABEL: {"schema": "fixture:p4w"},
            LABEL: deepcopy(trace),
        }
        result = {
            "reply": visible,
            "logic": deepcopy(logic),
            "runtime_trace": {"blackboard": [{"stage": "surface", "label": "utterance", "payload": {}}]},
        }
        result = p4y.deliver_existing_surface_traces_p4(result)
        result = append_source_bound_proposition_node_p4(result)
        labels = [row.get("label") for row in result["runtime_trace"]["blackboard"]]
        chain = [label for label in labels if label in required_chain]
        payloads = [row.get("payload") for row in result["runtime_trace"]["blackboard"] if row.get("label") == LABEL]
        integration_metrics["graph_trace_exact_payload_count"] += int(payloads == [trace] and result["runtime_trace"].get(LABEL) == trace)
        integration_metrics["graph_surface_chain_exact_count"] += int(chain == required_chain)
        integration_metrics["visible_reply_exact_count"] += int(result["reply"] == frozen["expected_reply"])
        integration_metrics["logic_trace_exact_count"] += int(result["logic"].get(LABEL) == trace)

    return {
        "schema": "uruha_p4_z_source_bound_proposition_evidence_v1",
        "dataset_sha256": hashlib.sha256(dataset_path.read_bytes()).hexdigest(),
        "metrics": metrics,
        "integration_metrics": integration_metrics,
        "cases": cases,
        "claim_boundary": dataset["claim_boundary"],
    }
