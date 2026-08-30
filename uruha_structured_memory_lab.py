"""Read-only graphical M3 Structured Temporal Memory lab."""

from __future__ import annotations

from html import escape
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DATASET_PATH = ROOT / "datasets/m3_structured_memory_synthetic_fixture_v1.json"
RESULT_PATH = ROOT / "analysis/m3_structured_memory_synthetic_first_result.json"
DEFAULT_QUERY_ID = "q06_technical"

QUERY_LABELS = {
    "q01_cooperation": "Q1 · 團隊既定路線",
    "q02_public_pressure": "Q2 · 公開壓力",
    "q03_commitment": "Q3 · 忙碌時的新承諾",
    "q04_privacy": "Q4 · 隱私界線",
    "q05_ambiguity": "Q5 · 模糊指示",
    "q06_technical": "Q6 · 重複技術失敗",
}
COMPONENT_LABELS = {
    "semantic_relevance": "語意相關",
    "recency": "時間新近",
    "frequency": "重複頻率",
    "importance": "重要程度",
    "emotional_salience": "情緒顯著",
    "relationship_relevance": "關係相關",
    "confidence": "證據信心",
}

STRUCTURED_MEMORY_LAB_CSS = r"""
.mm-lab{--cyan:#22d3ee;--green:#34d399;--violet:#a78bfa;--orange:#fb923c;--red:#fb7185;overflow:hidden;border:1px solid rgba(34,211,238,.25);border-radius:24px;color:#e2e8f0;background:radial-gradient(circle at 7% 0%,rgba(34,211,238,.16),transparent 32%),radial-gradient(circle at 94% 5%,rgba(167,139,250,.16),transparent 28%),#050914;box-shadow:0 30px 90px rgba(2,6,23,.5)}
.mm-lab *{box-sizing:border-box}.mm-hero{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:18px;align-items:center;padding:25px 28px 20px;border-bottom:1px solid rgba(148,163,184,.13)}.mm-kicker{color:#67e8f9;font-size:10px;font-weight:850;letter-spacing:.15em}.mm-title{margin:6px 0 0;color:#f8fafc;font-size:clamp(23px,3vw,38px);line-height:1.08}.mm-sub{max-width:940px;margin:8px 0 0;color:#94a3b8;font-size:11px;line-height:1.55}.mm-stamps{display:grid;gap:7px;min-width:225px}.mm-stamp{border:1px solid rgba(52,211,153,.34);border-radius:13px;padding:10px 13px;background:rgba(6,78,59,.18);text-align:right}.mm-stamp.warn{border-color:rgba(251,113,133,.4);background:rgba(127,29,29,.18)}.mm-stamp b{display:block;color:#a7f3d0;font-size:13px}.mm-stamp.warn b{color:#fecdd3}.mm-stamp span{display:block;margin-top:3px;color:#64748b;font-size:8px}.mm-flow{display:grid;grid-template-columns:1fr 32px 1fr 32px 1fr 32px 1fr;gap:7px;align-items:center;padding:16px 24px;background:rgba(15,23,42,.7);border-bottom:1px solid rgba(148,163,184,.12)}.mm-flow-node{min-height:74px;border:1px solid rgba(34,211,238,.24);border-radius:13px;padding:11px;background:rgba(14,116,144,.08)}.mm-flow-node b{display:block;color:#cffafe;font-size:9px}.mm-flow-node strong{display:block;margin-top:6px;color:#f8fafc;font-size:12px}.mm-flow-node small{display:block;margin-top:5px;color:#64748b;font-size:8px;line-height:1.35}.mm-arrow{height:2px;background:linear-gradient(90deg,rgba(34,211,238,.15),rgba(34,211,238,.8));position:relative}.mm-arrow:after{content:"";position:absolute;right:-1px;top:-3px;border-left:6px solid #22d3ee;border-top:4px solid transparent;border-bottom:4px solid transparent}.mm-body{padding:20px 24px 26px}.mm-label{margin:0 3px 9px;color:#64748b;font-size:9px;font-weight:850;letter-spacing:.12em}.mm-query{display:grid;grid-template-columns:minmax(0,1.3fr) .7fr;gap:10px}.mm-card{border:1px solid rgba(148,163,184,.15);border-radius:16px;padding:14px;background:rgba(15,23,42,.72)}.mm-card h3{margin:0;color:#f8fafc;font-size:12px}.mm-query-text{margin-top:8px;color:#bae6fd;font-size:13px;font-weight:700;line-height:1.45}.mm-chips{display:flex;flex-wrap:wrap;gap:5px;margin-top:10px}.mm-chip{border-radius:999px;padding:4px 8px;background:rgba(14,116,144,.2);color:#a5f3fc;font-size:8px}.mm-cutoff{display:grid;grid-template-columns:1fr 1fr;gap:7px;margin-top:9px}.mm-cutoff div{border:1px solid rgba(251,191,36,.24);border-radius:9px;padding:8px;background:rgba(113,63,18,.12)}.mm-cutoff b{display:block;color:#fde68a;font-size:8px}.mm-cutoff span{display:block;margin-top:4px;color:#94a3b8;font-size:8px}.mm-records{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:6px;margin-top:12px}.mm-record{min-height:66px;border:1px solid rgba(148,163,184,.14);border-radius:10px;padding:8px;background:rgba(30,41,59,.6)}.mm-record b{display:block;color:#94a3b8;font-size:8px}.mm-record span{display:block;margin-top:5px;color:#64748b;font-size:7px;line-height:1.3}.mm-record.selected{border-color:rgba(52,211,153,.8);background:rgba(6,78,59,.25);box-shadow:0 0 18px rgba(52,211,153,.12)}.mm-record.selected b{color:#a7f3d0}.mm-record.excluded{border-color:rgba(251,113,133,.55);background:repeating-linear-gradient(135deg,rgba(127,29,29,.18),rgba(127,29,29,.18) 5px,rgba(251,113,133,.04) 5px,rgba(251,113,133,.04) 10px)}.mm-record.excluded b{color:#fecdd3}.mm-reason{color:#fb7185!important}.mm-selected-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:10px;margin-top:14px}.mm-selected{border:1px solid rgba(52,211,153,.26);border-radius:16px;padding:13px;background:rgba(6,78,59,.12)}.mm-selected-head{display:flex;justify-content:space-between;gap:10px}.mm-selected-head b{color:#a7f3d0;font-size:11px}.mm-score{color:#f8fafc;font-size:14px;font-weight:850}.mm-event{margin-top:7px;color:#94a3b8;font-size:8px;line-height:1.42}.mm-component{display:grid;grid-template-columns:105px 1fr 34px;gap:7px;align-items:center;margin-top:7px;color:#94a3b8;font-size:7px}.mm-track{height:7px;border-radius:99px;overflow:hidden;background:rgba(148,163,184,.12)}.mm-track i{display:block;height:100%;border-radius:99px;background:linear-gradient(90deg,var(--violet),var(--cyan))}.mm-provenance{margin-top:9px;padding-top:8px;border-top:1px solid rgba(148,163,184,.1);color:#64748b;font-size:7px;line-height:1.45}.mm-ablation{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:7px;margin-top:14px}.mm-abl{border:1px solid rgba(167,139,250,.2);border-radius:12px;padding:10px;background:rgba(76,29,149,.1)}.mm-abl.full{border-color:rgba(52,211,153,.38);background:rgba(6,78,59,.13)}.mm-abl.drop{border-color:rgba(251,146,60,.28);background:rgba(124,45,18,.1)}.mm-abl b{display:block;color:#ddd6fe;font-size:9px}.mm-abl.full b{color:#a7f3d0}.mm-abl strong{display:block;margin-top:7px;color:#f8fafc;font-size:15px}.mm-abl span{display:block;margin-top:5px;color:#64748b;font-size:7px;line-height:1.4}.mm-proof{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:14px}.mm-proof-card{border-top:3px solid var(--green);padding:11px;background:rgba(15,23,42,.55)}.mm-proof-card.blocked{border-color:var(--red)}.mm-proof-card b{display:block;color:#f8fafc;font-size:9px}.mm-proof-card strong{display:block;margin-top:7px;color:#a7f3d0;font-size:14px}.mm-proof-card.blocked strong{color:#fecdd3}.mm-proof-card span{display:block;margin-top:5px;color:#64748b;font-size:8px;line-height:1.4}.mm-boundary{display:grid;grid-template-columns:repeat(3,1fr);gap:1px;margin-top:14px;background:rgba(148,163,184,.12)}.mm-boundary div{padding:11px 13px;background:#08101f}.mm-boundary b{display:block;font-size:9px}.mm-boundary span{display:block;margin-top:4px;color:#64748b;font-size:8px;line-height:1.42}.mm-boundary .yes b{color:#86efac}.mm-boundary .next b{color:#fde68a}.mm-boundary .no b{color:#fda4af}
@media(max-width:1050px){.mm-records{grid-template-columns:repeat(4,1fr)}.mm-ablation{grid-template-columns:repeat(2,1fr)}.mm-flow{grid-template-columns:1fr}.mm-arrow{width:2px;height:18px;margin:auto}}
@media(max-width:680px){.mm-hero{grid-template-columns:1fr;padding:20px 16px}.mm-stamp{text-align:left}.mm-body{padding:16px}.mm-query,.mm-selected-grid,.mm-proof,.mm-boundary{grid-template-columns:1fr}.mm-records{grid-template-columns:repeat(2,1fr)}.mm-ablation{grid-template-columns:1fr}}
"""


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _text(value):
    return escape(str(value or ""))


