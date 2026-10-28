"""Developer-authored, zero-model P4 actor/deixis surface contracts.

These fixtures use a new source-disjoint statement; they are not formal
holdout or evidence that the fresh Web product chose M32 on its own.
"""

import hashlib
from copy import deepcopy
from types import SimpleNamespace

import pytest

from uruha_brain_mac import RightBrain
import uruha_explicit_rewrite_action_p4 as rewrite_action


USER = "私は2041年3月12日の集合場所を琥珀色の温室の入口に決めた。"
STEM = USER.rstrip("。")
ECHO = f"{STEM}んだね。"
EXPECTED = f"そっちは{STEM[len('私は'):]}んだね。"


def _logic(user=USER, echo=ECHO):
    digest = hashlib.sha256(user.encode("utf-8")).hexdigest()
    stem = user.rstrip("。")
    event_id = "actor-fresh-event"
    m31_id = f"{event_id}:m31:fresh"
    m32_id = f"{event_id}:m32:fresh"
    return {
        "intent": "deterministic_semantic_commit_m32",
        "scene": "casual",
        "core_message_jp": echo,
        "current_turn_source_role_p4": {
            "schema": "uruha_current_turn_source_role_p4_v1",
            "raw_input_sha256": digest,
            "act": "ordinary_chat",
            "quote_role": "none",
            "outer_role": "current_user_utterance",
        },
        "semantic_authorization_m31": {
            "schema": "uruha_semantic_authorization_m31",
            "input_digest": digest[:16],
            "m32_repair_candidate": {
                "canonical_ready": True,
                "subject_jp": "私",
                "literal_summary_jp": stem,
            },
        },
        "semantic_commit_repair_m32": {
            "schema": "uruha_deterministic_semantic_commit_m32",
            "status": "deterministic_commit_repaired",
            "subject_jp": "私",
            "literal_summary_jp": stem,
            "response_jp": echo,
        },
        "mixed_act_lineage_p4": {
            "schema": "uruha_mixed_act_lineage_p4_v1",
            "status": "linked",
            "event_id": event_id,
            "raw_input_sha256": digest,
            "source_role_act": "ordinary_chat",
            "m31": {"status": "produced", "proposal_id": m31_id},
            "m32": {"status": "produced", "proposal_id": m32_id, "surface_authority_retained": True},
            "producer_edges": [
                {"from_id": event_id, "to_id": m31_id, "type": "event_to_m31"},
                {"from_id": m31_id, "to_id": m32_id, "type": "m31_to_m32"},
            ],
            "authority_blockers": [],
            "m33_authoritative": False,
        },
    }


def _guard(reply, user=USER, logic=None):
    logic = deepcopy(_logic(user, reply) if logic is None else logic)
    final = RightBrain(load_model=False).enforce_user_visible_japanese(
        reply, logic, user_input=user, memory_data={}
    )
    return final, logic["visible_language_guard"]


def test_exact_current_user_m32_echo_addresses_user_without_losing_proposition():
    final, guard = _guard(ECHO)
    assert final == EXPECTED
    assert "2041年3月12日" in final
    assert "琥珀色の温室の入口" in final
    assert "うちは" not in final and "私は" not in final
    assert guard["repair_action"] == "source_bound_user_actor_deixis"
    assert guard["actor_boundary"]["status"] == "source_bound_user_echo_repaired"
    assert guard["actor_boundary"]["role_proof_origin"] == "recomputed_from_current_emit_user_input"
    assert guard["final_reply"] == final
    assert guard["final_reply_sha256"] == hashlib.sha256(final.encode("utf-8")).hexdigest()


def test_role_certificate_can_be_attached_only_after_emit_without_losing_actor_repair():
    logic = _logic()
    del logic["current_turn_source_role_p4"]
    final, guard = _guard(ECHO, logic=logic)
    assert final == EXPECTED
    assert guard["actor_boundary"]["status"] == "source_bound_user_echo_repaired"


