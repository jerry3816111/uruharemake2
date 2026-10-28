"""Product-only grammar for natural current-turn practical-help requests.

M47 already owns the help/no-help route and M45.1/M46 own source-bounded
delivery.  This adapter only adds natural request constructions such as
"help me come up with a way".  It emits the same typed geometry as M47 and
does not generate an answer or infer a private state.
"""
from copy import deepcopy
import re

import uruha_actionable_help_delivery_m45 as action45
import uruha_crosslingual_help_routing_m47 as m47
import uruha_task_evidence_authorization_m45_1 as task_gate


LABEL = "current_request_authority_p2"
SCHEMA = "uruha_current_request_authority_p2"
_INSTALLED = False
_ORIGINAL_ROUTE = None
_ORIGINAL_MATERIALIZE = None
_ORIGINAL_TASK_SOURCES = None

_CLAUSE_START = r"(?:^|(?<=[。！？!?；;，,、\n]))\s*"
_ZH_TRANSITION = r"(?:(?:不過|不过|但是|現在|现在|那|那麼|那么)\s*){0,3}"
_EN_TRANSITION = r"(?:(?:but|now|please)\s+){0,3}"
_JA_TRANSITION = r"(?:(?:でも|じゃあ|今は|それなら)\s*){0,3}"

POSITIVE_PATTERNS = {
    "zh": (
        _CLAUSE_START
        + _ZH_TRANSITION
        + r"(?:請|请|麻煩|麻烦)?\s*(?:幫|帮)我[^。！？!?；;，,\n]{0,8}"
          r"(?:想|找|整理|規劃|规划|決定|定出|提出)[^。！？!?；;，,\n]{0,8}"
          r"(?:做法|方法|辦法|办法|步驟|步骤|下一步)",
        _CLAUSE_START
        + _ZH_TRANSITION
        + r"(?:可以|可不可以|能不能)[^。！？!?；;，,\n]{0,6}(?:幫|帮)我[^。！？!?；;，,\n]{0,8}"
          r"(?:想|找|決定)[^。！？!?；;，,\n]{0,8}(?:怎麼做|怎么做|做法|方法|辦法|办法|下一步)",
    ),
    "en": (
        _CLAUSE_START
        + _EN_TRANSITION
        + r"(?:(?:can|could|would)\s+you\s+)?(?:please\s+)?help\s+me\s+"
          r"(?:come\s+up\s+with|figure\s+out|find|choose|decide\s+on)\s+"
          r"(?:(?:a|one|the)\s+)?(?:way|method|approach|step|next\s+step)\b",
    ),
    "ja": (
        _CLAUSE_START
        + _JA_TRANSITION
        + r"(?:ちょっと\s*)?(?:方法|やり方|手順|次の一歩)(?:を)?[^。！？!?；;、,\n]{0,6}"
          r"(?:一緒に\s*)?(?:考えて(?!い)|探して(?!い)|決めて(?!い))"
          r"(?:ほしい|くれない|くれる|もらえる|ください)?",
        _CLAUSE_START
        + _JA_TRANSITION
        + r"(?:一緒に\s*)?(?:どうすればいいか|何をすればいいか)[^。！？!?；;、,\n]{0,6}"
          r"(?:考えて(?!い)|決めて(?!い))(?:ほしい|くれない|くれる|もらえる|ください)?",
    ),
}

NEGATIVE_PATTERNS = {
    "zh": (
        _CLAUSE_START
        + _ZH_TRANSITION
        + r"(?:不要|不用|別|别)\s*(?:幫|帮)我[^。！？!?；;，,\n]{0,14}"
          r"(?:做法|方法|辦法|办法|步驟|步骤|下一步)",
    ),
    "en": (
        _CLAUSE_START
        + _EN_TRANSITION
        + r"(?:do\s+not|don't|no\s+need\s+to)\s+help\s+me\s+"
          r"(?:come\s+up\s+with|figure\s+out|find|choose)[^.!?;,\n]{0,18}"
          r"(?:way|method|approach|step)\b",
    ),
    "ja": (
        _CLAUSE_START
        + _JA_TRANSITION
        + r"(?:方法|やり方|手順|次の一歩).{0,10}"
          r"(?:考えなくていい|考えないで|探さなくていい|決めなくていい)",
    ),
}

