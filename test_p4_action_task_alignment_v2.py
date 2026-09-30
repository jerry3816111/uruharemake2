"""Zero-call structural checks for B2; synthetic fixtures are not scored cases."""

from __future__ import annotations

from copy import deepcopy
import json

import p4_action_task_alignment_v2 as b2
import p4_action_transaction_scoring as b1


SOURCES = [
    {"id": "synthetic:0", "kind": "current_user", "text": "I have one blank card."},
    {"id": "synthetic:1", "kind": "current_user", "text": "Please let me write one heading on the card."},
    {"id": "synthetic:2", "kind": "current_user", "text": "I will do it myself."},
    {"id": "synthetic:3", "kind": "current_user", "text": "Stop after that heading."},
    {"id": "synthetic:4", "kind": "current_user", "text": "Do not draw on the card."},
]


def ref(index: int) -> dict:
    row = SOURCES[index]
    return {"source_id": row["id"], "source_span": row["text"], "quote": row["text"]}


def frame() -> dict:
    return {
        "requested_change": {"status": "known", "target_key": "card_heading",
                             "desired_state": "one heading exists", "evidence": [ref(1)]},
        "current_substrate": [{"resource_id": "blank_card", "availability": "available",
                               "evidence": [ref(0)]}],
        "forbidden": {"status": "present", "constraints": [{
            "constraint_id": "no_drawing", "target_keys": ["drawing"],
            "operation_keys": ["draw"], "evidence": [ref(4)],
        }]},
        "actor": {"status": "known", "value": "user", "evidence": [ref(2)]},
        "stop_condition": {"status": "known", "stop_id": "one_heading_done",
                           "description": "stop after one heading", "evidence": [ref(3)]},
    }


def transaction() -> dict:
    return {
        "status": "action", "task_source_id": SOURCES[1]["id"],
        "task_source_span": SOURCES[1]["text"],
        "task_target_quote": SOURCES[1]["text"],
        "forbidden_source_id": SOURCES[4]["id"],
        "forbidden_quote": SOURCES[4]["text"],
        "actor": "user", "receipt": None,
        "prerequisite_status": "available_from_source",
        "task_goal_jp": "カードに見出しを一つ作る",
        "progress_mechanism": "structure_scaffold",
        "action_object_jp": "カード", "action_verb_jp": "書く",
        "expected_state_change_jp": "見出しが一つできる",
        "completion_jp": "見出しを一つ書いたら終わり",
        "instruction_jp": "カードに見出しを一つ書いて、そこで終わりにしてね。",
        "reason_code": "none",
    }


def proposal(locked: dict) -> dict:
    return {
        "frame_digest": b2.frame_digest(locked),
        "required_substrate_ids": ["blank_card"],
        "effect_target_key": "card_heading",
        "effect_state": "one heading appears",
        "operation_keys": ["write_heading"],
        "touched_target_keys": ["card_heading"],
        "acknowledged_forbidden_ids": ["no_drawing"],
        "completion_stop_id": "one_heading_done",
        "abstain_blocker": None,
        "transaction": transaction(),
    }


def test_valid_frame_and_proposal_only_advance_to_unchanged_b1_guard():
    locked = frame()
    assert b2.frame_payload(SOURCES) == {"user_sources": SOURCES}
    assert b2.inspect_frame(locked, SOURCES)["structurally_valid"] is True
    audit = b2.inspect_proposal(proposal(locked), locked, SOURCES)
    assert audit["schema_valid"] is True
    assert audit["ready_for_b1_guard"] is True
    assert audit["action_eligible_for_b1_guard"] is True
    assert audit["abstain_eligible_for_b1_guard"] is False
    assert audit["deliverable"] is False
    assert audit["semantic_task_truth_checked"] is False
    assert audit["existing_b1_guard_checked"] is False


