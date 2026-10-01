"""Pure, bounded B2 typed-decision -> Japanese B1 transaction compiler.

This is an offline *structural* component.  Its only visible action language is
five fixed templates; candidates cannot supply a B1 transaction or Japanese
instruction.  Exact citations and symbolic prohibition scopes are checked, but
neither a model-authored frame's semantic roles nor omitted prohibitions are
proved by those checks.  No caller may treat ``compiled_action`` as delivery
authorization without independent prospective task/source evaluation.
"""

from __future__ import annotations

import re

import p4_action_task_alignment_v2 as b2
import p4_action_transaction_scoring as b1


SCHEMA = "p4_action_task_alignment_v2_typed_decision_v1"
RESULT_SCHEMA = "p4_action_task_alignment_v2_compiler_result_v1"
FIELDS = frozenset({
    "schema", "frame_digest", "decision", "operation", "resource_ids",
    "operand_kind", "target_ref", "destination_ref", "value_ref",
    "exact_value", "reason_code", "blocker_ref", "blocking_resource_id",
    "blocking_constraint_id",
})
OPERAND_KINDS = {
    "move_one_item": frozenset({"card", "item"}),
    "copy_exact_source_value": frozenset({"box", "legend"}),
    "circle_one_item": frozenset({"frame", "card", "item"}),
    "stand_upright": frozenset({"hourglass", "object"}),
    "insert_empty_heading": frozenset({"draft", "document", "card"}),
}
OPERATION_KEYS = {
    "move_one_item": ("move_one_item", "move", "touch", "modify"),
    "copy_exact_source_value": ("copy_exact_source_value", "copy", "write", "touch", "modify"),
    "circle_one_item": ("circle_one_item", "circle", "draw", "touch", "modify"),
    "stand_upright": ("stand_upright", "stand", "touch", "modify"),
    "insert_empty_heading": ("insert_empty_heading", "write_heading", "write", "touch", "modify"),
}
KNOWN_OPERATION_SCOPE_KEYS = frozenset(
    key for keys in OPERATION_KEYS.values() for key in keys
)
VALUE_RE = re.compile(r"(?:[A-Za-z0-9][A-Za-z0-9-]{0,39}|[一-龯々ぁ-ヿー]{1,40})\Z")
RESOURCE_ID_RE = re.compile(r"[a-z][a-z0-9_]{0,63}\Z")
ABSTAIN_REASONS = frozenset({
    "prerequisites", "unsupported_specificity", "source_grounding",
    "ambiguous_or_unsupported", "wrong_task", "private_inference",
    "forbidden_action", "actor_capability",
})
RESOURCE_BLOCK_REASONS = frozenset({
    "prerequisites", "unsupported_specificity", "source_grounding",
    "ambiguous_or_unsupported", "wrong_task", "private_inference",
})

_OBJECT_JP = {
    "card": "指定のカード", "item": "指定の一品", "box": "指定の空欄",
    "legend": "指定の図例欄", "frame": "指定の写真枠",
    "hourglass": "指定の砂時計", "object": "指定の道具",
    "draft": "指定の草案", "document": "指定の文書",
}


def _blocked(*violations: str, sidecar: dict | None = None,
             b1_guard: dict | None = None) -> dict:
    return {
        "schema": RESULT_SCHEMA, "status": "blocked",
        "violations": sorted(set(violations)), "transaction": None,
        "sidecar": sidecar, "b1_guard": b1_guard,
        "ready_for_b1_guard": False, "b1_guard_passed": False,
        "deliverable": False, "model_calls": 0, "product_runtime_changed": False,
        "semantic_role_checked": False, "source_omission_checked": False,
    }


def _exact_ref(ref: object, sources: dict[str, str]) -> bool:
    return bool(
        isinstance(ref, dict) and set(ref) == {"source_id", "source_span", "quote"}
        and all(type(ref.get(key)) is str for key in ref)
        and ref["quote"] and ref["quote"] == ref["quote"].strip()
        and len(ref["quote"]) <= 240
        and sources.get(ref["source_id"]) == ref["source_span"]
        and ref["quote"] in ref["source_span"]
    )


