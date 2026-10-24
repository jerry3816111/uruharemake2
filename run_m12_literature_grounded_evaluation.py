#!/usr/bin/env python3
"""Re-evaluate frozen UruhaBrain evidence with literature-grounded statistics."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from html import escape
import json
from pathlib import Path
from typing import Any

from longitudinal_human_model.statistical_evaluation import compare_conditions


ROOT = Path(__file__).resolve().parent
PROTOCOL_PATH = ROOT / "configs/m12_literature_grounded_evaluation_protocol.json"
RAW_PATH = ROOT / "analysis/m12_literature_grounded_evaluation_result.json"
REPORT_PATH = ROOT / "analysis/m12_literature_grounded_evaluation_report_2026-08-17.md"
DASHBOARD_PATH = ROOT / "analysis/m12_literature_grounded_evaluation_dashboard_2026-08-17.html"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _validate_binding(binding: dict[str, Any]) -> Path:
    path = ROOT / binding["path"]
    if not path.is_file():
        raise FileNotFoundError(path)
    actual = _sha256(path)
    if actual != binding["sha256"]:
        raise RuntimeError(f"frozen artifact hash mismatch: {binding['path']}")
    return path


def _rolling_summary(payload: dict[str, Any]) -> dict[str, Any] | None:
    rolling = payload.get("rolling_metrics")
    if not rolling:
        return None
    rows = [
        {
            "cutoff": cutoff,
            "sample_count": metrics["sample_count"],
            "top1": metrics["top1_accuracy"],
            "brier": metrics["brier_score"],
            "nll": metrics["negative_log_likelihood"],
            "ece_descriptive": metrics["expected_calibration_error"],
        }
        for cutoff, metrics in sorted(rolling.items())
    ]
    return {
        "rows": rows,
        "top1_range": max(row["top1"] for row in rows) - min(row["top1"] for row in rows),
        "nll_range": max(row["nll"] for row in rows) - min(row["nll"] for row in rows),
        "stable": False,
        "reason": "four rows per cutoff are too small for a stability claim; the observed ranges are retained as diagnostics",
    }


def _memory_evaluation(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload["summary"]
    conditions = summary["conditions"]
    system = conditions["uruha_memory"]
    recent = conditions["plain_recent"]
    full = conditions["plain_full"]
    return {
        "turn_count": summary["turn_count"],
        "checkpoint_count": summary["checkpoint_count"],
        "conditions": conditions,
        "system_minus_recent_task_pass": system["task_pass_count"] - recent["task_pass_count"],
        "system_minus_full_task_pass": system["task_pass_count"] - full["task_pass_count"],
        "system_to_full_prompt_token_ratio": (
            system["prompt_tokens"] + system["completion_tokens"]
        ) / (full["prompt_tokens"] + full["completion_tokens"]),
        "system_to_full_latency_ratio": system["latency_seconds"] / full["latency_seconds"],
        "verdict": "bounded_persistence_over_recent_but_no_task_advantage_over_full_context",
        "independent_semantic_holdout": summary["independent_semantic_holdout"],
        "general_llm_superiority_supported": summary["general_llm_superiority_supported"],
        "boundary": "five selected checkpoints in one 50-turn development family; not a LoCoMo-scale or source-independent memory result",
    }


def _faithfulness_evaluation(
    m7: dict[str, Any], m7_1: dict[str, Any], m8: dict[str, Any]
) -> dict[str, Any]:
    explanation = m7["explanation_faithfulness"]
    m8_checks = m8["diagnostic_hypothesis_checks"]
    replication_keys = [
        "m7_preference_removal_nll_improvement_replicates",
        "m7_relationship_removal_nll_improvement_replicates",
        "m7_temporal_removal_nll_improvement_replicates",
    ]
    return {
        "named_intervention_count": len(m7["named_interventions"]),
        "direct_explanation_intervention_count": len(explanation["rows"]),
        "nonzero_probability_effect_rate": explanation["nonzero_probability_effect_rate"],
        "initial_identifiable_component_count": m7["evaluated_ablation_metric_change_count"],
        "post_exposure_component_coverage_count": m7_1["evaluated_ablation_metric_change_count"],
        "post_exposure_component_coverage_complete": m7_1["component_coverage_complete"],
        "m8_ablation_direction_replication": {
            key: bool(m8_checks[key]) for key in replication_keys
        },
        "stable_component_importance_supported": all(m8_checks[key] for key in replication_keys),
        "verdict": "mechanistic_responsiveness_passes_but_component_importance_does_not_replicate",
        "boundary": "changing a model variable changes its output, but this does not validate the variable as a person's private psychological state",
    }


def build_evaluation(*, bootstrap_repetitions: int | None = None) -> dict[str, Any]:
    protocol = _read_json(PROTOCOL_PATH)
    repetitions = bootstrap_repetitions or protocol["statistical_analysis"][
        "paired_bootstrap_repetitions"
    ]
    seed = protocol["statistical_analysis"]["paired_bootstrap_seed"]
    track_results = []
    track_payloads: dict[str, dict[str, Any]] = {}
    for index, track in enumerate(protocol["tracks"]):
        path = _validate_binding(track)
        payload = _read_json(path)
        track_payloads[track["id"]] = payload
        comparison = compare_conditions(
            payload["rows"],
            candidate_condition=track["candidate"],
            baseline_condition=track["baseline"],
            bootstrap_repetitions=repetitions,
            seed=seed + index * 10,
        )
        candidate_metrics = payload["metrics"][track["candidate"]]
        baseline_metrics = payload["metrics"][track["baseline"]]
        track_results.append(
            {
                "id": track["id"],
                "evidence_boundary": track["evidence_boundary"],
                "formal_target_claim": bool(payload.get("formal_target_claim")),
                "comparison": comparison,
                "candidate_ece_descriptive": candidate_metrics[
                    "expected_calibration_error"
                ],
                "baseline_ece_descriptive": baseline_metrics[
                    "expected_calibration_error"
                ],
                "rolling": _rolling_summary(payload),
            }
        )

    auxiliary = {
        key: _read_json(_validate_binding(binding))
        for key, binding in protocol["auxiliary_artifacts"].items()
    }
    candidate_direction_count = sum(
        row["comparison"]["directional_verdict"]
        == "directionally_favors_candidate"
        for row in track_results
    )
    baseline_direction_count = sum(
        row["comparison"]["directional_verdict"]
        == "directionally_favors_baseline"
        for row in track_results
    )
    statistically_candidate_count = sum(
        row["comparison"]["inferential_verdict"]
        == "statistically_favors_candidate"
        for row in track_results
    )
    formal_track_count = sum(row["formal_target_claim"] for row in track_results)
    central_supported = (
        candidate_direction_count == len(track_results)
        and statistically_candidate_count == len(track_results)
        and formal_track_count > 0
    )
    return {
        "schema": "uruha.m12.literature_grounded_evaluation_result.v1",
        "status": "complete_retrospective_evidence_audit",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "protocol": {
            "path": str(PROTOCOL_PATH.relative_to(ROOT)),
            "sha256": _sha256(PROTOCOL_PATH),
            "posthoc_not_preregistered": True,
            "bootstrap_repetitions": repetitions,
        },
        "tracks": track_results,
        "replication": {
            "track_count": len(track_results),
            "directionally_favors_candidate_count": candidate_direction_count,
            "directionally_favors_baseline_count": baseline_direction_count,
            "statistically_favors_candidate_count": statistically_candidate_count,
            "formal_real_person_track_count": formal_track_count,
            "central_same_model_superiority_supported": central_supported,
            "verdict": "not_replicated_and_no_formal_real_person_track",
        },
        "faithfulness": _faithfulness_evaluation(
            auxiliary["m7_ablation"],
            auxiliary["m7_component_coverage"],
            track_payloads["M8_FRESH_SYNTHETIC_ROLLING"],
        ),
        "long_memory": _memory_evaluation(auxiliary["v2_22_long_memory"]),
        "claims": {
            "supported": [
                "The probability, rolling-cutoff, intervention, and memory evaluation instruments are executable and reproducible on hash-bound artifacts.",
                "The current system has bounded long-context persistence over an eight-turn recent-context baseline in the V2.22 development family.",
                "Named feature interventions change the actual model probabilities rather than only a post-hoc explanation string.",
            ],
            "not_supported": [
                "replicated superiority over the strong B5 structured-history LLM baseline",
                "formal Uruha future-behavior prediction",
                "stable cross-dataset causal importance of the current state components",
                "human felt-understanding, naturalness preference, or population validity",
            ],
            "evaluation_complete_for_current_frozen_artifacts": True,
            "central_scientific_hypothesis_pass": False,
        },
        "resource_note": "No model calls were made. M12 recomputes statistics from frozen per-case predictions and therefore adds evaluation evidence, not new prediction samples.",
    }


def _pct(value: float) -> str:
    return f"{100 * value:.1f}%"


def _num(value: float) -> str:
    return f"{value:+.4f}"


def render_markdown(result: dict[str, Any]) -> str:
    track_lines = []
    for track in result["tracks"]:
        comparison = track["comparison"]
        track_lines.append(
            "| {id} | {n} | {bd} [{blo}, {bhi}] | {nd} [{nlo}, {nhi}] | {ad} | {direction} |".format(
                id=track["id"],
                n=comparison["sample_count"],
                bd=_num(comparison["brier"]["mean_delta"]),
                blo=_num(comparison["brier"]["bootstrap_95_ci"][0]),
                bhi=_num(comparison["brier"]["bootstrap_95_ci"][1]),
                nd=_num(comparison["nll"]["mean_delta"]),
                nlo=_num(comparison["nll"]["bootstrap_95_ci"][0]),
                nhi=_num(comparison["nll"]["bootstrap_95_ci"][1]),
                ad=_pct(comparison["top1"]["mean_delta"]),
                direction=comparison["directional_verdict"],
            )
        )
    rolling_lines = []
    for track in result["tracks"]:
        if not track["rolling"]:
            continue
        for row in track["rolling"]["rows"]:
            rolling_lines.append(
                f"| {track['id']} | {row['cutoff']} | {_pct(row['top1'])} | {row['brier']:.4f} | {row['nll']:.4f} |"
            )
    memory = result["long_memory"]
    conditions = memory["conditions"]
    significance_lines = []
    for track in result["tracks"]:
        comparison = track["comparison"]
        significance_lines.append(
            f"- `{track['id']}`：Brier exact p={comparison['brier']['exact_sign_flip_two_sided_p']:.4f}；"
            f"NLL exact p={comparison['nll']['exact_sign_flip_two_sided_p']:.4f}；"
            f"Top-1 McNemar p={comparison['top1']['exact_mcnemar_two_sided_p']:.4f}；"
            f"判定 `{comparison['inferential_verdict']}`。"
        )
    return f"""# M12 論文方法對齊評測報告

