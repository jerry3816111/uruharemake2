"""Read-only graphical M4 HumanState snapshot lab."""

from __future__ import annotations

from html import escape
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RESULT_PATH = ROOT / "analysis/m4_human_state_synthetic_first_result.json"
DEFAULT_STATE_ID = "q06_technical"
STATE_CHOICES = {
    "q06_technical": "Q6 · 技術失敗狀態",
    "q04_privacy": "Q4 · 隱私界線狀態",
}
DIMENSIONS = (
    ("M", "Memory", "memory_activations"),
    ("E", "Emotion estimate", "emotion"),
    ("P", "Personality tendency", "personality"),
    ("R", "Relationship", "relationships"),
    ("V", "Preference / value", "preferences"),
    ("G", "Goal", "goals"),
    ("H", "Habit", "habits"),
    ("K", "Context", "context"),
    ("U", "Uncertainty", "uncertainty"),
)

HUMAN_STATE_LAB_CSS = r"""
.hs-lab{--cyan:#22d3ee;--green:#34d399;--violet:#a78bfa;--amber:#fbbf24;--red:#fb7185;overflow:hidden;border:1px solid rgba(167,139,250,.28);border-radius:24px;color:#e2e8f0;background:radial-gradient(circle at 5% 0%,rgba(167,139,250,.18),transparent 31%),radial-gradient(circle at 96% 3%,rgba(34,211,238,.14),transparent 29%),#050914;box-shadow:0 30px 90px rgba(2,6,23,.5)}
.hs-lab *{box-sizing:border-box}.hs-hero{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:18px;align-items:center;padding:25px 28px 20px;border-bottom:1px solid rgba(148,163,184,.13)}.hs-kicker{color:#c4b5fd;font-size:10px;font-weight:850;letter-spacing:.15em}.hs-title{margin:6px 0 0;color:#f8fafc;font-size:clamp(23px,3vw,38px);line-height:1.08}.hs-sub{max-width:930px;margin:8px 0 0;color:#94a3b8;font-size:11px;line-height:1.55}.hs-stamps{display:grid;gap:7px;min-width:230px}.hs-stamp{border:1px solid rgba(52,211,153,.34);border-radius:13px;padding:10px 13px;background:rgba(6,78,59,.18);text-align:right}.hs-stamp.warn{border-color:rgba(251,191,36,.34);background:rgba(113,63,18,.16)}.hs-stamp b{display:block;color:#a7f3d0;font-size:13px}.hs-stamp.warn b{color:#fde68a}.hs-stamp span{display:block;margin-top:3px;color:#64748b;font-size:8px}.hs-flow{display:grid;grid-template-columns:1fr 30px 1fr 30px 1fr 30px 1fr;gap:7px;align-items:center;padding:16px 24px;background:rgba(15,23,42,.7);border-bottom:1px solid rgba(148,163,184,.12)}.hs-flow-node{min-height:72px;border:1px solid rgba(167,139,250,.24);border-radius:13px;padding:11px;background:rgba(76,29,149,.08)}.hs-flow-node b{display:block;color:#ddd6fe;font-size:9px}.hs-flow-node strong{display:block;margin-top:6px;color:#f8fafc;font-size:12px}.hs-flow-node small{display:block;margin-top:5px;color:#64748b;font-size:8px;line-height:1.35}.hs-arrow{height:2px;background:linear-gradient(90deg,rgba(167,139,250,.15),rgba(34,211,238,.8));position:relative}.hs-arrow:after{content:"";position:absolute;right:-1px;top:-3px;border-left:6px solid #22d3ee;border-top:4px solid transparent;border-bottom:4px solid transparent}.hs-body{padding:20px 24px 26px}.hs-meta{display:grid;grid-template-columns:1fr 1fr 1.2fr;gap:8px}.hs-meta div{border:1px solid rgba(148,163,184,.15);border-radius:12px;padding:10px;background:rgba(15,23,42,.65)}.hs-meta b{display:block;color:#c4b5fd;font-size:8px}.hs-meta span{display:block;margin-top:5px;color:#94a3b8;font-size:8px;word-break:break-all}.hs-label{margin:15px 3px 9px;color:#64748b;font-size:9px;font-weight:850;letter-spacing:.12em}.hs-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:9px}.hs-node{border:1px solid rgba(148,163,184,.16);border-radius:15px;padding:12px;background:rgba(15,23,42,.72)}.hs-node-head{display:flex;align-items:baseline;gap:8px}.hs-letter{display:grid;place-items:center;width:28px;height:28px;border-radius:9px;background:rgba(167,139,250,.2);color:#ddd6fe;font-size:14px;font-weight:900}.hs-node-head b{color:#f8fafc;font-size:10px}.hs-item{margin-top:9px;padding-top:8px;border-top:1px solid rgba(148,163,184,.1)}.hs-item:first-of-type{border-top:0}.hs-item-top{display:flex;justify-content:space-between;gap:8px}.hs-item-name{color:#e2e8f0;font-size:8px}.hs-value{color:#67e8f9;font-size:10px;font-weight:800}.hs-status{display:inline-block;margin-top:5px;border-radius:999px;padding:3px 6px;font-size:7px}.hs-status.observed{color:#a7f3d0;background:rgba(6,78,59,.4)}.hs-status.inferred{color:#fde68a;background:rgba(113,63,18,.4)}.hs-status.unknown{color:#fecdd3;background:rgba(127,29,29,.35)}.hs-evidence{margin-top:5px;color:#64748b;font-size:7px;line-height:1.35;word-break:break-all}.hs-memory{display:grid;grid-template-columns:1fr auto;gap:6px;margin-top:8px;border:1px solid rgba(52,211,153,.2);border-radius:9px;padding:8px;background:rgba(6,78,59,.1)}.hs-memory b{color:#a7f3d0;font-size:8px}.hs-memory strong{color:#f8fafc;font-size:11px}.hs-relation{margin-top:8px;color:#c4b5fd;font-size:8px;font-weight:800}.hs-uncertainty{display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-top:8px}.hs-uncertainty div{border-radius:9px;padding:8px;background:rgba(127,29,29,.12)}.hs-uncertainty b{display:block;color:#fecdd3;font-size:13px}.hs-uncertainty span{display:block;margin-top:4px;color:#94a3b8;font-size:7px}.hs-evidence-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:7px}.hs-evidence-card{border:1px solid rgba(34,211,238,.18);border-radius:11px;padding:9px;background:rgba(14,116,144,.08)}.hs-evidence-card b{display:block;color:#a5f3fc;font-size:8px}.hs-evidence-card span{display:block;margin-top:5px;color:#64748b;font-size:7px;line-height:1.4;word-break:break-all}.hs-proof{display:grid;grid-template-columns:repeat(4,1fr);gap:6px;margin-top:14px}.hs-proof div{border-top:3px solid var(--green);padding:10px;background:rgba(15,23,42,.55)}.hs-proof div.next{border-color:var(--amber)}.hs-proof div.blocked{border-color:var(--red)}.hs-proof b{display:block;color:#f8fafc;font-size:8px}.hs-proof strong{display:block;margin-top:6px;color:#a7f3d0;font-size:12px}.hs-proof .next strong{color:#fde68a}.hs-proof .blocked strong{color:#fecdd3}.hs-proof span{display:block;margin-top:4px;color:#64748b;font-size:7px;line-height:1.4}.hs-boundary{display:grid;grid-template-columns:repeat(3,1fr);gap:1px;margin-top:14px;background:rgba(148,163,184,.12)}.hs-boundary div{padding:11px 13px;background:#08101f}.hs-boundary b{display:block;font-size:9px}.hs-boundary span{display:block;margin-top:4px;color:#64748b;font-size:8px;line-height:1.42}.hs-boundary .yes b{color:#86efac}.hs-boundary .next b{color:#fde68a}.hs-boundary .no b{color:#fda4af}
@media(max-width:1000px){.hs-flow{grid-template-columns:1fr}.hs-arrow{width:2px;height:18px;margin:auto}.hs-grid{grid-template-columns:repeat(2,1fr)}.hs-meta{grid-template-columns:1fr}.hs-evidence-grid,.hs-proof{grid-template-columns:repeat(2,1fr)}}
@media(max-width:680px){.hs-hero{grid-template-columns:1fr;padding:20px 16px}.hs-stamp{text-align:left}.hs-body{padding:16px}.hs-grid,.hs-evidence-grid,.hs-proof,.hs-boundary{grid-template-columns:1fr}}
"""


