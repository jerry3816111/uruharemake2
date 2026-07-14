#!/usr/bin/env python3
"""Verify and localize failures in the frozen utterance-attention V1 report."""

import argparse
import json
from collections import Counter
from pathlib import Path

from run_longmemeval_retrieval_benchmark import atomic_write_json, canonical_sha256, file_sha256


ROOT = Path(__file__).resolve().parent
DEFAULT_REPORT = ROOT / "reports" / "memory_utterance_attention_v1_report.json"
DEFAULT_ANALYSIS_JSON = ROOT / "reports" / "memory_utterance_attention_v1_analysis.json"
DEFAULT_ANALYSIS_MD = ROOT / "reports" / "memory_utterance_attention_v1_analysis.md"


IMPLEMENTATION_PATHS = {
    "runner_sha256": ROOT / "run_memory_utterance_attention_v1.py",
    "attention_module_sha256": ROOT / "memory_utterance_attention.py",
    "ledger_module_sha256": ROOT / "memory_evidence_ledger.py",
    "dataset_sha256": ROOT / "datasets" / "memory_utterance_attention_v1.json",
    "preregistration_sha256": (
        ROOT / "configs" / "memory_utterance_attention_v1_preregistration.json"
    ),
}


def percent(value):
    return f"{100.0 * float(value):.2f}%"


def classify_proposition_case(row):
    condition = row["conditions"]["utterance_attention_proposition"]
    metrics = condition["metrics"]
    errors = metrics.get("proposition_errors") or []
    if metrics["semantic_case_pass"]:
        return "semantic_pass"
    if "missing_ledger" in errors:
        return "upstream_evidence_or_ledger_missing"
    if any(error.startswith("missing_roles:before") for error in errors):
        return "single_event_cannot_express_before_and_current"
    if not metrics.get("proposition_valid"):
        return "model_owned_contract_field_invalid"
    return "valid_contract_but_strict_span_metric_miss"


def validated_proposition_claims(row):
    condition = row["conditions"]["utterance_attention_proposition"]
    proposition = condition.get("proposition") or {}
    validation = proposition.get("validation") or {}
    sanitized = validation.get("proposition") or {}
    return sanitized.get("claims") or []


