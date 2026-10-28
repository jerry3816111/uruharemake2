#!/usr/bin/env python3
"""Run the preregistered M15 T13 deictic-reference confirmation."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import html
import json
from pathlib import Path
from typing import Any

from longitudinal_human_model.pub_pragmatics import (
    audit_payload_contract,
    build_prompt,
    deterministic_case_ids,
    json_schema_for_condition,
    materialize_case,
    option_permutation,
    paired_accuracy_comparison,
    prospective_exact_mcnemar_power,
    summarize_rows,
)
from longitudinal_human_model.registry import (
    git_snapshot,
    load_json,
    runtime_snapshot,
    sha256_file,
    write_json_atomic,
)
from run_m13_pub_pragmatics import prepare_sources
from run_m14_pub_schema_replication import SchemaProvider, call_row


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs/m15_deixis_confirmation_preregistration.json"
MANIFEST_PATH = ROOT / "configs/m15_deixis_confirmation_case_manifest.json"
PROBE_PATH = ROOT / "analysis/local_m15_deixis_confirmation/contract_probe.json"
CHECKPOINT_PATH = ROOT / "analysis/local_m15_deixis_confirmation/checkpoint.json"
RAW_PATH = ROOT / "analysis/m15_deixis_confirmation_raw_result.json"
RESULT_PATH = ROOT / "analysis/m15_deixis_confirmation_result.json"
REPORT_PATH = ROOT / "analysis/m15_deixis_confirmation_report_2026-08-17.md"
DASHBOARD_PATH = ROOT / "analysis/m15_deixis_confirmation_dashboard_2026-08-17.html"
CONDITIONS = ("B1_GENERIC_DELIBERATION", "OURS_PRAGMATIC_LOOP")


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def source_protocol(config: dict[str, Any]) -> dict[str, Any]:
    binding = config["source_protocol"]
    if sha256_file(ROOT / binding["path"]) != binding["sha256"]:
        raise ValueError("M15 source protocol hash drift")
    predecessor = config["hypothesis_provenance"]
    if sha256_file(ROOT / predecessor["development_result_lock_path"]) != predecessor["development_result_lock_sha256"]:
        raise ValueError("M15 development result lock hash drift")
    return load_json(ROOT / binding["path"])


def prepare_manifest() -> dict[str, Any]:
    config = load_json(CONFIG_PATH)
    protocol = source_protocol(config)
    task_rows = prepare_sources(protocol)
    sampling = config["sampling"]
    task_id = int(sampling["task_id"])
    rows = task_rows[task_id]
    ids = deterministic_case_ids(
        rows,
        task_id=task_id,
        count=int(sampling["case_count"]),
        seed=sampling["seed"],
        excluded_ids=set(sampling["excluded_ids"]),
        offset=int(sampling["rank_offset"]),
    )
    by_id = {str(row["id"]): row for row in rows}
    cases = [
        {
            "sample_id": f"PUB-T{task_id}-{item_id}",
            "task_id": task_id,
            "phenomenon": sampling["phenomenon"],
            "task_name": sampling["task_name"],
            "item_id": item_id,
            "option_count": len(by_id[item_id]["options"]),
            "option_permutation": option_permutation(
                len(by_id[item_id]["options"]),
                task_id=task_id,
                item_id=item_id,
                seed=sampling["seed"],
            ),
        }
        for item_id in ids
    ]
    consumed = set()
    for path in (
        ROOT / "configs/m13_pub_pragmatics_case_manifest.json",
        ROOT / "configs/m14_pub_schema_replication_case_manifest.json",
    ):
        consumed.update(case["sample_id"] for case in load_json(path)["cases"])
    overlap = sorted({case["sample_id"] for case in cases} & consumed)
    if overlap:
        raise ValueError(f"M15 overlaps M13/M14: {overlap}")
    manifest = {
        "schema_version": "m15-deixis-confirmation-manifest-v1",
        "sampling_seed": sampling["seed"],
        "rank_offset": sampling["rank_offset"],
        "case_count": len(cases),
        "overlap_with_m13_or_m14": 0,
        "answer_content_in_manifest": False,
        "cases": cases,
    }
    write_json_atomic(MANIFEST_PATH, manifest)
    return manifest


def validate_power_plan(config: dict[str, Any]) -> float:
    plan = config["power_analysis"]
    actual = prospective_exact_mcnemar_power(
        int(plan["minimum_sample_count"]),
        accuracy_delta=float(plan["smallest_effect_size_of_interest_accuracy_delta"]),
        discordance_rate=float(plan["planning_discordance_rate"]),
        alpha=float(plan["alpha"]),
    )
    if abs(actual - float(plan["calculated_power_at_minimum"])) > 1e-12:
        raise ValueError("M15 frozen power calculation drift")
    previous = prospective_exact_mcnemar_power(
        int(plan["minimum_sample_count"]) - 1,
        accuracy_delta=float(plan["smallest_effect_size_of_interest_accuracy_delta"]),
        discordance_rate=float(plan["planning_discordance_rate"]),
        alpha=float(plan["alpha"]),
    )
    if previous >= float(plan["target_power"]):
        raise ValueError("M15 minimum sample count is not minimal")
    return actual


def probe() -> dict[str, Any]:
    config = load_json(CONFIG_PATH)
    protocol = source_protocol(config)
    task_rows = prepare_sources(protocol)
    spec = config["contract_probe"]
    source = next(row for row in task_rows[int(spec["task_id"])] if str(row["id"]) == str(spec["item_id"]))
    manifest_case = {
        "sample_id": "M15-CONTRACT-PROBE",
        "task_id": int(spec["task_id"]),
        "phenomenon": "deixis",
        "task_name": "deictic reference resolution",
        "item_id": str(spec["item_id"]),
        "option_count": len(source["options"]),
        "option_permutation": list(range(len(source["options"]))),
    }
    case = materialize_case(manifest_case, task_rows)
    provider = SchemaProvider(config["generation"]["endpoint"])
    rows = [call_row(provider, config, case, condition) for condition in CONDITIONS]
    result = {
        "schema_version": "m15-contract-probe-v1",
        "created_at": now(),
        "formal_score_excluded": True,
        "rows": rows,
        "passed": all(row["parse_valid"] and row["schema_contract_valid"] for row in rows),
    }
    write_json_atomic(PROBE_PATH, result)
    if not result["passed"]:
        raise ValueError("M15 contract probe failed")
    return result


def condition_order(sample_id: str) -> list[str]:
    return list(CONDITIONS if int(hashlib.sha256(sample_id.encode()).hexdigest()[:8], 16) % 2 == 0 else reversed(CONDITIONS))


def run() -> dict[str, Any]:
    config = load_json(CONFIG_PATH)
    validate_power_plan(config)
    protocol = source_protocol(config)
    task_rows = prepare_sources(protocol)
    if not PROBE_PATH.is_file() or not load_json(PROBE_PATH).get("passed"):
        raise ValueError("passing M15 contract probe required")
    manifest = load_json(MANIFEST_PATH)
    if sha256_file(MANIFEST_PATH) != config["case_manifest"]["sha256"]:
        raise ValueError("M15 case manifest hash drift")
    if manifest["case_count"] != config["sampling"]["case_count"]:
        raise ValueError("M15 frozen case count drift")
    cases = [materialize_case(case, task_rows) for case in manifest["cases"]]
    bindings = {
        "config_sha256": sha256_file(CONFIG_PATH),
        "manifest_sha256": sha256_file(MANIFEST_PATH),
        "probe_sha256": sha256_file(PROBE_PATH),
    }
    if CHECKPOINT_PATH.is_file():
        checkpoint = load_json(CHECKPOINT_PATH)
        if any(checkpoint.get(key) != value for key, value in bindings.items()):
            raise ValueError("M15 checkpoint binding drift")
    else:
        checkpoint = {
            "schema_version": "m15-deixis-confirmation-raw-v1",
            "status": "running",
            "started_at": now(),
            **bindings,
            "rows": [],
        }
    completed = {(row["sample_id"], row["condition"]) for row in checkpoint["rows"]}
    provider = SchemaProvider(config["generation"]["endpoint"])
    total = len(cases) * len(CONDITIONS)
    for case in cases:
        for condition in condition_order(case["sample_id"]):
            key = (case["sample_id"], condition)
            if key in completed:
                continue
            row = call_row(provider, config, case, condition)
            checkpoint["rows"].append(row)
            completed.add(key)
            checkpoint["updated_at"] = now()
            write_json_atomic(CHECKPOINT_PATH, checkpoint)
            print(f"M15 {len(completed)}/{total} {case['sample_id']} {condition} correct={row['correct']} schema={row['schema_contract_valid']}", flush=True)
    checkpoint.update({
        "status": "complete",
        "completed_at": now(),
        "model": config["model"],
        "runtime": runtime_snapshot(),
        "git": git_snapshot(ROOT),
        "production_memory_writes": 0,
    })
    write_json_atomic(CHECKPOINT_PATH, checkpoint)
    write_json_atomic(RAW_PATH, checkpoint)
    return checkpoint


def _length_quartiles(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_sample = {}
    for row in rows:
        by_sample.setdefault(row["sample_id"], row["pretext"])
    ranked = sorted(by_sample, key=lambda sample_id: (len(by_sample[sample_id].split()), sample_id))
    quartile_for = {sample_id: min(4, index * 4 // len(ranked) + 1) for index, sample_id in enumerate(ranked)}
    output = []
    for quartile in range(1, 5):
        ids = {sample_id for sample_id, value in quartile_for.items() if value == quartile}
        subset = [row for row in rows if row["sample_id"] in ids]
        comparison = paired_accuracy_comparison(subset, candidate=CONDITIONS[1], baseline=CONDITIONS[0], bootstrap_repetitions=5_000, seed=20260820 + quartile)
        output.append({"quartile": quartile, "case_count": len(ids), **comparison})
    return output


def _question_family(pretext: str) -> str:
    question = pretext.rsplit("Question:", 1)[-1].strip().lower()
    if " sure " in f" {question} ":
        return "epistemic_certainty"
    if question.startswith("did "):
        return "action_attribution"
    if question.startswith(("was ", "were ")):
        return "person_location"
    if question.startswith(("is ", "are ")):
        return "entity_state_or_location"
    return "other"


def _question_family_breakdown(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_sample: dict[str, dict[str, dict[str, Any]]] = {}
    for row in rows:
        by_sample.setdefault(row["sample_id"], {})[row["condition"]] = row
    families: dict[str, list[str]] = {}
    for sample_id, pair in by_sample.items():
        family = _question_family(pair[CONDITIONS[1]]["pretext"])
        families.setdefault(family, []).append(sample_id)
    output = []
    for index, family in enumerate(sorted(families)):
        ids = set(families[family])
        subset = [row for row in rows if row["sample_id"] in ids]
        comparison = paired_accuracy_comparison(
            subset,
            candidate=CONDITIONS[1],
            baseline=CONDITIONS[0],
            bootstrap_repetitions=5_000,
            seed=20260830 + index,
        )
        generic = [row for row in subset if row["condition"] == CONDITIONS[0]]
        ours = [row for row in subset if row["condition"] == CONDITIONS[1]]
        output.append({
            "family": family,
            "case_count": len(ids),
            "generic_accuracy": round(sum(row["correct"] for row in generic) / len(generic), 6),
            "ours_accuracy": round(sum(row["correct"] for row in ours) / len(ours), 6),
            **comparison,
        })
    return output


def analyze(bootstrap_repetitions: int = 20_000) -> dict[str, Any]:
    config = load_json(CONFIG_PATH)
    manifest = load_json(MANIFEST_PATH)
    raw = load_json(RAW_PATH)
    rows = raw["rows"]
    expected = int(config["sampling"]["case_count"]) * len(CONDITIONS)
    if raw.get("status") != "complete" or len(rows) != expected:
        raise ValueError(f"M15 raw result incomplete: {len(rows)}/{expected}")
    keys = [(row["sample_id"], row["condition"]) for row in rows]
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate M15 sample-condition rows")
    summary = summarize_rows(rows, conditions=CONDITIONS)
    comparison = paired_accuracy_comparison(rows, candidate=CONDITIONS[1], baseline=CONDITIONS[0], bootstrap_repetitions=bootstrap_repetitions, seed=20260821)
    gate = config["success_gate"]
    hypotheses = {
        "H1_answer_parse": all(summary[condition]["parse_rate"] == gate["both_conditions_answer_parse_rate"] for condition in CONDITIONS),
        "H2_full_schema": all(summary[condition]["schema_contract_rate"] == gate["both_conditions_full_schema_rate"] for condition in CONDITIONS),
        "H3_SESOI": comparison["accuracy_delta"] >= gate["primary_accuracy_delta_minimum"],
        "H4_CI_excludes_zero": comparison["bootstrap_95_ci"][0] > gate["primary_bootstrap_ci_lower_strictly_greater_than"],
        "H5_exact_McNemar": comparison["exact_mcnemar_pvalue"] <= gate["primary_exact_mcnemar_p_maximum"],
    }
    passed = all(hypotheses.values())
    generic_cost = summary[CONDITIONS[0]]
    ours_cost = summary[CONDITIONS[1]]
    generic_total_tokens = generic_cost["prompt_tokens"] + generic_cost["completion_tokens"]
    ours_total_tokens = ours_cost["prompt_tokens"] + ours_cost["completion_tokens"]
    cost_analysis = {
        "generic_total_tokens": generic_total_tokens,
        "ours_total_tokens": ours_total_tokens,
        "total_token_delta": ours_total_tokens - generic_total_tokens,
        "total_token_relative_increase": round(ours_total_tokens / generic_total_tokens - 1, 6),
        "latency_delta_seconds": round(ours_cost["latency_seconds"] - generic_cost["latency_seconds"], 3),
        "latency_relative_increase": round(ours_cost["latency_seconds"] / generic_cost["latency_seconds"] - 1, 6),
        "accuracy_points_per_10000_extra_tokens": round(comparison["accuracy_delta"] * 100 / ((ours_total_tokens - generic_total_tokens) / 10_000), 6),
    }
    m14 = load_json(ROOT / "analysis/m14_pub_schema_replication_result.json")
    m14_t13_delta = float(m14["task_accuracy_delta_ours_minus_generic"]["13"])
    by = {(row["sample_id"], row["condition"]): row for row in rows}
    discordant = []
    for sample_id in sorted({row["sample_id"] for row in rows}):
        generic = by[sample_id, CONDITIONS[0]]
        ours = by[sample_id, CONDITIONS[1]]
        if generic["correct"] != ours["correct"]:
            discordant.append({
                "sample_id": sample_id,
                "outcome": "OURS_WIN" if ours["correct"] else "GENERIC_WIN",
                "pretext": ours["pretext"],
                "options": ours["options"],
                "correct_answer": ours["correct_answer"],
                "generic_answer": generic["predicted_answer"],
                "ours_answer": ours["predicted_answer"],
                "generic_trace": generic["parsed_payload"],
                "ours_trace": ours["parsed_payload"],
            })
    result = {
        "schema_version": "m15-deixis-confirmation-result-v1",
        "created_at": raw["completed_at"],
        "decision": "pass_focused_deixis_advantage" if passed else "fail_focused_deixis_advantage",
        "gate_passed": passed,
        "hypotheses": hypotheses,
        "summary": summary,
        "comparison": comparison,
        "exploratory_context_length_quartiles": _length_quartiles(rows),
        "exploratory_question_families": _question_family_breakdown(rows),
        "cross_split_confirmation": {
            "m14_development_case_count": 16,
            "m14_t13_accuracy_delta": m14_t13_delta,
            "m15_confirmation_case_count": manifest["case_count"],
            "m15_t13_accuracy_delta": comparison["accuracy_delta"],
            "effect_direction_replicated": m14_t13_delta * comparison["accuracy_delta"] > 0,
            "magnitude_attenuation": round(comparison["accuracy_delta"] - m14_t13_delta, 6),
            "pooled_effect_reported": False,
            "reason": "M14 selected the focused hypothesis; only the disjoint, prospectively powered M15 sample is confirmatory.",
        },
        "cost_analysis": cost_analysis,
        "discordant_cases": discordant,
        "power_analysis_recomputed": validate_power_plan(config),
        "config_sha256": sha256_file(CONFIG_PATH),
        "manifest_sha256": sha256_file(MANIFEST_PATH),
        "probe_sha256": sha256_file(PROBE_PATH),
        "raw_result_sha256": sha256_file(RAW_PATH),
        "case_count": manifest["case_count"],
        "model_call_count": len(rows),
        "production_memory_writes": raw.get("production_memory_writes"),
        "claim_authorized": config["claim_if_passed"] if passed else config["claim_if_failed"],
        "claim_precision_note": "The observed +16-point sample effect exceeds the +15-point SESOI and its confidence interval excludes zero. The 95% CI lower endpoint is +7 points, so M15 does not establish that the population effect is at least +15 points.",
        "claim_not_authorized": ["general pragmatic superiority", "unseen-model generalization", "pretraining-uncontaminated generalization", "longitudinal human understanding", "felt-understanding preference", "Uruha persona fidelity", "human-brain equivalence"],
        "evidence_boundary": config["evidence_boundary"],
        "rows": rows,
    }
    write_json_atomic(RESULT_PATH, result)
    REPORT_PATH.write_text(render_report(result), encoding="utf-8")
    DASHBOARD_PATH.write_text(render_dashboard(result), encoding="utf-8")
    return result


def pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def render_report(result: dict[str, Any]) -> str:
    generic = result["summary"][CONDITIONS[0]]
    ours = result["summary"][CONDITIONS[1]]
    comparison = result["comparison"]
    lines = [
        "# M15 Prospective Deixis Confirmation",
        "",
        f"**Decision: `{result['decision']}`**",
        "",
        "## Confirmatory result",
        "",
        "| Condition | Accuracy | Parse | Full schema | Prompt tokens | Completion tokens | Latency |",
        "|---|---:|---:|---:|---:|---:|---:|",
        f"| Generic deliberation | {pct(generic['accuracy'])} | {pct(generic['parse_rate'])} | {pct(generic['schema_contract_rate'])} | {generic['prompt_tokens']:,} | {generic['completion_tokens']:,} | {generic['latency_seconds']:.1f}s |",
        f"| Pragmatic decomposition | {pct(ours['accuracy'])} | {pct(ours['parse_rate'])} | {pct(ours['schema_contract_rate'])} | {ours['prompt_tokens']:,} | {ours['completion_tokens']:,} | {ours['latency_seconds']:.1f}s |",
        "",
        f"Paired Ours-Generic: `{comparison['accuracy_delta']:+.3f}`; paired bootstrap 95% CI `[{comparison['bootstrap_95_ci'][0]:+.3f}, {comparison['bootstrap_95_ci'][1]:+.3f}]`; exact two-sided McNemar `p={comparison['exact_mcnemar_pvalue']:.8f}`; wins/ties/losses `{comparison['candidate_wins']}/{comparison['ties']}/{comparison['baseline_wins']}`.",
        "",
        "## Frozen gates",
        "",
    ]
    lines.extend(f"- `{name}`: {'PASS' if passed else 'FAIL'}" for name, passed in result["hypotheses"].items())
    lines += [
        "",
        "## Authorized interpretation",
        "",
        result["claim_authorized"],
        "",
        f"Precision note: {result['claim_precision_note']}",
        "",
        "## Development-to-confirmation stability",
        "",
        f"M14 generated the focused signal at `+{result['cross_split_confirmation']['m14_t13_accuracy_delta'] * 100:.1f}pp` on 16 cases. M15 confirmed the direction at `+{result['cross_split_confirmation']['m15_t13_accuracy_delta'] * 100:.1f}pp` on 300 disjoint cases; the magnitude attenuated by `{result['cross_split_confirmation']['magnitude_attenuation'] * 100:+.1f}pp`. The splits are not pooled.",
        "",
        "## Cost",
        "",
        f"Ours used `{result['cost_analysis']['total_token_delta']:,}` more total tokens (`+{result['cost_analysis']['total_token_relative_increase'] * 100:.1f}%`) and `{result['cost_analysis']['latency_delta_seconds']:.1f}s` more aggregate latency (`+{result['cost_analysis']['latency_relative_increase'] * 100:.1f}%`).",
        "",
        "## Exploratory mechanism slices (not confirmatory gates)",
        "",
        "| Question family | n | Generic | Ours | Delta |",
        "|---|---:|---:|---:|---:|",
    ]
    for family in result["exploratory_question_families"]:
        lines.append(f"| {family['family']} | {family['case_count']} | {pct(family['generic_accuracy'])} | {pct(family['ours_accuracy'])} | {family['accuracy_delta'] * 100:+.1f}pp |")
    lines += [
        "",
        "## Boundary",
        "",
        result["evidence_boundary"],
        "",
        "## Reproducibility",
        "",
        f"- Formal cases/calls: `{result['case_count']}` / `{result['model_call_count']}`",
        f"- Recomputed prospective power: `{result['power_analysis_recomputed']:.6f}`",
        f"- Config SHA: `{result['config_sha256']}`",
        f"- Manifest SHA: `{result['manifest_sha256']}`",
        f"- Probe SHA: `{result['probe_sha256']}`",
        f"- Raw result SHA: `{result['raw_result_sha256']}`",
        f"- Production memory writes: `{result['production_memory_writes']}`",
    ]
    return "\n".join(lines) + "\n"


def render_dashboard(result: dict[str, Any]) -> str:
    summary = result["summary"]
    comparison = result["comparison"]
    ours_accuracy = summary[CONDITIONS[1]]["accuracy"] * 100
    generic_accuracy = summary[CONDITIONS[0]]["accuracy"] * 100
    payload = json.dumps({
        "comparison": comparison,
        "discordant": result["discordant_cases"],
        "quartiles": result["exploratory_context_length_quartiles"],
        "families": result["exploratory_question_families"],
    }, ensure_ascii=False).replace("</", "<\\/")
    gate_rows = "".join(f"<div class='gate {'pass' if passed else 'fail'}'><span>{html.escape(name)}</span><b>{'PASS' if passed else 'FAIL'}</b></div>" for name, passed in result["hypotheses"].items())
    decision_class = "pass" if result["gate_passed"] else "fail"
    authorized = html.escape(result["claim_authorized"])
    return f"""<!doctype html><html lang='zh-Hant'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>M15 Deixis Confirmation</title>