def _load():
    return json.loads(RESULT_PATH.read_text(encoding="utf-8"))


def _text(value):
    if isinstance(value, bool):
        value = "true" if value else "false"
    if value is None:
        value = "UNKNOWN"
    return escape(str(value))


def state_choices():
    return [(label, key) for key, label in STATE_CHOICES.items()]


def _snapshot(state_id):
    result = _load()
    snapshots = {row["current_event_id"]: row for row in result["snapshots"]}
    if state_id not in snapshots:
        state_id = DEFAULT_STATE_ID
    return result, snapshots[state_id]


def _estimate_item(name, estimate):
    evidence = " · ".join(estimate["evidence_ids"]) or "no evidence — explicit unknown"
    return (
        '<div class="hs-item">'
        f'<div class="hs-item-top"><span class="hs-item-name">{_text(name)}</span><span class="hs-value">{_text(estimate["value"])}</span></div>'
        f'<span class="hs-status {_text(estimate["status"])}">{_text(estimate["status"])} · conf {estimate["confidence"]:.2f}</span>'
        f'<div class="hs-evidence" title="{_text(estimate["hypothesis_note"])}">↳ {_text(evidence)}</div></div>'
    )


def _dimension_node(letter, label, key, snapshot):
    head = f'<div class="hs-node-head"><span class="hs-letter">{letter}</span><b>{_text(label)}</b></div>'
    if key == "memory_activations":
        content = "".join(
            f'<div class="hs-memory"><b>{_text(row["memory_id"].upper())}</b><strong>A={row["score"]:.3f}</strong><span class="hs-evidence">{_text(row["evidence_id"])}</span></div>'
            for row in snapshot[key]
        )
    elif key == "relationships":
        chunks = []
        for entity, relationship in snapshot[key].items():
            chunks.append(f'<div class="hs-relation">ENTITY · {_text(entity)}</div>')
            chunks.extend(_estimate_item(name, value) for name, value in relationship["fields"].items())
        content = "".join(chunks)
    elif key == "uncertainty":
        value = snapshot[key]
        content = (
            f'<div class="hs-uncertainty"><div><b>{value["average_confidence"]:.2f}</b><span>average confidence</span></div>'
            f'<div><b>{len(value["unknown_fields"])}</b><span>explicit unknown paths</span></div></div>'
            + "".join(
                f'<div class="hs-item"><span class="hs-status unknown">UNKNOWN</span><div class="hs-evidence">{_text(path)}</div></div>'
                for path in value["unknown_fields"]
            )
            + "".join(
                f'<div class="hs-item"><span class="hs-status inferred">LOW CONFIDENCE</span><div class="hs-evidence">{_text(path)}</div></div>'
                for path in value["low_confidence_fields"]
            )
        )
    else:
        content = "".join(_estimate_item(name, value) for name, value in snapshot[key].items())
    return f'<article class="hs-node">{head}{content}</article>'


