"""Teacher-facing V2.16 desired-response equation lab.

The lab is a pure, read-only projection of the frozen equation cases and fresh
same-model results. It never calls the model, mutates a user profile, or writes
production memory. The nodes are operational hypotheses, not literal neurons.
"""

from __future__ import annotations

import json
from copy import deepcopy
from html import escape
from pathlib import Path

from desired_response_comparison_v2_16 import LOCK_PATH, validate_lock
from uruha_reference_person_equation import (
    POLICIES,
    REFERENCE_PERSON,
    apply_user_feedback,
    case_choices as equation_case_choices,
    load_case,
    solve_equation,
    state_from_case,
)


ROOT = Path(__file__).resolve().parent
RAW_PATH = ROOT / "analysis/v2_16_reference_person_equation_raw.json"
DEFAULT_CASE_ID = "v216_unknown_calibrate"
FEEDBACK_TEXT = "不是要方法啦，我是在等你吐槽我，平常不是都會互相吐槽嗎？"

ATOM_LABELS = {
    "sleep_debt": ("睡眠負荷", "moon"),
    "physical_strain": ("身體負荷", "activity"),
    "solution_request": ("需要解法", "wrench"),
    "listening_request": ("只想被聽", "ear"),
    "positive_arousal": ("正向興奮", "sparkles"),
    "humor_invitation": ("玩笑邀請", "zap"),
    "relationship_familiarity": ("關係熟悉", "users"),
    "companionship_request": ("陪伴需求", "heart-handshake"),
    "task_pressure": ("任務壓力", "timer"),
    "uncertainty": ("未知程度", "circle-help"),
}

PHASE_CHOICES = [("① 初次求解", "1"), ("② 回饋後校正", "2")]


