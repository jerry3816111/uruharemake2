#!/usr/bin/env python3
"""Audit the V45 holdout construction without any model inference."""

import argparse
import json
from collections import Counter
from pathlib import Path

from discourse_state_perception_v45 import detect_focus_discourse_signals
from grounded_commitment_classifier_v42 import ground_supported_targets
from grounded_frame_isolation_v39 import load_v39_anchor_ontology
from relational_commitment_context_v43 import select_evidence_anchor


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "configs" / "discourse_state_perception_v45_preregistration.json"
HOLDOUT_PATH = ROOT / "datasets" / "discourse_state_perception_v45_holdout.json"
DEVELOPMENT_PATH = ROOT / "datasets" / "action_selective_deliberation_v37_development.json"
DEFAULT_JSON = ROOT / "reports" / "discourse_state_perception_v45_holdout_audit.json"
DEFAULT_MARKDOWN = ROOT / "reports" / "discourse_state_perception_v45_holdout_audit.md"


def audit(holdout, development, config):
    ontology = load_v39_anchor_ontology()
    development_texts = {case["user_input"] for case in development["cases"]}
    duplicate_texts = sorted(
        case["user_input"] for case in holdout["cases"] if case["user_input"] in development_texts
    )
    expected_total = candidate_total = true_positive = 0
    missing_rows = []
    extra_rows = []
    evidence_total = evidence_supported = 0
    evidence_misses = []
    signal_counts = Counter()
    patterns = config["deterministic_discourse_signals"]["patterns"]
    for case in holdout["cases"]:
        gold = {
            (frame["domain"], frame["value"]): frame
            for frame in case["expected_frames"]
            if frame["value"] != "unsupported"
        }
        candidates = ground_supported_targets(case["user_input"], ontology)
        actual = {(row["domain"], row["value"]): row for row in candidates}
        expected_total += len(gold)
        candidate_total += len(actual)
        true_positive += len(set(gold) & set(actual))
        for key in sorted(set(gold) - set(actual)):
            missing_rows.append({"case_id": case["id"], "target": list(key)})
        for key in sorted(set(actual) - set(gold)):
            extra_rows.append(
                {
                    "case_id": case["id"],
                    "target": list(key),
                    "anchors": actual[key]["anchors"],
                }
            )
        for key in sorted(set(gold) & set(actual)):
            frame = gold[key]
            selected = select_evidence_anchor(
                case["user_input"], actual[key], frame["commitment"]
            )
            evidence_total += 1
            supported = any(
                selected["text"] in option or option in selected["text"]
                for option in frame["evidence_options"]
            )
            evidence_supported += supported
            if not supported:
                evidence_misses.append(
                    {
                        "case_id": case["id"],
                        "target": list(key),
                        "selected": selected["text"],
                        "gold_options": frame["evidence_options"],
                    }
                )
        for candidate in candidates:
            rows = detect_focus_discourse_signals(
                case["user_input"], candidate, patterns
            )
            types = {
                signal["signal_type"]
                for row in rows
                for signal in row["signals"]
            }
            signal_counts.update(types or ["none"])
    family_counts = Counter(case["family"] for case in holdout["cases"])
    recall = true_positive / expected_total if expected_total else 1.0
    precision = true_positive / candidate_total if candidate_total else 1.0
    return {
        "schema": "uruha_discourse_state_perception_holdout_audit_v45",
        "evidence_status": "deterministic_pre_inference_holdout_construction_audit",
        "model_inference_used": False,
        "case_count": len(holdout["cases"]),
        "family_counts": dict(sorted(family_counts.items())),
        "exact_development_utterance_overlap_count": len(duplicate_texts),
        "exact_development_utterance_overlaps": duplicate_texts,
        "supported_expected_target_count": expected_total,
        "candidate_target_count": candidate_total,
        "true_positive_target_count": true_positive,
        "candidate_target_recall": round(recall, 4),
        "candidate_precision": round(precision, 4),
        "missing_targets": missing_rows,
        "extra_targets": extra_rows,
        "deterministic_evidence_support_count": evidence_supported,
        "deterministic_evidence_target_count": evidence_total,
        "deterministic_evidence_support_rate": round(
            evidence_supported / evidence_total if evidence_total else 1.0, 4
        ),
        "deterministic_evidence_misses": evidence_misses,
        "detected_signal_counts": dict(sorted(signal_counts.items())),
        "construction_gate_passed": bool(
            len(holdout["cases"]) == 48
            and len(family_counts) == 8
            and all(count == 6 for count in family_counts.values())
            and not duplicate_texts
            and recall >= 0.95
            and precision >= 0.95
        ),
    }


def render_markdown(report):
    return "\n".join(
        [
            "# V45 fresh holdout construction audit",
            "",
            "No model inference was used in this audit.",
            "",
            f"- Cases/families: `{report['case_count']}` / `{len(report['family_counts'])}`",
            f"- Exact development utterance overlap: `{report['exact_development_utterance_overlap_count']}`",
            f"- Candidate recall: `{report['candidate_target_recall']}`",
            f"- Candidate precision: `{report['candidate_precision']}`",
            f"- Deterministic evidence support: `{report['deterministic_evidence_support_count']}/{report['deterministic_evidence_target_count']}`",
            f"- Extra candidate targets retained: `{report['extra_targets']}`",
            f"- Construction gate passed: `{report['construction_gate_passed']}`",
            "",
        ]
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args()
    loads = lambda path: json.loads(path.read_text(encoding="utf-8"))
    report = audit(loads(HOLDOUT_PATH), loads(DEVELOPMENT_PATH), loads(CONFIG_PATH))
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.markdown_output.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({"construction_gate_passed": report["construction_gate_passed"], "candidate_recall": report["candidate_target_recall"], "candidate_precision": report["candidate_precision"]}, indent=2))


if __name__ == "__main__":
    main()
