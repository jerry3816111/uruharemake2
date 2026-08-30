"""M53: fail closed on unsupported concrete quoted scaffold labels."""
from contextvars import ContextVar
from copy import deepcopy
from html import escape
import re

import uruha_actionable_help_delivery_m45 as action45
import uruha_goal_progress_delivery_m46 as m46


LABEL = "source_neutral_scaffold_m53"
SCHEMA = "uruha_source_neutral_scaffold_m53"
_INSTALLED = False
_PREVIOUS_STRUCTURAL = m46.structural_plan_violations
_PREVIOUS_INSPECT = m46.inspect_goal_progress
_PREVIOUS_DIAGNOSTIC = m46._diagnostic
_PREVIOUS_MATERIALIZE = action45.materialize_trace_m45
_STATE = ContextVar("m53_source_neutral_scaffold_state", default={})

_QUOTED_LABEL = re.compile(r"[「『“\"]([^」』”\"]{1,40})[」』”\"]")
_NEUTRAL = re.compile(
    r"^(?:見出し|項目|タイトル|空欄|未定|導入|本論|結論|はじめに|まとめ)"
    r"(?:[一二三四五六七八九十0-9０-９]+)?$"
)
_PLAN_FIELDS = (
    "progress_criterion_jp", "action_object_jp", "action_step_jp",
    "expected_state_change_jp", "completion_jp", "instruction_jp",
)


def _remember(plan, state):
    _STATE.set({id(plan): deepcopy(state)})


def _state_for(plan):
    return deepcopy((_STATE.get() or {}).get(id(plan))) if isinstance(plan, dict) else None


def _normalize(value):
    return re.sub(r"\s+", "", str(value or "")).casefold()


def _labels(plan):
    found = []
    for field in _PLAN_FIELDS:
        for match in _QUOTED_LABEL.finditer(str(plan.get(field) or "")):
            label = match.group(1).strip()
            if label and label not in found:
                found.append(label)
    return found


def authorize_named_scaffold_m53(plan, sources):
    labels = _labels(plan) if isinstance(plan, dict) else []
    source_texts = [_normalize(row.get("text")) for row in m46._allowed_sources(sources)]
    rows = []
    for label in labels:
        normalized = _normalize(label)
        exact_source = bool(normalized and any(normalized in text for text in source_texts))
        neutral = bool(_NEUTRAL.fullmatch(label))
        status = "exact_source" if exact_source else "neutral_scaffold_role" if neutral else "unsupported_concrete_label"
        rows.append({"label_digest": action45.digest(label), "status": status,
                     "source_supported": exact_source, "neutral_role": neutral})
    unsupported = [row for row in rows if row["status"] == "unsupported_concrete_label"]
    return {
        "schema": SCHEMA,
        "status": "blocked" if unsupported else "authorized" if rows else "no_named_labels",
        "named_label_count": len(rows),
        "exact_source_count": sum(row["source_supported"] for row in rows),
        "neutral_role_count": sum(row["neutral_role"] and not row["source_supported"] for row in rows),
        "unsupported_count": len(unsupported),
        "labels": rows,
        "plan_changed": False,
        "added_model_calls": 0,
        "raw_candidate_label_persisted": False,
        "long_term_memory_write": False,
        "claim_boundary": "quoted-label source authorization only; not open-domain hallucination detection",
    }


def structural_plan_violations_m53(plan, sources):
    prior = _PREVIOUS_STRUCTURAL(plan, sources)
    existing = _state_for(plan)
    if existing:
        return sorted(set(prior + (["unsupported_concrete_scaffold_label_m53"] if existing.get("unsupported_count") else [])))
    state = authorize_named_scaffold_m53(plan, sources)
    _remember(plan, state)
    if state["unsupported_count"]:
        prior = list(prior) + ["unsupported_concrete_scaffold_label_m53"]
    return sorted(set(prior))


def inspect_goal_progress_m53(plan, sources, review):
    result = _PREVIOUS_INSPECT(plan, sources, review)
    state = _state_for(plan) or authorize_named_scaffold_m53(plan, sources)
    state.update(m46_content_passed=result.get("content_passed") is True,
                 m46_surface_passed=result.get("surface_passed") is True,
                 reviewer_required=True)
    result[LABEL] = state
    return result


def diagnostic_m53(plan, status):
    result = _PREVIOUS_DIAGNOSTIC(plan, status)
    state = _state_for(plan)
    if isinstance(state, dict):
        result[LABEL] = state
    return result


