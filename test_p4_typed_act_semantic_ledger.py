"""Zero-model checks for the new bounded two-act semantic ledger.

Developer-authored T cases test a contract and isolated transaction. They are
not fresh model, Safari, temporal holdout or general semantic-equivalence proof.
"""

from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

import uruha_mixed_past_place_source_authority_p4 as past_place
import uruha_mixed_act_lineage_p4 as lineage
import uruha_current_turn_source_role_p4 as source_role
import uruha_typed_act_semantic_ledger_p4 as ledger
import uruha_typed_mixed_atomic_delivery_p4 as atomic
from uruha_memory_observatory import (
    M24_GRAPH_DETAIL_BUDGET_BYTES, M24_NODE_DETAIL_BUDGET_BYTES,
    collect_cognitive_graph, render_memory_observatory,
)
from test_p4_typed_mixed_atomic_delivery import _issued, _memory, _transaction_harness


DATA = json.loads((Path(__file__).parent / "datasets" /
                   "p4_typed_act_semantic_ledger_probe_2026-10-21.json").read_text(encoding="utf-8"))
BY_ID = {row["id"]: row for row in DATA["cases"]}
Z_BY_ID = {row["id"]: row for row in DATA["zero_model_controls"]}


def _sha(value):
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()


def _prepared(raw, user_turns=()):
    event, tick = _issued(raw=raw)
    event["memory_data"] = _memory(user_turns)
    admission = atomic.verify_typed_mixed_atomic_admission_p4(event, tick)
    source = past_place.build_mixed_past_place_certificate_p4(raw, event["memory_data"])
    style = atomic._bounded_requested_style(admission.get("source_role") or {})
    return event, tick, admission, source, style


@pytest.mark.parametrize("case_id,prior,status", [
    ("T0", (), "no_admitted_user_source"),
    ("T2", ("T1",), "source_backed"),
    ("T4", ("T1", "T3"), "no_admitted_user_source"),
    ("T6", ("T1", "T3", "T5"), "source_retracted_or_ambiguous"),
])
def test_frozen_positive_has_two_bound_actions_and_no_model_call(case_id, prior, status):
    row = BY_ID[case_id]
    event, _, admission, source, style = _prepared(
        row["input"], [BY_ID[key]["input"] for key in prior],
    )
    assert admission["eligible"] is True
    result = ledger.build_typed_act_semantic_ledger_p4(event, admission, source, style)
    assert result["eligible"] is True, result
    receipt = result["receipt"]
    assert receipt["schema"] == ledger.SCHEMA
    assert receipt["status"] == "bounded_slot_fidelity_verified"
    assert receipt["source_status"] == status
    assert [act["type"] for act in receipt["acts"]] == [
        "quoted_rewrite", "past_user_place_recall",
    ]
    assert [act["action_id"] for act in receipt["acts"]] == receipt["action_ids"]
    assert all(act["event_id"] == receipt["event_id"] for act in receipt["acts"])
    assert all(act["raw_input_sha256"] == receipt["raw_input_sha256"] for act in receipt["acts"])
    assert all(act["status"] == "bounded_slot_fidelity_verified" for act in receipt["acts"])
    assert all(act["semantic_equivalence_certified"] is False for act in receipt["acts"])
    assert receipt["acts"][0]["obligation_slot_digests"]["quote_date_sha256"] == _sha(row["quote_date"])
    assert receipt["acts"][0]["obligation_slot_digests"]["quote_state_sha256"] == _sha(row["quote_state"])
    assert receipt["acts"][1]["obligation_slot_digests"]["recall_date_sha256"] == _sha(row["recall_date"])
    assert receipt["acts"][0]["realized_surface_sha256"] == _sha(result["rewrite_phrase"])
    assert receipt["acts"][1]["realized_surface_sha256"] == _sha(result["recall_phrase"])
    assert receipt["bounded_slot_fidelity_verified"] is True
    assert receipt["semantic_equivalence_certified"] is False
    assert receipt["model_call"]["attempted_calls"] == 0
    assert receipt["model_call"]["completion_tokens"] == 0
    assert receipt["quote_date_sha256"] == _sha(row["quote_date"])
    assert receipt["quote_state_sha256"] == _sha(row["quote_state"])
    assert receipt["recall_date_sha256"] == _sha(row["recall_date"])
    assert receipt["dates_distinct"] is True
    assert row["quote_date"] in result["rewrite_phrase"]
    assert row["quote_state"] in result["rewrite_phrase"]
    assert result["rewrite_phrase"].endswith("なんだ")
    assert "です" not in result["rewrite_phrase"]
    assert row["recall_date"] in result["recall_phrase"]
    assert row["quote_date"] not in result["recall_phrase"]
    assert receipt["committed_visible_candidate_sha256"] == _sha(result["candidate"])
    assert receipt["rewrite_phrase_sha256"] == _sha(result["rewrite_phrase"])
    assert receipt["recall_phrase_sha256"] == _sha(result["recall_phrase"])
    assert row["input"] not in json.dumps(receipt, ensure_ascii=False)
    if status == "source_backed":
        assert "青い時計塔の裏" in result["recall_phrase"]
    else:
        assert "青い時計塔の裏" not in result["recall_phrase"]
        assert "白い連絡通路の入口" not in result["recall_phrase"]