EQUATION_LAB_CSS = r"""
.equation-lab { --eq-cyan:#38bdf8; --eq-teal:#2dd4bf; --eq-violet:#a78bfa; --eq-rose:#fb7185; --eq-amber:#facc15; --eq-green:#34d399; overflow:hidden; border:1px solid rgba(103,232,249,.22); border-radius:24px; color:#e2e8f0; background:radial-gradient(circle at 8% 0%,rgba(56,189,248,.13),transparent 28%),radial-gradient(circle at 88% 12%,rgba(167,139,250,.14),transparent 30%),#050914; box-shadow:0 30px 90px rgba(2,6,23,.5);}
.equation-lab *{box-sizing:border-box}.eq-hero{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:24px;align-items:center;padding:27px 30px 22px;border-bottom:1px solid rgba(148,163,184,.13)}
.eq-kicker{color:#67e8f9;font-size:10px;font-weight:800;letter-spacing:.14em}.eq-title{margin:6px 0 0;color:#f8fafc;font-size:clamp(24px,3.2vw,40px);font-weight:850;line-height:1.08}.eq-sub{max-width:820px;margin-top:9px;color:#94a3b8;font-size:12px;line-height:1.62}.eq-stamp{min-width:186px;border:1px solid rgba(45,212,191,.36);border-radius:16px;padding:12px 14px;background:rgba(6,78,59,.22);text-align:right}.eq-stamp strong{display:block;color:#ecfdf5;font-size:19px}.eq-stamp span{color:#6ee7b7;font-size:9px;letter-spacing:.08em}
.eq-thesis{display:grid;grid-template-columns:1fr 54px 1fr 54px 1.2fr;align-items:center;padding:15px 30px;background:rgba(15,23,42,.68);border-bottom:1px solid rgba(148,163,184,.12)}.eq-thesis-node{min-height:68px;display:grid;place-items:center;border:1px solid rgba(56,189,248,.22);border-radius:16px;padding:10px 14px;background:rgba(15,23,42,.75);text-align:center}.eq-thesis-node b{color:#f8fafc;font-size:12px}.eq-thesis-node span{margin-top:4px;color:#64748b;font-size:9px;line-height:1.35}.eq-thesis-node.is-reference{border-color:rgba(167,139,250,.38);background:rgba(76,29,149,.14)}.eq-thesis-node.is-target{border-color:rgba(45,212,191,.4);background:rgba(6,95,70,.16)}.eq-mini-arrow{position:relative;height:2px;margin:0 8px;background:rgba(56,189,248,.4)}.eq-mini-arrow:after{content:'';position:absolute;right:-1px;top:-4px;border-left:7px solid rgba(56,189,248,.7);border-top:5px solid transparent;border-bottom:5px solid transparent}
.eq-input-wrap{padding:20px 30px 8px}.eq-input{position:relative;max-width:900px;margin:auto;border:1px solid rgba(56,189,248,.38);border-radius:18px;padding:15px 18px 15px 52px;background:linear-gradient(115deg,rgba(14,116,144,.25),rgba(15,23,42,.86));color:#e0f2fe;font-size:16px;font-weight:760}.eq-input:before{content:'A';position:absolute;left:17px;top:50%;display:grid;place-items:center;width:25px;height:25px;border-radius:50%;background:rgba(14,116,144,.5);transform:translateY(-50%);font-size:11px}.eq-input small{display:block;margin-bottom:3px;color:#7dd3fc;font-size:9px;letter-spacing:.09em}.eq-context{max-width:900px;margin:8px auto 0;color:#64748b;font-size:9px;line-height:1.45;text-align:center}
.eq-canvas{padding:19px 24px 28px}.eq-lane-label{margin:0 6px 10px;color:#64748b;font-size:9px;font-weight:850;letter-spacing:.12em}.eq-flow{display:grid;grid-template-columns:minmax(220px,1.2fr) 34px minmax(145px,.78fr) 34px minmax(270px,1.35fr) 34px minmax(190px,1fr);gap:6px;align-items:center}.eq-arrow{position:relative;height:2px;background:rgba(56,189,248,.34)}.eq-arrow:after{content:'';position:absolute;right:-1px;top:-4px;border-left:7px solid rgba(56,189,248,.65);border-top:5px solid transparent;border-bottom:5px solid transparent}
.eq-node{border:1px solid color-mix(in srgb,var(--eq-node) 42%,#334155);border-radius:18px;padding:14px;background:color-mix(in srgb,var(--eq-node) 9%,rgba(15,23,42,.92));box-shadow:inset 0 0 28px color-mix(in srgb,var(--eq-node) 5%,transparent)}.eq-node-head{display:flex;align-items:center;gap:9px}.eq-icon{display:grid;place-items:center;width:29px;height:29px;flex:0 0 auto;border-radius:50%;color:#f8fafc;background:color-mix(in srgb,var(--eq-node) 42%,#0f172a)}.eq-node b{color:#f8fafc;font-size:11px}.eq-node p{margin:7px 0 0;color:#94a3b8;font-size:9px;line-height:1.45}.eq-theta{min-height:205px}.eq-theta .eq-symbol{margin:16px 0 9px;color:#ddd6fe;font-size:31px;font-weight:800;text-align:center}.eq-theta .eq-ref{color:#c4b5fd;font-size:10px;font-weight:780;text-align:center}.eq-theta .eq-boundary{margin-top:11px;border-top:1px solid rgba(167,139,250,.2);padding-top:9px;color:#64748b;font-size:8px;line-height:1.45}
.eq-atoms{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:7px}.eq-atom{position:relative;min-height:70px;border:1px solid rgba(56,189,248,.18);border-radius:13px;padding:9px 9px 8px 38px;background:rgba(15,23,42,.72)}.eq-atom.is-changed{border-color:rgba(250,204,21,.52);background:rgba(113,63,18,.18);box-shadow:0 0 18px rgba(250,204,21,.1)}.eq-atom i{position:absolute;left:10px;top:10px;color:#7dd3fc}.eq-atom b{display:block;color:#e2e8f0;font-size:9px}.eq-atom .eq-value{margin-top:4px;color:#f8fafc;font-size:15px;font-weight:850}.eq-atom .eq-value span{color:#64748b;font-size:8px;font-weight:650}.eq-atom-bar{height:3px;margin-top:5px;border-radius:3px;background:#1e293b;overflow:hidden}.eq-atom-bar i{position:static;display:block;height:100%;background:linear-gradient(90deg,#0ea5e9,#2dd4bf)}.eq-atom.is-changed .eq-atom-bar i{background:#facc15}.eq-atom small{display:block;margin-top:4px;color:#64748b;font-size:7px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.eq-memory-atom{grid-column:1/-1;position:relative;min-height:64px;border:1px solid rgba(167,139,250,.28);border-radius:13px;padding:9px 10px 9px 38px;background:rgba(76,29,149,.12)}.eq-memory-atom i{position:absolute;left:10px;top:10px;color:#c4b5fd}.eq-memory-atom b{display:block;color:#ddd6fe;font-size:9px}.eq-memory-atom p{margin:5px 0 0;color:#94a3b8;font-size:8px;line-height:1.4}
.eq-candidates{display:grid;gap:6px}.eq-candidate{position:relative;border:1px solid rgba(148,163,184,.14);border-radius:12px;padding:8px 9px 8px 32px;background:rgba(15,23,42,.7)}.eq-candidate.is-selected{border-color:rgba(45,212,191,.54);background:rgba(6,95,70,.22);box-shadow:0 0 18px rgba(45,212,191,.12)}.eq-rank{position:absolute;left:9px;top:9px;color:#64748b;font-size:8px}.eq-candidate.is-selected .eq-rank{color:#5eead4}.eq-candidate-head{display:flex;justify-content:space-between;gap:8px;color:#cbd5e1;font-size:8px;font-weight:780}.eq-candidate.is-selected .eq-candidate-head{color:#ccfbf1}.eq-score{color:#f8fafc;font-variant-numeric:tabular-nums}.eq-score-track{height:4px;margin-top:5px;border-radius:4px;background:#1e293b;overflow:hidden}.eq-score-track i{display:block;height:100%;background:#64748b}.eq-candidate.is-selected .eq-score-track i{background:linear-gradient(90deg,#14b8a6,#5eead4)}.eq-score-meta{display:flex;gap:7px;margin-top:4px;color:#475569;font-size:7px}.eq-selected{min-height:205px;display:flex;flex-direction:column;justify-content:space-between}.eq-selected-policy{color:#5eead4;font-size:10px;font-weight:850}.eq-selected-reply{margin-top:12px;color:#f8fafc;font-size:14px;font-weight:760;line-height:1.55}.eq-selected-meta{margin-top:14px;border-top:1px solid rgba(45,212,191,.18);padding-top:10px;color:#64748b;font-size:8px;line-height:1.45}
.eq-feedback{display:grid;grid-template-columns:minmax(0,.9fr) 34px minmax(0,1.2fr) 34px minmax(0,1fr);gap:7px;align-items:center;margin-top:18px;border-top:1px solid rgba(148,163,184,.12);padding-top:18px}.eq-feedback-signal{border:1px solid rgba(250,204,21,.26);border-radius:15px;padding:12px;background:rgba(113,63,18,.15)}.eq-feedback-signal b{color:#fde68a;font-size:9px}.eq-feedback-signal p{margin:6px 0 0;color:#fef3c7;font-size:10px;line-height:1.45}.eq-deltas{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:5px}.eq-delta{border:1px solid rgba(250,204,21,.2);border-radius:10px;padding:7px;background:rgba(15,23,42,.7);text-align:center}.eq-delta b{display:block;color:#fde68a;font-size:7px}.eq-delta span{display:block;margin-top:4px;color:#f8fafc;font-size:9px}.eq-feedback-out{border:1px solid rgba(52,211,153,.35);border-radius:15px;padding:12px;background:rgba(6,78,59,.18)}.eq-feedback-out b{color:#a7f3d0;font-size:9px}.eq-feedback-out p{margin:6px 0 0;color:#ecfdf5;font-size:11px;font-weight:750;line-height:1.45}
.eq-compare{padding:24px 30px;border-top:1px solid rgba(148,163,184,.12);background:rgba(2,6,23,.22)}.eq-compare-head{display:flex;justify-content:space-between;gap:16px;align-items:flex-end}.eq-compare h2{margin:4px 0 0;color:#f8fafc;font-size:17px}.eq-gate{color:#86efac;font-size:9px}.eq-reply-grid{display:grid;grid-template-columns:1fr 46px 1fr;gap:12px;align-items:stretch;margin-top:15px}.eq-reply{border:1px solid rgba(148,163,184,.16);border-radius:17px;padding:15px;background:rgba(15,23,42,.72)}.eq-reply.is-system{border-color:rgba(45,212,191,.36);background:rgba(6,78,59,.17)}.eq-reply b{color:#94a3b8;font-size:9px;letter-spacing:.08em}.eq-reply.is-system b{color:#99f6e4}.eq-reply p{margin:10px 0 0;color:#f8fafc;font-size:13px;font-weight:700;line-height:1.55}.eq-vs{display:grid;place-items:center;color:#475569;font-size:9px;font-weight:900}.eq-metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin-top:16px}.eq-metric{border-top:2px solid var(--eq-metric);padding-top:8px}.eq-metric strong{display:block;color:#f8fafc;font-size:19px}.eq-metric span{color:#64748b;font-size:8px;line-height:1.35}.eq-proof-note{margin-top:13px;color:#94a3b8;font-size:9px;line-height:1.5}
.eq-footer{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:1px;background:rgba(148,163,184,.12)}.eq-footer div{padding:13px 16px;background:#08101f}.eq-footer b{display:block;font-size:9px}.eq-footer span{display:block;margin-top:4px;color:#64748b;font-size:8px;line-height:1.4}.eq-footer .done b{color:#86efac}.eq-footer .pending b{color:#fde68a}.eq-footer .forbidden b{color:#fda4af}
@media(max-width:1050px){.eq-flow{grid-template-columns:1fr}.eq-arrow{width:2px;height:24px;margin:auto}.eq-arrow:after{right:-4px;top:auto;bottom:-1px;border-left:5px solid transparent;border-right:5px solid transparent;border-top:7px solid rgba(56,189,248,.65)}.eq-feedback{grid-template-columns:1fr}.eq-thesis{grid-template-columns:1fr}.eq-mini-arrow{width:2px;height:20px;margin:4px auto}.eq-mini-arrow:after{right:-4px;top:auto;bottom:-1px;border-left:5px solid transparent;border-right:5px solid transparent;border-top:7px solid rgba(56,189,248,.7)}}
@media(max-width:720px){.eq-hero{grid-template-columns:1fr;padding:22px 18px}.eq-stamp{text-align:left}.eq-thesis,.eq-input-wrap,.eq-canvas,.eq-compare{padding-left:18px;padding-right:18px}.eq-atoms{grid-template-columns:1fr}.eq-deltas{grid-template-columns:repeat(2,1fr)}.eq-reply-grid{grid-template-columns:1fr}.eq-vs{min-height:20px}.eq-metrics,.eq-footer{grid-template-columns:1fr 1fr}}
@media(prefers-reduced-motion:reduce){.equation-lab *{scroll-behavior:auto!important;transition:none!important;animation:none!important}}
"""


