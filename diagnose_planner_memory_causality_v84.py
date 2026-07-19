#!/usr/bin/env python3
"""Reproduce an aggregate post-hoc mechanism diagnosis for V84."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

import planner_memory_causality_v84 as v84
import planner_supervision_v76 as v76


ROOT = Path(__file__).resolve().parent
TRANSCRIPT_LABEL_RE = re.compile(r"(?:User|Uruha)\s*:", re.IGNORECASE)


def diagnose(packets, rows):
    intact_packets = [packet for packet in packets if packet["scenario_family"] == "memory_recall_update"]
    anchor_label_count = 0
    for packet in intact_packets:
        cues = (
            packet["payloads"][v84.C0]["context"]["audited_memory_brief"].get("allowed_memory_cues")
            or []
        )
        if any(TRANSCRIPT_LABEL_RE.search(str(cue.get("jp_anchor") or "")) for cue in cues):
            anchor_label_count += 1

    intact_rows = [row for row in rows if row["condition"] == v84.C0]
    removed_rows = [row for row in rows if row["condition"] == v84.T1]

    def label_count(target_rows):
        return sum(bool(TRANSCRIPT_LABEL_RE.search(str(row.get("raw_reply") or ""))) for row in target_rows)

    def arrow_count(target_rows):
        return sum("->" in str(row.get("raw_reply") or "") for row in target_rows)

    intact_failure_counts = Counter(
        code for row in intact_rows for code in row["score"]["failure_codes"]
    )
    removed_failure_counts = Counter(
        code for row in removed_rows for code in row["score"]["failure_codes"]
    )
    intact_output_labels = label_count(intact_rows)
    removed_output_labels = label_count(removed_rows)
    mechanism_supported = (
        anchor_label_count == len(intact_packets)
        and intact_output_labels == len(intact_rows)
        and removed_output_labels == 0
    )
    return {
        "schema": "uruha_planner_memory_causality_diagnosis_v84",
        "diagnosis_type": "post_hoc_mechanism_diagnosis_does_not_change_preregistered_decision",
        "preregistered_decision": "inconclusive_effect_between_preregistered_gates",
        "case_count": len(intact_packets),
        "observation_count_per_condition": len(intact_rows),
        "intact_packet_allowed_anchor_with_transcript_label_count": anchor_label_count,
        "intact_output_transcript_label_count": intact_output_labels,
        "removed_output_transcript_label_count": removed_output_labels,
        "intact_output_arrow_count": arrow_count(intact_rows),
        "removed_output_arrow_count": arrow_count(removed_rows),
        "intact_failure_code_counts": dict(sorted(intact_failure_counts.items())),
        "removed_failure_code_counts": dict(sorted(removed_failure_counts.items())),
        "mechanism_supported": mechanism_supported,
        "mechanism": (
            "The explicit memory path exposed a raw multilingual transcript-shaped jp_anchor as an allowed "
            "surface cue. The frozen RightBrain copied that cue; removing the memory-integration bundle removed "
            "both the required meaning and the transcript artifact."
        ),
        "next_falsifiable_hypothesis": (
            "Canonicalizing explicit memory cues before RightBrain payload construction can retain required-memory "
            "recall while eliminating transcript-label, CJK-language, and length failures."
        ),
        "authorizations": {
            "training_data": False,
            "production_runtime_change": False,
            "v84_decision_override": False,
        },
        "privacy": {
            "raw_reply_text_in_report": False,
            "memory_anchor_text_in_report": False,
            "candidate_or_session_ids_in_report": False,
        },
    }


def render_markdown(report):
    return "\n".join(
        [
            "# V84 Post-hoc Mechanism Diagnosis",
            "",
            f"- Preregistered decision remains: `{report['preregistered_decision']}`",
            f"- Intact packets with transcript-shaped allowed memory anchors: {report['intact_packet_allowed_anchor_with_transcript_label_count']}/{report['case_count']}",
            f"- Intact outputs reproducing transcript labels: {report['intact_output_transcript_label_count']}/{report['observation_count_per_condition']}",
            f"- Removed-condition outputs reproducing transcript labels: {report['removed_output_transcript_label_count']}/{report['observation_count_per_condition']}",
            f"- Mechanism supported: **{'YES' if report['mechanism_supported'] else 'NO'}**",
            "",
            "## Mechanism",
            "",
            report["mechanism"],
            "",
            "## Next Falsifiable Hypothesis",
            "",
            report["next_falsifiable_hypothesis"],
            "",
            "This diagnosis is aggregate-only and does not change the frozen V84 decision or authorize training/runtime changes.",
            "",
        ]
    )


def main():
    packets = v76.load_jsonl(ROOT / "analysis/local_planner_memory_causality_v84/packets.jsonl")
    rows = v76.load_jsonl(ROOT / "analysis/local_planner_memory_causality_v84/raw.jsonl")
    report = diagnose(packets, rows)
    json_path = ROOT / "reports/planner_memory_causality_v84_diagnosis.json"
    md_path = ROOT / "reports/planner_memory_causality_v84_diagnosis.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({"mechanism_supported": report["mechanism_supported"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
