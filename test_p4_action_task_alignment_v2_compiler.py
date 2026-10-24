"""Zero-call compiler contracts. Exposed dev cases are not a sealed score."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest

import p4_action_task_alignment_v2 as b2
import p4_action_task_alignment_v2_compiler as compiler
from p4_action_transaction_scoring import prepare_source_case
from test_p4_action_task_alignment_v2 import SOURCES, frame, ref


def decision(locked: dict, *, operation="insert_empty_heading", kind="card") -> dict:
    return {
        "schema": compiler.SCHEMA, "frame_digest": b2.frame_digest(locked),
        "decision": "action", "operation": operation,
        "resource_ids": ["blank_card"], "operand_kind": kind,
        "target_ref": ref(0), "destination_ref": None,
        "value_ref": None, "exact_value": None,
        "reason_code": "none", "blocker_ref": None,
        "blocking_resource_id": None, "blocking_constraint_id": None,
    }


def compile_synthetic(item: dict, locked: dict, sources=None) -> dict:
    sources = sources or SOURCES
    return compiler.compile_typed_decision(
        item, locked, sources,
        raw_user_input=" ".join(row["text"] for row in sources),
    )


def test_safe_heading_compiles_from_one_typed_operation_and_passes_b1_m39():
    locked = frame()
    result = compile_synthetic(decision(locked), locked)
    assert result["status"] == "compiled_action", result
    assert result["b1_guard"]["would_deliver"] is True
    assert result["b1_guard"]["m39_surface_trace"]["action"] == "accept"
    tx = result["transaction"]
    assert tx["actor"] == "user" and tx["receipt"] is None
    assert "見出し" in tx["instruction_jp"] and "描" not in tx["instruction_jp"]
    assert result["sidecar"]["operation_keys"] == list(
        compiler.OPERATION_KEYS["insert_empty_heading"])
    assert result["sidecar"]["completion_stop_id"] == "one_heading_done"
    assert result["deliverable"] is False
    assert result["semantic_role_checked"] is False


def test_draw_instruction_cannot_be_injected_or_selected_under_draw_ban():
    locked = frame()
    injected = decision(locked)
    injected["instruction_jp"] = "カードに絵を一つ描いて、そこで止めよ。"
    assert compile_synthetic(injected, locked)["status"] == "blocked"
    assert "typed_decision_shape_invalid" in compile_synthetic(injected, locked)["violations"]
    assert "unknown_operation" in compile_synthetic(
        {**decision(locked), "operation": "draw"}, locked)["violations"]
    assert "unknown_or_incompatible_operand" in compile_synthetic(
        {**decision(locked), "operand_kind": "unbounded_picture"}, locked)["violations"]

    sources = [*SOURCES, {"id": "synthetic:5", "kind": "current_user",
                          "text": "The card is labelled P-6."}]
    mark = {"source_id": "synthetic:5", "source_span": sources[-1]["text"],
            "quote": sources[-1]["text"]}
    circle = decision(locked, operation="circle_one_item", kind="card")
    circle.update(target_ref=mark, value_ref=mark, exact_value="P-6")
    result = compile_synthetic(circle, locked, sources)
    assert result["status"] == "blocked"
    assert "action_conflicts_with_forbidden" in result["violations"]
    assert result["transaction"] is None


def test_fake_prerequisites_not_credited_but_explicit_missing_resource_can_abstain():
    locked = frame()
    item = decision(locked)
    item.update(decision="abstain", operation=None, resource_ids=[], operand_kind=None,
                target_ref=None, reason_code="prerequisites", blocker_ref=ref(0),
                blocking_resource_id="blank_card")
    result = compile_synthetic(item, locked)
    assert result["status"] == "blocked"
    assert "resource_reason_without_unavailable_frame_blocker" in result["violations"]
    missing = frame()
    missing["current_substrate"][0]["availability"] = "absent"
    item["frame_digest"] = b2.frame_digest(missing)
    accepted = compile_synthetic(item, missing)
    assert accepted["status"] == "compiled_abstain", accepted
    assert accepted["transaction"]["reason_code"] == "prerequisites"
    assert accepted["transaction"]["instruction_jp"] == ""
    assert accepted["semantic_role_checked"] is False  # self-labelled frame is not gold


@pytest.mark.parametrize("bad_reason", [[], {}, 1, None])
def test_non_string_abstain_reason_fails_closed_without_exception(bad_reason):
    locked = frame()
    item = decision(locked)
    item.update(decision="abstain", operation=None, resource_ids=[], operand_kind=None,
                target_ref=None, reason_code=bad_reason, blocker_ref=ref(0),
                blocking_resource_id="blank_card")
    result = compile_synthetic(item, locked)
    assert result["status"] == "blocked"
    assert "unsupported_abstain_reason" in result["violations"]


def test_unrelated_available_resource_cannot_mask_an_absent_action_target():
    sources = [*SOURCES, {"id": "synthetic:5", "kind": "current_user",
                          "text": "An unrelated pen is available."}]
    locked = frame()
    locked["current_substrate"][0]["availability"] = "absent"
    locked["current_substrate"].append({
        "resource_id": "unrelated_pen", "availability": "available",
        "evidence": [{"source_id": "synthetic:5", "source_span": sources[-1]["text"],
                      "quote": sources[-1]["text"]}],
    })
    item = decision(locked)
    item["resource_ids"] = ["unrelated_pen"]
    result = compile_synthetic(item, locked, sources)
    assert result["status"] == "blocked"
    assert "target_not_bound_to_selected_available_resource" in result["violations"]


def test_non_value_action_cannot_smuggle_a_value_reference():
    locked = frame()
    item = decision(locked)
    item["value_ref"] = ref(0)
    result = compile_synthetic(item, locked)
    assert result["status"] == "blocked"
    assert "unexpected_value_payload" in result["violations"]


def test_known_wrong_operation_still_passes_structure_but_not_delivery():
    # Source asks for a heading, not a move; a source-exact request citation
    # cannot attest the semantic relation between the verb and the request.
    locked = frame()
    wrong = decision(locked, operation="move_one_item", kind="card")
    wrong["destination_ref"] = ref(1)
    result = compile_synthetic(wrong, locked)
    assert result["status"] == "compiled_action"  # known semantic gap
    assert result["b1_guard"]["would_deliver"] is True
    assert "移して" in result["transaction"]["instruction_jp"]
    assert "heading" in SOURCES[1]["text"] and "move" not in SOURCES[1]["text"]
    assert result["deliverable"] is False
    assert result["semantic_role_checked"] is False


def test_unrelated_forbidden_abstain_is_known_false_abstain_gap():
    # The source only forbids drawing; adding a heading is permitted. An
    # exact citation alone cannot validate the abstain reason's relevance.
    locked = frame()
    item = decision(locked)
    item.update(decision="abstain", operation=None, resource_ids=[], operand_kind=None,
                target_ref=None, reason_code="forbidden_action", blocker_ref=ref(4),
                blocking_constraint_id="no_drawing")
    result = compile_synthetic(item, locked)
    assert result["status"] == "compiled_abstain"  # known semantic gap
    assert result["b1_guard"]["valid_transaction"] is True
    assert result["deliverable"] is False
    assert result["semantic_role_checked"] is False


def test_two_source_values_produce_same_visible_instruction_without_value_truth():
    # Both literals are exact in the same source, but only C-4 is the requested
    # opening cue. This is a diagnostic red gate, not a successful dev result.
    source = [{"id": "synthetic:value", "kind": "current_user", "text":
               "The opening cue is C-4 and the closing cue is D-5. "
               "Please copy the opening cue into the blank box myself, then stop."}]
    citation = {"source_id": source[0]["id"], "source_span": source[0]["text"],
                "quote": source[0]["text"]}
    locked = {
        "requested_change": {"status": "known", "target_key": "blank_box",
                             "desired_state": "opening cue copied", "evidence": [citation]},
        "current_substrate": [{"resource_id": "blank_box", "availability": "available",
                               "evidence": [citation]}],
        "forbidden": {"status": "none_detected", "constraints": []},
        "actor": {"status": "known", "value": "user", "evidence": [citation]},
        "stop_condition": {"status": "known", "stop_id": "one_box_done",
                           "description": "stop after box", "evidence": [citation]},
    }
    outputs = []
    for literal in ("C-4", "D-5"):
        item = decision(locked, operation="copy_exact_source_value", kind="box")
        item["resource_ids"] = ["blank_box"]
        item["target_ref"] = citation
        item["value_ref"] = citation
        item["exact_value"] = literal
        result = compiler.compile_typed_decision(
            item, locked, source, raw_user_input=source[0]["text"])
        assert result["status"] == "compiled_action"  # known semantic gap
        assert result["b1_guard"]["would_deliver"] is True
        assert result["sidecar"]["internal_exact_value"] == literal
        assert result["deliverable"] is False
        outputs.append(result["transaction"]["instruction_jp"])
    assert outputs[0] == outputs[1]


def test_two_exact_prohibitions_are_checked_with_only_one_b1_primary_anchor():
    locked = frame()
    sources = [*SOURCES, {"id": "synthetic:5", "kind": "current_user",
                          "text": "Do not move other cards."}]
    second = {"constraint_id": "no_other_move", "target_keys": ["other_cards"],
              "operation_keys": ["move"],
              "evidence": [{"source_id": "synthetic:5",
                            "source_span": sources[-1]["text"],
                            "quote": sources[-1]["text"]}]}
    locked["forbidden"]["constraints"].append(second)
    item = decision(locked)
    result = compile_synthetic(item, locked, sources)
    assert result["status"] == "compiled_action", result
    sidecar = result["sidecar"]
    assert sidecar["all_framed_forbidden_checked"] is True
    assert len(sidecar["forbidden_checks"]) == 2
    assert all(check["exact_source_citations"] for check in sidecar["forbidden_checks"])
    assert sidecar["b1_checks_all_forbidden"] is False
    assert sidecar["b1_anchor_role"] == "primary_only_not_complete_coverage"
    assert result["transaction"]["forbidden_quote"] == sidecar["primary_forbidden_ref"]["quote"]
    tampered = deepcopy(locked)
    tampered["forbidden"]["constraints"][1]["evidence"][0]["quote"] = "not in source"
    item["frame_digest"] = b2.frame_digest(tampered)
    assert compile_synthetic(item, tampered, sources)["status"] == "blocked"


@pytest.mark.parametrize("case_id,operation,kind,target_role,value_role,literal", [
    ("p4_b2_dev_zh_01_v", "move_one_item", "card", "target", None, None),
    ("p4_b2_dev_zh_02_v", "copy_exact_source_value", "legend", "target", "availability", "虛線"),
    ("p4_b2_dev_en_01_v", "copy_exact_source_value", "box", "target", "availability", "C-4"),
    ("p4_b2_dev_en_02_v", "circle_one_item", "frame", "target", "target", "P-6"),
    ("p4_b2_dev_ja_01_v", "stand_upright", "hourglass", "target", None, None),
    ("p4_b2_dev_ja_02_v", "insert_empty_heading", "draft", "current", None, None),
])
def test_all_five_generic_operations_cover_exposed_dev_valid_families(
        case_id, operation, kind, target_role, value_role, literal):
    # Hand-built source-exact frames exercise template breadth only. They are
    # not generated frames, independent task judgments, or scored dev results.
    root = Path(__file__).resolve().parent
    cases = json.loads((root / "datasets/p4_action_task_alignment_v2_dev_sources.json")
                       .read_text(encoding="utf-8"))["cases"]
    gold = json.loads((root / "datasets/p4_action_task_alignment_v2_dev_gold.json")
                      .read_text(encoding="utf-8"))["gold_by_case_id"]
    case = next(row for row in cases if row["case_id"] == case_id)
    source = case["sources"][0]
    prepared = prepare_source_case(case)
    sources = prepared["sources"]
    spans = gold[case_id]["evidence_spans"]

    def cite(role, index=0):
        quote = spans[role][index]["quote"]
        clause = next(row for row in sources if quote in row["text"])
        return {"source_id": clause["id"], "source_span": clause["text"],
                "quote": quote}

    request = cite("request")
    locked = {
        "requested_change": {"status": "known", "target_key": "requested_target",
                             "desired_state": "one bounded change", "evidence": [request]},
        "current_substrate": [{"resource_id": "required_material", "availability": "available",
                               "evidence": [cite("availability", i)
                                            for i in range(len(spans["availability"]))]
                               + [cite("current", i) for i in range(len(spans["current"]))]
                               + [cite("target", i) for i in range(len(spans["target"]))]}],
        "forbidden": {"status": "present", "constraints": [
            {"constraint_id": f"ban_{i}", "target_keys": [f"other_target_{i}"],
             "operation_keys": ["modify"], "evidence": [cite("forbidden", i)]}
            for i in range(len(spans["forbidden"]))]},
        "actor": {"status": "known", "value": "user", "evidence": [cite("actor")]},
        "stop_condition": {"status": "known", "stop_id": "one_done",
                           "description": "stop after one", "evidence": [cite("stop")]},
    }
    item = decision(locked, operation=operation, kind=kind)
    item["resource_ids"] = ["required_material"]
    item["target_ref"] = cite(target_role)
    if operation == "move_one_item":
        item["destination_ref"] = request
    if literal is not None:
        item["value_ref"] = cite(value_role)
        item["exact_value"] = literal
    result = compiler.compile_typed_decision(
        item, locked, sources, raw_user_input=source["text"])
    assert result["status"] == "compiled_action", (case_id, result)
    assert result["b1_guard"]["would_deliver"] is True
    assert result["b1_guard"]["m39_surface_trace"]["action"] == "accept"
    if literal == "C-4":
        assert result["sidecar"]["internal_exact_value"] == "C-4"
        assert "C-4" not in result["transaction"]["instruction_jp"]
        assert "Ｃ－４" not in result["transaction"]["instruction_jp"]
        assert "元の文で示した値を文字どおり" in result["transaction"]["instruction_jp"]