日期：2026-08-17
狀態：**已完成目前選定 frozen artifacts 的回溯性總評**
中央優勢結論：**不支持／NOT SUPPORTED**

## 核心結論

這次評測不只比較總平均。每一個 system prediction 都和 B5 在同一事件
上成對比較；主要指標評量完整機率分布；同時報告不確定性，而且有利方向
必須在開發資料、新語義時間線與第二人物三條證據軌重現。

結果不支持中央假說。M6 的方向有利於 hybrid system，但 M8、M9 都有利於
B5 structured-history LLM；三條證據軌都不是正式真人 Uruha 未見未來資料。
因此目前證據**不能證明系統比強 LLM baseline 更好**。

## 成對機率預測比較

差值定義為 `candidate - B5`；Brier／NLL 越低越好，因此負值有利於系統。

| 證據軌 | n | Brier 差值 [95% bootstrap CI] | NLL 差值 [95% bootstrap CI] | Top-1 差值 | 方向 |
|---|---:|---:|---:|---:|---|
{chr(10).join(track_lines)}

- 有利於系統：{result['replication']['directionally_favors_candidate_count']}/{result['replication']['track_count']} 條。
- 有利於 B5：{result['replication']['directionally_favors_baseline_count']}/{result['replication']['track_count']} 條。
- 正式真人資料：{result['replication']['formal_real_person_track_count']} 條。
- 「同模型條件下優勢已重現」：`{str(result['replication']['central_same_model_superiority_supported']).lower()}`。

