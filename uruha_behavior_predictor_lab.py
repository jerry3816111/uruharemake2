"""Read-only graphical M6 behavior-probability laboratory."""

from __future__ import annotations

from html import escape
import json
from pathlib import Path

from run_m5_state_transitions import expand_fixture


ROOT = Path(__file__).resolve().parent
RESULT_PATH = ROOT / "analysis/m6_behavior_predictor_synthetic_first_generation_raw.json"
M5_DATASET_PATH = ROOT / "datasets/m5_state_transition_synthetic_fixture_v1.json"
DEFAULT_BEHAVIOR_SAMPLE_ID = "technical_failure_live::holdout"
CONDITIONS = {
    "B0_PRIOR": ("B0", "#94a3b8"),
    "B1_BASE_LLM": ("B1", "#fb7185"),
    "B2_PERSONA_PROMPT": ("B2", "#f59e0b"),
    "B3_RAG": ("B3", "#a78bfa"),
    "B4_FULL_HISTORY_SUMMARY": ("B4", "#60a5fa"),
    "B5_STRUCTURED_HISTORY": ("B5", "#22d3ee"),
    "OURS_HYBRID": ("OURS", "#34d399"),
}

BEHAVIOR_PREDICTOR_LAB_CSS = r"""
.bp-lab{--green:#34d399;--cyan:#22d3ee;--amber:#fbbf24;--red:#fb7185;overflow:hidden;border:1px solid rgba(52,211,153,.26);border-radius:24px;color:#e2e8f0;background:radial-gradient(circle at 5% 0%,rgba(52,211,153,.16),transparent 32%),radial-gradient(circle at 97% 3%,rgba(34,211,238,.14),transparent 29%),#050914;box-shadow:0 30px 90px rgba(2,6,23,.5)}.bp-lab *{box-sizing:border-box}.bp-hero{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:20px;align-items:center;padding:25px 28px 20px;border-bottom:1px solid rgba(148,163,184,.13)}.bp-kicker{color:#86efac;font-size:10px;font-weight:900;letter-spacing:.16em}.bp-title{margin:6px 0 0;color:#f8fafc;font-size:clamp(23px,3vw,38px);line-height:1.08}.bp-sub{max-width:930px;margin:9px 0 0;color:#94a3b8;font-size:11px;line-height:1.55}.bp-stamps{display:grid;gap:7px;min-width:245px}.bp-stamp{border:1px solid rgba(52,211,153,.34);border-radius:13px;padding:10px 13px;background:rgba(6,78,59,.18);text-align:right}.bp-stamp.warn{border-color:rgba(251,191,36,.35);background:rgba(113,63,18,.16)}.bp-stamp b{display:block;color:#a7f3d0;font-size:13px}.bp-stamp.warn b{color:#fde68a}.bp-stamp span{display:block;margin-top:3px;color:#64748b;font-size:8px}.bp-body{padding:20px 24px 26px}.bp-metrics{display:grid;grid-template-columns:repeat(7,1fr);gap:6px}.bp-metric{border:1px solid rgba(148,163,184,.14);border-top:3px solid var(--condition);border-radius:11px;padding:9px;background:rgba(15,23,42,.7)}.bp-metric b{color:var(--condition);font-size:9px}.bp-metric strong{display:block;margin-top:5px;color:#f8fafc;font-size:16px}.bp-metric span{display:block;margin-top:3px;color:#64748b;font-size:7px;line-height:1.35}.bp-flow{display:grid;grid-template-columns:1fr 26px 1fr 26px 1fr 26px 1fr 26px 1fr;gap:6px;align-items:center;margin-top:15px}.bp-node{min-height:105px;border:1px solid rgba(52,211,153,.18);border-radius:13px;padding:11px;background:rgba(6,78,59,.08)}.bp-node b{display:block;color:#a7f3d0;font-size:8px}.bp-node strong{display:block;margin-top:7px;color:#f8fafc;font-size:11px;line-height:1.35}.bp-node small{display:block;margin-top:5px;color:#64748b;font-size:7px;line-height:1.4}.bp-arrow{height:2px;background:linear-gradient(90deg,rgba(52,211,153,.12),rgba(34,211,238,.85));position:relative}.bp-arrow:after{content:"";position:absolute;right:-1px;top:-3px;border-left:6px solid #22d3ee;border-top:4px solid transparent;border-bottom:4px solid transparent}.bp-label{margin:17px 3px 9px;color:#64748b;font-size:9px;font-weight:850;letter-spacing:.12em}.bp-condition-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:8px}.bp-condition{border:1px solid rgba(148,163,184,.15);border-left:4px solid var(--condition);border-radius:13px;padding:10px;background:rgba(15,23,42,.66)}.bp-condition-head{display:flex;justify-content:space-between;gap:8px}.bp-condition-head b{color:var(--condition);font-size:9px}.bp-condition-head span{color:#94a3b8;font-size:8px}.bp-prob{display:grid;grid-template-columns:145px 1fr 42px;gap:7px;align-items:center;margin-top:6px}.bp-prob label{overflow:hidden;text-overflow:ellipsis;color:#94a3b8;font-size:7px;white-space:nowrap}.bp-track{height:6px;border-radius:99px;background:#1e293b;overflow:hidden}.bp-fill{height:100%;background:var(--condition);border-radius:99px}.bp-prob em{color:#e2e8f0;font-size:7px;font-style:normal;text-align:right}.bp-actual{margin-top:7px;color:#64748b;font-size:7px}.bp-actual.pass{color:#86efac}.bp-actual.fail{color:#fda4af}.bp-detail{display:grid;grid-template-columns:1.15fr 1fr;gap:9px}.bp-contrib,.bp-calibration{border:1px solid rgba(148,163,184,.15);border-radius:14px;padding:11px;background:rgba(15,23,42,.66)}.bp-contrib-row{display:grid;grid-template-columns:1fr 55px;gap:8px;margin-top:7px;padding-bottom:6px;border-bottom:1px solid rgba(148,163,184,.08)}.bp-contrib-row b{color:#cbd5e1;font-size:7px}.bp-contrib-row span{font-size:8px;text-align:right}.bp-contrib-row span.pos{color:#86efac}.bp-contrib-row span.neg{color:#fda4af}.bp-temp-grid{display:grid;grid-template-columns:repeat(7,1fr);gap:4px;margin-top:8px}.bp-temp{border-radius:7px;padding:7px 4px;background:#0f172a;text-align:center;border-top:2px solid #64748b}.bp-temp.selected{border-color:#34d399;background:rgba(6,78,59,.2)}.bp-temp b{display:block;color:#e2e8f0;font-size:8px}.bp-temp span{display:block;margin-top:3px;color:#64748b;font-size:6px}.bp-insight{display:grid;grid-template-columns:1.2fr 1fr 1fr;gap:8px;margin-top:15px}.bp-insight div{border-radius:12px;padding:12px;background:#08101f;border-top:3px solid var(--tone)}.bp-insight b{display:block;color:var(--tone);font-size:9px}.bp-insight span{display:block;margin-top:6px;color:#94a3b8;font-size:8px;line-height:1.48}.bp-boundary{display:grid;grid-template-columns:repeat(3,1fr);gap:1px;margin-top:15px;background:rgba(148,163,184,.12)}.bp-boundary div{padding:11px 13px;background:#08101f}.bp-boundary b{display:block;font-size:9px}.bp-boundary span{display:block;margin-top:4px;color:#64748b;font-size:8px;line-height:1.42}.bp-boundary .yes b{color:#86efac}.bp-boundary .next b{color:#fde68a}.bp-boundary .no b{color:#fda4af}
@media(max-width:1100px){.bp-metrics{grid-template-columns:repeat(4,1fr)}.bp-flow{grid-template-columns:1fr}.bp-arrow{width:2px;height:18px;margin:auto}.bp-detail{grid-template-columns:1fr}}
@media(max-width:700px){.bp-hero{grid-template-columns:1fr;padding:20px 16px}.bp-stamp{text-align:left}.bp-body{padding:16px}.bp-metrics,.bp-condition-grid,.bp-insight,.bp-boundary{grid-template-columns:1fr}.bp-temp-grid{grid-template-columns:repeat(4,1fr)}}
"""


