#!/usr/bin/env python3
"""Verify and explain the frozen cue-driven memory fallback V4 experiment."""

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
DEFAULT_REPORT = ROOT / "reports" / "memory_cue_extractive_v4_report.json"
DEFAULT_ANALYSIS_JSON = ROOT / "reports" / "memory_cue_extractive_v4_analysis.json"
DEFAULT_ANALYSIS_MD = ROOT / "reports" / "memory_cue_extractive_v4_analysis.md"
EXPECTED_REPORT_SHA256 = "b9086660d4387e153a18e9e9c7113b749e3381871cce1fc704606f577a861414"
EXPECTED_RESULTS_SHA256 = "fb5745139d4557363e03676332770512f216eb137f3976f20b45942c2e5e8f98"
EXPECTED_MODEL_DIGEST = (
    "845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e"
)

CONTROL = "full_session_freeform"
PROVENANCE = "provenance_gate_freeform"
REREAD = "model_reread_fallback"
CUE = "cue_extractive_fallback"
CONDITIONS = (CONTROL, PROVENANCE, REREAD, CUE)

IMPLEMENTATION_PATHS = {
    "runner_sha256": ROOT / "run_memory_cue_extractive_v4.py",
    "cue_module_sha256": ROOT / "memory_cue_extractive.py",
    "v3_runner_dependency_sha256": ROOT / "run_memory_provenance_reread_v3.py",
    "provenance_module_sha256": ROOT / "memory_provenance_reread.py",
    "attention_module_sha256": ROOT / "memory_utterance_attention.py",
    "ledger_module_sha256": ROOT / "memory_evidence_ledger.py",
    "ollama_runner_dependency_sha256": ROOT
    / "run_longmemeval_evidence_ledger_development.py",
    "dataset_builder_sha256": ROOT / "build_memory_cue_extractive_cases_v4.py",
    "dataset_sha256": ROOT / "datasets" / "memory_cue_extractive_v4.json",
    "preregistration_sha256": ROOT
    / "configs"
    / "memory_cue_extractive_v4_preregistration.json",
}


def percent(value):
    return f"{100.0 * float(value):.2f}%"


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
        **{
            name: states[name]
            for name in (
                "both_pass",
                "treatment_only",
                "control_only",
                "neither_pass",
            )
        },
        "treatment_win_case_ids": wins,
        "treatment_loss_case_ids": losses,
    }


def _find_comparison(report, control, treatment, metric):
    for row in report["paired_analysis"]:
        if (
            row["control"] == control
            and row["treatment"] == treatment
            and row["metric"] == metric
        ):
            return row
    raise ValueError(f"Missing paired comparison: {control} -> {treatment}, {metric}")


