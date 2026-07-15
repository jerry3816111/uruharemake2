#!/usr/bin/env python3
"""Analyze the preregistered V35 semantic action-authorization study."""

import argparse
import json
import math
import statistics
from pathlib import Path

from run_rightbrain_qwen35_migration_v33 import score_action_output
from vrm_action_policy_v34 import validate_model_tool_calls


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "action_semantic_authorization_v35_preregistration.json"
DATASET_PATH = ROOT / "datasets" / "rightbrain_role_specialization_v34_confirmation.json"
SOURCE_RAW_PATH = ROOT / "reports" / "rightbrain_role_specialization_v34_confirmation_raw.json"
DEFAULT_RAW = ROOT / "reports" / "action_semantic_authorization_v35_development_raw.json"
DEFAULT_JSON = ROOT / "reports" / "action_semantic_authorization_v35_development_analysis.json"
DEFAULT_MD = ROOT / "reports" / "action_semantic_authorization_v35_development_analysis.md"


def _rate(numerator, denominator):
    return round(numerator / denominator, 4) if denominator else None


def _mean(values):
    values = [float(value) for value in values if value is not None]
    return round(sum(values) / len(values), 4) if values else None


def _percentile(values, quantile):
    values = sorted(float(value) for value in values)
    if not values:
        return None
    index = max(0, min(len(values) - 1, math.ceil(quantile * len(values)) - 1))
    return round(values[index], 4)


def _fmt_pct(value):
    return "n/a" if value is None else f"{100 * value:.1f}%"


def _score_summary(rows):
    scores = [row["score"] for row in rows]
    no_action = [score for score in scores if score["expected_call_count"] == 0]
    return {
        "case_count": len(rows),
        "exact_accuracy": _rate(sum(score["exact_match"] for score in scores), len(scores)),
        "no_action_specificity": _rate(
            sum(score["no_action_correct"] for score in no_action), len(no_action)
        ),
        "required_action_recall": _mean(
            score["required_action_recall"] for score in scores
        ),
        "false_action_rate": _rate(
            sum(score["false_action"] for score in scores), len(scores)
        ),
        "negation_violation_count": sum(
            score["negation_violation"] for score in scores
        ),
        "invalid_tool_or_argument_rate": _rate(
            sum(score["invalid_tool_or_argument"] for score in scores), len(scores)
        ),
    }


def _baseline_rows(dataset, source_raw, source, *, lexical=False):
    cases = {case["id"]: case for case in dataset["action_cases"]}
    rows = []
    for source_row in source_raw["action_rows"]:
        if source_row["condition"] != source:
            continue
        case = cases[source_row["case_id"]]
        calls = source_row["score"]["actual_calls"]
        if lexical:
            calls = validate_model_tool_calls(case["user_input"], calls)["accepted_calls"]
        rows.append({"case_id": case["id"], "score": score_action_output(case, calls)})
    return rows


def _candidate_summary(rows, raw_summary):
    summary = _score_summary(rows)
    invoked = [row for row in rows if row["classifier_invoked"]]
    latencies = [
        row["response_metrics"]["wall_seconds"]
        for row in invoked
        if row.get("response_metrics")
    ]
    authorized_verdicts = [
        verdict
        for row in invoked
        for verdict in row["parsed_authorization"].get("verdicts") or []
        if verdict.get("authorized")
    ]
    summary.update(
        {
            "classifier_invocation_rate": _rate(len(invoked), len(rows)),
            "invoked_parse_success_rate": _rate(
                sum(row["parsed_authorization"]["parse_success"] for row in invoked),
                len(invoked),
            ),
            "accepted_evidence_validity_rate": _rate(
                sum(verdict.get("evidence_valid") for verdict in authorized_verdicts),
                len(authorized_verdicts),
            ),
            "median_authorizer_latency_seconds": (
                round(statistics.median(latencies), 4) if latencies else None
            ),
            "p95_authorizer_latency_seconds": _percentile(latencies, 0.95),
            "required_action_recall_delta_vs_raw": round(
                summary["required_action_recall"] - raw_summary["required_action_recall"],
                4,
            ),
        }
    )
    return summary


def _gate(summary, target):
    checks = {
        "end_to_end_exact_accuracy": summary["exact_accuracy"]
        >= target["end_to_end_exact_accuracy_at_least"],
        "no_action_specificity": summary["no_action_specificity"]
        >= target["no_action_specificity_at_least"],
        "false_action_rate": summary["false_action_rate"]
        <= target["false_action_rate_at_most"],
        "negation_violation_count": summary["negation_violation_count"]
        == target["negation_violation_count"],
        "invalid_tool_or_argument_rate": summary["invalid_tool_or_argument_rate"]
        == target["invalid_tool_or_argument_rate"],
        "required_action_recall_delta_vs_raw": summary[
            "required_action_recall_delta_vs_raw"
        ]
        >= target["required_action_recall_delta_vs_raw_at_least"],
        "invoked_parse_success_rate": summary["invoked_parse_success_rate"]
        >= target["invoked_parse_success_rate_at_least"],
        "accepted_evidence_validity_rate": summary["accepted_evidence_validity_rate"]
        == target["accepted_evidence_validity_rate"],
        "median_authorizer_latency_seconds": summary[
            "median_authorizer_latency_seconds"
        ]
        <= target["median_authorizer_latency_seconds_at_most"],
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "failed_checks": [name for name, passed in checks.items() if not passed],
    }


