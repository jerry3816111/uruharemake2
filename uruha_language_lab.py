"""Read-only graphical M10 behavior-to-language laboratory."""

from __future__ import annotations

from html import escape
import json
from pathlib import Path

from longitudinal_human_model.realization import BEHAVIOR_JP, DIRECT, ORACLE, PREDICTED


ROOT = Path(__file__).resolve().parent
RESULT_PATH = ROOT / "analysis/m10_1_behavior_authoritative_language_classifier_alias_result.json"
DEFAULT_LANGUAGE_SAMPLE_ID = "M-E1-01"

CONDITION_META = {
    DIRECT: ("DIRECT LLM", "#94a3b8", "沒有上游行為權限"),
    PREDICTED: ("PREDICTED", "#fbbf24", "服從 M9 預測行為"),
    ORACLE: ("ORACLE", "#34d399", "future-leaking 診斷上限"),
}

LANGUAGE_LAB_CSS = r"""
.lg-lab{overflow:hidden;border:1px solid rgba(251,191,36,.28);border-radius:24px;color:#e2e8f0;background:radial-gradient(circle at 6% 0%,rgba(251,191,36,.15),transparent 34%),radial-gradient(circle at 96% 4%,rgba(52,211,153,.12),transparent 31%),#050914;box-shadow:0 30px 90px rgba(2,6,23,.5)}.lg-lab *{box-sizing:border-box}.lg-hero{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:20px;align-items:center;padding:25px 28px 20px;border-bottom:1px solid rgba(148,163,184,.13)}.lg-kicker{color:#fde68a;font-size:10px;font-weight:900;letter-spacing:.16em}.lg-title{margin:6px 0 0;color:#f8fafc;font-size:clamp(23px,3vw,38px);line-height:1.08}.lg-sub{max-width:950px;margin:9px 0 0;color:#94a3b8;font-size:11px;line-height:1.55}.lg-stamps{display:grid;gap:7px;min-width:250px}.lg-stamp{border:1px solid rgba(251,113,133,.35);border-radius:13px;padding:10px 13px;background:rgba(127,29,29,.15);text-align:right}.lg-stamp.ok{border-color:rgba(52,211,153,.34);background:rgba(6,78,59,.17)}.lg-stamp b{display:block;color:#fecdd3;font-size:13px}.lg-stamp.ok b{color:#a7f3d0}.lg-stamp span{display:block;margin-top:3px;color:#64748b;font-size:8px}.lg-body{padding:20px 24px 26px}.lg-label{margin:17px 3px 9px;color:#64748b;font-size:9px;font-weight:850;letter-spacing:.12em}.lg-metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}.lg-metric{border-radius:13px;padding:12px;background:#08101f;border-top:3px solid var(--tone)}.lg-metric b{color:var(--tone);font-size:8px}.lg-metric strong{display:block;margin-top:7px;color:#f8fafc;font-size:20px}.lg-metric span{display:block;margin-top:4px;color:#64748b;font-size:7px;line-height:1.35}.lg-pipeline{display:grid;grid-template-columns:1.2fr 30px 1fr 30px 1fr 30px 1.2fr 30px 1fr;gap:6px;align-items:stretch}.lg-node{min-width:0;border:1px solid rgba(148,163,184,.15);border-top:3px solid var(--tone);border-radius:13px;padding:11px;background:rgba(15,23,42,.73)}.lg-node b{display:block;color:var(--tone);font-size:8px}.lg-node strong{display:block;margin-top:7px;color:#f8fafc;font-size:11px;line-height:1.42}.lg-node span{display:block;margin-top:6px;color:#64748b;font-size:7px;line-height:1.42}.lg-arrow{display:flex;align-items:center;justify-content:center;color:#64748b;font-size:19px}.lg-probs{display:grid;gap:5px;margin-top:7px}.lg-prob{display:grid;grid-template-columns:90px 1fr 34px;gap:5px;align-items:center}.lg-prob label,.lg-prob em{color:#94a3b8;font-size:6px;font-style:normal}.lg-track{height:5px;border-radius:5px;background:#111827;overflow:hidden}.lg-fill{height:100%;background:var(--tone);border-radius:5px}.lg-output{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}.lg-card{border:1px solid rgba(148,163,184,.15);border-top:3px solid var(--tone);border-radius:14px;padding:12px;background:#08101f}.lg-card-head{display:flex;justify-content:space-between;gap:8px;align-items:center}.lg-card-head b{color:var(--tone);font-size:9px}.lg-badge{padding:3px 6px;border-radius:999px;font-size:6px;background:rgba(15,23,42,.85)}.lg-badge.ok{color:#86efac;border:1px solid rgba(52,211,153,.3)}.lg-badge.fail{color:#fda4af;border:1px solid rgba(251,113,133,.3)}.lg-quote{min-height:62px;margin:10px 0;color:#f8fafc;font-size:12px;line-height:1.52}.lg-meta{display:grid;gap:4px}.lg-meta div{display:grid;grid-template-columns:78px 1fr;gap:5px}.lg-meta label{color:#64748b;font-size:7px}.lg-meta span{color:#94a3b8;font-size:7px}.lg-breakdown{display:grid;grid-template-columns:1.3fr 1fr;gap:9px}.lg-matrix,.lg-surface{border:1px solid rgba(148,163,184,.15);border-radius:14px;padding:12px;background:rgba(15,23,42,.65)}.lg-quad{display:grid;grid-template-columns:repeat(3,1fr);gap:6px}.lg-quad div{border-radius:10px;padding:9px;background:#08101f;border-top:3px solid var(--tone)}.lg-quad b{color:var(--tone);font-size:8px}.lg-quad strong{display:block;color:#f8fafc;font-size:17px;margin-top:4px}.lg-quad span{display:block;color:#64748b;font-size:6px;margin-top:3px;line-height:1.35}.lg-bars{display:grid;gap:8px}.lg-bar{display:grid;grid-template-columns:75px 1fr 42px;gap:6px;align-items:center}.lg-bar label{color:#94a3b8;font-size:7px}.lg-bar strong{color:#f8fafc;font-size:8px;text-align:right}.lg-boundary{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-top:15px}.lg-boundary div{border-radius:12px;padding:12px;background:#08101f;border-top:3px solid var(--tone)}.lg-boundary b{display:block;color:var(--tone);font-size:9px}.lg-boundary span{display:block;margin-top:6px;color:#94a3b8;font-size:8px;line-height:1.48}
@media(max-width:1100px){.lg-pipeline{grid-template-columns:1fr}.lg-arrow{transform:rotate(90deg)}.lg-breakdown{grid-template-columns:1fr}.lg-boundary{grid-template-columns:repeat(2,1fr)}}@media(max-width:760px){.lg-hero{grid-template-columns:1fr;padding:20px 16px}.lg-stamp{text-align:left}.lg-body{padding:16px}.lg-metrics,.lg-output,.lg-quad,.lg-boundary{grid-template-columns:1fr}}
"""


