"""Zero-model B contracts; prospective Safari prompts are kept out of fixtures."""

from copy import deepcopy
import hashlib
import os
import subprocess
import sys
from unittest.mock import patch

import pytest

import uruha_adaptive_person_model as adaptive
import uruha_reported_ack_m31_priority_p4 as priority
import uruha_reported_ack_route_admission_p4 as admission
import uruha_reported_ack_selected_visible_p4 as visible
import uruha_temporal_actor_scope_p4 as actor_scope
from uruha_brain_mac import RightBrain
from uruha_utterance_frame_shadow_p4 import inspect_utterance_frame_shadow_p4


SOURCE = "後輩が「先に確認して」と言っていた。"
OLD_CORE = actor_scope._REPORTED_CHECK_REPLY_JP


def _qualified(source=SOURCE):
    digest = priority._digest(source)
    original_classifier = adaptive.classify_explicit_desired_response_m25
    classifier = lambda text: actor_scope.gate_base_explicit_request_p4(
        text, original_classifier
    )
    projection = {
        "schema": adaptive.LITERAL_TOPIC_PROJECTION_SCHEMA_M29,
        "projection_required": True,
        "surface_authority": False,
        "input_digest": digest,
        "required_observable_act": None,
    }
    certificate = priority.reported_ack_m31_certificate_p4(
        source, projection, classifier
    )
    assert certificate is not None
    m22 = {
        "schema": "uruha_semantic_route_taxonomy_m22",
        "selected_type": "general_conversation",
        "recommended_route": "existing_guarded_router",
        "candidates": [{"task_type": "general_conversation"}],
        "evidence": [{"task_type": "general_conversation", "cue_id": "no_decisive_specialized_cue"}],
        "overlap_types": [],
        "decisive_evidence": ["no_decisive_specialized_cue"],
    }
    context = {
        "schema": admission.CONTEXT_SCHEMA,
        "input_digest": digest,
        "seed_plan": {},
        "seed_plan_status_p4": "no_rule_match",
        "actual_intent": "chat",
        "actual_scene": "casual",
        "route_info": {"route": "high_road", "reason": "deliberative"},
        "semantic_route_m22": m22,
        "grounded_profile_logic_present": False,
    }
    admitted = admission.route_admission_contract_p4(
        source, projection, context, certificate
    )
    assert admitted["status"] == "admitted"
    scope = classifier(source)[actor_scope.LABEL]
    scope["selected_action"] = "ack_reported_check_instruction_p4"
    logic = {
        "intent": "chat",
        "scene": "casual",
        "surface_act": "ack_reported_check_instruction_p4",
        "core_message_jp": OLD_CORE,
        "jp_summary": OLD_CORE,
        "response_mode": "acknowledge_reported_instruction",
        "constraints": {"max_chars": 32, "sentence_count": 2},
        "human_speech_plan": {
            "dialogue_act": "direct_chat_answer",
            "content_units": ["まず一点だけ答える", OLD_CORE],
        },
        "personhood_action_context_v2_13": {"core_message_jp": OLD_CORE},
        "semantic_authorization_m31": {
            "status": "deferred_to_reported_ack_p4",
            "input_digest": digest,
            priority.LABEL: certificate,
            admission.LABEL: admitted,
        },
        actor_scope.LABEL: scope,
        "semantic_route_m22": m22,
        "memory_use_expected": False,
        "memory_anchor": {},
    }
    selected = {"surface_act": logic["surface_act"], "core_message_jp": OLD_CORE}
    return logic, context["route_info"], selected


