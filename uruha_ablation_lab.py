"""Read-only graphical M7/M7.1 ablation and probability intervention laboratory."""

from __future__ import annotations

from html import escape
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
M7_PATH = ROOT / "analysis/m7_ablation_intervention_diagnostic_first_result.json"
M71_PATH = ROOT / "analysis/m7_1_component_coverage_remediation_result.json"
DEFAULT_ABLATION_COMPONENT = "temporal_dynamics"
COMPONENT_LABELS = {
    "memory": "記憶 · memory",
    "preference": "偏好 · preference",
    "habit": "習慣 · habit",
    "emotion": "情緒 · emotion",
    "personality": "人格 · personality",
    "relationship": "關係 · relationship",
    "goal": "目標 · goal",
    "temporal_dynamics": "時間動態 · temporal",
    "explicit_state_transition": "顯式狀態 · state",
    "llm_semantic_interpretation": "語意解讀 · semantic",
}

ABLATION_LAB_CSS = r"""
.ab-lab{--cyan:#22d3ee;--green:#34d399;--amber:#fbbf24;--red:#fb7185;overflow:hidden;border:1px solid rgba(34,211,238,.25);border-radius:24px;color:#e2e8f0;background:radial-gradient(circle at 8% 0%,rgba(34,211,238,.15),transparent 34%),radial-gradient(circle at 95% 2%,rgba(251,113,133,.12),transparent 30%),#050914;box-shadow:0 30px 90px rgba(2,6,23,.5)}.ab-lab *{box-sizing:border-box}.ab-hero{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:20px;align-items:center;padding:25px 28px 20px;border-bottom:1px solid rgba(148,163,184,.13)}.ab-kicker{color:#67e8f9;font-size:10px;font-weight:900;letter-spacing:.16em}.ab-title{margin:6px 0 0;color:#f8fafc;font-size:clamp(23px,3vw,38px);line-height:1.08}.ab-sub{max-width:930px;margin:9px 0 0;color:#94a3b8;font-size:11px;line-height:1.55}.ab-stamps{display:grid;gap:7px;min-width:250px}.ab-stamp{border:1px solid rgba(52,211,153,.35);border-radius:13px;padding:10px 13px;background:rgba(6,78,59,.18);text-align:right}.ab-stamp.warn{border-color:rgba(251,191,36,.36);background:rgba(113,63,18,.17)}.ab-stamp b{display:block;color:#a7f3d0;font-size:13px}.ab-stamp.warn b{color:#fde68a}.ab-stamp span{display:block;margin-top:3px;color:#64748b;font-size:8px}.ab-body{padding:20px 24px 26px}.ab-flow{display:grid;grid-template-columns:1fr 26px 1fr 26px 1fr 26px 1fr;gap:6px;align-items:center}.ab-node{min-height:102px;border:1px solid rgba(34,211,238,.18);border-radius:13px;padding:11px;background:rgba(8,47,73,.14)}.ab-node b{display:block;color:#67e8f9;font-size:8px}.ab-node strong{display:block;margin-top:7px;color:#f8fafc;font-size:12px;line-height:1.35}.ab-node small{display:block;margin-top:5px;color:#64748b;font-size:7px;line-height:1.4}.ab-arrow{height:2px;background:linear-gradient(90deg,rgba(34,211,238,.12),rgba(52,211,153,.85));position:relative}.ab-arrow:after{content:"";position:absolute;right:-1px;top:-3px;border-left:6px solid #34d399;border-top:4px solid transparent;border-bottom:4px solid transparent}.ab-label{margin:17px 3px 9px;color:#64748b;font-size:9px;font-weight:850;letter-spacing:.12em}.ab-grid{display:grid;grid-template-columns:1.3fr .9fr;gap:9px}.ab-panel{border:1px solid rgba(148,163,184,.15);border-radius:14px;padding:12px;background:rgba(15,23,42,.66)}.ab-row{display:grid;grid-template-columns:160px 1fr 60px;gap:8px;align-items:center;margin-top:7px}.ab-row label{color:#cbd5e1;font-size:8px}.ab-track{height:9px;border-radius:99px;background:#1e293b;position:relative;overflow:hidden}.ab-track:after{content:"";position:absolute;left:50%;top:0;width:1px;height:100%;background:#64748b}.ab-fill-pos,.ab-fill-neg{position:absolute;top:1px;height:7px;border-radius:99px}.ab-fill-pos{left:50%;background:#34d399}.ab-fill-neg{right:50%;background:#fb7185}.ab-row em{font-size:8px;font-style:normal;text-align:right}.ab-row em.pos{color:#86efac}.ab-row em.neg{color:#fda4af}.ab-focus{border-top:3px solid var(--tone);border-radius:12px;padding:12px;background:#08101f}.ab-focus b{color:var(--tone);font-size:10px}.ab-focus strong{display:block;margin-top:7px;color:#f8fafc;font-size:21px}.ab-focus span{display:block;margin-top:6px;color:#94a3b8;font-size:8px;line-height:1.5}.ab-intervention{display:grid;grid-template-columns:1fr 48px 1fr;gap:8px;align-items:center}.ab-prob-card{border:1px solid rgba(148,163,184,.15);border-radius:13px;padding:12px;background:#08101f}.ab-prob-card b{display:block;color:#94a3b8;font-size:8px}.ab-prob-card strong{display:block;margin-top:8px;font-size:21px}.ab-prob-card span{display:block;margin-top:5px;color:#64748b;font-size:8px}.ab-inter-arrow{color:#67e8f9;text-align:center;font-size:24px}.ab-coverage{display:grid;grid-template-columns:repeat(10,1fr);gap:5px}.ab-chip{border-radius:9px;padding:8px 5px;text-align:center;background:rgba(6,78,59,.2);border:1px solid rgba(52,211,153,.25)}.ab-chip b{display:block;color:#86efac;font-size:7px}.ab-chip span{display:block;margin-top:3px;color:#64748b;font-size:6px}.ab-insights,.ab-boundary{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:15px}.ab-insights div,.ab-boundary div{border-radius:12px;padding:12px;background:#08101f;border-top:3px solid var(--tone)}.ab-insights b,.ab-boundary b{display:block;color:var(--tone);font-size:9px}.ab-insights span,.ab-boundary span{display:block;margin-top:6px;color:#94a3b8;font-size:8px;line-height:1.48}
@media(max-width:1100px){.ab-flow{grid-template-columns:1fr}.ab-arrow{width:2px;height:18px;margin:auto}.ab-grid{grid-template-columns:1fr}.ab-coverage{grid-template-columns:repeat(5,1fr)}}@media(max-width:700px){.ab-hero{grid-template-columns:1fr;padding:20px 16px}.ab-stamp{text-align:left}.ab-body{padding:16px}.ab-insights,.ab-boundary{grid-template-columns:1fr}.ab-coverage{grid-template-columns:repeat(2,1fr)}.ab-row{grid-template-columns:110px 1fr 52px}}
"""


