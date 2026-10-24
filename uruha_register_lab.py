"""Read-only graphical M10.2 casual-register remediation laboratory."""

from __future__ import annotations

from html import escape
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RESULT_PATH = ROOT / "analysis/m10_2_behavior_preserving_register_first_result.json"
DEFAULT_REGISTER_CASE_ID = "R-EN-04"

REGISTER_LAB_CSS = r"""
.rr-lab{overflow:hidden;border:1px solid rgba(34,211,238,.25);border-radius:24px;color:#e2e8f0;background:radial-gradient(circle at 5% 0%,rgba(34,211,238,.15),transparent 34%),radial-gradient(circle at 96% 3%,rgba(251,113,133,.12),transparent 30%),#050914;box-shadow:0 30px 90px rgba(2,6,23,.5)}.rr-lab *{box-sizing:border-box}.rr-hero{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:20px;align-items:center;padding:25px 28px 20px;border-bottom:1px solid rgba(148,163,184,.13)}.rr-kicker{color:#67e8f9;font-size:10px;font-weight:900;letter-spacing:.16em}.rr-title{margin:6px 0 0;color:#f8fafc;font-size:clamp(23px,3vw,38px);line-height:1.08}.rr-sub{max-width:930px;margin:9px 0 0;color:#94a3b8;font-size:11px;line-height:1.55}.rr-stamps{display:grid;gap:7px;min-width:255px}.rr-stamp{border:1px solid rgba(251,113,133,.35);border-radius:13px;padding:10px 13px;background:rgba(127,29,29,.15);text-align:right}.rr-stamp.ok{border-color:rgba(52,211,153,.34);background:rgba(6,78,59,.17)}.rr-stamp b{display:block;color:#fecdd3;font-size:13px}.rr-stamp.ok b{color:#a7f3d0}.rr-stamp span{display:block;margin-top:3px;color:#64748b;font-size:8px}.rr-body{padding:20px 24px 26px}.rr-metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}.rr-metric{border-radius:13px;padding:12px;background:#08101f;border-top:3px solid var(--tone)}.rr-metric b{color:var(--tone);font-size:8px}.rr-metric strong{display:block;margin-top:7px;color:#f8fafc;font-size:20px}.rr-metric span{display:block;margin-top:4px;color:#64748b;font-size:7px;line-height:1.35}.rr-label{margin:17px 3px 9px;color:#64748b;font-size:9px;font-weight:850;letter-spacing:.12em}.rr-flow{display:grid;grid-template-columns:1fr 34px 1fr 34px 1fr;gap:7px;align-items:stretch}.rr-node{border:1px solid rgba(148,163,184,.15);border-top:3px solid var(--tone);border-radius:14px;padding:13px;background:#08101f}.rr-node b{color:var(--tone);font-size:8px}.rr-node p{min-height:48px;margin:9px 0;color:#f8fafc;font-size:13px;line-height:1.48}.rr-node span{display:block;color:#64748b;font-size:7px;line-height:1.4}.rr-arrow{display:flex;align-items:center;justify-content:center;color:#64748b;font-size:20px}.rr-pair{display:grid;grid-template-columns:1fr 1fr;gap:9px}.rr-card{border:1px solid rgba(148,163,184,.15);border-top:3px solid var(--tone);border-radius:14px;padding:13px;background:rgba(15,23,42,.68)}.rr-card h3{margin:0;color:var(--tone);font-size:10px}.rr-card p{min-height:52px;color:#f8fafc;font-size:13px;line-height:1.5}.rr-tags{display:flex;gap:5px;flex-wrap:wrap}.rr-tag{border:1px solid rgba(148,163,184,.2);border-radius:999px;padding:4px 7px;color:#94a3b8;font-size:6px}.rr-tag.ok{border-color:rgba(52,211,153,.3);color:#86efac}.rr-tag.fail{border-color:rgba(251,113,133,.3);color:#fda4af}.rr-grid{display:grid;grid-template-columns:repeat(6,1fr);gap:5px}.rr-case{border:1px solid rgba(148,163,184,.13);border-radius:9px;padding:8px;background:#08101f;border-top:3px solid var(--tone)}.rr-case b{display:block;color:var(--tone);font-size:7px}.rr-case span{display:block;margin-top:4px;color:#64748b;font-size:6px;line-height:1.35}.rr-bars{display:grid;grid-template-columns:1fr 1fr;gap:9px}.rr-panel{border:1px solid rgba(148,163,184,.15);border-radius:14px;padding:12px;background:rgba(15,23,42,.65)}.rr-bar{display:grid;grid-template-columns:85px 1fr 40px;gap:6px;align-items:center;margin:8px 0}.rr-bar label{color:#94a3b8;font-size:7px}.rr-track{height:7px;border-radius:7px;background:#111827;overflow:hidden}.rr-fill{height:100%;background:var(--tone);border-radius:7px}.rr-bar strong{color:#f8fafc;font-size:8px;text-align:right}.rr-boundary{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-top:15px}.rr-boundary div{border-radius:12px;padding:12px;background:#08101f;border-top:3px solid var(--tone)}.rr-boundary b{display:block;color:var(--tone);font-size:9px}.rr-boundary span{display:block;margin-top:6px;color:#94a3b8;font-size:8px;line-height:1.48}
@media(max-width:1000px){.rr-flow{grid-template-columns:1fr}.rr-arrow{transform:rotate(90deg)}.rr-grid{grid-template-columns:repeat(3,1fr)}.rr-boundary{grid-template-columns:repeat(2,1fr)}}@media(max-width:700px){.rr-hero{grid-template-columns:1fr;padding:20px 16px}.rr-stamp{text-align:left}.rr-body{padding:16px}.rr-metrics,.rr-pair,.rr-bars,.rr-grid,.rr-boundary{grid-template-columns:1fr}}
"""


