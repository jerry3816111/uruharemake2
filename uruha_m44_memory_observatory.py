"""Actual action/next-outcome card. No invented sample paths or scores."""
from html import escape
from uruha_m43_readable_memory_observatory import render_readable_memory_observatory_m43
from uruha_executed_action_receipt_m44 import LABEL, OUTCOME_LABEL


def render_memory_observatory_m44(result):
    html = render_readable_memory_observatory_m43(result)
    logic = result.get("logic") or {}
    trace, outcome = logic.get(LABEL) or {}, logic.get(OUTCOME_LABEL) or {}
    if not trace:
        return html
    registered = trace.get("status") == "registered_for_next_user_turn"
    results = {"supported": "這次接對了", "contradicted": "被否定，需要修正",
               "uncertain": "仍不知道", "expired": "已過期，不硬套"}
    values = [("過去的約定", "找到已確認來源" if registered else "本輪沒有新增依據"),
              ("最後的行動", "說出口且檢查通過" if registered else "保留原流程"),
              ("下一輪", "已留下可驗證紀錄" if registered else "不捏造新紀錄"),
              ("上一份紀錄的後果", results.get(outcome.get("outcome"), "還沒有結果"))]
    nodes = '<span class="m44-arrow" aria-hidden="true">→</span>'.join(
        f'<div class="m44-node"><div>{escape(label)}</div><strong>{escape(value)}</strong></div>'
        for label, value in values)
    card = ('<section class="m44-flow" aria-label="M44 actual action and next outcome">'
            '<style>.m44-flow{padding:16px;margin:12px 0;border:1px solid #468690;border-radius:14px;background:#132d3b;grid-column:1/-1;}'
            '.m44-flow *{color:#dcf5f5!important}.m44-title{font-size:16px;font-weight:700;margin-bottom:10px}'
            '.m44-nodes{display:flex;gap:10px;align-items:center;flex-wrap:wrap}.m44-node{flex:1;min-width:165px;padding:12px;border:1px solid #68a4af;border-radius:10px;background:#173545}'
            '.m44-node div{font-size:13px}.m44-node strong{font-size:16px;color:#a9fce1!important}.m44-arrow{font-size:20px}.m44-note{font-size:12px;line-height:1.7;margin-top:10px}</style>'
            '<div class="m44-title">做了什麼，要能接住後來的反應 · M44</div>'
            f'<div class="m44-nodes">{nodes}</div>'
            '<div class="m44-note">紀錄建立 ≠ 使用者認可。下一輪仍由實際反應判斷支持、否定或未知；不把推測寫成心理事實。'
            f'<br>本輪：{escape(str(trace.get("reason") or "unknown"))}</div></section>')
    anchor = '<section class="brain-comparison" aria-label="M43 confirmed feedback flow">'
    if anchor in html:
        return html.replace(anchor, card + anchor, 1)
    return html.replace('<div class="memory-observatory-head">', card + '<div class="memory-observatory-head">', 1)
