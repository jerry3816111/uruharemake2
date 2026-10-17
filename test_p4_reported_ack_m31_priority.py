"""Zero-model developer cases; not the future Safari or formal holdout set."""

from copy import deepcopy
import os
import subprocess
import sys
from unittest.mock import patch

import pytest

import uruha_adaptive_person_model as adaptive
import uruha_personhood_loop as personhood
import uruha_source_semantic_atoms_m33 as source_atoms
import uruha_temporal_actor_scope_p4 as actor_scope
import uruha_reported_ack_m31_priority_p4 as priority

BASE_CLASSIFIER = adaptive.classify_explicit_desired_response_m25


def _projection(text):
    return {
        "schema": adaptive.LITERAL_TOPIC_PROJECTION_SCHEMA_M29,
        "status": "projection_candidate",
        "projection_required": True,
        "surface_authority": False,
        "input_digest": priority._digest(text),
        "required_observable_act": None,
    }


def _classifier(text):
    return actor_scope.gate_base_explicit_request_p4(
        text, BASE_CLASSIFIER
    )


@pytest.mark.parametrize("source", [
    "同僚が「先に確認して」と言ってた。",
    "先生が「まず先に確認して」って言った。",
])
def test_single_report_has_same_source_actor_and_m31_certificate(source):
    proof = priority.reported_ack_m31_certificate_p4(
        source, _projection(source), _classifier
    )
    assert proof is not None
    assert proof["source_kind"] == "third_party_report"
    assert proof["actor"] == "third_party"
    assert proof["action"] == "reported_check_instruction"
    assert proof["input_digest"] == priority._digest(source)
    assert proof["m31_model_call_skipped"] is True
    assert not any("同僚" in str(value) or "先生" in str(value) for value in proof.values())


@pytest.mark.parametrize("source", [
    "同僚が「先に確認して」と言ってた。それと今日の天気は？",
    "先輩が「先に確認して」と言ってた、うるはは先に欲しい返し方を聞いて。",
    "同僚が先に確認してと言ってた。",
    "先に確認して。",
    "先に会議室を見てから返事してもいい？",
    "先生が「先に確認して」と言ってたけど、私は違うと思う。",
    "先生が「先に確認して」と言ってた？",
    "同僚は今日早退するらしい。",
    "同僚が「先に確認して」と言ってた。助けて、危ない。",
])
def test_non_single_or_direct_or_unknown_does_not_skip_m31(source):
    assert priority.reported_ack_m31_certificate_p4(
        source, _projection(source), _classifier
    ) is None


def test_digest_and_projection_authority_mismatch_fail_closed():
    source = "同僚が「先に確認して」と言ってた。"
    for mutation in (
        {"input_digest": "0" * 16},
        {"projection_required": False},
        {"surface_authority": True},
        {"source_statement_priority_p4": {"status": "source_rule_candidate"}},
        {"required_observable_act": "joint_complaint"},
    ):
        projection = {**_projection(source), **mutation}
        assert priority.reported_ack_m31_certificate_p4(
            source, projection, _classifier
        ) is None


def test_classifier_authority_tampering_fails_closed():
    source = "同僚が「先に確認して」と言ってた。"
    original = _classifier(source)
    for mutation in (
        {"selected_policy": "calibrate_need"},
        {"protected_risk_cue": True},
        {actor_scope.LABEL: {**original[actor_scope.LABEL], "input_digest": "0" * 16}},
        {actor_scope.LABEL: {**original[actor_scope.LABEL], "action": "unresolved"}},
        {actor_scope.LABEL: {**original[actor_scope.LABEL], "additional_clause_observed": True}},
    ):
        classifier = lambda _text, row={**original, **mutation}: deepcopy(row)
        assert priority.reported_ack_m31_certificate_p4(
            source, _projection(source), classifier
        ) is None


