"""Read-only graphical M8 rolling, scaling, and robustness laboratory."""

from __future__ import annotations

from html import escape
import json
from pathlib import Path


ROOT=Path(__file__).resolve().parent
RESULT_PATH=ROOT/"analysis/m8_1_rolling_scaling_parser_remediation_result.json"
DATASET_PATH=ROOT/"datasets/m8_rolling_semantic_synthetic_fixture_v1.json"
M71_PATH=ROOT/"analysis/m7_1_component_coverage_remediation_result.json"
DEFAULT_ROLLING_CUTOFF="E4"
CONDITIONS={
    "B0_PRIOR":("B0","#94a3b8"),"B1_BASE_LLM":("B1","#fb7185"),"B2_PERSONA_PROMPT":("B2","#f59e0b"),
    "B3_RAG":("B3","#a78bfa"),"B4_FULL_HISTORY_SUMMARY":("B4","#60a5fa"),"B5_STRUCTURED_HISTORY":("B5","#22d3ee"),"OURS_HYBRID":("OURS","#34d399")}

ROBUSTNESS_LAB_CSS=r"""
.rb-lab{--green:#34d399;--cyan:#22d3ee;--red:#fb7185;--amber:#fbbf24;overflow:hidden;border:1px solid rgba(251,113,133,.26);border-radius:24px;color:#e2e8f0;background:radial-gradient(circle at 6% 0%,rgba(251,113,133,.15),transparent 34%),radial-gradient(circle at 96% 4%,rgba(34,211,238,.13),transparent 30%),#050914;box-shadow:0 30px 90px rgba(2,6,23,.5)}.rb-lab *{box-sizing:border-box}.rb-hero{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:20px;align-items:center;padding:25px 28px 20px;border-bottom:1px solid rgba(148,163,184,.13)}.rb-kicker{color:#fda4af;font-size:10px;font-weight:900;letter-spacing:.16em}.rb-title{margin:6px 0 0;color:#f8fafc;font-size:clamp(23px,3vw,38px);line-height:1.08}.rb-sub{max-width:930px;margin:9px 0 0;color:#94a3b8;font-size:11px;line-height:1.55}.rb-stamps{display:grid;gap:7px;min-width:255px}.rb-stamp{border:1px solid rgba(251,113,133,.36);border-radius:13px;padding:10px 13px;background:rgba(127,29,29,.15);text-align:right}.rb-stamp.ok{border-color:rgba(52,211,153,.34);background:rgba(6,78,59,.17)}.rb-stamp b{display:block;color:#fecdd3;font-size:13px}.rb-stamp.ok b{color:#a7f3d0}.rb-stamp span{display:block;margin-top:3px;color:#64748b;font-size:8px}.rb-body{padding:20px 24px 26px}.rb-metrics{display:grid;grid-template-columns:repeat(7,1fr);gap:6px}.rb-metric{border:1px solid rgba(148,163,184,.14);border-top:3px solid var(--tone);border-radius:11px;padding:9px;background:rgba(15,23,42,.7)}.rb-metric b{color:var(--tone);font-size:9px}.rb-metric strong{display:block;margin-top:5px;color:#f8fafc;font-size:16px}.rb-metric span{display:block;margin-top:3px;color:#64748b;font-size:7px;line-height:1.35}.rb-label{margin:17px 3px 9px;color:#64748b;font-size:9px;font-weight:850;letter-spacing:.12em}.rb-roll{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}.rb-cut{border:1px solid rgba(148,163,184,.15);border-top:3px solid var(--tone);border-radius:13px;padding:11px;background:rgba(15,23,42,.66)}.rb-cut b{color:var(--tone);font-size:10px}.rb-cut strong{display:block;margin-top:7px;color:#f8fafc;font-size:19px}.rb-cut span{display:block;margin-top:5px;color:#64748b;font-size:7px;line-height:1.45}.rb-grid{display:grid;grid-template-columns:1.2fr .8fr;gap:9px}.rb-panel{border:1px solid rgba(148,163,184,.15);border-radius:14px;padding:12px;background:rgba(15,23,42,.66)}.rb-scale-row{display:grid;grid-template-columns:125px 1fr 56px;gap:7px;align-items:center;margin-top:7px}.rb-scale-row label{color:#cbd5e1;font-size:7px}.rb-track{height:8px;border-radius:99px;background:#1e293b;overflow:hidden}.rb-fill{height:100%;border-radius:99px;background:linear-gradient(90deg,#22d3ee,#fb7185)}.rb-scale-row em{color:#e2e8f0;font-size:7px;font-style:normal;text-align:right}.rb-seeds{display:grid;grid-template-columns:repeat(5,1fr);gap:5px}.rb-seed{border-radius:9px;padding:9px 5px;background:#08101f;border-top:2px solid #a78bfa;text-align:center}.rb-seed b{display:block;color:#c4b5fd;font-size:8px}.rb-seed strong{display:block;margin-top:5px;color:#f8fafc;font-size:13px}.rb-seed span{display:block;margin-top:3px;color:#64748b;font-size:6px}.rb-compare{display:grid;grid-template-columns:repeat(4,1fr);gap:7px}.rb-case{border:1px solid rgba(148,163,184,.15);border-radius:13px;padding:10px;background:#08101f}.rb-case b{display:block;color:#e2e8f0;font-size:8px}.rb-case p{height:38px;overflow:hidden;margin:6px 0;color:#64748b;font-size:7px;line-height:1.35}.rb-lane{display:grid;grid-template-columns:42px 1fr 36px;gap:5px;align-items:center;margin-top:5px}.rb-lane label{color:var(--tone);font-size:7px;font-weight:800}.rb-lane span{overflow:hidden;text-overflow:ellipsis;color:#94a3b8;font-size:6px;white-space:nowrap}.rb-lane em{font-size:7px;font-style:normal;text-align:right}.rb-lane.ok em{color:#86efac}.rb-lane.fail em{color:#fda4af}.rb-sign{display:grid;grid-template-columns:repeat(3,1fr);gap:7px}.rb-sign-card{border-radius:12px;padding:11px;background:#08101f;border-top:3px solid #fbbf24}.rb-sign-card b{color:#fde68a;font-size:9px}.rb-sign-card strong{display:block;margin-top:7px;color:#f8fafc;font-size:14px}.rb-sign-card span{display:block;margin-top:5px;color:#94a3b8;font-size:7px;line-height:1.42}.rb-boundary{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:15px}.rb-boundary div{border-radius:12px;padding:12px;background:#08101f;border-top:3px solid var(--tone)}.rb-boundary b{display:block;color:var(--tone);font-size:9px}.rb-boundary span{display:block;margin-top:6px;color:#94a3b8;font-size:8px;line-height:1.48}
@media(max-width:1100px){.rb-metrics{grid-template-columns:repeat(4,1fr)}.rb-grid{grid-template-columns:1fr}.rb-compare{grid-template-columns:repeat(2,1fr)}}@media(max-width:700px){.rb-hero{grid-template-columns:1fr;padding:20px 16px}.rb-stamp{text-align:left}.rb-body{padding:16px}.rb-metrics,.rb-roll,.rb-compare,.rb-sign,.rb-boundary{grid-template-columns:1fr}.rb-seeds{grid-template-columns:repeat(2,1fr)}}
"""


