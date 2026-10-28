"""M52: align M51 candidate operation fields with one casual Japanese surface.

This overlay may shorten an action object only to text already present in both
the generated object and generated instruction, and may inflect specification-
style sentence endings without changing the goal, mechanism, effect, or stop
condition. M46 remains the delivery authority.
"""
from copy import deepcopy
from html import escape
import re

import uruha_actionable_help_delivery_m45 as action45
import uruha_state_changing_candidates_m51 as m51


LABEL = "candidate_realization_m52"
SCHEMA = "uruha_candidate_realization_m52"
_INSTALLED = False
_PREVIOUS_SELECT = m51.select_candidate_batch
_PREVIOUS_MATERIALIZE = action45.materialize_trace_m45

_GENERIC_OBJECTS = {"こと", "それ", "もの", "やつ", "作業", "方法", "問題", "一つ", "一個"}
_JAPANESE_RUN = re.compile(r"[一-龯々ぁ-ヿー]+")


def _visible_object_substring(original_object, instruction):
    """Return a bounded suffix at a visible object marker, never new text."""
    if not isinstance(original_object, str) or not isinstance(instruction, str):
        return None
    if original_object and original_object in instruction:
        return original_object
    options = []
    for marker in re.finditer("を", instruction):
        run = re.search(r"([一-龯々ぁ-ヿー]+)$", instruction[:marker.start()])
        if not run:
            continue
        phrase = run.group(1)
        for width in range(2, min(len(phrase), 24) + 1):
            suffix = phrase[-width:]
            if (suffix in original_object and suffix not in _GENERIC_OBJECTS
                    and _JAPANESE_RUN.fullmatch(suffix)):
                options.append(suffix)
    if not options:
        return None
    # A longer shared suffix carries more of the already generated target, but
    # it must stay a compact noun phrase rather than recreating a whole clause.
    return max(options, key=lambda value: (len(value), value))


def _casualize_instruction(instruction):
    """Inflect only existing clause endings; do not invent an operation."""
    if not isinstance(instruction, str) or not instruction.strip():
        return instruction
    parts = [part.strip() for part in re.split(r"。+", instruction.strip()) if part.strip()]
    changed = False
    realized = []
    for index, part in enumerate(parts):
        before = part
        is_last = index == len(parts) - 1
        if is_last and re.search(r"停止する$", part):
            part = re.sub(r"停止する$", "そこで止めよ", part)
            part = re.sub(r"(?:たら|時に)そこで", lambda m: m.group(0)[:-3] + "、そこで", part)
        elif is_last and re.search(r"止める$", part):
            part = re.sub(r"止める$", "止めよ", part)
        elif not re.search(r"(?:みよ|しよ|止めよ|やって|書いて|分けて)$", part):
            if re.search(r"させる$", part):
                part = re.sub(r"させる$", "させてみよ", part)
            elif re.search(r"する$", part):
                part = re.sub(r"する$", "してみよ", part)
            elif re.search(r"[けべめれせてねでげじ]る$", part):
                part = part[:-1] + "てみよ"
        changed = changed or part != before
        realized.append(part)
    candidate = "。".join(realized) + "。"
    return candidate if changed else instruction


def _surface_existing_stop(stop):
    """Make the already generated stopping condition explicit, adding no condition."""
    if not isinstance(stop, str) or not stop.strip():
        return None
    text = _casualize_instruction(stop.strip().rstrip("。.!！"))
    text = str(text or "").strip().rstrip("。.!！")
    if not text:
        return None
    if re.search(r"(?:止めよ|停止|止める|終わ)", text):
        return text + "。"
    return text + "、そこで止めよ。"


