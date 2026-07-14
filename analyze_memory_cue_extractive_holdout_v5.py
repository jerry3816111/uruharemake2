#!/usr/bin/env python3
"""Verify and explain the untouched V5 memory cue replication."""

import argparse
import json
import re
from collections import Counter
from pathlib import Path

from run_longmemeval_retrieval_benchmark import (
    atomic_write_json,
    canonical_sha256,
    file_sha256,
)


ROOT = Path(__file__).resolve().parent
DEFAULT_REPORT = ROOT / "reports" / "memory_cue_extractive_holdout_v5_report.json"
DEFAULT_ANALYSIS_JSON = (
    ROOT / "reports" / "memory_cue_extractive_holdout_v5_analysis.json"
)
DEFAULT_ANALYSIS_MD = (
    ROOT / "reports" / "memory_cue_extractive_holdout_v5_analysis.md"
)
EXPECTED_REPORT_SHA256 = (
    "602149c93d78ca4163464cb2a021fd255cb8a6fa04609c4d84228a4a97ee4a95"
)
EXPECTED_RESULTS_SHA256 = (
    "36af4799b6da4d6eb75a179e79ef7448f696e4e1f4971f91d72fc3d178f3bd1d"
)
EXPECTED_MODEL_DIGEST = (
    "845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e"
)

CONTROL = "full_session_freeform"
PROVENANCE = "provenance_gate_freeform"
REREAD = "model_reread_fallback"
CUE = "cue_extractive_fallback"
CONDITIONS = (CONTROL, PROVENANCE, REREAD, CUE)

IMPLEMENTATION_PATHS = {
    "v5_runner_sha256": ROOT / "run_memory_cue_extractive_holdout_v5.py",
    "v4_runner_sha256": ROOT / "run_memory_cue_extractive_v4.py",
    "cue_module_sha256": ROOT / "memory_cue_extractive.py",
    "provenance_module_sha256": ROOT / "memory_provenance_reread.py",
    "attention_module_sha256": ROOT / "memory_utterance_attention.py",
    "ledger_module_sha256": ROOT / "memory_evidence_ledger.py",
    "ollama_runner_dependency_sha256": (
        ROOT / "run_longmemeval_evidence_ledger_development.py"
    ),
    "dataset_builder_sha256": ROOT / "build_memory_cue_extractive_holdout_v5.py",
    "dataset_sha256": ROOT / "datasets" / "memory_cue_extractive_holdout_v5.json",
    "preregistration_sha256": (
        ROOT / "configs" / "memory_cue_extractive_holdout_v5_preregistration.json"
    ),
}

TOKEN_RE = re.compile(r"[a-z0-9]+")


def percent(value):
    return f"{100.0 * float(value):.2f}%"


def _find_comparison(report, control, treatment, metric):
    for row in report["paired_analysis"]:
        if (
            row["control"] == control
            and row["treatment"] == treatment
            and row["metric"] == metric
        ):
            return row
    raise ValueError(f"Missing paired comparison: {control} -> {treatment}, {metric}")


def _condition_counts(results, condition):
    answerable = [row for row in results if row["gold"]["answerable"]]
    unanswerable = [row for row in results if not row["gold"]["answerable"]]
    answerable_pass = sum(
        bool(row["conditions"][condition]["metrics"]["answerable_semantic_case_pass"])
        for row in answerable
    )
    abstention_pass = sum(
        bool(
            row["conditions"][condition]["metrics"][
                "unanswerable_explicit_abstention"
            ]
        )
        for row in unanswerable
    )
    overall_pass = sum(
        bool(row["conditions"][condition]["metrics"]["overall_cognitive_case_pass"])
        for row in results
    )
    return {
        "answerable_pass_count": answerable_pass,
        "answerable_total": len(answerable),
        "answerable_pass_rate": answerable_pass / len(answerable),
        "unanswerable_abstention_count": abstention_pass,
        "unanswerable_total": len(unanswerable),
        "unanswerable_abstention_rate": abstention_pass / len(unanswerable),
        "overall_pass_count": overall_pass,
        "overall_total": len(results),
        "overall_pass_rate": overall_pass / len(results),
    }