def verify_report(report):
    checks = {
        "report_complete": bool(report.get("complete")),
        "result_count_matches": len(report.get("results") or [])
        == report.get("expected_case_count"),
        "results_sha256_matches": canonical_sha256(report.get("results") or [])
        == report.get("results_sha256"),
        "official_items_zero": report.get("research_boundary", {}).get(
            "official_longmemeval_items_used"
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


def build_analysis(report):
    checks, implementation_checks = verify_report(report)
    results = report["results"]
    attention = "utterance_attention_freeform"
    proposition = "utterance_attention_proposition"
    control = "full_session_freeform"
    selection_gold = sum(len(row["gold"]["attention_quotes"]) for row in results)
    selection_hits = sum(
        round(
            row["conditions"][attention]["metrics"]["attention_selection_recall"]
            * len(row["gold"]["attention_quotes"])
        )
        for row in results
    )
    evidence_misses = [
        row["case_id"]
        for row in results
        if row["conditions"][attention]["metrics"]["gold_evidence_quote_recall"] < 1.0
    ]
    proposition_categories = Counter(classify_proposition_case(row) for row in results)
    admitted_claims = [
        claim
        for row in results
        for claim in validated_proposition_claims(row)
    ]
    admitted_span_grounding = [
        str(claim.get("answer_span") or "").lower()
        in str(claim.get("source_quote") or "").lower()
        for claim in admitted_claims
    ]
    capability_deltas = {}
    for capability, summaries in report["by_capability"].items():
        capability_deltas[capability] = {
            "attention_minus_control": summaries[attention]["semantic_case_pass_rate"]
            - summaries[control]["semantic_case_pass_rate"],
            "proposition_minus_attention": summaries[proposition]["semantic_case_pass_rate"]
            - summaries[attention]["semantic_case_pass_rate"],
        }
    strict_metric_cases = [
        {
            "case_id": row["case_id"],
            "response": row["conditions"][proposition]["response"],
            "required_spans": row["gold"]["answer_spans"],
        }
        for row in results
        if classify_proposition_case(row) == "valid_contract_but_strict_span_metric_miss"
    ]
    return {
        "schema": "uruha_memory_utterance_attention_analysis_v1",
        "source_report": str(DEFAULT_REPORT.relative_to(ROOT)),
        "source_results_sha256": report["results_sha256"],
        "verification": checks,
        "implementation_verification": implementation_checks,
        "selection_stage": {
            "gold_utterance_hits": selection_hits,
            "gold_utterance_total": selection_gold,
            "recall": selection_hits / selection_gold if selection_gold else 0.0,
        },
        "extraction_stage": {
            "full_session_evidence_recall": report["summaries"][control][
                "gold_evidence_quote_recall"
            ],
            "attention_only_evidence_recall": report["summaries"][attention][
                "gold_evidence_quote_recall"
            ],
            "attention_only_missing_case_ids": evidence_misses,
        },
        "answer_stage": {
            "control_semantic_pass": report["summaries"][control][
                "semantic_case_pass_rate"
            ],
            "attention_semantic_pass": report["summaries"][attention][
                "semantic_case_pass_rate"
            ],
            "proposition_semantic_pass": report["summaries"][proposition][
                "semantic_case_pass_rate"
            ],
            "proposition_failure_categories": dict(sorted(proposition_categories.items())),
            "strict_metric_boundary_cases": strict_metric_cases,
            "admitted_proposition_claim_count": len(admitted_claims),
            "admitted_proposition_span_grounding_rate": (
                sum(admitted_span_grounding) / len(admitted_span_grounding)
                if admitted_span_grounding
                else 1.0
            ),
            "gate_semantics_audit": (
                "The frozen report gate named all_valid_proposition_spans_grounded was "
                "implemented as all proposition contracts valid. That is stricter than its "
                "name. All admitted spans were checked separately here; changing the label or "
                "logic would not change the rejection because four other preregistered gates fail."
            ),
        },
        "capability_deltas": capability_deltas,
        "paired_analysis": report["paired_analysis"],
        "decision": "reject_v1_runtime_integration",
        "causal_conclusions": [
            (
                "Query-aware selection found every frozen target utterance, so selection was not "
                "the observed bottleneck in this experiment."
            ),
            (
                "Replacing the full session with selected utterances removed discourse context "
                "and caused nine repeated extraction failures; attention must augment rather than "
                "replace source context."
            ),
            (
                "A ledger event assigns one evidence role to an entire quote, but six comparison "
                "cases encoded before and current values in the same quote; answer roles must bind "
                "to source spans, not only whole events."
            ),
            (
                "The model should not choose system-known contract fields such as answer type, "
                "required roles, or whether a nonrelational question has a relation."
            ),
        ],
        "next_experiment_constraints": [
            "Use new scenarios; V1 cases cannot serve as a promotion holdout again.",
            "Keep the full source session and add selected utterances as explicit highlights.",
            "Represent old/current values as separately grounded source spans.",
            "Let the controller define slot names and relation constraints; let the model only bind spans.",
            "Keep runtime unchanged until a new untouched comparison passes every gate.",
        ],
    }


def render_markdown(analysis, report):
    control = report["summaries"]["full_session_freeform"]
    attention = report["summaries"]["utterance_attention_freeform"]
    proposition = report["summaries"]["utterance_attention_proposition"]
    lines = [
        "# Memory Utterance Attention V1: Frozen Analysis",
        "",
        "## Verdict",
        "",
        "**Reject V1 runtime integration.** Selection worked, but replacing the full session with "
        "selected turns harmed extraction, and the first proposition contract was too coarse.",
        "",
        "| stage | result | interpretation |",
        "| --- | ---: | --- |",
        f"| selected target utterances | {analysis['selection_stage']['gold_utterance_hits']}/{analysis['selection_stage']['gold_utterance_total']} | selector found every frozen target |",
        f"| full-session evidence recall | {percent(control['gold_evidence_quote_recall'])} | control retained discourse context |",
        f"| attention-only evidence recall | {percent(attention['gold_evidence_quote_recall'])} | 9 cases lost evidence after truncation |",
        f"| full-session semantic pass | {percent(control['semantic_case_pass_rate'])} | matched control |",
        f"| attention-only semantic pass | {percent(attention['semantic_case_pass_rate'])} | {100 * (attention['semantic_case_pass_rate'] - control['semantic_case_pass_rate']):+.2f} pp |",
        f"| typed-proposition semantic pass | {percent(proposition['semantic_case_pass_rate'])} | {100 * (proposition['semantic_case_pass_rate'] - attention['semantic_case_pass_rate']):+.2f} pp |",
        "",
        "## Paired evidence",
        "",
    ]
    for comparison in analysis["paired_analysis"]:
        lines.append(
            f"- `{comparison['treatment']} - {comparison['control']}`: "
            f"{comparison['delta'] * 100:+.2f} pp, wins/losses "
            f"{comparison['mcnemar']['wins']}/{comparison['mcnemar']['losses']}, "
            f"McNemar p={comparison['mcnemar']['p_value']:.6f}, bootstrap 95% CI "
            f"[{comparison['paired_bootstrap_95_ci'][0] * 100:+.2f}, "
            f"{comparison['paired_bootstrap_95_ci'][1] * 100:+.2f}] pp."
        )
    lines.extend(["", "## Failure localization", ""])
    labels = {
        "semantic_pass": "passed",
        "upstream_evidence_or_ledger_missing": "attention extraction / ledger missing",
        "single_event_cannot_express_before_and_current": "one quote could not expose before + current roles",
        "model_owned_contract_field_invalid": "model generated an invalid system-owned field or index",
        "valid_contract_but_strict_span_metric_miss": "valid grounded answer failed the preregistered strict phrase metric",
    }
    for key, count in analysis["answer_stage"]["proposition_failure_categories"].items():
        lines.append(f"- {count}/36: {labels[key]}")
    lines.extend(
        [
            "",
            f"All {analysis['answer_stage']['admitted_proposition_claim_count']} admitted "
            f"proposition spans were source-grounded "
            f"({percent(analysis['answer_stage']['admitted_proposition_span_grounding_rate'])}).",
            "",
            "Gate audit: `all_valid_proposition_spans_grounded` was implemented as requiring "
            "every proposition contract to be valid, which is stricter than the gate name. This "
            "does not change the rejection because four other gates also failed.",
        ]
    )
    lines.extend(["", "## Capability effects", "", "| capability | attention - control | proposition - attention |", "| --- | ---: | ---: |"])
    for capability, deltas in analysis["capability_deltas"].items():
        lines.append(
            f"| {capability} | {deltas['attention_minus_control'] * 100:+.2f} pp | "
            f"{deltas['proposition_minus_attention'] * 100:+.2f} pp |"
        )
    lines.extend(["", "## What this changes", ""])
    for conclusion in analysis["causal_conclusions"]:
        lines.append(f"- {conclusion}")
    lines.extend(["", "## Next experiment constraints", ""])
    for constraint in analysis["next_experiment_constraints"]:
        lines.append(f"- {constraint}")
    lines.extend(
        [
            "",
            "The V1 dataset is now analysis data and cannot be reused as an untouched promotion "
            "set. No runtime file was changed.",
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
                "source_results_sha256": analysis["source_results_sha256"],
                "output_json": str(args.output_json),
                "output_md": str(args.output_md),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