def test_frame_lock_rejects_mismatch_and_cannot_be_rewritten_by_proposal():
    locked = frame()
    item = proposal(locked)
    item["frame_digest"] = "0" * 64
    assert "frame_digest_mismatch" in b2.inspect_proposal(item, locked, SOURCES)["violations"]
    item = proposal(locked)
    changed = deepcopy(locked)
    changed["requested_change"]["desired_state"] = "two headings exist"
    assert "frame_digest_mismatch" in b2.inspect_proposal(item, changed, SOURCES)["violations"]


def test_explicit_absence_and_unknown_required_resource_fail_closed():
    for availability, violation in (
        ("absent", "required_substrate_explicitly_absent"),
        ("unknown", "required_substrate_unknown_or_unlisted"),
    ):
        locked = frame()
        locked["current_substrate"][0]["availability"] = availability
        audit = b2.inspect_proposal(proposal(locked), locked, SOURCES)
        assert violation in audit["violations"]
        assert audit["ready_for_b1_guard"] is False
    locked = frame()
    item = proposal(locked)
    item["required_substrate_ids"] = ["unlisted_resource"]
    assert "required_substrate_unknown_or_unlisted" in b2.inspect_proposal(
        item, locked, SOURCES)["violations"]


def test_forbidden_constraint_must_be_acknowledged_and_not_touched():
    locked = frame()
    item = proposal(locked)
    item["acknowledged_forbidden_ids"] = []
    assert "forbidden_ids_not_all_acknowledged" in b2.inspect_proposal(
        item, locked, SOURCES)["violations"]
    item = proposal(locked)
    item["operation_keys"] = ["draw"]
    assert "proposal_conflicts_with_forbidden" not in b2.inspect_proposal(
        item, locked, SOURCES)["violations"]
    item = proposal(locked)
    item["touched_target_keys"] = ["card_heading", "drawing"]
    assert "proposal_conflicts_with_forbidden" not in b2.inspect_proposal(
        item, locked, SOURCES)["violations"]
    item["operation_keys"] = ["draw"]
    assert "proposal_conflicts_with_forbidden" in b2.inspect_proposal(
        item, locked, SOURCES)["violations"]
    scoped = frame()
    scoped["forbidden"]["constraints"][0]["target_keys"] = ["card_heading"]
    assert b2.inspect_proposal(proposal(scoped), scoped, SOURCES)[
        "ready_for_b1_guard"] is True
    locked["forbidden"] = {"status": "unknown", "constraints": []}
    item = proposal(locked)
    item["acknowledged_forbidden_ids"] = []
    item["transaction"]["forbidden_source_id"] = None
    item["transaction"]["forbidden_quote"] = None
    assert "forbidden_state_unknown" in b2.inspect_proposal(
        item, locked, SOURCES)["violations"]


def test_request_actor_stop_and_old_transaction_anchors_are_cross_checked():
    locked = frame()
    item = proposal(locked)
    item["transaction"]["task_target_quote"] = SOURCES[0]["text"]
    assert "transaction_not_anchored_to_request" in b2.inspect_proposal(
        item, locked, SOURCES)["violations"]
    item = proposal(locked)
    item["transaction"]["forbidden_quote"] = SOURCES[0]["text"]
    assert "b1_forbidden_anchor_mismatch" in b2.inspect_proposal(
        item, locked, SOURCES)["violations"]
    item = proposal(locked)
    item["completion_stop_id"] = "another_stop"
    assert "stop_unknown_or_mismatch" in b2.inspect_proposal(
        item, locked, SOURCES)["violations"]
    item = proposal(locked)
    item["transaction"]["actor"] = "assistant"
    assert "actor_unknown_or_not_user" in b2.inspect_proposal(
        item, locked, SOURCES)["violations"]


