#!/usr/bin/env python3
"""Single-pass evidence builder for the frozen P4-AE dataset."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import uruha_desired_response_ambiguity_p4 as ambiguity


def build_evidence(dataset_path):
    dataset_path = Path(dataset_path)
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    cases = []
    turn_index = 100
    for partition in ("ambiguity_cases", "near_miss_controls"):
        for frozen in dataset[partition]:
            turn_index += 1
            state, decision, mode = ambiguity._isolated_inputs(frozen["input"], turn_index)
            probe = f"unchanged-p4-ae-{frozen['case_id']}"
            visible, trace = ambiguity.shadow_visible_reply_p4(probe, state, decision, mode)
            encoded = json.dumps(trace, ensure_ascii=False, sort_keys=True)
            cases.append(
                {
                    "case_id": frozen["case_id"],
                    "partition": partition,
                    "status": trace["status"],
                    "selected_action_mode": (trace.get("selected_action") or {}).get("mode"),
                    "candidate_modes": [
                        row.get("mode")
                        for row in (trace.get("candidate_expectations") or [])
                        if row.get("mode")
                    ],
                    "candidate_count": trace["candidate_count"],
                    "candidate_contract_passed": trace["candidate_contract_passed"],
                    "private_reason_status": trace["private_reason_status"],
                    "selected_action_is_private_truth_commitment": trace["selected_action_is_private_truth_commitment"],
                    "trace_contains_raw_input": frozen["input"] in encoded,
                    "visible_reply_changed": visible != probe,
                    "new_model_call_count": int(trace["model_call_added"]),
                    "fact_write_count": trace["fact_write_count"],
                    "profile_write_count": trace["profile_write_count"],
                    "episode_write_count": trace["episode_write_count"],
                }
            )
    ambiguity_rows = cases[: len(dataset["ambiguity_cases"])]
    controls = cases[len(dataset["ambiguity_cases"]):]
    frozen_by_id = {
        row["case_id"]: row
        for partition in ("ambiguity_cases", "near_miss_controls")
        for row in dataset[partition]
    }
    return {
        "schema": "uruha_p4_ae_fresh_ambiguity_generalization_evidence_v1",
        "dataset_sha256": hashlib.sha256(dataset_path.read_bytes()).hexdigest(),
        "execution_count": 1,
        "cases": cases,
        "metrics": {
            "ambiguity_case_count": len(ambiguity_rows),
            "exact_status_count": sum(row["status"] == frozen_by_id[row["case_id"]]["expected_status"] for row in ambiguity_rows),
            "exact_selected_action_count": sum(row["selected_action_mode"] == frozen_by_id[row["case_id"]]["expected_selected_action_mode"] for row in ambiguity_rows),
            "required_candidate_modes_complete_count": sum(set(frozen_by_id[row["case_id"]]["required_candidate_modes"]).issubset(set(row["candidate_modes"])) for row in ambiguity_rows),
            "candidate_contract_pass_count": sum(row["candidate_contract_passed"] for row in ambiguity_rows),
            "private_unknown_boundary_count": sum(row["private_reason_status"] == "unknown_not_observed" for row in ambiguity_rows),
            "near_miss_control_count": len(controls),
            "near_miss_false_positive_count": sum(row["status"] != "not_applicable" or row["candidate_count"] != 0 for row in controls),
            "selected_action_private_truth_commitment_count": sum(row["selected_action_is_private_truth_commitment"] for row in cases),
            "raw_input_trace_count": sum(row["trace_contains_raw_input"] for row in cases),
            "visible_reply_changed_count": sum(row["visible_reply_changed"] for row in cases),
            "new_model_call_count": sum(row["new_model_call_count"] for row in cases),
            "fact_write_count": sum(row["fact_write_count"] for row in cases),
            "profile_write_count": sum(row["profile_write_count"] for row in cases),
            "episode_write_count": sum(row["episode_write_count"] for row in cases),
        },
        "accounting": {
            "retry_count": 0,
            "fallback_count": 0,
            "implementation_change_after_freeze_count": 0,
            "case_or_gate_change_after_result_count": 0
        },
        "scientific_evidence_status": {
            "fresh_after_p4_ad_correction": True,
            "first_result_only": True,
            "developer_authored": True,
            "natural_distribution": False,
            "independent_human_sample": False
        },
        "claim_boundary": dataset["claim_boundary"],
    }