def test_early_defer_keeps_reported_action_through_m31_m32_and_final():
    source = "同僚が「先に確認して」と言ってた。"
    previous = priority._ORIGINAL_M31
    try:
        def should_not_call_model(*_args):
            raise AssertionError("M31 model path must not run for the qualified report")
        priority._ORIGINAL_M31 = should_not_call_model
        with patch.object(adaptive, "classify_explicit_desired_response_m25", _classifier):
            semantic_plan, contract = (
                priority.authorize_literal_topic_with_reported_ack_priority_p4(
                    None, source, _projection(source)
                )
            )
    finally:
        priority._ORIGINAL_M31 = previous
    assert semantic_plan is None
    assert contract["status"] == "deferred_to_reported_ack_p4"
    assert contract["surface_authority"] is False
    assert contract["model_call_completed"] is False

    request = _classifier(source)
    decision = {"state": {"explicit_desired_response_m25": request}, "selected": None}
    selected, _ = actor_scope.apply_temporal_actor_scope_to_plan_p4(
        {"intent": "chat", "scene": "casual", "core_message_jp": "下書き"},
        decision,
        adaptive.apply_decision_to_plan,
    )
    assert selected["surface_act"] == "ack_reported_check_instruction_p4"
    selected, m31 = adaptive.apply_semantic_authorization_m31(selected, contract)
    m32_contract = adaptive.build_deterministic_semantic_commit_m32(contract)[1]
    selected, m32 = adaptive.apply_semantic_commit_repair_m32(selected, m32_contract)
    assert m31["surface_authority"] is False
    assert m32["surface_authority"] is False
    assert selected["surface_act"] == "ack_reported_check_instruction_p4"
    visible, audited = adaptive.ensure_semantic_authorization_m31_reaches_surface(
        selected["core_message_jp"], selected
    )
    assert visible == "そう言ってたんだ。何を先に確認する話？"
    assert audited["surface_status"] == "not_applicable"
    assert source_atoms.extract_source_semantic_atoms_m33(
        source, _projection(source)
    )["status"] == "source_pattern_unavailable"


def test_nonreport_delegates_to_original_without_mutation():
    source = "先に一回確認して。"
    calls = []
    sentinel = ({"some": "plan"}, {"some": "contract"})
    previous = priority._ORIGINAL_M31
    try:
        def original(_self, user_input, projection):
            calls.append((user_input, deepcopy(projection)))
            return sentinel
        priority._ORIGINAL_M31 = original
        actual = priority.authorize_literal_topic_with_reported_ack_priority_p4(
            None, source, _projection(source)
        )
    finally:
        priority._ORIGINAL_M31 = previous
    assert actual is sentinel
    assert calls == [(source, _projection(source))]


def test_exact_opt_in_product_install_chain_retains_source_certificate():
    # A separate interpreter keeps the product monkeypatch chain out of the
    # other regression tests.  This checks the real installed classifier,
    # not just the uninstalled actor gate used by the small fixtures above.
    program = r'''
import uruha_web_ui_product_p4_reported_ack_m31_priority
import uruha_adaptive_person_model as adaptive
import uruha_reported_ack_m31_priority_p4 as priority
from uruha_current_statement_source_authority_p4 import install_current_statement_source_authority_p4 as f1
from uruha_third_party_question_evidence_p4 import install_third_party_question_evidence_p4 as f2
from uruha_selected_offer_action_surface_fidelity_p4 import install_selected_offer_action_surface_fidelity_p4 as f3
from uruha_reported_offer_source_scope_p4 import install_reported_offer_source_scope_p4 as f4
from uruha_hash_prefix_provenance_gate_p4 import install_hash_prefix_provenance_gate_p4 as f5
from uruha_hash_prefix_event_transport_p4 import install_hash_prefix_event_transport_p4 as f6
from uruha_temporal_actor_scope_p4 import install_temporal_actor_scope_p4 as f7
from uruha_reported_ack_m31_priority_p4 import install_reported_ack_m31_priority_p4 as f8
from uruha_brain_mac import LeftBrain
for install in (f1, f2, f3, f4, f5, f6, f7, f8):
    assert install() is True
assert LeftBrain.authorize_literal_topic_m31 is priority.authorize_literal_topic_with_reported_ack_priority_p4
for text, expected in (
    ('先生が「先に確認して」と言っていた。', True),
    ('先生が「先に確認して」と言っていた。今日はどうする？', False),
):
    projection = {
        'schema': adaptive.LITERAL_TOPIC_PROJECTION_SCHEMA_M29,
        'projection_required': True,
        'surface_authority': False,
        'input_digest': priority._digest(text),
    }
    assert bool(priority.reported_ack_m31_certificate_p4(
        text, projection, adaptive.classify_explicit_desired_response_m25
    )) is expected
'''
    child = subprocess.run(
        [sys.executable, "-c", program],
        capture_output=True,
        text=True,
        timeout=30,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    assert child.returncode == 0, child.stdout + child.stderr
