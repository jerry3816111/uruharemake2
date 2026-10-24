"""M48: realize an existing structured action as one bounded Japanese surface.

The overlay may repair only a mismatch between M46's already-formed action
fields and its visible instruction.  It cannot choose a task, object, progress
mechanism, ordering rule, or completion semantics.  M46's independent content
review remains authoritative.
"""
from copy import deepcopy
from contextvars import ContextVar
from html import escape
import re

import uruha_actionable_help_delivery_m45 as action45
import uruha_goal_progress_delivery_m46 as m46


LABEL = "crosslingual_action_realization_m48"
SCHEMA = "uruha_crosslingual_action_realization_m48"
_INSTALLED = False
_PREVIOUS_STRUCTURAL = m46.structural_plan_violations
_PREVIOUS_INSPECT = m46.inspect_goal_progress
_PREVIOUS_DIAGNOSTIC = m46._diagnostic
_PREVIOUS_MATERIALIZE = action45.materialize_trace_m45
_REPAIR_STATE = ContextVar("m48_action_surface_state", default={})

REPAIRABLE = {
    "instruction_missing_action_object",
    "instruction_missing_visible_stop",
    "invalid_instruction_jp",
    "noncasual_register",
}


def _remember(plan, trace):
    _REPAIR_STATE.set({id(plan): deepcopy(trace)})


def _state_for(plan):
    return deepcopy((_REPAIR_STATE.get() or {}).get(id(plan))) if isinstance(plan, dict) else None


def _te_form(verb):
    """Bounded dictionary-to-te conversion for a final declared action verb."""
    if not isinstance(verb, str) or len(verb) < 2:
        return None
    if verb.endswith("する"):
        return verb[:-2] + "して"
    if verb == "来る":
        return "来て"
    if verb == "行く":
        return "行って"
    godan_ru = ("取る", "切る", "作る", "貼る", "測る", "送る", "戻る", "並べる")
    # 並べる is ichidan; keep it out of the godan suffix exception.
    godan_ru = tuple(row for row in godan_ru if row != "並べる")
    if verb.endswith(godan_ru):
        return verb[:-1] + "って"
    ending = verb[-1]
    stem = verb[:-1]
    if ending in "うつる":
        # Common M46 action verbs such as 分ける／並べる are ichidan.
        if ending == "る" and verb.endswith(("ける", "べる", "める", "れる", "せる", "てる")):
            return stem + "て"
        return stem + "って"
    if ending in "むぶぬ":
        return stem + "んで"
    if ending == "く":
        return stem + "いて"
    if ending == "ぐ":
        return stem + "いで"
    if ending == "す":
        return stem + "して"
    return None


def _realize_from_fields(plan):
    obj = plan.get("action_object_jp")
    verb = plan.get("action_verb_jp")
    step = plan.get("action_step_jp")
    completion = plan.get("completion_jp")
    if not all((m46._valid_japanese(obj, 70, object_field=True),
                m46._valid_japanese(verb, 40),
                m46._valid_japanese(step, 180),
                m46._valid_japanese(completion, 120))):
        return None, "invalid_internal_action_fields"
    if obj not in step:
        return None, "action_step_does_not_contain_declared_object"
    if not m46._verb_realized(verb, step):
        return None, "action_step_does_not_realize_declared_verb"

    original = str(plan.get("instruction_jp") or "").strip()
    if (m46._valid_japanese(original, 220)
            and obj in original
            and not m46.surface39.formal_register_detected_m39(original)):
        base = original.rstrip("。.!！")
    else:
        base = step.strip().rstrip("。.!！")
        if base.endswith(verb):
            if verb.endswith(("よ", "ろ", "て", "で")):
                # Some structured decodes return the already-realized short
                # command despite the dictionary-form instruction. Preserve
                # that exact operation rather than guessing a new verb.
                base = base
            else:
                te = _te_form(verb)
                if not te:
                    return None, "declared_verb_has_no_bounded_surface_inflection"
                base = base[:-len(verb)] + te + "みよ"
        elif not re.search(r"(?:て|で|よ|よう|ろ)$", base):
            return None, "action_step_is_not_boundedly_realizable"

    # The stop sentence adds no new criterion: it refers only to completion of
    # the already-declared action.  The typed completion remains in trace and
    # the reviewer still decides whether it truly advances the task.
    candidate = base + "。それができたら、そこで止めよ。"
    if len(candidate) > 220 or obj not in candidate:
        return None, "realized_surface_exceeds_contract"
    if not m46._valid_japanese(candidate, 220):
        return None, "realized_surface_is_not_japanese"
    if m46.surface39.formal_register_detected_m39(candidate):
        return None, "realized_surface_is_not_casual"
    return candidate, "bounded_existing_action_surface"


