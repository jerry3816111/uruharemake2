"""Synthetic contracts for the product-only profile acknowledgement boundary."""

from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace
import datetime
import os
import subprocess
import sys
import uuid

import chromadb
import pytest

from uruha_brain_mac import MemoryManager
import uruha_explicit_preference_acknowledgement_p4 as p4h
import uruha_multilingual_current_preference_p4 as p4i
import uruha_profile_owner_admission_p4 as owner
import uruha_profile_write_ack_truth_p4 as ack


FRIEND_MESSAGE = "友人からの伝言。今は甘酒が好き。今の好みとして覚えといて。"
QUOTED_MESSAGE = "「今はゆず茶が好き」と書いた。今の好みとして覚えといて。"
TWO_SELF_VALUES = "今は柿茶が好き。今は桑茶が好き。今の好みとして覚えといて。"
SELF_JA = "今は紫蘇茶が好き。今の好みとして覚えといて。"
SELF_EN = "I prefer plum tea. Please remember this as my current drink preference."
SELF_ZH = "我現在喜歡桂花茶。請記住我現在的飲料偏好。"
CORRECTION_JA = "訂正。もう紫蘇茶は好みじゃない。今は黒糖茶が好き。今の好みとして覚えといて。"


@pytest.fixture
def guard_chain(monkeypatch):
    """Run the frozen P4-H guard under the new outer product guard."""
    monkeypatch.setattr(
        p4h,
        "_ORIGINAL_VISIBLE_GUARD",
        lambda self, reply, logic, user_input="", memory_data=None: reply,
    )
    monkeypatch.setattr(ack, "_ORIGINAL_VISIBLE_GUARD", p4h.visible_guard_with_explicit_preference_acknowledgement_p4)
    monkeypatch.setattr(
        p4h,
        "_ORIGINAL_RULE_PLAN",
        lambda self, user_input, current_psyche, memory_data=None: {"intent": "delegated"},
    )
    monkeypatch.setattr(ack, "_ORIGINAL_RULE_PLAN", p4h.rule_plan_with_explicit_preference_memory_act_p4)


@pytest.fixture
def writer_chain(monkeypatch, tmp_path):
    client = chromadb.PersistentClient(path=str(tmp_path / "chroma"))
    memory = object.__new__(MemoryManager)
    memory.episode_col = client.get_or_create_collection("episodes")
    memory.profile_col = client.get_or_create_collection("profiles")
    memory.session_turns = []
    memory.short_term_buffer = []
    memory.session_profile = {"name": None, "likes": [], "dislikes": [], "favorites": []}
    memory._refresh_profile_state_shadow = lambda reference_time=None: None
    legacy_writer = MemoryManager._remember_profile_facts
    legacy_extractor = MemoryManager._extract_profile_facts
    monkeypatch.setattr(ack, "_ORIGINAL_LEGACY_PROFILE_FALLBACK", legacy_writer)
    monkeypatch.setattr(
        p4i,
        "_ORIGINAL_REMEMBER_PROFILE_FACTS",
        ack.legacy_profile_fallback_with_profile_write_ack_truth_p4,
    )
    monkeypatch.setattr(owner, "_ORIGINAL_REMEMBER_PROFILE_FACTS", p4i.remember_profile_facts_with_current_preference_p4)
    monkeypatch.setattr(owner, "_ORIGINAL_EXTRACT_PROFILE_FACTS", legacy_extractor)
    monkeypatch.setattr(MemoryManager, "_extract_profile_facts", owner._extract_with_admitted_facts)
    monkeypatch.setattr(MemoryManager, "_remember_profile_facts", owner.remember_profile_facts_with_owner_admission_p4)
    return memory


@pytest.mark.parametrize(
    "source,reason,reply",
    [
        (FRIEND_MESSAGE, "selected_source_has_unresolved_preamble", ack.NON_COMMITMENT_REPLY),
        (QUOTED_MESSAGE, "quoted_scope", ack.NON_COMMITMENT_REPLY),
        (TWO_SELF_VALUES, "selected_act_ambiguous_extraction", ack.MULTIPLE_VALUES_REPLY),
    ],
)
def test_rejected_preflight_uses_writer_decision_and_truthful_reason(source, reason, reply):
    observed = ack.preflight_profile_write_ack_p4(source)
    assert observed["selected"] is True
    assert observed["admitted"] is False
    assert observed["reason"] == reason
    assert observed["owner_admission"]["admitted_count"] == 0
    assert ack._rejection_reply(observed) == reply
    assert source not in repr(observed)