def _load():
    result = json.loads(RESULT_PATH.read_text(encoding="utf-8"))
    m5_dataset = json.loads(M5_DATASET_PATH.read_text(encoding="utf-8"))
    texts = {item.example_id: item.event_text for item in expand_fixture(m5_dataset) if item.split == "holdout"}
    return result, texts


def _text(value):
    return escape(str(value))


def behavior_sample_choices():
    _, texts = _load()
    return [(text, sample_id) for sample_id, text in texts.items()]


def _row(result, condition, sample_id):
    return next(row for row in result["rows"] if row["condition"] == condition and row["sample_id"] == sample_id)


def _predicted(row):
    return row.get("selected_behavior") or max(row["probabilities"], key=row["probabilities"].get)


def _metric_cards(result):
    cards = []
    for condition, (short, color) in CONDITIONS.items():
        metric = result["metrics"][condition]
        cards.append(
            f'<div class="bp-metric" style="--condition:{color}"><b>{short}</b><strong>{metric["top1_accuracy"]:.1%}</strong>'
            f'<span>Top-1<br>Brier {metric["brier_score"]:.3f}<br>NLL {metric["negative_log_likelihood"]:.3f}</span></div>'
        )
    return "".join(cards)


def _condition_cards(result, sample_id):
    cards = []
    labels = list(result["metrics"]["OURS_HYBRID"]["per_label"])
    for condition, (short, color) in CONDITIONS.items():
        row = _row(result, condition, sample_id)
        predicted = _predicted(row)
        actual = row["actual_observed_behavior"]
        ordered = sorted(labels, key=lambda label: (-row["probabilities"][label], labels.index(label)))
        bars = "".join(
            f'<div class="bp-prob"><label>{_text(label)}</label><div class="bp-track"><div class="bp-fill" style="width:{row["probabilities"][label]*100:.2f}%"></div></div><em>{row["probabilities"][label]:.1%}</em></div>'
            for label in ordered[:3]
        )
        status = "pass" if predicted == actual else "fail"
        cards.append(
            f'<div class="bp-condition" style="--condition:{color}"><div class="bp-condition-head"><b>{short} · {_text(condition)}</b><span>selected {_text(predicted)}</span></div>{bars}'
            f'<div class="bp-actual {status}">{"✓" if status=="pass" else "✕"} observed future · {_text(actual)}</div></div>'
        )
    return "".join(cards)