def query_choices():
    dataset = _load(DATASET_PATH)
    return [(QUERY_LABELS[row["query_id"]], row["query_id"]) for row in dataset["queries"]]


def _payload(query_id):
    dataset = _load(DATASET_PATH)
    result = _load(RESULT_PATH)
    queries = {row["query_id"]: row for row in dataset["queries"]}
    records = {row["memory_id"]: row for row in dataset["records"]}
    if query_id not in queries:
        query_id = DEFAULT_QUERY_ID
    row = next(row for row in result["conditions"]["none"]["rows"] if row["query_id"] == query_id)
    return dataset, result, queries[query_id], records, row


def _record_nodes(records, selected_ids, excluded):
    reasons = {row["memory_id"]: row["reasons"] for row in excluded}
    chunks = []
    for memory_id, record in records.items():
        css = " selected" if memory_id in selected_ids else " excluded" if memory_id in reasons else ""
        if memory_id in reasons:
            detail = " / ".join(reasons[memory_id])
        else:
            detail = " · ".join(record["topics"][:2])
        chunks.append(
            f'<div class="mm-record{css}" title="{_text(record["event"])}">'
            f'<b>{_text(memory_id.upper())}</b><span class="{"mm-reason" if memory_id in reasons else ""}">{_text(detail)}</span></div>'
        )
    return "".join(chunks)


