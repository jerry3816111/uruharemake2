"""Zero-model contracts for the opt-in P4 two-action terminal transaction.

These tests use synthetic producer receipts and developer-authored N cases. They
are not fresh-generation, Safari, semantic-equivalence or persistence evidence.
"""

from copy import deepcopy
from collections import Counter
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import uuid

import pytest

import uruha_adaptive_person_model as adaptive
import uruha_memory_runtime as memory_runtime
import uruha_mixed_act_lineage_p4 as lineage
import uruha_mixed_past_place_source_authority_p4 as past_place
import uruha_typed_mixed_atomic_delivery_p4 as atomic


DATA = json.loads((Path(__file__).parent / "datasets" /
                   "p4_typed_mixed_atomic_delivery_probe_2026-10-20.json").read_text(encoding="utf-8"))
BY_ID = {row["id"]: row["input"] for row in DATA["cases"]}


def _sha(value):
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def _issued(raw=BY_ID["N2"], cycle=7):
    """Make a linked event/M31/M32 chain without a model, server or registry."""
    certificate = lineage._new_event(raw, cycle)
    event = {"user_input": raw, lineage.EVENT_KEY: certificate, "memory_data": {}}
    event_id = certificate["event_id"]
    m31_id = f"{event_id}:m31:{uuid.uuid4().hex}"
    m32_id = f"{event_id}:m32:{uuid.uuid4().hex}"
    common = {
        "schema": lineage.SCHEMA,
        "parent_event_id": event_id,
        "raw_input_sha256": _sha(raw),
        "cycle_index": cycle,
        "action_coverage_status": "unverified",
        "raw_dialogue_persisted": False,
        "authority_transfer_permitted": False,
    }
    m31 = {
        "schema": adaptive.SEMANTIC_AUTHORIZATION_SCHEMA_M31,
        "status": "semantically_authorized",
        "surface_authority": False,
        "input_digest": _sha(raw)[:16],
        lineage.PRODUCER_KEY: {
            **common,
            "producer": "m31",
            "proposal_id": m31_id,
            "status_at_return": "semantically_authorized",
        },
    }
    m32 = {
        "schema": adaptive.SEMANTIC_COMMIT_REPAIR_SCHEMA_M32,
        "status": "deterministic_commit_repaired",
        "surface_authority": True,
        "source_m31_status": "semantically_authorized",
        lineage.PRODUCER_KEY: {
            **common,
            "producer": "m32",
            "proposal_id": m32_id,
            "parent_m31_id": m31_id,
            "parent_m31_direct_argument": True,
            "parent_m31_status_at_build": "semantically_authorized",
            "status_at_return": "deterministic_commit_repaired",
        },
    }
    logic = {
        "intent": "chat", "scene": "casual", "surface_act": "plain_reply",
        "semantic_authorization_m31": m31,
        "semantic_commit_repair_m32": m32,
        "source_anchored_semantic_commit_m33": {"surface_authority": False},
    }
    context = {
        "certificate": deepcopy(certificate),
        "m31_attempts": 1, "m32_attempts": 1,
        "m31_ids": [m31_id], "m32_ids": [m32_id],
    }
    lineage_receipt = lineage.verify_mixed_act_lineage_p4(
        event, logic, registered_context=context, registration_reason="registered",
        route_info={"route": "high_road"},
    )
    assert lineage_receipt["status"] == "linked", lineage_receipt
    logic[lineage.LABEL] = lineage_receipt
    return event, {"logic": logic, "route_info": {"route": "high_road"}}


def _admit(event, tick):
    return atomic.verify_typed_mixed_atomic_admission_p4(event, tick)