def test_source_bound_realization_has_no_bad_punctuation_or_invented_check():
    logic, route, selected = _qualified()
    receipt = visible.prepare_reported_ack_selected_visible_p4(
        SOURCE, logic, route, selected
    )
    core = logic["core_message_jp"]
    assert receipt["status"] == "selected"
    assert "後輩が「先に確認して」って言ってたんだね。" in core
    assert "まだ分かんない" in core
    assert "？" not in core and "？。" not in core
    assert "確認した" not in core
    assert logic["constraints"]["max_chars"] >= len(core)
    assert logic["human_speech_plan"]["content_units"][-1] == core
    assert logic["personhood_action_context_v2_13"]["core_message_jp"] == core
    assert SOURCE not in repr(receipt)
    assert "先に確認して" not in repr(receipt)
    assert not inspect_utterance_frame_shadow_p4(SOURCE, core)["violations"]
    brain = RightBrain.__new__(RightBrain)
    assert "malformed_japanese_punctuation" not in brain._user_visible_language_rejection_reasons(
        core, user_input=SOURCE, logic_data=logic, memory_data={}
    )


@pytest.mark.parametrize("mutation,reason", [
    ("stale_certificate", "same_turn_source_or_admission_not_proved"),
    ("route_rejected", "same_turn_source_or_admission_not_proved"),
    ("protected_route", "actual_selected_or_general_route_disagrees"),
    ("factual_m22", "actual_selected_or_general_route_disagrees"),
    ("selected_mismatch", "actual_selected_or_general_route_disagrees"),
    ("memory_anchor", "memory_or_profile_authority_present"),
    ("profile_shadow", "memory_or_profile_authority_present"),
])
def test_eligibility_fails_closed_without_touching_selected_core(mutation, reason):
    logic, route, selected = _qualified()
    if mutation == "stale_certificate":
        logic["semantic_authorization_m31"][priority.LABEL]["quote_digest"] = "0" * 16
    elif mutation == "route_rejected":
        logic["semantic_authorization_m31"][admission.LABEL]["status"] = "rejected"
    elif mutation == "protected_route":
        route["route"] = "low_road"
    elif mutation == "factual_m22":
        logic["semantic_route_m22"]["selected_type"] = "factual_or_memory"
    elif mutation == "selected_mismatch":
        selected["surface_act"] = "plain_reply"
    elif mutation == "memory_anchor":
        logic["memory_anchor"] = {"kind": "favorite_drink"}
    elif mutation == "profile_shadow":
        logic["profile_grounding_shadow"] = {"status": "present"}
    before = deepcopy(logic)
    receipt = visible.prepare_reported_ack_selected_visible_p4(
        SOURCE, logic, route, selected
    )
    assert receipt["status"] == "not_applied"
    assert receipt["reason"] == reason
    assert logic == before


def test_mixed_or_unbounded_quote_never_gets_b_surface_authority():
    logic, route, selected = _qualified()
    mixed = "後輩が「先に確認して」と言っていた。あとでうるはも確認して。"
    receipt = visible.prepare_reported_ack_selected_visible_p4(
        mixed, logic, route, selected
    )
    assert receipt["reason"] == "bounded_single_report_absent"
    assert logic["core_message_jp"] == OLD_CORE
    with_object = "後輩が「先に日程を確認して」と言っていた。"
    receipt = visible.prepare_reported_ack_selected_visible_p4(
        with_object, logic, route, selected
    )
    assert receipt["status"] == "not_applied"


def test_speech_variant_replaces_only_bound_current_candidate():
    logic, route, selected = _qualified()
    visible.prepare_reported_ack_selected_visible_p4(SOURCE, logic, route, selected)
    old = visible._ORIGINAL_VARIANTS
    try:
        visible._ORIGINAL_VARIANTS = lambda *_args, **_kwargs: ["legacy"]
        assert visible.speech_plan_variants_with_reported_ack_p4(
            None, "", logic, SOURCE
        ) == [logic["core_message_jp"]]
        assert visible.speech_plan_variants_with_reported_ack_p4(
            None, "", logic, SOURCE + "続き"
        ) == ["legacy"]
    finally:
        visible._ORIGINAL_VARIANTS = old


