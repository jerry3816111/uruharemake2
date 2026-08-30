"""M47: scope explicit cross-lingual requests for practical help.

This opt-in overlay changes one variable only: whether the current Chinese,
English, or Japanese utterance explicitly authorises or forbids a practical
step.  It does not generate the step and does not change M46's usefulness
criteria.  Exact source geometry is kept as offsets and digests, never copied
into the persistent interaction model as a psychological fact.
"""
from copy import deepcopy
import hashlib
from html import escape
import re

import uruha_adaptive_person_model as adaptive
import uruha_actionable_help_delivery_m45 as action45


LABEL = "crosslingual_help_routing_m47"
SCHEMA = "uruha_crosslingual_help_routing_m47"
_INSTALLED = False
_PREVIOUS_CLASSIFIER = adaptive.classify_explicit_desired_response_m25
_PREVIOUS_ASSIGNMENTS = adaptive._explicit_atom_assignments
_PREVIOUS_MATERIALIZE = action45.materialize_trace_m45


POSITIVE_PATTERNS = {
    "zh": (
        r"(?:給|给)我[^。！？!?；;，,\n]{0,18}(?:步驟|步骤|手順|方法|動作|动作)",
        r"(?:告訴|告诉)我[^。！？!?；;，,\n]{0,18}(?:怎麼做|怎么做|先做)",
    ),
    "en": (
        r"\bgive\s+me\s+(?:(?:one|a|the)\s+)?(?:[a-z-]+\s+){0,5}(?:step|method|thing\s+to\s+(?:do|try))\b",
        r"\btell\s+me\s+(?:what|how).{0,28}\bdo\b",
        r"\bwhat\s+should\s+i\s+do\s+first\b",
    ),
    "ja": (
        # M36 covered "一つの手順".  M47 also covers the natural reverse
        # order "手順を一つ" without treating the noun alone as a request.
        r"(?:一つ|ひとつ|一個).{0,12}(?:手順|方法|やること).{0,10}(?:教えて|決めて)",
        r"(?:手順|方法|やること|一歩).{0,8}(?:を)?(?:一つ|ひとつ|一個).{0,8}(?:だけ)?.{0,8}(?:教えて|決めて)",
        r"(?:今|いま).{0,10}(?:できる|やれる).{0,10}(?:手順|方法|こと|一歩).{0,14}(?:教えて|決めて)",
        r"(?:方法|手順).{0,5}(?:を)?教えて",
    ),
}

NEGATIVE_PATTERNS = {
    "zh": (
        r"(?:不要|不用|別|别|不想要|不需要)[^。！？!?；;，,\n]{0,6}(?:(?:給|给|提供|告訴|告诉)[^。！？!?；;，,\n]{0,3})?(?:方法|建議|建议|步驟|步骤|解法)",
        r"(?:方法|建議|建议|步驟|步骤|解法)[^。！？!?；;，,\n]{0,5}(?:不用|不要|不需要)",
    ),
    "en": (
        r"\b(?:do\s+not|don't)\s+(?:give|offer)\s+me\s+(?:advice|a\s+method|a\s+solution|steps?)\b",
        r"\b(?:no|do\s+not\s+want|don't\s+want)\s+(?:advice|methods?|solutions?|steps?)\b",
        r"\bnot\s+asking\s+for\s+(?:advice|a\s+solution|a\s+method|steps?)\b",
    ),
    "ja": (
        r"(?:方法|解決策|手順|アドバイス).{0,5}(?:は|も)?(?:いらない|要らない|ほしくない|欲しくない)",
        r"(?:方法|解決策|手順|アドバイス).{0,5}(?:出さないで|言わないで|やめて)",
        r"解決しようとせず",
    ),
}

METHOD_NOUNS = re.compile(r"(?:方法|建議|建议|アドバイス|method|advice)", re.I)
OTHER_SOLUTION_REQUESTS = re.compile(
    r"(?:有沒有辦法|有没有办法|怎麼辦|怎么办|怎麼停|怎么停|該先做什麼|该先做什么|"
    r"どうすれば|止め方|what\s+can\s+i\s+do|what\s+should\s+i\s+do|how\s+do\s+i\s+stop)",
    re.I,
)


def _digest(text):
    return hashlib.sha256(str(text or "").encode("utf-8")).hexdigest()[:16]