def _load():
    return json.loads(RESULT_PATH.read_text(encoding="utf-8"))


def _text(value):
    return escape(str(value))


def register_case_choices():
    result = _load()
    rows = {row["case_id"]: row for row in result["rows"] if row["condition"] == "S0_ONE_PASS"}
    return [(f'{case_id} · {row["language"].upper()}', case_id) for case_id, row in sorted(rows.items())]


def _bar(label, value, tone):
    return f'<div class="rr-bar"><label>{label}</label><div class="rr-track"><div class="rr-fill" style="--tone:{tone};width:{max(1,value*100):.2f}%"></div></div><strong>{value:.1%}</strong></div>'


def render_register_lab(case_id=DEFAULT_REGISTER_CASE_ID):
    result = _load()
    ids = {row["case_id"] for row in result["rows"]}
    case_id = case_id if case_id in ids else DEFAULT_REGISTER_CASE_ID
    rows = {row["condition"]: row for row in result["rows"] if row["case_id"] == case_id}
    before, after = rows["S0_ONE_PASS"], rows["S1_REGISTER_REPAIR"]
    passed = sum(result["hypothesis_checks"].values())
    m0, m1 = result["metrics"]["S0_ONE_PASS"], result["metrics"]["S1_REGISTER_REPAIR"]
    before_failures = [name for name, ok in before["visible_contract"].items() if not ok]
    after_failures = [name for name, ok in after["visible_contract"].items() if not ok]
    regression = before["authority_alignment"] and not after["authority_alignment"]
    cards = []
    for pair in result["pairs"]:
        tone = "#fb7185" if pair["aligned_to_misaligned_regression"] else "#34d399" if pair["reply_changed"] else "#64748b"
        label = "AUTHORITY REGRESSION" if pair["aligned_to_misaligned_regression"] else "REPAIRED / PRESERVED" if pair["reply_changed"] else "UNCHANGED"
        cards.append(f'<div class="rr-case" style="--tone:{tone}"><b>{_text(pair["case_id"])}</b><span>{label}</span></div>')
    resources = result["resources"]
    flow = f'''
      <div class="rr-node" style="--tone:#94a3b8"><b>1 · SHARED ONE-PASS</b><p>{_text(before["reply"])}</p><span>behavior={_text(before["authoritative_behavior"])} · decoded={_text(before["decoded_behavior"])}</span></div>
      <div class="rr-arrow">→</div>
      <div class="rr-node" style="--tone:#22d3ee"><b>2 · REGISTER-ONLY REPAIR</b><p>{_text(after["reply"])}</p><span>only casual surface may change · same behavior authority</span></div>
      <div class="rr-arrow">→</div>
      <div class="rr-node" style="--tone:{"#fb7185" if regression else "#34d399"}"><b>3 · DECODE + CONTRACT</b><p>{_text(after["decoded_behavior"])}</p><span>authority {"REGRESSION" if regression else "PRESERVED"} · surface {"PASS" if after["visible_contract_pass"] else "FAIL"}</span></div>'''
    return f'''
    <section class="rr-lab"><header class="rr-hero"><div><div class="rr-kicker">M10.2 · BEHAVIOR-PRESERVING REGISTER REPAIR</div><h1 class="rr-title">日文表面 72% → 100%，但不能用自然度掩蓋 1 個行為回歸</h1><p class="rr-sub">18 個全新中／英／日事件共享同一初稿，再只修 casual register。所有敬體 failure 都消失，但固定 proxy 在 R-JA-06 偵測到 pause-and-reassess → defer-commitment；因此整體 gate 保持失敗，等待真人盲評判斷是行為漂移還是 classifier limitation。</p></div><div class="rr-stamps"><div class="rr-stamp"><b>{passed} / 7 HYPOTHESES</b><span>overall gate · failed</span></div><div class="rr-stamp ok"><b>72 / 72 CALLS</b><span>18 new cases · zero retries</span></div></div></header><div class="rr-body">
      <div class="rr-metrics"><div class="rr-metric" style="--tone:#94a3b8"><b>ONE-PASS SURFACE</b><strong>72.22%</strong><span>13/18 · 5 polite failures</span></div><div class="rr-metric" style="--tone:#22d3ee"><b>REPAIRED SURFACE</b><strong>100%</strong><span>18/18 · +27.78 pp</span></div><div class="rr-metric" style="--tone:#fbbf24"><b>AUTHORITY</b><strong>100% → 94.44%</strong><span>18/18 → 17/18</span></div><div class="rr-metric" style="--tone:#fb7185"><b>REGRESSION</b><strong>1</strong><span>R-JA-06 · proxy disagreement</span></div></div>
      <div class="rr-label">SELECTED CASE · SAME RAW INTENT, BEFORE → SURFACE REPAIR → VERIFY</div><div class="rr-flow">{flow}</div>
      <div class="rr-label">BEFORE / AFTER CONTRACT DETAIL</div><div class="rr-pair"><div class="rr-card" style="--tone:#94a3b8"><h3>S0 · ONE PASS</h3><p>{_text(before["reply"])}</p><div class="rr-tags"><span class="rr-tag {"ok" if before["visible_contract_pass"] else "fail"}">surface {"pass" if before["visible_contract_pass"] else "fail"}</span><span class="rr-tag {"ok" if before["authority_alignment"] else "fail"}">authority {_text(before["decoded_behavior"])}</span>{''.join(f'<span class="rr-tag fail">{_text(x)}</span>' for x in before_failures)}</div></div><div class="rr-card" style="--tone:#22d3ee"><h3>S1 · REGISTER REPAIR</h3><p>{_text(after["reply"])}</p><div class="rr-tags"><span class="rr-tag {"ok" if after["visible_contract_pass"] else "fail"}">surface {"pass" if after["visible_contract_pass"] else "fail"}</span><span class="rr-tag {"ok" if after["authority_alignment"] else "fail"}">authority {_text(after["decoded_behavior"])}</span>{''.join(f'<span class="rr-tag fail">{_text(x)}</span>' for x in after_failures)}</div></div></div>
      <div class="rr-label">ALL 18 SOURCE-DISJOINT CASES</div><div class="rr-grid">{''.join(cards)}</div>
      <div class="rr-label">GAIN AND COST MUST BE READ TOGETHER</div><div class="rr-bars"><div class="rr-panel">{_bar('S0 surface',m0['visible_contract_pass_rate'],'#94a3b8')}{_bar('S1 surface',m1['visible_contract_pass_rate'],'#22d3ee')}</div><div class="rr-panel">{_bar('S0 authority',m0['authority_alignment_rate'],'#34d399')}{_bar('S1 authority',m1['authority_alignment_rate'],'#fbbf24')}</div></div>
      <div class="rr-boundary"><div style="--tone:#34d399"><b>真的改善</b><span>新 18 案 surface 13→18；五個敬體全修，0 surface pass→fail，12 句實際改變。</span></div><div style="--tone:#fb7185"><b>仍未通過</b><span>同模型 proxy 有 1 個 authority regression；不得只報 100% surface。</span></div><div style="--tone:#fbbf24"><b>額外成本</b><span>repair 18 calls · 6,930 tokens · 51.8s。全實驗 {resources['total_model_calls']} calls · {resources['prompt_tokens']+resources['completion_tokens']:,} tokens。</span></div><div style="--tone:#60a5fa"><b>人評邊界</b><span>18 組 blind A/B 已備妥，現在 0 raters；不宣稱自然度偏好或 Uruha fidelity。</span></div></div>
    </div></section>'''