def test_real_wrapper_call_order_has_no_preattached_role_but_guard_uses_current_event(monkeypatch):
    logic = _logic()
    del logic["current_turn_source_role_p4"]
    seen = {}

    def original_emit(self, event, tick_result):
        assert "current_turn_source_role_p4" not in tick_result["logic"]
        final = self.right_brain.enforce_user_visible_japanese(
            ECHO, tick_result["logic"], user_input=event["user_input"], memory_data={}
        )
        seen["final"] = final
        seen["guard"] = deepcopy(tick_result["logic"]["visible_language_guard"])
        return {"logic": tick_result["logic"], "runtime_trace": {}}

    monkeypatch.setenv(rewrite_action.FLAG, "1")
    monkeypatch.setattr(rewrite_action, "_ORIGINAL_EMIT", original_emit)
    monkeypatch.setattr(rewrite_action, "sync_current_history_m41_1", lambda _result: None)
    owner = SimpleNamespace(
        right_brain=RightBrain(load_model=False),
        runtime=SimpleNamespace(cycle_index=1, blackboard=[], turn_traces=[]),
    )
    result = rewrite_action.emit_response_with_explicit_rewrite_action_p4(
        owner, {"user_input": USER}, {"logic": logic, "route_info": {}}
    )
    assert seen["final"] == EXPECTED
    assert seen["guard"]["final_reply_sha256"] == hashlib.sha256(EXPECTED.encode()).hexdigest()
    assert result["logic"]["current_turn_source_role_p4"]["act"] == "ordinary_chat"


@pytest.mark.parametrize(
    "change",
    [
        "role_digest",
        "role_quote",
        "m31_digest",
        "m31_subject",
        "m31_proposition",
        "m32_status",
        "m32_reply",
        "lineage_event",
        "lineage_parent",
        "lineage_digest",
        "core_message",
        "intent",
    ],
)
def test_missing_or_stale_source_certificate_fails_closed(change):
    logic = _logic()
    if change == "role_digest":
        logic["current_turn_source_role_p4"]["raw_input_sha256"] = "0" * 64
    elif change == "role_quote":
        logic["current_turn_source_role_p4"]["quote_role"] = "friend_quote"
    elif change == "m31_digest":
        logic["semantic_authorization_m31"]["input_digest"] = "0" * 16
    elif change == "m31_subject":
        logic["semantic_authorization_m31"]["m32_repair_candidate"]["subject_jp"] = "友達"
    elif change == "m31_proposition":
        logic["semantic_authorization_m31"]["m32_repair_candidate"]["literal_summary_jp"] += "別の場所"
    elif change == "m32_status":
        logic["semantic_commit_repair_m32"]["status"] = "not_applicable"
    elif change == "m32_reply":
        logic["semantic_commit_repair_m32"]["response_jp"] = "別の返答。"
    elif change == "lineage_event":
        logic["mixed_act_lineage_p4"]["event_id"] = "stale-event"
    elif change == "lineage_parent":
        logic["mixed_act_lineage_p4"]["producer_edges"][1]["from_id"] = "stale-parent"
    elif change == "lineage_digest":
        logic["mixed_act_lineage_p4"]["raw_input_sha256"] = "0" * 64
    elif change == "core_message":
        logic["core_message_jp"] = "別の返答。"
    elif change == "intent":
        logic["intent"] = "ordinary_chat"

    final, guard = _guard(ECHO, logic=logic)
    assert final == "ん、もう少し聞かせて。"
    assert guard["repair_action"] == "unverified_user_actor_fail_closed"
    assert guard["actor_boundary"]["status"] == "source_unverified"
    assert "うちは" not in final


@pytest.mark.parametrize(
    "field", ["current_turn_source_role_p4", "semantic_authorization_m31", "semantic_commit_repair_m32", "mixed_act_lineage_p4"]
)
def test_malformed_certificate_shape_fails_closed_without_throwing(field):
    logic = _logic()
    logic[field] = ["malformed"]
    final, guard = _guard(ECHO, logic=logic)
    assert final == "ん、もう少し聞かせて。"
    assert guard["actor_boundary"]["status"] == "source_unverified"


