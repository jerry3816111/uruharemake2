import hashlib
import json
from pathlib import Path

import p4_az_previous_turn_cjk_ellipsis_authority_gate as gate
import uruha_compound_feedback_request_split_p4 as p4_ax
import uruha_response_form_constraint_boundary_p4 as p4_ay
import uruha_source_bound_current_action_delivery_p4 as p4_au


ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "datasets" / "p4_az_previous_turn_cjk_ellipsis_authority_v1.json"
BEFORE = ROOT / "analysis" / "p4_az_previous_turn_cjk_ellipsis_authority_before_2026-09-26.json"


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _evaluate_prechange(frozen):
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
    sources, p4_au_trace = p4_au.bind_prior_problem_source_p4_au(
        frozen["turn_2"], memory, feedback, 2, base
    )
    sources, updated_p4_au, p4_ay_trace = p4_ay.refine_response_form_constraint_boundary_p4_ay(
        frozen["turn_2"], memory, feedback, 2, sources, p4_au_trace
    )
    exact_sources = [row for row in sources if row.get("source_role") == "p4_au_exact_prior_problem"]
    return updated_p4_au, p4_ay_trace, exact_sources


def _before_metrics():
    contract = gate.load_contract()
    dataset = gate.load_dataset(contract)
    p4_ax.install_compound_feedback_request_split_hook_p4_ax()
    rows = []
    for partition in ("development_sequences", "fresh_positive_sequences", "fresh_control_sequences"):
        for frozen in dataset[partition]:
            updated_p4_au, p4_ay_trace, sources = _evaluate_prechange(frozen)
            rows.append((partition, frozen, updated_p4_au, p4_ay_trace, sources))

    predecessor = json.loads(
        (ROOT / dataset["predecessor_dataset"]["path"]).read_text(encoding="utf-8")
    )
    predecessor_present = 0
    for frozen in predecessor[dataset["predecessor_dataset"]["partition"]]:
        _updated, _p4_ay, sources = _evaluate_prechange(frozen)
        predecessor_present += int(bool(sources))

    return {
        "case_count": len(rows),
        "development_prior_source_linked_count": sum(bool(sources) for partition, _frozen, _au, _ay, sources in rows if partition == "development_sequences"),
        "fresh_positive_prior_source_linked_count": sum(bool(sources) for partition, _frozen, _au, _ay, sources in rows if partition == "fresh_positive_sequences"),
        "fresh_control_prior_source_added_count": sum(bool(sources) for partition, _frozen, _au, _ay, sources in rows if partition == "fresh_control_sequences"),
        "predecessor_positive_prior_source_present_count": predecessor_present,
        "target_gap_count": sum(not sources for partition, _frozen, _au, _ay, sources in rows if partition in {"development_sequences", "fresh_positive_sequences"}),
    }


def test_p4_az_contract_and_dataset_are_hash_bound_before_implementation():
    contract = gate.load_contract()
    dataset = gate.load_dataset(contract)

    assert contract["status"] == "prospectively_frozen_before_implementation"
    assert dataset["status"] == "prospectively_frozen_before_implementation"
    assert contract["dataset"]["sha256"] == _sha(DATASET)
    assert contract["dataset"]["case_count"] == 19
    assert contract["dataset"]["predecessor_positive_count"] == 6


def test_p4_az_fresh_cases_are_unseen_in_existing_p4_datasets():
    dataset = json.loads(DATASET.read_text(encoding="utf-8"))
    fresh = dataset["fresh_positive_sequences"] + dataset["fresh_control_sequences"]
    prior_paths = [path for path in (ROOT / "datasets").glob("p4_*.json") if path != DATASET]
    serialized = "\n".join(path.read_text(encoding="utf-8") for path in prior_paths)

    for row in fresh:
        assert row["turn_1"] not in serialized
        assert row["turn_2"] not in serialized


def test_p4_az_before_evidence_reproduces_seven_source_role_gaps():
    saved = json.loads(BEFORE.read_text(encoding="utf-8"))
    metrics = _before_metrics()

    assert saved["dataset_sha256"] == _sha(DATASET)
    assert metrics == saved["metrics"]
    assert metrics["development_prior_source_linked_count"] == 0
    assert metrics["fresh_positive_prior_source_linked_count"] == 0
    assert metrics["target_gap_count"] == 7
    assert metrics["predecessor_positive_prior_source_present_count"] == 6


def test_p4_az_controls_cover_each_forbidden_authority_family():
    dataset = json.loads(DATASET.read_text(encoding="utf-8"))
    controls = dataset["fresh_control_sequences"]

    assert len(controls) == 12
    assert sum(row["expected_prior_source_added"] for row in controls) == 0
    assert {row["control_family"] for row in controls} == {
        "third_party",
        "quoted_metalinguistic",
        "news_or_report",
        "physical_object_motion",
        "resolved_state",
        "hypothetical_or_ambiguous",
    }
    assert all(row["expected_status"] == "blocked_prior_source_authority" for row in controls)


def test_p4_az_contract_preserves_unspecified_role_and_all_other_gates():
    contract = gate.load_contract()
    forbidden = set(contract["single_variable"]["forbidden_changes"])

    assert "source_role_rewrite_to_user_first_person" in forbidden
    assert "p4_ay_task_replacement_discrimination" in forbidden
    assert "p4_au_turn_window_budget_trigger_or_non_role_guards" in forbidden
    assert "m53_m46_m45_or_m39_review_and_fail_closed" in forbidden
    assert contract["failure_policy"]["offline_pass_may_fix_or_hide_m45_json_failure"] is False
    assert contract["failure_policy"]["fresh_safari_case_required_after_offline_pass"] is True


def test_p4_az_gate_fails_closed_when_a_metric_is_missing():
    contract = gate.load_contract()
    result = gate.evaluate_offline_evidence(
        contract,
        {
            "schema": "uruha_p4_az_previous_turn_cjk_ellipsis_authority_evidence_v1",
            "dataset_sha256": contract["dataset"]["sha256"],
            "metrics": {},
        },
    )

    assert result["status"] == "fail"
    assert len(result["failed_gates"]) == len(contract["offline_gates"])