def realize_candidate_m52(candidate):
    row = deepcopy(candidate) if isinstance(candidate, dict) else {}
    original = deepcopy(row)
    original_object = row.get("object")
    instruction = row.get("instruction")
    trace = {
        "schema": SCHEMA,
        "status": "not_needed",
        "object_alignment": "already_visible" if isinstance(original_object, str) and original_object in str(instruction or "") else "missing",
        "object_changed": False,
        "instruction_changed": False,
        "semantic_fields_unchanged": True,
        "original_object_digest": action45.digest(str(original_object or "")),
        "original_instruction_digest": action45.digest(str(instruction or "")),
        "raw_candidate_text_persisted": False,
        "long_term_memory_write": False,
        "claim_boundary": "shared-substring object and clause-ending realization only; M46 remains authoritative",
    }
    if not isinstance(candidate, dict) or not isinstance(instruction, str):
        trace.update(status="blocked", reason="invalid_candidate")
        return row, trace

    if not isinstance(original_object, str) or original_object not in instruction:
        visible = _visible_object_substring(original_object, instruction)
        if not visible:
            trace.update(status="blocked", reason="no_shared_visible_object")
            return row, trace
        row["object"] = visible
        trace.update(object_alignment="shared_visible_substring", object_changed=True)

    casual = _casualize_instruction(instruction)
    stop_surface_added = False
    if not re.search(r"(?:止めよ|停止|止める|終わ)", casual):
        surfaced_stop = _surface_existing_stop(row.get("stop"))
        if surfaced_stop:
            casual = casual.rstrip() + surfaced_stop
            stop_surface_added = True
    row["instruction"] = casual
    trace["instruction_changed"] = casual != instruction
    trace["status"] = "realized" if trace["object_changed"] or trace["instruction_changed"] else "not_needed"
    trace["realized_object_digest"] = action45.digest(str(row.get("object") or ""))
    trace["realized_instruction_digest"] = action45.digest(str(casual or ""))
    trace["object_visible_after"] = bool(row.get("object") and row["object"] in casual)
    trace["stop_surface_added"] = stop_surface_added
    trace["stop_visible_after"] = bool(re.search(r"(?:止めよ|停止|止める|終わ)", casual))
    trace["semantic_fields_unchanged"] = all(
        row.get(key) == original.get(key) for key in ("mechanism", "effect", "stop")
    )
    return row, trace


def select_candidate_batch_m52(batch, sources):
    prepared = deepcopy(batch) if isinstance(batch, dict) else {}
    original_parent = {key: deepcopy(prepared.get(key)) for key in ("sid", "span", "goal", "unknown")}
    realized_items, rows = [], []
    for index, item in enumerate(prepared.get("items") or []):
        realized, trace = realize_candidate_m52(item)
        realized_items.append(realized)
        rows.append({
            "index": index,
            "status": trace.get("status"),
            "object_alignment": trace.get("object_alignment"),
            "object_changed": trace.get("object_changed"),
            "instruction_changed": trace.get("instruction_changed"),
            "semantic_fields_unchanged": trace.get("semantic_fields_unchanged"),
            "object_visible_after": trace.get("object_visible_after"),
            "stop_surface_added": trace.get("stop_surface_added"),
            "stop_visible_after": trace.get("stop_visible_after"),
            "original_object_digest": trace.get("original_object_digest"),
            "realized_object_digest": trace.get("realized_object_digest"),
            "original_instruction_digest": trace.get("original_instruction_digest"),
            "realized_instruction_digest": trace.get("realized_instruction_digest"),
            "reason": trace.get("reason"),
        })
    prepared["items"] = realized_items
    plan, state = _PREVIOUS_SELECT(prepared, sources)
    parent_unchanged = all(prepared.get(key) == value for key, value in original_parent.items())
    state[LABEL] = {
        "schema": SCHEMA,
        "status": "realized" if any(row["status"] == "realized" for row in rows) else (
            "blocked" if any(row["status"] == "blocked" for row in rows) else "not_needed"),
        "candidate_count": len(rows),
        "realized_count": sum(row["status"] == "realized" for row in rows),
        "blocked_count": sum(row["status"] == "blocked" for row in rows),
        "object_repair_count": sum(row["object_changed"] is True for row in rows),
        "surface_repair_count": sum(row["instruction_changed"] is True for row in rows),
        "stop_surface_add_count": sum(row["stop_surface_added"] is True for row in rows),
        "source_goal_unknown_unchanged": parent_unchanged,
        "semantic_fields_unchanged": parent_unchanged and all(row["semantic_fields_unchanged"] for row in rows),
        "candidates": rows,
        "added_model_calls": 0,
        "raw_candidate_text_persisted": False,
        "long_term_memory_write": False,
        "claim_boundary": "candidate field/surface realization only; usefulness and delivery remain M46 decisions",
    }
    return plan, state


