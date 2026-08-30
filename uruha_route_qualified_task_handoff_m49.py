"""M49: hand M47-qualified embedded task spans to M46 as evidence.

M45.1 conservatively excludes any whole clause containing a response-form
request. M47 later learned to identify non-overlapping task prefixes inside
that clause. This overlay hands only those exact current-input spans to M46;
it does not infer, translate, or answer the task.
"""
from copy import deepcopy
from html import escape

import uruha_actionable_help_delivery_m45 as action45
import uruha_goal_progress_delivery_m46 as m46
import uruha_task_evidence_authorization_m45_1 as task_gate
import uruha_crosslingual_help_routing_m47 as m47


LABEL = "route_qualified_task_handoff_m49"
SCHEMA = "uruha_route_qualified_task_handoff_m49"
_INSTALLED = False
_PREVIOUS_TASK_SOURCES = task_gate.task_sources
_PREVIOUS_MATERIALIZE = action45.materialize_trace_m45


def _overlaps(start, end, other):
    return not (end <= other.get("start", -1) or start >= other.get("end", -1))


def _trim_span(text, start, end):
    start, end = max(0, int(start)), min(len(text), int(end))
    while start < end and text[start] in " \t\r\n，,、":
        start += 1
    while end > start and text[end - 1] in " \t\r\n，,、":
        end -= 1
    return start, end


def task_sources_m49(sources):
    kept, gate = _PREVIOUS_TASK_SOURCES(sources)
    kept = list(kept)
    additions, rejected = [], []
    for source in sources:
        if source.get("kind") != "current_user":
            continue
        original = source.get("text")
        if not isinstance(original, str) or not original.strip() or len(original) > 2000:
            continue
        route = m47.classify_help_route_m47(original)
        if route.get("status") != "practical_help_authorized":
            continue
        response_refs = list(route.get("candidate_evidence") or [])
        desired = route.get("desired_response_span")
        if isinstance(desired, dict):
            response_refs.append(desired)
        for index, ref in enumerate(route.get("task_spans") or []):
            start, end = _trim_span(original, ref.get("start", 0), ref.get("end", 0))
            text = original[start:end]
            record = {
                "source_id": source.get("id"),
                "span_start": start,
                "span_length": end - start,
                "span_digest": action45.digest(text),
                "ref_role": ref.get("role"),
            }
            if not text:
                rejected.append({**record, "reason": "empty_after_trim"})
                continue
            if action45.digest(original[ref.get("start", 0):ref.get("end", 0)]) != ref.get("span_digest"):
                rejected.append({**record, "reason": "m47_span_digest_mismatch"})
                continue
            if any(_overlaps(start, end, row) for row in response_refs):
                rejected.append({**record, "reason": "overlaps_response_form_evidence"})
                continue
            # M47 owns the cross-lingual response-form split, but its prefix is
            # still only a candidate task span. Reuse M45.1's existing
            # response/correction classifiers on the isolated span so a meta
            # correction such as "You misunderstood" cannot become a task.
            isolated_request = task_gate.adaptive.classify_explicit_desired_response_m25(text)
            isolated_correction = task_gate.adaptive._explicit_correction_cues(text)
            if isolated_request.get("detected") or isolated_correction.get("detected"):
                rejected.append({**record, "reason": "isolated_response_or_correction_span"})
                continue
            already_covered = any(
                item.get("kind") == "current_user"
                and (item.get("origin") or {}).get("source_id") == source.get("id")
                and (item.get("origin") or {}).get("span_start", -1) <= start
                and end <= ((item.get("origin") or {}).get("span_start", -1)
                            + (item.get("origin") or {}).get("span_length", 0))
                for item in kept
            )
            if already_covered:
                rejected.append({**record, "reason": "already_present_as_independent_task_clause"})
                continue
            item = {
                "id": f'{source["id"]}:m49:{index}',
                "kind": "current_user",
                "text": text,
                "source_role": "route_qualified_task_span_m49",
                "origin": {
                    "source_id": source["id"],
                    "source_digest": action45.digest(original),
                    "span_start": start,
                    "span_length": len(text),
                    "span_digest": action45.digest(text),
                    "m47_role": ref.get("role"),
                    "m47_cue_id": route.get("cue_id"),
                },
            }
            kept.append(item)
            additions.append(item)

    # Model sources retain exact current text only for this turn. The trace
    # projection below is raw-free and is what enters graph/history.
    state = {
        "schema": SCHEMA,
        "status": "task_spans_added" if additions else "no_new_task_span",
        "base_allowed_count": gate.get("allowed_clause_count", 0),
        "added_count": len(additions),
        "added_sources": [
            {"id": row["id"], "kind": row["kind"], "source_role": row["source_role"],
             "origin": deepcopy(row["origin"])}
            for row in additions
        ],
        "rejected": rejected,
        "final_allowed_count": len(kept),
        "raw_dialogue_persisted": False,
        "long_term_memory_write": False,
        "claim_boundary": "exact current task-span handoff only; not plan use or source alignment proof",
    }
    gate = deepcopy(gate)
    gate["allowed_clause_count"] = len(kept)
    gate["allowed_origins"] = [deepcopy(row.get("origin") or {}) for row in kept]
    gate["status"] = "content_available" if kept else "no_independent_task_content"
    gate[LABEL] = state
    return kept, gate