def test_unknown_request_actor_stop_and_multiple_forbidden_fail_closed():
    locked = frame()
    locked["requested_change"] = {"status": "unknown", "target_key": None,
                                  "desired_state": None, "evidence": []}
    assert "requested_change_unknown" in b2.inspect_proposal(
        proposal(locked), locked, SOURCES)["violations"]
    locked = frame()
    locked["actor"] = {"status": "unknown", "value": None, "evidence": []}
    assert "actor_unknown_or_not_user" in b2.inspect_proposal(
        proposal(locked), locked, SOURCES)["violations"]
    locked = frame()
    locked["stop_condition"] = {"status": "unknown", "stop_id": None,
                                "description": None, "evidence": []}
    assert "stop_unknown_or_mismatch" in b2.inspect_proposal(
        proposal(locked), locked, SOURCES)["violations"]
    locked = frame()
    second = deepcopy(locked["forbidden"]["constraints"][0])
    second["constraint_id"] = "no_second_operation"
    locked["forbidden"]["constraints"].append(second)
    item = proposal(locked)
    item["acknowledged_forbidden_ids"].append(second["constraint_id"])
    assert "b1_cannot_anchor_multiple_forbidden_constraints" in b2.inspect_proposal(
        item, locked, SOURCES)["violations"]


def test_exact_source_and_nonadjacent_citations_are_checked():
    locked = frame()
    assert b2.inspect_frame(locked, SOURCES)["source_exact"] is True
    changed = deepcopy(locked)
    changed["requested_change"]["evidence"][0]["quote"] = "Please let me write two headings"
    audit = b2.inspect_frame(changed, SOURCES)
    assert audit["structurally_valid"] is False
    assert "requested_change_citation_not_exact" in audit["violations"]
    changed = deepcopy(locked)
    changed["forbidden"]["constraints"][0]["evidence"][0]["source_id"] = SOURCES[0]["id"]
    assert "forbidden_citation_not_exact" in b2.inspect_frame(
        changed, SOURCES)["violations"]


def test_bad_json_and_incomplete_shape_fail_closed():
    assert b2.parse_json_object('{"x":1,"x":2}') is None
    assert b2.parse_json_object('{"x":NaN}') is None
    assert b2.parse_json_object('[]') is None
    assert b2.parse_json_object(json.dumps(frame())) == frame()
    assert b2.inspect_frame({"requested_change": {}}, SOURCES)["structurally_valid"] is False
    assert b2.inspect_proposal({}, frame(), SOURCES)["ready_for_b1_guard"] is False
    incomplete = proposal(frame())
    incomplete["required_substrate_ids"] = None
    assert b2.inspect_proposal(incomplete, frame(), SOURCES)["ready_for_b1_guard"] is False
    assert b2.inspect_proposal({"frame_digest": []}, {"current_substrate": [
        {"resource_id": [], "availability": "available", "evidence": []},
    ]}, SOURCES)["ready_for_b1_guard"] is False


def test_unsupported_abstain_reason_is_rejected_by_frame_blocker_contract():
    locked = frame()
    item = proposal(locked)
    for key in ("required_substrate_ids", "operation_keys", "touched_target_keys",
                "acknowledged_forbidden_ids"):
        item[key] = []
    for key in ("effect_target_key", "effect_state", "completion_stop_id"):
        item[key] = ""
    item["transaction"]["status"] = "abstain"
    item["transaction"]["reason_code"] = "prerequisites"
    for key in ("task_goal_jp", "progress_mechanism", "action_object_jp",
                "action_verb_jp", "expected_state_change_jp", "completion_jp",
                "instruction_jp"):
        item["transaction"][key] = ""
    audit = b2.inspect_proposal(item, locked, SOURCES)
    assert audit["structurally_valid"] is False
    assert audit["ready_for_b1_guard"] is False
    assert "abstain_reason_not_bound_to_frame_blocker" in audit["violations"]
    assert audit["action_eligible_for_b1_guard"] is False
    assert audit["abstain_eligible_for_b1_guard"] is False
    assert audit["existing_b1_guard_checked"] is False
    assert audit["deliverable"] is False
    # The unchanged B1 layer alone still misses this unsupported reason.
    b1_audit = b1.inspect_transaction(item["transaction"], SOURCES,
                                      raw_user_input=" ".join(row["text"] for row in SOURCES))
    assert b1_audit["guard_violations"] == []
    assert all(resource["availability"] == "available"
               for resource in locked["current_substrate"])
    # Source-bound here means internally tied to a self-labelled frame. It is
    # not semantic validation; a wrong frame can still lie about absence.
    missing = frame()
    missing["current_substrate"][0]["availability"] = "absent"
    item["frame_digest"] = b2.frame_digest(missing)
    item["abstain_blocker"] = ref(0)
    supported = b2.inspect_proposal(item, missing, SOURCES)
    assert supported["ready_for_b1_guard"] is True
    assert supported["abstain_eligible_for_b1_guard"] is True
    assert supported["semantic_task_truth_checked"] is False


