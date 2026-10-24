"""Zero-model admission contracts; the separate fresh Safari set is not used here."""

from copy import deepcopy
import os
import subprocess
import sys
from unittest.mock import patch

import pytest

import uruha_adaptive_person_model as adaptive
import uruha_reported_ack_m31_priority_p4 as priority
import uruha_reported_ack_route_admission_p4 as admission
import uruha_temporal_actor_scope_p4 as actor_scope
from uruha_brain_mac import LeftBrain


SOURCE = "同僚が「先に確認して」と言っていた。"
BASE_CLASSIFIER = adaptive.classify_explicit_desired_response_m25


def _projection(text=SOURCE):
    return {
        "schema": adaptive.LITERAL_TOPIC_PROJECTION_SCHEMA_M29,
        "projection_required": True,
        "surface_authority": False,
        "input_digest": priority._digest(text),
        "required_observable_act": None,
    }


def _classifier(text):
    return actor_scope.gate_base_explicit_request_p4(
        text, BASE_CLASSIFIER
    )


def _context(text=SOURCE):
    return {
        "schema": admission.CONTEXT_SCHEMA,
        "input_digest": priority._digest(text),
        "seed_plan": {"intent": "chat", "scene": "casual"},
        "seed_plan_status_p4": "matched_rule",
        "actual_intent": "chat",
        "actual_scene": "casual",
        "route_info": {"route": "high_road", "reason": "deliberative"},
        "semantic_route_m22": {
            "schema": "uruha_semantic_route_taxonomy_m22",
            "selected_type": "general_conversation",
            "recommended_route": "existing_guarded_router",
            "candidates": [{"task_type": "general_conversation", "score": 0.4}],
            "evidence": [{"task_type": "general_conversation", "cue_id": "no_decisive_specialized_cue"}],
            "overlap_types": [],
            "decisive_evidence": ["no_decisive_specialized_cue"],
        },
        "grounded_profile_logic_present": False,
    }


def _candidate(source=SOURCE, projection=None):
    with patch.object(
        adaptive, "classify_explicit_desired_response_m25", _classifier
    ):
        return priority.reported_ack_m31_certificate_p4(
            source, projection or _projection(source),
            adaptive.classify_explicit_desired_response_m25,
        )


def test_ordinary_route_and_same_turn_certificate_admit_without_original_m31():
    certificate = _candidate()
    assert certificate is not None
    decision = admission.route_admission_contract_p4(
        SOURCE, _projection(), _context(), certificate
    )
    assert decision["status"] == "admitted"
    assert decision["m31_model_call_skipped"] is True
    assert SOURCE not in repr(decision)
    old = admission._ORIGINAL_M31
    try:
        admission._ORIGINAL_M31 = lambda *_: (_ for _ in ()).throw(
            AssertionError("original M31 should not run")
        )
        with patch.object(
            adaptive, "classify_explicit_desired_response_m25", _classifier
        ):
            plan, authorization = admission.authorize_literal_topic_with_route_context_p4(
                None, SOURCE, _projection(), _context()
            )
    finally:
        admission._ORIGINAL_M31 = old
    assert plan is None
    assert authorization["status"] == "deferred_to_reported_ack_p4"
    assert authorization["model_call_attempted"] is False
    assert authorization[admission.LABEL]["status"] == "admitted"


def test_true_no_rule_match_has_explicit_seed_provenance_and_can_admit():
    left = LeftBrain.__new__(LeftBrain)
    actual = left.classify_user_signal(
        SOURCE, {"mood": 0.0, "trust": 50.0}, {}
    )
    assert actual["seed_plan"] == {}
    assert actual["seed_plan_status_p4"] == "no_rule_match"
    assert (actual["actual_intent"], actual["actual_scene"]) == ("chat", "casual")
    context = _context()
    context.update({
        "seed_plan": actual["seed_plan"],
        "seed_plan_status_p4": actual["seed_plan_status_p4"],
        "actual_intent": actual["actual_intent"],
        "actual_scene": actual["actual_scene"],
    })
    certificate = _candidate()
    decision = admission.route_admission_contract_p4(
        SOURCE, _projection(), context, certificate
    )
    assert decision["status"] == "admitted"
    assert decision["seed_plan_status_p4"] == "no_rule_match"
    old = admission._ORIGINAL_M31
    try:
        admission._ORIGINAL_M31 = lambda *_: (_ for _ in ()).throw(
            AssertionError("original M31 should not run")
        )
        with patch.object(adaptive, "classify_explicit_desired_response_m25", _classifier):
            _, authorization = admission.authorize_literal_topic_with_route_context_p4(
                None, SOURCE, _projection(), context
            )
    finally:
        admission._ORIGINAL_M31 = old
    assert authorization["status"] == "deferred_to_reported_ack_p4"
    assert authorization[admission.LABEL]["status"] == "admitted"


