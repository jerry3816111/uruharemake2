#!/usr/bin/env python3
"""Post-hoc V43 diagnostic; never changes the preregistered primary score."""

import argparse
import json
import re
from collections import Counter
from pathlib import Path

from action_selective_deliberation_v37 import COMMITMENTS


ROOT = Path(__file__).resolve().parent
DATASET_PATH = ROOT / "datasets" / "action_selective_deliberation_v37_development.json"
DEFAULT_RAW = ROOT / "reports" / "relational_commitment_context_v43_development_raw.json"
DEFAULT_JSON = ROOT / "reports" / "relational_commitment_context_v43_posthoc_diagnostic.json"
DEFAULT_MARKDOWN = ROOT / "reports" / "relational_commitment_context_v43_posthoc_diagnostic.md"
CONDITIONS = ("commitment_only_candidate", "relational_context_candidate")
LABEL_RE = re.compile(
    r"(?<![A-Za-z_])(" + "|".join(sorted(COMMITMENTS)) + r")(?![A-Za-z_])"
)


def recover_unique_label(raw_reply):
    labels = sorted(set(LABEL_RE.findall(str(raw_reply or ""))))
    return labels[0] if len(labels) == 1 else None


def output_shape(raw_reply, strict_parse_success):
    if strict_parse_success:
        return "strict_object"
    text = str(raw_reply or "").strip()
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return "plain_enum_token" if text in COMMITMENTS else "invalid_json_other"
    if isinstance(payload, str) and payload in COMMITMENTS:
        return "json_string_enum"
    if isinstance(payload, dict) and isinstance(payload.get("commitment"), dict):
        return "nested_commitment_object"
    return "other_json_shape"


def diagnose(raw_report, dataset):
    gold = {
        (case["id"], f"{frame['domain']}.{frame['value']}"): frame["commitment"]
        for case in dataset["cases"]
        for frame in case["expected_frames"]
        if frame["value"] != "unsupported"
    }
    summaries = {}
    recovered = {}
    for condition in CONDITIONS:
        rows = [
            row for row in raw_report["judgment_rows"] if row["condition"] == condition
        ]
        correct = 0
        recoverable = 0
        shapes = Counter()
        unresolved = []
        for row in rows:
            key = (row["case_id"], row["target_id"])
            result = row["result"]
            label = recover_unique_label(result["raw_reply"])
            recovered[(condition, *key)] = label
            shapes[output_shape(result["raw_reply"], result["parsed"]["parse_success"])] += 1
            if label is None:
                unresolved.append({"case_id": key[0], "target_id": key[1]})
                continue
            recoverable += 1
            correct += label == gold[key]
        total = len(rows)
        summaries[condition] = {
            "target_count": total,
            "strict_parse_success_count": shapes["strict_object"],
            "strict_parse_success_rate": round(shapes["strict_object"] / total, 4),
            "unique_label_recoverable_count": recoverable,
            "unique_label_recoverable_rate": round(recoverable / total, 4),
            "posthoc_correct_count": correct,
            "posthoc_accuracy_over_all_targets": round(correct / total, 4),
            "posthoc_accuracy_when_recoverable": round(correct / recoverable, 4),
            "output_shape_counts": dict(sorted(shapes.items())),
            "unresolved_targets": unresolved,
        }

    fixed = []
    regressed = []
    for key, expected in gold.items():
        base_correct = recovered[(CONDITIONS[0], *key)] == expected
        relational_correct = recovered[(CONDITIONS[1], *key)] == expected
        row = {"case_id": key[0], "target_id": key[1]}
        if not base_correct and relational_correct:
            fixed.append(row)
        if base_correct and not relational_correct:
            regressed.append(row)
    return {
        "schema": "uruha_relational_commitment_context_posthoc_diagnostic_v43",
        "evidence_status": "posthoc_exploratory_not_a_primary_metric",
        "changes_preregistered_score": False,
        "authorizes_holdout_or_runtime": False,
        "method": "Recover a label only when exactly one commitment enum token appears anywhere in the raw response; do not resolve multiple labels.",
        "conditions": summaries,
        "relational_exploratory_attribution": {
            "fixed_vs_commitment_only": fixed,
            "regressed_vs_commitment_only": regressed,
        },
        "conclusion": "The one-field carrier failed structurally. Relational context recovered several coordinated requests but also spread request force into locally negated targets, so both carrier design and target isolation require a new preregistered experiment.",
    }


def render_markdown(report):
    lines = [
        "# V43 post-hoc carrier diagnostic",
        "",
        "> Exploratory only. This does not alter the preregistered V43 failure or authorize holdout/runtime use.",
        "",
        "| condition | strict object | unique label recoverable | post-hoc correct/all | correct/recoverable |",
        "|---|---:|---:|---:|---:|",
    ]
    for name, row in report["conditions"].items():
        lines.append(
            f"| {name} | {row['strict_parse_success_count']}/{row['target_count']} | "
            f"{row['unique_label_recoverable_count']}/{row['target_count']} | "
            f"{row['posthoc_correct_count']}/{row['target_count']} | "
            f"{100 * row['posthoc_accuracy_when_recoverable']:.1f}% |"
        )
    lines.extend(
        [
            "",
            f"- Output shapes: `{json.dumps({name: row['output_shape_counts'] for name, row in report['conditions'].items()}, ensure_ascii=False)}`",
            f"- Relational fixes: `{report['relational_exploratory_attribution']['fixed_vs_commitment_only']}`",
            f"- Relational regressions: `{report['relational_exploratory_attribution']['regressed_vs_commitment_only']}`",
            f"- Conclusion: {report['conclusion']}",
            "",
        ]
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args()
    raw_report = json.loads(args.raw.read_text(encoding="utf-8"))
    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    report = diagnose(raw_report, dataset)
    args.json_output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    args.markdown_output.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(report["conditions"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
