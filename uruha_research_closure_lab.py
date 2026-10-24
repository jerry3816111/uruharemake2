"""M11 graphical evidence closure for the longitudinal human-model program."""

from __future__ import annotations

import hashlib
import json
from html import escape
from pathlib import Path


ROOT = Path(__file__).resolve().parent
MAP_PATH = ROOT / "configs/m11_research_evidence_map.json"
DEFAULT_CLOSURE_STAGE = "M8"

STATUS_LABELS = {
    "complete": "治理完成",
    "engineering_complete": "工程完成",
    "bounded_pass": "有限通過",
    "mixed_negative": "混合／負證據",
    "negative_result": "假說失敗",
    "blocked_human": "等待真人",
}

RESEARCH_CLOSURE_CSS = """
.closure-shell{background:radial-gradient(circle at 8% 5%,#1b2b43 0,#070c15 45%,#04070c 100%);color:#edf6ff;border:1px solid #28364b;border-radius:24px;padding:26px;box-shadow:0 22px 65px rgba(0,0,0,.34)}
.closure-kicker{font-size:11px;font-weight:800;letter-spacing:.16em;color:#5ed8ff!important}.closure-title{font-size:34px;font-weight:850;line-height:1.16;color:#f8fbff!important;margin:8px 0}.closure-sub{font-size:13px;line-height:1.6;color:#a9bad0!important;max-width:1050px}.closure-badges{display:flex;gap:8px;flex-wrap:wrap;margin:15px 0}.closure-badge{border:1px solid #34465f;border-radius:99px;padding:6px 10px;color:#c7d6e8!important;background:#0b1422;font-size:11px}.closure-equation{display:flex;align-items:stretch;gap:8px;overflow-x:auto;padding:13px 0 18px}.closure-eq-node{min-width:128px;flex:1;border:1px solid #30425a;border-radius:14px;background:#0a1220;padding:13px}.closure-eq-node small{color:#738aa6!important;letter-spacing:.1em}.closure-eq-node b{display:block;color:#f2f7ff!important;font-size:14px;margin:6px 0}.closure-eq-node span{color:#9badc2!important;font-size:10px}.closure-arrow{align-self:center;color:#526b88!important;font-size:21px}.closure-spine{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin:10px 0 16px}.closure-stage{border:1px solid #2a3a50;border-left:4px solid #52647b;border-radius:13px;background:#09111e;padding:12px;min-height:118px}.closure-stage.selected{outline:2px solid #5bd4ff;outline-offset:1px}.closure-stage.bounded_pass,.closure-stage.engineering_complete,.closure-stage.complete{border-left-color:#62d9ae}.closure-stage.negative_result{border-left-color:#ff657c}.closure-stage.mixed_negative{border-left-color:#ffc75f}.closure-stage.blocked_human{border-left-color:#b792ff}.closure-stage-top{display:flex;align-items:center;justify-content:space-between;gap:6px}.closure-stage-id{color:#f5f9ff!important;font-size:14px;font-weight:800}.closure-status{font-size:9px;letter-spacing:.08em;color:#aebed2!important}.closure-stage-title{color:#cbd8e8!important;font-size:12px;margin:7px 0}.closure-stage-metric{color:#fff!important;font-size:15px;font-weight:750;line-height:1.35}.closure-detail{display:grid;grid-template-columns:1fr 1.2fr 1.2fr;gap:10px;margin:14px 0}.closure-detail>div{background:#0b1421;border:1px solid #2d3c51;border-radius:14px;padding:14px}.closure-detail span{display:block;color:#728aa6!important;font-size:9px;letter-spacing:.13em;margin-bottom:6px}.closure-detail b{color:#f2f7ff!important;font-size:13px;line-height:1.5}.closure-axis-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:11px}.closure-axis{background:#09111d;border:1px solid #29384d;border-radius:13px;padding:12px}.closure-axis-head{display:flex;justify-content:space-between;gap:8px;color:#eaf3ff!important;font-size:12px}.closure-track{height:9px;border-radius:99px;background:#1b2637;overflow:hidden;margin:9px 0}.closure-fill{height:100%;background:linear-gradient(90deg,#56cfff,#63e7b1)}.closure-axis-note{color:#8499b3!important;font-size:10px}.closure-claim-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:11px;margin-top:17px}.closure-claim{border:1px solid #2a3a50;border-radius:15px;background:#08101b;padding:14px}.closure-claim.supported{border-top:3px solid #63e3ad}.closure-claim.unsupported{border-top:3px solid #ff6b82}.closure-claim.blocked{border-top:3px solid #ffc85d}.closure-claim h3{font-size:13px;color:#f3f8ff!important;margin:0 0 8px}.closure-claim ul{margin:0;padding-left:18px}.closure-claim li{color:#aebed1!important;font-size:11px;line-height:1.5;margin:6px 0}.closure-gates{display:grid;grid-template-columns:1fr auto 1fr auto 1.1fr;gap:9px;align-items:stretch;margin-top:18px}.closure-gate{border:1px solid #34455c;background:#0a1320;border-radius:14px;padding:14px}.closure-gate em{display:block;color:#ffca65!important;font-size:10px;font-style:normal;letter-spacing:.1em}.closure-gate b{display:block;color:#f5f9ff!important;margin:7px 0;font-size:14px}.closure-gate span{color:#98abc1!important;font-size:10px;line-height:1.45}.closure-gate-arrow{align-self:center;color:#617994!important;font-size:22px}.closure-boundary{margin-top:16px;border:1px solid #4a3450;background:#160d19;border-radius:13px;padding:12px;color:#d8bfd7!important;font-size:11px;line-height:1.55}@media(max-width:1000px){.closure-spine{grid-template-columns:repeat(3,1fr)}.closure-claim-grid{grid-template-columns:1fr}.closure-gates{grid-template-columns:1fr}.closure-gate-arrow{transform:rotate(90deg)}}@media(max-width:720px){.closure-spine,.closure-axis-grid,.closure-detail{grid-template-columns:1fr}}
"""