_DISCOURSE_ACK = re.compile(
    r"(?:謝謝|谢谢|多謝|多谢|感謝|感谢|thanks?|thank\s+you|ありがとう|ありがと|助かった)",
    re.I,
)


def _evidence(text, patterns, kind):
    rows = []
    for language, group in patterns.items():
        for index, pattern in enumerate(group, start=1):
            for match in re.finditer(pattern, text, re.I):
                rows.append(
                    {
                        "kind": kind,
                        "language": language,
                        "cue_id": f"solve_regulation:{language}:p2:{kind}:{index}",
                        "start": match.start(),
                        "end": match.end(),
                        "length": match.end() - match.start(),
                        "span_digest": m47._digest(match.group(0)),
                    }
                )
    return rows


def classify_help_route_p2(user_input):
    """Extend M47 only when a new natural request construction is decisive."""
    text = str(user_input or "")
    base = deepcopy(_ORIGINAL_ROUTE(text))
    positives = _evidence(text, POSITIVE_PATTERNS, "authorize")
    negatives = _evidence(text, NEGATIVE_PATTERNS, "forbid")
    positives = [
        row
        for row in positives
        if not any(
            negative["start"] <= row["start"] and row["end"] <= negative["end"]
            for negative in negatives
        )
    ]
    new_rows = positives + negatives
    if not new_rows:
        return base

    evidence = list(base.get("candidate_evidence") or []) + new_rows
    unique = {}
    for row in evidence:
        unique[(row.get("kind"), row.get("cue_id"), row.get("start"), row.get("end"))] = row
    evidence = sorted(unique.values(), key=lambda row: (row["end"], row["length"]))[-8:]
    decisive = evidence[-1]
    if ":p2:" not in str(decisive.get("cue_id") or ""):
        return base

    authorized = decisive["kind"] == "authorize"
    desired = m47._span_ref(text, decisive["start"], decisive["end"], "desired_response_clause")
    task_spans = m47._task_refs(text, decisive, evidence) if authorized else []
    task_spans = [
        row
        for row in task_spans
        if not _pure_discourse_ack(text[row["start"] : row["end"]])
    ]
    audit = {
        "schema": SCHEMA,
        "status": "natural_help_request_authorized" if authorized else "natural_help_request_forbidden",
        "base_status": base.get("status"),
        "direction": decisive["kind"],
        "language": decisive["language"],
        "cue_id": decisive["cue_id"],
        "desired_response_span": deepcopy(desired),
        "task_span_count": len(task_spans),
        "model_call_added": False,
        "long_term_memory_write": False,
        "raw_dialogue_persisted": False,
        "claim_boundary": "current observable response-form request only; not task completion or private-state truth",
    }
    base.update(
        status="practical_help_authorized" if authorized else "practical_help_forbidden",
        detected=True,
        direction=decisive["kind"],
        language=decisive["language"],
        cue_id=decisive["cue_id"],
        desired_response_span=desired,
        task_spans=task_spans,
        candidate_evidence=[
            {key: row[key] for key in ("kind", "language", "cue_id", "start", "end", "length", "span_digest")}
            for row in evidence
        ],
        selected_policy="solve_regulation" if authorized else None,
        negated_policy=None if authorized else "solve_regulation",
        input_digest=m47._digest(text),
        raw_dialogue_persisted=False,
        long_term_memory_write=False,
    )
    base[LABEL] = audit
    return base


def _pure_discourse_ack(text):
    normalized = re.sub(r"[\s。！？!?；;，,、.…]+", "", str(text or "")).strip()
    return bool(normalized and _DISCOURSE_ACK.fullmatch(normalized))


