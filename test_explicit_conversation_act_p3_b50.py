import hashlib
from copy import deepcopy

import pytest

import uruha_adaptive_person_model as adaptive
import uruha_web_ui as web
from test_adaptive_person_model_m16 import decision_for
from test_generalized_literal_topic_projection_m29 import _Client, valid_payload
from test_personhood_loop_v2_13 import _FakeLeftBrain, _IsolatedContractBrain
from uruha_brain_mac import LeftBrain, RightBrain, UruhaBrainV4_Mac
from uruha_memory_observatory import collect_cognitive_graph


SOURCE = "現在先別分析，陪我吐槽一下這些註解怎麼會一直長出來。"
VISIBLE = "またこの注釈増えてんのかよ、いい加減にしろって。"


class JointComplaintAuthorizer(_FakeLeftBrain):
    def __init__(self, *, accepted=True):
        super().__init__()
        self.accepted = accepted
        self.calls = []

    def authorize_literal_topic_m31(self, user_input, projection):
        self.calls.append((user_input, deepcopy(projection)))
        if not self.accepted:
            return None, {
                "status": "semantic_authority_rejected",
                "reason": "synthetic_rejection",
                "surface_authority": False,
                "model_call_completed": True,
                "authorization_checks": {
                    "required_observable_act_preserved": False,
                },
            }
        return {"core_message_jp": VISIBLE}, {
            "status": "semantically_authorized",
            "reason": "synthetic_source_first_joint_complaint",
            "surface_authority": True,
            "model_call_completed": True,
            "confidence": 0.93,
            "response_jp": VISIBLE,
            "surface_anchors_jp": ["注釈", "増えて"],
            "authorization_checks": {
                "required_observable_act_preserved": True,
                "joint_complaint_topic_anchor_present": True,
                "joint_complaint_not_generic_presence_or_question": True,
            },
        }


def _logic(text=SOURCE):
    state, decision = decision_for(text, adaptive.empty_model(), 1)
    logic, _trace = adaptive.apply_decision_to_plan(
        {
            "intent": "chat",
            "scene": "casual",
            "surface_act": "plain_reply",
            "core_message_jp": "分かった。",
        },
        decision,
    )
    logic["explicit_desired_response_m25"] = deepcopy(
        decision["explicit_desired_response_m25"]
    )
    return logic


def _brain(*, accepted=True):
    brain = object.__new__(UruhaBrainV4_Mac)
    brain.left_brain = JointComplaintAuthorizer(accepted=accepted)
    brain.right_brain = RightBrain(load_model=False)
    return brain


@pytest.mark.parametrize(
    ("text", "language"),
    [
        ("陪我吐槽一下這些通知一直跳。", "zh"),
        ("Complain with me about these alerts that keep appearing.", "en"),
        ("この通知が増え続けるの、一緒に文句言って。", "ja"),
    ],
)
def test_cross_lingual_joint_complaint_gets_narrow_current_turn_authority(
    text, language
):
    contract = adaptive.classify_explicit_desired_response_m25(text)
    act = contract["explicit_conversation_act_p3_b50"]

    assert contract["selected_policy"] == "share_arousal"
    assert act["status"] == "explicit_joint_complaint_requested"
    assert act["act"] == "joint_complaint"
    assert act["authoritative"] is True
    assert act["matched_language"] == language
    assert act["raw_dialogue_persisted"] is False
    assert text not in str(act)


@pytest.mark.parametrize(
    "text",
    [
        "這些通知真的很煩。",
        "先陪我一下。",
        "吐槽我一句。",
        "These alerts are annoying.",
        "この通知うざい。",
    ],
)
def test_negative_content_companionship_and_teasing_do_not_infer_joint_complaint(
    text,
):
    act = adaptive.classify_explicit_conversation_act_p3_b50(text)
    assert act["detected"] is False
    assert act["authoritative"] is False