def _selected_cards(selected, records):
    chunks = []
    for trace in selected:
        record = records[trace["memory_id"]]
        bars = []
        for name, label in COMPONENT_LABELS.items():
            value = float(trace["components"][name])
            bars.append(
                f'<div class="mm-component"><span>{_text(label)}</span><div class="mm-track"><i style="width:{value * 100:.1f}%"></i></div><b>{value:.2f}</b></div>'
            )
        provenance = trace["provenance"]
        chunks.append(
            '<article class="mm-selected">'
            f'<div class="mm-selected-head"><b>{_text(trace["memory_id"].upper())} · SELECTED</b><span class="mm-score">A={trace["score"]:.3f}</span></div>'
            f'<div class="mm-event">{_text(record["event"])}</div>{"".join(bars)}'
            f'<div class="mm-provenance">SOURCE {_text(provenance["source_url_or_id"])} · available {_text(provenance["available_at"])}<br>extractor {_text(provenance["extraction_model"])} · dataset {_text(provenance["dataset_version"])}</div>'
            '</article>'
        )
    return "".join(chunks)


def _ablation_cards(result):
    order = ["none", *COMPONENT_LABELS]
    chunks = []
    for condition in order:
        metrics = result["conditions"][condition]["metrics"]
        full = condition == "none"
        label = "完整記憶函數" if full else f'移除「{COMPONENT_LABELS[condition]}」'
        chunks.append(
            f'<div class="mm-abl {"full" if full else "drop"}"><b>{_text(label)}</b>'
            f'<strong>Recall@2 {metrics["recall_at_k"] * 100:.1f}%</strong>'
            f'<span>ranking 改變 {metrics["rank_order_changed_queries"]}/6 · selected-set 改變 {metrics["selected_set_changed_queries"]}/6<br>平均分數變動 {metrics["mean_absolute_score_delta_from_full"]:.4f}</span></div>'
        )
    return "".join(chunks)