def _sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_evidence_map():
    payload = json.loads(MAP_PATH.read_text(encoding="utf-8"))
    mismatches = []
    master = payload["master_spec"]
    if _sha256(master["path"]) != master["sha256"]:
        mismatches.append("master_spec")
    for source_id, binding in payload["sources"].items():
        path = Path(binding["path"])
        if not path.is_absolute():
            path = ROOT / path
        if not path.is_file() or _sha256(path) != binding["sha256"]:
            mismatches.append(source_id)
    if mismatches:
        raise RuntimeError("M11 evidence map source mismatch: " + ", ".join(mismatches))
    return payload


def closure_stage_choices():
    return [row["id"] for row in load_evidence_map()["stages"]]


def _stage(payload, stage_id):
    for row in payload["stages"]:
        if row["id"] == stage_id:
            return row
    return payload["stages"][0]


def _li(values):
    return "".join(f"<li>{escape(value)}</li>" for value in values)


def render_research_closure(stage_id=DEFAULT_CLOSURE_STAGE):
    payload = load_evidence_map()
    selected = _stage(payload, stage_id)
    equation = [
        ("H≤t", "封印歷史", "cutoff 前可觀察事件"),
        ("Mₜ", "結構記憶", "來源、有效期、衰減"),
        ("Sₜ", "估計狀態", "已知／推測／未知"),
        ("T", "狀態轉移", "事件如何改變狀態"),
        ("P(Y)", "行為分布", "先於任何自然語言"),
        ("L", "日文實現", "受行為 authority 約束"),
        ("J", "未來／人評", "驗證、反駁、校正"),
    ]
    equation_html = "".join(
        (
            ("<div class='closure-arrow'>→</div>" if index else "")
            + "<div class='closure-eq-node'>"
            + f"<small>{escape(symbol)}</small><b>{escape(label)}</b><span>{escape(note)}</span>"
            + "</div>"
        )
        for index, (symbol, label, note) in enumerate(equation)
    )
    stages_html = "".join(
        f"<div class='closure-stage {escape(row['status'])} {'selected' if row['id'] == selected['id'] else ''}'>"
        f"<div class='closure-stage-top'><span class='closure-stage-id'>{escape(row['id'])}</span>"
        f"<span class='closure-status'>{escape(STATUS_LABELS[row['status']])}</span></div>"
        f"<div class='closure-stage-title'>{escape(row['title'])}</div>"
        f"<div class='closure-stage-metric'>{escape(row['headline'])}</div></div>"
        for row in payload["stages"]
    )
    axes_html = "".join(
        f"<div class='closure-axis'><div class='closure-axis-head'><b>{escape(axis['label'])}</b>"
        f"<span>{axis['percent_low']}–{axis['percent_high']}%</span></div>"
        f"<div class='closure-track'><div class='closure-fill' style='width:{axis['percent_high']}%'></div></div>"
        f"<div class='closure-axis-note'>{escape(axis['basis'])}</div></div>"
        for axis in payload["maturity_axes"]
    )
    claims = payload["claims"]
    return f"""
    <section class="closure-shell">
      <div class="closure-kicker">M11 · RESEARCH EVIDENCE CLOSURE · HASH-BOUND SYNTHESIS</div>
      <div class="closure-title">不是做一個會聊天的角色，而是檢驗一條「人類行為方程」能不能預測未見未來</div>
      <div class="closure-sub">一ノ瀬うるは是公開可觀察人格的第一個目標案例；真正研究單位是可反駁的計算模型。每一層都必須先封印未來、輸出機率，再讓之後發生的行為或真人評分來支持或否定。</div>
      <div class="closure-badges"><span class="closure-badge">12 stages</span><span class="closure-badge">negative results retained</span><span class="closure-badge">formal Uruha evidence 0%</span><span class="closure-badge">0/3 language raters</span></div>
      <div class="closure-equation">{equation_html}</div>
      <div class="closure-spine">{stages_html}</div>
      <div class="closure-detail">
        <div><span>SELECTED STAGE</span><b>{escape(selected['id'])} · {escape(selected['title'])}</b></div>
        <div><span>WHAT THE EVIDENCE ACTUALLY SHOWS</span><b>{escape(selected['evidence'])}</b></div>
        <div><span>ALLOWED CLAIM</span><b>{escape(selected['claim'])}</b></div>
      </div>
      <div class="closure-axis-grid">{axes_html}</div>
      <div class="closure-claim-grid">
        <div class="closure-claim supported"><h3>目前有證據支持</h3><ul>{_li(claims['supported'])}</ul></div>
        <div class="closure-claim unsupported"><h3>目前不能宣稱</h3><ul>{_li(claims['not_supported'])}</ul></div>
        <div class="closure-claim blocked"><h3>完成研究還缺</h3><ul>{_li(claims['blocked_next'])}</ul></div>
      </div>
      <div class="closure-gates">
        <div class="closure-gate"><em>HUMAN GATE A</em><b>V7 雙人資料編碼</b><span>兩位真人各 18 格；目前 0。可靠度過關才准做完整 formal Uruha dataset。</span></div>
        <div class="closure-gate-arrow">→</div>
        <div class="closure-gate"><em>CORE SCIENCE GATE</em><b>新資料重跑預測</b><span>rolling cutoff、B0–B5、Ours、消融、介入、第二人轉移；M8/M9 負結果必須被解決或接受。</span></div>
        <div class="closure-gate-arrow">→</div>
        <div class="closure-gate"><em>HUMAN GATE B</em><b>M10.3 三人盲評</b><span>三位真人各 18 組；目前 0/3。只能證明下游自然度與行為保持，不能代替預測效度。</span></div>
      </div>
      <div class="closure-boundary">{escape(payload['global_boundary'])} 工程架構完成度不是模型正確率；synthetic success 不是 real-person evidence；失敗的假說也算完成一次有效研究，但不等於整體研究成功。</div>
    </section>
    """
