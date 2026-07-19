#!/usr/bin/env python3
"""Aggregate post-hoc diagnosis for V86 required/forbidden conflicts."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import planner_outcome_evaluator_v83 as v83
import planner_supervision_v76 as v76
import rightbrain_memory_surface_v86 as v86


ROOT = Path(__file__).resolve().parent


def _compact(value):
    return "".join(str(value or "").split())


def stale_opening_conflicts(packet, candidate):
    plan = candidate.get("target_plan") or {}
    speech = plan.get("human_speech_plan") or {}
    recent = [str(value or "").strip() for value in (speech.get("forbidden_repetition") or {}).get("recent_openings") or []]
    forbidden = [str(value or "").strip() for value in plan.get("must_avoid") or []]
    semantic_values = [
        str(plan.get("core_message_jp") or ""),
        *[str(value or "") for value in speech.get("content_units") or []],
        *[str(value or "") for value in speech.get("grounding_terms") or []],
        *[str(value or "") for group in packet["outcome_contract"]["required_semantic_groups"] for value in group],
    ]
    conflicts = []
    for marker in recent:
        compact_marker = _compact(marker)
        if not compact_marker or marker not in forbidden:
            continue
        if any(compact_marker in _compact(value) for value in semantic_values):
            conflicts.append(marker)
    return list(dict.fromkeys(conflicts))


def diagnose(packets, rows, candidates):
    candidates_by_id = {candidate["id"]: candidate for candidate in candidates}
    conflicts_by_id = {
        packet["candidate_id"]: stale_opening_conflicts(packet, candidates_by_id[packet["candidate_id"]])
        for packet in packets
    }
    conflict_packet_count = sum(bool(values) for values in conflicts_by_id.values())
    conflict_marker_count = sum(len(values) for values in conflicts_by_id.values())
    violations = Counter()
    conflict_explained = Counter()
    for row in rows:
        if not row["score"]["forbidden_violation"]:
            continue
        condition = row["condition"]
        violations[condition] += 1
        reply = str(row.get("raw_reply") or "")
        if any(v83._marker_hit(reply, marker) for marker in conflicts_by_id[row["candidate_id"]]):
            conflict_explained[condition] += 1
    treatment_violations = violations[v86.T2]
    mechanism_supported = treatment_violations > 0 and conflict_explained[v86.T2] == treatment_violations
    return {
        "schema": "uruha_rightbrain_memory_surface_diagnosis_v86",
        "diagnosis_type": "post_hoc_mechanism_diagnosis_does_not_change_preregistered_decision",
        "preregistered_decision": "inconclusive_effect_between_preregistered_gates",
        "packet_count": len(packets),
        "packets_with_stale_opening_required_conflict": conflict_packet_count,
        "stale_opening_conflict_marker_count": conflict_marker_count,
        "forbidden_violation_count_by_condition": {
            condition: violations[condition] for condition in v86.CONDITIONS
        },
        "conflict_explained_violation_count_by_condition": {
            condition: conflict_explained[condition] for condition in v86.CONDITIONS
        },
        "mechanism_supported": mechanism_supported,
        "mechanism": (
            "The speech-plan repetition guard copied recent reply openings into must_avoid even when the current "
            "LeftBrain meaning required the same opening. RightBrain therefore received a contract that required "
            "and forbade the same phrase."
        ),
        "next_falsifiable_hypothesis": (
            "Projecting only stale recent-opening conflicts out of the RightBrain forbidden list can remove the "
            "contract contradiction without weakening hard safety, persona, or generic-repetition prohibitions."
        ),
        "authorizations": {
            "production_shadow": False,
            "production_default": False,
            "training_data": False,
            "v86_decision_override": False,
        },
        "privacy": {
            "raw_reply_text_in_report": False,
            "forbidden_marker_text_in_report": False,
            "candidate_or_session_ids_in_report": False,
        },
    }


def render_markdown(report):
    return "\n".join(
        [
            "# V86 Post-hoc Contract-Conflict Diagnosis",
            "",
            f"- Frozen decision remains: `{report['preregistered_decision']}`",
            f"- Fresh packets with a stale-opening conflict: {report['packets_with_stale_opening_required_conflict']}/{report['packet_count']}",
            f"- Treatment forbidden violations explained by the conflict: {report['conflict_explained_violation_count_by_condition'][v86.T2]}/{report['forbidden_violation_count_by_condition'][v86.T2]}",
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
            "This aggregate diagnosis does not change V86 or authorize runtime activation.",
            "",
        ]
    )


def main():
    contract = json.loads((ROOT / "configs/rightbrain_memory_surface_v86_preregistration.json").read_text(encoding="utf-8"))
    packets = v76.load_jsonl(ROOT / contract["local_paths"]["packet_queue"])
    rows = v76.load_jsonl(ROOT / contract["local_paths"]["raw_results"])
    candidates = v76.load_jsonl(ROOT / contract["private_sources"]["candidate_queue"]["path"])
    report = diagnose(packets, rows, candidates)
    json_path = ROOT / "reports/rightbrain_memory_surface_v86_diagnosis.json"
    md_path = ROOT / "reports/rightbrain_memory_surface_v86_diagnosis.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({"mechanism_supported": report["mechanism_supported"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
