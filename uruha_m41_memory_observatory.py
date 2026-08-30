"""Small finalization indicator; real node graph remains the existing renderer."""
from uruha_m40_memory_observatory import render_memory_observatory_m40


def render_memory_observatory_m41(result):
    html = render_memory_observatory_m40(result)
    trace = (result.get("runtime_trace") or {}).get("trace_finalization_m41") or {}
    if not trace:
        return html
    count = int(trace.get("materialized_node_count") or 0)
    card = (
        '<div class="brain-comparison" aria-label="M41 trace delivery integrity">'
        '<div class="brain-comparison-card is-uruha">'
        '<div class="brain-comparison-label">實際結果 → 可展開節點 · M41</div>'
        f'<div class="brain-comparison-flow">當輪來源 → runtime → 回傳快照 → 圖上 {count}/2 個 late-check nodes</div>'
        '<div class="brain-comparison-note">節點內容直接來自本輪 M39/M40；缺來源不造節點。只修傳遞，不改回覆、路由或記憶。</div>'
        '</div></div>'
    )
    marker = '<div class="brain-comparison" aria-label="M40 lexical boundary route">'
    if marker not in html:
        marker = '<div class="memory-observatory-head">'
    return html.replace(marker, card + marker, 1)