def _memory(user_turns):
    recent = []
    passed = []
    for index, user in enumerate(user_turns):
        turn = {"user": user, "reply": "ん、分かった。", "episode_id": f"atomic-recent-{index}"}
        recent.append(turn)
        candidate = memory_runtime.recent_turn_candidates([turn])[0]
        passed.append({
            "source": "recent_turn", "channel": "recent_turns",
            "trace_id": memory_runtime.memory_trace_id(candidate),
            "text": f"User:{user} -> Uruha:ん、分かった。",
        })
    return {
        "recent_turns": recent,
        "memory_provenance": {
            "passed_to_leftbrain": passed,
            "passed_to_leftbrain_trace_ids": [row["trace_id"] for row in passed],
        },
    }


def test_linked_two_action_chain_is_only_a_candidate_for_terminal_delivery():
    event, tick = _issued()
    admission = _admit(event, tick)
    assert admission["eligible"] is True, admission
    assert [action["type"] for action in admission["actions"]] == [
        "quoted_rewrite", "past_user_place_recall",
    ]
    assert tick["logic"][lineage.LABEL]["authority_transfer_permitted"] is False
    assert tick["logic"]["semantic_authorization_m31"]["surface_authority"] is False
    assert tick["logic"]["semantic_commit_repair_m32"]["surface_authority"] is True
    assert admission.get("semantic_equivalence_verified") is not True


@pytest.mark.parametrize("mutation", [
    "missing_event", "changed_raw", "wrong_event", "wrong_event_digest",
    "wrong_event_cycle", "missing_action", "duplicate_action_id", "wrong_quote_span",
    "wrong_outside_span", "wrong_receipt_action", "missing_parent", "wrong_parent",
    "indirect_parent", "wrong_m31_digest", "wrong_m32_digest", "wrong_m31_cycle",
    "wrong_m32_cycle", "duplicate_producer_id", "missing_edge", "wrong_edge",
    "lineage_rejected", "m31_new_authority", "m32_not_authoritative",
])
def test_event_action_and_producer_tampering_never_admits(mutation):
    event, tick = _issued()
    cert = event[lineage.EVENT_KEY]
    actions = cert["actions"]
    logic = tick["logic"]
    m31 = logic["semantic_authorization_m31"]
    m32 = logic["semantic_commit_repair_m32"]
    receipt = logic[lineage.LABEL]
    if mutation == "missing_event":
        del event[lineage.EVENT_KEY]
    elif mutation == "changed_raw":
        event["user_input"] += "別文"
    elif mutation == "wrong_event":
        cert["event_id"] = "different-event"
    elif mutation == "wrong_event_digest":
        cert["raw_input_sha256"] = "0" * 64
    elif mutation == "wrong_event_cycle":
        cert["cycle_index"] += 1
    elif mutation == "missing_action":
        actions.pop()
    elif mutation == "duplicate_action_id":
        actions[1]["action_id"] = actions[0]["action_id"]
    elif mutation == "wrong_quote_span":
        actions[0]["raw_spans"][0][0] += 1
    elif mutation == "wrong_outside_span":
        actions[1]["raw_spans"][0][1] -= 1
    elif mutation == "wrong_receipt_action":
        receipt["actions"][1]["raw_spans"][0][0] += 1
    elif mutation == "missing_parent":
        m32[lineage.PRODUCER_KEY]["parent_m31_id"] = None
    elif mutation == "wrong_parent":
        m32[lineage.PRODUCER_KEY]["parent_m31_id"] = "different-parent"
    elif mutation == "indirect_parent":
        m32[lineage.PRODUCER_KEY]["parent_m31_direct_argument"] = False
    elif mutation == "wrong_m31_digest":
        m31[lineage.PRODUCER_KEY]["raw_input_sha256"] = "0" * 64
    elif mutation == "wrong_m32_digest":
        m32[lineage.PRODUCER_KEY]["raw_input_sha256"] = "0" * 64
    elif mutation == "wrong_m31_cycle":
        m31[lineage.PRODUCER_KEY]["cycle_index"] += 1
    elif mutation == "wrong_m32_cycle":
        m32[lineage.PRODUCER_KEY]["cycle_index"] += 1
    elif mutation == "duplicate_producer_id":
        m32[lineage.PRODUCER_KEY]["proposal_id"] = m31[lineage.PRODUCER_KEY]["proposal_id"]
    elif mutation == "missing_edge":
        receipt["producer_edges"].pop()
    elif mutation == "wrong_edge":
        receipt["producer_edges"][1]["from_id"] = "other"
    elif mutation == "lineage_rejected":
        receipt["status"] = "rejected"
    elif mutation == "m31_new_authority":
        m31["surface_authority"] = True
    elif mutation == "m32_not_authoritative":
        m32["surface_authority"] = False
    decision = _admit(event, tick)
    assert decision["eligible"] is False, (mutation, decision)
    assert decision.get("reason"), mutation