@pytest.mark.parametrize(
    "text",
    [
        "不要陪我吐槽，先說解法。",
        "Don't complain with me; give me one step.",
        "一緒に文句言わなくていい。方法を教えて。",
    ],
)
def test_negated_joint_complaint_never_gets_act_authority(text):
    act = adaptive.classify_explicit_conversation_act_p3_b50(text)
    assert act["status"] == "explicit_joint_complaint_negated"
    assert act["negated"] is True
    assert act["authoritative"] is False


def test_protected_crisis_cue_blocks_joint_complaint_authority():
    contract = adaptive.classify_explicit_desired_response_m25(
        "I want to die. Complain with me about these alerts."
    )
    act = contract["explicit_conversation_act_p3_b50"]
    assert contract["authority"] == "protected_risk_route"
    assert act["authority"] == "protected_risk_route"
    assert act["authoritative"] is False


def test_source_first_realization_replaces_generic_presence_with_topic_act():
    brain = _brain()
    logic = _logic()
    reply, trace = brain._realize_explicit_conversation_act_p3_b50(
        "うん。今は質問しないで、ちょっとここにいる。",
        logic,
        SOURCE,
        memory_data={},
    )

    assert reply == VISIBLE
    assert logic["core_message_jp"] == VISIBLE
    assert trace["status"] == "joint_complaint_realized"
    assert trace["surface_authority"] is True
    assert trace["surface_anchor_count"] == 2
    assert trace["complaint_marker_present"] is True
    assert trace["generic_presence_question_or_advice_absent"] is True
    assert len(brain.left_brain.calls) == 1
    assert brain.left_brain.calls[0][1]["required_observable_act"] == (
        "joint_complaint"
    )


def _joint_projection():
    return {
        "status": "source_first_joint_complaint_requested",
        "projection_required": True,
        "surface_authority": False,
        "input_digest": hashlib.sha256(SOURCE.encode("utf-8")).hexdigest()[:16],
        "required_observable_act": "joint_complaint",
    }


def _joint_verdict(response=VISIBLE):
    return {
        "source_normalization": {
            "polarity": "affirmed",
            "subject_jp": "注釈",
            "predicate_jp": "増えている",
            "time_quantity_relation_jp": "また",
            "literal_summary_jp": (
                "また増えている注釈に一緒に文句を言うよう求めている。"
            ),
        },
        "surface_authorization": {
            "unsupported_addition_absent": True,
            "safe_response_jp": response,
            "safe_surface_anchors_jp": ["注釈", "増えて"],
        },
        "confidence": 0.93,
    }


def test_native_m31_joint_act_contract_accepts_complaint_not_generic_presence():
    left = LeftBrain(_Client(valid_payload()))
    left._native_semantic_authorizer_m31 = lambda _prompt: _joint_verdict()
    plan, contract = left.authorize_literal_topic_m31(
        SOURCE,
        _joint_projection(),
    )

    assert plan["core_message_jp"] == VISIBLE
    assert contract["status"] == "semantically_authorized"
    assert contract["authorization_checks"][
        "required_observable_act_preserved"
    ] is True
    assert contract["authorization_checks"][
        "joint_complaint_topic_anchor_present"
    ] is True


def test_native_m31_joint_act_contract_rejects_generic_presence():
    left = LeftBrain(_Client(valid_payload()))
    verdict = _joint_verdict(
        response="うん。今は質問しないで、ちょっとここにいる。"
    )
    verdict["surface_authorization"]["safe_surface_anchors_jp"] = [
        "注釈",
        "増えて",
    ]
    left._native_semantic_authorizer_m31 = lambda _prompt: verdict
    plan, contract = left.authorize_literal_topic_m31(
        SOURCE,
        _joint_projection(),
    )

    assert plan is None
    assert contract["status"] == "semantic_authority_rejected"
    assert contract["authorization_checks"][
        "required_observable_act_preserved"
    ] is False