def _extract_state(result):
    logic = result.get("logic") or {}
    state = logic.get(m51.LABEL)
    if not isinstance(state, dict):
        state = ((logic.get(action45.LABEL) or {}).get(m51.LABEL) or {})
    nested = state.get(LABEL) if isinstance(state, dict) else None
    return deepcopy(nested) if isinstance(nested, dict) else None


def materialize_trace_m52(result, feedback=None):
    _PREVIOUS_MATERIALIZE(result, feedback)
    from uruha_trace_history_sync_m41_1 import sync_current_history_m41_1
    state = _extract_state(result)
    if not state:
        return
    logic = result.setdefault("logic", {}); logic[LABEL] = deepcopy(state)
    current = result.setdefault("runtime_trace", {}); current[LABEL] = deepcopy(state)
    rows = [row for row in current.get("blackboard") or [] if row.get("label") != LABEL]
    index = next((i for i, row in enumerate(rows) if row.get("label") in {m51.LABEL, "goal_progress_delivery_m46", "utterance"}), len(rows))
    rows.insert(index, {"label": LABEL, "stage": "realize", "payload": deepcopy(state), "salience": 1.0})
    current["blackboard"] = rows; sync_current_history_m41_1(result)


def render_m52(result):
    html = m51.render_m51(result)
    state = (result.get("logic") or {}).get(LABEL)
    if not isinstance(state, dict):
        state = _extract_state(result)
    if not isinstance(state, dict):
        return html
    values = (
        ("候選", state.get("candidate_count", 0)),
        ("物件逐字對齊", state.get("object_repair_count", 0)),
        ("口語句尾對齊", state.get("surface_repair_count", 0)),
        ("停止條件說出", state.get("stop_surface_add_count", 0)),
        ("被阻擋", state.get("blocked_count", 0)),
        ("goal/effect/stop", "未改" if state.get("semantic_fields_unchanged") else "不成立"),
        ("新增模型呼叫", state.get("added_model_calls", 0)),
    )
    nodes = '<span class="m52-arrow" aria-hidden="true">→</span>'.join(
        f'<div class="m52-node"><span>{escape(str(title))}</span><strong>{escape(str(value))}</strong></div>'
        for title, value in values)
    card = ('<section class="m52-flow" aria-label="M52 candidate realization"><style>'
            '.m52-flow{grid-column:1/-1;background:linear-gradient(135deg,#183a35,#23493f);border:2px solid #63e6bd;border-radius:16px;padding:16px;margin:12px 0;color:#edfff9}'
            '.m52-flow *{color:#edfff9!important}.m52-title{font-size:19px;font-weight:750}.m52-sub{font-size:13px;line-height:1.6;margin-top:4px}.m52-nodes{display:flex;align-items:stretch;gap:7px;overflow-x:auto;margin-top:13px;padding-bottom:5px}'
            '.m52-node{min-width:155px;flex:1;background:#2d5d50;padding:12px;border-radius:10px}.m52-node span{display:block;font-size:12px;opacity:.82;margin-bottom:6px}.m52-node strong{font-size:15px}.m52-arrow{align-self:center;font-size:20px;color:#63e6bd!important}</style>'
            '<div class="m52-title">同一候選的操作欄位有沒有真的說成自然日文？ · M52</div>'
            '<div class="m52-sub">只能縮成候選內已共同出現的物件，並調整既有句尾；goal、effect、stop 不准改，M46 仍決定能不能交付。</div>'
            f'<div class="m52-nodes">{nodes}</div></section>')
    anchor = '<section class="m51-flow" aria-label="M51 state changing candidates">'
    return html.replace(anchor, card + anchor, 1) if anchor in html else card + html


def install_m52_candidate_realization():
    global _INSTALLED, _PREVIOUS_SELECT, _PREVIOUS_MATERIALIZE
    if _INSTALLED:
        return False
    _PREVIOUS_SELECT = m51.select_candidate_batch
    _PREVIOUS_MATERIALIZE = action45.materialize_trace_m45
    m51.select_candidate_batch = select_candidate_batch_m52
    action45.materialize_trace_m45 = materialize_trace_m52
    _INSTALLED = True
    return True