@pytest.mark.parametrize("source,act", [(SELF_JA, "write"), (SELF_EN, "write"), (SELF_ZH, "write"), (CORRECTION_JA, "correction")])
def test_explicit_self_preflight_keeps_p4_h_authority(source, act, writer_chain):
    observed = ack.preflight_profile_write_ack_p4(source, memory=writer_chain)
    assert observed["selected"] is True
    assert observed["admitted"] is True
    assert observed["act"] == act
    assert observed["owner_admission"]["admitted_count"] == 1
    assert source not in repr(observed)


def test_rejected_plan_and_surface_precede_episode_and_cancel_p4_h_promise(guard_chain):
    plan = ack.rule_plan_with_profile_write_ack_truth_p4(object(), FRIEND_MESSAGE, {}, {})
    assert plan["intent"] == "profile_write_ack_rejected"
    assert plan["core_message_jp"] == ack.NON_COMMITMENT_REPLY
    assert "覚えとく" not in plan["core_message_jp"]
    logic = {"visible_language_guard": {"original_reply": "友人の話なんだね。"}}
    final = ack.visible_guard_with_profile_write_ack_truth_p4(
        object(), "友人の話なんだね。", logic, user_input=FRIEND_MESSAGE, memory_data={}
    )
    assert final == ack.NON_COMMITMENT_REPLY
    assert logic[p4h.LABEL]["status"] == "blocked_by_profile_owner_admission_p4"
    assert logic[p4h.LABEL]["surface_authority"] is False
    assert logic["visible_language_guard"]["final_reply"] == final
    assert logic[ack.LABEL]["status"] == "preflight_rejected_pending_writer"


def test_two_self_values_get_clarification_not_false_third_party_attribution(guard_chain):
    plan = ack.rule_plan_with_profile_write_ack_truth_p4(object(), TWO_SELF_VALUES, {}, {})
    assert plan["core_message_jp"] == ack.MULTIPLE_VALUES_REPLY
    logic = {"visible_language_guard": {"original_reply": "候補があるね。"}}
    final = ack.visible_guard_with_profile_write_ack_truth_p4(
        object(), "候補があるね。", logic, user_input=TWO_SELF_VALUES, memory_data={}
    )
    assert final == ack.MULTIPLE_VALUES_REPLY
    assert "あなたの好みとしては" not in final
    assert "覚えとく" not in final


@pytest.mark.parametrize("source,act", [(SELF_JA, "write"), (SELF_EN, "write"), (SELF_ZH, "write"), (CORRECTION_JA, "correction")])
def test_positive_plan_and_surface_are_frozen_p4_h_exact(guard_chain, writer_chain, source, act):
    memory_data = {ack.LABEL: ack.preflight_profile_write_ack_p4(source, memory=writer_chain)}
    plan = ack.rule_plan_with_profile_write_ack_truth_p4(object(), source, {}, memory_data)
    assert plan["intent"] == ("explicit_preference_memory_correction" if act == "correction" else "explicit_preference_memory_write")
    logic = {"visible_language_guard": {"original_reply": "了解しました。"}}
    final = ack.visible_guard_with_profile_write_ack_truth_p4(
        object(), "了解しました。", logic, user_input=source, memory_data=memory_data
    )
    assert final == p4h.AUTHORITATIVE_SURFACES[act]
    assert logic[p4h.LABEL]["status"] == "explicit_preference_memory_act_committed"
    assert logic[ack.LABEL]["status"] == "preflight_admitted_pending_writer"


