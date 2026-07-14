#!/usr/bin/env python3
"""Verify and explain the frozen memory provenance/reread V3 experiment."""

import argparse
import json
from collections import Counter
from pathlib import Path

from run_longmemeval_retrieval_benchmark import (
    atomic_write_json,
    canonical_sha256,
    file_sha256,
)


ROOT = Path(__file__).resolve().parent
DEFAULT_REPORT = ROOT / "reports" / "memory_provenance_reread_v3_report.json"
DEFAULT_ANALYSIS_JSON = ROOT / "reports" / "memory_provenance_reread_v3_analysis.json"
DEFAULT_ANALYSIS_MD = ROOT / "reports" / "memory_provenance_reread_v3_analysis.md"
EXPECTED_REPORT_SHA256 = "0d709949ca490c3110970911932d6c716cb39ef6e0c2d96a138869993d122e31"

CONTROL = "full_session_freeform"
PROVENANCE = "provenance_gate_only_freeform"
ADAPTIVE = "adaptive_provenance_reread_freeform"
SPAN = "adaptive_provenance_reread_span_contract"
CONDITIONS = (CONTROL, PROVENANCE, ADAPTIVE, SPAN)

IMPLEMENTATION_PATHS = {
    "runner_sha256": ROOT / "run_memory_provenance_reread_v3.py",
    "provenance_module_sha256": ROOT / "memory_provenance_reread.py",
    "highlight_span_module_sha256": ROOT / "memory_highlight_span_contract.py",
    "attention_module_sha256": ROOT / "memory_utterance_attention.py",
    "ledger_module_sha256": ROOT / "memory_evidence_ledger.py",
    "v1_runner_dependency_sha256": ROOT / "run_memory_utterance_attention_v1.py",
    "ollama_runner_dependency_sha256": ROOT
    / "run_longmemeval_evidence_ledger_development.py",
    "hash_io_dependency_sha256": ROOT / "run_longmemeval_retrieval_benchmark.py",
    "dataset_builder_sha256": ROOT / "build_memory_provenance_reread_cases_v3.py",
    "dataset_sha256": ROOT / "datasets" / "memory_provenance_reread_v3.json",
    "preregistration_sha256": ROOT
    / "configs"
    / "memory_provenance_reread_v3_preregistration.json",
    "metric_recompute_runner_sha256": ROOT
    / "recompute_memory_provenance_reread_v3_metrics.py",
}


def percent(value):
    return f"{100.0 * float(value):.2f}%"


def verify_report(report, report_path=DEFAULT_REPORT):
    metric_audit = report.get("metric_recompute") or {}
    checks = {
        "report_sha256_matches": file_sha256(report_path) == EXPECTED_REPORT_SHA256,
        "report_complete": bool(report.get("complete")),
        "result_count_matches": len(report.get("results") or [])
        == report.get("expected_case_count")
        == report.get("completed_case_count")
        == 48,
        "results_sha256_matches": canonical_sha256(report.get("results") or [])
        == report.get("results_sha256"),
        "decision_rejects_runtime": report.get("decision")
        == "reject_v3_runtime_integration",
        "runtime_not_authorized": not report.get("research_boundary", {}).get(
            "runtime_change_authorized", True
        ),
        "no_model_calls_in_recompute": metric_audit.get("model_calls_made") == 0,
        "responses_unchanged_in_recompute": metric_audit.get("responses_changed")
        is False,
        "dataset_unchanged_in_recompute": metric_audit.get("dataset_changed") is False,
        "prompts_unchanged_in_recompute": metric_audit.get("prompts_changed") is False,
    }
    bound = report.get("implementation_evidence") or {}
    implementation_checks = {
        key: path.is_file() and file_sha256(path) == bound.get(key)
        for key, path in IMPLEMENTATION_PATHS.items()
    }
    checks["implementation_hashes_match"] = all(implementation_checks.values())
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError(f"Frozen V3 report verification failed: {failed}")
    return checks, implementation_checks


def paired_states(results, control, treatment, metric):
    states = Counter()
    wins = []
    losses = []
    for row in results:
        control_pass = bool(row["conditions"][control]["metrics"].get(metric))
        treatment_pass = bool(row["conditions"][treatment]["metrics"].get(metric))
        if control_pass and treatment_pass:
            states["both_pass"] += 1
        elif treatment_pass:
            states["treatment_only"] += 1
            wins.append(row["case_id"])
        elif control_pass:
            states["control_only"] += 1
            losses.append(row["case_id"])
        else:
            states["neither_pass"] += 1
    return {
        **{name: states[name] for name in (
            "both_pass", "treatment_only", "control_only", "neither_pass"
        )},
        "treatment_win_case_ids": wins,
        "treatment_loss_case_ids": losses,
    }