def render_human_state_lab(state_id=DEFAULT_STATE_ID):
    result, snapshot = _snapshot(state_id)
    nodes = "".join(_dimension_node(letter, label, key, snapshot) for letter, label, key in DIMENSIONS)
    evidence = "".join(
        f'<div class="hs-evidence-card"><b>{_text(row["evidence_id"])} · {_text(row["evidence_kind"])}</b>'
        f'<span>{_text(row["source_url_or_id"])}<br>observed {_text(row["observed_at"])}<br>available {_text(row["available_at"])}<br>{_text(row["extraction_model"])} · {_text(row["dataset_version"])}</span></div>'
        for row in snapshot["evidence_catalog"]
    )
    summary = result["summary"]
    return (
        '<section class="hs-lab"><header class="hs-hero"><div><div class="hs-kicker">M4 · TIMESTAMPED HUMANSTATE SNAPSHOT</div>'
        '<h1 class="hs-title">不是宣稱看穿人心：是把每個「我怎麼估計這個人」鎖成可反駁快照</h1>'
        '<p class="hs-sub">同一時間點的 Memory、Emotion、Personality、Relationship、Value、Goal、Habit、Context、Uncertainty 全部保留來源與信心。未知就寫 UNKNOWN；這一頁沒有 transition，也沒有把模型變數冒充成真人內心。</p></div>'
        '<div class="hs-stamps"><div class="hs-stamp"><b>M4 SNAPSHOT · PASS</b><span>2 deterministic IDs · exact replay</span></div>'
        '<div class="hs-stamp warn"><b>NO TRANSITION / NO PREDICTOR</b><span>M5 is the next dependency</span></div></div></header>'
        '<div class="hs-flow"><div class="hs-flow-node"><b>① CURRENT EVENT</b><strong>當下可觀察訊號</strong><small>只用 prediction time 已可得內容</small></div><i class="hs-arrow"></i>'
        '<div class="hs-flow-node"><b>② M3 MEMORY</b><strong>被選中的合法記憶</strong><small>activation 與 provenance 原樣繼承</small></div><i class="hs-arrow"></i>'
        '<div class="hs-flow-node"><b>③ M/E/P/R/V/G/H/K/U</b><strong>observed / inferred / unknown</strong><small>每個 estimate 都有 evidence IDs</small></div><i class="hs-arrow"></i>'
        '<div class="hs-flow-node"><b>④ IMMUTABLE SNAPSHOT</b><strong>SHA identity ＋ exact replay</strong><small>後續 transition 可以比較 before / after</small></div></div>'
        '<div class="hs-body"><div class="hs-meta"><div><b>STATE EVENT</b><span>{}</span></div><div><b>TIMESTAMP / CUTOFF</b><span>{}<br>{}</span></div><div><b>SNAPSHOT SHA-256</b><span>{}</span></div></div>'.format(
            _text(STATE_CHOICES[snapshot["current_event_id"]]), _text(snapshot["timestamp"]), _text(snapshot["available_history_cutoff"]), _text(snapshot["snapshot_id"])
        )
        + f'<div class="hs-label">THE FULL HUMANSTATE VECTOR · 9 inspectable parts</div><div class="hs-grid">{nodes}</div>'
        + f'<div class="hs-label">EVIDENCE CATALOG · every estimate points here</div><div class="hs-evidence-grid">{evidence}</div>'
        + '<div class="hs-proof"><div><b>DETERMINISTIC ID</b><strong>2 / 2</strong><span>同一 payload 產生相同 snapshot SHA。</span></div>'
        f'<div><b>ROUNDTRIP REPLAY</b><strong>exact</strong><span>serialize → reload 完全一致。</span></div><div><b>EVIDENCE SAFETY</b><strong>future {summary["future_evidence_count"]} · broken refs {summary["unresolved_evidence_reference_count"]}</strong><span>所有 memory evidence 早於 cutoff。</span></div>'
        '<div class="next"><b>NEXT DEPENDENCY</b><strong>M5 · T0–T3</strong><span>下一步才比較不同 state-transition 家族。</span></div></div>'
        '<div class="hs-boundary"><div class="yes"><b>現在真的完成</b><span>person-independent schema、9-part state、timestamp/cutoff、evidence binding、explicit unknown、snapshot identity、exact replay。</span></div>'
        '<div class="next"><b>它為研究增加什麼</b><span>後續不再只看 LLM 的文字理由；可以固定 Sₜ，逐項改動並比較 Sₜ₊₁ 與行為機率。</span></div>'
        '<div class="no"><b>現在不能宣稱</b><span>這些數值是真實心理、已學會人類轉變規律、已提升 B0–B5 預測、已完成 Uruha Digital Twin。</span></div></div>'
        '</div></section>'
    )