@pytest.mark.parametrize("change", [
    "m33_authoritative", "protected_route", "memory_contract", "profile_contract",
    "other_action_type", "single_rewrite", "sensitive_quote",
])
def test_competing_authority_or_nonmatching_action_does_not_transfer(change):
    event, tick = _issued()
    logic = tick["logic"]
    if change == "m33_authoritative":
        logic["source_anchored_semantic_commit_m33"]["surface_authority"] = True
    elif change == "protected_route":
        tick["route_info"] = {"route": "low_road"}
    elif change == "memory_contract":
        logic["memory_recall_contract"] = {"surface_authority": True}
    elif change == "profile_contract":
        logic["profile_grounding_shadow"] = {"surface_authority": True}
    elif change == "other_action_type":
        event[lineage.EVENT_KEY]["actions"][1]["type"] = "other_action"
    elif change == "single_rewrite":
        event, tick = _issued(BY_ID["N9"])
    elif change == "sensitive_quote":
        event, tick = _issued(BY_ID["N8"])
    decision = _admit(event, tick)
    assert decision["eligible"] is False, (change, decision)


@pytest.mark.parametrize("key,value", [
    ("memory_recall_contract", []), ("profile_grounding_shadow", ""),
    ("semantic_route_m22", []), ("source_anchored_semantic_commit_m33", ""),
])
def test_present_malformed_competing_contract_fails_closed(key, value):
    event, tick = _issued()
    tick["logic"][key] = value
    assert _admit(event, tick)["eligible"] is False


def test_malformed_route_context_fails_closed():
    event, tick = _issued()
    tick["route_info"] = []
    assert _admit(event, tick)["eligible"] is False


def test_direct_user_source_is_separate_from_assistant_third_party_wrong_date_and_retraction():
    seed = BY_ID["N1"]
    direct = past_place.build_mixed_past_place_certificate_p4(BY_ID["N2"], _memory([seed]))
    assert direct["status"] == "source_backed"
    assert direct["admitted_value"] == "白磁の掲示板の横"
    assert direct["source_channel"] == "recent_turns"
    assert direct["claim_boundary"].startswith("User said this")

    wrong_date = past_place.build_mixed_past_place_certificate_p4(BY_ID["N3"], _memory([seed]))
    assert wrong_date["admitted_value"] is None
    assert wrong_date["status"] == "no_admitted_user_source"

    friend = past_place.build_mixed_past_place_certificate_p4(BY_ID["N5"], _memory([BY_ID["N4"]]))
    assert friend["admitted_value"] is None
    assert friend["status"] == "no_admitted_user_source"

    # A model's past answer and a condensed summary are not direct User speech.
    assistant_only = _memory(["まだ決めていない。"])
    assistant_only["recent_turns"][0]["reply"] = seed
    assistant_only["memory_provenance"]["passed_to_leftbrain"][0]["text"] = (
        f"User:まだ決めていない。 -> Uruha:{seed}"
    )
    assistant_cert = past_place.build_mixed_past_place_certificate_p4(
        BY_ID["N2"], assistant_only,
    )
    assert assistant_cert["admitted_value"] is None
    assert assistant_cert["status"] == "no_admitted_user_source"
    summary_only = {
        "memory_provenance": {
            "passed_to_leftbrain": [{
                "source": "episode", "collection_name": "summary",
                "memory_id": "summary-1", "trace_id": "stored:summary:summary-1",
                "episode_record_kind": "summary", "episode_record_kind_origin": "stored_metadata",
                "text": f"Summary: {seed}",
            }],
            "passed_to_leftbrain_trace_ids": ["stored:summary:summary-1"],
        },
    }
    summary_cert = past_place.build_mixed_past_place_certificate_p4(
        BY_ID["N2"], summary_only,
    )
    assert summary_cert["admitted_value"] is None
    assert summary_cert["status"] == "no_admitted_user_source"

    retracted = past_place.build_mixed_past_place_certificate_p4(
        BY_ID["N7"], _memory([seed, BY_ID["N6"]]),
    )
    assert retracted["admitted_value"] is None
    assert retracted["status"] == "source_retracted_or_ambiguous"

    unknown = past_place.build_mixed_past_place_certificate_p4(BY_ID["N0"], _memory([]))
    assert unknown["admitted_value"] is None
    assert unknown["status"] == "no_admitted_user_source"