def _covered_by_evidence(ref: dict, evidence: list[dict]) -> bool:
    """A shorter exact operand quote must occur in a cited substrate span."""

    return any(
        ref["source_id"] == row["source_id"]
        and ref["source_span"] == row["source_span"]
        and ref["quote"] in row["quote"]
        for row in evidence
    )


def _first_request_ref(frame: dict) -> dict | None:
    refs = frame["requested_change"]["evidence"]
    return sorted(refs, key=lambda row: (
        row["source_id"], row["quote"], row["source_span"]
    ))[0] if refs else None


def _primary_forbidden(frame: dict) -> tuple[dict | None, dict | None]:
    constraints = frame["forbidden"]["constraints"]
    if not constraints:
        return None, None
    primary = sorted(constraints, key=lambda row: row["constraint_id"])[0]
    ref = sorted(primary["evidence"], key=lambda row: (
        row["source_id"], row["quote"], row["source_span"]
    ))[0]
    return primary, ref


def _render(operation: str, kind: str) -> dict:
    """No candidate text is interpolated into any Japanese field."""

    obj = _OBJECT_JP[kind]
    if operation == "move_one_item":
        destination_noun = "列" if kind == "card" else "場所"
        destination = f"指定の{destination_noun}"
        return {
            "task_goal_jp": f"{obj}を{destination}へ移す",
            "progress_mechanism": "direct_atomic_completion",
            "action_object_jp": obj, "action_verb_jp": "移す",
            "expected_state_change_jp": f"{obj}だけが{destination}に移る",
            "completion_jp": "その一つを移したら止める",
            "instruction_jp": f"まず{obj}だけを、元の文で移動先に指定した{destination_noun}へ移して、そこで止めよ。",
        }
    if operation == "copy_exact_source_value":
        return {
            "task_goal_jp": f"{obj}に元の文の値を写す",
            "progress_mechanism": "direct_atomic_completion",
            "action_object_jp": obj, "action_verb_jp": "写す",
            "expected_state_change_jp": f"{obj}だけに元の文の値が入る",
            "completion_jp": "その一か所に値を写したら止める",
            "instruction_jp": f"まず{obj}に、元の文で示した値を文字どおり一つ写して、そこで止めよ。",
        }
    if operation == "circle_one_item":
        return {
            "task_goal_jp": f"{obj}を一つ囲む",
            "progress_mechanism": "direct_atomic_completion",
            "action_object_jp": obj, "action_verb_jp": "囲む",
            "expected_state_change_jp": f"{obj}だけが丸で囲まれる",
            "completion_jp": "その一つを囲んだら止める",
            "instruction_jp": f"まず元の文で指定した{obj}だけを一つ丸で囲んで、そこで止めよ。",
        }
    if operation == "stand_upright":
        return {
            "task_goal_jp": f"{obj}を立てる",
            "progress_mechanism": "direct_atomic_completion",
            "action_object_jp": obj, "action_verb_jp": "立てる",
            "expected_state_change_jp": f"{obj}だけが立つ",
            "completion_jp": "その一つを立てたら止める",
            "instruction_jp": f"まず{obj}だけを一つ立てて、そこで止めよ。",
        }
    if operation == "insert_empty_heading":
        return {
            "task_goal_jp": f"{obj}に空の見出しを加える",
            "progress_mechanism": "structure_scaffold",
            "action_object_jp": obj, "action_verb_jp": "加える",
            "expected_state_change_jp": f"{obj}に空の見出しが一つできる",
            "completion_jp": "空の見出しを一つ加えたら止める",
            "instruction_jp": f"まず{obj}に空の見出しを一つだけ加えて、そこで止めよ。",
        }
    raise ValueError("unknown operation")


def _action_scope(frame: dict, operation: str, kind: str) -> tuple[list[str], list[str]]:
    target = frame["requested_change"]["target_key"]
    touched = {target, kind}
    if operation == "circle_one_item":
        touched.add("drawing")
    elif operation == "insert_empty_heading":
        touched.add("heading")
    elif operation == "copy_exact_source_value":
        touched.add("written_value")
    return list(OPERATION_KEYS[operation]), sorted(touched)


