"""P4-BB: compile one already-authorized typed task spec into an M46 plan.

This is deliberately not a raw-dialogue understanding component.  The caller
must provide a source-exact typed spec produced and authorized elsewhere.  The
compiler accepts only six bounded, reversible templates, never calls a model,
and fails closed for unknown representations.  A compiled plan remains an
operational hypothesis, not proof that the upstream spec or advice is useful.
"""
from copy import deepcopy
import time

import uruha_actionable_help_delivery_m45 as action45
import uruha_goal_progress_delivery_m46 as m46
from rightbrain_language_quality import has_bad_language, has_japanese


LABEL = "typed_action_compiler_p4_bb"
SCHEMA = "uruha_typed_action_compiler_p4_bb"
TASK_SPEC_SCHEMA = "uruha_typed_task_spec_p4_bb"
ALLOWED_SOURCE_KINDS = {"current_user", "linked_previous_user"}
ALLOWED_SAFETY_CLASS = "low_risk_reversible"


TEMPLATE_CONTRACTS = {
    "blank_work_three_headings": {
        "progress_mechanism": "structure_scaffold",
        "evidence_roles": {"task_object", "state", "request"},
        "slots": {"work_object_jp", "scaffold_unit_jp", "count_word_jp", "unknown_constraint_jp"},
    },
    "binary_rule_two_piles": {
        "progress_mechanism": "group_by_rule",
        "evidence_roles": {"task_object", "rule", "completion"},
        "slots": {"items_jp", "left_label_jp", "right_label_jp", "unknown_constraint_jp"},
    },
    "extract_one_by_named_rule": {
        "progress_mechanism": "extract_relevant_subset",
        "evidence_roles": {"task_object", "selection_rule", "completion"},
        "slots": {"collection_jp", "selected_item_jp", "unknown_constraint_jp"},
    },
    "verify_one_named_condition": {
        "progress_mechanism": "verify_named_condition",
        "evidence_roles": {"task_object", "condition", "limit"},
        "slots": {"target_jp", "condition_jp", "unknown_constraint_jp"},
    },
    "close_one_named_obstacle": {
        "progress_mechanism": "remove_named_obstacle",
        "evidence_roles": {"task_object", "obstacle", "limit"},
        "slots": {"obstacle_jp", "unknown_constraint_jp"},
    },
    "write_one_atomic_value": {
        "progress_mechanism": "direct_atomic_completion",
        "evidence_roles": {"task_object", "value", "limit"},
        "slots": {"atomic_object_jp", "unknown_constraint_jp"},
    },
}

# Han-only strings cannot be distinguished as Japanese from Chinese by script
# alone.  This bounded compiler therefore accepts only the Han-only ontology
# entries prospectively frozen for this version; all open vocabulary must carry
# Japanese grammatical material or be handled by a later, separately tested
# task-spec producer.
_V1_HAN_ONLY_JAPANESE = {"発表資料", "決定事項", "今日の日付"}
_COUNT_WORDS = {"一つ", "二つ", "三つ"}


def _trace(status="blocked", reason="not_compiled", started=None):
    return {
        "schema": SCHEMA,
        "status": status,
        "reason": reason,
        "template_id": None,
        "progress_mechanism": None,
        "source": None,
        "evidence_atom_count": 0,
        "model_calls": 0,
        "raw_dialogue_persisted": False,
        "factual_memory_write_count": 0,
        "compile_seconds": round(time.perf_counter() - started, 8) if started else 0.0,
        "claim_boundary": (
            "already-authorized typed-spec compilation only; upstream understanding, "
            "advice usefulness, open-domain coverage, and human preference are untested"
        ),
    }


def _finish(trace, started):
    trace["compile_seconds"] = round(time.perf_counter() - started, 8)
    return trace


def _valid_japanese_slot(value):
    if not isinstance(value, str) or not value.strip() or len(value) > 140:
        return False
    if has_bad_language(value):
        return False
    if any("ぁ" <= char <= "ヿ" or char == "ー" for char in value):
        return has_japanese(value)
    return value in _V1_HAN_ONLY_JAPANESE