def analyze(raw_path=DEFAULT_RAW):
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    source_raw = json.loads(SOURCE_RAW_PATH.read_text(encoding="utf-8"))
    raw = json.loads(Path(raw_path).read_text(encoding="utf-8"))
    cases = {case["id"]: case for case in dataset["action_cases"]}
    sources = config["development_evidence"]["proposal_sources"]

    baselines = {}
    for source in sources:
        raw_rows = _baseline_rows(dataset, source_raw, source)
        lexical_rows = _baseline_rows(dataset, source_raw, source, lexical=True)
        baselines[source] = {
            "raw_direct": _score_summary(raw_rows),
            "v34_lexical_validator": _score_summary(lexical_rows),
        }

    target = config["development_gate_per_proposal_source"]
    candidates = {}
    for candidate in config["candidate_authorizers"]:
        source_results = {}
        candidate_passed = True
        for source in sources:
            rows = [
                row
                for row in raw["rows"]
                if row["authorizer_condition"] == candidate
                and row["proposal_source"] == source
            ]
            if len(rows) != len(cases):
                raise ValueError(f"Incomplete V35 condition: {candidate}/{source}")
            summary = _candidate_summary(rows, baselines[source]["raw_direct"])
            gate = _gate(summary, target)
            candidate_passed = candidate_passed and gate["passed"]
            failures = []
            for row in rows:
                if row["score"]["exact_match"]:
                    continue
                case = cases[row["case_id"]]
                failures.append(
                    {
                        "case_id": case["id"],
                        "family": case["family"],
                        "user_input": case["user_input"],
                        "expected_calls": case["expected_calls"],
                        "proposed_calls": row["proposed_calls"],
                        "accepted_calls": row["accepted_calls"],
                        "parsed_authorization": row["parsed_authorization"],
                    }
                )
            source_results[source] = {
                "summary": summary,
                "gate": gate,
                "failures": failures,
            }
        candidates[candidate] = {
            "passed_all_proposal_sources": candidate_passed,
            "proposal_sources": source_results,
        }

    selected = next(
        (
            candidate
            for candidate in config["candidate_authorizers"]
            if candidates[candidate]["passed_all_proposal_sources"]
        ),
        None,
    )
    decision = (
        f"advance_{selected}_to_fresh_v35_confirmation"
        if selected
        else "do_not_advance_v35_semantic_authorizer"
    )
    return {
        "schema": "uruha_action_semantic_authorization_development_analysis_v35",
        "evidence_status": "development_only_not_confirmation",
        "source_report": str(Path(raw_path).resolve().relative_to(ROOT)),
        "baselines": baselines,
        "candidates": candidates,
        "selected_candidate": selected,
        "development_gate_passed": selected is not None,
        "decision": decision,
        "runtime_change_authorized": False,
        "fresh_confirmation_required": selected is not None,
    }


def _markdown(analysis):
    lines = [
        "# V35 semantic action authorization development result",
        "",
        "> Development evidence on the retired V34 confirmation set. It cannot authorize runtime use.",
        "",
        "## Baselines",
        "",
        "| proposal source | path | exact | no-action | recall | false action |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for source, paths in analysis["baselines"].items():
        for path, summary in paths.items():
            lines.append(
                f"| {source} | {path} | {_fmt_pct(summary['exact_accuracy'])} | "
                f"{_fmt_pct(summary['no_action_specificity'])} | "
                f"{_fmt_pct(summary['required_action_recall'])} | "
                f"{_fmt_pct(summary['false_action_rate'])} |"
            )
    lines.extend(
        [
            "",
            "## Semantic authorizers",
            "",
            "| authorizer | proposal source | exact | no-action | recall | false action | parse | p50 | gate |",
            "|---|---|---:|---:|---:|---:|---:|---:|---|",
        ]
    )
    for candidate, result in analysis["candidates"].items():
        for source, source_result in result["proposal_sources"].items():
            summary = source_result["summary"]
            lines.append(
                f"| {candidate} | {source} | {_fmt_pct(summary['exact_accuracy'])} | "
                f"{_fmt_pct(summary['no_action_specificity'])} | "
                f"{_fmt_pct(summary['required_action_recall'])} | "
                f"{_fmt_pct(summary['false_action_rate'])} | "
                f"{_fmt_pct(summary['invoked_parse_success_rate'])} | "
                f"{summary['median_authorizer_latency_seconds']:.2f}s | "
                f"{'PASS' if source_result['gate']['passed'] else 'FAIL'} |"
            )
    lines.extend(
        [
            "",
            f"- Selected candidate: `{analysis['selected_candidate']}`",
            f"- Decision: `{analysis['decision']}`",
            "- Runtime remains unchanged; a fresh frozen holdout is required after a development pass.",
            "",
        ]
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MD)
    args = parser.parse_args()
    analysis = analyze(args.raw)
    args.json_output.write_text(
        json.dumps(analysis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    args.markdown_output.write_text(_markdown(analysis), encoding="utf-8")
    print(
        json.dumps(
            {
                "selected_candidate": analysis["selected_candidate"],
                "decision": analysis["decision"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
