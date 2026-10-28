"""Read-only graphical M5 T0-T3 state-transition comparison lab."""

from __future__ import annotations

from html import escape
import json
from pathlib import Path

from run_m5_state_transitions import expand_fixture


ROOT = Path(__file__).resolve().parent
RESULT_PATH = ROOT / "analysis/m5_state_transition_synthetic_first_generation_raw.json"
DATASET_PATH = ROOT / "datasets/m5_state_transition_synthetic_fixture_v1.json"
DEFAULT_TRANSITION_ID = "technical_failure_live::holdout"
FAMILY_LABELS = {
    "T0_STATIC": "T0 · 靜止",
    "T1_WEIGHTED": "T1 · 手寫權重",
    "T2_LINEAR": "T2 · 學得線性",
    "T3_HYBRID": "T3 · LLM 感知＋學習",
}
FAMILY_COLORS = {
    "T0_STATIC": "#fb7185",
    "T1_WEIGHTED": "#fbbf24",
    "T2_LINEAR": "#34d399",
    "T3_HYBRID": "#22d3ee",
}

TRANSITION_LAB_CSS = r"""
.tr-lab{--cyan:#22d3ee;--green:#34d399;--amber:#fbbf24;--red:#fb7185;--violet:#a78bfa;overflow:hidden;border:1px solid rgba(34,211,238,.25);border-radius:24px;color:#e2e8f0;background:radial-gradient(circle at 7% 0%,rgba(34,211,238,.16),transparent 32%),radial-gradient(circle at 96% 4%,rgba(52,211,153,.12),transparent 28%),#050914;box-shadow:0 30px 90px rgba(2,6,23,.5)}.tr-lab *{box-sizing:border-box}.tr-hero{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:20px;align-items:center;padding:25px 28px 20px;border-bottom:1px solid rgba(148,163,184,.13)}.tr-kicker{color:#67e8f9;font-size:10px;font-weight:900;letter-spacing:.16em}.tr-title{margin:6px 0 0;color:#f8fafc;font-size:clamp(23px,3vw,38px);line-height:1.08}.tr-sub{max-width:920px;margin:9px 0 0;color:#94a3b8;font-size:11px;line-height:1.55}.tr-stamps{display:grid;gap:7px;min-width:240px}.tr-stamp{border:1px solid rgba(52,211,153,.34);border-radius:13px;padding:10px 13px;background:rgba(6,78,59,.18);text-align:right}.tr-stamp.warn{border-color:rgba(251,191,36,.35);background:rgba(113,63,18,.16)}.tr-stamp b{display:block;color:#a7f3d0;font-size:13px}.tr-stamp.warn b{color:#fde68a}.tr-stamp span{display:block;margin-top:3px;color:#64748b;font-size:8px}.tr-body{padding:20px 24px 26px}.tr-score-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}.tr-score{border:1px solid rgba(148,163,184,.15);border-top:3px solid var(--family);border-radius:12px;padding:11px;background:rgba(15,23,42,.68)}.tr-score b{display:block;color:#e2e8f0;font-size:9px}.tr-score strong{display:block;margin-top:5px;color:var(--family);font-size:20px}.tr-score span{display:block;margin-top:3px;color:#64748b;font-size:8px}.tr-error-track{height:5px;margin-top:9px;border-radius:99px;background:#1e293b;overflow:hidden}.tr-error-fill{height:100%;background:var(--family);border-radius:99px}.tr-flow{display:grid;grid-template-columns:1fr 30px 1.15fr 30px 1.6fr 30px 1fr;gap:7px;align-items:center;margin-top:15px}.tr-flow-node{min-height:104px;border:1px solid rgba(34,211,238,.2);border-radius:14px;padding:12px;background:rgba(8,47,73,.13)}.tr-flow-node b{display:block;color:#a5f3fc;font-size:9px}.tr-flow-node strong{display:block;margin-top:7px;color:#f8fafc;font-size:12px;line-height:1.35}.tr-flow-node small{display:block;margin-top:6px;color:#64748b;font-size:8px;line-height:1.42}.tr-arrow{height:2px;background:linear-gradient(90deg,rgba(34,211,238,.15),rgba(52,211,153,.85));position:relative}.tr-arrow:after{content:"";position:absolute;right:-1px;top:-3px;border-left:6px solid #34d399;border-top:4px solid transparent;border-bottom:4px solid transparent}.tr-parallel{display:grid;grid-template-columns:repeat(2,1fr);gap:5px}.tr-mini{border-left:3px solid var(--family);border-radius:7px;padding:7px;background:rgba(15,23,42,.7)}.tr-mini b{color:var(--family);font-size:8px}.tr-mini span{display:block;margin-top:3px;color:#94a3b8;font-size:7px}.tr-label{margin:17px 3px 9px;color:#64748b;font-size:9px;font-weight:850;letter-spacing:.12em}.tr-dimension-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:9px}.tr-dimension{border:1px solid rgba(148,163,184,.15);border-radius:14px;padding:11px;background:rgba(15,23,42,.66)}.tr-dimension-head{display:flex;justify-content:space-between;align-items:center;gap:8px}.tr-dimension-head b{color:#f8fafc;font-size:9px}.tr-dimension-head span{color:#a7f3d0;font-size:8px}.tr-state-track{height:7px;margin:8px 0;border-radius:99px;background:#1e293b;position:relative}.tr-state-before,.tr-state-actual{position:absolute;top:-2px;width:3px;height:11px;border-radius:2px}.tr-state-before{background:#94a3b8}.tr-state-actual{background:#34d399}.tr-preds{display:grid;grid-template-columns:repeat(4,1fr);gap:4px}.tr-pred{border-radius:7px;padding:6px;text-align:center;background:#0f172a;border-top:2px solid var(--family)}.tr-pred b{display:block;color:var(--family);font-size:9px}.tr-pred span{display:block;margin-top:2px;color:#64748b;font-size:7px}.tr-feature-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}.tr-feature{border:1px solid rgba(167,139,250,.18);border-radius:11px;padding:9px;background:rgba(76,29,149,.08)}.tr-feature-head{display:flex;justify-content:space-between;gap:8px}.tr-feature-head b{color:#ddd6fe;font-size:8px}.tr-feature-head span{color:#94a3b8;font-size:7px}.tr-dual-track{height:8px;margin-top:8px;border-radius:99px;background:#1e293b;position:relative;overflow:hidden}.tr-gold{position:absolute;inset:0 auto 0 0;background:rgba(52,211,153,.55)}.tr-extracted{position:absolute;top:2px;bottom:2px;left:0;background:#22d3ee}.tr-insight{display:grid;grid-template-columns:1.2fr 1fr 1fr;gap:8px;margin-top:15px}.tr-insight div{border-radius:12px;padding:12px;background:#08101f;border-top:3px solid var(--tone)}.tr-insight b{display:block;color:var(--tone);font-size:9px}.tr-insight span{display:block;margin-top:6px;color:#94a3b8;font-size:8px;line-height:1.48}.tr-boundary{display:grid;grid-template-columns:repeat(3,1fr);gap:1px;margin-top:15px;background:rgba(148,163,184,.12)}.tr-boundary div{padding:11px 13px;background:#08101f}.tr-boundary b{display:block;font-size:9px}.tr-boundary span{display:block;margin-top:4px;color:#64748b;font-size:8px;line-height:1.42}.tr-boundary .yes b{color:#86efac}.tr-boundary .next b{color:#fde68a}.tr-boundary .no b{color:#fda4af}
@media(max-width:1000px){.tr-score-grid{grid-template-columns:repeat(2,1fr)}.tr-flow{grid-template-columns:1fr}.tr-arrow{width:2px;height:18px;margin:auto}.tr-dimension-grid{grid-template-columns:repeat(2,1fr)}.tr-insight{grid-template-columns:1fr}}
@media(max-width:680px){.tr-hero{grid-template-columns:1fr;padding:20px 16px}.tr-stamp{text-align:left}.tr-body{padding:16px}.tr-score-grid,.tr-dimension-grid,.tr-feature-grid,.tr-boundary{grid-template-columns:1fr}}
"""


