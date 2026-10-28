"""Teacher-facing, read-only M1/M2 Temporal Prediction Observatory."""

from __future__ import annotations

from html import escape
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DATASET_PATH = ROOT / "datasets/m1_temporal_prediction_synthetic_fixture_v1.json"
RESULT_PATH = ROOT / "analysis/m1_temporal_prediction_observatory_synthetic_v1_1_raw.json"
M2_RESULT_PATH = ROOT / "analysis/m2_strong_temporal_baselines_synthetic_first_generation_raw.json"
FAILED_V1_PATH = ROOT / "analysis/m1_temporal_prediction_observatory_synthetic_first_generation_raw.json"
GATE_PATH = ROOT / "configs/m1_uruha_temporal_data_gate.json"
DEFAULT_SAMPLE_ID = "s07"

BASELINE_LABELS = {
    "B0_PRIOR": ("B0｜只看過去頻率", "prior"),
    "B1_BASE_LLM": ("B1｜普通 LLM，只看當前事件", "base"),
    "B2_PERSONA_PROMPT": ("B2｜同模型＋人物摘要", "persona"),
    "B3_RAG": ("B3｜同模型＋cutoff 前記憶", "rag"),
    "B4_FULL_HISTORY_SUMMARY": ("B4｜同模型＋完整歷史摘要", "summary"),
    "B5_STRUCTURED_HISTORY": ("B5｜同模型＋結構化完整歷史", "structured"),
}
BEHAVIOR_LABELS = {
    "acknowledge_then_continue": "承接後繼續",
    "joke_and_deflect": "玩笑卸壓／轉開",
    "defer_commitment": "延後承諾",
    "direct_rejection": "直接拒絕",
    "ask_clarification": "先問清楚",
    "pause_and_reassess": "暫停並重估",
}