def test_nontarget_and_protected_surface_remain_prior_authority(guard_chain, monkeypatch):
    ordinary = "今日は静かに本を読む。"
    logic = {"visible_language_guard": {"original_reply": "そうなんだ。"}}
    assert ack.rule_plan_with_profile_write_ack_truth_p4(object(), ordinary, {}, {}) == {"intent": "delegated"}
    assert ack.visible_guard_with_profile_write_ack_truth_p4(
        object(), "そうなんだ。", logic, user_input=ordinary, memory_data={}
    ) == "そうなんだ。"
    assert ack.LABEL not in logic

    monkeypatch.setattr(
        p4h,
        "_ORIGINAL_VISIBLE_GUARD",
        lambda self, reply, logic, user_input="", memory_data=None: "今は一人で抱えないで。",
    )
    protected = {
        "semantic_route_m22": {"selected_type": "safety_sensitive"},
        "visible_language_guard": {"final_reply": "今は一人で抱えないで。"},
    }
    assert ack.visible_guard_with_profile_write_ack_truth_p4(
        object(), "ignored", protected, user_input=FRIEND_MESSAGE, memory_data={}
    ) == "今は一人で抱えないで。"
    assert protected[ack.LABEL]["protected_logic"] is True
    assert protected[p4h.LABEL]["surface_authority"] is False


def test_protected_generic_ack_cannot_become_memory_promise(guard_chain):
    logic = {
        "semantic_route_m22": {"selected_type": "safety_sensitive"},
        "visible_language_guard": {"final_reply": "了解しました。"},
    }
    final = ack.visible_guard_with_profile_write_ack_truth_p4(
        object(), "了解しました。", logic, user_input=FRIEND_MESSAGE, memory_data={}
    )
    assert final == "了解しました。"
    assert final not in p4h.AUTHORITATIVE_SURFACES.values()
    assert logic[p4h.LABEL]["surface_authority"] is False
    assert logic[ack.LABEL]["protected_logic"] is True


def test_protected_generic_ack_without_prior_guard_evidence_fails_before_write(guard_chain):
    logic = {"semantic_route_m22": {"selected_type": "safety_sensitive"}}
    with pytest.raises(ack.ProfileWriteAckIntegrityError, match="protected_surface_unavailable_prewrite"):
        ack.visible_guard_with_profile_write_ack_truth_p4(
            object(), "了解しました。", logic, user_input=FRIEND_MESSAGE, memory_data={}
        )


def test_protected_intent_overrides_general_route_without_overwriting_safety(guard_chain, monkeypatch):
    monkeypatch.setattr(
        p4h,
        "_ORIGINAL_VISIBLE_GUARD",
        lambda self, reply, logic, user_input="", memory_data=None: "今は一人で抱えないで。",
    )
    logic = {
        "intent": "crisis_support",
        "scene": "support",
        "semantic_route_m22": {"selected_type": "general_conversation"},
        "visible_language_guard": {"final_reply": "今は一人で抱えないで。"},
    }
    final = ack.visible_guard_with_profile_write_ack_truth_p4(
        object(), "ignored", logic, user_input=FRIEND_MESSAGE, memory_data={}
    )
    assert final == "今は一人で抱えないで。"
    assert logic[ack.LABEL]["protected_logic"] is True


def _add_prior_typed_preference(memory, *, value, scope):
    record = p4i._typed_record(
        "like",
        value,
        timestamp=datetime.datetime.now().astimezone().isoformat(timespec="microseconds"),
        memory_id=str(uuid.uuid4()),
        extraction={
            "language": "ja",
            "input_sha256": ack._digest("synthetic prior preference"),
            "act": "write",
            "classifier_cue_id": "synthetic:write",
        },
        scope=scope,
        semantics="current_preference",
    )
    memory.profile_col.add(
        ids=[record["memory_id"]],
        documents=[record["document"]],
        metadatas=[record["metadata"]],
    )