def _load():
    result = json.loads(RESULT_PATH.read_text(encoding="utf-8"))
    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    examples = {item.example_id: item for item in expand_fixture(dataset) if item.split == "holdout"}
    return result, dataset, examples


def _text(value):
    return escape(str(value))


def transition_choices():
    _, _, examples = _load()
    return [(item.event_text, item.example_id) for item in examples.values()]


def _family_trace(result, family, example_id):
    return next(row for row in result["families"][family]["traces"] if row["example_id"] == example_id)


def _score_cards(result):
    max_rmse = max(result["families"][family]["metrics"]["rmse"] for family in FAMILY_LABELS)
    cards = []
    for family, label in FAMILY_LABELS.items():
        metrics = result["families"][family]["metrics"]
        width = 100 * metrics["rmse"] / max_rmse
        cards.append(
            f'<div class="tr-score" style="--family:{FAMILY_COLORS[family]}"><b>{label}</b>'
            f'<strong>{metrics["rmse"]:.4f}</strong><span>holdout RMSE · 越低越好<br>方向命中 {metrics["direction_accuracy"]:.1%}</span>'
            f'<div class="tr-error-track"><div class="tr-error-fill" style="width:{width:.1f}%"></div></div></div>'
        )
    return "".join(cards)


def _dimension_cards(result, example, example_id):
    traces = {family: _family_trace(result, family, example_id) for family in FAMILY_LABELS}
    cards = []
    for dimension, actual in example.next_state.items():
        before = example.previous_state[dimension]
        predictions = "".join(
            f'<div class="tr-pred" style="--family:{FAMILY_COLORS[family]}"><b>{trace["next_state"][dimension]:.2f}</b>'
            f'<span>|e| {abs(trace["next_state"][dimension] - actual):.3f}</span></div>'
            for family, trace in traces.items()
        )
        cards.append(
            '<div class="tr-dimension"><div class="tr-dimension-head">'
            f'<b>{_text(dimension)}</b><span>before {before:.2f} → gold {actual:.2f}</span></div>'
            f'<div class="tr-state-track"><i class="tr-state-before" style="left:{before*100:.1f}%"></i><i class="tr-state-actual" style="left:{actual*100:.1f}%"></i></div>'
            f'<div class="tr-preds">{predictions}</div></div>'
        )
    return "".join(cards)