{chr(10).join(significance_lines)}

這是對已曝光產物的回溯性 audit，所以 p 值是對不確定性的診斷，不是新的
預註冊 confirmatory claim。M9 的 Brier、NLL 成對結果支持 B5；M6 與 M8
沒有提供足夠統計證據判定勝方。

## Rolling cutoff 穩定性

| 證據軌 | Cutoff | Top-1 | Brier | NLL |
|---|---|---:|---:|---:|
{chr(10).join(rolling_lines)}

M8、M9 每個 cutoff 都只有四個案例。大幅波動代表目前沒有穩定性證據，
不能把任何單一 cutoff 的結果當成母體效能的精確估計。

## 解釋忠實度

- 具名 interventions：{result['faithfulness']['named_intervention_count']} 次。
- 直接 top-feature interventions：{result['faithfulness']['direct_explanation_intervention_count']} 次。
- 對機率造成非零變化：{_pct(result['faithfulness']['nonzero_probability_effect_rate'])}。
- Post-exposure 可獨立 ablate 元件：{result['faithfulness']['post_exposure_component_coverage_count']}/10。
- M7 的 preference／relationship／temporal 移除方向在 M8 重現：**0/3**。

結論：trace 確實接到真正的機率計算，但個別心理元件的重要方向沒有跨資料
穩定。這證明的是 computational faithfulness，不是私人心理狀態的真實性。