def _answerable_failures(results, condition):
    return [
        row["case_id"]
        for row in results
        if row["gold"]["answerable"]
        and not row["conditions"][condition]["metrics"][
            "answerable_semantic_case_pass"
        ]
    ]


def _case_projection(row, condition):
    artifact = row["conditions"][condition]
    metrics = artifact["metrics"]
    return {
        "case_id": row["case_id"],
        "scenario_id": row["scenario_id"],
        "split": row["split"],
        "capability": row["capability"],
        "position": row["evidence_position"],
        "question": row["question"],
        "response": artifact["response"],
        "semantic_pass": metrics["answerable_semantic_case_pass"],
        "explicit_abstention": metrics["explicit_abstention"],
        "fallback_triggered": metrics["fallback_triggered"],
        "fallback_recovered": metrics["fallback_recovered"],
        "span_errors": metrics.get("span_contract_errors"),
    }


def build_analysis(report, report_path=DEFAULT_REPORT):
    checks, implementation_checks = verify_report(report, report_path)
    results = report["results"]
    summaries = report["summaries"]

    triggered = [
        row
        for row in results
        if row["conditions"][ADAPTIVE]["metrics"]["fallback_triggered"]
    ]
    recovered = [
        row
        for row in triggered
        if row["conditions"][ADAPTIVE]["metrics"]["fallback_recovered"]
    ]
    answerable_triggered = [row for row in triggered if row["gold"]["answerable"]]
    unanswerable_triggered = [row for row in triggered if not row["gold"]["answerable"]]

    provenance_pair = paired_states(
        results, CONTROL, PROVENANCE, "overall_cognitive_case_pass"
    )
    adaptive_pair = paired_states(
        results, PROVENANCE, ADAPTIVE, "overall_cognitive_case_pass"
    )
    span_pair = paired_states(
        results, ADAPTIVE, SPAN, "overall_cognitive_case_pass"
    )

    mug_failures = [
        _case_projection(row, ADAPTIVE)
        for row in answerable_triggered
        if row["scenario_id"] == "dev_mug_current_count"
    ]
    polarity_regressions = [
        _case_projection(row, SPAN)
        for row in results
        if row["case_id"] in span_pair["treatment_loss_case_ids"]
        and row["scenario_id"] == "dev_preharp_violin_ownership"
    ]
    frequency_regressions = [
        _case_projection(row, SPAN)
        for row in results
        if row["case_id"] in span_pair["treatment_loss_case_ids"]
        and row["scenario_id"] == "transfer_takeout_frequency_decrease"
    ]
    span_improvements = [
        _case_projection(row, SPAN)
        for row in results
        if row["case_id"] in span_pair["treatment_win_case_ids"]
    ]

    provenance_gain_rows = [
        row
        for row in results
        if row["case_id"] in provenance_pair["treatment_win_case_ids"]
    ]
    source_admission = {
        condition: {
            "assistant_event_count": sum(
                row["conditions"][condition]["metrics"]["assistant_event_count"]
                for row in results
            ),
            "assistant_fact_admission_rate": summaries[condition][
                "assistant_fact_admission_rate"
            ],
        }
        for condition in CONDITIONS
    }

    cost = {
        "adaptive_minus_provenance_mean_latency_seconds": summaries[ADAPTIVE][
            "mean_latency_seconds"
        ]
        - summaries[PROVENANCE]["mean_latency_seconds"],
        "adaptive_minus_provenance_mean_prompt_tokens": summaries[ADAPTIVE][
            "mean_prompt_tokens"
        ]
        - summaries[PROVENANCE]["mean_prompt_tokens"],
        "span_minus_adaptive_mean_latency_seconds": summaries[SPAN][
            "mean_latency_seconds"
        ]
        - summaries[ADAPTIVE]["mean_latency_seconds"],
        "adaptive_minus_provenance_evidence_recall": summaries[ADAPTIVE][
            "gold_user_evidence_quote_recall"
        ]
        - summaries[PROVENANCE]["gold_user_evidence_quote_recall"],
    }

    return {
        "schema": "uruha_memory_provenance_reread_analysis_v3",
        "source_report": str(report_path.relative_to(ROOT)),
        "source_report_sha256": file_sha256(report_path),
        "source_results_sha256": report["results_sha256"],
        "verification": checks,
        "implementation_verification": implementation_checks,
        "metric_recompute_audit": report["metric_recompute"],
        "condition_summary": {
            condition: {
                "answerable_pass_count": round(
                    36 * summaries[condition]["answerable_semantic_case_pass_rate"]
                ),
                "answerable_total": 36,
                "answerable_pass_rate": summaries[condition][
                    "answerable_semantic_case_pass_rate"
                ],
                "unanswerable_abstention_count": round(
                    12 * summaries[condition][
                        "unanswerable_explicit_abstention_rate"
                    ]
                ),
                "unanswerable_total": 12,
                "unanswerable_abstention_rate": summaries[condition][
                    "unanswerable_explicit_abstention_rate"
                ],
                "overall_pass_count": round(
                    48 * summaries[condition]["overall_cognitive_case_pass_rate"]
                ),
                "overall_total": 48,
                "overall_pass_rate": summaries[condition][
                    "overall_cognitive_case_pass_rate"
                ],
                "false_abstention_rate_on_answerable": summaries[condition][
                    "false_abstention_rate_on_answerable"
                ],
                "evidence_recall": summaries[condition][
                    "gold_user_evidence_quote_recall"
                ],
                "mean_latency_seconds": summaries[condition]["mean_latency_seconds"],
                "mean_prompt_tokens": summaries[condition]["mean_prompt_tokens"],
            }
            for condition in CONDITIONS
        },
        "paired_effects": {
            "provenance_vs_control": provenance_pair,
            "adaptive_vs_provenance": adaptive_pair,
            "span_vs_adaptive": span_pair,
            "formal_statistics": report["paired_analysis"],
        },
        "provenance_gate_attribution": {
            "overall_gain_case_count": len(provenance_gain_rows),
            "gain_answerable_case_count": sum(
                bool(row["gold"]["answerable"]) for row in provenance_gain_rows
            ),
            "gain_unanswerable_case_count": sum(
                not row["gold"]["answerable"] for row in provenance_gain_rows
            ),
            "gain_case_ids": [row["case_id"] for row in provenance_gain_rows],
            "answerable_failure_sets_identical_to_control": (
                _answerable_failures(results, CONTROL)
                == _answerable_failures(results, PROVENANCE)
            ),
            "source_admission": source_admission,
            "interpretation": (
                "The measured P gain came from explicit abstention on all 12 "
                "unanswerable cases, not from improved answerable memory reasoning "
                "or reduced assistant-fact admission."
            ),
        },
        "adaptive_reread": {
            "trigger_count": len(triggered),
            "answerable_trigger_count": len(answerable_triggered),
            "unanswerable_trigger_count": len(unanswerable_triggered),
            "recovery_count": len(recovered),
            "recovery_rate": len(recovered) / len(triggered) if triggered else None,
            "trigger_case_ids": [row["case_id"] for row in triggered],
            "answerable_false_abstentions": mug_failures,
            "cost_delta": cost,
            "interpretation": (
                "The highlighted second read increased evidence recall slightly but "
                "recovered zero answers while adding latency and prompt tokens; it is "
                "not eligible for runtime promotion."
            ),
        },
        "span_contract": {
            "regression_count": len(span_pair["treatment_loss_case_ids"]),
            "improvement_count": len(span_pair["treatment_win_case_ids"]),
            "discourse_marker_polarity_regressions": polarity_regressions,
            "frequency_scalar_regressions": frequency_regressions,
            "grounded_negative_evidence_improvements": span_improvements,
            "interpretation": (
                "The binder helped two incomplete negative answers but caused six "
                "regressions, so its net effect is harmful in V3."
            ),
        },
        "failed_gates": [name for name, passed in report["gates"].items() if not passed],
        "decision": "reject_v3_runtime_integration",
        "causal_conclusions": [
            (
                "Source monitoring is a relevant human-memory function, but this "
                "experiment found no assistant-fact contamination to remove."
            ),
            (
                "A provenance sufficiency gate improved calibrated uncertainty only: "
                "answerable accuracy stayed 31/36 while unanswerable abstention rose "
                "from 0/12 to 12/12."
            ),
            (
                "Adaptive highlighted rereading raised evidence recall from 68.75% "
                "to 72.92%, but this produced no answer recovery in the frozen V3 cases."
            ),
            (
                "The current span contract confuses discourse correction with answer "
                "polarity and cannot resolve frequency words such as twice."
            ),
        ],
        "next_experiment_constraints": [
            "Do not modify runtime from V3; both preregistered promotion gates failed.",
            "Treat all V3 scenarios as consumed development evidence.",
            (
                "Evaluate explicit abstention separately on new untouched cases; do "
                "not attribute its gain to source filtering."
            ),
            (
                "Test a deterministic query-aligned user-turn candidate path against "
                "the mug extraction blind spot before attempting another model reread."
            ),
            (
                "If span binding is revisited, preregister discourse-marker-aware "
                "polarity and frequency-word normalization on new cases."
            ),
        ],
    }


