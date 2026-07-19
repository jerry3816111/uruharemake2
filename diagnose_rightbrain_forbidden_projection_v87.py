#!/usr/bin/env python3
"""Diagnose the post-hoc control-setting mismatch in the V87 replay."""

from __future__ import annotations

import copy
import json
from collections import Counter
from pathlib import Path

import rightbrain_forbidden_projection_v87 as v87
import run_rightbrain_forbidden_projection_v87 as runner
from uruha_brain_mac import RightBrain


ROOT = Path(__file__).resolve().parent
PREREG_PATH = ROOT / "configs/rightbrain_forbidden_projection_v87_preregistration.json"
FORMAL_REPORT_PATH = ROOT / "reports/rightbrain_forbidden_projection_v87.json"


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def evaluate_setting(right_brain, bound, *, canonical, explicit_length, projection):
    previous = (
        right_brain.memory_cue_canonicalization_enabled,
        right_brain.explicit_length_contract_enabled,
        right_brain.forbidden_conflict_projection_enabled,
    )
    right_brain.memory_cue_canonicalization_enabled = canonical
    right_brain.explicit_length_contract_enabled = explicit_length
    right_brain.forbidden_conflict_projection_enabled = projection
    reason_counts = Counter()
    accepted = 0
    contract_matches = 0
    projected_markers = 0
    try:
        for packet, row, candidate in bound:
            logic = copy.deepcopy(candidate["target_plan"])
            expected_groups = packet["outcome_contract"]["required_semantic_groups"]
            observed_groups = [list(group) for group in right_brain._model_required_semantic_groups(logic)]
            contract_matches += observed_groups == expected_groups
            reasons = right_brain._model_candidate_rejection_reasons(
                row["raw_reply"],
                logic,
                int(packet["outcome_contract"]["maximum_reply_chars"]),
            )
            accepted += not reasons
            reason_counts.update(reasons)
            projected_markers += int(
                (logic.get("model_surface_forbidden_projection") or {}).get(
                    "dropped_stale_recent_opening_count"
                )
                or 0
            )
    finally:
        (
            right_brain.memory_cue_canonicalization_enabled,
            right_brain.explicit_length_contract_enabled,
            right_brain.forbidden_conflict_projection_enabled,
        ) = previous
    semantic_rejections = sum(
        count for reason, count in reason_counts.items() if reason.startswith("semantic_slots_missing:")
    )
    return {
        "canonical_memory_cue": canonical,
        "explicit_length_contract": explicit_length,
        "forbidden_conflict_projection": projection,
        "case_count": len(bound),
        "required_contract_match_count": contract_matches,
        "gate_accept_count": accepted,
        "semantic_rejection_count": semantic_rejections,
        "must_avoid_rejection_count": reason_counts["must_avoid_violation"],
        "projected_marker_count": projected_markers,
    }


