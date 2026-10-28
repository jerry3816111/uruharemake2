import hashlib
import json
from pathlib import Path

import p4_ay_response_form_constraint_boundary_gate as gate
import uruha_compound_feedback_request_split_p4 as p4_ax
import uruha_executed_action_outcome_closure_p4 as p4_at
import uruha_source_bound_current_action_delivery_p4 as p4_au


ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "datasets" / "p4_ay_response_form_constraint_boundary_v1.json"
BEFORE = ROOT / "analysis" / "p4_ay_response_form_constraint_boundary_before_2026-09-26.json"


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _before_metrics():
    contract = gate.load_contract()
    dataset = gate.load_dataset(contract)
    p4_ax.install_compound_feedback_request_split_hook_p4_ax()
    rows = []
    for partition in ("development_sequences", "fresh_positive_sequences", "fresh_control_sequences"):
        for frozen in dataset[partition]:
            feedback = p4_au._fixture_feedback(frozen)
            memory = {
                "recent_turns": [
                    {
                        "user": frozen["turn_1"],
                        "reply": "verified previous visible clarification",
                        "episode_id": f"before-{frozen['case_id']}",
                    }
                ]
            }
            base = p4_au._ORIGINAL_SOURCE_PACKET_P4_AU(
                frozen["turn_2"], memory, feedback, turn_index=2
            )
            _sources, trace = p4_au.bind_prior_problem_source_p4_au(
                frozen["turn_2"], memory, feedback, 2, base
            )
            rows.append((partition, frozen, feedback[p4_at.LABEL], trace))

    predecessor_dataset = json.loads(
        (ROOT / dataset["predecessor_dataset"]["path"]).read_text(encoding="utf-8")
    )
    predecessor_linked = 0
    for frozen in predecessor_dataset[dataset["predecessor_dataset"]["partition"]]:
        feedback = p4_au._fixture_feedback(frozen)
        memory = {
            "recent_turns": [
                {"user": frozen["turn_1"], "reply": "previous", "episode_id": "predecessor"}
            ]
        }
        base = p4_au._ORIGINAL_SOURCE_PACKET_P4_AU(frozen["turn_2"], memory, feedback, 2)
        _sources, trace = p4_au.bind_prior_problem_source_p4_au(
            frozen["turn_2"], memory, feedback, 2, base
        )
        predecessor_linked += int(trace["prior_source_added"])

    return {
        "case_count": len(rows),
        "development_prior_source_linked_count": sum(
            trace["prior_source_added"] for partition, _frozen, _feedback, trace in rows
            if partition == "development_sequences"
        ),
        "fresh_positive_prior_source_linked_count": sum(
            trace["prior_source_added"] for partition, _frozen, _feedback, trace in rows
            if partition == "fresh_positive_sequences"
        ),
        "fresh_control_prior_source_added_count": sum(
            trace["prior_source_added"] for partition, _frozen, _feedback, trace in rows
            if partition == "fresh_control_sequences"
        ),
        "predecessor_positive_prior_source_linked_count": predecessor_linked,
        "target_gap_count": sum(
            trace["status"] == "blocked_current_task_replacement"
            for partition, _frozen, feedback, trace in rows
            if partition in {"development_sequences", "fresh_positive_sequences"}
            and (feedback.get(p4_ax.LABEL) or {}).get("status") == "bounded_support_composed"
        ),
    }


def test_p4_ay_contract_and_dataset_are_hash_bound_before_implementation():
    contract = gate.load_contract()
    dataset = gate.load_dataset(contract)

    assert contract["status"] == "prospectively_frozen_before_implementation"
    assert dataset["status"] == "prospectively_frozen_before_implementation"
    assert contract["dataset"]["sha256"] == _sha(DATASET)
    assert contract["dataset"]["case_count"] == 19
    assert contract["dataset"]["predecessor_positive_count"] == 6


def test_p4_ay_fresh_cases_are_unseen_in_existing_p4_datasets():
    dataset = json.loads(DATASET.read_text(encoding="utf-8"))
    fresh = dataset["fresh_positive_sequences"] + dataset["fresh_control_sequences"]
    prior_paths = [
        path for path in (ROOT / "datasets").glob("p4_*.json") if path != DATASET
    ]
    serialized = "\n".join(path.read_text(encoding="utf-8") for path in prior_paths)

    for row in fresh:
        assert row["turn_1"] not in serialized
        assert row["turn_2"] not in serialized


def test_p4_ay_before_evidence_reproduces_the_seven_target_gaps():
    saved = json.loads(BEFORE.read_text(encoding="utf-8"))
    metrics = _before_metrics()

    assert saved["status"] == "target_gap_reproduced_before_implementation"
    assert saved["dataset_sha256"] == _sha(DATASET)
    assert metrics == saved["metrics"]
    assert metrics["development_prior_source_linked_count"] == 0
    assert metrics["fresh_positive_prior_source_linked_count"] == 0
    assert metrics["target_gap_count"] == 7
    assert metrics["predecessor_positive_prior_source_linked_count"] == 6


def test_p4_ay_freezes_genuine_replacement_and_non_authority_controls():
    dataset = json.loads(DATASET.read_text(encoding="utf-8"))
    controls = dataset["fresh_control_sequences"]

    assert sum(row["control_family"] == "genuine_topic_replacement" for row in controls) == 3
    assert sum(row["expected_prior_source_added"] for row in controls) == 0
    assert {row["control_family"] for row in controls} == {
        "genuine_topic_replacement",
        "third_party_feedback",
        "quoted_metalinguistic_feedback",
        "receipt_mismatch",
        "non_practical_policy",
        "no_previous_action_feedback",
    }


def test_p4_ay_contract_forbids_widening_other_authority_or_delivery_gates():
    contract = gate.load_contract()
    forbidden = set(contract["single_variable"]["forbidden_changes"])

    assert "p4_ax_support_authority_or_patterns" in forbidden
    assert "p4_at_outcome_or_exact_receipt_identity" in forbidden
    assert "p4_au_prior_source_role_trigger_budget_or_turn_window" in forbidden
    assert "genuine_current_problem_or_topic_replacement_block" in forbidden
    assert "m53_m46_m45_or_m39_review_and_fail_closed" in forbidden
    assert contract["failure_policy"]["offline_pass_may_fix_or_hide_m45_json_failure"] is False
    assert contract["failure_policy"]["fresh_safari_case_required_after_offline_pass"] is True


def test_p4_ay_gate_fails_closed_when_a_metric_is_missing():
    contract = gate.load_contract()
    result = gate.evaluate_offline_evidence(
        contract,
        {
            "schema": "uruha_p4_ay_response_form_constraint_boundary_evidence_v1",
            "dataset_sha256": contract["dataset"]["sha256"],
            "metrics": {},
        },
    )

    assert result["status"] == "fail"
    assert len(result["failed_gates"]) == len(contract["offline_gates"])
