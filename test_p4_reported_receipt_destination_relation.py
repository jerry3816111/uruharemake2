"""Frozen source-disjoint product contracts for the opt-in relation adapter."""

from collections import Counter
import hashlib
import json
from pathlib import Path
import re

import pytest
import uruha_reported_receipt_destination_relation_p4 as relation
import uruha_source_bound_proposition_preservation_p4 as p4z

from uruha_reported_receipt_destination_relation_p4 import (
    LABEL,
    _guard_with_reported_receipt_destination_p4,
    _emit_with_reported_receipt_destination_p4,
    _remember_profile_with_reported_receipt_destination_p4,
    _post_check_with_reported_receipt_destination_p4,
    append_reported_receipt_destination_node_p4,
    extract_reported_receipt_destination_p4,
    inspect_reported_receipt_destination_p4,
    preserve_reported_receipt_destination_p4,
)


ROOT = Path(__file__).resolve().parent
DATA = json.loads(
    (ROOT / "datasets/p4_reported_receipt_destination_probe_2026-10-23.json").read_text(encoding="utf-8")
)


def _sha(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@pytest.mark.parametrize("case", DATA["contract_cases"], ids=lambda row: row["id"])
def test_frozen_source_and_candidate_contract(case):
    visible, trace = preserve_reported_receipt_destination_p4(case["source"], case["candidate"])
    assert trace["status"] == case["expected_status"]
    if "expected_reply_unchanged" in case:
        assert (visible == case["candidate"]) is case["expected_reply_unchanged"]
    if case.get("expected_relation"):
        assert case["expected_relation"] in visible
    if case.get("forbidden_relation"):
        assert case["forbidden_relation"] not in visible
    if trace["status"] == "source_pattern_unavailable":
        assert trace["action"] == "abstain_unchanged"
        assert extract_reported_receipt_destination_p4(case["source"]) is None
    else:
        source = extract_reported_receipt_destination_p4(case["source"])
        assert source["location_role"] == "receiving_destination_selected"
        assert source["temporal_scope"] == "unresolved_source_ambiguity"
        assert inspect_reported_receipt_destination_p4(source, visible) == []
        serialized = json.dumps(trace, ensure_ascii=False)
        assert case["source"] not in serialized
        assert visible not in serialized
        assert trace["model_call_added"] is False
        assert trace["fact_write_count"] == 0
        assert trace["profile_write_count"] == 0


def test_two_new_positive_sources_have_independent_typed_slots():
    first, second = (extract_reported_receipt_destination_p4(case["source"]) for case in DATA["cases"] if case["kind"] == "reported_receipt_destination_positive")
    assert first["actor"] == "同僚"
    assert first["object"] == "銅の望遠鏡"
    assert first["destination"] == "灰色の温室の北廊下"
    assert second["actor"] == "妹"
    assert second["object"] == "木製のオルゴール"
    assert second["destination"] == "青い図書館の東階段"
    assert first["rule_id"] == second["rule_id"]


class _SpeechHistory:
    def __init__(self, before, intent):
        self.history = [{"role": "user", "content": "observed source", "intent": intent}, {"role": "assistant", "content": before, "intent": intent}]
        self.reply_variant_counts = Counter({before: 1})
        self.intent_variant_counts = Counter({(intent, before): 1})
        self.normalized_reply_counts = Counter({before: 1})
        self.intent_normalized_counts = Counter({(intent, before): 1})

    def _normalize_reply_key(self, reply):
        return reply

    def _bind_forbidden_projection_shadow_visible_reply(self, logic, visible):
        pass


def _guard(_brain, candidate, logic, *, user_input, memory_data):
    logic["visible_language_guard"] = {
        "final_reply": candidate,
        "final_reply_sha256": _sha(candidate),
    }
    return candidate


def test_guarded_visible_surface_and_current_history_are_exactly_bound():
    row = DATA["contract_cases"][0]
    before = row["candidate"]
    actor = _SpeechHistory(before, "deterministic_semantic_commit_m32")
    logic = {"intent": "deterministic_semantic_commit_m32"}
    calls = []

    def counted_guard(brain, candidate, state, *, user_input, memory_data):
        calls.append(candidate)
        return _guard(brain, candidate, state, user_input=user_input, memory_data=memory_data)

    final = _guard_with_reported_receipt_destination_p4(
        actor, before, logic, row["source"], {}, counted_guard,
    )
    assert len(calls) == 1
    assert final == calls[0]
    assert final == logic["visible_language_guard"]["final_reply"]
    assert final == actor.history[-1]["content"]
    assert logic[LABEL]["after_digest"] == _sha(final)
    assert logic[LABEL]["history_status"] == "current_assistant_synced"
    assert actor.reply_variant_counts[before] == 0
    assert actor.reply_variant_counts[final] == 1
    assert actor.intent_variant_counts[(logic["intent"], before)] == 0
    assert actor.intent_variant_counts[(logic["intent"], final)] == 1


def test_changed_guard_output_with_wrong_relation_is_terminal():
    row = DATA["contract_cases"][0]
    before = row["candidate"]
    actor = _SpeechHistory(before, "deterministic_semantic_commit_m32")
    logic = {"intent": "deterministic_semantic_commit_m32"}

    def wrong_guard(brain, candidate, state, *, user_input, memory_data):
        wrong = before
        return _guard(brain, wrong, state, user_input=user_input, memory_data=memory_data)

    with pytest.raises(RuntimeError, match="final guard mismatch"):
        _guard_with_reported_receipt_destination_p4(actor, before, logic, row["source"], {}, wrong_guard)
    assert LABEL not in logic
    assert actor.history[-1]["content"] == before


def test_stale_guard_digest_or_current_history_is_terminal():
    row = DATA["contract_cases"][0]
    before = row["candidate"]
    actor = _SpeechHistory(before, "deterministic_semantic_commit_m32")
    logic = {"intent": "deterministic_semantic_commit_m32"}

    def stale_digest(brain, candidate, state, *, user_input, memory_data):
        _guard(brain, candidate, state, user_input=user_input, memory_data=memory_data)
        state["visible_language_guard"]["final_reply_sha256"] = "0" * 64
        return candidate

    with pytest.raises(RuntimeError, match="final guard mismatch"):
        _guard_with_reported_receipt_destination_p4(actor, before, logic, row["source"], {}, stale_digest)
    assert LABEL not in logic

    actor.history[-1]["content"] = "stale assistant"
    with pytest.raises(RuntimeError, match="current history mismatch"):
        _guard_with_reported_receipt_destination_p4(actor, before, logic, row["source"], {}, _guard)
    assert LABEL not in logic


def test_render_failure_cannot_publish_an_unverified_relation(monkeypatch):
    row = DATA["contract_cases"][0]
    monkeypatch.setattr(relation, "_render", lambda contract: "間違った場所で決めたらしいね。")
    with pytest.raises(RuntimeError, match="repair failed closed"):
        preserve_reported_receipt_destination_p4(row["source"], row["candidate"])


def test_protected_route_preserves_prior_authority_without_new_repair():
    row = DATA["contract_cases"][0]
    before = row["candidate"]
    actor = _SpeechHistory(before, "crisis_support")
    logic = {"intent": "crisis_support", "scene": "support"}
    final = _guard_with_reported_receipt_destination_p4(actor, before, logic, row["source"], {}, _guard)
    assert final == before
    assert logic[LABEL]["status"] == "protected_route_not_repaired"
    assert logic[LABEL]["changed"] is False
    assert logic[LABEL]["before_digest"] == logic[LABEL]["after_digest"] == _sha(before)


def test_unrelated_old_p4_z_families_are_not_new_relation():
    for source in (
        "後輩は紫のマグカップをなくしたらしい。",
        "「北側窗口十點停止受理」只是引用，請不要當成真的。",
    ):
        assert extract_reported_receipt_destination_p4(source) is None
    visible, trace = p4z.preserve_source_bound_proposition_p4(
        "後輩は紫のマグカップをなくしたらしい。", "後輩が紫のマグカップをなくしたらしいって話ね。",
    )
    assert trace["status"] == "accepted_verified"
    assert "location_role" not in trace
    assert "temporal_scope" not in trace


def test_downstream_surface_mutation_fails_before_episode():
    row = DATA["contract_cases"][0]
    actor = _SpeechHistory(row["candidate"], "deterministic_semantic_commit_m32")
    logic = {"intent": "deterministic_semantic_commit_m32"}
    final = _guard_with_reported_receipt_destination_p4(
        actor, row["candidate"], logic, row["source"], {}, _guard,
    )
    class Brain:
        right_brain = actor
    with pytest.raises(RuntimeError, match="pre-episode mismatch"):
        _post_check_with_reported_receipt_destination_p4(
            Brain(), logic, row["source"], final.replace("に決め", "で決め"), {}, lambda *args: None,
        )


def test_missing_relation_trace_is_rejected_before_prior_post_check():
    row = DATA["contract_cases"][0]
    actor = _SpeechHistory(row["candidate"], "deterministic_semantic_commit_m32")
    class Brain:
        right_brain = actor
    calls = []
    def prior(*args):
        calls.append("prior")
    with pytest.raises(RuntimeError, match="verification missing before episode"):
        _post_check_with_reported_receipt_destination_p4(
            Brain(), {"intent": "deterministic_semantic_commit_m32"},
            row["source"], row["candidate"], {}, prior,
        )
    assert calls == []


def test_graph_node_is_one_real_blackboard_item_before_utterance():
    row = DATA["contract_cases"][0]
    final, trace = preserve_reported_receipt_destination_p4(row["source"], row["candidate"])
    result = {"reply": final, "logic": {LABEL: trace}, "runtime_trace": {"blackboard": [
        {"stage": "surface", "label": "utterance", "payload": {"reply": final}},
    ]}}
    append_reported_receipt_destination_node_p4(result)
    append_reported_receipt_destination_node_p4(result)
    rows = result["runtime_trace"]["blackboard"]
    assert [row["label"] for row in rows] == [LABEL, "utterance"]
    assert result["runtime_trace"][LABEL] == rows[0]["payload"] == trace

    import uruha_memory_observatory as graph
    rendered = graph.collect_cognitive_graph(result)
    nodes = [node for node in rendered["nodes"] if node["label"] == LABEL]
    assert len(nodes) == 1
    assert "接收地點角色" in nodes[0]["signal"]
    assert "unresolved_source_ambiguity" in nodes[0]["detail"]
    assert {("runtime-0", "runtime-1", "is-main")} <= {
        (edge["source"], edge["target"], edge["class"]) for edge in rendered["edges"]
    }


def test_new_opt_in_entry_keeps_frozen_d_installer_order():
    old = (ROOT / "uruha_web_ui_product_p4_current_decision_ack.py").read_text(encoding="utf-8")
    new = (ROOT / "uruha_web_ui_product_p4_reported_receipt_destination.py").read_text(encoding="utf-8")
    installer = re.compile(r"^\s+(?:.*\.)?(install_[a-z_0-9]+_p4)\(\)$", re.M)
    assert installer.findall(new) == installer.findall(old) + ["install_reported_receipt_destination_relation_p4"]
    assert "import uruha_web_ui_product_p4_current_decision_ack as _prior" in new


def test_selected_d_authority_is_not_replaced():
    row = DATA["contract_cases"][0]
    before = row["candidate"]
    actor = _SpeechHistory(before, "deterministic_semantic_commit_m32")
    logic = {
        "intent": "deterministic_semantic_commit_m32",
        relation.p4d.LABEL: {
            "schema": relation.p4d.SCHEMA,
            "selected_status": "source_authorized_plan_selected",
        },
    }
    final = _guard_with_reported_receipt_destination_p4(actor, before, logic, row["source"], {}, _guard)
    assert final == before
    assert logic[LABEL]["status"] == "protected_route_not_repaired"
    assert logic[LABEL]["changed"] is False


def test_eligible_emit_error_rolls_back_short_history_without_episode():
    row = DATA["contract_cases"][0]
    actor = _SpeechHistory(row["candidate"], "deterministic_semantic_commit_m32")
    before = list(actor.history)
    counts = actor.reply_variant_counts.copy()
    class Brain:
        right_brain = actor
    logic = {"intent": "deterministic_semantic_commit_m32"}
    def failed_emit(_brain, _event, _tick):
        actor.history.append({"role": "assistant", "content": "bad", "intent": logic["intent"]})
        actor.reply_variant_counts["bad"] += 1
        raise RuntimeError("pre-episode failure")
    with pytest.raises(RuntimeError, match="pre-episode failure"):
        _emit_with_reported_receipt_destination_p4(
            Brain(), {"user_input": row["source"]}, {"logic": logic}, failed_emit,
        )
    assert actor.history == before
    assert actor.reply_variant_counts == counts


def test_third_party_source_cannot_become_user_profile_fact():
    source = "研究員は2096年3月14日に銅の望遠鏡を受け取る場所を猫が好きな館に決めたらしい。"
    assert extract_reported_receipt_destination_p4(source) is not None
    logic = {LABEL: {"pre_episode_status": "verified_before_episode_write"}}
    memory = object()
    tx = {"memory": memory, "source": source, "logic": logic, "profile_suppressed": False}
    token = relation._ACTIVE_EMIT.set(tx)
    calls = []
    try:
        assert _remember_profile_with_reported_receipt_destination_p4(
            memory, source, lambda *args: calls.append(args),
        ) is None
    finally:
        relation._ACTIVE_EMIT.reset(token)
    assert calls == []
    assert tx["profile_suppressed"] is True
    assert logic[LABEL]["profile_write_status"] == "suppressed_for_third_party_report"


def test_profile_suppression_requires_pre_episode_certificate():
    row = DATA["contract_cases"][0]
    memory = object()
    tx = {"memory": memory, "source": row["source"], "logic": {}, "profile_suppressed": False}
    token = relation._ACTIVE_EMIT.set(tx)
    try:
        with pytest.raises(RuntimeError, match="profile suppression unverified"):
            _remember_profile_with_reported_receipt_destination_p4(
                memory, row["source"], lambda *args: None,
            )
    finally:
        relation._ACTIVE_EMIT.reset(token)
    assert tx["profile_suppressed"] is False