TEMPORAL_PREDICTION_LAB_CSS = r"""
.tp-lab{--tp-blue:#38bdf8;--tp-green:#34d399;--tp-amber:#fbbf24;--tp-red:#fb7185;--tp-violet:#a78bfa;overflow:hidden;border:1px solid rgba(56,189,248,.25);border-radius:24px;color:#e2e8f0;background:radial-gradient(circle at 8% 0%,rgba(56,189,248,.16),transparent 30%),radial-gradient(circle at 93% 2%,rgba(167,139,250,.15),transparent 31%),#050914;box-shadow:0 30px 90px rgba(2,6,23,.5)}
.tp-lab *{box-sizing:border-box}.tp-hero{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:20px;align-items:center;padding:25px 28px 20px;border-bottom:1px solid rgba(148,163,184,.13)}.tp-kicker{color:#67e8f9;font-size:10px;font-weight:800;letter-spacing:.14em}.tp-title{margin:6px 0 0;color:#f8fafc;font-size:clamp(23px,3vw,38px);font-weight:850;line-height:1.08}.tp-sub{max-width:920px;margin-top:8px;color:#94a3b8;font-size:11px;line-height:1.55}.tp-stamps{display:grid;gap:7px;min-width:230px}.tp-stamp{border:1px solid rgba(52,211,153,.34);border-radius:13px;padding:10px 13px;background:rgba(6,78,59,.2);text-align:right}.tp-stamp.warn{border-color:rgba(251,113,133,.38);background:rgba(127,29,29,.2)}.tp-stamp b{display:block;color:#a7f3d0;font-size:14px}.tp-stamp.warn b{color:#fecdd3}.tp-stamp span{color:#94a3b8;font-size:8px;letter-spacing:.06em}.tp-thesis{display:grid;grid-template-columns:1fr 35px 1fr 35px 1fr 35px 1fr;gap:7px;align-items:center;padding:16px 24px;background:rgba(15,23,42,.68);border-bottom:1px solid rgba(148,163,184,.12)}.tp-thesis-node{min-height:72px;border:1px solid rgba(56,189,248,.24);border-radius:13px;padding:11px;background:rgba(14,116,144,.08)}.tp-thesis-node b{display:block;color:#e0f2fe;font-size:10px}.tp-thesis-node strong{display:block;margin-top:6px;color:#f8fafc;font-size:12px}.tp-thesis-node small{display:block;margin-top:5px;color:#64748b;font-size:8px;line-height:1.35}.tp-arrow{height:2px;background:linear-gradient(90deg,rgba(56,189,248,.15),rgba(56,189,248,.8));position:relative}.tp-arrow:after{content:"";position:absolute;right:-1px;top:-3px;border-left:6px solid #38bdf8;border-top:4px solid transparent;border-bottom:4px solid transparent}.tp-body{padding:20px 24px 26px}.tp-section-label{margin:0 3px 9px;color:#64748b;font-size:9px;font-weight:850;letter-spacing:.12em}.tp-timeline{display:grid;grid-template-columns:minmax(0,2fr) 95px minmax(170px,.8fr) 35px minmax(150px,.7fr);gap:10px;align-items:stretch}.tp-past{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:5px;border:1px solid rgba(148,163,184,.14);border-radius:16px;padding:10px;background:rgba(15,23,42,.65)}.tp-event{min-height:52px;border:1px solid rgba(148,163,184,.13);border-radius:9px;padding:7px;background:rgba(30,41,59,.68);color:#64748b;font-size:7px;line-height:1.25}.tp-event b{display:block;color:#94a3b8;font-size:8px;margin-bottom:4px}.tp-event.used{border-color:rgba(167,139,250,.7);background:rgba(76,29,149,.3);box-shadow:0 0 16px rgba(167,139,250,.11)}.tp-cutoff{display:grid;place-items:center;border:1px solid rgba(251,191,36,.36);border-radius:15px;background:repeating-linear-gradient(135deg,rgba(113,63,18,.18),rgba(113,63,18,.18) 6px,rgba(251,191,36,.04) 6px,rgba(251,191,36,.04) 12px);text-align:center}.tp-cutoff b{display:block;color:#fde68a;font-size:11px}.tp-cutoff span{display:block;margin-top:5px;color:#d97706;font-size:7px}.tp-current,.tp-outcome{border:1px solid rgba(56,189,248,.35);border-radius:16px;padding:13px;background:rgba(14,116,144,.12)}.tp-current b,.tp-outcome b{color:#7dd3fc;font-size:8px}.tp-current p,.tp-outcome p{margin:7px 0 0;color:#f8fafc;font-size:11px;font-weight:700;line-height:1.45}.tp-outcome{border-color:rgba(52,211,153,.38);background:rgba(6,78,59,.15)}.tp-outcome b{color:#6ee7b7}.tp-outcome p{color:#a7f3d0}.tp-lanes{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:9px;margin-top:14px}.tp-lane{--lane:#94a3b8;border:1px solid color-mix(in srgb,var(--lane) 34%,#334155);border-radius:16px;padding:12px;background:color-mix(in srgb,var(--lane) 7%,rgba(15,23,42,.88))}.tp-lane.prior{--lane:#64748b}.tp-lane.base{--lane:var(--tp-blue)}.tp-lane.persona{--lane:var(--tp-amber)}.tp-lane.rag{--lane:var(--tp-violet)}.tp-lane.correct{box-shadow:inset 0 3px 0 rgba(52,211,153,.72)}.tp-lane.wrong{box-shadow:inset 0 3px 0 rgba(251,113,133,.72)}.tp-lane-head{min-height:36px;display:flex;justify-content:space-between;gap:8px}.tp-lane-head b{color:#f8fafc;font-size:9px;line-height:1.35}.tp-verdict{height:max-content;border-radius:999px;padding:3px 7px;font-size:7px}.tp-verdict.correct{color:#a7f3d0;background:rgba(6,78,59,.5)}.tp-verdict.wrong{color:#fecdd3;background:rgba(127,29,29,.45)}.tp-prob{display:grid;grid-template-columns:82px 1fr 35px;gap:6px;align-items:center;margin-top:7px;color:#94a3b8;font-size:7px}.tp-prob.actual{color:#a7f3d0}.tp-prob-track{height:7px;overflow:hidden;border-radius:99px;background:rgba(148,163,184,.12)}.tp-prob-track i{display:block;height:100%;border-radius:99px;background:var(--lane)}.tp-prob.actual .tp-prob-track{outline:1px solid rgba(52,211,153,.65)}.tp-lane-foot{min-height:30px;margin-top:9px;padding-top:7px;border-top:1px solid rgba(148,163,184,.1);color:#64748b;font-size:7px;line-height:1.4}.tp-analysis{display:grid;grid-template-columns:1.15fr .85fr;gap:10px;margin-top:16px}.tp-card{border:1px solid rgba(148,163,184,.15);border-radius:16px;padding:13px;background:rgba(15,23,42,.7)}.tp-card h3{margin:0;color:#f8fafc;font-size:11px}.tp-metric-row{display:grid;grid-template-columns:125px repeat(4,minmax(55px,1fr));gap:7px;align-items:center;margin-top:10px}.tp-metric-row>span{color:#94a3b8;font-size:8px}.tp-metric-cell{position:relative;height:29px;border-radius:7px;overflow:hidden;background:rgba(148,163,184,.08);text-align:center}.tp-metric-cell i{position:absolute;bottom:0;left:0;top:0;opacity:.32;background:var(--tp-blue)}.tp-metric-cell b{position:relative;color:#f8fafc;font-size:8px;line-height:29px}.tp-metric-head{color:#64748b!important;text-align:center}.tp-cost{display:grid;grid-template-columns:96px 1fr auto;gap:7px;align-items:center;margin-top:9px;color:#94a3b8;font-size:8px}.tp-cost-track{height:8px;overflow:hidden;border-radius:99px;background:rgba(148,163,184,.12)}.tp-cost-track i{display:block;height:100%;border-radius:99px;background:var(--tp-violet)}.tp-retrieval{display:grid;grid-template-columns:repeat(4,1fr);gap:6px;margin-top:10px}.tp-memory{border:1px solid rgba(167,139,250,.28);border-radius:9px;padding:8px;background:rgba(76,29,149,.17)}.tp-memory b{display:block;color:#c4b5fd;font-size:7px}.tp-memory span{display:block;margin-top:5px;color:#94a3b8;font-size:7px;line-height:1.35}.tp-audit{display:grid;grid-template-columns:1fr 32px 1fr;gap:8px;align-items:center;margin-top:16px}.tp-audit-node{border:1px solid rgba(251,113,133,.28);border-radius:14px;padding:12px;background:rgba(127,29,29,.11)}.tp-audit-node.pass{border-color:rgba(52,211,153,.3);background:rgba(6,78,59,.12)}.tp-audit-node b{display:block;color:#fecdd3;font-size:9px}.tp-audit-node.pass b{color:#a7f3d0}.tp-audit-node strong{display:block;margin-top:6px;color:#f8fafc;font-size:13px}.tp-audit-node span{display:block;margin-top:5px;color:#94a3b8;font-size:8px;line-height:1.4}.tp-roadmap{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:5px;margin-top:16px}.tp-stage{min-height:86px;border-top:3px solid rgba(148,163,184,.24);padding:9px 7px;background:rgba(15,23,42,.45)}.tp-stage.done{border-color:var(--tp-green)}.tp-stage.active{border-color:var(--tp-amber)}.tp-stage.blocked{border-color:var(--tp-red)}.tp-stage b{display:block;color:#f8fafc;font-size:9px}.tp-stage span{display:block;margin-top:6px;color:#64748b;font-size:7px;line-height:1.4}.tp-boundary{display:grid;grid-template-columns:repeat(3,1fr);gap:1px;margin-top:16px;background:rgba(148,163,184,.12)}.tp-boundary div{padding:11px 13px;background:#08101f}.tp-boundary b{display:block;font-size:9px}.tp-boundary span{display:block;margin-top:4px;color:#64748b;font-size:8px;line-height:1.42}.tp-boundary .yes b{color:#86efac}.tp-boundary .mixed b{color:#fde68a}.tp-boundary .no b{color:#fda4af}
@media(max-width:1050px){.tp-lanes{grid-template-columns:repeat(2,1fr)}.tp-timeline{grid-template-columns:1fr}.tp-arrow{width:2px;height:18px;margin:auto}.tp-analysis{grid-template-columns:1fr}.tp-thesis{grid-template-columns:1fr}.tp-retrieval{grid-template-columns:repeat(2,1fr)}}
@media(max-width:680px){.tp-hero{grid-template-columns:1fr;padding:20px 16px}.tp-stamp{text-align:left}.tp-body{padding:16px}.tp-lanes,.tp-roadmap,.tp-boundary{grid-template-columns:1fr}.tp-past{grid-template-columns:repeat(3,1fr)}.tp-metric-row{grid-template-columns:90px repeat(4,minmax(42px,1fr));gap:3px}.tp-retrieval{grid-template-columns:1fr}.tp-audit{grid-template-columns:1fr}}
.tp-lanes{grid-template-columns:repeat(3,minmax(0,1fr))}.tp-lane.summary{--lane:var(--tp-green)}.tp-lane.structured{--lane:#fb923c}.tp-metric-row{grid-template-columns:110px repeat(6,minmax(45px,1fr));gap:5px}.tp-summary{margin-top:8px;border:1px solid rgba(52,211,153,.24);border-radius:10px;padding:9px;background:rgba(6,78,59,.11);color:#94a3b8;font-size:7px;line-height:1.45}.tp-summary b{display:block;color:#a7f3d0;font-size:8px;margin-bottom:5px}
@media(max-width:1050px){.tp-lanes{grid-template-columns:repeat(2,1fr)}}
@media(max-width:680px){.tp-lanes{grid-template-columns:1fr}.tp-metric-row{grid-template-columns:70px repeat(6,minmax(34px,1fr));gap:2px}}
"""


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _text(value):
    return escape(str(value or ""))