def _load():
    return (json.loads(RESULT_PATH.read_text()),json.loads(DATASET_PATH.read_text()),json.loads(M71_PATH.read_text()))


def rolling_cutoff_choices():
    result,dataset,_=_load(); counts=result["validation"]["inputs"]["history_counts"]
    return [(f'{cutoff["cutoff_id"]} · {counts[index]} history events',cutoff["cutoff_id"]) for index,cutoff in enumerate(dataset["rolling_cutoffs"])]


def _text(value): return escape(str(value))
def _pred(row): return row.get("selected_behavior") or max(row["probabilities"],key=row["probabilities"].get)


def _metric_cards(result):
    return "".join(f'<div class="rb-metric" style="--tone:{color}"><b>{short}</b><strong>{result["metrics"][condition]["top1_accuracy"]:.1%}</strong><span>Brier {result["metrics"][condition]["brier_score"]:.3f}<br>NLL {result["metrics"][condition]["negative_log_likelihood"]:.3f}</span></div>' for condition,(short,color) in CONDITIONS.items())


def _rolling_cards(result):
    counts=[8,12,16,20]
    cards=[]
    for index,cutoff in enumerate(("E1","E2","E3","E4")):
        row=result["rolling_metrics"][cutoff]; tone="#34d399" if row["top1_accuracy"]>=.75 else "#fb7185"
        cards.append(f'<div class="rb-cut" style="--tone:{tone}"><b>{cutoff} · {counts[index]} HISTORY</b><strong>{row["top1_accuracy"]:.0%}</strong><span>Brier {row["brier_score"]:.3f} · NLL {row["negative_log_likelihood"]:.3f}<br>ECE {row["expected_calibration_error"]:.3f}</span></div>')
    return "".join(cards)


def _scaling(result):
    rows=[]
    for name,metric in result["history_scaling_metrics"].items():
        width=min(100,metric["negative_log_likelihood"]/3.2*100)
        rows.append(f'<div class="rb-scale-row"><label>{_text(name)}</label><div class="rb-track"><div class="rb-fill" style="width:{width:.1f}%"></div></div><em>NLL {metric["negative_log_likelihood"]:.3f}</em></div>')
    return "".join(rows)


def _seed_cards(result):
    return "".join(f'<div class="rb-seed"><b>{seed}</b><strong>{metric["top1_accuracy"]:.1%}</strong><span>NLL {metric["negative_log_likelihood"]:.3f}</span></div>' for seed,metric in result["seed_metrics"].items())