def _base_plan(source, spec, mechanism):
    return {
        "status": "action",
        "goal_source_id": source["id"],
        "goal_source_span": source["text"],
        "task_goal_jp": "",
        "criterion_basis": "direct_from_source",
        "progress_criterion_jp": "",
        "progress_mechanism": mechanism,
        "action_object_jp": "",
        "action_verb_jp": "",
        "action_step_jp": "",
        "expected_state_change_jp": "",
        "completion_jp": "",
        "unknown_constraint_jp": spec["slots"]["unknown_constraint_jp"],
        "instruction_jp": "",
    }


def _compile_scaffold(source, spec):
    slots = spec["slots"]
    work = slots["work_object_jp"]
    unit = slots["scaffold_unit_jp"]
    count = slots["count_word_jp"]
    plan = _base_plan(source, spec, "structure_scaffold")
    plan.update(
        task_goal_jp=f"{work}の作成を始める",
        criterion_basis="safe_proposed_criterion",
        progress_criterion_jp=f"{unit}が{count}書かれた状態",
        action_object_jp=f"{unit}を{count}",
        action_verb_jp="書く",
        action_step_jp=f"メモに{unit}を{count}だけ書く",
        expected_state_change_jp=f"{work}に最小の骨組みができる",
        completion_jp=f"{unit}を{count}書いたら止める",
        instruction_jp=f"まずメモに{unit}を{count}だけ書いて、そこで止めよ。",
    )
    return plan


def _compile_group(source, spec):
    slots = spec["slots"]
    items = slots["items_jp"]
    left = slots["left_label_jp"]
    right = slots["right_label_jp"]
    plan = _base_plan(source, spec, "group_by_rule")
    plan.update(
        task_goal_jp=f"{items}を会社名の有無で分ける",
        progress_criterion_jp=f"領収書が{left}と{right}の二群に分かれた状態",
        action_object_jp=items,
        action_verb_jp="置く",
        action_step_jp=f"{items}を、{left}は左、{right}は右に置く",
        expected_state_change_jp="領収書が会社名の有無で二群になる",
        completion_jp="全部置いたら止める",
        instruction_jp=f"{items}を、{left}は左、{right}は右に置いて、全部置いたら止めよ。",
    )
    return plan


def _compile_extract(source, spec):
    slots = spec["slots"]
    collection = slots["collection_jp"]
    item = slots["selected_item_jp"]
    plan = _base_plan(source, spec, "extract_relevant_subset")
    plan.update(
        task_goal_jp=f"{collection}から{item}を見つける",
        progress_criterion_jp=f"{item}が一つ抜き出された状態",
        action_object_jp=item,
        action_verb_jp="抜き出す",
        action_step_jp=f"{collection}から{item}を一つだけ抜き出す",
        expected_state_change_jp=f"雑談から{item}が一つ分離される",
        completion_jp="一つ抜き出したら止める",
        instruction_jp=f"{collection}から{item}を一つだけ抜き出して、そこで止めよ。",
    )
    return plan


def _compile_verify(source, spec):
    slots = spec["slots"]
    target = slots["target_jp"]
    condition = slots["condition_jp"]
    plan = _base_plan(source, spec, "verify_named_condition")
    plan.update(
        task_goal_jp=f"{target}を送信前に確認する",
        progress_criterion_jp="件名にプロジェクト名があるか確認済みの状態",
        action_object_jp=target,
        action_verb_jp="確認する",
        action_step_jp=f"{target}に{condition}か一回確認する",
        expected_state_change_jp="件名の条件が確認済みになる",
        completion_jp="一回確認したら止める",
        instruction_jp=f"まず{target}だけ見て、{condition}か一回確認したら、そこで止めよ。",
    )
    return plan


def _compile_remove(source, spec):
    obstacle = spec["slots"]["obstacle_jp"]
    plan = _base_plan(source, spec, "remove_named_obstacle")
    plan.update(
        task_goal_jp="作業画面の不要なタブを減らす",
        progress_criterion_jp=f"{obstacle}が一つ少ない状態",
        action_object_jp=obstacle,
        action_verb_jp="閉じる",
        action_step_jp=f"{obstacle}を一つ閉じる",
        expected_state_change_jp="作業画面の不要なタブが一つ減る",
        completion_jp="一つ閉じたら止める",
        instruction_jp=f"{obstacle}を一つだけ閉じて、そこで止めよ。",
    )
    return plan