def _contributions(ours):
    return "".join(
        f'<div class="bp-contrib-row"><b>{_text(row["feature"])}</b><span class="{"pos" if row["contribution"]>=0 else "neg"}">{row["contribution"]:+.3f}</span></div>'
        for row in ours["explanation"]["selected_label_top_contributions"]
    )


def _temperature_cards(result):
    selected = result["calibration"]["selected_temperature"]
    return "".join(
        f'<div class="bp-temp {"selected" if row["temperature"]==selected else ""}"><b>T={row["temperature"]:g}</b><span>dev NLL<br>{row["dev_negative_log_likelihood"]:.4f}</span></div>'
        for row in result["calibration"]["candidates"]
    )


def render_behavior_predictor_lab(sample_id=DEFAULT_BEHAVIOR_SAMPLE_ID):
    result, texts = _load()
    if sample_id not in texts:
        sample_id = DEFAULT_BEHAVIOR_SAMPLE_ID
    ours = _row(result, "OURS_HYBRID", sample_id)
    predicted = ours["selected_behavior"]
    actual = ours["actual_observed_behavior"]
    correct = predicted == actual
    top = ours["behavior_candidates"][0]
    baseline_res = result["resources"]["fresh_b0_b5"]
    ours_res = result["resources"]["ours_inclusive"]
    status_label = "THIS ROW · CORRECT" if correct else "PRESERVED FAILURE"
    status_detail = f'{predicted} · p={top["probability"]:.3f}'
    state_values = ours["explanation"]["evidence"]["state_features"]
    state_summary = " · ".join(f"{name} {value:.2f}" for name, value in list(state_values.items())[:3])
    return (
        '<section class="bp-lab"><header class="bp-hero"><div><div class="bp-kicker">M6 · CALIBRATED BEHAVIOR PREDICTOR</div>'
        '<h1 class="bp-title">先預測「下一步會做什麼」的機率，再允許語言模型說話</h1>'
        '<p class="bp-sub">同一個未來事件同時交給 B0–B5 與 Ours。Ours 不直接生成句子：它把 transitioned state、event、memory、person parameters 變成可檢查 logits，校準後才選 behavior。所有輸出仍停在行為層。</p></div>'
        '<div class="bp-stamps"><div class="bp-stamp"><b>SYNTHETIC LIFT · PASS</b><span>Top-1 tie · Brier & NLL strictly lower</span></div>'
        f'<div class="bp-stamp warn"><b>{status_label}</b><span>{_text(status_detail)}</span></div></div></header>'
        f'<div class="bp-body"><div class="bp-metrics">{_metric_cards(result)}</div>'
        '<div class="bp-flow"><div class="bp-node"><b>① T3 TRANSITIONED STATE</b>'
        f'<strong>{_text(state_summary)}</strong><small>frozen M5 Qwen features + learned transition</small></div><i class="bp-arrow"></i>'
        '<div class="bp-node"><b>② BEHAVIOR LOGITS</b><strong>6 labels · exact linear contributions</strong><small>state + event + memory + person parameters</small></div><i class="bp-arrow"></i>'
        f'<div class="bp-node"><b>③ SOFTMAX</b><strong>{_text(top["label"])} · raw logit {top["logit"]:.2f}</strong><small>normalizes all six candidates</small></div><i class="bp-arrow"></i>'
        f'<div class="bp-node"><b>④ CALIBRATION</b><strong>temperature = {result["calibration"]["selected_temperature"]:g}</strong><small>selected only on 8 dev rows · not holdout</small></div><i class="bp-arrow"></i>'
        f'<div class="bp-node"><b>⑤ SELECT / REVEAL FUTURE</b><strong>{_text(predicted)} → {_text(actual)}</strong><small>{"match" if correct else "mismatch retained"} · no utterance generation</small></div></div>'
        f'<div class="bp-label">SAME HOLDOUT EVENT · {_text(texts[sample_id])}</div><div class="bp-condition-grid">{_condition_cards(result, sample_id)}</div>'
        '<div class="bp-label">WHY OURS SELECTED THIS LABEL · actual model terms, not an LLM-written story</div><div class="bp-detail"><div class="bp-contrib">'
        f'<b style="color:#86efac;font-size:9px">TOP CONTRIBUTIONS TO {_text(predicted)}</b>{_contributions(ours)}</div>'
        '<div class="bp-calibration"><b style="color:#67e8f9;font-size:9px">DEV-ONLY TEMPERATURE SEARCH</b>'
        f'<div class="bp-temp-grid">{_temperature_cards(result)}</div><div style="margin-top:10px;color:#94a3b8;font-size:8px;line-height:1.5">uncalibrated dev NLL {result["calibration"]["uncalibrated_dev_nll"]:.4f} → selected {result["calibration"]["calibrated_dev_nll"]:.4f}. T=0.5 sharpens confidence; with only eight synthetic dev rows this can overfit.</div></div></div>'
        '<div class="bp-insight"><div style="--tone:#34d399"><b>窄版差異成立</b><span>Ours 與最佳 baseline Top-1 同為 87.5%，但 Brier 0.151 vs 0.347、NLL 0.194 vs 0.695；代表本 fixture 上機率品質較好，不代表一般化。</span></div>'
        f'<div style="--tone:#22d3ee"><b>資源不藏</b><span>B0–B5 fresh 合計 41 calls、{baseline_res["prompt_tokens"]+baseline_res["completion_tokens"]:,} tokens、{baseline_res["latency_seconds"]:.1f}s。Ours 含 M5 前置 40 calls、{ours_res["inclusive_prompt_tokens"]+ours_res["inclusive_completion_tokens"]:,} tokens、{ours_res["inclusive_feature_latency_seconds"]:.1f}s。</span></div>'
        '<div style="--tone:#fb7185"><b>失敗也可切換看到</b><span>quiet_success 時 Ours 以 77.5% 錯選 direct_rejection；B2–B5 多數答對。M7 必須用 intervention 找出是哪個 state／feature 造成，不准直接重調 holdout。</span></div></div>'
        '<div class="bp-boundary"><div class="yes"><b>現在真的完成</b><span>state→logits→probability→calibration→selection、B0–B5 同資料比較、direct contributions、strict cutoff、成本與 frozen failure。</span></div>'
        '<div class="next"><b>下一個必要證據</b><span>M7 對 state/event/memory/person components 做 ablation，並做 probability-level intervention，驗證 explanation 是否真的有因果作用。</span></div>'
        '<div class="no"><b>現在不能宣稱</b><span>已預測 Uruha、已還原真人心理、已通過 unseen semantic holdout、已證明人類理解或已完成語言／voice runtime。</span></div></div>'
        '</div></section>'
    )