def test_native_m31_rejects_participants_mislabeled_as_complaint_topic():
    left = LeftBrain(_Client(valid_payload()))
    verdict = _joint_verdict()
    verdict["source_normalization"].update(
        {
            "subject_jp": "私と君",
            "literal_summary_jp": (
                "私と君が注釈に一緒に文句を言ってほしい。"
            ),
        }
    )
    verdict["surface_authorization"].update(
        {
            "safe_response_jp": "私と君、注釈うざい、またかよ。",
            "safe_surface_anchors_jp": ["私と君", "注釈"],
        }
    )
    left._native_semantic_authorizer_m31 = lambda _prompt: verdict
    plan, contract = left.authorize_literal_topic_m31(
        SOURCE,
        _joint_projection(),
    )

    assert plan is None
    assert contract["status"] == "semantic_authority_rejected"
    assert contract["authorization_checks"][
        "joint_complaint_topic_not_participant"
    ] is False


def test_rejected_realization_keeps_failure_visible_in_act_audit():
    brain = _brain(accepted=False)
    logic = _logic()
    generic = "うん。今は質問しないで、ちょっとここにいる。"
    reply, trace = brain._realize_explicit_conversation_act_p3_b50(
        generic,
        logic,
        SOURCE,
        memory_data={},
    )
    logic["explicit_conversation_act_p3_b50"] = trace
    audit = brain._audit_explicit_conversation_act_p3_b50(reply, logic)

    assert reply == generic
    assert trace["status"] == "joint_complaint_realization_rejected"
    assert audit["surface_status"] == "mismatch"
    assert audit["performed"] is False


def test_canonical_topic_repairs_only_surface_anchor_failure():
    class CanonicalOnlyAuthorizer(JointComplaintAuthorizer):
        def authorize_literal_topic_m31(self, user_input, projection):
            self.calls.append((user_input, deepcopy(projection)))
            return None, {
                "status": "semantic_authority_rejected",
                "reason": "surface_anchor_only_failure",
                "surface_authority": False,
                "model_call_completed": True,
                "authorization_checks": {
                    "proposal_or_repair_path_valid": False,
                    "safe_surface_anchors_visible": False,
                    "safe_surface_anchors_grounded_in_canonical": True,
                    "required_observable_act_preserved": True,
                    "joint_complaint_topic_anchor_present": False,
                },
                "m32_repair_candidate": {
                    "canonical_ready": True,
                    "subject_jp": "注釈",
                    "literal_summary_jp": (
                        "増え続ける注釈に一緒に文句を言ってほしい。"
                    ),
                },
            }

    brain = _brain()
    brain.left_brain = CanonicalOnlyAuthorizer()
    reply, trace = brain._realize_explicit_conversation_act_p3_b50(
        "うん。今は質問しないで、ちょっとここにいる。",
        _logic(),
        SOURCE,
        memory_data={},
    )

    assert reply == "注釈、またかよ。いい加減にしてくれって。"
    assert trace["status"] == "joint_complaint_realized"
    assert trace["canonical_topic_act_repair"] is True
    assert trace["canonical_topic_authority"] is True
    assert trace["source_first_authorization"] is False


def test_canonical_topic_never_repairs_semantic_or_act_failure():
    class UnsafeCanonicalAuthorizer(JointComplaintAuthorizer):
        def authorize_literal_topic_m31(self, user_input, projection):
            self.calls.append((user_input, deepcopy(projection)))
            return None, {
                "status": "semantic_authority_rejected",
                "surface_authority": False,
                "model_call_completed": True,
                "authorization_checks": {
                    "proposal_or_repair_path_valid": False,
                    "required_observable_act_preserved": False,
                },
                "m32_repair_candidate": {
                    "canonical_ready": True,
                    "subject_jp": "注釈",
                    "literal_summary_jp": "注釈に一緒に文句を言ってほしい。",
                },
            }

    brain = _brain()
    brain.left_brain = UnsafeCanonicalAuthorizer()
    generic = "うん。今は質問しないで、ちょっとここにいる。"
    reply, trace = brain._realize_explicit_conversation_act_p3_b50(
        generic,
        _logic(),
        SOURCE,
        memory_data={},
    )

    assert reply == generic
    assert trace["status"] == "joint_complaint_realization_rejected"
    assert trace["canonical_topic_act_repair"] is False