def _compile_atomic(source, spec):
    obj = spec["slots"]["atomic_object_jp"]
    plan = _base_plan(source, spec, "direct_atomic_completion")
    plan.update(
        task_goal_jp=f"空欄に{obj}を入れる",
        progress_criterion_jp=f"空欄に{obj}が一つ書かれた状態",
        action_object_jp=obj,
        action_verb_jp="書く",
        action_step_jp=f"空欄に{obj}だけ書く",
        expected_state_change_jp=f"空欄が{obj}で埋まる",
        completion_jp="日付を書いたら止める",
        instruction_jp=f"まず空欄に{obj}だけ書いて、そこで止めよ。",
    )
    return plan


_COMPILERS = {
    "blank_work_three_headings": _compile_scaffold,
    "binary_rule_two_piles": _compile_group,
    "extract_one_by_named_rule": _compile_extract,
    "verify_one_named_condition": _compile_verify,
    "close_one_named_obstacle": _compile_remove,
    "write_one_atomic_value": _compile_atomic,
}


def compile_typed_action_p4_bb(source, task_spec):
    """Return ``(plan, trace)``; plan is ``None`` on every blocked path."""
    started = time.perf_counter()
    trace = _trace(started=started)
    if not isinstance(task_spec, dict):
        trace["reason"] = "missing_typed_task_spec"
        return None, _finish(trace, started)
    if not isinstance(source, dict) or source.get("kind") not in ALLOWED_SOURCE_KINDS:
        trace["reason"] = "source_kind_not_allowed"
        return None, _finish(trace, started)
    if (task_spec.get("schema") != TASK_SPEC_SCHEMA
            or task_spec.get("source_id") != source.get("id")
            or task_spec.get("source_span") != source.get("text")):
        trace["reason"] = "source_identity_mismatch"
        return None, _finish(trace, started)

    template_id = task_spec.get("template_id")
    trace["template_id"] = template_id
    contract = TEMPLATE_CONTRACTS.get(template_id)
    if not contract:
        trace["reason"] = "unsupported_template"
        return None, _finish(trace, started)
    trace["progress_mechanism"] = contract["progress_mechanism"]
    if task_spec.get("safety_class") != ALLOWED_SAFETY_CLASS:
        trace["reason"] = "safety_class_not_allowed"
        return None, _finish(trace, started)

    atoms = task_spec.get("evidence_atoms")
    if not isinstance(atoms, list) or any(not isinstance(row, dict) for row in atoms):
        trace["reason"] = "evidence_role_contract_mismatch"
        return None, _finish(trace, started)
    roles = [row.get("role") for row in atoms]
    if len(roles) != len(set(roles)) or set(roles) != contract["evidence_roles"]:
        trace["reason"] = "evidence_role_contract_mismatch"
        return None, _finish(trace, started)
    if any(not isinstance(row.get("text"), str) or not row["text"]
           or row["text"] not in source["text"] for row in atoms):
        trace["reason"] = "evidence_atom_not_exact"
        return None, _finish(trace, started)
    trace["evidence_atom_count"] = len(atoms)

    slots = task_spec.get("slots")
    if not isinstance(slots, dict) or set(slots) != contract["slots"]:
        trace["reason"] = "slot_contract_mismatch"
        return None, _finish(trace, started)
    if template_id == "blank_work_three_headings" and slots.get("count_word_jp") not in _COUNT_WORDS:
        trace["reason"] = "slot_value_not_allowed"
        return None, _finish(trace, started)
    if any(not _valid_japanese_slot(value) for value in slots.values()):
        trace["reason"] = "invalid_japanese_slot"
        return None, _finish(trace, started)

    plan = _COMPILERS[template_id](source, task_spec)
    violations = m46.structural_plan_violations(plan, [source])
    if violations:
        trace.update(reason="compiled_plan_invalid", structural_violations=violations)
        return None, _finish(trace, started)

    trace.update(
        status="compiled",
        reason="typed_template_compiled",
        source={"id": source["id"], "kind": source["kind"], "digest": action45.digest(source["text"])},
        plan_digest=action45.digest(plan),
    )
    return deepcopy(plan), _finish(trace, started)