def render_structured_memory_lab(query_id=DEFAULT_QUERY_ID):
    dataset, result, query, records, row = _payload(query_id)
    selected_ids = row["selected_memory_ids"]
    excluded_count = len(row["excluded"])
    topics = "".join(f'<span class="mm-chip">{_text(topic)}</span>' for topic in query["topics"])
    entities = "".join(f'<span class="mm-chip">關係 · {_text(entity)}</span>' for entity in query["entities"])
    gates = result["gate_checks"]
    return (
        '<section class="mm-lab">'
        '<header class="mm-hero"><div><div class="mm-kicker">M3 · STRUCTURED TEMPORAL MEMORY</div>'
        '<h1 class="mm-title">記憶不是文字倉庫：每一筆都能被追溯、計分、移除與否決</h1>'
        '<p class="mm-sub">先用時間與有效性 gate 封掉不合法記憶，再把語意、時間、頻率、重要性、情緒、關係與信心分開計算。這是 HumanState 前的記憶器官；目前只驗證機制，尚未宣稱提升真人行為預測。</p></div>'
        '<div class="mm-stamps"><div class="mm-stamp"><b>M3 MECHANISM · PASS</b><span>14 records · 6 queries · 8 conditions</span></div>'
        '<div class="mm-stamp warn"><b>REAL-PERSON EVIDENCE · BLOCKED</b><span>synthetic fixture · equal weights not fitted</span></div></div></header>'
        '<div class="mm-flow"><div class="mm-flow-node"><b>① RECORD</b><strong>來源＋時間＋有效期</strong><small>記憶內容與 provenance 綁在一起</small></div><i class="mm-arrow"></i>'
        '<div class="mm-flow-node"><b>② ELIGIBILITY</b><strong>先封鎖未來與失效記憶</strong><small>subject · cutoff · available · validity</small></div><i class="mm-arrow"></i>'
        '<div class="mm-flow-node"><b>③ ACTIVATION</b><strong>7 個可拆分成分</strong><small>每一分從哪裡來都看得到</small></div><i class="mm-arrow"></i>'
        '<div class="mm-flow-node"><b>④ RETRIEVAL TRACE</b><strong>排序＋ablation</strong><small>移除一項後重新計算，不做事後故事</small></div></div>'
        '<div class="mm-body"><div class="mm-label">CURRENT QUERY · CUTOFF BEFORE RETRIEVAL</div>'
        '<div class="mm-query"><div class="mm-card"><h3>{}</h3><div class="mm-query-text">{}</div><div class="mm-chips">{}{}</div></div>'.format(
            _text(QUERY_LABELS[query["query_id"]]), _text(query["text"]), topics, entities
        )
        + '<div class="mm-card"><h3>時間封印</h3><div class="mm-cutoff"><div><b>PREDICTION</b><span>{}</span></div><div><b>AVAILABLE CUTOFF</b><span>{}</span></div></div>'.format(
            _text(query["prediction_time"]), _text(query["available_history_cutoff"])
        )
        + f'<div class="mm-chips"><span class="mm-chip">selected {len(selected_ids)}</span><span class="mm-chip">excluded {excluded_count}</span><span class="mm-chip">future selected 0</span></div></div></div>'
        '<div class="mm-label" style="margin-top:15px">14 MEMORY RECORDS · 綠色被選中，紅色在排序前被 gate 排除</div>'
        f'<div class="mm-records">{_record_nodes(records, selected_ids, row["excluded"])}</div>'
        '<div class="mm-label" style="margin-top:15px">SELECTED MEMORY ACTIVATION · 每個分數都可拆解</div>'
        f'<div class="mm-selected-grid">{_selected_cards(row["selected"], records)}</div>'
        '<div class="mm-label" style="margin-top:15px">MEMORY-ONLY ABLATION · 同一資料只移除一個成分</div>'
        f'<div class="mm-ablation">{_ablation_cards(result)}</div>'
        '<div class="mm-proof"><div class="mm-proof-card"><b>TEMPORAL / VALIDITY GATE</b><strong>future 0 · expired 0</strong><span>高分的 m13_future 與 m14_expired 仍無法進入 selected。</span></div>'
        f'<div class="mm-proof-card"><b>FULL RETRIEVAL PROXY</b><strong>Recall@2 {result["conditions"]["none"]["metrics"]["recall_at_k"] * 100:.1f}%</strong><span>6 個作者設計合成 query；只證明 instrument 能工作。</span></div>'
        '<div class="mm-proof-card blocked"><b>NEXT SCIENTIFIC GATE</b><strong>M4 HumanState</strong><span>把記憶送入 timestamped state snapshot；之後才評 behavior lift。</span></div></div>'
        '<div class="mm-boundary"><div class="yes"><b>現在真的完成</b><span>schema、provenance、cutoff、validity、7-part activation、deterministic retrieval、single-component ablation。</span></div>'
        '<div class="next"><b>相對 B5 的新增價值</b><span>B5 只把整段歷史交給 LLM；M3 的每筆記憶與每個分數都可查、可刪、可干預。但尚未證明 predictive lift。</span></div>'
        '<div class="no"><b>現在不能宣稱</b><span>Uruha 記憶模型已驗證、equal weights 是人腦參數、lexical proxy 等於語意理解、Human Twin 已完成。</span></div></div>'
        f'<div style="display:none">gate={_text(all(gates.values()))} dataset={_text(dataset["dataset_id"])} status={_text(result["status"])}</div>'
        '</div></section>'
    )