def _answer_token_coverage(row, response):
    response_tokens = set(TOKEN_RE.findall(response.lower()))
    coverages = []
    for answer_span in row["gold"].get("answer_spans") or []:
        expected = set(TOKEN_RE.findall(answer_span.lower()))
        if expected:
            coverages.append(len(expected & response_tokens) / len(expected))
    return max(coverages, default=0.0)


def _case_projection(row):
    artifact = row["conditions"][CUE]
    metrics = artifact["metrics"]
    return {
        "case_id": row["case_id"],
        "scenario_id": row["scenario_id"],
        "split": row["split"],
        "capability": row["capability"],
        "position": row["evidence_position"],
        "question": row["question"],
        "expected_answer_spans": row["gold"].get("answer_spans") or [],
        "response": artifact["response"],
        "answer_token_coverage": _answer_token_coverage(row, artifact["response"]),
        "gate_sufficient": metrics["gate_sufficient"],
        "fallback_triggered": metrics["fallback_triggered"],
        "required_slot_span_hit": metrics["required_slot_span_hit"],
        "polarity_hit": metrics["polarity_hit"],
        "relation_hit": metrics["relation_hit"],
    }


def verify_report(report, report_path=DEFAULT_REPORT):
    protocol = report.get("protocol") or {}
    results = report.get("results") or []
    dataset_path = ROOT / report.get("dataset_path", "")
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    result_ids = [row["case_id"] for row in results]
    dataset_ids = [row["case_id"] for row in dataset["cases"]]
    failed_gates = {name for name, passed in report["gates"].items() if not passed}
    expected_failed_gates = {
        "cue_vs_provenance_distinct_recovered_scenario_count_at_least_two",
        "cue_recovery_represented_in_both_holdout_splits",
    }

    checks = {
        "report_sha256_matches": file_sha256(report_path) == EXPECTED_REPORT_SHA256,
        "report_complete": bool(report.get("complete")),
        "result_count_matches": len(results)
        == report.get("expected_case_count")
        == report.get("completed_case_count")
        == 72,
        "result_ids_unique_and_match_dataset": len(set(result_ids)) == 72
        and result_ids == dataset_ids,
        "results_sha256_matches": canonical_sha256(results)
        == report.get("results_sha256")
        == EXPECTED_RESULTS_SHA256,
        "dataset_file_sha256_matches": file_sha256(dataset_path)
        == protocol["dataset"]["file_sha256"],
        "dataset_cases_sha256_matches": canonical_sha256(dataset["cases"])
        == protocol["dataset"]["cases_sha256"],
        "model_digest_matches": report.get("model_evidence", {}).get("digest")
        == EXPECTED_MODEL_DIGEST,
        "decision_is_efficiency_only": report.get("decision")
        == "replicated_efficiency_only_no_runtime",
        "quality_and_safety_pass": bool(report.get("quality_and_safety_pass")),
        "only_preregistered_breadth_gates_failed": failed_gates
        == expected_failed_gates,
        "all_gates_did_not_pass": not report.get("all_gates_pass"),
        "runtime_not_authorized": (
            not report.get("research_boundary", {}).get(
                "active_runtime_change_authorized", True
            )
            and not protocol["decision_policy"].get(
                "active_runtime_change_authorized", True
            )
        ),
        "no_official_or_prior_case_reuse": (
            report.get("research_boundary", {}).get("official_benchmark_items_used")
            == 0
            and report.get("research_boundary", {}).get(
                "prior_scenario_or_question_reuse_count"
            )
            == 0
            and protocol["dataset"].get("v1_v2_v3_v4_scenario_or_question_reuse_count")
            == 0
        ),
        "candidate_source_integrity_passed": (
            report["gates"]["all_candidate_context_is_exact_user_source"]
            and report["gates"]["no_assistant_turn_admitted_to_candidate_context"]
        ),
    }
    bound = report.get("implementation_evidence") or {}
    implementation_checks = {
        key: path.is_file() and file_sha256(path) == bound.get(key)
        for key, path in IMPLEMENTATION_PATHS.items()
    }
    checks["implementation_hashes_match"] = all(implementation_checks.values())
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError(f"Frozen V5 report verification failed: {failed}")
    return checks, implementation_checks