def _matches(text, groups, kind):
    rows = []
    for language, patterns in groups.items():
        for index, pattern in enumerate(patterns, start=1):
            for match in re.finditer(pattern, text, re.I):
                rows.append({
                    "kind": kind,
                    "language": language,
                    "cue_id": f"solve_regulation:{language}:m47:{kind}:{index}",
                    "start": match.start(),
                    "end": match.end(),
                    "length": match.end() - match.start(),
                    "span_digest": _digest(match.group(0)),
                })
    return rows


def _span_ref(text, start, end, role):
    start = max(0, int(start))
    end = min(len(text), max(start, int(end)))
    return {
        "role": role,
        "start": start,
        "end": end,
        "length": end - start,
        "span_digest": _digest(text[start:end]),
        "source": "current_user_input",
    }


def _task_refs(text, route_row, route_evidence=()):
    """Reference task-bearing clauses without duplicating raw dialogue."""
    route_start, route_end = route_row["start"], route_row["end"]
    refs = []
    cursor = 0
    for match in re.finditer(r"[^。！？!?；;\n]+", text):
        start, end = match.start(), match.end()
        overlaps_response_form = any(
            not (end <= row["start"] or start >= row["end"])
            for row in route_evidence
        )
        if (end <= route_start or start >= route_end) and not overlaps_response_form:
            if METHOD_NOUNS.fullmatch(text[start:end].strip()):
                continue
            refs.append(_span_ref(text, start, end, "task_clause"))
        elif start < route_start and text[start:route_start].strip(" ，,、"):
            prefix_end = route_start
            if not any(not (prefix_end <= row["start"] or start >= row["end"])
                       for row in route_evidence):
                refs.append(_span_ref(text, start, prefix_end, "task_clause_prefix"))
        cursor = end
    # A request without independent task evidence intentionally has no task
    # reference; M46 will ask for the missing task instead of inventing one.
    unique = []
    seen = set()
    for row in refs:
        key = (row["start"], row["end"])
        if row["length"] and key not in seen:
            seen.add(key)
            unique.append(row)
    return unique[:8]


def classify_help_route_m47(user_input):
    text = str(user_input or "")
    positive = _matches(text, POSITIVE_PATTERNS, "authorize")
    negative = _matches(text, NEGATIVE_PATTERNS, "forbid")
    # "不要給我方法" contains the positive-looking substring "給我方法".
    # A cue wholly inside an explicit negative scope is not an independent
    # authorization.  Later, non-overlapping replacement requests still win.
    effective_positive = [
        row for row in positive
        if not any(neg["start"] <= row["start"] and row["end"] <= neg["end"]
                   for neg in negative)
    ]
    evidence = sorted(effective_positive + negative,
                      key=lambda row: (row["end"], row["length"]))
    decisive = evidence[-1] if evidence else None
    status = (
        "practical_help_authorized"
        if decisive and decisive["kind"] == "authorize"
        else "practical_help_forbidden"
        if decisive
        else "no_explicit_help_route"
    )
    route_ref = (
        _span_ref(text, decisive["start"], decisive["end"], "desired_response_clause")
        if decisive else None
    )
    task_refs = _task_refs(text, decisive, evidence) if decisive else []
    return {
        "schema": SCHEMA,
        "status": status,
        "detected": bool(decisive),
        "direction": decisive["kind"] if decisive else "none",
        "language": decisive["language"] if decisive else None,
        "cue_id": decisive["cue_id"] if decisive else None,
        "desired_response_span": route_ref,
        "task_spans": task_refs,
        "candidate_evidence": [
            {key: row[key] for key in ("kind", "language", "cue_id", "start", "end", "length", "span_digest")}
            for row in evidence[-8:]
        ],
        "selected_policy": "solve_regulation" if status == "practical_help_authorized" else None,
        "negated_policy": "solve_regulation" if status == "practical_help_forbidden" else None,
        "input_digest": _digest(text),
        "raw_dialogue_persisted": False,
        "long_term_memory_write": False,
        "claim_boundary": "current response-form scope only; not task success or private-state understanding",
    }