## 50 輪記憶

| 條件 | 有來源主要回溯 | Strict task | False-memory assertion | 總 tokens | 延遲 |
|---|---:|---:|---:|---:|---:|
| Uruha memory | {conditions['uruha_memory']['primary_source_grounded_recall_count']}/2 | {conditions['uruha_memory']['task_pass_count']}/5 | {conditions['uruha_memory']['false_memory_assertion_count']} | {conditions['uruha_memory']['prompt_tokens'] + conditions['uruha_memory']['completion_tokens']:,} | {conditions['uruha_memory']['latency_seconds']:.2f}s |
| Recent 8 turns | {conditions['plain_recent']['primary_source_grounded_recall_count']}/2 | {conditions['plain_recent']['task_pass_count']}/5 | {conditions['plain_recent']['false_memory_assertion_count']} | {conditions['plain_recent']['prompt_tokens'] + conditions['plain_recent']['completion_tokens']:,} | {conditions['plain_recent']['latency_seconds']:.2f}s |
| Full transcript | {conditions['plain_full']['primary_source_grounded_recall_count']}/2 | {conditions['plain_full']['task_pass_count']}/5 | {conditions['plain_full']['false_memory_assertion_count']} | {conditions['plain_full']['prompt_tokens'] + conditions['plain_full']['completion_tokens']:,} | {conditions['plain_full']['latency_seconds']:.2f}s |

Uruha memory 勝過只看最近八輪的 bounded baseline，但在 strict task 與
full-context LLM 打平，同時使用 {memory['system_to_full_prompt_token_ratio']:.2f}x tokens 與
{memory['system_to_full_latency_ratio']:.2f}x 延遲。這只有五個 checkpoint，且不是獨立 semantic
holdout，因此不能證明通用記憶優勢。

## 論文方法依據

