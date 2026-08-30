"""Presentation-only M38 overlay for the frozen progressive observatory."""

from html import escape

from uruha_memory_observatory import render_memory_observatory as _render_base


def _find_m38(value):
    if isinstance(value, dict):
        direct = value.get("target_guarded_feedback_m38")
        if isinstance(direct, dict):
            return direct
        for item in value.values():
            found = _find_m38(item)
            if found:
                return found
    elif isinstance(value, list):
        for item in reversed(value):
            found = _find_m38(item)
            if found:
                return found
    return {}


def render_memory_observatory_m38(result):
    html = _render_base(result)
    trace = _find_m38(result or {})
    if not trace:
        return html
    status = escape(str(trace.get("status") or "not_applied"))
    outcome = escape(str(trace.get("outcome") or "uncertain"))
    previous = escape(str(trace.get("previous_policy_id") or "none"))
    replacement = escape(str(trace.get("replacement_policy_id") or "none"))
    reference = str(bool(trace.get("correction_reference_detected"))).lower()
    linked = str(bool(trace.get("feedback_linked_to_previous_prediction"))).lower()
    candidates = escape(", ".join(trace.get("replacement_candidates") or []) or "none")
    overlay = (
        '<div class="brain-comparison" aria-label="M38 target guarded feedback linkage">'
        '<div class="brain-comparison-card is-uruha">'
        '<div class="brain-comparison-label">TARGET-GUARDED MULTISCRIPT FEEDBACK LINKAGE · M38</div>'
        '<div class="brain-comparison-flow">previous prediction → observable correction reference → unique replacement target → link or fail closed → M34 revision</div>'
        f'<div class="brain-comparison-note">{status} · outcome {outcome} · correction reference {reference} · candidates {candidates} · {previous} → {replacement} · linked {linked} · raw write false</div>'
        '</div><div class="brain-comparison-card">'
        '<div class="brain-comparison-label">NEGATION SAFETY BOUNDARY</div>'
        '<div class="brain-comparison-flow">普通「不／not／ない」 ≠ 對上一輪的更正</div>'
        '<div class="brain-comparison-note">必須同時有上一個 pending prediction、可觀察的更正指涉與唯一 response-policy target；沒有 target 或多個 target 都不改寫舊分支。</div>'
        '</div></div>'
    )
    marker = '<div class="brain-comparison" aria-label="直接生成與 UruhaBrain M34 counterfactual pragmatic branch 差異">'
    return html.replace(marker, overlay + marker, 1)