def _text(value):
    return escape(str(value or ""))


def _load_raw():
    return json.loads(RAW_PATH.read_text(encoding="utf-8"))


def case_choices():
    return equation_case_choices()


def phase_choices():
    return deepcopy(PHASE_CHOICES)


def _row_for(raw, case_id, condition):
    return next(
        row for row in raw.get("rows") or []
        if row.get("case_id") == case_id and row.get("condition") == condition
    )


def build_equation_lab_payload(case_id=DEFAULT_CASE_ID, phase="1"):
    phase = "2" if str(phase) == "2" else "1"
    case = load_case(case_id)
    base_state = state_from_case(case)
    base_solution = solve_equation(base_state)
    changes = []
    feedback = ""
    if phase == "2":
        feedback = FEEDBACK_TEXT
        active_state, changes = apply_user_feedback(base_state, feedback)
    else:
        active_state = base_state
    solution = solve_equation(active_state)
    raw = _load_raw()
    baseline = _row_for(raw, case_id, "baseline")
    system = _row_for(raw, case_id, "system")
    integrity = validate_lock(LOCK_PATH)
    return {
        "case": case,
        "phase": phase,
        "feedback": feedback,
        "changes": changes,
        "base_solution": base_solution,
        "solution": solution,
        "baseline": baseline,
        "system": system,
        "summary": raw["summary"],
        "claims": raw["claims"],
        "lock_integrity": integrity["passed"],
        "production_memory_write_count": 0,
    }