def _load():
    return json.loads(RESULT_PATH.read_text(encoding="utf-8"))


def _text(value):
    return escape(str(value))


def language_case_choices():
    result = _load()
    rows = {row["sample_id"]: row for row in result["rows"] if row["condition"] == DIRECT}
    return [(f'{sample} · {row["cutoff_id"]}', sample) for sample, row in sorted(rows.items())]


def _bar(label, value, tone):
    width = max(1.0, min(100.0, float(value) * 100.0))
    return (
        f'<div class="lg-bar"><label>{_text(label)}</label><div class="lg-track">'
        f'<div class="lg-fill" style="--tone:{tone};width:{width:.2f}%"></div></div>'
        f'<strong>{float(value):.1%}</strong></div>'
    )


def _probabilities(probabilities):
    if not probabilities:
        return '<span>direct baseline · no upstream distribution</span>'
    ranked = sorted(probabilities.items(), key=lambda item: (-item[1], item[0]))[:3]
    return '<div class="lg-probs">' + ''.join(
        f'<div class="lg-prob"><label>{_text(label)}</label><div class="lg-track"><div class="lg-fill" style="--tone:#fbbf24;width:{max(1,value*100):.2f}%"></div></div><em>{value:.1%}</em></div>'
        for label, value in ranked
    ) + '</div>'