def _classify_failures(results):
    failures = []
    for row in results:
        artifact = row["conditions"][CUE]
        metrics = artifact["metrics"]
        if not row["gold"]["answerable"] or metrics["answerable_semantic_case_pass"]:
            continue
        projection = _case_projection(row)
        if (
            metrics["fallback_triggered"]
            and not metrics["candidate_gate_sufficient"]
            and metrics["explicit_abstention"]
        ):
            layer = "candidate_sufficiency_false_negative"
        elif (
            metrics["gate_sufficient"]
            and not metrics["required_slot_span_hit"]
            and projection["answer_token_coverage"] == 1.0
            and metrics["polarity_hit"]
            and metrics["relation_hit"]
        ):
            layer = "exact_span_order_sensitivity"
        elif metrics["gate_sufficient"] and not metrics["required_slot_span_hit"]:
            layer = "answer_realization_incomplete"
        else:
            layer = "other"
        failures.append({"layer": layer, **projection})
    counts = Counter(row["layer"] for row in failures)
    return {
        "count": len(failures),
        "counts": dict(sorted(counts.items())),
        "cases": failures,
    }


def build_analysis(report, report_path=DEFAULT_REPORT):
    checks, implementation_checks = verify_report(report, report_path)
    results = report["results"]
    summaries = report["summaries"]
    counts = {
        condition: {
            **_condition_counts(results, condition),
            "mean_latency_seconds": summaries[condition]["mean_latency_seconds"],
            "mean_prompt_tokens": summaries[condition]["mean_prompt_tokens"],
            "mean_completion_tokens": summaries[condition]["mean_completion_tokens"],
            "position_invariant_scenario_rate": summaries[condition][
                "position_invariant_scenario_rate"
            ],
        }
        for condition in CONDITIONS
    }

    triggered = [
        row
        for row in results
        if row["conditions"][CUE]["metrics"]["fallback_triggered"]
    ]
    answerable_triggered = [row for row in triggered if row["gold"]["answerable"]]
    unanswerable_triggered = [
        row for row in triggered if not row["gold"]["answerable"]
    ]
    candidate_sufficient = [
        row
        for row in triggered
        if row["conditions"][CUE]["metrics"]["candidate_gate_sufficient"]
    ]
    unsafe_gate_rows = [
        row for row in candidate_sufficient if not row["gold"]["answerable"]
    ]
    unsafe_gate_final_abstentions = [
        row
        for row in unsafe_gate_rows
        if row["conditions"][CUE]["metrics"]["unanswerable_explicit_abstention"]
    ]

    e_vs_p_overall = _find_comparison(
        report, PROVENANCE, CUE, "overall_cognitive_case_pass"
    )
    e_vs_p_answerable = _find_comparison(
        report, PROVENANCE, CUE, "answerable_semantic_case_pass"
    )
    e_vs_r_overall = _find_comparison(
        report, REREAD, CUE, "overall_cognitive_case_pass"
    )
    e_vs_r_answerable = _find_comparison(
        report, REREAD, CUE, "answerable_semantic_case_pass"
    )
    latency_saved = (
        summaries[REREAD]["mean_latency_seconds"]
        - summaries[CUE]["mean_latency_seconds"]
    )
    prompt_tokens_saved = (
        summaries[REREAD]["mean_prompt_tokens"]
        - summaries[CUE]["mean_prompt_tokens"]
    )

    return {
        "schema": "uruha_memory_cue_extractive_holdout_analysis_v5",
        "source_report": str(report_path.relative_to(ROOT)),
        "source_report_sha256": file_sha256(report_path),
        "source_results_sha256": report["results_sha256"],
        "verification": checks,
        "implementation_verification": implementation_checks,
        "condition_summary": counts,
        "paired_effects": {
            "cue_vs_provenance": report["paired_states"]["cue_vs_provenance"],
            "cue_vs_provenance_overall": e_vs_p_overall,
            "cue_vs_provenance_answerable": e_vs_p_answerable,
            "cue_vs_reread": report["paired_states"]["cue_vs_reread"],
            "cue_vs_reread_overall": e_vs_r_overall,
            "cue_vs_reread_answerable": e_vs_r_answerable,
        },
        "fallback_attribution": {
            "trigger_count": len(triggered),
            "answerable_trigger_count": len(answerable_triggered),
            "unanswerable_trigger_count": len(unanswerable_triggered),
            "candidate_sufficient_count": len(candidate_sufficient),
            "semantic_recovery_count": report["recovery_audit"]["case_count"],
            "distinct_recovered_scenario_count": report["recovery_audit"][
                "distinct_scenario_count"
            ],
            "recovery_splits": report["recovery_audit"]["splits"],
            "recovery_case_ids": report["recovery_audit"]["case_ids"],
            "candidate_gate_false_sufficient_unanswerable_count": len(
                unsafe_gate_rows
            ),
            "final_abstention_after_false_sufficient_gate_count": len(
                unsafe_gate_final_abstentions
            ),
            "candidate_exact_user_source_rate": summaries[CUE][
                "candidate_context_exact_source_rate"
            ],
            "candidate_assistant_admission_rate": summaries[CUE][
                "candidate_assistant_turn_admission_rate"
            ],
        },
        "cue_vs_reread_efficiency": {
            "mean_latency_seconds_saved": latency_saved,
            "mean_latency_reduction_rate": latency_saved
            / summaries[REREAD]["mean_latency_seconds"],
            "mean_prompt_tokens_saved": prompt_tokens_saved,
            "mean_prompt_token_reduction_rate": prompt_tokens_saved
            / summaries[REREAD]["mean_prompt_tokens"],
        },
        "remaining_answerable_failures": _classify_failures(results),
        "failed_preregistered_gates": [
            name for name, passed in report["gates"].items() if not passed
        ],
        "decision": "preserve_runtime_replication_failed_breadth",
        "runtime_change_authorized": False,
        "claim_strength": "replicated_efficiency_and_local_recovery_only",
        "causal_conclusions": [
            (
                "E 相對 P 多答對 72 題中的 2 題且沒有逐題退步，但兩題只是 "
                "holdout B 同一情境的不同位置，因此沒有重現廣泛回想效果。"
            ),
            (
                "E 對 18/18 個不可回答案例都正確拒答，也沒有混入 assistant 發言；"
                "但候選充分性 gate 本身誤把 6 題判成可回答，是最終回答層再次拒答"
                "才形成最後一道安全防線。"
            ),
            (
                "E 相對模型重讀多通過 3 題、沒有退步，而且延遲與 prompt tokens "
                "都更低；因此本次重現的是效率和局部品質，不是廣泛檢索能力。"
            ),
            (
                "剩餘 16 個可回答失敗分成：6 個 gate 假陰性、7 個回答實現不完整，"
                "以及 3 個固定 span 詞序敏感分數；這三層必須分開評估。"
            ),
        ],
        "next_experiment_constraints": [
            "V5 的預註冊廣度門檻失敗，不得整合進 runtime。",
            "72 個 V5 案例都已是用過的評估證據，之後不得用來調參或修規則。",
            "另建開發集測試通用頻率正規化與完整回答契約，不在 V5 題目上補洞。",
            "固定原本 exact-span 分數，同時預註冊語意等價指標，避免把詞序差異誤判成記憶失敗。",
            "未來任何 runtime 提案都必須使用新的情境不重疊 holdout，並維持明確拒答安全。",
        ],
    }