def _extract_state(result):
    logic = result.get("logic") or {}; m46_state = logic.get(m46.LABEL)
    if not isinstance(m46_state, dict):
        m46_state = ((logic.get(action45.LABEL) or {}).get(m46.LABEL) or {})
    state = m46_state.get(LABEL) if isinstance(m46_state, dict) else None
    if not isinstance(state, dict) and isinstance(m46_state, dict):
        state = (m46_state.get("diagnostic") or {}).get(LABEL)
    return deepcopy(state) if isinstance(state, dict) else None


def materialize_trace_m53(result, feedback=None):
    _PREVIOUS_MATERIALIZE(result, feedback)
    from uruha_trace_history_sync_m41_1 import sync_current_history_m41_1
    state = _extract_state(result)
    if not state:
        return
    logic = result.setdefault("logic", {}); logic[LABEL] = deepcopy(state)
    current = result.setdefault("runtime_trace", {}); current[LABEL] = deepcopy(state)
    rows = [row for row in current.get("blackboard") or [] if row.get("label") != LABEL]
    index = next((i for i, row in enumerate(rows) if row.get("label") in {m46.LABEL, action45.LABEL, "utterance"}), len(rows))
    rows.insert(index, {"label": LABEL, "stage": "authorize", "payload": deepcopy(state), "salience": 1.0})
    current["blackboard"] = rows; sync_current_history_m41_1(result)


def render_m53(result):
    from uruha_candidate_realization_m52 import render_m52
    html = render_m52(result); state = (result.get("logic") or {}).get(LABEL)
    if not isinstance(state, dict): state = _extract_state(result)
    if not isinstance(state, dict): return html
    values = (
        ("具名標籤", state.get("named_label_count", 0)),
        ("來源逐字支持", state.get("exact_source_count", 0)),
        ("中性結構角色", state.get("neutral_role_count", 0)),
        ("無來源具體標籤", state.get("unsupported_count", 0)),
        ("原 plan", "未改" if state.get("plan_changed") is False else "已改"),
        ("授權結果", state.get("status") or "未形成"),
    )
    nodes = '<span class="m53-arrow" aria-hidden="true">→</span>'.join(
        f'<div class="m53-node"><span>{escape(str(title))}</span><strong>{escape(str(value))}</strong></div>'
        for title, value in values)
    card = ('<section class="m53-flow" aria-label="M53 source neutral scaffold"><style>'
            '.m53-flow{grid-column:1/-1;background:linear-gradient(135deg,#35243f,#493056);border:2px solid #d8a7ff;border-radius:16px;padding:16px;margin:12px 0;color:#fff7ff}'
            '.m53-flow *{color:#fff7ff!important}.m53-title{font-size:19px;font-weight:750}.m53-sub{font-size:13px;line-height:1.6;margin-top:4px}.m53-nodes{display:flex;align-items:stretch;gap:7px;overflow-x:auto;margin-top:13px;padding-bottom:5px}'
            '.m53-node{min-width:158px;flex:1;background:#62436f;padding:12px;border-radius:10px}.m53-node span{display:block;font-size:12px;opacity:.82;margin-bottom:6px}.m53-node strong{font-size:15px}.m53-arrow{align-self:center;font-size:20px;color:#d8a7ff!important}</style>'
            '<div class="m53-title">這些具名分類是來源給的，還是系統自己編的？ · M53</div>'
            '<div class="m53-sub">來源逐字標籤與中性結構位置可通過；無來源的具體主題直接阻擋。這不是通用幻覺偵測，原 M46 仍需審核。</div>'
            f'<div class="m53-nodes">{nodes}</div></section>')
    anchor = '<section class="m52-flow" aria-label="M52 candidate realization">'
    return html.replace(anchor, card + anchor, 1) if anchor in html else card + html


def install_m53_source_neutral_scaffold():
    global _INSTALLED, _PREVIOUS_STRUCTURAL, _PREVIOUS_INSPECT, _PREVIOUS_DIAGNOSTIC, _PREVIOUS_MATERIALIZE
    if _INSTALLED: return False
    _PREVIOUS_STRUCTURAL = m46.structural_plan_violations; _PREVIOUS_INSPECT = m46.inspect_goal_progress
    _PREVIOUS_DIAGNOSTIC = m46._diagnostic; _PREVIOUS_MATERIALIZE = action45.materialize_trace_m45
    m46.structural_plan_violations = structural_plan_violations_m53
    m46.inspect_goal_progress = inspect_goal_progress_m53; m46._diagnostic = diagnostic_m53
    action45.materialize_trace_m45 = materialize_trace_m53; _INSTALLED = True; return True