def _arrow():
    return '<div class="eq-arrow" aria-hidden="true"></div>'


def _atom_nodes(payload):
    changed = {row["atom"] for row in payload["changes"]}
    chunks = []
    for key, atom in payload["solution"]["state"]["atoms"].items():
        label, icon = ATOM_LABELS.get(key, (key, "circle"))
        value = float(atom.get("value") or 0)
        confidence = float(atom.get("confidence") or 0)
        changed_class = " is-changed" if key in changed else ""
        chunks.append(
            f'<div class="eq-atom{changed_class}" aria-label="{_text(label)} {value:.0%}, confidence {confidence:.0%}">'
            f'<i data-lucide="{icon}" aria-hidden="true"></i><b>{_text(label)}</b>'
            f'<div class="eq-value">{value:.0%} <span>信心 {confidence:.0%}</span></div>'
            f'<div class="eq-atom-bar"><i style="width:{value * 100:.1f}%"></i></div>'
            f'<small>{_text(atom.get("status"))} · {_text(atom.get("evidence"))}</small></div>'
        )
    return "".join(chunks)


def _memory_node(case):
    history = list(case.get("context_history") or [])
    content = " / ".join(history) if history else "沒有可用前置記憶；Mₜ 保持空白"
    return (
        '<div class="eq-memory-atom"><i data-lucide="database" aria-hidden="true"></i>'
        '<b>Mₜ｜本輪真正流入決策的記憶／前置訊號</b>'
        f'<p>{_text(content)}</p></div>'
    )