def render_markdown(analysis):
    labels = {
        CONTROL: "A: 完整 session 自由回答",
        PROVENANCE: "P: 使用者來源 gate",
        REREAD: "R: 模型重新閱讀",
        CUE: "E: 原始使用者句線索回想",
    }
    lines = [
        "# 記憶線索回想 V5 未見資料分析",
        "",
        "## 結論",
        "",
        "**只重現效率與局部回想效果，不進入正式聊天 runtime。** 安全與成本通過，",
        "但兩個新增答對案例都屬於同一情境、同一 holdout，未達預註冊的泛化廣度。",
        "",
        "## 四組結果",
        "",
        "| 組別 | 可回答題 | 不可回答題正確拒答 | 全部 | 跨位置一致 | 平均延遲 | Prompt tokens |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for condition in CONDITIONS:
        row = analysis["condition_summary"][condition]
        lines.append(
            f"| {labels[condition]} | {row['answerable_pass_count']}/54 "
            f"({percent(row['answerable_pass_rate'])}) | "
            f"{row['unanswerable_abstention_count']}/18 "
            f"({percent(row['unanswerable_abstention_rate'])}) | "
            f"{row['overall_pass_count']}/72 ({percent(row['overall_pass_rate'])}) | "
            f"{percent(row['position_invariant_scenario_rate'])} | "
            f"{row['mean_latency_seconds']:.3f}s | {row['mean_prompt_tokens']:.1f} |"
        )

    e_vs_p = analysis["paired_effects"]["cue_vs_provenance"]
    formal = analysis["paired_effects"]["cue_vs_provenance_overall"]
    fallback = analysis["fallback_attribution"]
    efficiency = analysis["cue_vs_reread_efficiency"]
    lines.extend(
        [
            "",
            "## 真正改善了什麼",
            "",
            f"- E 相對 P：`{e_vs_p['treatment_only']}` 勝、"
            f"`{e_vs_p['control_only']}` 敗，總體 `{formal['delta'] * 100:+.2f} pp`。",
            f"- McNemar `p={formal['mcnemar']['p_value']:.3f}`；bootstrap 95% CI "
            f"`[{formal['paired_bootstrap_95_ci'][0] * 100:+.2f}, "
            f"{formal['paired_bootstrap_95_ci'][1] * 100:+.2f}] pp`，不能主張廣泛提升。",
            f"- 回想只涵蓋 `{fallback['distinct_recovered_scenario_count']}` 個情境、"
            f"split=`{', '.join(fallback['recovery_splits'])}`，因此廣度 gate 失敗。",
            f"- 相對模型重讀，E 平均少 `{efficiency['mean_latency_seconds_saved']:.3f}s` "
            f"({percent(efficiency['mean_latency_reduction_rate'])})，少 "
            f"`{efficiency['mean_prompt_tokens_saved']:.1f}` prompt tokens "
            f"({percent(efficiency['mean_prompt_token_reduction_rate'])})。",
            "",
            "## 安全不是單一 gate 的功勞",
            "",
            f"- 最終不可回答題：`18/18` 正確拒答；assistant 來源混入率 "
            f"`{percent(fallback['candidate_assistant_admission_rate'])}`。",
            f"- 但候選充分性 gate 對 `{fallback['candidate_gate_false_sufficient_unanswerable_count']}` "
            "題誤判為可回答；最終回答層再次拒答，才保住安全。",
            "",
            "## 剩餘失敗分層",
            "",
            "| 層級 | 題數 | 意義 |",
            "|---|---:|---|",
        ]
    )
    failure_counts = analysis["remaining_answerable_failures"]["counts"]
    descriptions = {
        "candidate_sufficiency_false_negative": "原句已選到，但 cadence gate 不認得自然頻率說法。",
        "answer_realization_incomplete": "記憶與 gate 正確，最後回答漏掉實體或位置細節。",
        "exact_span_order_sensitivity": "必要詞都在回答中，只因詞序不等於固定 span 而失分；正式分數不回改。",
        "other": "尚未定位。",
    }
    for name in (
        "candidate_sufficiency_false_negative",
        "answer_realization_incomplete",
        "exact_span_order_sensitivity",
        "other",
    ):
        if not failure_counts.get(name):
            continue
        lines.append(
            f"| `{name}` | {failure_counts[name]} | {descriptions[name]} |"
        )

    lines.extend(["", "## 證據邊界", ""])
    lines.extend(f"- {item}" for item in analysis["causal_conclusions"])
    lines.extend(["", "## 下一個實驗的限制", ""])
    lines.extend(f"- {item}" for item in analysis["next_experiment_constraints"])
    lines.extend(
        [
            "",
            "## 稽核",
            "",
            f"- 正式報告 SHA-256：`{analysis['source_report_sha256']}`。",
            f"- 結果陣列 SHA-256：`{analysis['source_results_sha256']}`。",
            "- 72 題 ID、未見資料、模型 digest、frozen V4 方法與所有實作依賴均已核對。",
        ]
    )
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_ANALYSIS_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_ANALYSIS_MD)
    args = parser.parse_args()

    report = json.loads(args.report.read_text(encoding="utf-8"))
    analysis = build_analysis(report, args.report)
    atomic_write_json(args.output_json, analysis)
    args.output_md.write_text(render_markdown(analysis), encoding="utf-8")
    print(
        json.dumps(
            {
                "output_json": str(args.output_json),
                "output_md": str(args.output_md),
                "decision": analysis["decision"],
                "recovered_scenarios": analysis["fallback_attribution"][
                    "distinct_recovered_scenario_count"
                ],
                "remaining_answerable_failures": analysis[
                    "remaining_answerable_failures"
                ]["count"],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
