#!/usr/bin/env python3
"""Audit whether the V39 ontology can propose grounded supported-action targets."""

import argparse
import json
from pathlib import Path

from action_ontology_grounding_v38 import find_action_anchors
from grounded_frame_isolation_v39 import load_v39_anchor_ontology


ROOT = Path(__file__).resolve().parent
DATASET_PATH = ROOT / "datasets" / "action_selective_deliberation_v37_development.json"
DEFAULT_JSON = ROOT / "reports" / "grounded_action_candidate_audit_v42.json"
DEFAULT_MARKDOWN = ROOT / "reports" / "grounded_action_candidate_audit_v42.md"


def _rate(numerator, denominator):
    return round(numerator / denominator, 4) if denominator else 1.0


def audit_case(case, ontology):
    expected_supported = {
        (frame["domain"], frame["value"]): frame
        for frame in case["expected_frames"]
        if frame["value"] != "unsupported"
    }
    expected_unsupported = [
        frame for frame in case["expected_frames"] if frame["value"] == "unsupported"
    ]
    candidates = {}
    for domain, value in sorted(ontology):
        anchors = find_action_anchors(case["user_input"], domain, value, ontology)
        if anchors:
            candidates[(domain, value)] = anchors
    expected_keys = set(expected_supported)
    candidate_keys = set(candidates)
    matched = expected_keys & candidate_keys
    evidence_covered = []
    evidence_missing = []
    for key in sorted(matched):
        options = expected_supported[key]["evidence_options"]
        anchors = candidates[key]
        if any(
            anchor["text"] in option or option in anchor["text"]
            for anchor in anchors
            for option in options
        ):
            evidence_covered.append(key)
        else:
            evidence_missing.append(key)
    return {
        "case_id": case["id"],
        "family": case["family"],
        "user_input": case["user_input"],
        "expected_supported_targets": [
            {"domain": domain, "value": value}
            for domain, value in sorted(expected_keys)
        ],
        "candidate_targets": [
            {
                "domain": domain,
                "value": value,
                "anchors": candidates[(domain, value)],
            }
            for domain, value in sorted(candidate_keys)
        ],
        "true_positive_targets": [list(key) for key in sorted(matched)],
        "missing_targets": [list(key) for key in sorted(expected_keys - candidate_keys)],
        "extra_targets": [list(key) for key in sorted(candidate_keys - expected_keys)],
        "evidence_covered_targets": [list(key) for key in evidence_covered],
        "evidence_missing_targets": [list(key) for key in evidence_missing],
        "expected_unsupported_frame_count": len(expected_unsupported),
    }


def audit_dataset(dataset, ontology):
    rows = [audit_case(case, ontology) for case in dataset["cases"]]
    expected = sum(len(row["expected_supported_targets"]) for row in rows)
    candidates = sum(len(row["candidate_targets"]) for row in rows)
    true_positive = sum(len(row["true_positive_targets"]) for row in rows)
    missing = sum(len(row["missing_targets"]) for row in rows)
    extra = sum(len(row["extra_targets"]) for row in rows)
    evidence_covered = sum(len(row["evidence_covered_targets"]) for row in rows)
    expected_unsupported = sum(row["expected_unsupported_frame_count"] for row in rows)
    empty_expected = [row for row in rows if not row["expected_supported_targets"]]
    return {
        "schema": "uruha_grounded_action_candidate_audit_v42",
        "evidence_status": "retired_development_feasibility_audit_no_model_inference",
        "dataset": str(DATASET_PATH.relative_to(ROOT)),
        "case_count": len(rows),
        "summary": {
            "supported_expected_target_count": expected,
            "candidate_target_count": candidates,
            "true_positive_target_count": true_positive,
            "missing_target_count": missing,
            "extra_target_count": extra,
            "supported_target_recall": _rate(true_positive, expected),
            "candidate_precision": _rate(true_positive, candidates),
            "matched_target_evidence_coverage": _rate(evidence_covered, true_positive),
            "case_exact_candidate_set_rate": _rate(
                sum(
                    not row["missing_targets"] and not row["extra_targets"]
                    for row in rows
                ),
                len(rows),
            ),
            "empty_supported_target_specificity": _rate(
                sum(not row["candidate_targets"] for row in empty_expected),
                len(empty_expected),
            ),
            "expected_unsupported_frame_count_out_of_scope": expected_unsupported,
        },
        "rows": rows,
    }


def render_markdown(report):
    summary = report["summary"]
    lines = [
        "# V42 grounded action-candidate feasibility audit",
        "",
        "No model inference was performed. The existing V39 ontology was evaluated unchanged on retired development data.",
        "",
        "| metric | value |",
        "|---|---:|",
        f"| supported targets | {summary['supported_expected_target_count']} |",
        f"| target recall | {100 * summary['supported_target_recall']:.1f}% |",
        f"| candidate precision | {100 * summary['candidate_precision']:.1f}% |",
        f"| matched evidence coverage | {100 * summary['matched_target_evidence_coverage']:.1f}% |",
        f"| exact candidate-set cases | {100 * summary['case_exact_candidate_set_rate']:.1f}% |",
        f"| empty-target specificity | {100 * summary['empty_supported_target_specificity']:.1f}% |",
        f"| unsupported frames outside this classifier | {summary['expected_unsupported_frame_count_out_of_scope']} |",
        "",
        "## Missing targets",
        "",
    ]
    missing_rows = [row for row in report["rows"] if row["missing_targets"]]
    if not missing_rows:
        lines.append("- None")
    for row in missing_rows:
        lines.append(
            f"- `{row['case_id']}`: `{row['missing_targets']}` from `{row['user_input']}`"
        )
    lines.extend(["", "## Extra targets", ""])
    extra_rows = [row for row in report["rows"] if row["extra_targets"]]
    if not extra_rows:
        lines.append("- None")
    for row in extra_rows:
        lines.append(
            f"- `{row['case_id']}`: `{row['extra_targets']}` from `{row['user_input']}`"
        )
    lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=DATASET_PATH)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args()
    dataset = json.loads(args.dataset.read_text(encoding="utf-8"))
    report = audit_dataset(dataset, load_v39_anchor_ontology())
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    args.markdown_output.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(report["summary"], indent=2))


if __name__ == "__main__":
    main()
