import hashlib
import json
from pathlib import Path

import uruha_adaptive_person_model as adaptive
import uruha_desired_response_ambiguity_p4 as ambiguity
import uruha_desired_response_eligibility_p4 as eligibility
import uruha_multilingual_observable_trigger_p4 as trigger
import p4_aq_live_extended_trigger_ordering_gate as gate


ROOT = Path(__file__).resolve().parent


def test_contract_binds_fresh_cases_and_unchanged_predecessors():
    contract = gate.load_contract()
    dataset_path = ROOT / contract["dataset"]["path"]
    assert hashlib.sha256(dataset_path.read_bytes()).hexdigest() == contract["dataset"]["sha256"]
    for path_text, digest in contract["predecessors"].values():
        assert hashlib.sha256((ROOT / path_text).read_bytes()).hexdigest() == digest
    prior_inputs = set()
    for path in (ROOT / "datasets").glob("p4_a*.json"):
        if path == dataset_path:
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        for partition in (
            "development_cases",
            "fresh_positive_cases",
            "fresh_control_cases",
            "turns",
        ):
            prior_inputs.update(
                row.get("input") for row in payload.get(partition, []) if row.get("input")
            )
    dataset = gate.load_dataset(contract)
    fresh_inputs = {
        row["input"]
        for partition in ("fresh_positive_cases", "fresh_control_cases")
        for row in dataset[partition]
    }
    assert fresh_inputs.isdisjoint(prior_inputs)


def test_preflight_has_three_extended_only_languages_and_guarded_controls():
    dataset = gate.load_dataset(gate.load_contract())
    positives = dataset["fresh_positive_cases"]
    controls = dataset["fresh_control_cases"]
    assert {row["language"] for row in positives} == {"zh", "en", "ja"}
    assert {row["language"] for row in controls} == {"zh", "en", "ja"}
    assert {row["control_type"] for row in controls} == {
        "literal_or_metalinguistic",
        "resolved_state",
        "ordinary_motion",
    }
    for row in positives:
        base = adaptive.extract_observable_trigger_predicates_m37(row["input"])
        extended = trigger.extend_observable_trigger_p4(row["input"], base)
        assert base["predicates"] == []
        assert (extended["coverage_extension"] or {})["status"] == "additive_compositional_trigger"
        assert extended["predicates"] == ["cognitive_overactivity"]
    for row in controls:
        base = adaptive.extract_observable_trigger_predicates_m37(row["input"])
        extended = trigger.extend_observable_trigger_p4(row["input"], base)
        assert base["predicates"] == []
        assert (extended["coverage_extension"] or {})["status"] == "abstained_no_bounded_composition"
        assert extended["predicates"] == []


def test_preserved_p4_an_mode_reproduces_zero_candidate_before_boundary():
    frozen = gate.load_dataset(gate.load_contract())["development_cases"][0]
    state, decision, _ = ambiguity._isolated_inputs(frozen["input"], 1)
    mode = adaptive.build_desired_response_mode_contract(
        {"selected_type": "general_conversation"},
        state,
        decision,
    )
    before = eligibility.build_desired_response_eligibility_guard_p4(
        state,
        decision,
        mode,
    )
    extended = trigger.extend_observable_trigger_p4(
        frozen["input"], state["observable_trigger_m37"]
    )
    repaired_state = trigger.apply_extended_trigger_to_shadow_state_p4(state, extended)
    after = eligibility.build_desired_response_eligibility_guard_p4(
        repaired_state,
        decision,
        mode,
    )
    assert mode["eligible"] is frozen["expected_predecessor_mode_eligible"]
    assert before["candidate_count"] == frozen["expected_predecessor_candidate_count"]
    assert after["candidate_count"] == frozen["expected_candidate_count"]
    assert (after["eligibility"] or {})["authority"] == frozen["expected_eligibility_authority"]


def test_contract_forbids_rule_reply_and_real_execution_changes():
    contract = gate.load_contract()
    boundary = contract["implementation_boundary"]
    assert boundary["trigger_detector_change_allowed"] is False
    assert boundary["eligibility_authority_change_allowed"] is False
    assert boundary["candidate_score_or_order_change_allowed"] is False
    assert boundary["feedback_classifier_change_allowed"] is False
    assert boundary["temporal_or_identity_rule_change_allowed"] is False
    assert boundary["visible_reply_or_prompt_change_allowed"] is False
    assert contract["failure_policy"]["real_product_or_safari_execution_authorized"] is False