@pytest.mark.parametrize("phrase,source,accepted", [
    ("集合場所、まだ決まってないんだ", "集合場所はまだ決まっていません", True),
    ("集合場所は決まったよ", "集合場所はまだ決まっていません", False),
    ("集合場所はもう決めたよ", "集合場所はまだ決まっていません", False),
    ("集合場所は明日決めるね", "集合場所はまだ決まっていません", False),
    ("集合場所、まだ決まってないんだよ。明日は必ず決める", "集合場所はまだ決まっていません", False),
    ("集合時間は今日だよ", "集合時間は明日です", False),
    ("集合場所はまだ決まっていません", "集合場所はまだ決まっていません", False),
    ("We're still undecided", "集合場所はまだ決まっていません", False),
])
def test_bounded_phrase_filter_rejects_observable_polarity_time_promise_drift(phrase, source, accepted):
    result, reason = atomic.validate_typed_mixed_rewrite_phrase_p4(phrase, source)
    assert result is accepted, (phrase, reason)
    assert isinstance(reason, str) and reason


@pytest.mark.parametrize("field,value", [
    ("status", "model_error"), ("attempted_calls", 2),
    ("completed_calls", 0), ("model", "other:model"),
    ("temperature", 0.5), ("max_tokens", 160),
    ("timeout_seconds", 12.0), ("completion_tokens", 81),
    ("call_latency_seconds", 6.3), ("model_phrase_sha256", "0" * 64),
])
def test_rewrite_call_contract_or_cost_violation_never_grants_terminal_candidate(field, value):
    phrase = "集合場所、まだ決まってないんだ"
    call = {
        "stage": atomic.rewrite.STAGE, "model": atomic.rewrite.MODEL,
        "attempted_calls": 1, "completed_calls": 1,
        "temperature": 0, "max_tokens": 80, "timeout_seconds": 6.0,
        "prompt_tokens": 12, "completion_tokens": 8,
        "call_latency_seconds": 0.01,
        "status": "bounded_shape_accepted_semantics_unverified",
        "model_phrase_sha256": _sha(phrase),
    }
    assert atomic._valid_rewrite_call(phrase, call) is True
    call[field] = value
    assert atomic._valid_rewrite_call(phrase, call) is False