def classify_explicit_desired_response_m47(user_input):
    contract = deepcopy(_PREVIOUS_CLASSIFIER(user_input))
    route = classify_help_route_m47(user_input)
    status = route["status"]
    alternatives = [
        row for row in (contract.get("alternatives") or [])
        if row.get("policy_id") != "solve_regulation"
    ]
    negated = set(contract.get("negated_policies") or [])
    protected = bool(contract.get("protected_risk_cue"))

    if status == "practical_help_authorized":
        negated.discard("solve_regulation")
        solve = {
            "policy_id": "solve_regulation",
            "mode": adaptive.POLICY_TO_RESPONSE_MODE_M23["solve_regulation"],
            "cue_id": route["cue_id"],
            "language": route["language"],
        }
        alternatives.insert(0, solve)
        contract.update(
            detected=True,
            status="blocked_by_protected_risk_cue" if protected else "selected",
            selected_policy="solve_regulation",
            selected_mode=solve["mode"],
            authority="protected_risk_route" if protected else "current_explicit_desired_response",
            confidence=0.99,
        )
    elif status == "practical_help_forbidden":
        negated.add("solve_regulation")
        if contract.get("selected_policy") == "solve_regulation":
            replacement = alternatives[0] if alternatives else {}
            contract.update(
                detected=bool(replacement),
                status=("blocked_by_protected_risk_cue" if replacement and protected
                        else "selected" if replacement else "not_detected"),
                selected_policy=replacement.get("policy_id"),
                selected_mode=replacement.get("mode"),
                authority=("protected_risk_route" if replacement and protected
                           else "current_explicit_desired_response" if replacement
                           else "not_applicable"),
                confidence=0.99 if replacement else 0.0,
            )

    contract["alternatives"] = alternatives
    contract["negated_policies"] = sorted(negated)
    contract["matched_languages"] = sorted(set(contract.get("matched_languages") or [])
                                               | ({route["language"]} if route["language"] else set()))
    contract[LABEL] = route
    contract["raw_dialogue_persisted"] = False
    return contract


def explicit_atom_assignments_m47(user_input):
    assignments = deepcopy(_PREVIOUS_ASSIGNMENTS(user_input))
    route = classify_help_route_m47(user_input)
    if route["status"] == "practical_help_authorized":
        assignments["solution_request"] = (0.99, 0.99, "m47_scoped_explicit_request")
        assignments["uncertainty"] = (0.04, 0.98, "m47_scoped_explicit_request")
    elif route["status"] == "practical_help_forbidden":
        assignments["solution_request"] = (0.03, 0.99, "m47_scoped_explicit_negation")
    elif (METHOD_NOUNS.search(str(user_input or ""))
          and not OTHER_SOLUTION_REQUESTS.search(str(user_input or ""))):
        row = assignments.get("solution_request")
        if row and len(row) >= 3 and row[2] == "explicit_user_request":
            assignments.pop("solution_request", None)
    return assignments


def _selected_policy(logic):
    return str(logic.get("desired_response_policy_m18")
               or logic.get("desired_response_policy_m17")
               or logic.get("desired_response_policy_m16") or "")


def materialize_trace_m47(result, feedback=None):
    _PREVIOUS_MATERIALIZE(result, feedback)
    from uruha_trace_history_sync_m41_1 import sync_current_history_m41_1
    logic = result.setdefault("logic", {})
    explicit = logic.get("explicit_desired_response_m25") or {}
    route = deepcopy(explicit.get(LABEL) or {})
    if not route:
        return
    policy = _selected_policy(logic)
    delivery = logic.get(action45.LABEL) or {}
    m46 = delivery.get("goal_progress_delivery_m46") or {}
    should_intervene = route.get("status") == "practical_help_authorized"
    did_intervene = bool(m46 or delivery.get("status") not in {None, "not_applicable"})
    route.update({
        "actual_selected_policy": policy or None,
        "route_consistent": (
            policy == "solve_regulation" if should_intervene
            else policy != "solve_regulation" if route.get("status") == "practical_help_forbidden"
            else True
        ),
        "m46_should_intervene": should_intervene,
        "m46_did_intervene": did_intervene,
        "m46_delivery_status": delivery.get("status") or "not_applicable",
        "long_term_memory_write": False,
    })
    logic[LABEL] = deepcopy(route)
    current = result.setdefault("runtime_trace", {})
    current[LABEL] = deepcopy(route)
    rows = [row for row in current.get("blackboard") or [] if row.get("label") != LABEL]
    index = next((i for i, row in enumerate(rows)
                  if row.get("label") in {"goal_progress_delivery_m46", action45.LABEL, "utterance"}),
                 len(rows))
    rows.insert(index, {"label": LABEL, "stage": "route", "payload": deepcopy(route), "salience": 1.0})
    current["blackboard"] = rows
    sync_current_history_m41_1(result)