- [Gneiting & Raftery (2007)](https://sites.stat.washington.edu/raftery/Research/PDF/Gneiting2007jasa.pdf): Brier and logarithmic scores as strictly proper scoring rules.
- [Guo et al. (2017)](https://proceedings.mlr.press/v70/guo17a.html): calibration, ECE, reliability diagrams, and temperature scaling.
- [Peyrard et al. (2021)](https://aclanthology.org/2021.acl-long.179/): compare NLP systems on paired instances, not only independent means.
- [Berg-Kirkpatrick et al. (2012)](https://aclanthology.org/D12-1091/): bootstrap-based statistical significance analysis in NLP.
- [Maharana et al. (2024)](https://aclanthology.org/2024.acl-long.747/): long-term conversational memory requires more than one recall item.
- [Liu et al. (2016)](https://aclanthology.org/D16-1230/): word-overlap metrics are poor substitutes for dialogue quality.

## 已完成與尚未完成

目前已完成：

- SHA 綁定、可執行的評測 protocol；
- 每事件成對 proper-score 統計與信賴區間；
- rolling、transfer、intervention、memory、failure 與成本總評；
- 對「是否重現 B5 優勢」給出沒有通過的誠實結論。

仍然缺少：

- 正式 temporal holdout 的 Uruha 行為資料；
- 真人資料上的 replication；
- 自然日文偏好與 felt understanding 的獨立證據；
- 足量 unseen samples 支持精確 calibration 與母體主張。

M12 沒有呼叫模型，只評估 frozen predictions；沒有在看過舊答案後假裝製造
新的 test samples。
"""


def _ci_svg(result: dict[str, Any]) -> str:
    tracks = result["tracks"]
    values = [
        value
        for track in tracks
        for value in track["comparison"]["brier"]["bootstrap_95_ci"]
    ] + [0.0]
    low = min(values)
    high = max(values)
    padding = max(0.05, (high - low) * 0.12)
    low -= padding
    high += padding
    width = 860
    left = 210
    plot_width = 590

    def x(value: float) -> float:
        return left + (value - low) / (high - low) * plot_width

    elements = [
        f"<line x1='{x(0):.1f}' y1='24' x2='{x(0):.1f}' y2='{48 + 62 * len(tracks)}' stroke='#ffcf6b' stroke-width='2'/>",
        f"<text x='{x(0) + 5:.1f}' y='18' fill='#ffcf6b' font-size='11'>0 = no difference</text>",
    ]
    for index, track in enumerate(tracks):
        comparison = track["comparison"]
        mean = comparison["brier"]["mean_delta"]
        ci_low, ci_high = comparison["brier"]["bootstrap_95_ci"]
        y = 58 + index * 62
        color = "#5ce0ad" if mean < 0 else "#ff7184"
        elements.extend(
            [
                f"<text x='8' y='{y + 4}' fill='#eaf3ff' font-size='12'>{escape(track['id'])}</text>",
                f"<line x1='{x(ci_low):.1f}' y1='{y}' x2='{x(ci_high):.1f}' y2='{y}' stroke='{color}' stroke-width='5' stroke-linecap='round'/>",
                f"<circle cx='{x(mean):.1f}' cy='{y}' r='7' fill='{color}'/>",
                f"<text x='810' y='{y + 4}' fill='#9db0c8' font-size='11' text-anchor='end'>{mean:+.3f}</text>",
            ]
        )
    return f"<svg viewBox='0 0 {width} {70 + 62 * len(tracks)}' role='img'>{''.join(elements)}</svg>"


def render_html(result: dict[str, Any]) -> str:
    track_cards = []
    for track in result["tracks"]:
        comparison = track["comparison"]
        cls = "good" if comparison["directional_verdict"] == "directionally_favors_candidate" else "bad"
        track_cards.append(
            f"<article class='track {cls}'><div class='eyebrow'>{escape(track['id'])} · n={comparison['sample_count']}</div>"
            f"<h3>{escape(comparison['directional_verdict'])}</h3>"
            f"<div class='metric'><span>Δ Brier</span><b>{comparison['brier']['mean_delta']:+.4f}</b></div>"
            f"<div class='metric'><span>Δ NLL</span><b>{comparison['nll']['mean_delta']:+.4f}</b></div>"
            f"<div class='metric'><span>Δ Top-1</span><b>{_pct(comparison['top1']['mean_delta'])}</b></div>"
            f"<p>{escape(track['evidence_boundary'])}</p></article>"
        )
    rolling_rows = []
    for track in result["tracks"]:
        if track["rolling"]:
            for row in track["rolling"]["rows"]:
                rolling_rows.append(
                    f"<tr><td>{escape(track['id'])}</td><td>{escape(row['cutoff'])}</td><td>{_pct(row['top1'])}</td><td>{row['brier']:.3f}</td><td>{row['nll']:.3f}</td></tr>"
                )
    memory = result["long_memory"]["conditions"]
    return f"""<!doctype html><html lang='zh-Hant'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>M12 Literature-Grounded Evaluation</title><style>
body{{margin:0;background:#050912;color:#edf5ff;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}}main{{max-width:1180px;margin:auto;padding:34px}}.hero{{background:radial-gradient(circle at 15% 0,#183654,#0a1220 50%,#070b13);border:1px solid #2d4059;border-radius:26px;padding:30px}}.eyebrow{{color:#5bd7ff;font-size:11px;font-weight:800;letter-spacing:.12em}}h1{{font-size:38px;line-height:1.15;margin:10px 0}}.lead{{color:#adc0d6;line-height:1.7;max-width:920px}}.verdict{{display:inline-block;margin-top:14px;padding:9px 13px;border-radius:99px;background:#35121a;border:1px solid #853247;color:#ff9cab;font-weight:800}}h2{{margin-top:32px}}.grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:13px}}.track,.panel{{background:#0b1321;border:1px solid #2c3d52;border-radius:17px;padding:17px}}.track.good{{border-top:4px solid #5ce0ad}}.track.bad{{border-top:4px solid #ff7184}}.track h3{{font-size:15px}}.metric{{display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #203044}}.metric span,.track p,.note{{color:#8fa5be;font-size:12px;line-height:1.55}}.chart{{background:#09111e;border:1px solid #293b51;border-radius:18px;padding:14px;overflow:auto}}svg{{width:100%;min-width:720px}}table{{width:100%;border-collapse:collapse;background:#09111e;border-radius:16px;overflow:hidden}}th,td{{padding:10px;border-bottom:1px solid #213147;text-align:left;font-size:12px}}th{{color:#72dfff}}.memory{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}}.memory b{{font-size:23px}}.boundary{{margin-top:26px;background:#1b1018;border:1px solid #5e334d;border-radius:15px;padding:16px;color:#ddbed2;line-height:1.6}}@media(max-width:820px){{.grid,.memory{{grid-template-columns:1fr}}main{{padding:16px}}h1{{font-size:29px}}}}
</style></head><body><main><section class='hero'><div class='eyebrow'>M12 · LITERATURE-GROUNDED · HASH-BOUND · PAIRED EVALUATION</div><h1>這套系統有沒有比強 LLM 更會預測人？</h1><div class='lead'>用相同事件逐案例比較完整機率分布，不靠「看起來比較像」。主指標採 proper scoring rules，加入 bootstrap、exact paired tests、rolling cutoffs、第二人 transfer、消融與長記憶成本。</div><div class='verdict'>目前答案：沒有得到可重複的優勢證據</div></section><h2>三條證據軌</h2><section class='grid'>{''.join(track_cards)}</section><h2>Δ Brier 與 95% paired bootstrap CI</h2><div class='chart'>{_ci_svg(result)}<div class='note'>左側（負值）有利於系統；右側（正值）有利於 B5。M6 與 M8/M9 的方向相反。</div></div><h2>Rolling cutoff 穩定性</h2><table><thead><tr><th>Track</th><th>Cutoff</th><th>Top-1</th><th>Brier</th><th>NLL</th></tr></thead><tbody>{''.join(rolling_rows)}</tbody></table><h2>50 輪記憶：能力與成本分開</h2><section class='memory'><div class='panel'><div class='eyebrow'>URUHA MEMORY</div><b>{memory['uruha_memory']['task_pass_count']}/5</b><p>strict task · {memory['uruha_memory']['prompt_tokens'] + memory['uruha_memory']['completion_tokens']:,} tokens · {memory['uruha_memory']['latency_seconds']:.1f}s</p></div><div class='panel'><div class='eyebrow'>RECENT 8</div><b>{memory['plain_recent']['task_pass_count']}/5</b><p>strict task · {memory['plain_recent']['prompt_tokens'] + memory['plain_recent']['completion_tokens']:,} tokens · {memory['plain_recent']['latency_seconds']:.1f}s</p></div><div class='panel'><div class='eyebrow'>FULL TRANSCRIPT</div><b>{memory['plain_full']['task_pass_count']}/5</b><p>strict task · {memory['plain_full']['prompt_tokens'] + memory['plain_full']['completion_tokens']:,} tokens · {memory['plain_full']['latency_seconds']:.1f}s</p></div></section><h2>解釋是否真的接到計算？</h2><section class='grid'><div class='panel'><div class='eyebrow'>INTERVENTIONS</div><h3>{result['faithfulness']['named_intervention_count']} 次</h3><p>40/40 top-feature intervention 造成非零機率變化。</p></div><div class='panel'><div class='eyebrow'>COMPONENT COVERAGE</div><h3>{result['faithfulness']['post_exposure_component_coverage_count']}/10</h3><p>元件都能單獨移除；可識別不等於有效。</p></div><div class='panel'><div class='eyebrow'>REPLICATION</div><h3>0/3</h3><p>preference、relationship、temporal 的 M7 方向未在 M8 重現。</p></div></section><div class='boundary'><b>可以主張：</b>評測器、機率輸出、rolling、intervention 和 bounded memory persistence 都可重現。<br><b>不能主張：</b>已比強 B5 更好、已預測一ノ瀬うるは、已驗證真人心理狀態、或真人感覺更被理解。這不是保守措辭，而是目前數據真正給出的研究結論。</div></main></body></html>"""


def main() -> int:
    result = build_evaluation()
    RAW_PATH.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    REPORT_PATH.write_text(render_markdown(result), encoding="utf-8")
    DASHBOARD_PATH.write_text(render_html(result), encoding="utf-8")
    print(json.dumps({
        "status": result["status"],
        "central_same_model_superiority_supported": result["replication"]["central_same_model_superiority_supported"],
        "raw": str(RAW_PATH.relative_to(ROOT)),
        "report": str(REPORT_PATH.relative_to(ROOT)),
        "dashboard": str(DASHBOARD_PATH.relative_to(ROOT)),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