@pytest.mark.parametrize("mutation,reason", [
    ({"route_info": {"route": "low_road", "cognitive_hijack": True}}, "protected_or_unverified_signal_route"),
    ({"route_info": {"route": "high_road", "reason": "acute_crisis", "intent": "crisis_support"}}, "protected_or_unverified_signal_route"),
    ({"seed_plan": {"intent": "crisis_support", "scene": "boundary"}}, "seed_provenance_missing_or_not_ordinary"),
    ({"seed_plan": {}}, "seed_provenance_missing_or_not_ordinary"),
    ({"seed_plan": None}, "route_context_missing_or_malformed"),
    ({"seed_plan": {"intent": "chat"}}, "seed_provenance_missing_or_not_ordinary"),
    ({"seed_plan_status_p4": None}, "seed_provenance_missing_or_not_ordinary"),
    ({"seed_plan_status_p4": "unknown"}, "seed_provenance_missing_or_not_ordinary"),
    ({"seed_plan_status_p4": "no_rule_match"}, "seed_provenance_missing_or_not_ordinary"),
    ({"actual_intent": "hallucination_safe"}, "seed_or_actual_signal_not_ordinary_chat"),
    ({"semantic_route_m22": {"schema": "uruha_semantic_route_taxonomy_m22", "selected_type": "safety_sensitive", "recommended_route": "protected"}}, "m22_not_exclusively_general_conversation"),
    ({"semantic_route_m22": {"schema": "uruha_semantic_route_taxonomy_m22", "selected_type": "factual_or_memory", "recommended_route": "grounded"}}, "m22_not_exclusively_general_conversation"),
    ({"grounded_profile_logic_present": True}, "factual_grounding_present_or_unknown"),
    ({"route_info": None}, "route_context_missing_or_malformed"),
    ({"input_digest": "0" * 16}, "same_turn_digest_missing_or_mismatched"),
    ({"semantic_route_m22": {"schema": "uruha_semantic_route_taxonomy_m22", "selected_type": "general_conversation", "recommended_route": "existing_guarded_router", "decisive_evidence": ["no_decisive_specialized_cue"], "overlap_types": [], "candidates": ["invalid"]}}, "m22_not_exclusively_general_conversation"),
    ({"semantic_route_m22": {"schema": "uruha_semantic_route_taxonomy_m22", "selected_type": "general_conversation", "recommended_route": "existing_guarded_router", "decisive_evidence": ["no_decisive_specialized_cue"], "overlap_types": [], "candidates": [{"task_type": "general_conversation"}], "evidence": [{"task_type": "safety_sensitive", "cue_id": "protected_low_road"}]}}, "m22_not_exclusively_general_conversation"),
])
def test_protected_factual_missing_or_contradictory_context_calls_original_once(mutation, reason):
    context = {**_context(), **mutation}
    source_projection = _projection()
    sentinel = ({"original": True}, {"status": "original_m31", "surface_authority": False})
    calls = []
    old = admission._ORIGINAL_M31
    try:
        def original(_self, source, projection):
            calls.append((source, projection))
            return sentinel
        admission._ORIGINAL_M31 = original
        with patch.object(
            adaptive, "classify_explicit_desired_response_m25", _classifier
        ):
            plan, authorization = admission.authorize_literal_topic_with_route_context_p4(
                None, SOURCE, source_projection, context
            )
    finally:
        admission._ORIGINAL_M31 = old
    assert plan is sentinel[0]
    assert calls == [(SOURCE, source_projection)]
    assert calls[0][1] is source_projection
    assert authorization["status"] == "original_m31"
    assert authorization[admission.LABEL]["status"] == "rejected"
    assert authorization[admission.LABEL]["reason"] == reason
    assert admission.LABEL not in sentinel[1]


@pytest.mark.parametrize("source", [
    "同僚が「先に確認して」と言っていた。あとでうるはも聞いて。",
    "先に確認して。",
    "同僚が確認が必要だと言っていた。",
])
def test_non_single_or_direct_or_unknown_never_defer(source):
    calls = []
    old = admission._ORIGINAL_M31
    try:
        def original(_self, text, projection):
            calls.append(text)
            return None, {"status": "original_m31"}
        admission._ORIGINAL_M31 = original
        with patch.object(
            adaptive, "classify_explicit_desired_response_m25", _classifier
        ):
            _, authorization = admission.authorize_literal_topic_with_route_context_p4(
                None, source, _projection(source), _context(source)
            )
    finally:
        admission._ORIGINAL_M31 = old
    assert calls == [source]
    assert authorization[admission.LABEL]["status"] == "not_source_candidate"


