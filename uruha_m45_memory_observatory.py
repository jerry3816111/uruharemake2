"""Live M45 delivery card, sourced only from this turn's real audit."""
from html import escape
from uruha_m44_memory_observatory import render_memory_observatory_m44
from uruha_actionable_help_delivery_m45 import LABEL


def render_memory_observatory_m45(result):
    html = render_memory_observatory_m44(result)
    trace = (result.get("logic") or {}).get(LABEL) or {}
    if not trace:
        return html
    action = trace.get("action") or {}
    state = {"delivered": "已給出可做的步驟", "awaiting_context": "缺少情境，尚未交付",
             "not_applicable": "本輪不是實用建議"}.get(trace.get("status"), "檢查未通過，沒有冒算完成")
    values = [("問題來源", (trace.get("evidence") or {}).get("source_id") or "尚無足夠依據"),
              ("具體動作", " · ".join(filter(None, [action.get("object_jp"), action.get("verb_jp")])) or "未交付"),
              ("做到哪裡", action.get("completion_jp") or "尚未建立完成條件"), ("最後結果", state)]
    nodes = '<span aria-hidden="true">→</span>'.join(
        f'<div class="m45-node"><span>{escape(title)}</span><strong>{escape(value)}</strong></div>' for title, value in values)
    card = ('<section class="m45-flow" aria-label="M45 actionable help delivery">'
            '<style>.m45-flow{grid-column:1/-1;background:#132d3b;border:2px solid #60c5b7;border-radius:14px;padding:16px;margin:12px 0;color:#e6faf6}'
            '.m45-flow *{color:#e6faf6!important}.m45-title{font-size:18px;font-weight:700}.m45-nodes{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin:12px 0}'
            '.m45-node{flex:1;min-width:170px;background:#173d48;padding:12px;border-radius:9px;overflow-wrap:anywhere}.m45-node span{display:block;font-size:13px;margin-bottom:5px}'
            '.m45-node strong{font-size:16px}.m45-note{font-size:13px;line-height:1.7}</style>'
            '<div class="m45-title">不只說「一起想」，要真的給出下一步 · M45</div>'
            f'<div class="m45-nodes">{nodes}</div>'
            '<div class="m45-note">選了給方法 ≠ 已經給方法。來源、動作和完成條件要一起對上；缺資訊不計成功。'
            f'<br>本輪額外檢查 {trace.get("added_seconds",0)} 秒；本機模型呼叫 {trace.get("model_calls_attempted",0)} 次。模型審核不是人類評分。</div></section>')
    anchor = '<section class="m44-flow" aria-label="M44 actual action and next outcome">'
    return html.replace(anchor, card + anchor, 1) if anchor in html else card + html