def test_final_receipt_uses_real_reply_and_preserves_legacy_mismatch():
    logic, route, selected = _qualified()
    visible.prepare_reported_ack_selected_visible_p4(SOURCE, logic, route, selected)
    core = logic["core_message_jp"]
    logic[actor_scope.LABEL]["surface_status"] = "reported_instruction_ack_missing"
    reply = "ん、" + core
    full_digest = hashlib.sha256(reply.encode("utf-8")).hexdigest()
    logic["visible_language_guard"] = {"final_rejection_reasons": [], "changed": False}
    logic["utterance_frame_shadow_p4"] = {"violations": [], "reply_digest": full_digest}
    logic["utterance_frame_coverage_extension_p4"] = {"violations": [], "reply_digest": full_digest}
    logic["frame_preserving_visible_repair_p4"] = {"changed": False, "after_violations": [], "after_digest": full_digest}
    logic["semantic_persona_surface_verifier_m39"] = {
        "action": "accept", "changed": False, "unresolved_violations": [],
        "final_reply_digest": priority._digest(reply),
    }
    result = {
        "reply": reply,
        "logic": logic,
        "runtime_trace": {
            "selected_plan": {"surface_act": selected["surface_act"], "core_message_jp": core},
            "blackboard": [
                {"stage": "select", "label": "selected_plan", "payload": {"core_message_jp": core}},
                {"stage": "surface", "label": "utterance", "payload": {"reply": reply}},
            ],
        },
    }
    visible.materialize_reported_ack_selected_visible_p4(result, SOURCE)
    audit = result["logic"][visible.LABEL]
    assert audit["status"] == "final_visible"
    assert audit["legacy_actor_surface_status"] == "reported_instruction_ack_missing"
    assert result["runtime_trace"][visible.LABEL] == audit
    assert [row["label"] for row in result["runtime_trace"]["blackboard"]] == [
        "selected_plan", visible.LABEL, "utterance"
    ]
    visible.materialize_reported_ack_selected_visible_p4(result, SOURCE)
    assert sum(row["label"] == visible.LABEL for row in result["runtime_trace"]["blackboard"]) == 1
    result["reply"] = "ん、その話もう少し聞かせて。"
    visible.materialize_reported_ack_selected_visible_p4(result, SOURCE)
    assert result["logic"][visible.LABEL]["status"] == "selected_not_visible"
    assert result["reply"] == "ん、その話もう少し聞かせて。"
    result["reply"] = f"「{reply}」っていう文だね。"
    visible.materialize_reported_ack_selected_visible_p4(result, SOURCE)
    assert result["logic"][visible.LABEL]["status"] == "selected_not_visible"


def test_new_opt_in_install_chain_is_distinct_from_a_entry():
    program = r'''
import uruha_web_ui_product_p4_reported_ack_selected_visible
from uruha_current_statement_source_authority_p4 import install_current_statement_source_authority_p4 as f1
from uruha_third_party_question_evidence_p4 import install_third_party_question_evidence_p4 as f2
from uruha_selected_offer_action_surface_fidelity_p4 import install_selected_offer_action_surface_fidelity_p4 as f3
from uruha_reported_offer_source_scope_p4 import install_reported_offer_source_scope_p4 as f4
from uruha_hash_prefix_provenance_gate_p4 import install_hash_prefix_provenance_gate_p4 as f5
from uruha_hash_prefix_event_transport_p4 import install_hash_prefix_event_transport_p4 as f6
from uruha_temporal_actor_scope_p4 import install_temporal_actor_scope_p4 as f7
from uruha_reported_ack_m31_priority_p4 import install_reported_ack_m31_priority_p4 as f8
from uruha_reported_ack_route_admission_p4 import install_reported_ack_route_admission_p4 as f9
from uruha_reported_ack_selected_visible_p4 import install_reported_ack_selected_visible_p4 as f10
from uruha_brain_mac import RightBrain, UruhaBrainV4_Mac
prior = RightBrain._speech_plan_variants
for install in (f1,f2,f3,f4,f5,f6,f7,f8,f9):
    assert install() is True
assert f10() is True
assert RightBrain._speech_plan_variants is not prior
assert f10() is False
assert UruhaBrainV4_Mac.emit_response_if_ready.__name__ == "emit_with_reported_ack"
'''
    child = subprocess.run(
        [sys.executable, "-c", program], capture_output=True, text=True,
        timeout=30, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    assert child.returncode == 0, child.stdout + child.stderr
