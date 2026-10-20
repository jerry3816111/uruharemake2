"""Zero-model contracts for the P4 verified producer receipt graph projection."""

from copy import deepcopy
import hashlib

import pytest

from uruha_memory_observatory import (
    M24_GRAPH_DETAIL_BUDGET_BYTES,
    M24_NODE_DETAIL_BUDGET_BYTES,
    collect_cognitive_graph,
    render_memory_observatory,
)


SCHEMA = "uruha_mixed_act_lineage_p4_v1"
EVENT = "1234567890abcdef1234567890abcdef"
M31 = EVENT + ":m31:fedcba0987654321fedcba0987654321"
M32 = EVENT + ":m32:00112233445566778899aabbccddeeff"
PROJECTION_IDS = {
    "producer-projection-event", "producer-projection-m31", "producer-projection-m32",
}


def linked_result(raw="「集合場所はまだ相談中です」を柔らかく言い換えて、前の場所も教えて。", role="mixed_request"):
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    common = {
        "schema": SCHEMA, "parent_event_id": EVENT,
        "raw_input_sha256": digest, "cycle_index": 7,
        "action_coverage_status": "unverified",
        "raw_dialogue_persisted": False,
        "authority_transfer_permitted": False,
    }
    m31_stamp = {
        **common, "producer": "m31", "proposal_id": M31,
        "status_at_return": "semantically_authorized",
    }
    m32_stamp = {
        **common, "producer": "m32", "proposal_id": M32,
        "parent_m31_id": M31,
        "parent_m31_direct_argument": True,
        "parent_m31_status_at_build": "semantically_authorized",
        "status_at_return": "deterministic_commit_repaired",
    }
    actions = [{"action_id": f"{EVENT}:{name}", "type": name,
                "coverage_status": "unverified", "raw_spans": [[1, 5]]}
               for name in ("quoted_rewrite", "past_user_place_recall")] if role == "mixed_request" else []
    blockers = ["protected_source_role"] if role == "protected" else []
    receipt = {
        "schema": SCHEMA, "status": "linked", "reason": "producer_parent_chain_verified",
        "event_id": EVENT, "raw_input_sha256": digest, "cycle_index": 7,
        "source_role_act": role, "actions": actions,
        "m31": {"status": "produced", "proposal_id": M31,
                "surface_authority_retained": True},
        "m32": {"status": "produced", "proposal_id": M32,
                "surface_authority_retained": True},
        "m33_authoritative": False, "authority_blockers": blockers,
        "producer_edges": [
            {"from_id": EVENT, "to_id": M31, "type": "event_to_m31"},
            {"from_id": M31, "to_id": M32, "type": "m31_to_m32"},
        ],
        "action_coverage_status": "unverified",
        "authority_transfer_permitted": False,
        "reply_changed_by_lineage": False,
        "raw_dialogue_persisted": False,
        "model_calls_added": 0,
    }
    trace = {
        "cycle_index": 7,
        # Like the actual capped blackboard, the producer event and proposal
        # rows are absent.  Only the independent complete receipt remains.
        "blackboard": [
            {"stage": "reason", "label": f"older-{index}",
             "payload": {"status": "observed"}}
            for index in range(66)
        ] + [{"stage": "verify", "label": "mixed_act_lineage_p4", "payload": receipt}],
        "mixed_act_lineage_p4": receipt,
        "semantic_authorization_m31": {
            "schema": "uruha_semantic_authorization_m31",
            "status": "semantically_authorized", "surface_authority": True,
            "input_digest": digest[:16],
            "mixed_act_producer_lineage_p4": m31_stamp,
        },
        "semantic_commit_repair_m32": {
            "schema": "uruha_deterministic_semantic_commit_m32",
            "status": "deterministic_commit_repaired", "surface_authority": True,
            "source_m31_status": "semantically_authorized",
            "mixed_act_producer_lineage_p4": m32_stamp,
        },
        "source_anchored_semantic_commit_m33": {"surface_authority": False},
        "current_turn_source_role_p4": {
            "raw_input_sha256": digest, "cycle_index": 7, "act": role,
        },
    }
    return {"user_text": raw, "reply": "まだ相談中って感じかな。",
            "runtime_trace": trace, "memory_data": {}}


def producer_edges(graph):
    return [edge for edge in graph["edges"] if edge["class"] == "is-producer"]


def projected_nodes(graph):
    return [node for node in graph["nodes"] if node.get("producer_projection")]