@pytest.mark.parametrize("case_id", ["T7", "T8", "Z0", "Z1", "Z2", "Z3"])
def test_unsupported_or_protected_input_abstains_without_candidate(case_id):
    row = BY_ID.get(case_id) or Z_BY_ID[case_id]
    event, _, admission, source, style = _prepared(row["input"])
    result = ledger.build_typed_act_semantic_ledger_p4(event, admission, source, style)
    assert result["eligible"] is False
    assert "candidate" not in result
    assert "receipt" not in result


@pytest.mark.parametrize("fault", [
    "raw", "event_id", "cycle", "action_id", "quote_sha", "source_binding", "source_date",
])
def test_changed_event_or_source_cannot_reuse_prepared_ledger(fault):
    raw = BY_ID["T2"]["input"]
    event, _, admission, source, style = _prepared(raw, [BY_ID["T1"]["input"]])
    assert ledger.build_typed_act_semantic_ledger_p4(event, admission, source, style)["eligible"]
    event, admission, source = deepcopy(event), deepcopy(admission), deepcopy(source)
    if fault == "raw":
        event["user_input"] = raw.replace("2028年4月8日", "2028年4月9日")
    elif fault == "event_id":
        admission["event_id"] = "0" * 32
    elif fault == "cycle":
        admission["cycle_index"] += 1
    elif fault == "action_id":
        admission["actions"][0]["action_id"] = "other"
    elif fault == "quote_sha":
        admission["source_role"]["quote_raw_sha256"] = "0" * 64
    elif fault == "source_binding":
        source["binding_sha256"] = "0" * 64
    elif fault == "source_date":
        source["date_anchor"] = "2028年4月6日"
    result = ledger.build_typed_act_semantic_ledger_p4(event, admission, source, style)
    assert result["eligible"] is False, (fault, result)


@pytest.mark.parametrize("case_id,prior", [
    ("T0", ()),
    ("T2", ("T1",)),
])
def test_zero_model_terminal_delivers_both_bound_actions_without_free_rewrite(monkeypatch, case_id, prior):
    raw = BY_ID[case_id]["input"]
    brain, event, tick, calls = _transaction_harness(
        monkeypatch, raw=raw, memory=_memory([BY_ID[key]["input"] for key in prior]),
    )
    monkeypatch.setenv(ledger.FLAG, "1")
    result = atomic.emit_response_with_typed_mixed_atomic_delivery_p4(brain, event, tick)
    receipt = result["logic"][atomic.LABEL]
    assert calls["generate"] == 0
    assert calls["episode"] == [result["reply"]]
    assert receipt["status"] == "delivered_structure_semantics_unverified"
    assert receipt["terminal_priority_status"] == "applied_after_legacy_m32"
    assert receipt["final_consistent"] is True
    assert receipt["semantic_equivalence_certified"] is False
    assert receipt["rewrite_action_surface_status"] == "bounded_slot_visible_semantics_unverified"
    assert receipt["semantic_ledger"]["bounded_slot_fidelity_verified"] is True
    assert receipt["model_call"]["attempted_calls"] == 0
    assert BY_ID[case_id]["quote_date"] in result["reply"]
    assert BY_ID[case_id]["recall_date"] in result["reply"]
    assert result["runtime_trace"][atomic.LABEL] == receipt
    if case_id == "T2":
        assert "青い時計塔の裏" in result["reply"]


