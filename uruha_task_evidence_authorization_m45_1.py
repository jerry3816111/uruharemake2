"""M45.1: response-form evidence is not independent task-content evidence.

Conservative clause authorization using existing classifiers, NOT a new topic
whitelist or general task parser. A task embedded in the same request clause
may be withheld. Keep M45's failed first Web run and frozen implementation.
"""
import re
import time

import uruha_actionable_help_delivery_m45 as base
import uruha_adaptive_person_model as adaptive

_ORIGINAL = base.deliver_action
_INSTALLED = False
LABEL = "task_evidence_authorization_m45_1"
_CLAUSE = re.compile(r"[^,，;；。.!！?？\n]+(?:[,，;；。.!！?？\n]+|$)")


def task_sources(sources):
    """Keep only exact independent clauses; no assistant-derived context."""
    kept, excluded = [], []
    for source in sources:
        if source.get("kind") not in {"current_user", "linked_previous_user"}:
            excluded.append({"source_id": source.get("id"), "reason": "not_user_evidence"})
            continue
        original = source.get("text") or ""
        for index, match in enumerate(_CLAUSE.finditer(original)):
            raw = match.group()
            text = raw.strip()
            if not text:
                continue
            offset = match.start() + len(raw) - len(raw.lstrip())
            request = adaptive.classify_explicit_desired_response_m25(text)
            correction = adaptive._explicit_correction_cues(text)
            origin = {"source_id": source["id"], "source_digest": base.digest(original),
                      "span_start": offset, "span_length": len(text), "span_digest": base.digest(text)}
            if request.get("detected") or correction.get("detected"):
                excluded.append({**origin, "reason": "response_form_or_correction_clause"})
                continue
            kept.append({"id": f'{source["id"]}:clause:{index}', "kind": source["kind"],
                         "text": text, "origin": origin})
    return kept, {"schema": LABEL, "status": "content_available" if kept else "no_independent_task_content",
                  "allowed_clause_count": len(kept), "excluded": excluded,
                  "allowed_origins": [s["origin"] for s in kept],
                  "raw_dialogue_persisted": False,
                  "claim_boundary": "bounded clause separation, not semantic proof or universal task extraction"}


def deliver_with_task_evidence(user_input, candidate, logic, sources, call_json=None):
    start = time.monotonic()
    if (base.surface39._selected_policy_m39(logic) != "solve_regulation" or base._protected(logic)
            or (logic.get("supported_feedback_closure_m43") or {}).get("authoritative")
            or (logic.get("feedback_topic_transition_m28") or {}).get("surface_authority")
            or any(len(s.get("text") or "") > 2000 for s in sources)):
        return _ORIGINAL(user_input, candidate, logic, sources, call_json)
    filtered, gate = task_sources(sources)
    gate["gate_seconds"] = round(time.monotonic() - start, 6)
    final, trace = _ORIGINAL(user_input, candidate, logic, filtered, call_json)
    if not filtered:
        # The original empty-source branch makes zero model calls. Do not allow
        # a model to manufacture a task before deciding whether one was given.
        final = base.CLARIFY.replace("\u3000", " ")
        trace.update(status="awaiting_context", delivered=False,
                     reason="no_independent_task_content_m45_1",
                     changed=final != str(candidate or ""), final_reply_digest=base.digest(final))
    trace[LABEL] = gate
    trace["including_task_gate_seconds_m45_1"] = round(time.monotonic() - start, 5)
    return final, trace


def install_m45_1_task_evidence():
    global _INSTALLED
    if _INSTALLED:
        return False
    base.deliver_action = deliver_with_task_evidence
    _INSTALLED = True
    return True


def render_m45_1(result):
    from uruha_m45_memory_observatory import render_memory_observatory_m45
    html = render_memory_observatory_m45(result)
    gate = ((result.get("logic") or {}).get(base.LABEL) or {}).get(LABEL)
    if not gate:
        return html
    count = gate["allowed_clause_count"]
    note = (f'任務來源分離 · M45.1：保留 {count} 段獨立內容；'
            f'排除 {len(gate["excluded"])} 段回覆形式要求。'
            '「想要方法」不是任務本身；沒有內容就不猜。此分句檢查仍有覆蓋限制。')
    return html.replace('<div class="m45-title">',
                        f'<div class="m45-note">{note}</div><div class="m45-title">', 1)