def test_multi_scope_old_value_gets_prewrite_clarification_and_zero_delta(writer_chain, guard_chain):
    _add_prior_typed_preference(writer_chain, value="紫蘇茶", scope="drink")
    _add_prior_typed_preference(writer_chain, value="紫蘇茶", scope="snack")
    preflight = ack.preflight_profile_write_ack_p4(CORRECTION_JA, memory=writer_chain)
    assert preflight["owner_admitted"] is True
    assert preflight["admitted"] is False
    assert preflight["scope_state"]["status"] == "ambiguous"
    assert preflight["scope_state"]["active_old_scope_count"] == 2
    assert preflight["reason"] == "old_value_has_multiple_active_scopes"
    memory_data = {ack.LABEL: preflight}
    plan = ack.rule_plan_with_profile_write_ack_truth_p4(object(), CORRECTION_JA, {}, memory_data)
    assert plan["core_message_jp"] == ack.AMBIGUOUS_SCOPE_REPLY
    logic = {"visible_language_guard": {"original_reply": "了解しました。"}}
    reply = ack.visible_guard_with_profile_write_ack_truth_p4(
        object(), "了解しました。", logic, user_input=CORRECTION_JA, memory_data=memory_data
    )
    assert reply == ack.AMBIGUOUS_SCOPE_REPLY
    brain, result = _real_result(writer_chain, CORRECTION_JA, reply, logic)
    assert writer_chain.profile_col.count() == 2
    assert all(
        "黒糖茶" not in str(metadata.get("value") or "")
        for metadata in writer_chain.profile_col.get(include=["metadatas"])["metadatas"]
    )
    assert writer_chain.episode_col.count() == 1
    assert writer_chain.session_turns[-1]["reply"] == ack.AMBIGUOUS_SCOPE_REPLY
    typed = result["memory_runtime"][p4i.LABEL]
    actual_owner = result["memory_runtime"][owner.LABEL]
    assert (typed["status"], typed["reason"]) == (
        "ambiguous_extraction", "old_value_has_multiple_active_scopes"
    )
    assert actual_owner["admitted_count"] == 1
    assert actual_owner["writer_status"] == "typed_write_not_completed"
    assert actual_owner["profile_collection_count_delta"] == 0
    ack.materialize_profile_write_ack_truth_p4(brain, result)
    assert result["logic"][ack.LABEL]["status"] == "matched"
    assert result["logic"][ack.LABEL]["owner_admitted"] is True
    assert result["logic"][ack.LABEL]["admitted"] is False
    assert result["logic"][ack.LABEL]["actual_writer_status"] == "typed_write_not_completed"
    assert result["logic"][ack.LABEL]["checks"]["writer_outcome"] == "matched"
    assert result["logic"][ack.LABEL]["legacy_fallback_suppressed"] is True
    assert result["logic"][ack.LABEL]["checks"]["legacy_fallback_suppressed"] == "matched"
    assert result["logic"][ack.LABEL]["legacy_fallback_evidence"]["episode_id_sha256"] == result["logic"][ack.LABEL]["episode_id_sha256"]
    assert CORRECTION_JA not in repr(result["logic"][ack.LABEL]["legacy_fallback_evidence"])
    assert not [row for row in result["runtime_trace"]["blackboard"] if row["label"] == p4h.LABEL]
    assert [row for row in result["runtime_trace"]["blackboard"] if row["label"] == ack.LABEL][0]["payload"]["status"] == "matched"


def test_state_blocked_guard_does_not_disable_adjacent_legacy_owner_write(writer_chain):
    _add_prior_typed_preference(writer_chain, value="紫蘇茶", scope="drink")
    _add_prior_typed_preference(writer_chain, value="紫蘇茶", scope="snack")
    writer_chain._remember_profile_facts(CORRECTION_JA)
    assert writer_chain.profile_col.count() == 2
    writer_chain._remember_profile_facts("海が好き。")
    assert writer_chain.profile_col.count() == 3
    assert writer_chain._last_profile_owner_admission_p4["path"] == "legacy"
    assert writer_chain._last_profile_owner_admission_p4["writer_status"] == "legacy_writer_returned"
    assert writer_chain._last_profile_owner_admission_p4["profile_collection_count_delta"] == 1
    assert any(
        metadata.get("value") == "海"
        for metadata in writer_chain.profile_col.get(include=["metadatas"])["metadatas"]
    )


