"""Current-turn evidence card; the expandable graph uses real runtime payloads."""
from html import escape
from uruha_m41_memory_observatory import render_memory_observatory_m41


def render_memory_observatory_m42(result):
    html = render_memory_observatory_m41(result)
    payload = (result.get("logic") or {}).get("cjk_relationship_evidence_m42") or {}
    if not payload:
        return html
    before = (payload.get("candidate_plan") or {}).get("intent") or "一般對話"
    after = (payload.get("authorized_plan") or {}).get("intent") or "一般對話"
    authorization = {"authorized":"找到當輪要求", "not_authorized":"沒有足夠的要求證據",
                     "uncertain":"指向不明，保留原邊界", "not_applicable":"不在本次 CJK 修正範圍"}.get(payload.get("authorization"),"未知")
    card = (
        '<div class="brain-comparison" aria-label="M42 relationship act evidence">'
        '<div class="brain-comparison-card is-uruha">'
        '<div class="brain-comparison-label">字裡有「夫」≠ 要求角色當配偶 · M42</div>'
        f'<div class="brain-comparison-flow">原候選 {escape(before)} → {escape(authorization)} → 實際 {escape(after)}</div>'
        f'<div class="brain-comparison-note">本輪依據：{escape(str(payload.get("reason")))}；只判斷文字中的行動，不把對方私下的想法當事實。</div>'
        '</div></div>'
    )
    marker = '<div class="memory-observatory-head">'
    return html.replace(marker,card+marker,1)