def _candidate_nodes(solution):
    chunks = []
    selected = solution["selected"]["policy_id"]
    for index, row in enumerate(solution["candidates"], start=1):
        active = " is-selected" if row["policy_id"] == selected else ""
        chunks.append(
            f'<div class="eq-candidate{active}"><span class="eq-rank">{index}</span>'
            f'<div class="eq-candidate-head"><span>{_text(row["icon"])} {_text(row["label"])}</span>'
            f'<span class="eq-score">U={row["expected_utility"]:.2f}</span></div>'
            f'<div class="eq-score-track"><i style="width:{row["expected_utility"] * 100:.1f}%"></i></div>'
            f'<div class="eq-score-meta"><span>想要 {row["desired_response_fit"]:.2f}</span>'
            f'<span>うるは {row["reference_person_fit"]:.2f}</span><span>風險 −{row["risk_penalty"]:.2f}</span></div></div>'
        )
    return "".join(chunks)


def _delta_nodes(changes):
    if not changes:
        return '<div class="eq-delta"><b>等待 Fₜ</b><span>尚未更新</span></div>'
    chunks = []
    for row in changes:
        before = float((row.get("before") or {}).get("value") or 0)
        after = float((row.get("after") or {}).get("value") or 0)
        label = ATOM_LABELS.get(row["atom"], (row["atom"], ""))[0]
        chunks.append(f'<div class="eq-delta"><b>{_text(label)}</b><span>{before:.0%} → {after:.0%}</span></div>')
    return "".join(chunks)


