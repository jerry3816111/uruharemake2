#!/usr/bin/env python3
"""Verify and localize failures in the frozen memory highlight/span V2 report."""

import argparse
import json
from collections import Counter
from pathlib import Path

from run_longmemeval_retrieval_benchmark import atomic_write_json, canonical_sha256, file_sha256


ROOT = Path(__file__).resolve().parent
DEFAULT_REPORT = ROOT / "reports" / "memory_highlight_span_v2_report.json"
DEFAULT_ANALYSIS_JSON = ROOT / "reports" / "memory_highlight_span_v2_analysis.json"
DEFAULT_ANALYSIS_MD = ROOT / "reports" / "memory_highlight_span_v2_analysis.md"

CONTROL = "full_session_freeform"
HIGHLIGHT = "highlighted_full_session_freeform"
SPAN = "highlighted_full_session_span_contract"

IMPLEMENTATION_PATHS = {
    "runner_sha256": ROOT / "run_memory_highlight_span_v2.py",
    "highlight_span_module_sha256": ROOT / "memory_highlight_span_contract.py",
    "attention_module_sha256": ROOT / "memory_utterance_attention.py",
    "ledger_module_sha256": ROOT / "memory_evidence_ledger.py",
    "v1_runner_dependency_sha256": ROOT / "run_memory_utterance_attention_v1.py",
    "ollama_runner_dependency_sha256": ROOT / "run_longmemeval_evidence_ledger_development.py",
    "hash_io_dependency_sha256": ROOT / "run_longmemeval_retrieval_benchmark.py",
    "dataset_builder_sha256": ROOT / "build_memory_highlight_span_cases_v2.py",
    "dataset_sha256": ROOT / "datasets" / "memory_highlight_span_v2.json",
    "preregistration_sha256": (
        ROOT / "configs" / "memory_highlight_span_v2_preregistration.json"
    ),
}


def percent(value):
    return f"{100.0 * float(value):.2f}%"


def verify_report(report):
    checks = {
        "report_complete": bool(report.get("complete")),
        "result_count_matches": len(report.get("results") or [])
        == report.get("expected_case_count")
        == 36,
        "results_sha256_matches": canonical_sha256(report.get("results") or [])
        == report.get("results_sha256"),
        "official_items_zero": report.get("research_boundary", {}).get(
            "official_longmemeval_items_used"
        )
        == 0,
        "v1_cases_not_reused": report.get("research_boundary", {}).get(
            "v1_case_reuse_count"
        )
        == 0,
        "consumed_heldout_not_reused": not report.get("research_boundary", {}).get(
            "consumed_heldout_reused", True
        ),
        "runtime_not_authorized": not report.get("research_boundary", {}).get(
            "runtime_change_authorized", True
        ),
    }
    bound = report.get("implementation_evidence") or {}
    implementation_checks = {
        key: file_sha256(path) == bound.get(key)
        for key, path in IMPLEMENTATION_PATHS.items()
    }
    checks["implementation_hashes_match"] = all(implementation_checks.values())
    if not all(checks.values()):
        failed = [name for name, passed in checks.items() if not passed]
        raise ValueError(f"Frozen report verification failed: {failed}")
    return checks, implementation_checks


def classify_failure(row, condition_id):
    artifact = row["conditions"][condition_id]
    metrics = artifact["metrics"]
    if metrics["semantic_case_pass"]:
        return "semantic_pass"
    generation_text = str((artifact["note"].get("generation") or {}).get("text") or "")
    facts = ((artifact["note"].get("evidence") or {}).get("facts") or [])
    if "<memory-highlight" in generation_text and not metrics["grounded_quote_pass"]:
        return "controller_markup_copied_into_quote"
    if facts and all(fact.get("source_role") == "assistant" for fact in facts):
        return "assistant_acknowledgement_misread_as_user_fact"
    if not metrics["ledger_grounded"]:
        return "upstream_evidence_or_ledger_missing"
    if condition_id == SPAN and not metrics.get("span_contract_valid"):
        return "span_contract_invalid"
    return "answer_semantic_miss"


