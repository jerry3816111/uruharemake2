"""Offline paired scorer for the M46 reviewer-necessity experiment.

Both decisions use one frozen M51 packet and one M52-selected plan.  This
module makes no model calls, installs no product overlays, and never delivers
an utterance.  A supplied review is an observed input, not a substitute for
an actual M46 model call in the formal runner.  It applies M39 to the selected
instruction as an isolated common guard; this is not the full M45/Web pipeline.
"""

from __future__ import annotations

from copy import deepcopy

import uruha_actionable_help_delivery_m45 as m45
import uruha_candidate_realization_m52 as m52
import uruha_goal_progress_delivery_m46 as m46
import uruha_neutral_operational_role_authorization_p4 as p4_av
import uruha_semantic_persona_surface_m39 as m39
import uruha_source_neutral_scaffold_m53 as m53
import uruha_state_changing_candidates_m51 as m51


def _require_isolated_modules() -> None:
    """Fail closed if a Web import has installed process-global overlays."""

    if (m46.structural_plan_violations.__module__ != m46.__name__
            or m46.inspect_goal_progress.__module__ != m46.__name__
            or m51.select_candidate_batch is not m52._PREVIOUS_SELECT
            or m53.authorize_named_scaffold_m53 is not p4_av._ORIGINAL_AUTHORIZE_P4_AV):
        raise RuntimeError("M46 ablation scorer requires an isolated, uninstalled process")


def _guard(plan: dict, sources: list[dict]) -> tuple[list[str], dict]:
    structural = list(m46.structural_plan_violations(plan, sources))
    labels = p4_av.authorize_neutral_operational_roles_p4_av(plan, sources)
    if labels["unsupported_count"]:
        structural.append("unsupported_concrete_scaffold_label_m53")
    return sorted(set(structural)), labels


def _guarded_selection_index(batch: dict, sources: list[dict], state: dict) -> int:
    """Detect when the uninstalled M52 selector differs from M53-aware selection.

    Product M53 adds a structural violation before M51 chooses a candidate.
    Rather than mutating global functions to simulate that overlay, a parity
    mismatch makes both offline decisions ineligible.
    """

    rows = []
    for index, item in enumerate(batch["items"]):
        realized, _ = m52.realize_candidate_m52(item)
        plan = m51._as_plan(batch, realized)
        violations, _ = _guard(plan, sources)
        if "duplicate_candidate" in state["candidates"][index]["violations"]:
            violations = sorted(set(violations + ["duplicate_candidate"]))
        rows.append(violations)
    return next((index for index, violations in enumerate(rows) if not violations),
                min(range(len(rows)), key=lambda index: len(rows[index])))


def _arm_score(would_deliver: bool, gold_label: str) -> dict:
    return {
        "would_deliver": would_deliver,
        "false_action": would_deliver and gold_label != "valid",
        "valid_retained": would_deliver and gold_label == "valid",
        "valid_retention_denominator": gold_label == "valid",
        "uncertain_action_risk": would_deliver and gold_label == "uncertain",
    }


def score_packet(source: dict, batch: dict, review: dict | None,
                 gold_label: str | bool) -> dict:
    """Score A/B on one identical, already-generated M51 source+batch packet.

    ``gold_label`` is an independently supplied label for the selected plan;
    this function neither creates nor validates that label.  A missing review
    always fails A.  B is a counterfactual *offline* decision, never an
    instruction to bypass the live reviewer.  Boolean labels are accepted only
    for compact fake fixtures; formal evidence should use valid/invalid/uncertain.
    """

    if not isinstance(source, dict) or not isinstance(batch, dict):
        raise TypeError("source and batch must be dictionaries")
    if review is not None and not isinstance(review, dict):
        raise TypeError("review must be a dictionary or None")
    if type(gold_label) is bool:
        gold_label = "valid" if gold_label else "invalid"
    if not isinstance(gold_label, str):
        raise TypeError("gold_label must be an independent string label or boolean fixture")
    if gold_label not in {"valid", "invalid", "uncertain"}:
        raise ValueError("gold_label must be valid, invalid, or uncertain")
    _require_isolated_modules()

    source_copy = deepcopy(source)
    batch_copy = deepcopy(batch)
    sources = [source_copy]
    plan, selection = m52.select_candidate_batch_m52(batch_copy, sources)
    violations, label_audit = _guard(plan, sources)
    guarded_index = _guarded_selection_index(batch_copy, sources, selection)
    selector_parity = guarded_index == selection["selected_index"]
    if not selector_parity:
        violations = sorted(set(violations + ["selection_guard_parity_mismatch"]))
    m39_reply, m39_trace = m39.verify_and_repair_surface_m39(
        source_copy.get("text"), plan.get("instruction_jp"),
        {"desired_response_policy_m18": "solve_regulation"},
    )
    m39_exact_accept = bool(
        m39_trace.get("action") == "accept"
        and m39_reply == plan.get("instruction_jp")
    )
    if not m39_exact_accept:
        violations = sorted(set(violations + ["m39_surface_not_exactly_accepted"]))
    deterministic_eligible = not violations

    review_audit = (
        m46.inspect_goal_progress(deepcopy(plan), sources, deepcopy(review))
        if review is not None else None
    )
    review_passed = bool(
        review_audit
        and review_audit["content_passed"] is True
        and review_audit["surface_passed"] is True
    )
    arm_b = _arm_score(deterministic_eligible, gold_label)
    arm_a = _arm_score(deterministic_eligible and review_passed, gold_label)
    return {
        "schema": "uruha_p4_m46_reviewer_necessity_component_score_v1",
        "source_id": source_copy.get("id"),
        "source_digest": m45.digest(source_copy.get("text")),
        "selected_plan": deepcopy(plan),
        "selected_plan_digest": m45.digest(plan),
        "selected_fingerprint": selection["selected_fingerprint"],
        "selected_index": selection["selected_index"],
        "m53_aware_selected_index": guarded_index,
        "selection_guard_parity": selector_parity,
        "m52_selection": deepcopy(selection),
        "guard_violations": violations,
        "label_authorization": label_audit,
        "m39_surface_trace": m39_trace,
        "m39_final_byte_identical": m39_reply == plan.get("instruction_jp"),
        "deterministic_eligible": deterministic_eligible,
        "review_supplied": review is not None,
        "review_audit": review_audit,
        "gold_label": gold_label,
        "arms": {"A_model_review": arm_a, "B_deterministic_only": arm_b},
        "incremental_review_informative": deterministic_eligible,
        "model_calls_by_scorer": 0,
        "product_runtime_changed": False,
        "claim_boundary": (
            "Offline M51/M52/M46/M53/P4-AV plus isolated M39 surface "
            "approximation; not full M45 runtime, Safari, or human usefulness."
        ),
    }