def render_m47(result):
    from uruha_goal_progress_delivery_m46 import render_m46
    html = render_m46(result)
    route = (result.get("logic") or {}).get(LABEL)
    if not isinstance(route, dict):
        route = (((result.get("logic") or {}).get("explicit_desired_response_m25") or {}).get(LABEL))
    if not isinstance(route, dict):
        return html
    status_text = {
        "practical_help_authorized": "使用者明確要一個方法",
        "practical_help_forbidden": "使用者明確不要方法",
        "no_explicit_help_route": "沒有明確要求方法",
    }.get(route.get("status"), "尚未判定")
    route_result = "路由一致" if route.get("route_consistent") else "路由錯誤"
    m46_text = ("應進入，且已進入" if route.get("m46_should_intervene") and route.get("m46_did_intervene")
                else "應進入，但未進入" if route.get("m46_should_intervene")
                else "不應進入，且未進入" if not route.get("m46_did_intervene")
                else "不應進入，但誤進入")
    values = (
        ("語言訊號", route.get("language") or "無明確訊號"),
        ("回覆形式範圍", status_text),
        ("任務證據", f'{len(route.get("task_spans") or [])} 個原句位置'),
        ("實際選擇", route.get("actual_selected_policy") or "無"),
        ("M46 行動生成", m46_text),
        ("路由驗收", route_result),
    )
    nodes = '<span class="m47-arrow" aria-hidden="true">→</span>'.join(
        f'<div class="m47-node"><span>{escape(title)}</span><strong>{escape(str(value))}</strong></div>'
        for title, value in values
    )
    card = ('<section class="m47-flow" aria-label="M47 crosslingual help routing">'
            '<style>.m47-flow{grid-column:1/-1;background:linear-gradient(135deg,#16332f,#243f2e);border:2px solid #72e6ab;border-radius:16px;padding:16px;margin:12px 0;color:#effff7}'
            '.m47-flow *{color:#effff7!important}.m47-title{font-size:19px;font-weight:750}.m47-sub{font-size:13px;line-height:1.6;margin-top:4px}.m47-nodes{display:flex;align-items:stretch;gap:7px;overflow-x:auto;margin-top:13px;padding-bottom:5px}'
            '.m47-node{min-width:168px;flex:1;background:#214d3c;padding:12px;border-radius:10px;overflow-wrap:anywhere}.m47-node span{display:block;font-size:12px;opacity:.82;margin-bottom:6px}.m47-node strong{font-size:15px;line-height:1.45}.m47-arrow{align-self:center;font-size:20px;color:#72e6ab!important}</style>'
            '<div class="m47-title">這次是要方法，還是不要方法？ · M47</div>'
            '<div class="m47-sub">先把任務內容和期待的回覆形式分開，再決定是否啟動 M46；這張卡只證明路由，不把回答品質算進來。</div>'
            f'<div class="m47-nodes">{nodes}</div></section>')
    anchor = '<section class="m46-flow" aria-label="M46 goal progress delivery">'
    return html.replace(anchor, card + anchor, 1) if anchor in html else card + html


def install_m47_crosslingual_help_routing():
    global _INSTALLED, _PREVIOUS_CLASSIFIER, _PREVIOUS_ASSIGNMENTS, _PREVIOUS_MATERIALIZE
    if _INSTALLED:
        return False
    _PREVIOUS_CLASSIFIER = adaptive.classify_explicit_desired_response_m25
    _PREVIOUS_ASSIGNMENTS = adaptive._explicit_atom_assignments
    _PREVIOUS_MATERIALIZE = action45.materialize_trace_m45
    adaptive.classify_explicit_desired_response_m25 = classify_explicit_desired_response_m47
    adaptive._explicit_atom_assignments = explicit_atom_assignments_m47
    action45.materialize_trace_m45 = materialize_trace_m47
    _INSTALLED = True
    return True
