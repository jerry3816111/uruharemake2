"""M40 presentation overlay; inference remains in research/debug, not reply."""
from html import escape
from uruha_m39_memory_observatory import render_memory_observatory_m39


def _trace(result):
    runtime = result.get("runtime_trace") or result.get("cognition_trace", {}).get("runtime_trace") or {}
    return runtime.get("lexical_boundary_route_m40") or (result.get("logic") or {}).get("lexical_boundary_route_m40") or {}


def render_memory_observatory_m40(result):
    html = render_memory_observatory_m39(result)
    trace = _trace(result or {})
    if not trace:
        return html
    old = escape(str((trace.get("baseline_boundary_plan") or {}).get("intent") or "no boundary"))
    new = escape(str((trace.get("guarded_boundary_plan") or {}).get("intent") or "no boundary"))
    route = escape(str(trace.get("selected_task_shape") or "pending"))
    rejected = int(trace.get("rejected_unbounded_cue_count") or 0)
    card = (
        '<div class="brain-comparison" aria-label="M40 lexical boundary route">'
        '<div class="brain-comparison-card is-uruha">'
        '<div class="brain-comparison-label">詞彙證據 → 路由 · M40</div>'
        f'<div class="brain-comparison-flow">原判定 {old} → 詞邊界稽核 → {new} → {route}</div>'
        f'<div class="brain-comparison-note">排除 {rejected} 個跨詞／詞內誤撞。既有規則與詞表相同；沒有認同白名單，沒有關閉安全。</div>'
        '</div><div class="brain-comparison-card">'
        '<div class="brain-comparison-label">為何這會影響「被理解」</div>'
        '<div class="brain-comparison-flow">正常認同不該先被轉成威脅</div>'
        '<div class="brain-comparison-note">修正在訊號進入情緒評估之前，後續記憶支持、策略、日文表面仍走原流程。這只證明詞彙邊界修正，不代表全面理解或全面安全。</div>'
        '</div></div>'
    )
    marker = '<div class="brain-comparison" aria-label="M39 semantic persona surface verifier">'
    if marker not in html:
        marker = '<div class="memory-observatory-head">'
    return html.replace(marker, card + marker, 1)