def test_unsupported_quote_stays_on_old_route_without_new_model_call(monkeypatch):
    brain, event, tick, calls = _transaction_harness(
        monkeypatch, raw=BY_ID["T7"]["input"], memory=_memory([BY_ID["T1"]["input"]]),
    )
    monkeypatch.setenv(ledger.FLAG, "1")
    result = atomic.emit_response_with_typed_mixed_atomic_delivery_p4(brain, event, tick)
    assert calls["generate"] == 0
    assert result["reply"] == "旧経路の返事。"
    assert result["logic"][atomic.LABEL]["status"] == "candidate_rejected_original_route_kept"
    assert result["logic"][atomic.LABEL]["semantic_ledger_status"]


def test_lost_user_source_before_final_guard_cannot_publish_old_place(monkeypatch):
    brain, event, tick, calls = _transaction_harness(
        monkeypatch, raw=BY_ID["T2"]["input"], memory=_memory([BY_ID["T1"]["input"]]),
    )
    monkeypatch.setenv(ledger.FLAG, "1")
    old_emit = atomic._ORIGINAL_EMIT

    def source_disappears(brain_obj, current_event, current_tick):
        current_event["memory_data"] = _memory([])
        return old_emit(brain_obj, current_event, current_tick)

    monkeypatch.setattr(atomic, "_ORIGINAL_EMIT", source_disappears)
    result = atomic.emit_response_with_typed_mixed_atomic_delivery_p4(brain, event, tick)
    assert calls["generate"] == 0
    assert result["logic"][atomic.LABEL]["terminal_priority_status"] == "rejected_at_final_guard"
    assert result["logic"][atomic.LABEL]["final_consistent"] is False
    assert "青い時計塔の裏" not in result["reply"]


def _delivered_graph_result(monkeypatch, case_id):
    raw = BY_ID[case_id]["input"]
    prior = [BY_ID["T1"]["input"]] if case_id == "T2" else []
    brain, event, tick, calls = _transaction_harness(
        monkeypatch, raw=raw, memory=_memory(prior),
    )
    monkeypatch.setenv(ledger.FLAG, "1")
    result = atomic.emit_response_with_typed_mixed_atomic_delivery_p4(brain, event, tick)
    assert calls["generate"] == 0
    assert result["logic"][atomic.LABEL]["final_consistent"] is True
    trace = result["runtime_trace"]
    logic = result["logic"]
    trace[lineage.LABEL] = deepcopy(logic[lineage.LABEL])
    trace["semantic_authorization_m31"] = deepcopy(logic["semantic_authorization_m31"])
    trace["semantic_commit_repair_m32"] = deepcopy(logic["semantic_commit_repair_m32"])
    trace["source_anchored_semantic_commit_m33"] = deepcopy(logic["source_anchored_semantic_commit_m33"])
    trace["current_turn_source_role_p4"] = source_role.public_source_role_certificate_p4(
        source_role.classify_current_turn_source_role_p4(raw, cycle_index=7)
    )
    result["user_text"] = raw
    result["memory_data"] = event["memory_data"]
    return result