def test_semantically_wrong_task_can_still_pass_mechanical_contract():
    """This is a limitation probe, not a B2 success or scored case."""

    sources = deepcopy(SOURCES)
    sources[1]["text"] = "The card has no heading."
    sources.insert(2, {"id": "synthetic:request", "kind": "current_user",
                       "text": "Actually, I want to number the pages instead."})
    wrong = frame()
    wrong["requested_change"]["evidence"] = [{
        "source_id": sources[1]["id"], "source_span": sources[1]["text"],
        "quote": sources[1]["text"],
    }]
    item = proposal(wrong)
    item["transaction"]["task_source_id"] = sources[1]["id"]
    item["transaction"]["task_source_span"] = sources[1]["text"]
    item["transaction"]["task_target_quote"] = sources[1]["text"]
    audit = b2.inspect_proposal(item, wrong, sources)
    assert audit["ready_for_b1_guard"] is True
    assert audit["semantic_task_truth_checked"] is False
    assert audit["source_omission_checked"] is False


def test_a_frame_that_omits_a_real_prohibition_can_still_pass_mechanics():
    """Only prospective independent annotation can expose this omission."""

    locked = frame()
    locked["forbidden"] = {"status": "none_detected", "constraints": []}
    item = proposal(locked)
    item["acknowledged_forbidden_ids"] = []
    item["transaction"]["forbidden_source_id"] = None
    item["transaction"]["forbidden_quote"] = None
    audit = b2.inspect_proposal(item, locked, SOURCES)
    assert audit["ready_for_b1_guard"] is True
    assert audit["source_omission_checked"] is False


def test_model_key_surface_mismatch_is_a_known_pre_model_false_action_counterexample():
    """Two green mechanical audits cannot authorize a Japanese action.

    The transaction changes to drawing despite a ban; the model-authored B2
    keys still claim it is writing a heading. This is a negative fixture, not
    a scored source case or evidence that the final action is safe.
    """

    locked = frame()
    item = proposal(locked)
    tx = item["transaction"]
    tx["action_verb_jp"] = "描く"
    tx["instruction_jp"] = "カードに絵を一つ描いて、そこで終わりにしてね。"
    tx["expected_state_change_jp"] = "カードに絵が一つできる"
    tx["completion_jp"] = "絵を一つ描いたら終わり"
    b2_audit = b2.inspect_proposal(item, locked, SOURCES)
    b1_audit = b1.inspect_transaction(tx, SOURCES,
                                      raw_user_input=" ".join(row["text"] for row in SOURCES))
    assert b2_audit["ready_for_b1_guard"] is True
    assert b1_audit["would_deliver"] is True
    assert b2_audit["deliverable"] is False
    assert b2_audit["semantic_task_truth_checked"] is False


def test_no_old_exposed_case_specific_keyword_in_contract_prompts():
    assert "p4_tx_zh_01" not in b2.FRAME_SYSTEM + b2.PROPOSAL_SYSTEM
    assert "今の一文" not in b2.FRAME_SYSTEM + b2.PROPOSAL_SYSTEM
