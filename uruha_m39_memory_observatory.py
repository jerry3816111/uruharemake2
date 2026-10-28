"""Presentation overlay for the M39 final-surface integrity node."""

from html import escape

from uruha_m38_memory_observatory import render_memory_observatory_m38 as _render_base


def _find_m39(value):
    if isinstance(value, dict):
        direct = value.get("semantic_persona_surface_verifier_m39")
        if isinstance(direct, dict):
            return direct
        if value.get("schema") == "uruha_semantic_persona_surface_verifier_m39":
            return value
        for item in value.values():
            found = _find_m39(item)
            if found:
                return found
    elif isinstance(value, list):
        for item in reversed(value):
            found = _find_m39(item)
            if found:
                return found
    return {}


def render_memory_observatory_m39(result):
    html = _render_base(result)
    trace = _find_m39(result or {})
    if not trace:
        return html
    status = escape(str(trace.get("status") or "not_applied"))
    action = escape(str(trace.get("action") or "none"))
    policy = escape(str(trace.get("selected_policy_id") or "none"))
    role = escape(", ".join(trace.get("role_violations_before") or []) or "none")
    additions = escape(", ".join(trace.get("unsupported_additions_before") or []) or "none")
    act_before = str(bool(trace.get("policy_act_match_before"))).lower()
    act_after = str(bool(trace.get("policy_act_match_after"))).lower()
    overlay = (
        '<div class="brain-comparison" aria-label="M39 semantic persona surface verifier">'
        '<div class="brain-comparison-card is-uruha">'
        '<div class="brain-comparison-label">SEMANTIC + PERSONA SURFACE-ACT VERIFIER · M39</div>'
        '<div class="brain-comparison-flow">source roles + observable concepts → final Japanese → unsupported-addition audit → selected-policy act audit → bounded repair or accept</div>'
        f'<div class="brain-comparison-note">{status} · action {action} · policy {policy} · role errors {role} · unsupported {additions} · policy act {act_before} → {act_after} · raw write false</div>'
        '</div><div class="brain-comparison-card">'
        '<div class="brain-comparison-label">WHY M39 EXISTS</div>'
        '<div class="brain-comparison-flow">選對回覆策略 ≠ 最後一句真的說對</div>'
        '<div class="brain-comparison-note">M39 不重選心理推測；它只阻止「我／你／第三人稱翻反」、來源沒說的事件被補進去，以及 graph 說陪伴但表面只重述。</div>'
        '</div></div>'
    )
    marker = '<div class="brain-comparison" aria-label="M38 target guarded feedback linkage">'
    return html.replace(marker, overlay + marker, 1)


__all__ = ["render_memory_observatory_m39"]