def test_one_active_old_scope_keeps_correction_and_exact_scope_readback(writer_chain, guard_chain):
    _add_prior_typed_preference(writer_chain, value="紫蘇茶", scope="drink")
    preflight = ack.preflight_profile_write_ack_p4(CORRECTION_JA, memory=writer_chain)
    assert preflight["admitted"] is True
    assert preflight["scope_state"]["status"] == "unique"
    memory_data = {ack.LABEL: preflight}
    logic = {"visible_language_guard": {"original_reply": "了解しました。"}}
    reply = ack.visible_guard_with_profile_write_ack_truth_p4(
        object(), "了解しました。", logic, user_input=CORRECTION_JA, memory_data=memory_data
    )
    brain, result = _real_result(writer_chain, CORRECTION_JA, reply, logic)
    ack.materialize_profile_write_ack_truth_p4(brain, result)
    assert writer_chain.profile_col.count() == 3
    assert result["logic"][ack.LABEL]["status"] == "matched"
    assert result["logic"][ack.LABEL]["checks"]["profile_id_readback"] == "matched"
    assert reply == p4h.AUTHORITATIVE_SURFACES["correction"]


def test_unavailable_scope_state_fails_before_writer_or_episode(writer_chain, monkeypatch):
    preflight = ack.preflight_profile_write_ack_p4(CORRECTION_JA)
    assert preflight["admitted"] is False
    assert preflight["scope_state"]["status"] == "unavailable"
    monkeypatch.setattr(ack, "_ORIGINAL_EMIT", lambda *_args: pytest.fail("writer path was entered"))
    with pytest.raises(ack.ProfileWriteAckIntegrityError, match="scope_state_unavailable_prewrite"):
        ack.emit_response_if_ready_with_profile_write_ack_truth_p4(
            SimpleNamespace(),
            {"user_input": CORRECTION_JA, "memory_data": {ack.LABEL: preflight}},
            {},
        )
    assert writer_chain.episode_col.count() == 0
    assert writer_chain.profile_col.count() == 0


def _real_result(memory, source, reply, logic):
    doc = memory.save_episode(source, reply, {}, logic)
    owner_audit = deepcopy(memory._last_profile_owner_admission_p4)
    typed_audit = deepcopy(memory._last_multilingual_current_preference_p4)
    rows = [
        {"stage": "surface", "label": p4h.LABEL, "payload": deepcopy(logic.get(p4h.LABEL) or {})},
        {"stage": "surface", "label": "utterance", "payload": {"reply": reply}},
        {"stage": "memory", "label": "memory_updates", "payload": {}},
        {"stage": "memory", "label": owner.LABEL, "payload": deepcopy(owner_audit)},
    ]
    result = {
        "reply": reply,
        "logic": logic,
        "episode_doc": doc,
        "memory_runtime": {owner.LABEL: owner_audit, p4i.LABEL: typed_audit},
        "runtime_trace": {"cycle_index": 1, "blackboard": rows},
    }
    brain = SimpleNamespace(memory=memory, runtime=SimpleNamespace(last_reply=reply, blackboard=rows, turn_traces=[]))
    return brain, result


def test_rejected_actual_writer_and_persisted_episode_match_graph(writer_chain, guard_chain):
    logic = {"visible_language_guard": {"original_reply": "友人の話なんだね。"}}
    reply = ack.visible_guard_with_profile_write_ack_truth_p4(
        object(), "友人の話なんだね。", logic, user_input=FRIEND_MESSAGE, memory_data={}
    )
    brain, result = _real_result(writer_chain, FRIEND_MESSAGE, reply, logic)
    assert writer_chain.profile_col.count() == 0
    assert writer_chain.episode_col.count() == 1
    ack.materialize_profile_write_ack_truth_p4(brain, result)
    assert result["logic"][ack.LABEL]["status"] == "matched"
    assert not any(row["label"] == p4h.LABEL for row in result["runtime_trace"]["blackboard"])
    assert "flow" not in result["logic"][p4h.LABEL]
    assert [row for row in result["runtime_trace"]["blackboard"] if row["label"] == ack.LABEL][0]["payload"]["checks"]["episode_persistent_reply"] == "matched"
    assert writer_chain.session_turns[-1]["reply"] == reply


def test_multiple_self_values_do_not_get_recorded_or_called_third_party(writer_chain, guard_chain):
    logic = {"visible_language_guard": {"original_reply": "候補があるね。"}}
    reply = ack.visible_guard_with_profile_write_ack_truth_p4(
        object(), "候補があるね。", logic, user_input=TWO_SELF_VALUES, memory_data={}
    )
    brain, result = _real_result(writer_chain, TWO_SELF_VALUES, reply, logic)
    ack.materialize_profile_write_ack_truth_p4(brain, result)
    assert writer_chain.profile_col.count() == 0
    assert result["logic"][ack.LABEL]["status"] == "matched"
    assert result["logic"][ack.LABEL]["reason"] == "selected_act_ambiguous_extraction"
    assert result["reply"] == ack.MULTIPLE_VALUES_REPLY