def _delivery_fixture():
    visible = "「集合場所、まだ決まってないんだ」がいいかな。その日の場所は白磁の掲示板の横って言ってたな。"
    receipt = {
        "status": "candidate_committed",
        "committed_visible_candidate_sha256": _sha(visible),
        "episode_call_reply_sha256": _sha(visible),
        "history_commit_status": "pre_guard_draft_rolled_back_final_visible_committed",
        "terminal_priority_status": "applied_after_legacy_m32",
        "semantics_status": "semantics_unverified",
    }
    result = {
        "reply": visible,
        "logic": {"visible_language_guard": {"final_reply": visible, "final_reply_sha256": _sha(visible)}},
        "runtime_trace": {"blackboard": [
            {"stage": "surface", "label": "utterance", "payload": {"reply": visible}},
        ]},
        "episode_doc": f"Time: 2026-10-20 14:00 | User: {BY_ID['N2']} | Uruha: {visible} | Mood: calm",
    }
    right_brain = SimpleNamespace(history=[
        {"role": "user", "content": "今の会話"},
        {"role": "assistant", "content": visible},
    ])
    return result, receipt, right_brain


def test_delivery_audit_requires_final_guard_graph_episode_and_history_to_agree():
    result, receipt, right_brain = _delivery_fixture()
    audit = atomic.audit_typed_mixed_atomic_delivery_p4(
        result, receipt, right_brain=right_brain,
    )
    assert audit["final_consistent"] is True, audit
    assert audit["status"] == "delivered_structure_semantics_unverified"
    assert audit.get("semantic_equivalence_verified") is not True


def test_history_transaction_removes_all_pre_guard_drafts_and_counter_effects():
    class Right:
        def __init__(self):
            self.history = []
            self.reply_variant_counts = Counter()
            self.intent_variant_counts = Counter()
            self.normalized_reply_counts = Counter()
            self.intent_normalized_counts = Counter()

        def _remember_turn(self, summary, reply, intent):
            self.history.extend([
                {"role": "user", "content": summary, "intent": intent},
                {"role": "assistant", "content": reply, "intent": intent},
            ])
            self.reply_variant_counts[reply] += 1
            self.intent_variant_counts[(intent, reply)] += 1
            self.normalized_reply_counts[reply] += 1
            self.intent_normalized_counts[(intent, reply)] += 1

    right = Right()
    right._remember_turn("前の会話", "前の安全な返事", "chat")
    logic = {"jp_summary": "今の会話", "intent": "chat"}
    tx = {"right_brain": right, "history_snapshot": atomic._history_snapshot(right, logic)}
    right._remember_turn("draft 1", "誤った下書き一", "chat")
    right._remember_turn("draft 2", "誤った下書き二", "chat")
    final = "その日の場所は、会話だけじゃ分からないな。"
    status = atomic._commit_history(tx, final, logic)
    assert status == "pre_guard_draft_rolled_back_final_visible_committed"
    assert tx["history_committed"] is True
    assert [row["content"] for row in right.history if row["role"] == "assistant"] == [
        "前の安全な返事", final,
    ]
    for name in (
        "reply_variant_counts", "intent_variant_counts",
        "normalized_reply_counts", "intent_normalized_counts",
    ):
        counts = getattr(right, name)
        assert all("下書き" not in str(key) for key in counts)
    assert right.reply_variant_counts[final] == 1


@pytest.mark.parametrize("mutation", [
    "reply", "guard", "guard_digest", "graph", "missing_graph", "episode_receipt",
    "missing_episode_receipt", "episode_doc", "history", "missing_history",
    "history_rollback_missing", "candidate_digest",
])
def test_delivery_audit_does_not_mark_partial_or_downstream_mismatch_as_complete(mutation):
    result, receipt, right_brain = _delivery_fixture()
    if mutation == "reply":
        result["reply"] = "別の答え。"
    elif mutation == "guard":
        result["logic"]["visible_language_guard"]["final_reply"] = "別の答え。"
    elif mutation == "guard_digest":
        result["logic"]["visible_language_guard"]["final_reply_sha256"] = "0" * 64
    elif mutation == "graph":
        result["runtime_trace"]["blackboard"][0]["payload"]["reply"] = "別の答え。"
    elif mutation == "missing_graph":
        result["runtime_trace"]["blackboard"] = []
    elif mutation == "episode_receipt":
        receipt["episode_call_reply_sha256"] = "0" * 64
    elif mutation == "missing_episode_receipt":
        del receipt["episode_call_reply_sha256"]
    elif mutation == "episode_doc":
        result["episode_doc"] = f"Time: 2026-10-20 14:00 | User: {BY_ID['N2']} | Uruha: 別の答え。 | Mood: calm"
    elif mutation == "history":
        right_brain.history[-1]["content"] = "別の答え。"
    elif mutation == "missing_history":
        right_brain.history = []
    elif mutation == "history_rollback_missing":
        receipt["history_commit_status"] = "history_transaction_unavailable"
    elif mutation == "candidate_digest":
        receipt["committed_visible_candidate_sha256"] = "0" * 64
    audit = atomic.audit_typed_mixed_atomic_delivery_p4(
        result, receipt, right_brain=right_brain,
    )
    assert audit["final_consistent"] is False, (mutation, audit)
    assert audit["status"] != "delivered_structure_semantics_unverified"