def verify_report(report, report_path=DEFAULT_REPORT):
    results = report.get("results") or []
    protocol = report.get("protocol") or {}
    dataset_path = ROOT / report.get("dataset_path", "")
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    result_ids = [row["case_id"] for row in results]
    dataset_ids = [row["case_id"] for row in dataset["cases"]]
    cue_rows = [
        row["conditions"][CUE]
        for row in results
        if row["conditions"][CUE]["metrics"]["fallback_triggered"]
    ]
    frozen = protocol["frozen_preimplementation_components"]

    checks = {
        "report_sha256_matches": file_sha256(report_path) == EXPECTED_REPORT_SHA256,
        "report_complete": bool(report.get("complete")),
        "result_count_matches": len(results)
        == report.get("expected_case_count")
        == report.get("completed_case_count")
        == 48,
        "result_ids_unique_and_match_dataset": len(set(result_ids)) == 48
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
        "all_preregistered_gates_pass": bool(report.get("all_gates_pass"))
        and all((report.get("gates") or {}).values()),
        "decision_is_untouched_evaluation_only": report.get("decision")
        == "eligible_for_new_untouched_evaluation",
        "runtime_not_authorized": not report.get("research_boundary", {}).get(
            "runtime_change_authorized", True
        ),
        "no_official_or_prior_case_reuse": (
            report.get("research_boundary", {}).get("official_longmemeval_items_used")
            == 0
            and report.get("research_boundary", {}).get("v1_case_reuse_count") == 0
            and report.get("research_boundary", {}).get("v2_case_reuse_count") == 0
            and report.get("research_boundary", {}).get("v3_case_reuse_count") == 0
        ),
        "candidate_rows_exist": bool(cue_rows),
        "candidate_context_exact_user_only": bool(cue_rows)
        and all(
            row["metrics"]["candidate_context_user_source_rate"] == 1.0
            and row["metrics"]["candidate_context_exact_source_rate"] == 1.0
            and row["metrics"]["candidate_assistant_turn_admission_rate"] == 0.0
            for row in cue_rows
        ),
        "frozen_selector_hash_matches": file_sha256(
            ROOT / "memory_utterance_attention.py"
        )
        == frozen["selector"]["module_sha256"],
        "frozen_candidate_gate_hash_matches": file_sha256(
            ROOT / "memory_provenance_reread.py"
        )
        == frozen["candidate_sufficiency_gate"]["module_sha256"],
    }
    bound = report.get("implementation_evidence") or {}
    implementation_checks = {
        key: path.is_file() and file_sha256(path) == bound.get(key)
        for key, path in IMPLEMENTATION_PATHS.items()
    }
    checks["implementation_hashes_match"] = all(implementation_checks.values())
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError(f"Frozen V4 report verification failed: {failed}")
    return checks, implementation_checks


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
        "gate_sufficient": metrics["gate_sufficient"],
        "required_slot_span_hit": metrics["required_slot_span_hit"],
        "polarity_hit": metrics["polarity_hit"],
        "relation_hit": metrics["relation_hit"],
        "fallback_triggered": metrics["fallback_triggered"],
        "fallback_semantic_recovered": metrics.get("fallback_semantic_recovered"),
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
            "position_invariant_scenario_rate": summaries[condition][
                "position_invariant_scenario_rate"
            ],
        }
        for condition in CONDITIONS
    }

    p_vs_a = paired_states(results, CONTROL, PROVENANCE, "overall_cognitive_case_pass")
    e_vs_p = paired_states(results, PROVENANCE, CUE, "overall_cognitive_case_pass")
    e_vs_r = paired_states(results, REREAD, CUE, "overall_cognitive_case_pass")
    e_vs_p_stats = _find_comparison(
        report, PROVENANCE, CUE, "overall_cognitive_case_pass"
    )

    triggered = [
        row
        for row in results
        if row["conditions"][CUE]["metrics"]["fallback_triggered"]
    ]
    answerable_triggered = [row for row in triggered if row["gold"]["answerable"]]
    unanswerable_triggered = [row for row in triggered if not row["gold"]["answerable"]]
    cue_recovered = [
        row
        for row in answerable_triggered
        if row["conditions"][CUE]["metrics"]["fallback_semantic_recovered"]
    ]
    reread_recovered = [
        row
        for row in answerable_triggered
        if row["conditions"][REREAD]["metrics"]["fallback_semantic_recovered"]
    ]
    candidate_sufficient = [
        row
        for row in triggered
        if row["conditions"][CUE]["metrics"]["candidate_gate_sufficient"]
    ]

    cue_failures = [
        row
        for row in results
        if row["gold"]["answerable"]
        and not row["conditions"][CUE]["metrics"]["answerable_semantic_case_pass"]
    ]
    failure_counts = Counter(row["capability"] for row in cue_failures)
    failure_groups = {
        "current_count_scope_mismatch": {
            "count": failure_counts["current_count"],
            "cases": [
                _case_projection(row, CUE)
                for row in cue_failures
                if row["capability"] == "current_count"
            ],
            "root_cause": (
                "The ledger and answer gate passed, but the answer generator narrowed "
                "the remembered water-bottle set against a material qualifier and "
                "refused the grounded count."
            ),
        },
        "previous_frequency_normalization": {
            "count": failure_counts["previous_frequency"],
            "cases": [
                _case_projection(row, CUE)
                for row in cue_failures
                if row["capability"] == "previous_frequency"
            ],
            "root_cause": (
                "The frozen generic sufficiency gate does not normalize the natural "
                "frequency phrase 'three mornings a week', so both fallbacks abstain."
            ),
        },
        "historical_yes_no_answer_contract": {
            "count": failure_counts["historical_yes_no"],
            "cases": [
                _case_projection(row, CUE)
                for row in cue_failures
                if row["capability"] == "historical_yes_no"
            ],
            "root_cause": (
                "One polarity error and three bare 'No.' answers remain. The evidence "
                "was available, but the final answer did not preserve the requested entity."
            ),
        },
    }

    semantic_vectors_identical = all(
        row["conditions"][REREAD]["metrics"]["overall_cognitive_case_pass"]
        == row["conditions"][CUE]["metrics"]["overall_cognitive_case_pass"]
        for row in results
    )
    response_difference_ids = [
        row["case_id"]
        for row in results
        if row["conditions"][REREAD]["response"]
        != row["conditions"][CUE]["response"]
    ]
    latency_saved = (
        summaries[REREAD]["mean_latency_seconds"]
        - summaries[CUE]["mean_latency_seconds"]
    )
    prompt_tokens_saved = (
        summaries[REREAD]["mean_prompt_tokens"]
        - summaries[CUE]["mean_prompt_tokens"]
    )

    return {
        "schema": "uruha_memory_cue_extractive_analysis_v4",
        "source_report": str(report_path.relative_to(ROOT)),
        "source_report_sha256": file_sha256(report_path),
        "source_results_sha256": report["results_sha256"],
        "verification": checks,
        "implementation_verification": implementation_checks,
        "condition_summary": counts,
        "paired_effects": {
            "provenance_vs_control": p_vs_a,
            "cue_vs_provenance": e_vs_p,
            "cue_vs_reread": e_vs_r,
            "cue_vs_provenance_formal": e_vs_p_stats,
        },
        "fallback_attribution": {
            "trigger_count": len(triggered),
            "answerable_trigger_count": len(answerable_triggered),
            "unanswerable_trigger_count": len(unanswerable_triggered),
            "candidate_sufficient_count": len(candidate_sufficient),
            "cue_recovery_count": len(cue_recovered),
            "reread_recovery_count": len(reread_recovered),
            "cue_recovery_case_ids": [row["case_id"] for row in cue_recovered],
            "reread_recovery_case_ids": [row["case_id"] for row in reread_recovered],
            "trigger_case_ids": [row["case_id"] for row in triggered],
            "exact_user_source_rate": summaries[CUE][
                "candidate_context_exact_source_rate"
            ],
            "assistant_admission_rate": summaries[CUE][
                "candidate_assistant_turn_admission_rate"
            ],
        },
        "cue_vs_reread": {
            "semantic_pass_vectors_identical": semantic_vectors_identical,
            "response_difference_count": len(response_difference_ids),
            "response_difference_case_ids": response_difference_ids,
            "mean_latency_seconds_saved": latency_saved,
            "mean_latency_reduction_rate": latency_saved
            / summaries[REREAD]["mean_latency_seconds"],
            "mean_prompt_tokens_saved": prompt_tokens_saved,
            "mean_prompt_token_reduction_rate": prompt_tokens_saved
            / summaries[REREAD]["mean_prompt_tokens"],
        },
        "remaining_answerable_failures": {
            "count": len(cue_failures),
            "groups": failure_groups,
        },
        "decision": "proceed_to_new_untouched_evaluation_only",
        "runtime_change_authorized": False,
        "claim_strength": "weak_positive_development_evidence",
        "causal_conclusions": [
            (
                "E improved P by one of 48 cases (+2.08 percentage points), but the "
                "paired McNemar p-value is 1.0 and the bootstrap interval includes zero."
            ),
            (
                "E and R have identical correctness on all 48 cases. E's demonstrated "
                "advantage is efficiency, not higher accuracy than model rereading."
            ),
            (
                "E recovered one end-position current-time case while preserving 12/12 "
                "unanswerable abstentions and admitting no assistant source."
            ),
            (
                "Ten answerable failures remain in count scope, natural frequency, and "
                "historical yes/no realization; most are not retrieval failures."
            ),
        ],
        "next_experiment_constraints": [
            "Do not modify runtime from V4; the report explicitly authorizes only a new untouched evaluation.",
            "Treat all 48 V4 cases and both pilots as consumed development evidence.",
            "Freeze the V4 implementation and preregister a new scenario-disjoint holdout before running it.",
            "Require more than one paired recovery and report uncertainty before any runtime promotion.",
            "Evaluate answer-contract failures separately from retrieval so a better surface answer is not misattributed to memory retrieval.",
        ],
    }