def _forbidden_sidecar(frame: dict, operation_keys: list[str],
                       touched_keys: list[str]) -> tuple[dict, list[str]]:
    checks = []
    violations = []
    for constraint in sorted(frame["forbidden"]["constraints"],
                             key=lambda row: row["constraint_id"]):
        targets = set(constraint["target_keys"])
        operations = set(constraint["operation_keys"])
        unknown_operations = sorted(operations - KNOWN_OPERATION_SCOPE_KEYS)
        target_match = not targets or bool(targets.intersection(touched_keys))
        operation_match = not operations or bool(operations.intersection(operation_keys))
        conflict = target_match and operation_match
        checks.append({
            "constraint_id": constraint["constraint_id"],
            "exact_source_citations": constraint["evidence"],
            "target_keys": sorted(targets), "operation_keys": sorted(operations),
            "target_scope_matches": target_match,
            "operation_scope_matches": operation_match,
            "conflicts_with_derived_action": conflict,
            "unknown_operation_scope_keys": unknown_operations,
        })
        if unknown_operations:
            violations.append("unknown_forbidden_operation_scope")
        if conflict:
            violations.append("action_conflicts_with_forbidden")
    primary, ref = _primary_forbidden(frame)
    return {
        "operation_keys": operation_keys, "touched_target_keys": touched_keys,
        "forbidden_checks": checks,
        "all_framed_forbidden_checked": len(checks) == len(frame["forbidden"]["constraints"]),
        "primary_forbidden_id": primary["constraint_id"] if primary else None,
        "primary_forbidden_ref": ref,
        "b1_anchor_role": "primary_only_not_complete_coverage" if primary else "none",
        "b1_checks_all_forbidden": False,
        "symbolic_scope_only_not_semantic_proof": True,
    }, violations


def _base_transaction(frame: dict, sources: list[dict], status: str) -> dict:
    request_ref = _first_request_ref(frame)
    source = next((row for row in sources if row["id"] == request_ref["source_id"]), None) if request_ref else sources[0]
    _primary, forbidden_ref = _primary_forbidden(frame)
    return {
        "status": status, "task_source_id": source["id"],
        "task_source_span": source["text"],
        "task_target_quote": request_ref["quote"] if request_ref else "",
        "forbidden_source_id": forbidden_ref["source_id"] if forbidden_ref else None,
        "forbidden_quote": forbidden_ref["quote"] if forbidden_ref else None,
        "actor": frame["actor"]["value"] if frame["actor"]["status"] == "known" else "unknown",
        "receipt": None,
        "prerequisite_status": "available_from_source" if status == "action" else "unknown",
        **{field: "" for field in b1.ACTION_FIELDS},
        "reason_code": "none",
    }