def repair_action_surface_m48(plan, sources):
    before = _PREVIOUS_STRUCTURAL(plan, sources)
    trace = {
        "schema": SCHEMA,
        "status": "not_needed" if not before else "not_authorized",
        "formed_before_surface": True,
        "pre_repair_violations": list(before),
        "post_repair_violations": list(before),
        "repair_types": [],
        "object_jp": plan.get("action_object_jp") if isinstance(plan, dict) else None,
        "verb_jp": plan.get("action_verb_jp") if isinstance(plan, dict) else None,
        "completion_jp": plan.get("completion_jp") if isinstance(plan, dict) else None,
        "changed": False,
        "semantic_fields_changed": False,
        "raw_dialogue_persisted": False,
        "long_term_memory_write": False,
        "claim_boundary": "surface realization only; M46 content review still required",
    }
    if not isinstance(plan, dict) or not before:
        if isinstance(plan, dict):
            _remember(plan, trace)
        return before
    blockers = sorted(set(before) - REPAIRABLE)
    if blockers:
        trace.update(status="blocked_by_nonrealization_violation", blockers=blockers)
        _remember(plan, trace)
        return before

    candidate, reason = _realize_from_fields(plan)
    if not candidate:
        trace.update(status="repair_failed_closed", reason=reason)
        _remember(plan, trace)
        return before
    original = str(plan.get("instruction_jp") or "")
    plan["instruction_jp"] = candidate
    after = _PREVIOUS_STRUCTURAL(plan, sources)
    trace.update(
        status="repaired" if not after else "repair_failed_closed",
        reason=reason,
        post_repair_violations=list(after),
        repair_types=sorted(set(before) & REPAIRABLE),
        changed=candidate != original,
        before_digest=action45.digest(original),
        after_digest=action45.digest(candidate),
        object_visible=bool(plan.get("action_object_jp") in candidate),
        operation_visible=bool(m46._verb_realized(plan.get("action_verb_jp"), candidate)),
        stop_visible=bool(re.search(r"(?:たら|そこで|止め)", candidate)),
    )
    _remember(plan, trace)
    return after


def structural_plan_violations_m48(plan, sources):
    if _state_for(plan):
        # The plan may be checked again inside M46's final audit. Preserve the
        # first before/after record and only verify the current surface.
        return _PREVIOUS_STRUCTURAL(plan, sources)
    return repair_action_surface_m48(plan, sources)


def inspect_goal_progress_m48(plan, sources, review):
    result = _PREVIOUS_INSPECT(plan, sources, review)
    state = _state_for(plan) or {
        "schema": SCHEMA,
        "status": "not_available",
        "raw_dialogue_persisted": False,
        "long_term_memory_write": False,
    }
    state.update(
        m46_content_passed=result.get("content_passed") is True,
        m46_surface_passed=result.get("surface_passed") is True,
        reviewer_required=True,
    )
    result[LABEL] = state
    return result


def diagnostic_m48(plan, status):
    result = _PREVIOUS_DIAGNOSTIC(plan, status)
    state = _state_for(plan)
    if isinstance(state, dict):
        result[LABEL] = state
    return result


def _extract_state(result):
    logic = result.get("logic") or {}
    m46_state = logic.get(m46.LABEL)
    if not isinstance(m46_state, dict):
        m46_state = ((logic.get(action45.LABEL) or {}).get(m46.LABEL) or {})
    state = m46_state.get(LABEL) if isinstance(m46_state, dict) else None
    if not isinstance(state, dict):
        state = ((m46_state.get("diagnostic") or {}).get(LABEL)
                 if isinstance(m46_state, dict) else None)
    return deepcopy(state) if isinstance(state, dict) else None