def _cases(result,dataset,cutoff):
    ids=next(row["test_event_ids"] for row in dataset["rolling_cutoffs"] if row["cutoff_id"]==cutoff)
    texts={row["event_id"]:row["observable_text"] for row in dataset["events"]}
    cards=[]
    for sample_id in ids:
        lanes=[]
        for condition in ("B1_BASE_LLM","B5_STRUCTURED_HISTORY","OURS_HYBRID"):
            row=next(r for r in result["rows"] if r["sample_id"]==sample_id and r["condition"]==condition)
            pred=_pred(row); actual=row["actual_observed_behavior"]; ok=pred==actual; short,color=CONDITIONS[condition]
            lanes.append(f'<div class="rb-lane {"ok" if ok else "fail"}" style="--tone:{color}"><label>{short}</label><span>{_text(pred)}</span><em>{"✓" if ok else "✕"}</em></div>')
        cards.append(f'<div class="rb-case"><b>{sample_id}</b><p>{_text(texts[sample_id])}</p>{"".join(lanes)}</div>')
    return "".join(cards)


def render_robustness_lab(cutoff=DEFAULT_ROLLING_CUTOFF):
    result,dataset,m71=_load()
    if cutoff not in {"E1","E2","E3","E4"}: cutoff=DEFAULT_ROLLING_CUTOFF
    passed=sum(result["diagnostic_hypothesis_checks"].values()); resources=result["resources"]
    signs=[]
    for component in ("temporal_dynamics","relationship","preference"):
        before=m71["ablations"][component]["delta_vs_full"]["negative_log_likelihood"]
        after=result["ablations"][component]["delta_vs_full"]["negative_log_likelihood"]
        signs.append(f'<div class="rb-sign-card"><b>{_text(component)}</b><strong>{before:+.3f} → {after:+.3f}</strong><span>M7 removal helped; M8 removal harms · direction did not replicate</span></div>')
    return (
        '<section class="rb-lab"><header class="rb-hero"><div><div class="rb-kicker">M8 / M8.1 · ROLLING + SCALING + ROBUSTNESS</div><h1 class="rb-title">工程跑完，不代表假設成功：新時間軸上，B5 贏了，更多記憶反而把系統帶偏</h1><p class="rb-sub">24 個全新虛構事件，4 個嚴格 cutoff，16 個未參與 M5/M6 開發的測試句；同時跑 B0–B5、8 種歷史量、5 個 seeds 與 M7 sign replication。紅色結果不隱藏，也不重跑追綠。</p></div>'
        f'<div class="rb-stamps"><div class="rb-stamp"><b>{passed} / 8 HYPOTHESES</b><span>scientific gate · predominantly negative</span></div><div class="rb-stamp ok"><b>108 / 108 CALLS</b><span>engineering complete · leakage 0</span></div></div></header><div class="rb-body">'
        f'<div class="rb-metrics">{_metric_cards(result)}</div><div class="rb-label">ROLLING CUTOFF · SAME SYSTEM, DIFFERENT FUTURE WINDOWS</div><div class="rb-roll">{_rolling_cards(result)}</div>'
        f'<div class="rb-label">HISTORY VOLUME · LONGER BAR = WORSE NLL</div><div class="rb-grid"><div class="rb-panel">{_scaling(result)}</div><div class="rb-panel"><b style="color:#c4b5fd;font-size:9px">5 BOOTSTRAP SEEDS · FULL HISTORY</b><div class="rb-seeds" style="margin-top:10px">{_seed_cards(result)}</div><p style="color:#94a3b8;font-size:8px;line-height:1.5;margin-top:10px">Top-1 50.0–68.75%; NLL 2.142–2.944. D2 has best NLL 2.055, while D7 worsens to 2.916. More history is not monotonic evidence.</p></div></div>'
        f'<div class="rb-label">SELECTED CUTOFF · {cutoff} · B1 VS B5 VS OURS</div><div class="rb-compare">{_cases(result,dataset,cutoff)}</div>'
        f'<div class="rb-label">M7 NEGATIVE FINDINGS DO NOT REPLICATE · Δ NLL WHEN COMPONENT IS REMOVED</div><div class="rb-sign">{"".join(signs)}</div>'
        '<div class="rb-boundary"><div style="--tone:#34d399"><b>完成的研究器具</b><span>rolling cutoff、zero leakage、new semantics、B0–B5、8 data volumes、5 seeds、sign replication、immutable failures。</span></div>'
        f'<div style="--tone:#fbbf24"><b>資源沒有藏</b><span>{resources["total_model_calls"]} calls · {resources["prompt_tokens"]+resources["completion_tokens"]:,} tokens · {resources["model_latency_seconds"]:.1f}s model · {resources["numeric_fit_predict_seconds"]:.1f}s numeric。M8 first failure 與 2 次 bounded normalization 全保留。</span></div>'
        '<div style="--tone:#fb7185"><b>現在不能宣稱</b><span>Ours 優於 structured-history LLM、更多記憶必然更好、跨時間穩定、已預測 Uruha 或已還原真人。下一步 M9 是 second-person transfer。</span></div></div></div></section>'
    )