def sample_choices():
    dataset = _load(DATASET_PATH)
    choices = []
    for sample in dataset["samples"]:
        label = BEHAVIOR_LABELS[sample["actual_observed_behavior"]]
        choices.append((f"{sample['sample_id'].upper()} · {label}", sample["sample_id"]))
    return choices


def _selected_payload(sample_id):
    dataset = _load(DATASET_PATH)
    result = _load(RESULT_PATH)
    m2_result = _load(M2_RESULT_PATH)
    failed = _load(FAILED_V1_PATH)
    gate = _load(GATE_PATH)
    sample = next((row for row in dataset["samples"] if row["sample_id"] == sample_id), None)
    if sample is None:
        sample = dataset["samples"][0]
    combined_rows = list(result["rows"]) + list(m2_result["rows"])
    rows = {row["baseline"]: row for row in combined_rows if row["sample_id"] == sample["sample_id"]}
    history = {row["history_id"]: row for row in dataset["history"]}
    return dataset, result, m2_result, failed, gate, sample, rows, history


def _history_nodes(sample, history, retrieved):
    chunks = []
    for history_id in sample["available_history_ids"]:
        row = history[history_id]
        used = " used" if history_id in retrieved else ""
        chunks.append(
            f'<div class="tp-event{used}" title="{_text(row["observable_summary"])}">'
            f'<b>{_text(history_id.upper())}</b>{_text(BEHAVIOR_LABELS[row["behavior_label"]])}</div>'
        )
    return "".join(chunks)