def test_linked_native_receipt_projects_three_nodes_and_exact_two_visible_paths():
    result = linked_result()
    graph = collect_cognitive_graph(result)
    html = render_memory_observatory(result)
    nodes = projected_nodes(graph)
    assert {node["id"] for node in nodes} == PROJECTION_IDS
    assert [node["label"] for node in nodes] == [
        "EVENT · verified", "M31 · verified", "M32 · verified",
    ]
    assert [(node["x"], node["y"]) for node in nodes] == [(18, 50), (206, 50), (394, 50)]
    assert producer_edges(graph) == [
        {"source": "producer-projection-event", "target": "producer-projection-m31", "class": "is-producer"},
        {"source": "producer-projection-m31", "target": "producer-projection-m32", "class": "is-producer"},
    ]
    assert html.count('<path class="brain-edge is-producer"') == 2
    assert html.count('marker-end="url(#brain-producer-arrow)"') == 2
    assert "VERIFIED RECEIPT PROJECTION · EVENT → M31 → M32" in html
    assert "action coverage unverified · authority transfer false" in html
    assert html.count("is-producer-projection") == 3
    assert all("verified receipt projection" in node["detail"] for node in nodes)
    assert all(result["user_text"] not in node["detail"] for node in nodes)
    budget = graph["payload_budget_m24"]
    assert budget["budget_met"]
    assert budget["rendered_detail_bytes"] <= M24_GRAPH_DETAIL_BUDGET_BYTES
    assert budget["largest_node_detail_bytes"] <= M24_NODE_DETAIL_BUDGET_BYTES


def test_protected_linked_chain_is_visible_without_any_authority_claim():
    result = linked_result(role="protected")
    receipt = result["runtime_trace"]["mixed_act_lineage_p4"]
    receipt["actions"] = []
    graph = collect_cognitive_graph(result)
    html = render_memory_observatory(result)
    assert len(producer_edges(graph)) == 2
    assert "blocker protected_source_role" in html
    assert "authority transfer false" in html
    assert all('"authority_transfer_permitted": false' in node["detail"]
               for node in projected_nodes(graph))


def test_clipped_blackboard_preview_does_not_replace_complete_native_receipt():
    result = linked_result()
    trace = result["runtime_trace"]
    complete = trace["mixed_act_lineage_p4"]
    trace["blackboard"][-1]["payload"] = {
        key: complete[key] for key in (
            "schema", "status", "reason", "event_id", "raw_input_sha256",
            "cycle_index", "source_role_act",
        )
    }
    trace["blackboard"][-1]["payload"]["actions"] = ["clipped preview, not evidence"]
    graph = collect_cognitive_graph(result)
    assert len(projected_nodes(graph)) == 3
    assert len(producer_edges(graph)) == 2


def _mutate(result, case):
    trace = result["runtime_trace"]
    receipt = trace["mixed_act_lineage_p4"]
    m31 = trace["semantic_authorization_m31"]
    m32 = trace["semantic_commit_repair_m32"]
    m31_stamp = m31["mixed_act_producer_lineage_p4"]
    m32_stamp = m32["mixed_act_producer_lineage_p4"]
    if case == "other_current_user":
        result["user_text"] += "別件"
    elif case == "other_current_cycle":
        trace["cycle_index"] = 8
    elif case == "wrong_receipt_schema":
        receipt["schema"] = "another-schema"
    elif case == "rejected":
        receipt["status"] = "rejected"
    elif case == "not_produced":
        receipt["status"] = "not_produced"
    elif case == "wrong_reason":
        receipt["reason"] = "inferred_from_order"
    elif case == "wrong_event":
        m31_stamp["parent_event_id"] = "other-event"
    elif case == "wrong_m31_parent":
        m32_stamp["parent_m31_id"] = "other-parent"
    elif case == "not_direct_argument":
        m32_stamp["parent_m31_direct_argument"] = False
    elif case == "wrong_m31_digest":
        m31_stamp["raw_input_sha256"] = "0" * 64
    elif case == "wrong_m32_digest":
        m32_stamp["raw_input_sha256"] = "0" * 64
    elif case == "wrong_m31_cycle":
        m31_stamp["cycle_index"] = 8
    elif case == "wrong_m32_cycle":
        m32_stamp["cycle_index"] = 8
    elif case == "wrong_m31_input_digest":
        m31["input_digest"] = "0" * 16
    elif case == "wrong_m31_status_parent":
        m32_stamp["parent_m31_status_at_build"] = "unrelated"
    elif case == "wrong_m32_source_status":
        m32["source_m31_status"] = "unrelated"
    elif case == "missing_m31_status":
        m31.pop("status")
        m31_stamp["status_at_return"] = None
        m32["source_m31_status"] = None
        m32_stamp["parent_m31_status_at_build"] = None
    elif case == "conflicting_blackboard_receipt":
        trace["blackboard"][-1]["payload"] = {"schema": SCHEMA, "status": "rejected"}
    elif case == "duplicate_proposal_id":
        receipt["m32"]["proposal_id"] = M31
        m32_stamp["proposal_id"] = M31
    elif case in {"invalid_m31_uuid_suffix", "wrong_m31_prefix"}:
        new_id = (
            EVENT + ":m31:not-a-uuid"
            if case == "invalid_m31_uuid_suffix"
            else EVENT + ":m32:" + M31.rsplit(":", 1)[1]
        )
        receipt["m31"]["proposal_id"] = new_id
        m31_stamp["proposal_id"] = new_id
        m32_stamp["parent_m31_id"] = new_id
        receipt["producer_edges"][0]["to_id"] = new_id
        receipt["producer_edges"][1]["from_id"] = new_id
    elif case == "wrong_edge_endpoint":
        receipt["producer_edges"][1]["from_id"] = "unrelated"
    elif case == "duplicate_edge":
        receipt["producer_edges"][1] = deepcopy(receipt["producer_edges"][0])
    elif case == "extra_edge":
        receipt["producer_edges"].append(deepcopy(receipt["producer_edges"][1]))
    elif case == "missing_edge":
        receipt["producer_edges"].pop()
    elif case == "missing_m31":
        trace.pop("semantic_authorization_m31")
    elif case == "missing_m32":
        trace.pop("semantic_commit_repair_m32")
    elif case == "missing_m31_stamp":
        m31.pop("mixed_act_producer_lineage_p4")
    elif case == "missing_m32_stamp":
        m32.pop("mixed_act_producer_lineage_p4")
    elif case == "not_produced_m31":
        receipt["m31"]["status"] = "not_produced"
    elif case == "stale_role_certificate":
        trace["current_turn_source_role_p4"]["cycle_index"] = 6
    elif case == "malformed_role_certificate":
        trace["current_turn_source_role_p4"] = "not a certificate"
    elif case == "m33_authority_mismatch":
        trace["source_anchored_semantic_commit_m33"]["surface_authority"] = True
    elif case == "authority_transfer":
        receipt["authority_transfer_permitted"] = True
    elif case == "coverage_claim":
        receipt["action_coverage_status"] = "verified"
    elif case == "protected_without_blocker":
        receipt["source_role_act"] = "protected"
        trace["current_turn_source_role_p4"]["act"] = "protected"
    elif case == "unknown_blocker_text":
        receipt["authority_blockers"] = ["秘密の原文"]
    elif case == "unknown_source_role":
        receipt["source_role_act"] = "秘密の原文"
        trace["current_turn_source_role_p4"]["act"] = "秘密の原文"
    else:
        raise AssertionError(case)