def _load():
    return (
        json.loads(M7_PATH.read_text(encoding="utf-8")),
        json.loads(M71_PATH.read_text(encoding="utf-8")),
    )


def ablation_component_choices():
    return [(label, component) for component, label in COMPONENT_LABELS.items()]


def _text(value):
    return escape(str(value))


def _ablation_rows(result):
    rows = []
    scale = 1.75
    for component in COMPONENT_LABELS:
        delta = result["ablations"][component]["delta_vs_full"]["negative_log_likelihood"]
        width = min(49.0, abs(delta) / scale * 49.0)
        klass = "pos" if delta >= 0 else "neg"
        rows.append(
            f'<div class="ab-row"><label>{_text(COMPONENT_LABELS[component])}</label><div class="ab-track"><i class="ab-fill-{klass}" style="width:{width:.2f}%"></i></div><em class="{klass}">{delta:+.3f}</em></div>'
        )
    return "".join(rows)


def render_ablation_lab(component=DEFAULT_ABLATION_COMPONENT):
    m7, m71 = _load()
    if component not in COMPONENT_LABELS:
        component = DEFAULT_ABLATION_COMPONENT
    selected = m71["ablations"][component]
    delta = selected["delta_vs_full"]
    tone = "#34d399" if delta["negative_log_likelihood"] > 0 else "#fb7185"
    reading = "移除後變差：此元件在本 fixture 有幫助" if delta["negative_log_likelihood"] > 0 else "移除後變好：此元件目前可能有噪音"
    quiet = m7["quiet_success_diagnostic"]["best_named_intervention"]
    coverage = "".join(
        f'<div class="ab-chip"><b>✓ {_text(name)}</b><span>Δ NLL {m71["ablations"][name]["delta_vs_full"]["negative_log_likelihood"]:+.3f}</span></div>'
        for name in COMPONENT_LABELS
    )
    first_pref = m7["ablations"]["preference"]["status"]
    first_habit = m7["ablations"]["habit"]["status"]
    return (
        '<section class="ab-lab"><header class="ab-hero"><div><div class="ab-kicker">M7 / M7.1 · ABLATION + INTERVENTION</div>'
        '<h1 class="ab-title">不是看它「講得像不像」，而是拔掉一個變數，看行為機率真的怎麼變</h1>'
        '<p class="ab-sub">M7 先原樣重播 frozen M6，再逐一移除 memory、preference、habit、emotion、personality、relationship、goal、temporal dynamics、explicit state、semantic interpretation。M7.1 只修補可識別性，不重寫 M6 成績。</p></div>'
        '<div class="ab-stamps"><div class="ab-stamp"><b>10 / 10 COMPONENTS</b><span>independently ablatable · 28 explicit features</span></div><div class="ab-stamp warn"><b>DIAGNOSTIC · NOT NEW LIFT</b><span>same 8 synthetic holdouts · post-exposure</span></div></div></header>'
        '<div class="ab-body"><div class="ab-flow"><div class="ab-node"><b>① FROZEN PREDICTION</b><strong>M6 probabilities replay exactly</strong><small>same model weights · same T=0.5 · same failures</small></div><i class="ab-arrow"></i>'
        '<div class="ab-node"><b>② REMOVE / SET VARIABLE</b><strong>one component or named value</strong><small>no prompt explanation · actual numeric intervention</small></div><i class="ab-arrow"></i>'
        '<div class="ab-node"><b>③ RECOMPUTE</b><strong>logits → calibrated probability</strong><small>all downstream features propagated when required</small></div><i class="ab-arrow"></i>'
        '<div class="ab-node"><b>④ COMPARE</b><strong>Δ Top-1 · Δ Brier · Δ NLL</strong><small>positive and negative evidence both retained</small></div></div>'
        '<div class="ab-label">REMOVE ONE COMPONENT · Δ NLL RELATIVE TO FULL MODEL (RIGHT = REMOVAL HARMS; LEFT = REMOVAL HELPS)</div>'
        f'<div class="ab-grid"><div class="ab-panel">{_ablation_rows(m71)}</div><div class="ab-focus" style="--tone:{tone}"><b>SELECTED · {_text(COMPONENT_LABELS[component])}</b><strong>Δ NLL {delta["negative_log_likelihood"]:+.3f}</strong><span>{reading}</span><span>Δ Top-1 {delta["top1_accuracy"]:+.1%} · Δ Brier {delta["brier_score"]:+.3f} · Δ ECE {delta["expected_calibration_error"]:+.3f}</span></div></div>'
        f'<div class="ab-label">PRESERVED FAILURE → CONTROLLED PROBABILITY INTERVENTION</div><div class="ab-intervention"><div class="ab-prob-card"><b>quiet_success · ORIGINAL</b><strong style="color:#fda4af">correct p 22.5%</strong><span>wrong selection: direct_rejection · p 77.5%</span></div><div class="ab-inter-arrow">→</div><div class="ab-prob-card"><b>SET event.support = 1.0</b><strong style="color:#86efac">correct p 99.995%</strong><span>selection flips to acknowledge_then_continue · Δ {quiet["delta_actual_probability"]:+.3f}</span></div></div>'
        f'<div class="ab-label">COVERAGE REPAIR · FIRST M7: preference={first_pref}, habit={first_habit} → M7.1: ALL EVALUATED</div><div class="ab-coverage">{coverage}</div>'
        '<div class="ab-insights"><div style="--tone:#34d399"><b>真的有作用</b><span>移除 semantic、explicit state、habit 會明顯惡化 NLL；40/40 個 explanation top-feature intervention 都改變實際機率。</span></div><div style="--tone:#fb7185"><b>真的找到壞器官</b><span>移除 temporal、relationship、preference 反而改善 NLL。這些負結果沒有被重調或藏掉，將成為 M8 新資料驗證對象。</span></div><div style="--tone:#22d3ee"><b>沒有生成漂亮故事</b><span>M7 與 M7.1 都是 0 model calls、0 utterances。圖上每個變化直接來自預測器重算。</span></div></div>'
        '<div class="ab-boundary"><div style="--tone:#86efac"><b>現在完成</b><span>10/10 component ablation、80 named interventions、40 explanation checks、可重播 lock、圖像化正負結果。</span></div><div style="--tone:#fde68a"><b>下一步 M8</b><span>rolling cutoff、多 seeds、新 semantic holdout，檢查 temporal／relationship 的負效果是否重現。</span></div><div style="--tone:#fda4af"><b>仍不能宣稱</b><span>已找出真人腦方程式、變數等於私人心理真值、Uruha 實證成立，或新資料上已泛化。</span></div></div></div></section>'
    )