def _probability_rows(row, actual):
    sorted_rows = sorted(row["probabilities"].items(), key=lambda item: (-item[1], item[0]))
    chunks = []
    for label, probability in sorted_rows:
        actual_class = " actual" if label == actual else ""
        chunks.append(
            f'<div class="tp-prob{actual_class}"><span>{_text(BEHAVIOR_LABELS[label])}</span>'
            f'<div class="tp-prob-track"><i style="width:{probability * 100:.1f}%"></i></div>'
            f'<b>{probability * 100:.1f}%</b></div>'
        )
    return "".join(chunks)


def _baseline_lane(baseline, row, actual):
    label, css = BASELINE_LABELS[baseline]
    predicted = max(row["probabilities"], key=row["probabilities"].get)
    correct = predicted == actual
    verdict = "命中" if correct else "誤判"
    retrieved = row.get("retrieved_history_ids") or []
    if baseline == "B0_PRIOR":
        info = "0 token · 均衡歷史使先驗無法分辨情境"
    elif baseline == "B1_BASE_LLM":
        info = "只接收當前事件；沒有 persona、沒有跨輪記憶"
    elif baseline == "B2_PERSONA_PROMPT":
        info = "增加固定人物摘要；仍沒有事件級歷史檢索"
    elif baseline == "B3_RAG":
        info = f"實際檢索：{' · '.join(item.upper() for item in retrieved)}"
    elif baseline == "B4_FULL_HISTORY_SUMMARY":
        info = "一次濃縮完整合法歷史；12 個事件共用 frozen derivative"
    else:
        info = "12 筆歷史按行為分組完整送入；仍由 LLM 直接決定機率"
    return (
        f'<article class="tp-lane {css} {"correct" if correct else "wrong"}">'
        f'<div class="tp-lane-head"><b>{_text(label)}</b><span class="tp-verdict {"correct" if correct else "wrong"}">{verdict}</span></div>'
        f'{_probability_rows(row, actual)}<div class="tp-lane-foot">{_text(info)}</div></article>'
    )