def _transaction_harness(monkeypatch, *, raw=BY_ID["N2"], memory=None, phrase=None):
    """Drive the actual opt-in wrapper with only fake speech, guard and storage."""
    event, tick = _issued(raw)
    event["memory_data"] = _memory([BY_ID["N1"]]) if memory is None else memory
    if phrase is None:
        phrase = "集合場所、まだ決まってないんだ"

    class Right:
        def __init__(self):
            self.history = []
            self.reply_variant_counts = Counter()
            self.intent_variant_counts = Counter()
            self.normalized_reply_counts = Counter()
            self.intent_normalized_counts = Counter()

        def _structured_surface_required(self):
            return False

        def _remember_turn(self, summary, reply, intent):
            self.history.extend([
                {"role": "user", "content": summary, "intent": intent},
                {"role": "assistant", "content": reply, "intent": intent},
            ])
            self.reply_variant_counts[reply] += 1
            self.intent_variant_counts[(intent, reply)] += 1
            self.normalized_reply_counts[reply] += 1
            self.intent_normalized_counts[(intent, reply)] += 1

    right = Right()
    right._remember_turn("前の会話", "前の安全な返事", "chat")
    memory_object = SimpleNamespace()
    brain = SimpleNamespace(
        right_brain=right, memory=memory_object,
        runtime=SimpleNamespace(cycle_index=7, blackboard=[], turn_traces=[{"cycle_index": 7, "blackboard": []}]),
    )
    calls = {"generate": 0, "episode": []}
    monkeypatch.setenv(atomic.FLAG, "1")

    def fake_generate(_brain, source, outside):
        calls["generate"] += 1
        assert source in raw
        assert "言い換えて" in outside
        return phrase, {"stage": atomic.rewrite.STAGE, "model": atomic.rewrite.MODEL,
                        "attempted_calls": 1, "completed_calls": 1,
                        "temperature": 0, "max_tokens": 80, "timeout_seconds": 6.0,
                        "prompt_tokens": 12, "completion_tokens": 8,
                        "call_latency_seconds": 0.01,
                        "status": "bounded_shape_accepted_semantics_unverified",
                        "model_phrase_sha256": _sha(phrase)}

    def fake_guard(_right, reply, logic, user_input="", memory_data=None):
        assert user_input == raw
        logic["visible_language_guard"] = {
            "final_reply": reply, "final_reply_sha256": _sha(reply),
            "final_rejection_reasons": [],
        }
        return reply

    def fake_old_speak(_right, *_args):
        reply = "旧経路の返事。"
        _right._remember_turn("今の会話", reply, "chat")
        return reply

    def fake_save(_memory_object, user_input, reply, mood, _logic):
        calls["episode"].append(reply)
        return f"Time: 2026-10-20 14:00 | User: {user_input} | Uruha: {reply} | Mood: {mood}"

    def fake_emit(_brain, current_event, current_tick):
        logic = current_tick["logic"]
        if atomic._ACTIVE.get() is not None:
            right._remember_turn("下書き一", "誤った下書き一", "chat")
            right._remember_turn("下書き二", "誤った下書き二", "chat")
        spoken = atomic.speak_with_typed_mixed_atomic_delivery_p4(
            right, raw, logic, current_event["memory_data"], {},
        )
        visible = atomic.visible_guard_with_typed_mixed_atomic_delivery_p4(
            right, spoken, logic, user_input=raw, memory_data=current_event["memory_data"],
        )
        doc = atomic.save_episode_with_typed_mixed_atomic_delivery_p4(
            memory_object, raw, visible, "calm", logic,
        )
        return {
            "reply": visible, "logic": logic, "episode_doc": doc,
            "runtime_trace": {
                "cycle_index": 7,
                "blackboard": [{"stage": "surface", "label": "utterance", "payload": {"reply": visible}}],
            },
            "runtime_state": {"recent_turn_traces": [{"cycle_index": 7, "blackboard": []}]},
        }

    monkeypatch.setattr(atomic.rewrite, "_generate", fake_generate)
    monkeypatch.setattr(atomic, "_ORIGINAL_EMIT", fake_emit)
    monkeypatch.setattr(atomic, "_ORIGINAL_GUARD", fake_guard)
    monkeypatch.setattr(atomic, "_ORIGINAL_SPEAK", fake_old_speak)
    monkeypatch.setattr(atomic, "_ORIGINAL_SAVE_EPISODE", fake_save)
    return brain, event, tick, calls