def _extract_state(result):
    logic = result.get("logic") or {}
    delivery = logic.get(action45.LABEL) or {}
    gate = delivery.get(task_gate.LABEL) or {}
    state = deepcopy(gate.get(LABEL)) if isinstance(gate, dict) else None
    if not isinstance(state, dict):
        return None
    m46_state = delivery.get(m46.LABEL) or {}
    added_ids = {row.get("id") for row in state.get("added_sources") or []}
    goal_source_id = ((m46_state.get("source") or {}).get("id")
                      if isinstance(m46_state, dict) else None)
    state.update(
        m46_status=m46_state.get("status") or "not_applicable",
        goal_source_id=goal_source_id,
        goal_selected_added_span=goal_source_id in added_ids if goal_source_id else False,
        m46_source_count=len(delivery.get("sources") or []),
        delivered=delivery.get("delivered") is True,
    )
    return state


def materialize_trace_m49(result, feedback=None):
    _PREVIOUS_MATERIALIZE(result, feedback)
    from uruha_trace_history_sync_m41_1 import sync_current_history_m41_1
    state = _extract_state(result)
    if not state:
        return
    logic = result.setdefault("logic", {})
    logic[LABEL] = deepcopy(state)
    current = result.setdefault("runtime_trace", {})
    current[LABEL] = deepcopy(state)
    rows = [row for row in current.get("blackboard") or [] if row.get("label") != LABEL]
    index = next((i for i, row in enumerate(rows)
                  if row.get("label") in {m46.LABEL, "crosslingual_action_realization_m48",
                                          action45.LABEL, "utterance"}), len(rows))
    rows.insert(index, {"label": LABEL, "stage": "ground", "payload": deepcopy(state), "salience": 1.0})
    current["blackboard"] = rows
    sync_current_history_m41_1(result)


def render_m49(result):
    from uruha_crosslingual_action_realization_m48 import render_m48
    html = render_m48(result)
    state = (result.get("logic") or {}).get(LABEL)
    if not isinstance(state, dict):
        state = _extract_state(result)
    if not isinstance(state, dict):
        return html
    selected = ("有，planner goal 綁到新增 span" if state.get("goal_selected_added_span")
                else "沒有；只證明來源已送達")
    values = (
        ("M45.1 原來源", state.get("base_allowed_count", 0)),
        ("M47 task spans", state.get("added_count", 0)),
        ("M46 可用來源", state.get("final_allowed_count", 0)),
        ("新增 span 被選為 goal", selected),
        ("M46 狀態", state.get("m46_status") or "未形成"),
        ("交付", "是" if state.get("delivered") else "否"),
    )
    nodes = '<span class="m49-arrow" aria-hidden="true">→</span>'.join(
        f'<div class="m49-node"><span>{escape(str(title))}</span><strong>{escape(str(value))}</strong></div>'
        for title, value in values
    )
    card = ('<section class="m49-flow" aria-label="M49 route qualified task handoff">'
            '<style>.m49-flow{grid-column:1/-1;background:linear-gradient(135deg,#2b244d,#2b3156);border:2px solid #8fa8ff;border-radius:16px;padding:16px;margin:12px 0;color:#f4f6ff}'
            '.m49-flow *{color:#f4f6ff!important}.m49-title{font-size:19px;font-weight:750}.m49-sub{font-size:13px;line-height:1.6;margin-top:4px}.m49-nodes{display:flex;align-items:stretch;gap:7px;overflow-x:auto;margin-top:13px;padding-bottom:5px}'
            '.m49-node{min-width:168px;flex:1;background:#393b6a;padding:12px;border-radius:10px;overflow-wrap:anywhere}.m49-node span{display:block;font-size:12px;opacity:.82;margin-bottom:6px}.m49-node strong{font-size:15px;line-height:1.45}.m49-arrow{align-self:center;font-size:20px;color:#8fa8ff!important}</style>'
            '<div class="m49-title">任務內容有沒有在進 planner 前消失？ · M49</div>'
            '<div class="m49-sub">只把 M47 已分離且不重疊的 task span 交給 M46；送達不等於模型有遵守，也不等於回答有用。</div>'
            f'<div class="m49-nodes">{nodes}</div></section>')
    anchor = '<section class="m48-flow" aria-label="M48 crosslingual action realization">'
    return html.replace(anchor, card + anchor, 1) if anchor in html else card + html


def install_m49_route_qualified_task_handoff():
    global _INSTALLED, _PREVIOUS_TASK_SOURCES, _PREVIOUS_MATERIALIZE
    if _INSTALLED:
        return False
    _PREVIOUS_TASK_SOURCES = task_gate.task_sources
    _PREVIOUS_MATERIALIZE = action45.materialize_trace_m45
    task_gate.task_sources = task_sources_m49
    action45.materialize_trace_m45 = materialize_trace_m49
    _INSTALLED = True
    return True