def test_participant_pair_cannot_be_used_as_complaint_topic():
    class ParticipantTopicAuthorizer(JointComplaintAuthorizer):
        def authorize_literal_topic_m31(self, user_input, projection):
            self.calls.append((user_input, deepcopy(projection)))
            return None, {
                "status": "semantic_authority_rejected",
                "surface_authority": False,
                "model_call_completed": True,
                "authorization_checks": {
                    "proposal_or_repair_path_valid": False,
                    "safe_surface_anchors_visible": False,
                    "safe_surface_anchors_grounded_in_canonical": True,
                    "required_observable_act_preserved": True,
                    "joint_complaint_topic_anchor_present": False,
                },
                "m32_repair_candidate": {
                    "canonical_ready": True,
                    "subject_jp": "私と君",
                    "literal_summary_jp": (
                        "私と君が一緒に注釈へ文句を言ってほしい。"
                    ),
                },
            }

    brain = _brain()
    brain.left_brain = ParticipantTopicAuthorizer()
    generic = "うん。今は質問しないで、ちょっとここにいる。"
    reply, trace = brain._realize_explicit_conversation_act_p3_b50(
        generic,
        _logic(),
        SOURCE,
        memory_data={},
    )

    assert reply == generic
    assert trace["status"] == "joint_complaint_realization_rejected"
    assert trace["canonical_topic_act_repair"] is False


def test_full_isolated_runtime_records_performed_act_without_persisting_source():
    brain = _IsolatedContractBrain()
    brain.left_brain = JointComplaintAuthorizer()
    brain.right_brain = RightBrain(load_model=False)
    turn = brain.run_turn_debug(SOURCE)
    act = turn["runtime_trace"]["explicit_conversation_act_p3_b50"]
    m25 = turn["runtime_trace"]["explicit_desired_response_m25"]

    assert turn["reply"] == VISIBLE
    assert act["surface_status"] == "matched"
    assert act["performed"] is True
    assert m25["surface_status"] == "matched"
    assert m25["explicit_conversation_act_p3_b50"]["performed"] is True
    assert SOURCE not in str(act)


def test_graph_and_compact_web_trace_show_act_between_selection_and_guard():
    act = {
        "schema": adaptive.EXPLICIT_CONVERSATION_ACT_SCHEMA_P3_B50,
        "status": "joint_complaint_realized",
        "surface_status": "matched",
        "surface_authority": True,
    }
    graph = collect_cognitive_graph(
        {
            "user_text": "redacted",
            "reply": VISIBLE,
            "runtime_trace": {
                "blackboard": [
                    {
                        "stage": "select",
                        "label": "explicit_desired_response_m25",
                        "payload": {"selected_policy": "share_arousal"},
                    },
                    {
                        "stage": "surface",
                        "label": "explicit_conversation_act_p3_b50",
                        "payload": act,
                    },
                    {
                        "stage": "verify",
                        "label": "japanese_semantic_repair_m49",
                        "payload": {"status": "not_required"},
                    },
                    {
                        "stage": "surface",
                        "label": "visible_language_guard",
                        "payload": {"passed": True},
                    },
                ]
            },
        }
    )
    ids = {node["label"]: node["id"] for node in graph["nodes"]}
    edges = {(edge["source"], edge["target"]) for edge in graph["edges"]}

    assert (
        ids["explicit_desired_response_m25"],
        ids["explicit_conversation_act_p3_b50"],
    ) in edges
    assert (
        ids["explicit_conversation_act_p3_b50"],
        ids["japanese_semantic_repair_m49"],
    ) in edges
    compact = web._compact_runtime_trace_m24(
        {"explicit_conversation_act_p3_b50": act}
    )
    assert compact["explicit_conversation_act_p3_b50"]["surface_status"] == (
        "matched"
    )
