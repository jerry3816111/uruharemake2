"""Zero-model contracts for the read-only two-action terminal graph projection.

Synthetic receipts test graph honesty; they are not model, Safari, source
durability, or rewrite-semantic-equivalence evidence.
"""

from copy import deepcopy
import hashlib

import pytest

from test_p4_verified_producer_graph_projection import linked_result
from uruha_memory_observatory import (
    MEMORY_OBSERVATORY_CSS,
    M24_GRAPH_DETAIL_BUDGET_BYTES,
    M24_NODE_DETAIL_BUDGET_BYTES,
    collect_cognitive_graph,
    render_memory_observatory,
)


ATOMIC_IDS = {
    "typed-atomic-rewrite", "typed-atomic-recall", "typed-atomic-terminal",
}


def _sha(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def delivered_result(*, source_backed=True, raw=None, m31_authority=False):
    result = linked_result(raw=raw) if raw is not None else linked_result()
    trace = result["runtime_trace"]
    lineage = trace["mixed_act_lineage_p4"]
    m31 = trace["semantic_authorization_m31"]
    m32 = trace["semantic_commit_repair_m32"]
    m31["surface_authority"] = m31_authority
    lineage["m31"]["surface_authority_retained"] = m31_authority
    m32["terminal_transaction_shadowed_surface_p4"] = "typed_mixed_atomic_delivery_p4"
    reply = "「集合場所、まだ相談中なんだ」がいいかな。前の場所は白磁の掲示板の横って言ってたな。" if source_backed else (
        "「集合場所、まだ相談中なんだ」がいいかな。その日の場所は、今ある会話だけじゃ分からないな。"
    )
    result["reply"] = reply
    result["episode_doc"] = f"Time: 2026-10-20 | User: {result['user_text']} | Uruha: {reply} | Mood: calm"
    digest = _sha(reply)
    source_status = "source_backed" if source_backed else "no_admitted_user_source"
    receipt = {
        "schema": "uruha_typed_mixed_atomic_delivery_p4_v1",
        "status": "delivered_structure_semantics_unverified",
        "action_coverage_status": "visible_structure_delivered_semantics_unverified",
        "event_id": lineage["event_id"],
        "raw_input_sha256": lineage["raw_input_sha256"],
        "cycle_index": trace["cycle_index"],
        "m31_proposal_id": lineage["m31"]["proposal_id"],
        "m32_proposal_id": lineage["m32"]["proposal_id"],
        "action_ids": [action["action_id"] for action in lineage["actions"]],
        "prior_m31_surface_authority": m31_authority,
        "prior_m32_surface_authority": True,
        "lineage_authority_transfer_permitted": False,
        "terminal_priority_status": "applied_after_legacy_m32",
        "rewrite_action_surface_status": "shape_visible_semantics_unverified",
        "rewrite_contrast_status": "bounded_contrast_accepted_semantics_unverified",
        "recall_action_surface_status": (
            "source_backed_visible" if source_backed else "honest_unknown_visible"
        ),
        "source_status": source_status,
        "source_channel": "recent_turns" if source_backed else None,
        "source_trace_id": "recent:user:one" if source_backed else None,
        "semantic_equivalence_certified": False,
        "db_readback_verified": False,
        "persistent_fact_write": False,
        "raw_dialogue_persisted_in_receipt": False,
        "final_consistent": True,
        "quote_sha256": "1" * 64,
        "rewrite_phrase_sha256": "2" * 64,
        "source_binding_sha256": "3" * 64,
        "source_reply_sha256": "4" * 64,
        "committed_visible_candidate_sha256": digest,
        "final_visible_sha256": digest,
        "final_guard_reply_sha256": digest,
        "episode_call_reply_sha256": digest,
        "model_call": {
            "attempted_calls": 1, "completed_calls": 1,
            "model_phrase_sha256": "2" * 64,
            "status": "bounded_shape_accepted_semantics_unverified",
        },
        **{key: True for key in (
            "candidate_equals_final", "guard_equals_final", "graph_utterance_equals_final",
            "episode_argument_equals_final", "episode_doc_equals_final",
            "right_brain_history_equals_final", "terminal_priority_applied",
            "history_committed",
        )},
    }
    result["logic"] = {
        "typed_mixed_atomic_delivery_p4": deepcopy(receipt),
        "visible_language_guard": {
            "final_reply": reply, "final_reply_sha256": digest,
            "final_rejection_reasons": [],
        },
    }
    trace["typed_mixed_atomic_delivery_p4"] = deepcopy(receipt)
    trace["blackboard"].extend([
        {"stage": "surface", "label": "typed_mixed_atomic_delivery_p4", "payload": deepcopy(receipt)},
        {"stage": "surface", "label": "utterance", "payload": {"reply": reply}},
    ])
    return result


def _atomic_nodes(graph):
    return [node for node in graph["nodes"] if node.get("atomic_delivery_projection")]


def _atomic_edges(graph):
    return [edge for edge in graph["edges"] if edge["class"] == "is-atomic-delivery"]


@pytest.mark.parametrize("source_backed", [True, False])
@pytest.mark.parametrize("m31_authority", [False, True])
def test_structurally_delivered_actions_get_distinct_native_graph_paths(source_backed, m31_authority):
    result = delivered_result(source_backed=source_backed, m31_authority=m31_authority)
    graph = collect_cognitive_graph(result)
    html = render_memory_observatory(result)
    assert {node["id"] for node in _atomic_nodes(graph)} == ATOMIC_IDS
    assert graph["typed_mixed_atomic_projection_p4"]["semantic_equivalence_certified"] is False
    assert graph["typed_mixed_atomic_projection_p4"]["source_status"] == (
        "source_backed" if source_backed else "no_admitted_user_source"
    )
    assert {(node["id"], node["x"], node["y"]) for node in _atomic_nodes(graph)} == {
        ("typed-atomic-rewrite", 610, 50),
        ("typed-atomic-recall", 610, 142),
        ("typed-atomic-terminal", 840, 96),
    }
    assert _atomic_edges(graph) == [
        {"source": "producer-projection-m32", "target": "typed-atomic-rewrite", "class": "is-atomic-delivery"},
        {"source": "producer-projection-m32", "target": "typed-atomic-recall", "class": "is-atomic-delivery"},
        {"source": "typed-atomic-rewrite", "target": "typed-atomic-terminal", "class": "is-atomic-delivery"},
        {"source": "typed-atomic-recall", "target": "typed-atomic-terminal", "class": "is-atomic-delivery"},
        {"source": "typed-atomic-terminal", "target": "turn-output", "class": "is-atomic-delivery"},
    ]
    assert html.count('<path class="brain-edge is-atomic-delivery"') == 5
    assert html.count('marker-end="url(#brain-atomic-arrow)"') == 5
    assert html.count("is-atomic-delivery-projection") == 3
    assert "has-producer has-atomic" in html
    assert ".brain-graph-canvas.has-atomic .brain-stage-lane { top: 238px; }" in MEMORY_OBSERVATORY_CSS
    assert "VISIBLE TWO-ACTION DELIVERY · REWRITE + RECALL → UTTERANCE" in html
    assert "rewrite meaning unverified · DB readback unverified" in html
    assert ("recall direct User source" if source_backed else "recall honest unknown") in html
    for node in _atomic_nodes(graph):
        assert result["user_text"] not in node["detail"]
        assert "白磁の掲示板の横" not in node["detail"]
        assert "meaning and DB durability unverified" in node["detail"] if node["id"] == "typed-atomic-terminal" else True
        if node["id"] == "typed-atomic-terminal":
            assert f'"prior_m31_surface_authority": {str(m31_authority).lower()}' in node["detail"]
    budget = graph["payload_budget_m24"]
    assert budget["budget_met"]
    assert budget["rendered_detail_bytes"] <= M24_GRAPH_DETAIL_BUDGET_BYTES
    assert budget["largest_node_detail_bytes"] <= M24_NODE_DETAIL_BUDGET_BYTES


@pytest.mark.parametrize("m31_authority", [False, True])
@pytest.mark.parametrize("site", ["terminal_receipt", "lineage_receipt", "producer_trace"])
@pytest.mark.parametrize("fault", ["mismatch", "missing", "non_bool"])
def test_m31_authority_disagreement_never_projects_delivered_actions(m31_authority, site, fault):
    result = delivered_result(m31_authority=m31_authority)
    trace = result["runtime_trace"]
    if site == "terminal_receipt":
        targets = [
            trace["typed_mixed_atomic_delivery_p4"],
            result["logic"]["typed_mixed_atomic_delivery_p4"],
            next(row["payload"] for row in trace["blackboard"]
                 if row.get("label") == "typed_mixed_atomic_delivery_p4"),
        ]
        key = "prior_m31_surface_authority"
    elif site == "lineage_receipt":
        targets = [trace["mixed_act_lineage_p4"]["m31"]]
        key = "surface_authority_retained"
    else:
        targets = [trace["semantic_authorization_m31"]]
        key = "surface_authority"
    for target in targets:
        if fault == "missing":
            target.pop(key)
        else:
            target[key] = not m31_authority if fault == "mismatch" else "true"
    graph = collect_cognitive_graph(result)
    html = render_memory_observatory(result)
    assert _atomic_nodes(graph) == []
    assert _atomic_edges(graph) == []
    assert graph["typed_mixed_atomic_projection_p4"] is None
    assert 'marker-end="url(#brain-atomic-arrow)"' not in html


def _mutate(result, case):
    trace = result["runtime_trace"]
    receipt = trace["typed_mixed_atomic_delivery_p4"]
    logic_receipt = result["logic"]["typed_mixed_atomic_delivery_p4"]
    if case == "rejected":
        receipt["status"] = logic_receipt["status"] = "candidate_rejected_original_route_kept"
    elif case == "partial_coverage":
        receipt["action_coverage_status"] = logic_receipt["action_coverage_status"] = "not_verified"
    elif case == "not_final_consistent":
        receipt["final_consistent"] = logic_receipt["final_consistent"] = False
    elif case == "semantic_claim":
        receipt["semantic_equivalence_certified"] = logic_receipt["semantic_equivalence_certified"] = True
    elif case == "db_claim":
        receipt["db_readback_verified"] = logic_receipt["db_readback_verified"] = True
    elif case == "other_event":
        receipt["event_id"] = logic_receipt["event_id"] = "other-event"
    elif case == "other_cycle":
        receipt["cycle_index"] = logic_receipt["cycle_index"] = 8
    elif case == "other_digest":
        receipt["raw_input_sha256"] = logic_receipt["raw_input_sha256"] = "0" * 64
    elif case == "action_id":
        receipt["action_ids"][0] = logic_receipt["action_ids"][0] = "other-action"
    elif case == "duplicate_action":
        receipt["action_ids"][1] = logic_receipt["action_ids"][1] = receipt["action_ids"][0]
    elif case == "parent_id":
        receipt["m32_proposal_id"] = logic_receipt["m32_proposal_id"] = "other-parent"
    elif case == "producer_broken":
        trace["semantic_commit_repair_m32"]["mixed_act_producer_lineage_p4"]["parent_m31_id"] = "other-parent"
    elif case == "m32_not_shadowed":
        trace["semantic_commit_repair_m32"].pop("terminal_transaction_shadowed_surface_p4")
    elif case == "terminal_not_applied":
        receipt["terminal_priority_status"] = logic_receipt["terminal_priority_status"] = "rejected_at_final_guard"
    elif case == "rewrite_not_delivered":
        receipt["rewrite_action_surface_status"] = logic_receipt["rewrite_action_surface_status"] = "not_delivered"
    elif case == "recall_not_delivered":
        receipt["recall_action_surface_status"] = logic_receipt["recall_action_surface_status"] = "not_delivered"
    elif case == "wrong_source_role":
        trace["mixed_act_lineage_p4"]["source_role_act"] = "single_rewrite"
        trace["current_turn_source_role_p4"]["act"] = "single_rewrite"
    elif case == "source_protected":
        trace["mixed_act_lineage_p4"]["authority_blockers"] = ["protected_source_role"]
    elif case == "source_channel_missing":
        receipt["source_channel"] = logic_receipt["source_channel"] = None
    elif case == "call_not_completed":
        receipt["model_call"]["completed_calls"] = logic_receipt["model_call"]["completed_calls"] = 0
    elif case == "candidate_digest":
        receipt["committed_visible_candidate_sha256"] = logic_receipt["committed_visible_candidate_sha256"] = "0" * 64
    elif case == "actual_reply":
        result["reply"] = "別の答え。"
    elif case == "guard_reply":
        result["logic"]["visible_language_guard"]["final_reply"] = "別の答え。"
    elif case == "utterance_reply":
        trace["blackboard"][-1]["payload"]["reply"] = "別の答え。"
    elif case == "episode_reply":
        result["episode_doc"] = "Time: t | User: q | Uruha: 別の答え。 | Mood: calm"
    elif case == "trace_receipt":
        trace["blackboard"][-2]["payload"]["status"] = "different"
    elif case == "logic_receipt":
        logic_receipt["status"] = "different"
    elif case == "missing_guard":
        result["logic"].pop("visible_language_guard")
    elif case == "missing_utterance":
        trace["blackboard"].pop()
    else:
        raise AssertionError(case)


@pytest.mark.parametrize("case", [
    "rejected", "partial_coverage", "not_final_consistent", "semantic_claim",
    "db_claim", "other_event", "other_cycle", "other_digest", "action_id",
    "duplicate_action", "parent_id", "producer_broken", "m32_not_shadowed",
    "terminal_not_applied", "rewrite_not_delivered", "recall_not_delivered",
    "wrong_source_role", "source_protected", "source_channel_missing",
    "call_not_completed", "candidate_digest", "actual_reply", "guard_reply",
    "utterance_reply", "episode_reply", "trace_receipt", "logic_receipt",
    "missing_guard", "missing_utterance",
])
def test_failed_or_mismatched_receipt_never_projects_action_completion(case):
    result = delivered_result()
    _mutate(result, case)
    graph = collect_cognitive_graph(result)
    html = render_memory_observatory(result)
    assert _atomic_nodes(graph) == []
    assert _atomic_edges(graph) == []
    assert graph["typed_mixed_atomic_projection_p4"] is None
    assert 'marker-end="url(#brain-atomic-arrow)"' not in html
    assert "VISIBLE TWO-ACTION DELIVERY · REWRITE + RECALL → UTTERANCE" not in html


def test_raw_text_is_escaped_and_never_copied_to_atomic_details():
    raw = "秘密の原文<script>alert(1)</script>"
    result = delivered_result(raw=raw)
    graph = collect_cognitive_graph(result)
    html = render_memory_observatory(result)
    assert len(_atomic_nodes(graph)) == 3
    assert "<script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert all(raw not in node["detail"] for node in _atomic_nodes(graph))