def render_markdown(analysis):
    summary = analysis["condition_summary"]
    labels = {
        CONTROL: "A: full-session freeform",
        PROVENANCE: "P: provenance gate",
        ADAPTIVE: "R: provenance + adaptive reread",
        SPAN: "S: adaptive reread + span contract",
    }
    lines = [
        "# Memory provenance and adaptive reread V3 analysis",
        "",
        "## Decision",
        "",
        "**Reject V3 runtime integration.** The experiment preserves useful negative "
        "evidence instead of promoting a feature merely because one aggregate score rose.",
        "",
        "## Condition results",
        "",
        "| Condition | Answerable | Unanswerable abstention | Overall | Mean latency | Mean prompt tokens |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for condition in CONDITIONS:
        row = summary[condition]
        lines.append(
            f"| {labels[condition]} | {row['answerable_pass_count']}/36 "
            f"({percent(row['answerable_pass_rate'])}) | "
            f"{row['unanswerable_abstention_count']}/12 "
            f"({percent(row['unanswerable_abstention_rate'])}) | "
            f"{row['overall_pass_count']}/48 ({percent(row['overall_pass_rate'])}) | "
            f"{row['mean_latency_seconds']:.3f}s | {row['mean_prompt_tokens']:.1f} |"
        )

    provenance = analysis["provenance_gate_attribution"]
    adaptive = analysis["adaptive_reread"]
    span = analysis["span_contract"]
    lines.extend(
        [
            "",
            "## What actually caused the score changes",
            "",
            f"- P beat A on `{provenance['overall_gain_case_count']}` cases: "
            f"`{provenance['gain_unanswerable_case_count']}` unanswerable and "
            f"`{provenance['gain_answerable_case_count']}` answerable.",
            "- A and P had the same answerable failures. P therefore improved explicit "
            "uncertainty handling, not memory reasoning.",
            "- Every condition admitted zero assistant events, so V3 did not observe "
            "assistant-source contamination.",
            f"- R triggered `{adaptive['trigger_count']}` second reads and recovered "
            f"`{adaptive['recovery_count']}`. Relative to P it added "
            f"`{adaptive['cost_delta']['adaptive_minus_provenance_mean_latency_seconds']:.3f}s` "
            "mean latency and "
            f"`{adaptive['cost_delta']['adaptive_minus_provenance_mean_prompt_tokens']:.1f}` "
            "mean prompt tokens; evidence recall rose by "
            f"`{100.0 * adaptive['cost_delta']['adaptive_minus_provenance_evidence_recall']:.2f} pp` "
            "without changing answer accuracy.",
            f"- S fixed `{span['improvement_count']}` cases but regressed "
            f"`{span['regression_count']}` cases.",
            "",
            "## Localized failures",
            "",
            "| Failure | Cases | Root cause |",
            "|---|---:|---|",
            f"| Mug current count | {len(adaptive['answerable_false_abstentions'])} | "
            "Both full and highlighted extraction missed grounded user evidence; reread "
            "could not recover it. |",
            f"| Pre-harp violin polarity | {len(span['discourse_marker_polarity_regressions'])} | "
            "The binder treated a source sentence's corrective `No` as the answer's polarity. |",
            f"| Takeout frequency relation | {len(span['frequency_scalar_regressions'])} | "
            "The deterministic scalar reader did not resolve `twice`. |",
            "",
            "## Evidence boundary",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in analysis["causal_conclusions"])
    lines.extend(["", "## Next experiment constraints", ""])
    lines.extend(f"- {item}" for item in analysis["next_experiment_constraints"])
    lines.extend(
        [
            "",
            "## Audit",
            "",
            f"- Source report SHA-256: `{analysis['source_report_sha256']}`.",
            f"- Source results SHA-256: `{analysis['source_results_sha256']}`.",
            "- Metric recomputation made `0` model calls and changed no dataset, "
            "prompt, or response.",
            f"- Failed promotion gates: `{', '.join(analysis['failed_gates'])}`.",
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
                "fallback_recovery_count": analysis["adaptive_reread"][
                    "recovery_count"
                ],
                "span_regression_count": analysis["span_contract"][
                    "regression_count"
                ],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
