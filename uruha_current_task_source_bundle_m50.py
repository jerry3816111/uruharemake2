"""M50: compose exact same-turn task fragments into one planner source."""
from copy import deepcopy
from html import escape

import uruha_actionable_help_delivery_m45 as action45
import uruha_goal_progress_delivery_m46 as m46
import uruha_task_evidence_authorization_m45_1 as task_gate
import uruha_crosslingual_help_routing_m47 as m47


LABEL = "current_task_source_bundle_m50"
SCHEMA = "uruha_current_task_source_bundle_m50"
_INSTALLED = False
_PREVIOUS_TASK_SOURCES = task_gate.task_sources
_PREVIOUS_MATERIALIZE = action45.materialize_trace_m45


def _source_by_id(sources, source_id):
    return next((row for row in sources if row.get("id") == source_id), None)


def _validated_components(original_source, rows):
    original = original_source.get("text")
    if not isinstance(original, str) or not original.strip() or len(original) > 2000:
        return None, "invalid_original_source"
    source_digest = action45.digest(original)
    components = []
    for row in rows:
        origin = row.get("origin") or {}
        try:
            start = int(origin.get("span_start"))
            length = int(origin.get("span_length"))
        except (TypeError, ValueError):
            return None, "invalid_component_offset"
        end = start + length
        text = row.get("text")
        if (origin.get("source_id") != original_source.get("id")
                or origin.get("source_digest") != source_digest
                or start < 0 or end > len(original) or length <= 0
                or original[start:end] != text
                or origin.get("span_digest") != action45.digest(text)):
            return None, "component_origin_mismatch"
        components.append({"row": row, "start": start, "end": end})
    components.sort(key=lambda item: (item["start"], item["end"]))
    if any(left["end"] > right["start"] for left, right in zip(components, components[1:])):
        return None, "component_overlap"
    return components, None


def task_sources_m50(sources):
    kept, gate = _PREVIOUS_TASK_SOURCES(sources)
    kept = list(kept)
    bundles, rejected = [], []
    current_groups = {}
    for row in kept:
        if row.get("kind") != "current_user":
            continue
        source_id = (row.get("origin") or {}).get("source_id")
        if source_id:
            current_groups.setdefault(source_id, []).append(row)

    replacement = {}
    for source_id, rows in current_groups.items():
        if len(rows) < 2:
            continue
        original_source = _source_by_id(sources, source_id)
        if not isinstance(original_source, dict):
            rejected.append({"source_id": source_id, "reason": "original_source_missing"})
            continue
        original = original_source.get("text") or ""
        route = m47.classify_help_route_m47(original)
        correction = task_gate.adaptive._explicit_correction_cues(original)
        if route.get("status") != "practical_help_authorized" or correction.get("detected"):
            rejected.append({"source_id": source_id, "reason": "route_or_correction_not_bundle_safe"})
            continue
        components, reason = _validated_components(original_source, rows)
        if reason:
            rejected.append({"source_id": source_id, "reason": reason})
            continue
        bundle_text = "\n".join(item["row"]["text"] for item in components)
        component_trace = [{
            "id": item["row"]["id"],
            "span_start": item["start"],
            "span_length": item["end"] - item["start"],
            "span_digest": action45.digest(item["row"]["text"]),
        } for item in components]
        bundle = {
            "id": f"{source_id}:m50:bundle",
            "kind": "current_user",
            "text": bundle_text,
            "source_role": "current_task_bundle_m50",
            "origin": {
                "source_id": source_id,
                "source_digest": action45.digest(original),
                "bundle_digest": action45.digest(bundle_text),
                "component_count": len(component_trace),
                "components": component_trace,
            },
        }
        for item in components:
            replacement[item["row"]["id"]] = bundle
        bundles.append(bundle)

    final, emitted = [], set()
    for row in kept:
        bundle = replacement.get(row.get("id"))
        if bundle:
            if bundle["id"] not in emitted:
                final.append(bundle)
                emitted.add(bundle["id"])
        else:
            final.append(row)

    state = {
        "schema": SCHEMA,
        "status": "bundled" if bundles else "not_bundled",
        "input_source_count": len(kept),
        "bundle_count": len(bundles),
        "bundles": [{
            "id": row["id"],
            "kind": row["kind"],
            "source_role": row["source_role"],
            "origin": deepcopy(row["origin"]),
        } for row in bundles],
        "rejected": rejected,
        "final_source_count": len(final),
        "compatibility_basis": "same_current_turn_nonoverlap_no_observable_correction",
        "semantic_compatibility_proven": False,
        "raw_dialogue_persisted": False,
        "long_term_memory_write": False,
        "claim_boundary": "exact fragment composition only; not semantic compatibility or plan quality proof",
    }
    gate = deepcopy(gate)
    gate["allowed_clause_count"] = len(final)
    gate["allowed_origins"] = [deepcopy(row.get("origin") or {}) for row in final]
    gate["status"] = "content_available" if final else "no_independent_task_content"
    gate[LABEL] = state
    return final, gate