def diagnose(contract, formal_report, packets, raw_rows, candidates):
    right_brain = RightBrain(load_model=False)
    defaults = {
        "canonical_memory_cue": bool(right_brain.memory_cue_canonicalization_enabled),
        "explicit_length_contract": bool(right_brain.explicit_length_contract_enabled),
        "forbidden_conflict_projection": bool(right_brain.forbidden_conflict_projection_enabled),
    }
    bound = v87.bind_cases(packets, raw_rows, candidates, contract)
    observed_control = evaluate_setting(
        right_brain,
        bound,
        canonical=defaults["canonical_memory_cue"],
        explicit_length=defaults["explicit_length_contract"],
        projection=False,
    )
    observed_treatment = evaluate_setting(
        right_brain,
        bound,
        canonical=defaults["canonical_memory_cue"],
        explicit_length=defaults["explicit_length_contract"],
        projection=True,
    )
    intended_control = evaluate_setting(
        right_brain,
        bound,
        canonical=True,
        explicit_length=True,
        projection=False,
    )
    intended_treatment = evaluate_setting(
        right_brain,
        bound,
        canonical=True,
        explicit_length=True,
        projection=True,
    )
    formal_summary = formal_report["summary"]
    formal_reproduction_matches = (
        observed_control["gate_accept_count"] == round(formal_summary["control_gate_accept_rate"] * len(bound))
        and observed_treatment["gate_accept_count"]
        == round(formal_summary["treatment_gate_accept_rate"] * len(bound))
        and observed_treatment["projected_marker_count"] == formal_summary["projected_marker_count"]
    )
    control_variable_violation = (
        "same memory-cue and explicit-length settings" in contract["controls"]
        and not defaults["canonical_memory_cue"]
        and not defaults["explicit_length_contract"]
        and observed_control["required_contract_match_count"] < len(bound)
        and intended_control["required_contract_match_count"] == len(bound)
    )
    return {
        "schema": "uruha_rightbrain_forbidden_projection_diagnosis_v87_1",
        "diagnosis_type": "post_hoc_control_variable_audit_does_not_change_v87_decision",
        "formal_v87_decision": formal_report["decision"],
        "formal_v87_integrity_flag": formal_report["integrity_passed"],
        "formal_reproduction_matches": formal_reproduction_matches,
        "control_variable_violation_found": control_variable_violation,
        "root_cause": (
            "The V87 replay left canonical memory cues and the explicit length contract at their default-off "
            "runtime values even though the preregistration required the frozen V86 treatment settings. The "
            "candidate gate therefore evaluated a different semantic contract from the V86 replies."
        ),
        "observed_v87_settings": {
            "control": observed_control,
            "treatment": observed_treatment,
        },
        "intended_v86_treatment_settings_post_hoc_preview": {
            "control": intended_control,
            "treatment": intended_treatment,
        },
        "next_falsifiable_step": (
            "Preregister and lock a corrected V87.2 paired replay that explicitly sets canonical memory cues "
            "and the explicit length contract to true in both conditions, while changing only forbidden-conflict projection."
        ),
        "authorizations": {
            "v87_decision_override": False,
            "fresh_full_pipeline_holdout": False,
            "production_shadow": False,
            "production_default": False,
            "training_data": False,
        },
        "privacy": {
            "raw_reply_text_in_report": False,
            "forbidden_marker_text_in_report": False,
            "candidate_or_session_ids_in_report": False,
        },
    }


def render_markdown(report):
    observed = report["observed_v87_settings"]
    intended = report["intended_v86_treatment_settings_post_hoc_preview"]
    return "\n".join(
        [
            "# V87 Post-hoc Control-Variable Diagnosis",
            "",
            f"- Formal V87 decision remains: `{report['formal_v87_decision']}`",
            f"- Formal replay reproduced: **{'YES' if report['formal_reproduction_matches'] else 'NO'}**",
            f"- Control-variable violation found: **{'YES' if report['control_variable_violation_found'] else 'NO'}**",
            "",
            "| Replay setting | Contract match | Gate accept | Semantic rejects | Projected markers |",
            "|---|---:|---:|---:|---:|",
            f"| Observed control | {observed['control']['required_contract_match_count']}/12 | {observed['control']['gate_accept_count']}/12 | {observed['control']['semantic_rejection_count']} | {observed['control']['projected_marker_count']} |",
            f"| Observed treatment | {observed['treatment']['required_contract_match_count']}/12 | {observed['treatment']['gate_accept_count']}/12 | {observed['treatment']['semantic_rejection_count']} | {observed['treatment']['projected_marker_count']} |",
            f"| Intended control (post-hoc) | {intended['control']['required_contract_match_count']}/12 | {intended['control']['gate_accept_count']}/12 | {intended['control']['semantic_rejection_count']} | {intended['control']['projected_marker_count']} |",
            f"| Intended treatment (post-hoc) | {intended['treatment']['required_contract_match_count']}/12 | {intended['treatment']['gate_accept_count']}/12 | {intended['treatment']['semantic_rejection_count']} | {intended['treatment']['projected_marker_count']} |",
            "",
            "## Root Cause",
            "",
            report["root_cause"],
            "",
            "The intended-setting rows are exploratory diagnostics, not a replacement formal result.",
            "",
            "## Next Falsifiable Step",
            "",
            report["next_falsifiable_step"],
            "",
        ]
    )


def main():
    contract = load_json(PREREG_PATH)
    formal_report = load_json(FORMAL_REPORT_PATH)
    v87.verify_sources(contract, ROOT)
    packets, raw_rows, candidates = runner.load_sources(contract)
    report = diagnose(contract, formal_report, packets, raw_rows, candidates)
    json_path = ROOT / "reports/rightbrain_forbidden_projection_v87_diagnosis.json"
    md_path = ROOT / "reports/rightbrain_forbidden_projection_v87_diagnosis.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    print(
        json.dumps(
            {
                "control_variable_violation_found": report["control_variable_violation_found"],
                "formal_v87_decision": report["formal_v87_decision"],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