def build_analysis(report):
    checks, implementation_checks = verify_report(report)
    results = report["results"]
    paired_states = Counter()
    evidence_union_hits = 0
    failure_rows = []
    categories = Counter()
    for row in results:
        control_pass = row["conditions"][CONTROL]["metrics"]["semantic_case_pass"]
        highlight_pass = row["conditions"][HIGHLIGHT]["metrics"]["semantic_case_pass"]
        if control_pass and highlight_pass:
            paired_states["both_pass"] += 1
        elif control_pass:
            paired_states["control_only"] += 1
        elif highlight_pass:
            paired_states["highlight_only"] += 1
        else:
            paired_states["neither_pass"] += 1
        evidence_union_hits += bool(
            row["conditions"][CONTROL]["metrics"]["gold_evidence_quote_recall"] > 0
            or row["conditions"][HIGHLIGHT]["metrics"]["gold_evidence_quote_recall"] > 0
        )
        for condition in (CONTROL, HIGHLIGHT, SPAN):
            category = classify_failure(row, condition)
            categories[category] += 1
            if category == "semantic_pass":
                continue
            artifact = row["conditions"][condition]
            failure_rows.append(
                {
                    "case_id": row["case_id"],
                    "split": row["split"],
                    "capability": row["capability"],
                    "position": row["evidence_position"],
                    "condition": condition,
                    "category": category,
                    "response": artifact["response"],
                    "note_generation": (artifact["note"].get("generation") or {}).get(
                        "text"
                    ),
                    "contract_errors": artifact["metrics"].get("span_contract_errors"),
                }
            )

    span_upstream_available = [
        row
        for row in results
        if row["conditions"][SPAN]["metrics"]["ledger_grounded"]
    ]
    conditional_contract_valid = sum(
        bool(row["conditions"][SPAN]["metrics"]["span_contract_valid"])
        for row in span_upstream_available
    )
    conditional_contract_semantic = sum(
        bool(row["conditions"][SPAN]["metrics"]["semantic_case_pass"])
        for row in span_upstream_available
    )
    highlight_summary = report["summaries"][HIGHLIGHT]
    span_summary = report["summaries"][SPAN]
    return {
        "schema": "uruha_memory_highlight_span_analysis_v2",
        "source_report": str(DEFAULT_REPORT.relative_to(ROOT)),
        "source_results_sha256": report["results_sha256"],
        "verification": checks,
        "implementation_verification": implementation_checks,
        "overall": {
            condition: {
                "semantic_case_pass_rate": report["summaries"][condition][
                    "semantic_case_pass_rate"
                ],
                "gold_evidence_quote_recall": report["summaries"][condition][
                    "gold_evidence_quote_recall"
                ],
                "position_invariant_scenario_rate": report["summaries"][condition][
                    "position_invariant_scenario_rate"
                ],
            }
            for condition in (CONTROL, HIGHLIGHT, SPAN)
        },
        "attention_integrity": {
            "target_utterance_recall": highlight_summary["attention_selection_recall"],
            "selection_precision": highlight_summary["attention_selection_precision"],
            "full_context_restoration_rate": highlight_summary[
                "full_context_restoration_rate"
            ],
            "controller_markup_leak_case_count": sum(
                row["category"] == "controller_markup_copied_into_quote"
                and row["condition"] == HIGHLIGHT
                for row in failure_rows
            ),
        },
        "paired_complementarity": {
            **dict(sorted(paired_states.items())),
            "either_control_or_highlight_pass_count": sum(
                count
                for state, count in paired_states.items()
                if state != "neither_pass"
            ),
            "evidence_union_coverage_count": evidence_union_hits,
            "total": len(results),
        },
        "span_contract": {
            "overall_valid_rate": span_summary["span_contract_valid_rate"],
            "upstream_available_count": len(span_upstream_available),
            "valid_when_upstream_available_count": conditional_contract_valid,
            "valid_when_upstream_available_rate": (
                conditional_contract_valid / len(span_upstream_available)
                if span_upstream_available
                else 0.0
            ),
            "semantic_when_upstream_available_count": conditional_contract_semantic,
            "semantic_when_upstream_available_rate": (
                conditional_contract_semantic / len(span_upstream_available)
                if span_upstream_available
                else 0.0
            ),
        },
        "failure_categories": dict(sorted(categories.items())),
        "failure_rows": failure_rows,
        "paired_analysis": report["paired_analysis"],
        "gates": report["gates"],
        "decision": "reject_v2_runtime_integration",
        "causal_conclusions": [
            (
                "Keeping the full session prevented the nine extraction losses seen in V1, but "
                "inline highlight markup was copied into one otherwise correct quote and was "
                "properly rejected by source grounding."
            ),
            (
                "Highlighting fixed one control failure where an assistant acknowledgement was "
                "misread as the user's appointment time, but introduced one different transfer "
                "failure, so its paired net semantic gain was zero."
            ),
            (
                "Control and highlight failures were complementary: at least one path had the "
                "answer-bearing evidence in all 36 cases. This supports evidence arbitration or "
                "a confidence-triggered second read, not unconditional trust in either path."
            ),
            (
                "The controller-owned span contract was valid and semantically correct in all "
                "35 cases with an upstream ledger, including same-quote comparisons and explicit "
                "negation, but it cannot recover evidence that extraction discarded."
            ),
        ],
        "next_experiment_constraints": [
            "Use new scenarios; V2 cases are consumed development evidence.",
            (
                "Strip only controller-owned highlight tags from generated quotes before exact "
                "grounding, and accept the repair only when the stripped quote aligns to source."
            ),
            (
                "Add a provenance sufficiency check that distrusts assistant acknowledgements as "
                "user-memory values and triggers an attention-guided second read."
            ),
            (
                "Keep the span contract after evidence arbitration, because its conditional "
                "35/35 result does not justify removing it."
            ),
            "Measure the extra latency and token cost of any second read.",
            "Do not change runtime until a new untouched comparison passes every gate.",
        ],
    }