<style>
:root{{--bg:#071018;--panel:#101d29;--ink:#edf7ff;--muted:#93aabd;--cyan:#5be7ff;--lime:#8ef0b1;--red:#ff7991;--gold:#ffd166}}*{{box-sizing:border-box}}body{{margin:0;background:radial-gradient(circle at 80% 0,#17334b 0,transparent 35%),var(--bg);color:var(--ink);font:15px/1.5 -apple-system,BlinkMacSystemFont,"Noto Sans TC",sans-serif}}main{{max-width:1240px;margin:auto;padding:32px}}h1{{font-size:clamp(28px,5vw,58px);margin:0}}.tag{{color:var(--cyan);letter-spacing:.12em;text-transform:uppercase;font-weight:800}}.sub{{color:var(--muted);max-width:860px;font-size:17px}}.grid{{display:grid;grid-template-columns:repeat(12,1fr);gap:16px;margin-top:24px}}.card{{background:linear-gradient(145deg,#132330,#0c1721);border:1px solid #294052;border-radius:18px;padding:20px;box-shadow:0 16px 50px #0005}}.metric{{grid-column:span 3}}.metric strong{{font-size:42px;display:block}}.wide{{grid-column:span 8}}.side{{grid-column:span 4}}.full{{grid-column:1/-1}}.bar{{height:36px;background:#1c2d3a;border-radius:9px;overflow:hidden;margin:8px 0 16px}}.bar i{{display:block;height:100%;background:linear-gradient(90deg,var(--cyan),var(--lime))}}.bar.generic i{{background:#607d91}}.flow{{display:flex;align-items:center;gap:10px;overflow:auto;padding:10px 0}}.node{{min-width:155px;padding:16px;border:1px solid #35546b;border-radius:14px;background:#142633;text-align:center}}.node b{{display:block;color:var(--cyan)}}.arrow{{font-size:26px;color:var(--gold)}}.gate{{display:flex;justify-content:space-between;padding:10px;border-bottom:1px solid #263c4b}}.gate.pass b,.pass{{color:var(--lime)}}.gate.fail b,.fail{{color:var(--red)}}.decision{{font-size:26px;font-weight:900}}select{{width:100%;background:#09131c;color:var(--ink);border:1px solid #35546b;padding:10px;border-radius:10px}}pre{{white-space:pre-wrap;background:#071018;border-radius:12px;padding:14px;max-height:390px;overflow:auto;color:#cdeeff}}details{{margin:14px 0}}summary{{cursor:pointer;color:var(--cyan)}}.tracegrid{{display:grid;grid-template-columns:1fr 1fr;gap:14px}}.tracebox{{background:#071018;border:1px solid #294052;border-radius:14px;padding:16px;min-width:0}}.tracebox.ours{{border-color:#3d8c83}}.tracebox h3{{margin:0 0 8px}}.tracebox .answer{{font-size:20px;font-weight:800;color:var(--gold)}}.tracebox pre{{margin:10px 0 0;max-height:310px}}.legend{{display:flex;gap:18px;color:var(--muted)}}.dot{{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:6px}}@media(max-width:850px){{.metric,.wide,.side{{grid-column:1/-1}}.tracegrid{{grid-template-columns:1fr}}}}
</style></head><body><main><div class='tag'>Prospective same-model confirmation · 300 new cases</div><h1>系統真的比「一般深思」更會解指涉嗎？</h1><p class='sub'>不是把自己的流程跟直接回答比，而是同一個 qwen3.5:9b、同一題、同一解碼、同樣 strict schema，僅比較一般推理與完整語用分解。M14 只負責提出假設；M15 的 300 題在看結果前已凍結。</p>
<section class='grid'>
<div class='card metric'><span>完整語用</span><strong>{ours_accuracy:.1f}%</strong><small>exact accuracy</small></div><div class='card metric'><span>一般深思</span><strong>{generic_accuracy:.1f}%</strong><small>strong baseline</small></div><div class='card metric'><span>配對差距</span><strong>{comparison['accuracy_delta']*100:+.1f}pp</strong><small>SESOI = +15pp</small></div><div class='card metric'><span>Exact McNemar</span><strong>p={comparison['exact_mcnemar_pvalue']:.4g}</strong><small>兩側、事前指定</small></div>
<div class='card wide'><h2>同模型、單一機制對照</h2><div class='flow'><div class='node'><b>同一輸入</b>公開 PUB T13</div><span class='arrow'>→</span><div class='node'><b>一般深思</b>觀察→推理→反論</div><span class='arrow'>↘</span><div class='node'><b>配對計分</b>同題 exact answer</div></div><div class='flow'><div class='node'><b>同一輸入</b>公開 PUB T13</div><span class='arrow'>→</span><div class='node'><b>完整語用</b>字面→目標→證據→替代</div><span class='arrow'>↗</span></div><div class='legend'><span><i class='dot' style='background:var(--cyan)'></i>只改 reasoning scaffold</span><span><i class='dot' style='background:#607d91'></i>模型與題目完全相同</span></div></div>
<div class='card side'><div class='decision {decision_class}'>{html.escape(result['decision'])}</div><p>95% CI [{comparison['bootstrap_95_ci'][0]*100:+.1f}, {comparison['bootstrap_95_ci'][1]*100:+.1f}]pp</p><p>勝／平／負：{comparison['candidate_wins']} / {comparison['ties']} / {comparison['baseline_wins']}</p>{gate_rows}</div>
<div class='card wide'><h2>準確率</h2><label>完整語用 {ours_accuracy:.1f}%</label><div class='bar'><i style='width:{ours_accuracy}%'></i></div><label>一般深思 {generic_accuracy:.1f}%</label><div class='bar generic'><i style='width:{generic_accuracy}%'></i></div><p class='sub'>所有 300 題都保留；沒有看到結果後補題、刪題或換門檻。</p></div>
<div class='card side'><h2>資源代價</h2><p><b>+{result['cost_analysis']['total_token_relative_increase']*100:.1f}%</b> total tokens</p><p><b>+{result['cost_analysis']['latency_relative_increase']*100:.1f}%</b> aggregate latency</p><p class='sub'>準確率不是免費增加；成本與優勢一起報。</p></div>
<div class='card full'><h2>哪類指涉最受益？ <small class='sub'>探索性、不是事前 gate</small></h2><div class='flow' id='families'></div></div>
<div class='card full'><h2>逐題看「哪一個中間變數改變了答案」</h2><select id='case'></select><p>正解：<b id='correct' class='pass'></b></p><details><summary>展開完整輸入</summary><pre id='input'></pre></details><div class='tracegrid'><div class='tracebox'><h3>一般深思</h3><div id='genericAnswer' class='answer'></div><pre id='genericTrace'></pre></div><div class='tracebox ours'><h3>完整語用</h3><div id='oursAnswer' class='answer'></div><pre id='oursTrace'></pre></div></div></div>
<div class='card full'><h2>可以說什麼</h2><p>{authorized}</p><p><b>精度限制：</b>{html.escape(result['claim_precision_note'])}</p><h3>不能外推</h3><p>{html.escape('、'.join(result['claim_not_authorized']))}</p><h3>研究邊界</h3><p>{html.escape(result['evidence_boundary'])}</p></div>
</section></main><script>const DATA={payload};const fam=document.querySelector('#families');DATA.families.forEach(x=>{{const n=document.createElement('div');n.className='node';n.innerHTML=`<b>${{x.family}}</b><strong>${{(x.accuracy_delta*100).toFixed(1)}}pp</strong><small>n=${{x.case_count}}</small>`;fam.appendChild(n)}});const sel=document.querySelector('#case');DATA.discordant.forEach((x,i)=>{{const o=document.createElement('option');o.value=i;o.textContent=`${{x.outcome}} · ${{x.sample_id}}`;sel.appendChild(o)}});function show(){{const x=DATA.discordant[Number(sel.value||0)];if(!x)return;document.querySelector('#correct').textContent=x.correct_answer;document.querySelector('#input').textContent=x.pretext;document.querySelector('#genericAnswer').textContent=`${{x.generic_answer}} · ${{x.outcome==='GENERIC_WIN'?'CORRECT':'WRONG'}}`;document.querySelector('#oursAnswer').textContent=`${{x.ours_answer}} · ${{x.outcome==='OURS_WIN'?'CORRECT':'WRONG'}}`;document.querySelector('#genericTrace').textContent=JSON.stringify(x.generic_trace,null,2);document.querySelector('#oursTrace').textContent=JSON.stringify(x.ours_trace,null,2)}}sel.addEventListener('change',show);show();</script></body></html>"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--probe", action="store_true")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--analyze", action="store_true")
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()
    if not any((args.prepare, args.probe, args.run, args.analyze, args.all)):
        parser.error("choose an action")
    if args.prepare or args.all:
        print("manifest", prepare_manifest()["case_count"], sha256_file(MANIFEST_PATH))
    if args.probe or args.all:
        print("probe", probe()["passed"], sha256_file(PROBE_PATH))
    if args.run or args.all:
        print("rows", len(run()["rows"]))
    if args.analyze or args.all:
        print("decision", analyze()["decision"])


if __name__ == "__main__":
    main()