def test_positive_actual_writer_and_persisted_episode_match_graph(writer_chain, guard_chain):
    logic = {"visible_language_guard": {"original_reply": "了解しました。"}}
    reply = ack.visible_guard_with_profile_write_ack_truth_p4(
        object(), "了解しました。", logic, user_input=SELF_JA, memory_data={}
    )
    brain, result = _real_result(writer_chain, SELF_JA, reply, logic)
    assert writer_chain.profile_col.count() == 1
    assert writer_chain.episode_col.count() == 1
    ack.materialize_profile_write_ack_truth_p4(brain, result)
    assert result["logic"][ack.LABEL]["status"] == "matched"
    assert result["logic"][ack.LABEL]["checks"]["profile_id_readback"] == "matched"
    assert result["reply"] == p4h.AUTHORITATIVE_SURFACES["write"]


def test_correction_actual_writer_keeps_both_rows_and_episode(writer_chain, guard_chain):
    initial_logic = {"visible_language_guard": {"original_reply": "了解しました。"}}
    initial_reply = ack.visible_guard_with_profile_write_ack_truth_p4(
        object(), "了解しました。", initial_logic, user_input=SELF_JA, memory_data={}
    )
    _real_result(writer_chain, SELF_JA, initial_reply, initial_logic)
    correction_logic = {"visible_language_guard": {"original_reply": "了解しました。"}}
    memory_data = {ack.LABEL: ack.preflight_profile_write_ack_p4(CORRECTION_JA, memory=writer_chain)}
    correction_reply = ack.visible_guard_with_profile_write_ack_truth_p4(
        object(), "了解しました。", correction_logic, user_input=CORRECTION_JA, memory_data=memory_data
    )
    brain, result = _real_result(writer_chain, CORRECTION_JA, correction_reply, correction_logic)
    ack.materialize_profile_write_ack_truth_p4(brain, result)
    assert writer_chain.profile_col.count() == 3
    assert writer_chain.episode_col.count() == 2
    assert result["logic"][ack.LABEL]["status"] == "matched"
    assert result["logic"][ack.LABEL]["checks"]["profile_id_readback"] == "matched"
    assert result["reply"] == p4h.AUTHORITATIVE_SURFACES["correction"]


def test_unexpected_writer_failure_is_mismatch_and_never_late_rewrites_reply(writer_chain, guard_chain):
    logic = {"visible_language_guard": {"original_reply": "了解しました。"}}
    reply = ack.visible_guard_with_profile_write_ack_truth_p4(
        object(), "了解しました。", logic, user_input=SELF_JA, memory_data={}
    )
    brain, result = _real_result(writer_chain, SELF_JA, reply, logic)
    result["memory_runtime"][owner.LABEL]["writer_status"] = "typed_write_not_completed"
    ack.materialize_profile_write_ack_truth_p4(brain, result)
    assert result["logic"][ack.LABEL]["status"] == "mismatch"
    assert result["logic"][ack.LABEL]["checks"]["writer_outcome"] == "mismatch"
    assert result["reply"] == reply
    assert writer_chain.session_turns[-1]["reply"] == reply
    with pytest.raises(ack.ProfileWriteAckIntegrityError, match="mismatch"):
        ack.require_matched_profile_write_ack_p4(result)


def test_missing_writer_evidence_is_unknown_not_success(writer_chain, guard_chain):
    logic = {"visible_language_guard": {"original_reply": "友人の話なんだね。"}}
    reply = ack.visible_guard_with_profile_write_ack_truth_p4(
        object(), "友人の話なんだね。", logic, user_input=FRIEND_MESSAGE, memory_data={}
    )
    brain, result = _real_result(writer_chain, FRIEND_MESSAGE, reply, logic)
    result["memory_runtime"].pop(owner.LABEL)
    ack.materialize_profile_write_ack_truth_p4(brain, result)
    assert result["logic"][ack.LABEL]["status"] == "unknown"
    assert result["logic"][ack.LABEL]["writeback_observed"] is False
    with pytest.raises(ack.ProfileWriteAckIntegrityError, match="unknown"):
        ack.require_matched_profile_write_ack_p4(result)