def _condition_card(row):
    label, color, description = CONDITION_META[row["condition"]]
    surface = row["visible_contract_pass"]
    outcome = row["outcome_alignment"]
    authority = row["authority_alignment"]
    authority_text = "n/a" if authority is None else ("忠實" if authority else "繞過")
    failures = [name for name, passed in row["visible_contract"].items() if not passed]
    return f'''
    <div class="lg-card" style="--tone:{color}">
      <div class="lg-card-head"><b>{label}</b><span class="lg-badge {"ok" if outcome else "fail"}">{"OUTCOME ✓" if outcome else "OUTCOME ✕"}</span></div>
      <p class="lg-quote">{_text(row["reply"])}</p>
      <div class="lg-meta">
        <div><label>上游權限</label><span>{_text(row["authority_behavior"] or "none")} · {authority_text}</span></div>
        <div><label>句子解碼</label><span>{_text(row["decoded_behavior"])}</span></div>
        <div><label>表面契約</label><span>{"PASS" if surface else "FAIL · " + _text(", ".join(failures))}</span></div>
        <div><label>條件意義</label><span>{description}</span></div>
      </div>
    </div>'''


def render_language_lab(sample_id=DEFAULT_LANGUAGE_SAMPLE_ID):
    result = _load()
    valid_ids = {row["sample_id"] for row in result["rows"]}
    sample_id = sample_id if sample_id in valid_ids else DEFAULT_LANGUAGE_SAMPLE_ID
    case_rows = {
        row["condition"]: row for row in result["rows"] if row["sample_id"] == sample_id
    }
    predicted = case_rows[PREDICTED]
    actual = predicted["actual_observed_behavior"]
    metrics = result["metrics"]
    passed = sum(bool(value) for value in result["hypothesis_checks"].values())

    event_node = f'<div class="lg-node" style="--tone:#60a5fa"><b>1 · OBSERVED EVENT</b><strong>{_text(predicted["event_context"])}</strong><span>{sample_id} · {predicted["cutoff_id"]} · future still sealed at prediction time</span></div>'
    probability_node = f'<div class="lg-node" style="--tone:#fbbf24"><b>2 · M9 DISTRIBUTION</b><strong>{_text(predicted["authority_behavior"])}</strong>{_probabilities(predicted["upstream_probabilities"])}</div>'
    utterance_node = f'<div class="lg-node" style="--tone:#f59e0b"><b>3 · JAPANESE REALIZATION</b><strong>{_text(predicted["reply"])}</strong><span>style cannot override behavior · raw output retained</span></div>'
    decoded_node = f'<div class="lg-node" style="--tone:{"#34d399" if predicted["authority_alignment"] else "#fb7185"}"><b>4 · DECODED ACT</b><strong>{_text(predicted["decoded_behavior"])}</strong><span>{"faithful to authority" if predicted["authority_alignment"] else "LLM bypassed authority"}</span></div>'
    outcome_node = f'<div class="lg-node" style="--tone:{"#34d399" if predicted["outcome_alignment"] else "#fb7185"}"><b>5 · OBSERVED OUTCOME</b><strong>{_text(actual)}</strong><span>{_text(BEHAVIOR_JP[actual])}<br>{"end-to-end match" if predicted["outcome_alignment"] else "faithful language can still be wrong"}</span></div>'

    l1_rows = [row for row in result["rows"] if row["condition"] == PREDICTED]
    correct_faithful = sum(row["authority_behavior"] == row["actual_observed_behavior"] and row["authority_alignment"] is True for row in l1_rows)
    faithful_wrong = sum(row["authority_behavior"] != row["actual_observed_behavior"] and row["authority_alignment"] is True for row in l1_rows)
    lucky_bypass = sum(row["authority_behavior"] != row["actual_observed_behavior"] and row["authority_alignment"] is False and row["outcome_alignment"] for row in l1_rows)

    metric_cards = ''.join([
        '<div class="lg-metric" style="--tone:#94a3b8"><b>DIRECT OUTCOME</b><strong>62.5%</strong><span>10/16 · 沒有行為權限</span></div>',
        '<div class="lg-metric" style="--tone:#fbbf24"><b>PREDICTED AUTHORITY</b><strong>87.5%</strong><span>14/16 · 語言層多數服從</span></div>',
        '<div class="lg-metric" style="--tone:#fb7185"><b>PREDICTED OUTCOME</b><strong>56.25%</strong><span>9/16 · 仍輸給 direct</span></div>',
        '<div class="lg-metric" style="--tone:#34d399"><b>ORACLE CEILING</b><strong>100%</strong><span>16/16 · future-leaking</span></div>',
    ])
    cards = ''.join(_condition_card(case_rows[condition]) for condition in (DIRECT, PREDICTED, ORACLE))
    outcome_bars = ''.join([
        _bar('Direct outcome', metrics[DIRECT]["outcome_alignment_rate"], '#94a3b8'),
        _bar('Pred outcome', metrics[PREDICTED]["outcome_alignment_rate"], '#fb7185'),
        _bar('Oracle outcome', metrics[ORACLE]["outcome_alignment_rate"], '#34d399'),
    ])
    surface_bars = ''.join([
        _bar('Direct surface', metrics[DIRECT]["visible_contract_pass_rate"], '#94a3b8'),
        _bar('Pred surface', metrics[PREDICTED]["visible_contract_pass_rate"], '#fbbf24'),
        _bar('Oracle surface', metrics[ORACLE]["visible_contract_pass_rate"], '#f59e0b'),
    ])
    resources = result["resources"]
    return f'''
    <section class="lg-lab">
      <header class="lg-hero"><div><div class="lg-kicker">M10 / M10.1 · BEHAVIOR → LANGUAGE</div><h1 class="lg-title">語言層會聽命，但預測錯了，它就會忠實地說錯</h1><p class="lg-sub">同一事件、同一模型、完全相同 scored prompt tokens。Direct 讓 LLM 自己決定；Predicted 強制服從 M9；Oracle 用未來正解只量語言上限。這把 predictor error 與 realization error 拆成可觀察的兩條責任鏈。</p></div><div class="lg-stamps"><div class="lg-stamp"><b>{passed} / 9 HYPOTHESES</b><span>overall scientific gate · failed</span></div><div class="lg-stamp ok"><b>144 / 144 CALLS</b><span>token parity · 16/16 exact</span></div></div></header>
      <div class="lg-body"><div class="lg-metrics">{metric_cards}</div>
        <div class="lg-label">SELECTED CASE · EVENT → DISTRIBUTION → UTTERANCE → DECODED ACT → OUTCOME</div>
        <div class="lg-pipeline">{event_node}<div class="lg-arrow">→</div>{probability_node}<div class="lg-arrow">→</div>{utterance_node}<div class="lg-arrow">→</div>{decoded_node}<div class="lg-arrow">→</div>{outcome_node}</div>
        <div class="lg-label">SAME CASE · THREE LANGUAGE CONDITIONS</div><div class="lg-output">{cards}</div>
        <div class="lg-label">WHERE THE ERROR REALLY LIVES</div><div class="lg-breakdown"><div class="lg-matrix"><div class="lg-quad"><div style="--tone:#34d399"><b>預測對＋忠實</b><strong>{correct_faithful}</strong><span>真正端到端成功</span></div><div style="--tone:#fb7185"><b>預測錯＋忠實</b><strong>{faithful_wrong}</strong><span>語言正確執行錯誤決策</span></div><div style="--tone:#60a5fa"><b>預測錯＋繞過</b><strong>{lucky_bypass}</strong><span>偶然修正，不是架構保證</span></div></div><div style="margin-top:12px" class="lg-bars">{outcome_bars}</div></div><div class="lg-surface"><div class="lg-bars">{surface_bars}</div><p style="margin:12px 0 0;color:#fda4af;font-size:8px;line-height:1.5">主要不是混語，而是敬體漂移：Direct 4 次、Predicted 8 次、Oracle 12 次。行為越明確，越容易被寫成工作說明口吻。</p></div></div>
        <div class="lg-boundary"><div style="--tone:#34d399"><b>真的證明</b><span>行為權限 14/16、oracle 16/16；語言層可受控，且錯誤責任可逐 case 追蹤。</span></div><div style="--tone:#fbbf24"><b>成本</b><span>{resources["total_model_calls"]} calls · {resources["prompt_tokens"]+resources["completion_tokens"]:,} tokens · {resources["model_latency_seconds"]:.1f}s · 6 aliases。</span></div><div style="--tone:#60a5fa"><b>盲評待辦</b><span>16 組 A/B/C packet 已分離 key；目前 0 位真人，不能宣稱人類偏好或被理解感。</span></div><div style="--tone:#fb7185"><b>不能宣稱</b><span>Predicted 勝 direct、Uruha fidelity、真人心智、production ready。Oracle 使用未來，永不進 runtime。</span></div></div>
      </div>
    </section>'''