def _feature_cards(result, example, example_id):
    record = next(row for row in result["feature_extraction"]["records"] if row["example_id"] == example_id)
    cards = []
    for name, gold in example.event_features.items():
        extracted = record["features"][name]
        cards.append(
            '<div class="tr-feature"><div class="tr-feature-head">'
            f'<b>{_text(name)}</b><span>gold {gold:.2f} · Qwen {extracted:.2f}</span></div>'
            f'<div class="tr-dual-track"><i class="tr-gold" style="width:{gold*100:.1f}%"></i><i class="tr-extracted" style="width:{extracted*100:.1f}%"></i></div></div>'
        )
    return "".join(cards)


def render_transition_lab(example_id=DEFAULT_TRANSITION_ID):
    result, _, examples = _load()
    if example_id not in examples:
        example_id = DEFAULT_TRANSITION_ID
    example = examples[example_id]
    t3_mae = result["feature_extraction"]["quality"]["holdout"]["mae"]
    resource = result["resource_accounting"]
    return (
        '<section class="tr-lab"><header class="tr-hero"><div><div class="tr-kicker">M5 · COMPARABLE STATE TRANSITIONS</div>'
        '<h1 class="tr-title">同一個人、同一事件、同一記憶：四種「下一刻會怎麼變」正面比較</h1>'
        '<p class="tr-sub">這不是讓 LLM 直接寫答案。所有家族都接收同一份 previous state、current event、retrieved memories、person parameters；T3 的 Qwen 只能讀事件並輸出六個可觀察特徵，不能看到 next state。</p></div>'
        '<div class="tr-stamps"><div class="tr-stamp"><b>FROZEN RUN · PASS</b><span>40 calls · 24 train / 8 dev / 8 holdout</span></div>'
        f'<div class="tr-stamp warn"><b>T3 IS NOT THE WINNER</b><span>feature MAE {t3_mae:.3f} · perception bottleneck retained</span></div></div></header>'
        f'<div class="tr-body"><div class="tr-score-grid">{_score_cards(result)}</div>'
        '<div class="tr-flow"><div class="tr-flow-node"><b>① Sₜ · PREVIOUS STATE</b><strong>六維可重播狀態</strong><small>arousal / irritation / caution / task focus / relationship tension / uncertainty</small></div><i class="tr-arrow"></i>'
        f'<div class="tr-flow-node"><b>② OBSERVED EVENT</b><strong>{_text(example.event_text)}</strong><small>holdout text · training 時未看過這句話</small></div><i class="tr-arrow"></i>'
        '<div class="tr-flow-node"><b>③ SAME CONTRACT · FOUR ROUTES</b><div class="tr-parallel">'
        + ''.join(f'<div class="tr-mini" style="--family:{FAMILY_COLORS[key]}"><b>{label}</b><span>{"static" if key=="T0_STATIC" else "gold features" if key in ("T1_WEIGHTED","T2_LINEAR") else "Qwen features"}</span></div>' for key, label in FAMILY_LABELS.items())
        + '</div></div><i class="tr-arrow"></i><div class="tr-flow-node"><b>④ Sₜ₊₁ · COMPARE</b><strong>估計值 vs disclosed synthetic oracle</strong><small>只評 state transition；沒有預測行為，也沒有生成對話</small></div></div>'
        f'<div class="tr-label">SELECTED HOLDOUT · gray = before · green = synthetic gold · four boxes = predicted next state</div><div class="tr-dimension-grid">{_dimension_cards(result, example, example_id)}</div>'
        f'<div class="tr-label">T3 PERCEPTION BOTTLENECK · green = fixture feature · cyan = Qwen extraction</div><div class="tr-feature-grid">{_feature_cards(result, example, example_id)}</div>'
        '<div class="tr-insight"><div style="--tone:#34d399"><b>最強機制證據 · T2</b><span>在這個公開方程式生成的 synthetic holdout，學得線性 transition RMSE 0.0042、方向命中 100%。它證明共同介面、訓練、dev 選擇與下一狀態比較確實可運作。</span></div>'
        '<div style="--tone:#22d3ee"><b>真實瓶頸 · T3</b><span>T3 RMSE 0.0576，輸給使用 gold feature 的 T1/T2。原因不是被藏起來：Qwen 事件特徵 MAE 0.229，repetition 與 support 偏差最大。</span></div>'
        f'<div style="--tone:#fbbf24"><b>實際資源</b><span>{resource["model_call_count"]} 次本機呼叫 · {resource["prompt_tokens"] + resource["completion_tokens"]:,} tokens · 累計推論 {resource["latency_seconds"]:.1f}s。T0–T2 本身不需要 LLM 呼叫。</span></div></div>'
        '<div class="tr-boundary"><div class="yes"><b>現在真的完成</b><span>T0–T3 共同介面、可檢查 contribution、train/dev/holdout 分離、凍結 first-generation 執行、no-retry、逐列 trace 與資源帳。</span></div>'
        '<div class="next"><b>它為研究增加什麼</b><span>HumanState 不再只是靜態快照；現在能把「同一輸入經不同 transition 如何成為下一狀態」拆開比較，M6 才能接 behavior predictor。</span></div>'
        '<div class="no"><b>現在不能宣稱</b><span>synthetic state 等於真人內心、T3 優於所有方法、已預測真實人類行為、已完成 Uruha twin 或一般化優勢。</span></div></div>'
        '</div></section>'
    )