@pytest.mark.parametrize(
    "altered",
    [
        "私は2041年3月12日の集合場所を青い窓の前に決めたんだね。",
        "私は2041年3月13日の集合場所を琥珀色の温室の入口に決めたんだね。",
        "私は2041年3月12日の集合場所を琥珀色の温室の入口に変えたんだね。",
    ],
)
def test_near_miss_date_place_or_action_is_not_user_certified(altered):
    final, guard = _guard(altered, logic=_logic())
    assert final == "ん、もう少し聞かせて。"
    assert guard["actor_boundary"]["status"] == "source_unverified"


@pytest.mark.parametrize(
    "user",
    [
        "友達が「私は2041年3月12日の集合場所を琥珀色の温室の入口に決めた」と言った。",
        "「私は2041年3月12日の集合場所を琥珀色の温室の入口に決めた」を言い換えて。",
        "私は2041年3月12日の集合場所を琥珀色の温室の入口に決めたかも。",
        "私は2041年3月12日の集合場所を前の案じゃなく琥珀色の温室の入口に訂正した。",
        "私は2041年3月12日の集合場所を琥珀色の温室の入口に決めたが、友達は白い階段の下に決めた。",
        "私は2041年3月12日の集合場所を琥珀色の温室の入口に決めたけど太郎は白い階段を選んだ。",
        "私は2041年3月12日の集合場所を琥珀色の温室の入口に決めた太郎が別の場所を選んだ。",
    ],
)
def test_reported_quoted_uncertain_or_corrected_source_never_gets_user_certificate(user):
    final, guard = _guard(ECHO, user=user, logic=_logic(user, ECHO))
    assert guard["actor_boundary"]["status"] == "source_unverified"
    assert final == "ん、もう少し聞かせて。"


def test_quoted_first_person_stays_attributed_while_unquoted_self_register_changes():
    raw = "友達は「私は白い階段の下に決めた」と言ってた。私はまだ決めてない。"
    user = "友達の台詞「私は白い階段の下に決めた」をそのまま引用して。"
    final, guard = _guard(raw, user=user, logic={"scene": "casual"})
    assert final == "友達は「私は白い階段の下に決めた」と言ってた。うちはまだ決めてない。"
    assert guard["actor_boundary"]["status"] == "not_applicable"
    assert RightBrain(load_model=False)._sanitize_reply(raw, max_chars=120) == raw


def test_unbalanced_quote_does_not_publish_ambiguous_first_person_owner():
    raw = "友達は「私は行った”と言った。私はまだ決めてない。"
    final, guard = _guard(raw, user="友達の台詞を聞いた。", logic={"scene": "casual"})
    assert final == "ん、その話もう少し聞かせて。"
    assert "unbalanced_japanese_quote" in guard["initial_rejection_reasons"]


def test_real_uruha_self_reference_stays_uruha_and_private_life_word_is_untouched():
    raw = "私はまだ決めてない。私生活の話でもないし。"
    final, guard = _guard(raw, user="お前はどう思う？", logic={"scene": "casual"})
    assert final == "うちはまだ決めてない。私生活の話でもないし。"
    assert guard["repair_action"] == "localized_known_terms"


def test_user_decision_followed_by_question_about_uruha_is_not_rebound_to_user():
    user = "私は見学先を決めた。お前はもう決めた？"
    final, guard = _guard("私はまだ決めてない。", user=user, logic={"scene": "casual"})
    assert final == "うちはまだ決めてない。"
    assert guard["actor_boundary"]["status"] == "not_applicable"


@pytest.mark.parametrize("user", ["我今天還沒決定。", "I have not decided yet.", "まだ決めてないの？"])
def test_nonmatching_languages_do_not_convert_real_uruha_self_into_user_actor(user):
    final, guard = _guard("私はまだ決めてない。", user=user, logic={"scene": "casual"})
    assert final == "うちはまだ決めてない。"
    assert guard["actor_boundary"]["status"] == "not_applicable"