@pytest.mark.parametrize("case_id,expected_source", [
    ("T0", "no_admitted_user_source"),
    ("T2", "source_backed"),
])
def test_native_graph_shows_four_receipt_verified_nodes_and_six_arrows(monkeypatch, case_id, expected_source):
    result = _delivered_graph_result(monkeypatch, case_id)
    graph = collect_cognitive_graph(result)
    html = render_memory_observatory(result)
    nodes = [node for node in graph["nodes"] if node.get("atomic_delivery_projection")]
    edges = [edge for edge in graph["edges"] if edge["class"] == "is-atomic-delivery"]
    assert {node["id"] for node in nodes} == {
        "typed-atomic-ledger", "typed-atomic-rewrite", "typed-atomic-recall",
        "typed-atomic-terminal",
    }
    assert len(edges) == 6
    assert {tuple((edge["source"], edge["target"])) for edge in edges} == {
        ("producer-projection-m32", "typed-atomic-ledger"),
        ("typed-atomic-ledger", "typed-atomic-rewrite"),
        ("typed-atomic-ledger", "typed-atomic-recall"),
        ("typed-atomic-rewrite", "typed-atomic-terminal"),
        ("typed-atomic-recall", "typed-atomic-terminal"),
        ("typed-atomic-terminal", "turn-output"),
    }
    summary = graph["typed_mixed_atomic_projection_p4"]
    assert summary["source_status"] == expected_source
    assert summary["bounded_slot_fidelity_verified"] is True
    assert summary["semantic_equivalence_certified"] is False
    assert summary["model_calls_added"] == 0
    assert "BOUNDED SLOT LEDGER" in html
    assert "general meaning and DB readback unverified" in html
    assert html.count('<path class="brain-edge is-atomic-delivery"') == 6
    assert all(result["user_text"] not in node["detail"] for node in nodes)
    assert all("青い時計塔の裏" not in node["detail"] for node in nodes)
    budget = graph["payload_budget_m24"]
    assert budget["budget_met"] is True
    assert budget["rendered_detail_bytes"] <= M24_GRAPH_DETAIL_BUDGET_BYTES
    assert budget["largest_node_detail_bytes"] <= M24_NODE_DETAIL_BUDGET_BYTES


@pytest.mark.parametrize("field,bad", [
    ("quote_date_sha256", "0" * 64),
    ("quote_state_sha256", "0" * 64),
    ("recall_date_sha256", "0" * 64),
    ("source_binding_sha256", "0" * 64),
    ("quote_role", "user_fact"),
    ("recall_actor", "assistant"),
])
def test_native_graph_rejects_tampered_semantic_ledger_even_if_receipt_copies_match(monkeypatch, field, bad):
    result = _delivered_graph_result(monkeypatch, "T0")
    trace = result["runtime_trace"]
    terminal = next(row["payload"] for row in trace["blackboard"]
                    if row.get("label") == atomic.LABEL)
    for receipt in (result["logic"][atomic.LABEL], trace[atomic.LABEL], terminal):
        receipt["semantic_ledger"][field] = bad
    graph = collect_cognitive_graph(result)
    assert graph["typed_mixed_atomic_projection_p4"] is None
    assert not [node for node in graph["nodes"] if node.get("atomic_delivery_projection")]
    assert not [edge for edge in graph["edges"] if edge["class"] == "is-atomic-delivery"]