def test_nested_run_emit_finishes_once_with_one_graph_node_and_one_history_row(
    writer_chain, guard_chain, monkeypatch
):
    logic = {"visible_language_guard": {"original_reply": "友人の話なんだね。"}}
    reply = ack.visible_guard_with_profile_write_ack_truth_p4(
        object(), "友人の話なんだね。", logic, user_input=FRIEND_MESSAGE, memory_data={}
    )
    brain, result = _real_result(writer_chain, FRIEND_MESSAGE, reply, logic)
    result["runtime_state"] = {
        "blackboard": [],
        "recent_turn_traces": [{"cycle_index": 1, "blackboard": []}],
    }
    brain.runtime.turn_traces = [{"cycle_index": 1, "blackboard": []}]
    monkeypatch.setattr(ack, "_ORIGINAL_EMIT", lambda self, event, tick_result: result)
    monkeypatch.setattr(
        ack,
        "_ORIGINAL_RUN",
        lambda self, user_input, input_context=None: ack.emit_response_if_ready_with_profile_write_ack_truth_p4(
            self, {}, {}
        ),
    )
    observed = ack.run_turn_debug_with_profile_write_ack_truth_p4(brain, FRIEND_MESSAGE)
    assert observed is result
    assert ack._RUN_ACTIVE.get() is False
    assert [row["label"] for row in result["runtime_trace"]["blackboard"]].count(ack.LABEL) == 1
    assert len(result["runtime_state"]["recent_turn_traces"]) == 1
    assert [row["label"] for row in result["runtime_state"]["recent_turn_traces"][-1]["blackboard"]].count(ack.LABEL) == 1
    assert [row["label"] for row in brain.runtime.turn_traces[-1]["blackboard"]].count(ack.LABEL) == 1