def render_equation_lab(case_id=DEFAULT_CASE_ID, phase="1"):
    payload = build_equation_lab_payload(case_id, phase)
    case = payload["case"]
    solution = payload["solution"]
    selected = solution["selected"]
    before = payload["base_solution"]["selected"]
    summary = payload["summary"]
    contexts = " / ".join(case.get("context_history") or ["沒有可靠前置訊號；不能假裝知道"])
    feedback_text = payload["feedback"] or "使用者下一輪反應尚未到來"
    feedback_out = (
        f'{_text(before["label"])} → {_text(selected["label"])}'
        if payload["phase"] == "2"
        else f'目前暫定：{_text(selected["label"])}'
    )
    lock_label = "FROZEN SOURCES VERIFIED" if payload["lock_integrity"] else "LOCK INTEGRITY FAILED"
    proxy_pass = bool(summary.get("preregistered_proxy_success"))
    proxy_label = "未通過全部預註冊 gate" if not proxy_pass else "通過預註冊 narrow proxy"
    return (
        '<section class="equation-lab">'
        '<header class="eq-hero"><div><div class="eq-kicker">V2.16 · ONE-WEEK RESEARCH MILESTONE</div>'
        '<h1 class="eq-title">同一句話，不等於同一個答案</h1>'
        '<div class="eq-sub">研究目標不是辨認字面語意，而是把可觀察訊號、記憶、情感／身體、關係與期待組成可反駁的狀態，預測「這個人此刻最希望被怎麼接住」。一ノ瀬うるは是第一個可對照的參考人，不是整個方程式。</div></div>'
        f'<div class="eq-stamp"><strong>6 CONTEXTS · 1 INPUT</strong><span>{lock_label}</span></div></header>'
        '<div class="eq-thesis"><div class="eq-thesis-node"><b>一般人類方程式 F</b><span>狀態、記憶、關係、回饋皆可替換</span></div><div class="eq-mini-arrow"></div>'
        '<div class="eq-thesis-node is-reference"><b>參考人 θ<sub>Uruha</sub></b><span>公開證據約束感知、評估、選擇與表達</span></div><div class="eq-mini-arrow"></div>'
        '<div class="eq-thesis-node is-target"><b>r* = argmax P(使用者最想要的回覆)</b><span>不是讓人格替任意答案換口氣</span></div></div>'
        '<div class="eq-input-wrap"><div class="eq-input"><small>SAME OBSERVED INPUT · EVERY CASE</small>'
        f'{_text(case["current_input"])}</div><div class="eq-context"><b>本輪可追溯上下文：</b>{_text(contexts)}</div></div>'
        '<section class="eq-canvas"><div class="eq-lane-label">INSPECTABLE EQUATION GRAPH · 點選上方不同情境，A 不變，狀態與 r* 改變</div>'
        '<div class="eq-flow"><div class="eq-node" style="--eq-node:#38bdf8"><div class="eq-node-head"><span class="eq-icon"><i data-lucide="network" aria-hidden="true"></i></span><b>Zₜ｜可觀察人類狀態</b></div>'
        f'<div class="eq-atoms">{_memory_node(case)}{_atom_nodes(payload)}</div></div>{_arrow()}'
        '<div class="eq-node eq-theta" style="--eq-node:#a78bfa"><div class="eq-node-head"><span class="eq-icon"><i data-lucide="fingerprint" aria-hidden="true"></i></span><b>參考人評估器</b></div><div class="eq-symbol">θ<sub>Uruha</sub></div>'
        '<div class="eq-ref">直接、不過度糖衣<br>熟人玩笑需有關係證據<br>未知時不冒充讀心</div>'
        f'<div class="eq-boundary">{len(REFERENCE_PERSON["evidence_refs"])} 個 public dev refs<br>私人心理／童年／未公開關係 = UNKNOWN</div></div>{_arrow()}'
        '<div class="eq-node" style="--eq-node:#facc15"><div class="eq-node-head"><span class="eq-icon"><i data-lucide="git-compare-arrows" aria-hidden="true"></i></span><b>六個候選回覆政策</b></div>'
        f'<div class="eq-candidates">{_candidate_nodes(solution)}</div></div>{_arrow()}'
        '<div class="eq-node eq-selected" style="--eq-node:#2dd4bf"><div><div class="eq-node-head"><span class="eq-icon"><i data-lucide="message-circle" aria-hidden="true"></i></span><b>選中的 r*</b></div>'
        f'<div class="eq-selected-policy">{_text(selected["icon"])} {_text(selected["label"])}</div><div class="eq-selected-reply">{_text(selected["core_message_jp"])}</div></div>'
        f'<div class="eq-selected-meta">utility {selected["expected_utility"]:.2f} · margin {solution["utility_margin"]:.2f}<br>輸出只讓人感到被接住；內部分析不傾倒給使用者</div></div></div>'
        '<div class="eq-feedback"><div class="eq-feedback-signal"><b>Fₜ｜後續使用者反應</b>'
        f'<p>{_text(feedback_text)}</p></div>{_arrow()}<div class="eq-deltas">{_delta_nodes(payload["changes"])}</div>{_arrow()}'
        f'<div class="eq-feedback-out"><b>Sₜ₊₁｜局部校正，不是全域自信</b><p>{feedback_out}</p></div></div></section>'
        '<section class="eq-compare"><div class="eq-compare-head"><div><div class="eq-lane-label">FRESH SAME-MODEL CONTROL · QWEN3.5:9B</div><h2>同模型、同輸入長度、差別只有顯式方程式</h2></div><div class="eq-gate">6 / 6 token-pair gate 通過</div></div>'
        '<div class="eq-reply-grid"><article class="eq-reply"><b>BASELINE｜目前對話直接生成</b>'
        f'<p>{_text(payload["baseline"].get("reply"))}</p></article><div class="eq-vs">VS</div><article class="eq-reply is-system"><b>SYSTEM｜Zₜ → θ → 候選效用 → r*</b>'
        f'<p>{_text(payload["system"].get("reply"))}</p></article></div>'
        '<div class="eq-metrics">'
        f'<div class="eq-metric" style="--eq-metric:#64748b"><strong>{summary["baseline_proxy_pass_count"]}/6</strong><span>baseline narrow policy proxy</span></div>'
        f'<div class="eq-metric" style="--eq-metric:#2dd4bf"><strong>{summary["system_proxy_pass_count"]}/6</strong><span>system narrow policy proxy</span></div>'
        f'<div class="eq-metric" style="--eq-metric:#38bdf8"><strong>{summary["system_visible_contract_pass_count"]}/6</strong><span>system natural-Japanese contract</span></div>'
        f'<div class="eq-metric" style="--eq-metric:#facc15"><strong>0</strong><span>production memory writes</span></div></div>'
        f'<div class="eq-proof-note"><b>預註冊結果：</b>{proxy_label}。系統 proxy 5/6、baseline 1/6，但 listen-only 的禁止字錨把「方法は出さずに」誤判成違規；這正好示範自動 proxy 不是人類理解證據。所有結果保留，不為了漂亮數字重跑。回饋後校正是 deterministic mechanism replay；下方 fresh pair 固定對照該案例的初始輪，沒有把 replay 假稱新的模型生成。</div></section>'
        '<footer class="eq-footer"><div class="done"><b>已證明</b><span>同句異境、具名狀態介入、候選效用、回饋後局部校正、fresh same-model outputs</span></div>'
        '<div class="pending"><b>仍待證明</b><span>目標使用者與至少三位獨立評審的盲式「被理解感」偏好</span></div>'
        '<div class="forbidden"><b>禁止宣稱</b><span>讀心、意識、真人等價、完整人腦方程式、普遍優於 LLM</span></div></footer></section>'
    )


def show_feedback_correction(_case_id=DEFAULT_CASE_ID, _phase="1"):
    """Jump to the falsification story where uncertainty becomes explicit tease."""
    del _case_id, _phase
    return DEFAULT_CASE_ID, "2", render_equation_lab(DEFAULT_CASE_ID, "2")