def test_native_graph_rejects_forged_visible_state_even_with_consistent_digests(monkeypatch):
    result = _delivered_graph_result(monkeypatch, "T0")
    old = result["reply"]
    wrong = old.replace("確認中", "決めてない")
    assert wrong != old
    result["reply"] = wrong
    result["episode_doc"] = result["episode_doc"].replace(old, wrong)
    result["logic"]["visible_language_guard"].update({
        "final_reply": wrong, "final_reply_sha256": _sha(wrong),
    })
    trace = result["runtime_trace"]
    utterance = next(row["payload"] for row in trace["blackboard"] if row.get("label") == "utterance")
    utterance["reply"] = wrong
    changed_rewrite = "2028年4月6日の集合場所はまだ決めてないなんだ"
    terminal = next(row["payload"] for row in trace["blackboard"]
                    if row.get("label") == atomic.LABEL)
    for receipt in (result["logic"][atomic.LABEL], trace[atomic.LABEL], terminal):
        for field in (
            "committed_visible_candidate_sha256", "final_visible_sha256",
            "final_guard_reply_sha256", "episode_call_reply_sha256",
        ):
            receipt[field] = _sha(wrong)
        receipt["rewrite_phrase_sha256"] = _sha(changed_rewrite)
        receipt["semantic_ledger"]["rewrite_phrase_sha256"] = _sha(changed_rewrite)
        receipt["semantic_ledger"]["candidate_sha256"] = _sha(wrong)
        receipt["semantic_ledger"]["committed_visible_candidate_sha256"] = _sha(wrong)
    graph = collect_cognitive_graph(result)
    assert graph["typed_mixed_atomic_projection_p4"] is None
    assert not [node for node in graph["nodes"] if node.get("atomic_delivery_projection")]

@pytest.mark.parametrize("case_id,forged_place", [
    ("T0", "架空の広場"),
    ("T2", "作り話の駅前"),
])
def test_native_graph_rejects_forged_recall_even_when_visible_hashes_agree(
    monkeypatch, case_id, forged_place,
):
    result = _delivered_graph_result(monkeypatch, case_id)
    raw = BY_ID[case_id]["input"]
    source = past_place.build_mixed_past_place_certificate_p4(raw, result["memory_data"])
    old_recall = source["authorized_reply"] if source["status"] == "source_backed" else (
        f"{BY_ID[case_id]['recall_date']}の集合場所は、今ある会話だけじゃ分からないな。"
    )
    forged_recall = (
        f"{BY_ID[case_id]['recall_date']}の集合場所は{forged_place}にしたって言ってたな。"
    )
    old = result["reply"]
    assert old.endswith(old_recall)
    wrong = old[:-len(old_recall)] + forged_recall
    result["reply"] = wrong
    result["episode_doc"] = result["episode_doc"].replace(old, wrong)
    result["logic"]["visible_language_guard"].update({
        "final_reply": wrong, "final_reply_sha256": _sha(wrong),
    })
    trace = result["runtime_trace"]
    utterance = next(row["payload"] for row in trace["blackboard"] if row.get("label") == "utterance")
    utterance["reply"] = wrong
    terminal = next(row["payload"] for row in trace["blackboard"]
                    if row.get("label") == atomic.LABEL)
    for receipt in (result["logic"][atomic.LABEL], trace[atomic.LABEL], terminal):
        for field in (
            "committed_visible_candidate_sha256", "final_visible_sha256",
            "final_guard_reply_sha256", "episode_call_reply_sha256",
        ):
            receipt[field] = _sha(wrong)
        bound = receipt["semantic_ledger"]
        bound["candidate_sha256"] = _sha(wrong)
        bound["committed_visible_candidate_sha256"] = _sha(wrong)
        bound["recall_phrase_sha256"] = _sha(forged_recall)
        if isinstance(bound.get("acts"), list) and len(bound["acts"]) == 2:
            bound["acts"][1]["realized_surface_sha256"] = _sha(forged_recall)
    graph = collect_cognitive_graph(result)
    assert graph["typed_mixed_atomic_projection_p4"] is None
    assert not [node for node in graph["nodes"] if node.get("atomic_delivery_projection")]
    assert not [edge for edge in graph["edges"] if edge["class"] == "is-atomic-delivery"]


@pytest.mark.parametrize("case_id", ["T0", "T2"])
def test_native_graph_requires_actual_turn_memory_snapshot(monkeypatch, case_id):
    result = _delivered_graph_result(monkeypatch, case_id)
    result.pop("memory_data")
    graph = collect_cognitive_graph(result)
    assert graph["typed_mixed_atomic_projection_p4"] is None
    assert not [node for node in graph["nodes"] if node.get("atomic_delivery_projection")]