def test_missing_context_and_late_repair_fail_closed():
    calls = []
    old = admission._ORIGINAL_M31
    try:
        def original(_self, source, projection):
            calls.append((source, deepcopy(projection)))
            return None, {"status": "original_m31"}
        admission._ORIGINAL_M31 = original
        with patch.object(
            adaptive, "classify_explicit_desired_response_m25", _classifier
        ):
            _, authorization = admission.authorize_literal_topic_with_route_context_p4(
                None, SOURCE, _projection(), None
            )
        _, late = admission.authorize_literal_topic_without_route_context_p4(
            None, SOURCE, _projection()
        )
    finally:
        admission._ORIGINAL_M31 = old
    assert len(calls) == 2
    assert authorization[admission.LABEL]["reason"] == "route_context_missing_or_malformed"
    assert late["status"] == "original_m31"


def test_omitted_seed_and_omitted_marker_fail_closed():
    certificate = _candidate()
    for omitted in ("seed_plan", "seed_plan_status_p4"):
        context = _context()
        context.pop(omitted)
        decision = admission.route_admission_contract_p4(
            SOURCE, _projection(), context, certificate
        )
        assert decision["status"] == "rejected"
        assert decision["reason"] in {
            "route_context_missing_or_malformed",
            "seed_provenance_missing_or_not_ordinary",
        }
        calls = []
        old = admission._ORIGINAL_M31
        try:
            def original(_self, text, proposed):
                calls.append((text, proposed))
                return None, {"status": "original_m31"}
            admission._ORIGINAL_M31 = original
            projection = _projection()
            with patch.object(adaptive, "classify_explicit_desired_response_m25", _classifier):
                _, authorization = admission.authorize_literal_topic_with_route_context_p4(
                    None, SOURCE, projection, context
                )
        finally:
            admission._ORIGINAL_M31 = old
        assert calls == [(SOURCE, projection)]
        assert authorization["status"] == "original_m31"


def test_matched_seed_and_marker_remain_diagnostic_not_private_fact():
    left = LeftBrain.__new__(LeftBrain)
    with patch.object(left, "_rule_based_plan", return_value={
        "intent": "hallucination_safe", "scene": "boundary"
    }):
        actual = left.classify_user_signal(SOURCE, {}, {})
    assert actual["seed_plan_status_p4"] == "matched_rule"
    context = _context()
    context.update({
        "seed_plan": actual["seed_plan"],
        "seed_plan_status_p4": actual["seed_plan_status_p4"],
        "actual_intent": actual["actual_intent"],
        "actual_scene": actual["actual_scene"],
    })
    decision = admission.route_admission_contract_p4(
        SOURCE, _projection(), context, _candidate()
    )
    assert decision["status"] == "rejected"
    assert decision["reason"] == "seed_provenance_missing_or_not_ordinary"
    assert decision["private_state_truth_claimed"] is False


@pytest.mark.parametrize("mutation,reason", [
    ({"route_info": {"route": "low_road", "reason": "prediction_error_surprise", "cognitive_hijack": True}}, "protected_or_unverified_signal_route"),
    ({"semantic_route_m22": {"schema": "uruha_semantic_route_taxonomy_m22", "selected_type": "safety_sensitive", "recommended_route": "protected"}}, "m22_not_exclusively_general_conversation"),
    ({"semantic_route_m22": {"schema": "uruha_semantic_route_taxonomy_m22", "selected_type": "factual_or_memory", "recommended_route": "grounded"}}, "m22_not_exclusively_general_conversation"),
    ({"grounded_profile_logic_present": True}, "factual_grounding_present_or_unknown"),
    ({"input_digest": "0" * 16}, "same_turn_digest_missing_or_mismatched"),
    ({"actual_intent": "crisis_support"}, "seed_or_actual_signal_not_ordinary_chat"),
])
def test_no_rule_match_branch_still_calls_original_once_when_protected(mutation, reason):
    context = _context()
    context.update({"seed_plan": {}, "seed_plan_status_p4": "no_rule_match"})
    context.update(mutation)
    projection = _projection()
    calls = []
    old = admission._ORIGINAL_M31
    try:
        def original(_self, text, proposed):
            calls.append((text, proposed))
            return None, {"status": "original_m31"}
        admission._ORIGINAL_M31 = original
        with patch.object(adaptive, "classify_explicit_desired_response_m25", _classifier):
            _, authorization = admission.authorize_literal_topic_with_route_context_p4(
                None, SOURCE, projection, context
            )
    finally:
        admission._ORIGINAL_M31 = old
    assert calls == [(SOURCE, projection)]
    assert authorization["status"] == "original_m31"
    assert authorization[admission.LABEL]["reason"] == reason