def _metric_table(metrics):
    rows = [
        ("Top-1 ↑", "top1_accuracy", 1.0),
        ("Brier ↓", "brier_score", 1.0),
        ("NLL ↓", "negative_log_likelihood", 2.0),
        ("ECE ↓", "expected_calibration_error", 0.5),
    ]
    header = '<div class="tp-metric-row"><span></span>' + "".join(
        f'<span class="tp-metric-head">{baseline[:2]}</span>' for baseline in BASELINE_LABELS
    ) + "</div>"
    body = []
    for label, key, ceiling in rows:
        cells = []
        for baseline in BASELINE_LABELS:
            value = float(metrics[baseline][key])
            width = min(100.0, value / ceiling * 100.0)
            cells.append(
                f'<div class="tp-metric-cell"><i style="width:{width:.1f}%"></i><b>{value:.3f}</b></div>'
            )
        body.append(f'<div class="tp-metric-row"><span>{label}</span>{"".join(cells)}</div>')
    return header + "".join(body)


def _cost_rows(result, m2_result):
    by_baseline = dict(result["resources"]["by_baseline"])
    by_baseline.update(m2_result["resources"]["by_baseline"])
    totals = {
        baseline: row["prompt_tokens"] + row["completion_tokens"] for baseline, row in by_baseline.items()
    }
    maximum = max(totals.values()) or 1
    chunks = []
    for baseline in BASELINE_LABELS:
        name = BASELINE_LABELS[baseline][0].split("｜")[0]
        row = by_baseline[baseline]
        chunks.append(
            f'<div class="tp-cost"><span>{name}</span><div class="tp-cost-track"><i style="width:{max(1, totals[baseline] / maximum * 100):.1f}%"></i></div>'
            f'<b>{totals[baseline]} tok · {row["latency_seconds"]:.1f}s</b></div>'
        )
    summary = m2_result["resources"]["summary_runtime"]
    summary_tokens = summary["prompt_tokens"] + summary["completion_tokens"]
    chunks.append(
        f'<div class="tp-cost"><span>B4 摘要建置</span><div class="tp-cost-track"><i style="width:{max(1, summary_tokens / maximum * 100):.1f}%"></i></div>'
        f'<b>{summary_tokens} tok · {summary["latency_seconds"]:.1f}s</b></div>'
    )
    return "".join(chunks)


def _retrieval_cards(retrieved, history):
    return "".join(
        f'<div class="tp-memory"><b>{_text(history[item]["history_id"].upper())} · {_text(BEHAVIOR_LABELS[history[item]["behavior_label"]])}</b>'
        f'<span>{_text(history[item]["observable_summary"])}</span></div>'
        for item in retrieved
    )