def render_markdown(analysis, report):
    overall = analysis["overall"]
    complement = analysis["paired_complementarity"]
    span = analysis["span_contract"]
    lines = [
        "# Memory Highlight + Span Contract V2: Frozen Analysis",
        "",
        "## Verdict",
        "",
        "**Reject V2 runtime integration.** Full-context highlighting preserved source context "
        "and the span contract worked whenever upstream evidence existed, but highlighting did "
        "not improve paired semantic accuracy and failed one frozen transfer case.",
        "",
        "| condition | semantic pass | evidence recall | position-invariant |",
        "| --- | ---: | ---: | ---: |",
    ]
    labels = {
        CONTROL: "A: full context",
        HIGHLIGHT: "B: full context + highlight",
        SPAN: "C: B + span contract",
    }
    for condition in (CONTROL, HIGHLIGHT, SPAN):
        values = overall[condition]
        lines.append(
            f"| {labels[condition]} | {percent(values['semantic_case_pass_rate'])} | "
            f"{percent(values['gold_evidence_quote_recall'])} | "
            f"{percent(values['position_invariant_scenario_rate'])} |"
        )

    lines.extend(["", "## Paired result", ""])
    for comparison in analysis["paired_analysis"]:
        lines.append(
            f"- `{comparison['treatment']} - {comparison['control']}`: "
            f"{comparison['delta'] * 100:+.2f} pp, wins/losses "
            f"{comparison['mcnemar']['wins']}/{comparison['mcnemar']['losses']}, "
            f"McNemar p={comparison['mcnemar']['p_value']:.6f}, bootstrap 95% CI "
            f"[{comparison['paired_bootstrap_95_ci'][0] * 100:+.2f}, "
            f"{comparison['paired_bootstrap_95_ci'][1] * 100:+.2f}] pp."
        )

    lines.extend(
        [
            "",
            "## What worked",
            "",
            f"- Attention found all target utterances: "
            f"{percent(analysis['attention_integrity']['target_utterance_recall'])} recall, "
            f"{percent(analysis['attention_integrity']['selection_precision'])} precision.",
            f"- Every highlighted context restored exactly: "
            f"{percent(analysis['attention_integrity']['full_context_restoration_rate'])}.",
            f"- Span contract conditional validity: "
            f"{span['valid_when_upstream_available_count']}/{span['upstream_available_count']} "
            f"({percent(span['valid_when_upstream_available_rate'])}).",
            "",
            "## Why the gate failed",
            "",
            "| case | condition | failure |",
            "| --- | --- | --- |",
        ]
    )
    for row in analysis["failure_rows"]:
        lines.append(f"| {row['case_id']} | {row['condition']} | {row['category']} |")

    lines.extend(
        [
            "",
            "## Complementarity",
            "",
            f"- Both A and B passed: {complement.get('both_pass', 0)}/36.",
            f"- A only passed: {complement.get('control_only', 0)}/36.",
            f"- B only passed: {complement.get('highlight_only', 0)}/36.",
            f"- Neither passed: {complement.get('neither_pass', 0)}/36.",
            f"- At least one path carried answer evidence: "
            f"{complement['evidence_union_coverage_count']}/36.",
            "",
            "## Causal interpretation",
            "",
        ]
    )
    for conclusion in analysis["causal_conclusions"]:
        lines.append(f"- {conclusion}")
    lines.extend(["", "## Next experiment constraints", ""])
    for constraint in analysis["next_experiment_constraints"]:
        lines.append(f"- {constraint}")
    lines.extend(
        [
            "",
            "These 36 cases are consumed development evidence. No runtime file was changed.",
            "",
        ]
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_ANALYSIS_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_ANALYSIS_MD)
    args = parser.parse_args()
    report = json.loads(args.report.read_text(encoding="utf-8"))
    analysis = build_analysis(report)
    atomic_write_json(args.output_json, analysis)
    args.output_md.write_text(render_markdown(analysis, report), encoding="utf-8")
    print(
        json.dumps(
            {
                "decision": analysis["decision"],
                "failure_count": len(analysis["failure_rows"]),
                "source_results_sha256": analysis["source_results_sha256"],
                "output_json": str(args.output_json),
                "output_md": str(args.output_md),
            }
        )
    )


if __name__ == "__main__":
    main()