def _extract_state(result):
    logic = result.get("logic") or {}
    delivery = logic.get(action45.LABEL) or {}
    gate = delivery.get(task_gate.LABEL) or {}
    state = deepcopy(gate.get(LABEL)) if isinstance(gate, dict) else None
    if not isinstance(state, dict):
        return None
    m46_state = delivery.get(m46.LABEL) or {}
    bundle_ids = {row.get("id") for row in state.get("bundles") or []}
    goal_source_id = ((m46_state.get("source") or {}).get("id")
                      if isinstance(m46_state, dict) else None)
    state.update(
        m46_status=m46_state.get("status") or "not_applicable",
        goal_source_id=goal_source_id,
        goal_selected_bundle=goal_source_id in bundle_ids if goal_source_id else False,
        delivered=delivery.get("delivered") is True,
    )
    return state


def materialize_trace_m50(result, feedback=None):
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


def render_m50(result):
    from uruha_route_qualified_task_handoff_m49 import render_m49
    html = render_m49(result)
    state = (result.get("logic") or {}).get(LABEL)
    if not isinstance(state, dict):
        state = _extract_state(result)
    if not isinstance(state, dict):
        return html
    selected = ("有，goal 使用完整 bundle" if state.get("goal_selected_bundle")
                else "沒有；bundle 到達不等於被採用")
    values = (
        ("原 task sources", state.get("input_source_count", 0)),
        ("完整 bundle", state.get("bundle_count", 0)),
        ("planner 可選來源", state.get("final_source_count", 0)),
        ("goal 使用 bundle", selected),
        ("M46 狀態", state.get("m46_status") or "未形成"),
        ("交付", "是" if state.get("delivered") else "否"),
    )
    nodes = '<span class="m50-arrow" aria-hidden="true">→</span>'.join(
        f'<div class="m50-node"><span>{escape(str(title))}</span><strong>{escape(str(value))}</strong></div>'
        for title, value in values
    )
    card = ('<section class="m50-flow" aria-label="M50 current task source bundle">'
            '<style>.m50-flow{grid-column:1/-1;background:linear-gradient(135deg,#173c42,#26455a);border:2px solid #63d4c7;border-radius:16px;padding:16px;margin:12px 0;color:#effffc}'
            '.m50-flow *{color:#effffc!important}.m50-title{font-size:19px;font-weight:750}.m50-sub{font-size:13px;line-height:1.6;margin-top:4px}.m50-nodes{display:flex;align-items:stretch;gap:7px;overflow-x:auto;margin-top:13px;padding-bottom:5px}'
            '.m50-node{min-width:168px;flex:1;background:#285461;padding:12px;border-radius:10px;overflow-wrap:anywhere}.m50-node span{display:block;font-size:12px;opacity:.82;margin-bottom:6px}.m50-node strong{font-size:15px;line-height:1.45}.m50-arrow{align-self:center;font-size:20px;color:#63d4c7!important}</style>'
            '<div class="m50-title">完整任務有沒有被拆成只能任選一段？ · M50</div>'
            '<div class="m50-sub">同一當輪的 exact task fragments 以一個 bundle 送入 planner；結構共現不等於已證明語意相容，也不等於回答有用。</div>'
            f'<div class="m50-nodes">{nodes}</div></section>')
    anchor = '<section class="m49-flow" aria-label="M49 route qualified task handoff">'
    return html.replace(anchor, card + anchor, 1) if anchor in html else card + html


def install_m50_current_task_source_bundle():
    global _INSTALLED, _PREVIOUS_TASK_SOURCES, _PREVIOUS_MATERIALIZE
    if _INSTALLED:
        return False
    _PREVIOUS_TASK_SOURCES = task_gate.task_sources
    _PREVIOUS_MATERIALIZE = action45.materialize_trace_m45
    task_gate.task_sources = task_sources_m50
    action45.materialize_trace_m45 = materialize_trace_m50
    _INSTALLED = True
    return True