def test_zero_model_full_transaction_delivers_rewrite_and_direct_user_recall(monkeypatch):
    brain, event, tick, calls = _transaction_harness(monkeypatch)
    result = atomic.emit_response_with_typed_mixed_atomic_delivery_p4(brain, event, tick)
    visible = result["reply"]
    receipt = result["logic"][atomic.LABEL]
    assert calls["generate"] == 1
    assert calls["episode"] == [visible]
    assert "まだ決まってないんだ" in visible
    assert "白磁の掲示板の横" in visible
    assert receipt["source_status"] == "source_backed"
    assert receipt["source_trace_id"]
    assert receipt["terminal_priority_status"] == "applied_after_legacy_m32"
    assert receipt["status"] == "delivered_structure_semantics_unverified"
    assert receipt["final_consistent"] is True
    assert receipt["semantic_equivalence_certified"] is False
    assert receipt["db_readback_verified"] is False
    assert tick["logic"][lineage.LABEL]["authority_transfer_permitted"] is False
    assert tick["logic"]["semantic_commit_repair_m32"]["surface_authority"] is True
    assert tick["logic"]["semantic_commit_repair_m32"]["terminal_transaction_shadowed_surface_p4"] == atomic.LABEL
    assert [row["content"] for row in brain.right_brain.history if row["role"] == "assistant"] == [
        "前の安全な返事", visible,
    ]
    assert all("下書き" not in str(key) for key in brain.right_brain.reply_variant_counts)
    assert result["runtime_trace"][atomic.LABEL] == receipt
    assert brain.runtime.turn_traces[-1] == result["runtime_trace"]
    assert result["runtime_state"]["recent_turn_traces"][-1] == result["runtime_trace"]
    assert next(row["payload"] for row in result["runtime_trace"]["blackboard"]
                if row["label"] == atomic.LABEL) == receipt


def test_zero_model_unknown_source_keeps_rewrite_but_does_not_invent_place(monkeypatch):
    brain, event, tick, calls = _transaction_harness(
        monkeypatch, raw=BY_ID["N0"], memory=_memory([]), phrase="集合場所、まだ確認中なんだ",
    )
    result = atomic.emit_response_with_typed_mixed_atomic_delivery_p4(brain, event, tick)
    receipt = result["logic"][atomic.LABEL]
    assert calls["generate"] == 1
    assert receipt["source_status"] == "no_admitted_user_source"
    assert receipt["status"] == "delivered_structure_semantics_unverified"
    assert "まだ確認中なんだ" in result["reply"]
    assert "分からない" in result["reply"]
    assert "白磁の掲示板の横" not in result["reply"]