def materialize_trace_m48(result, feedback=None):
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
                  if row.get("label") in {m46.LABEL, action45.LABEL, "utterance"}), len(rows))
    rows.insert(index, {"label": LABEL, "stage": "realize", "payload": deepcopy(state), "salience": 1.0})
    current["blackboard"] = rows
    sync_current_history_m41_1(result)


def render_m48(result):
    from uruha_crosslingual_help_routing_m47 import render_m47
    html = render_m47(result)
    state = (result.get("logic") or {}).get(LABEL)
    if not isinstance(state, dict):
        state = _extract_state(result)
    if not isinstance(state, dict):
        return html
    verdict = {
        "repaired": "表面已對齊，仍等 M46 審核",
        "not_needed": "原句已對齊",
        "blocked_by_nonrealization_violation": "內容問題，不准表面修補",
        "repair_failed_closed": "無法安全對齊，已拒絕",
    }.get(state.get("status"), state.get("status") or "未形成")
    values = (
        ("內部物件", state.get("object_jp") or "未形成"),
        ("內部操作", state.get("verb_jp") or "未形成"),
        ("原表面缺口", "／".join(state.get("pre_repair_violations") or []) or "無"),
        ("一致化", "已修正" if state.get("changed") else "未改動"),
        ("停止點", "可見" if state.get("stop_visible") else "原句或未通過"),
        ("最終權限", verdict),
    )
    nodes = '<span class="m48-arrow" aria-hidden="true">→</span>'.join(
        f'<div class="m48-node"><span>{escape(title)}</span><strong>{escape(str(value))}</strong></div>'
        for title, value in values
    )
    card = ('<section class="m48-flow" aria-label="M48 crosslingual action realization">'
            '<style>.m48-flow{grid-column:1/-1;background:linear-gradient(135deg,#40272a,#3c3520);border:2px solid #ffc46a;border-radius:16px;padding:16px;margin:12px 0;color:#fff8e8}'
            '.m48-flow *{color:#fff8e8!important}.m48-title{font-size:19px;font-weight:750}.m48-sub{font-size:13px;line-height:1.6;margin-top:4px}.m48-nodes{display:flex;align-items:stretch;gap:7px;overflow-x:auto;margin-top:13px;padding-bottom:5px}'
            '.m48-node{min-width:168px;flex:1;background:#5a4330;padding:12px;border-radius:10px;overflow-wrap:anywhere}.m48-node span{display:block;font-size:12px;opacity:.82;margin-bottom:6px}.m48-node strong{font-size:15px;line-height:1.45}.m48-arrow{align-self:center;font-size:20px;color:#ffc46a!important}</style>'
            '<div class="m48-title">內部動作有沒有真的落到最後一句？ · M48</div>'
            '<div class="m48-sub">只把既有物件、操作與停止點對齊成自然日文；不能補任務內容，也不能取代 M46 的有用性審核。</div>'
            f'<div class="m48-nodes">{nodes}</div></section>')
    anchor = '<section class="m47-flow" aria-label="M47 crosslingual help routing">'
    return html.replace(anchor, card + anchor, 1) if anchor in html else card + html


def install_m48_crosslingual_action_realization():
    global _INSTALLED, _PREVIOUS_STRUCTURAL, _PREVIOUS_INSPECT, _PREVIOUS_DIAGNOSTIC, _PREVIOUS_MATERIALIZE
    if _INSTALLED:
        return False
    _PREVIOUS_STRUCTURAL = m46.structural_plan_violations
    _PREVIOUS_INSPECT = m46.inspect_goal_progress
    _PREVIOUS_DIAGNOSTIC = m46._diagnostic
    _PREVIOUS_MATERIALIZE = action45.materialize_trace_m45
    m46.structural_plan_violations = structural_plan_violations_m48
    m46.inspect_goal_progress = inspect_goal_progress_m48
    m46._diagnostic = diagnostic_m48
    action45.materialize_trace_m45 = materialize_trace_m48
    _INSTALLED = True
    return True