def _action_checks(decision: dict, frame: dict, source_map: dict[str, str]) -> tuple[list[str], dict]:
    violations: list[str] = []
    operation = decision["operation"]
    kind = decision["operand_kind"]
    if type(operation) is not str or operation not in OPERAND_KINDS:
        return ["unknown_operation"], {}
    if type(kind) is not str or kind not in OPERAND_KINDS[operation]:
        return ["unknown_or_incompatible_operand"], {}
    if decision["reason_code"] != "none" or any(decision[key] is not None for key in (
            "blocker_ref", "blocking_resource_id", "blocking_constraint_id")):
        violations.append("action_has_abstain_payload")
    resources = decision["resource_ids"]
    frame_resources = {row["resource_id"]: row["availability"]
                       for row in frame["current_substrate"]}
    if (not isinstance(resources, list) or not 1 <= len(resources) <= 4
            or any(type(item) is not str or not RESOURCE_ID_RE.fullmatch(item)
                   for item in resources)
            or len(resources) != len(set(resources))):
        violations.append("invalid_required_resources")
        resources = []
    for resource_id in resources:
        if frame_resources.get(resource_id) != "available":
            violations.append("required_resource_not_available_from_frame")
    if frame["requested_change"]["status"] != "known":
        violations.append("requested_change_unknown")
    if frame["actor"]["status"] != "known" or frame["actor"]["value"] != "user":
        violations.append("actor_not_user")
    if frame["stop_condition"]["status"] != "known":
        violations.append("stop_unknown")
    if frame["forbidden"]["status"] == "unknown":
        violations.append("forbidden_state_unknown")
    if not _exact_ref(decision["target_ref"], source_map):
        violations.append("target_ref_not_exact")
    else:
        available_evidence = [ref for row in frame["current_substrate"]
                              if row["resource_id"] in resources
                              and row["availability"] == "available"
                              for ref in row["evidence"]]
        if not _covered_by_evidence(decision["target_ref"], available_evidence):
            violations.append("target_not_bound_to_selected_available_resource")
    has_destination = operation == "move_one_item"
    if has_destination != (decision["destination_ref"] is not None):
        violations.append("destination_ref_contract_mismatch")
    elif has_destination and not _exact_ref(decision["destination_ref"], source_map):
        violations.append("destination_ref_not_exact")
    elif has_destination and decision["destination_ref"] not in frame["requested_change"]["evidence"]:
        violations.append("destination_not_bound_to_request")
    has_value = operation in {"copy_exact_source_value", "circle_one_item"}
    if has_value != (decision["value_ref"] is not None and decision["exact_value"] is not None):
        violations.append("value_ref_contract_mismatch")
    elif has_value:
        value_ref = decision["value_ref"]
        literal = decision["exact_value"]
        if not _exact_ref(value_ref, source_map):
            violations.append("value_ref_not_exact")
        if (type(literal) is not str or not VALUE_RE.fullmatch(literal)
                or not isinstance(value_ref, dict)
                or type(value_ref.get("quote")) is not str
                or type(value_ref.get("source_span")) is not str
                or value_ref["quote"].count(literal) != 1
                or value_ref["source_span"].count(literal) != 1):
            violations.append("exact_value_not_unique_safe_source_literal")
        available_refs = [ref for row in frame["current_substrate"]
                          if row["resource_id"] in resources
                          and row["availability"] == "available"
                          for ref in row["evidence"]]
        if operation == "copy_exact_source_value" and not any(
                type(ref.get("quote")) is str and literal in ref["quote"]
                for ref in available_refs):
            violations.append("copy_value_not_in_available_substrate_evidence")
    elif decision["value_ref"] is not None or decision["exact_value"] is not None:
        violations.append("unexpected_value_payload")
    if operation == "circle_one_item" and decision["target_ref"] != decision["value_ref"]:
        violations.append("circled_item_and_value_ref_diverge")

    operation_keys, touched_keys = _action_scope(frame, operation, kind) if (
        frame["requested_change"]["status"] == "known") else (list(OPERATION_KEYS[operation]), [])
    sidecar, forbidden_violations = _forbidden_sidecar(frame, operation_keys, touched_keys)
    violations.extend(forbidden_violations)
    sidecar.update({
        "typed_operation": operation,
        "operand_kind": kind,
        "required_substrate_ids": list(resources),
        "effect_target_key": frame["requested_change"]["target_key"],
        "completion_stop_id": frame["stop_condition"]["stop_id"],
        # Internal provenance only: the exact literal is not normalized or
        # copied into Japanese fields, where B1/M46 reject ASCII such as C-4.
        "internal_exact_value": decision["exact_value"] if has_value else None,
        "internal_exact_value_ref": decision["value_ref"] if has_value else None,
        "semantic_role_checked": False,
        "source_omission_checked": False,
    })
    return violations, sidecar