def test_zero_model_rejected_candidate_and_protected_route_retain_old_reply(monkeypatch):
    brain, event, tick, calls = _transaction_harness(
        monkeypatch, phrase="集合場所は決まったよ",
    )
    rejected = atomic.emit_response_with_typed_mixed_atomic_delivery_p4(brain, event, tick)
    assert calls["generate"] == 1
    assert rejected["reply"] == "旧経路の返事。"
    assert rejected["logic"][atomic.LABEL]["status"] == "candidate_rejected_original_route_kept"
    assert rejected["logic"][atomic.LABEL]["final_consistent"] is False
    assert rejected["logic"]["semantic_commit_repair_m32"]["surface_authority"] is True

    protected_brain, protected_event, protected_tick, protected_calls = _transaction_harness(monkeypatch)
    protected_tick["route_info"] = {"route": "low_road"}
    protected = atomic.emit_response_with_typed_mixed_atomic_delivery_p4(
        protected_brain, protected_event, protected_tick,
    )
    assert protected_calls["generate"] == 0
    assert protected["reply"] == "旧経路の返事。"
    assert atomic.LABEL not in protected["logic"]


def test_source_lost_between_prepare_and_guard_must_not_leak_stale_place(monkeypatch):
    brain, event, tick, _ = _transaction_harness(monkeypatch)

    def source_disappears_during_generation(_brain, _source, _outside):
        event["memory_data"] = _memory([])
        phrase = "集合場所、まだ決まってないんだ"
        return phrase, {
            "stage": atomic.rewrite.STAGE, "model": atomic.rewrite.MODEL,
            "attempted_calls": 1, "completed_calls": 1,
            "temperature": 0, "max_tokens": 80, "timeout_seconds": 6.0,
            "prompt_tokens": 12, "completion_tokens": 8, "call_latency_seconds": 0.01,
            "status": "bounded_shape_accepted_semantics_unverified",
            "model_phrase_sha256": _sha(phrase),
        }

    monkeypatch.setattr(atomic.rewrite, "_generate", source_disappears_during_generation)
    result = atomic.emit_response_with_typed_mixed_atomic_delivery_p4(brain, event, tick)
    receipt = result["logic"][atomic.LABEL]
    assert receipt["terminal_priority_status"] == "rejected_at_final_guard"
    assert receipt["final_consistent"] is False
    assert "白磁の掲示板の横" not in result["reply"]
    assert result["reply"] != "「集合場所、まだ決まってないんだ」って感じかな。2026年11月18日の集合場所は白磁の掲示板の横にしたって言ってたな。"


def test_guard_normalization_cannot_publish_uncommitted_variant(monkeypatch):
    brain, event, tick, calls = _transaction_harness(monkeypatch)

    def normalizing_guard(_right, reply, logic, user_input="", memory_data=None):
        altered = reply.replace("って感じかな。", "がいいかな。")
        logic["visible_language_guard"] = {
            "final_reply": altered, "final_reply_sha256": _sha(altered),
            "final_rejection_reasons": [],
        }
        return altered

    monkeypatch.setattr(atomic, "_ORIGINAL_GUARD", normalizing_guard)
    result = atomic.emit_response_with_typed_mixed_atomic_delivery_p4(brain, event, tick)
    receipt = result["logic"][atomic.LABEL]
    assert calls["generate"] == 1
    assert receipt["terminal_priority_status"] == "rejected_at_final_guard"
    assert receipt["final_consistent"] is False
    assert "白磁の掲示板の横" not in result["reply"]
    assert calls["episode"] == [result["reply"]]
    assert [row["content"] for row in brain.right_brain.history if row["role"] == "assistant"] == [
        "前の安全な返事", result["reply"],
    ]
    assert all("下書き" not in str(key) for key in brain.right_brain.reply_variant_counts)