@pytest.mark.parametrize("malformed", [{}, "not_a_plan"])
def test_empty_or_malformed_rule_result_is_not_no_rule_match(malformed):
    left = LeftBrain.__new__(LeftBrain)
    with patch.object(left, "_rule_based_plan", return_value=malformed):
        actual = left.classify_user_signal(SOURCE, {}, {})
    assert actual["seed_plan_status_p4"] == "invalid"
    assert actual["seed_plan"] == {}
    context = _context()
    context.update({
        "seed_plan": actual["seed_plan"],
        "seed_plan_status_p4": actual["seed_plan_status_p4"],
    })
    decision = admission.route_admission_contract_p4(
        SOURCE, _projection(), context, _candidate()
    )
    assert decision["status"] == "rejected"
    assert decision["reason"] == "seed_provenance_missing_or_not_ordinary"


def test_tampered_m29_digest_and_correction_route_never_defer():
    calls = []
    old = admission._ORIGINAL_M31
    try:
        def original(_self, source, projection):
            calls.append((source, deepcopy(projection)))
            return None, {"status": "original_m31"}
        admission._ORIGINAL_M31 = original
        corrected = _context()
        corrected["semantic_route_m22"]["selected_type"] = "explicit_correction"
        corrected["semantic_route_m22"]["recommended_route"] = "correction_authority"
        with patch.object(
            adaptive, "classify_explicit_desired_response_m25", _classifier
        ):
            _, correction = admission.authorize_literal_topic_with_route_context_p4(
                None, SOURCE, _projection(), corrected
            )
            tampered = _projection()
            tampered["input_digest"] = "0" * 16
            _, mismatch = admission.authorize_literal_topic_with_route_context_p4(
                None, SOURCE, tampered, _context()
            )
    finally:
        admission._ORIGINAL_M31 = old
    assert len(calls) == 2
    assert correction[admission.LABEL]["status"] == "rejected"
    assert mismatch[admission.LABEL]["status"] == "not_source_candidate"
    assert calls[1][1]["input_digest"] == "0" * 16


def test_certificate_shape_itself_is_not_route_authority():
    certificate = _candidate()
    assert certificate
    for bad_certificate in ({}, {**certificate, "schema": "forged"}, {**certificate, "action": "unresolved"}):
        decision = admission.route_admission_contract_p4(
            SOURCE, _projection(), _context(), bad_certificate
        )
        assert decision["status"] == "not_source_candidate"
        assert decision["source_certificate_present"] is False


def test_exact_opt_in_install_chain_is_distinct_from_old_entry():
    program = r'''
import uruha_web_ui_product_p4_reported_ack_route_admission
import uruha_reported_ack_route_admission_p4 as admission
import uruha_reported_ack_m31_priority_p4 as priority
from uruha_current_statement_source_authority_p4 import install_current_statement_source_authority_p4 as f1
from uruha_third_party_question_evidence_p4 import install_third_party_question_evidence_p4 as f2
from uruha_selected_offer_action_surface_fidelity_p4 import install_selected_offer_action_surface_fidelity_p4 as f3
from uruha_reported_offer_source_scope_p4 import install_reported_offer_source_scope_p4 as f4
from uruha_hash_prefix_provenance_gate_p4 import install_hash_prefix_provenance_gate_p4 as f5
from uruha_hash_prefix_event_transport_p4 import install_hash_prefix_event_transport_p4 as f6
from uruha_temporal_actor_scope_p4 import install_temporal_actor_scope_p4 as f7
from uruha_reported_ack_m31_priority_p4 import install_reported_ack_m31_priority_p4 as f8
from uruha_reported_ack_route_admission_p4 import install_reported_ack_route_admission_p4 as f9
from uruha_brain_mac import LeftBrain
for installer in (f1,f2,f3,f4,f5,f6,f7,f8):
    assert installer() is True
assert LeftBrain.authorize_literal_topic_m31 is priority.authorize_literal_topic_with_reported_ack_priority_p4
assert not hasattr(LeftBrain, "authorize_literal_topic_m31_with_route_context_p4")
assert f9() is True
assert LeftBrain.authorize_literal_topic_m31 is admission.authorize_literal_topic_without_route_context_p4
assert LeftBrain.authorize_literal_topic_m31_with_route_context_p4 is admission.authorize_literal_topic_with_route_context_p4
assert f9() is False
'''
    child = subprocess.run(
        [sys.executable, "-c", program], capture_output=True, text=True,
        timeout=30, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    assert child.returncode == 0, child.stdout + child.stderr
