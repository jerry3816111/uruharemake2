"""Show the actual feedback act and its scope, not a fabricated reasoning demo."""
from html import escape
from uruha_m42_memory_observatory import render_memory_observatory_m42
from uruha_supported_feedback_closure_m43 import LABEL_M43


def render_memory_observatory_m43(result):
    html = render_memory_observatory_m42(result)
    trace = (result.get("logic") or {}).get(LABEL_M43) or {}
    if not trace:
        return html
    supported = bool(trace.get("decisive_previous_support"))
    pure = (trace.get("act") or {}).get("status") == "pure_support"
    active = bool(trace.get("authoritative"))
    surface = trace.get("surface") or {}
    steps = [
        ("上一輪", "已有連結的支持" if supported else "尚無明確支持"),
        ("這句話", "只有確認" if pure else "仍有新內容或不確定"),
        ("當輪行動", "短承接，不再猜" if active else "保留正常回覆流程"),
        ("實際輸出", "承接已驗證" if surface.get("status")=="verified_acknowledgement" else "依原流程檢查"),
    ]
    nodes = '<span aria-hidden="true"> → </span>'.join(
        '<div style="border:1px solid #578795;border-radius:12px;padding:10px;min-width:120px">'
        f'<div>{escape(label)}</div><strong>{escape(value)}</strong></div>' for label,value in steps)
    card = (
        '<section class="brain-comparison" aria-label="M43 confirmed feedback flow">'
        '<div class="brain-comparison-card is-uruha">'
        '<div class="brain-comparison-label">確認應改變下一個行動 · M43</div>'
        f'<div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap">{nodes}</div>'
        '<div class="brain-comparison-note">這是本輪實際流程。只收束已確認的回覆期待；新問題、其他未解事項及心理推測不會被一併清除。下方節點可展開原始證據。</div>'
        '</div></section>'
    )
    return html.replace('<div class="memory-observatory-head">',card+'<div class="memory-observatory-head">',1)