@pytest.mark.parametrize("case", [
    "other_current_user", "other_current_cycle", "wrong_receipt_schema",
    "rejected", "not_produced", "wrong_reason", "wrong_event",
    "wrong_m31_parent", "not_direct_argument", "wrong_m31_digest",
    "wrong_m32_digest", "wrong_m31_cycle", "wrong_m32_cycle",
    "wrong_m31_input_digest", "wrong_m31_status_parent", "wrong_m32_source_status",
    "missing_m31_status", "conflicting_blackboard_receipt",
    "duplicate_proposal_id", "invalid_m31_uuid_suffix", "wrong_m31_prefix",
    "wrong_edge_endpoint", "duplicate_edge",
    "extra_edge", "missing_edge", "missing_m31", "missing_m32",
    "missing_m31_stamp", "missing_m32_stamp", "not_produced_m31",
    "stale_role_certificate", "malformed_role_certificate", "m33_authority_mismatch",
    "authority_transfer", "coverage_claim",
    "protected_without_blocker", "unknown_blocker_text", "unknown_source_role",
])
def test_broken_native_receipt_cannot_create_verified_paths(case):
    result = linked_result()
    _mutate(result, case)
    graph = collect_cognitive_graph(result)
    html = render_memory_observatory(result)
    assert projected_nodes(graph) == []
    assert producer_edges(graph) == []
    assert '<path class="brain-edge is-producer"' not in html
    assert "VERIFIED RECEIPT PROJECTION · EVENT → M31 → M32" not in html


def test_projection_summary_is_html_escaped_and_does_not_copy_user_raw():
    raw = "秘密の原文<script>alert(1)</script>"
    result = linked_result(raw)
    receipt = result["runtime_trace"]["mixed_act_lineage_p4"]
    receipt["authority_blockers"] = ["protected_source_role"]
    graph = collect_cognitive_graph(result)
    html = render_memory_observatory(result)
    assert len(producer_edges(graph)) == 2
    assert "<script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert all(raw not in node["detail"] for node in projected_nodes(graph))


def test_raw_user_text_masquerading_as_status_never_enters_verified_detail():
    raw = "秘密の原話"
    result = linked_result(raw)
    trace = result["runtime_trace"]
    m31 = trace["semantic_authorization_m31"]
    m32 = trace["semantic_commit_repair_m32"]
    m31["status"] = raw
    m31["mixed_act_producer_lineage_p4"]["status_at_return"] = raw
    m32["source_m31_status"] = raw
    m32["mixed_act_producer_lineage_p4"]["parent_m31_status_at_build"] = raw
    graph = collect_cognitive_graph(result)
    assert projected_nodes(graph) == []
    assert producer_edges(graph) == []


@pytest.mark.parametrize("raw", [EVENT, M31.rsplit(":", 1)[1]])
def test_raw_user_text_masquerading_as_valid_hex_id_never_enters_verified_detail(raw):
    result = linked_result(raw)
    graph = collect_cognitive_graph(result)
    assert projected_nodes(graph) == []
    assert producer_edges(graph) == []