def render_temporal_prediction_lab(sample_id=DEFAULT_SAMPLE_ID):
    dataset, result, m2_result, failed, gate, sample, rows, history = _selected_payload(str(sample_id))
    actual = sample["actual_observed_behavior"]
    retrieved = rows["B3_RAG"]["retrieved_history_ids"]
    lanes = "".join(_baseline_lane(name, rows[name], actual) for name in BASELINE_LABELS)
    model_input_count = len(sample["available_history_ids"])
    return f"""
    <section class="tp-lab">
      <header class="tp-hero"><div><div class="tp-kicker">M2 · INTERPRETABLE LONGITUDINAL HUMAN DIGITAL TWIN</div><h1 class="tp-title">不是猜一句話：是在時間封印下預測下一個人類行為</h1><div class="tp-sub">研究問題是：只准看某個時間點以前的公開可觀察證據，系統能否比相同基礎模型更準、更校準地預測一個人的下一個可觀察行為？一ノ瀬うるは是第一個真實案例；目前畫面先用合成人物驗證整個實驗儀器與 B0–B5 比較地板。</div></div><div class="tp-stamps"><div class="tp-stamp"><b>72 PREDICTIONS · B0–B5 COMPLETE</b><span>M1 ONE-WEEK CHECKPOINT · ARCHIVED</span></div><div class="tp-stamp warn"><b>{_text(gate['decision'])}</b><span>URUHA FORMAL DATA · 0 CODED EVENTS</span></div></div></header>
      <div class="tp-thesis"><div class="tp-thesis-node"><b>① 可觀察輸入 Aₜ</b><strong>事件、關係、時序</strong><small>不把未公開心理當資料</small></div><div class="tp-arrow"></div><div class="tp-thesis-node"><b>② 縱向狀態 Sₜ</b><strong>cutoff 前的記憶與人物參數</strong><small>每個來源、時間、可用性可追蹤</small></div><div class="tp-arrow"></div><div class="tp-thesis-node"><b>③ 行為分布 P(Bₜ₊₁)</b><strong>先算每種行為機率</strong><small>語言回答是下游，不是研究真值</small></div><div class="tp-arrow"></div><div class="tp-thesis-node"><b>④ 未來結果 yₜ₊₁</b><strong>解封後計算誤差</strong><small>Brier · NLL · ECE · ranking</small></div></div>
      <div class="tp-body">
        <div class="tp-section-label">TEMPORAL EVIDENCE GRAPH · 紫色是 B3 本輪真的取用的記憶</div>
        <div class="tp-timeline"><div class="tp-past">{_history_nodes(sample, history, retrieved)}</div><div class="tp-cutoff"><div><b>🔒 CUTOFF</b><span>{_text(sample['available_history_cutoff'][:10])}<br>{model_input_count} records allowed<br>future hidden</span></div></div><div class="tp-current"><b>CURRENT EVENT · {_text(sample['sample_id'].upper())}</b><p>{_text(sample['event_context'])}</p></div><div class="tp-arrow"></div><div class="tp-outcome"><b>🔓 OBSERVED AFTER PREDICTION</b><p>{_text(BEHAVIOR_LABELS[actual])}</p></div></div>
        <div class="tp-section-label" style="margin-top:16px">SAME MODEL / SAME EVENT · INFORMATION CONDITION IS THE CHANGED VARIABLE</div>
        <div class="tp-lanes">{lanes}</div>
        <div class="tp-analysis"><section class="tp-card"><h3>12 個未來樣本｜B0–B5 整體機率品質</h3>{_metric_table(m2_result['combined_b0_b5_metrics'])}<div class="tp-retrieval">{_retrieval_cards(retrieved, history)}</div><div class="tp-summary"><b>B4 FULL-HISTORY SUMMARY · 12 個事件 → 1 個 frozen derivative</b>{_text(m2_result['summaries'][0]['summary'])}</div></section><section class="tp-card"><h3>比較成本｜M1 36 calls + M2 25 calls</h3>{_cost_rows(result, m2_result)}<div class="tp-cost"><span>M2 整輪</span><div class="tp-cost-track"><i style="width:100%"></i></div><b>{m2_result['resources']['prompt_tokens'] + m2_result['resources']['completion_tokens']} tok · {m2_result['resources']['latency_seconds']:.1f}s</b></div></section></div>
        <div class="tp-section-label" style="margin-top:16px">FAILED RUN IS EVIDENCE · 不把失敗藏掉</div>
        <div class="tp-audit"><div class="tp-audit-node"><b>V1 · FROZEN FIRST GENERATION</b><strong>{failed['observed_prediction_rows']} / {failed['expected_prediction_rows']} · INVALID</strong><span>19 筆輸出是合法六類機率，但 JSON 放在最外層；原 parser 依合約拒絕。原始失敗完整保留。</span></div><div class="tp-arrow"></div><div class="tp-audit-node pass"><b>V1.1 · SINGLE-CHANGE REMEDIATION</b><strong>{result['observed_prediction_rows']} / {result['expected_prediction_rows']} · COMPLETE</strong><span>只接受等價 top-level probability map；資料、prompt、模型、seed、分數與 no-retry 規則不變。它是 nonfresh engineering rerun。</span></div></div>
        <div class="tp-roadmap"><div class="tp-stage done"><b>✓ M0｜研究規格</b><span>問題、假設、變數、倫理與 leakage policy 已綁定 master spec。</span></div><div class="tp-stage done"><b>✓ M1｜一週完成線</b><span>時間切割、B0–B3、機率評估、成本、鎖與圖像化；已封存。</span></div><div class="tp-stage done"><b>✓ M2｜強基線</b><span>B4 full-summary 與 B5 structured-history 已完成首次模型執行。</span></div><div class="tp-stage active"><b>→ M3–M6｜真正模型</b><span>memory、HumanState、transition、Ours hybrid、消融與干預。</span></div><div class="tp-stage blocked"><b>✕ 真人資料 gate</b><span>Uruha 0 個正式事件；需兩位獨立 coder 先通過 reliability。</span></div></div>
        <div class="tp-boundary"><div class="yes"><b>現在真的完成</b><span>B0–B5 六組比較介面、72 筆合成預測、完整機率／成本與失敗可視化。</span></div><div class="mixed"><b>目前觀察</b><span>B2/B3 Top‑1 83.3% 最高；B5 Top‑1 75%，但 Brier 0.291、NLL 0.637 最佳。Ours 必須面對兩種地板。</span></div><div class="no"><b>現在不能宣稱</b><span>Uruha 預測成功、B5 已泛化、比 LLM 更懂真人、完成 Human Twin、人腦方程式或意識。</span></div></div>
      </div>
    </section>
    """
