import json

from uruha_semantic_persona_surface_m39 import (
    inspect_surface_m39,
    verify_and_repair_surface_m39,
)


def _logic(policy, route="emotional_bid"):
    return {
        "desired_response_policy_m18": policy,
        "semantic_route_m22": {"selected_type": route},
        "counterfactual_pragmatic_branch_m34": {
            "selected_branch": {"policy_id": policy} if policy else {},
        },
    }


def test_role_inversion_is_repaired_without_raw_trace():
    source = "I have not slept since yesterday, and I need you to listen."
    candidate = "私は昨日から寝てなくて、聞いてほしいんだね。"
    final_reply, trace = verify_and_repair_surface_m39(
        source,
        candidate,
        _logic("listen_presence"),
    )
    assert trace["action"] == "repair"
    assert "agent_first_person_owns_user_state" in trace["violations_before"]
    assert trace["policy_act_match_after"] is True
    assert final_reply == "その話、最後まで聞く。続けて。"
    encoded = json.dumps(trace, ensure_ascii=False)
    assert source not in encoded
    assert candidate not in encoded


def test_unsupported_result_is_removed_but_companionship_remains():
    source = "The outline has not moved. Stay with me a minute."
    candidate = "結果が来るまで一緒に待っとく。"
    final_reply, trace = verify_and_repair_surface_m39(
        source,
        candidate,
        _logic("share_arousal"),
    )
    assert trace["action"] == "repair"
    assert "external_reply_or_result" in trace["violations_before"]
    assert "結果" not in final_reply
    assert "ここにいる" in final_reply


def test_third_party_choice_is_not_reassigned_to_user():
    final_reply, trace = verify_and_repair_surface_m39(
        "My cousin says she does not want to join, and I am unsure why.",
        "お前は参加したくないけど、理由が分からないんだな。",
        _logic("calibrate_need", route="general_conversation"),
    )
    assert trace["action"] == "repair"
    assert "user_owns_third_party_state" in trace["violations_before"]
    assert trace["policy_act_match_after"] is True
    assert "お前は参加したくない" not in final_reply


def test_selected_policy_must_be_visible_not_only_metadata():
    final_reply, trace = verify_and_repair_surface_m39(
        "I need you here.",
        "そうなんだな。",
        _logic("share_arousal"),
    )
    assert trace["action"] == "repair"
    assert "selected_policy_not_realized" in trace["violations_before"]
    assert trace["policy_act_match_after"] is True
    assert "ここにいる" in final_reply


def test_correct_surface_is_not_changed():
    candidate = "分かった。先に最後まで聞く。続けて。"
    final_reply, trace = verify_and_repair_surface_m39(
        "先に最後まで聞いて。",
        candidate,
        _logic("listen_presence", route="explicit_correction"),
    )
    assert trace["action"] == "accept"
    assert trace["changed"] is False
    assert final_reply == candidate


def test_protected_routes_are_not_modified():
    candidate = "今すぐ危ないなら、一人にならず救急か近くの人に連絡して。"
    final_reply, trace = verify_and_repair_surface_m39(
        "I may hurt myself.",
        candidate,
        _logic(None, route="safety_sensitive"),
    )
    assert trace["action"] == "not_applicable"
    assert trace["protected_route"] is True
    assert final_reply == candidate


def test_formal_register_is_repaired_to_casual_persona():
    final_reply, trace = verify_and_repair_surface_m39(
        "Could you listen?",
        "承知しました。どうぞお話しください。",
        _logic("listen_presence"),
    )
    assert trace["action"] == "repair"
    assert "formal_register" in trace["violations_before"]
    assert "ください" not in final_reply
    assert inspect_surface_m39("Could you listen?", final_reply, _logic("listen_presence"))["policy_act_match"]