def render_markdown(analysis):
    labels = {
        CONTROL: "A: full-session freeform",
        PROVENANCE: "P: provenance gate",
        REREAD: "R: model reread fallback",
        CUE: "E: exact user-utterance fallback",
    }
    lines = [
        "# Memory cue-driven extractive fallback V4 analysis",
        "",
        "## Decision",
        "",
        "**Proceed only to a new untouched evaluation. Runtime integration remains "
        "unauthorized.** V4 is weak positive development evidence, not a generalization claim.",
        "",
        "## Condition results",
        "",
        "| Condition | Answerable | Unanswerable abstention | Overall | Mean latency | Mean prompt tokens |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for condition in CONDITIONS:
        row = analysis["condition_summary"][condition]
        lines.append(
            f"| {labels[condition]} | {row['answerable_pass_count']}/36 "
            f"({percent(row['answerable_pass_rate'])}) | "
            f"{row['unanswerable_abstention_count']}/12 "
            f"({percent(row['unanswerable_abstention_rate'])}) | "
            f"{row['overall_pass_count']}/48 ({percent(row['overall_pass_rate'])}) | "
            f"{row['mean_latency_seconds']:.3f}s | {row['mean_prompt_tokens']:.1f} |"
        )

    pair = analysis["paired_effects"]["cue_vs_provenance"]
    formal = analysis["paired_effects"]["cue_vs_provenance_formal"]
    fallback = analysis["fallback_attribution"]
    efficiency = analysis["cue_vs_reread"]
    lines.extend(
        [
            "",
            "## What actually improved",
            "",
            f"- E beat P on `{pair['treatment_only']}` case and lost on "
            f"`{pair['control_only']}`: `{', '.join(pair['treatment_win_case_ids'])}`.",
            f"- The overall gain is `{formal['delta'] * 100:+.2f} pp`; McNemar "
            f"`p={formal['mcnemar']['p_value']:.6f}` and bootstrap 95% CI "
            f"`[{formal['paired_bootstrap_95_ci'][0] * 100:+.2f}, "
            f"{formal['paired_bootstrap_95_ci'][1] * 100:+.2f}] pp`. This is not "
            "statistically persuasive evidence of broad improvement.",
            f"- The fallback triggered on `{fallback['trigger_count']}` cases: "
            f"`{fallback['answerable_trigger_count']}` answerable and "
            f"`{fallback['unanswerable_trigger_count']}` unanswerable. E recovered "
            f"`{fallback['cue_recovery_count']}` answerable case.",
            f"- Candidate sources were `{percent(fallback['exact_user_source_rate'])}` "
            "exact user utterances with "
            f"`{percent(fallback['assistant_admission_rate'])}` assistant admission.",
            "",
            "## E versus model rereading",
            "",
            f"- Correctness vectors identical: `{efficiency['semantic_pass_vectors_identical']}`.",
            f"- E saved `{efficiency['mean_latency_seconds_saved']:.3f}s` mean latency "
            f"({percent(efficiency['mean_latency_reduction_rate'])}) and "
            f"`{efficiency['mean_prompt_tokens_saved']:.1f}` mean prompt tokens "
            f"({percent(efficiency['mean_prompt_token_reduction_rate'])}) relative to R.",
            "- Therefore V4 supports a cheaper fallback, not a more accurate fallback than R.",
            "",
            "## Remaining answerable failures",
            "",
            "| Failure family | Cases | Localized cause |",
            "|---|---:|---|",
        ]
    )
    for group in analysis["remaining_answerable_failures"]["groups"].values():
        lines.append(
            f"| {group['cases'][0]['capability'] if group['cases'] else '-'} | "
            f"{group['count']} | {group['root_cause']} |"
        )

    lines.extend(["", "## Evidence boundary", ""])
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
            "- Frozen dataset, selector, sufficiency gate, implementation, model digest, "
            "and all 48 result IDs verified.",
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
                "cue_recovery_count": analysis["fallback_attribution"][
                    "cue_recovery_count"
                ],
                "remaining_answerable_failure_count": analysis[
                    "remaining_answerable_failures"
                ]["count"],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