def task_sources_p2(sources):
    """Do not let a pure acknowledgement become the task for a new request."""
    kept, gate = _ORIGINAL_TASK_SOURCES(sources)
    originals = {row.get("id"): row for row in sources if row.get("kind") == "current_user"}
    final = []
    removed = []
    p2_scoped = False
    for row in kept:
        origin = row.get("origin") or {}
        source = originals.get(origin.get("source_id"))
        route = classify_help_route_p2((source or {}).get("text")) if source else {}
        scoped = isinstance(route.get(LABEL), dict) and route.get("status") == "practical_help_authorized"
        p2_scoped = p2_scoped or scoped
        desired = route.get("desired_response_span") or {}
        row_start = origin.get("span_start")
        row_end = row_start + origin.get("span_length", 0) if isinstance(row_start, int) else None
        overlaps_request = bool(
            isinstance(row_start, int)
            and isinstance(row_end, int)
            and isinstance(desired.get("start"), int)
            and isinstance(desired.get("end"), int)
            and row_start < desired["end"]
            and desired["start"] < row_end
        )
        discourse_only = _pure_discourse_ack(row.get("text"))
        if scoped and row.get("kind") == "current_user" and (discourse_only or overlaps_request):
            removed.append(
                {
                    "source_id": origin.get("source_id"),
                    "span_start": origin.get("span_start"),
                    "span_length": origin.get("span_length"),
                    "span_digest": origin.get("span_digest"),
                    "reason": (
                        "current_request_discourse_ack_not_task"
                        if discourse_only
                        else "current_request_response_form_not_task"
                    ),
                }
            )
            continue
        final.append(row)
    if not p2_scoped:
        return kept, gate
    gate = deepcopy(gate)
    gate["allowed_clause_count"] = len(final)
    gate["allowed_origins"] = [deepcopy(row.get("origin") or {}) for row in final]
    gate["status"] = "content_available" if final else "no_independent_task_content"
    gate.setdefault("excluded", []).extend(removed)
    gate[LABEL] = {
        "schema": SCHEMA,
        "status": "discourse_only_sources_removed" if removed else "no_discourse_source_removed",
        "removed_count": len(removed),
        "removed": removed,
        "final_allowed_count": len(final),
        "raw_dialogue_persisted": False,
        "long_term_memory_write": False,
        "claim_boundary": "pure acknowledgement exclusion only; not general task understanding",
    }
    return final, gate


def materialize_current_request_trace_p2(result, feedback=None):
    _ORIGINAL_MATERIALIZE(result, feedback)
    from uruha_trace_history_sync_m41_1 import sync_current_history_m41_1

    logic = result.setdefault("logic", {})
    explicit = logic.get("explicit_desired_response_m25") or {}
    route = logic.get(m47.LABEL) or explicit.get(m47.LABEL) or {}
    state = deepcopy(route.get(LABEL)) if isinstance(route, dict) else None
    if not isinstance(state, dict):
        return
    delivery = logic.get(action45.LABEL) or {}
    source_gate = delivery.get(task_gate.LABEL) or {}
    source_audit = source_gate.get(LABEL) if isinstance(source_gate, dict) else None
    state.update(
        actual_selected_policy=(
            logic.get("desired_response_policy_m18")
            or logic.get("desired_response_policy_m17")
            or logic.get("desired_response_policy_m16")
        ),
        m47_route_consistent=route.get("route_consistent"),
        m46_should_intervene=route.get("m46_should_intervene"),
        m46_did_intervene=route.get("m46_did_intervene"),
        source_gate=deepcopy(source_audit) if isinstance(source_audit, dict) else None,
        final_reply_digest=m47._digest(result.get("reply") or ""),
    )
    logic[LABEL] = deepcopy(state)
    trace = result.setdefault("runtime_trace", {})
    rows = [row for row in trace.get("blackboard", []) if row.get("label") != LABEL]
    index = next(
        (i for i, row in enumerate(rows) if row.get("label") == m47.LABEL),
        next((i for i, row in enumerate(rows) if row.get("label") == "utterance"), len(rows)),
    )
    rows.insert(index, {"stage": "route", "label": LABEL, "payload": deepcopy(state), "salience": 1.0})
    trace["blackboard"] = rows
    trace[LABEL] = deepcopy(state)
    sync_current_history_m41_1(result)


def install_current_request_authority_p2():
    global _INSTALLED, _ORIGINAL_ROUTE, _ORIGINAL_MATERIALIZE, _ORIGINAL_TASK_SOURCES
    if _INSTALLED:
        return False
    _ORIGINAL_ROUTE = m47.classify_help_route_m47
    _ORIGINAL_MATERIALIZE = action45.materialize_trace_m45
    _ORIGINAL_TASK_SOURCES = task_gate.task_sources
    m47.classify_help_route_m47 = classify_help_route_p2
    action45.materialize_trace_m45 = materialize_current_request_trace_p2
    task_gate.task_sources = task_sources_p2
    _INSTALLED = True
    return True