def test_isolated_no_model_full_brain_rejects_false_promise_before_episode(tmp_path):
    """The additive entry must preserve one visible/episode/graph reply."""
    program = r'''
import datetime, json, os, uuid
from pathlib import Path
root=Path(os.environ["P4_ACK_TEST_ROOT"])
os.environ["URUHA_ADAPTIVE_PERSON_MODEL_PATH"]=str(root/"adaptive.json")
os.environ["URUHA_MEMORY_DB_PATH"]=str(root/"memory")
os.environ["URUHA_WEB_PREWARM_BRAIN"]="0"
os.environ["URUHA_IDLE_VISIBLE_PROACTIVE_ENABLED"]="false"
os.environ["GRADIO_ANALYTICS_ENABLED"]="false"
import project_paths
project_paths.WEB_LOG_DIR=str(root/"web")
project_paths.WEB_CONVERSATION_LOG_JSONL_PATH=str(root/"web/turns.jsonl")
project_paths.WEB_CONVERSATION_LOG_TXT_PATH=str(root/"web/turns.txt")
import uruha_web_ui_product_p4_profile_ack as entry
from test_personhood_loop_v2_13 import _IsolatedContractBrain
from uruha_brain_mac import LeftBrain, MemoryManager, RightBrain
from uruha_memory_observatory import collect_cognitive_graph
import uruha_profile_write_ack_truth_p4 as ack
import uruha_multilingual_current_preference_p4 as p4i
source="友人からの伝言。今は甘酒が好き。今の好みとして覚えといて。"
brain=_IsolatedContractBrain()
brain.memory=MemoryManager()
brain.left_brain=LeftBrain(None)
brain.right_brain=RightBrain(load_model=False)
brain.right_brain.speak=lambda user_input,logic,memory_data,psyche: str(logic.get("core_message_jp") or "ん。")
result=brain.run_turn_debug(source)
truth=result["logic"][ack.LABEL]
assert truth["status"]=="matched",truth
assert result["reply"]==ack.NON_COMMITMENT_REPLY,result["reply"]
assert result["memory_runtime"]["profile_owner_admission_p4"]["admitted_count"]==0
assert brain.memory.profile_col.count()==0
assert brain.memory.episode_col.count()==1
assert brain.memory.session_turns[-1]["reply"]==result["reply"]
nodes=[row for row in result["runtime_trace"]["blackboard"] if row.get("label")==ack.LABEL]
assert len(nodes)==1,nodes
assert not [row for row in result["runtime_trace"]["blackboard"] if row.get("label")=="explicit_preference_acknowledgement_p4"]
graph=collect_cognitive_graph(result)
assert len([node for node in graph["nodes"] if node["label"]==ack.LABEL])==1
positive="今は紫蘇茶が好き。今の好みとして覚えといて。"
second=brain.run_turn_debug(positive)
assert second["logic"][ack.LABEL]["status"]=="matched",second["logic"][ack.LABEL]
assert second["reply"]=="ん、その好みは覚えとく。",second["reply"]
assert brain.memory.profile_col.count()==1
assert brain.memory.episode_col.count()==2
assert brain.memory.session_turns[-1]["reply"]==second["reply"]
assert len([row for row in second["runtime_trace"]["blackboard"] if row.get("label")==ack.LABEL])==1
for scope in ("drink", "snack"):
    prior=p4i._typed_record(
        "like", "よもぎ茶",
        timestamp=datetime.datetime.now().astimezone().isoformat(timespec="microseconds"),
        memory_id=str(uuid.uuid4()),
        extraction={"language":"ja", "input_sha256":ack._digest("synthetic prior"), "act":"write", "classifier_cue_id":"synthetic:write"},
        scope=scope, semantics="current_preference",
    )
    brain.memory.profile_col.add(ids=[prior["memory_id"]],documents=[prior["document"]],metadatas=[prior["metadata"]])
correction="訂正。もうよもぎ茶は好みじゃない。今は黒糖茶が好き。今の好みとして覚えといて。"
third=brain.run_turn_debug(correction)
truth3=third["logic"][ack.LABEL]
assert truth3["status"]=="matched",truth3
assert truth3["reason"]=="old_value_has_multiple_active_scopes",truth3
assert truth3["owner_admitted"] is True and truth3["admitted"] is False,truth3
assert truth3["legacy_fallback_suppressed"] is True and truth3["checks"]["legacy_fallback_suppressed"]=="matched",truth3
assert third["reply"]==ack.AMBIGUOUS_SCOPE_REPLY,third["reply"]
assert brain.memory.profile_col.count()==3
assert not [m for m in brain.memory.profile_col.get(include=["metadatas"])["metadatas"] if "黒糖茶" in str(m.get("value") or "")]
assert brain.memory.episode_col.count()==3
assert brain.memory.session_turns[-1]["reply"]==third["reply"]
typed=third["memory_runtime"][p4i.LABEL]
owner=third["memory_runtime"]["profile_owner_admission_p4"]
assert (typed["status"],typed["reason"])==("ambiguous_extraction","old_value_has_multiple_active_scopes"),typed
assert (owner["admitted_count"],owner["writer_status"],owner["profile_collection_count_delta"])==(1,"typed_write_not_completed",0),owner
assert len([row for row in third["runtime_trace"]["blackboard"] if row.get("label")==ack.LABEL and row.get("payload",{}).get("status")=="matched"])==1
assert not [row for row in third["runtime_trace"]["blackboard"] if row.get("label")=="explicit_preference_acknowledgement_p4"]
graph3=collect_cognitive_graph(third)
assert len([node for node in graph3["nodes"] if node["label"]==ack.LABEL])==1
assert not [node for node in graph3["nodes"] if node["label"]=="explicit_preference_acknowledgement_p4"]
assert entry.RUNTIME is entry._prior.RUNTIME
print(json.dumps({"status":truth["status"],"reply":result["reply"],"positive_status":second["logic"][ack.LABEL]["status"],"ambiguous_status":truth3["status"]},ensure_ascii=False))
'''
    completed = subprocess.run(
        [sys.executable, "-c", program],
        env={**os.environ, "P4_ACK_TEST_ROOT": str(tmp_path)},
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert ack.NON_COMMITMENT_REPLY in completed.stdout