def _abstain_checks(decision: dict, frame: dict, source_map: dict[str, str]) -> list[str]:
    violations = []
    if (decision["operation"] is not None or decision["resource_ids"] != []
            or decision["operand_kind"] is not None
            or any(decision[key] is not None for key in (
                "target_ref", "destination_ref", "value_ref", "exact_value"))):
        violations.append("abstain_has_action_payload")
    reason = decision["reason_code"]
    blocker = decision["blocker_ref"]
    if type(reason) is not str or reason not in ABSTAIN_REASONS:
        violations.append("unsupported_abstain_reason")
        return violations
    if not _exact_ref(blocker, source_map):
        violations.append("abstain_blocker_not_exact")
    if reason in RESOURCE_BLOCK_REASONS:
        resource_id = decision["blocking_resource_id"]
        rows = [row for row in frame["current_substrate"]
                if row["resource_id"] == resource_id
                and row["availability"] in {"absent", "unknown"}]
        if (len(rows) != 1 or blocker not in rows[0]["evidence"]
                or decision["blocking_constraint_id"] is not None):
            violations.append("resource_reason_without_unavailable_frame_blocker")
    elif reason == "forbidden_action":
        rows = [row for row in frame["forbidden"]["constraints"]
                if row["constraint_id"] == decision["blocking_constraint_id"]]
        if (len(rows) != 1 or blocker not in rows[0]["evidence"]
                or decision["blocking_resource_id"] is not None):
            violations.append("forbidden_reason_without_frame_blocker")
    elif reason == "actor_capability":
        if (frame["actor"]["status"] != "known"
                or frame["actor"]["value"] != "assistant"
                or blocker not in frame["actor"]["evidence"]
                or decision["blocking_resource_id"] is not None
                or decision["blocking_constraint_id"] is not None):
            violations.append("actor_reason_without_frame_blocker")
    return violations


def compile_typed_decision(decision: object, frame: object, sources: list[dict],
                           *, raw_user_input: str) -> dict:
    """Compile one finite decision; never issue a user-visible release verdict.

    ``compiled_action`` means the generated B1 transaction passed the old
    mechanical guard, *not* that the candidate understood the task.  The
    original source text is supplied only for the existing M39 surface audit.
    """

    try:
        frame_audit = b2.inspect_frame(frame, sources)
        source_map = b2._sources(sources)
    except (TypeError, ValueError, KeyError):
        return _blocked("invalid_sources_or_frame")
    if not frame_audit["structurally_valid"] or not isinstance(frame, dict):
        return _blocked("frame_invalid")
    if not isinstance(decision, dict) or set(decision) != FIELDS:
        return _blocked("typed_decision_shape_invalid")
    if decision["schema"] != SCHEMA:
        return _blocked("typed_decision_schema_mismatch")
    if decision["frame_digest"] != b2.frame_digest(frame):
        return _blocked("frame_digest_mismatch")
    if type(raw_user_input) is not str or not raw_user_input.strip():
        return _blocked("raw_user_input_missing")

    status = decision["decision"]
    if status == "action":
        violations, sidecar = _action_checks(decision, frame, source_map)
        if violations:
            return _blocked(*violations, sidecar=sidecar)
        transaction = _base_transaction(frame, sources, "action")
        transaction.update(_render(decision["operation"], decision["operand_kind"]))
    elif status == "abstain":
        violations = _abstain_checks(decision, frame, source_map)
        if violations:
            return _blocked(*violations)
        transaction = _base_transaction(frame, sources, "abstain")
        transaction["reason_code"] = decision["reason_code"]
        primary, _ref = _primary_forbidden(frame)
        sidecar = {
            "typed_operation": None, "reason_code": decision["reason_code"],
            "blocker_ref": decision["blocker_ref"],
            "blocking_resource_id": decision["blocking_resource_id"],
            "blocking_constraint_id": decision["blocking_constraint_id"],
            "all_framed_forbidden_checked": False,
            "primary_forbidden_id": primary["constraint_id"] if primary else None,
            "b1_anchor_role": "primary_only_not_complete_coverage" if primary else "none",
            "b1_checks_all_forbidden": False,
            "semantic_role_checked": False, "source_omission_checked": False,
        }
    else:
        return _blocked("unknown_decision")

    guard = b1.inspect_transaction(transaction, sources, raw_user_input=raw_user_input)
    if not guard["valid_transaction"] or (status == "action" and not guard["would_deliver"]):
        return _blocked("b1_guard_rejected", sidecar=sidecar, b1_guard=guard)
    return {
        "schema": RESULT_SCHEMA, "status": f"compiled_{status}",
        "violations": [], "transaction": transaction,
        "sidecar": sidecar, "b1_guard": guard,
        "ready_for_b1_guard": True, "b1_guard_passed": True,
        "deliverable": False, "model_calls": 0, "product_runtime_changed": False,
        "semantic_role_checked": False, "source_omission_checked": False,
    }
