"""Reconstruct the frozen A two-stage observation from raw model responses.

This is an isolated, zero-call component approximation, not Web delivery.  It
does not read gold, trust caller-supplied acceptance flags, or infer semantic
validity from the reviewer's self-report.  Only a separately locked annotation
can establish the latter in the paired scorer.
"""

from __future__ import annotations

from copy import deepcopy

from jsonschema import Draft202012Validator

import p4_action_transaction_scoring as tx
import p4_m46_reviewer_necessity_scoring as legacy
import uruha_actionable_help_delivery_m45 as m45
import uruha_candidate_realization_m52 as m52
import uruha_goal_progress_delivery_m46 as m46
import uruha_semantic_persona_surface_m39 as m39
import uruha_state_changing_candidates_m51 as m51
import uruha_task_evidence_authorization_m45_1 as task_gate


# The old review has no explicit prohibition/private-inference reason field.
# A false check may only be translated where its meaning is sufficiently
# narrow.  Conflicting categories and all other failures remain unknown.
_REVIEW_REASONS = {
    "goal_matches_source": "wrong_task",
    "criterion_is_observable": "non_action",
    "action_changes_task_state": "non_action",
    "action_is_operationally_specific": "non_action",
    "effect_links_action_to_criterion": "non_action",
    "not_random_or_task_relabeling": "non_action",
    "no_invented_facts": "source_grounding",
    "no_unknown_prerequisites": "prerequisites",
    "casual_japanese": "natural_japanese",
    "completion_is_visible": "stop_visible",
    "no_identity_or_role_error": "actor_capability",
    "review_source_id_mismatch": "source_grounding",
    "review_source_span_mismatch": "source_grounding",
    "review_observed_nonprogress_mechanism": "non_action",
}
_GUARD_REASONS = {
    "invalid_exact_goal_source": "source_grounding",
    "unsupported_concrete_scaffold_label_m53": "unsupported_specificity",
    "noncasual_register": "natural_japanese",
    "instruction_missing_visible_stop": "stop_visible",
    "nonprogress_or_unknown_mechanism": "non_action",
    "criterion_only_relabels_goal": "non_action",
    "action_only_relabels_goal": "non_action",
    "unspecified_action_object": "non_action",
    "instruction_missing_action_object": "non_action",
    "plan_missing_action_verb": "non_action",
}


def _reason(violations: list[str], mapping: dict[str, str]) -> str:
    if not violations or any(item not in mapping for item in violations):
        return "unknown_reason"
    codes = {mapping[item] for item in violations}
    return next(iter(codes)) if len(codes) == 1 else "unknown_reason"


def _prepared(case: object) -> list[dict]:
    """Check that each filtered clause is an exact slice of the *full* input."""

    tx.require_isolated_m45_1_source_filter()
    if not isinstance(case, dict) or type(case.get("case_id")) is not str:
        raise ValueError("A requires a prepared source case")
    raw = case.get("raw_user_input")
    if type(raw) is not str or not raw.strip() or len(raw) > 2000:
        raise ValueError("A requires the complete bounded raw_user_input")
    if (case.get("policy_fixed_not_product_routed") is not True
            or case.get("logic") != tx.FIXED_COMPONENT_LOGIC):
        raise ValueError("A requires the common fixed policy fixture")
    sources = tx._allowed_sources(case.get("sources"))
    gate = case.get("source_gate")
    if (not isinstance(gate, dict) or gate.get("status") != "content_available"
            or gate.get("allowed_clause_count") != len(sources)
            or gate.get("allowed_origins") != [row.get("origin") for row in sources]):
        raise ValueError("A requires the prepared M45.1 source gate")
    for source in sources:
        origin = source.get("origin")
        if (source.get("kind") != "current_user" or not isinstance(origin, dict)
                or type(origin.get("source_id")) is not str
                or type(origin.get("span_start")) is not int
                or type(origin.get("span_length")) is not int
                or origin["span_start"] < 0
                or origin["span_length"] != len(source["text"])
                or raw[origin["span_start"]:origin["span_start"] + origin["span_length"]] != source["text"]
                or origin.get("source_digest") != m45.digest(raw)
                or origin.get("span_digest") != m45.digest(source["text"])):
            raise ValueError("A source is not exact in the complete raw input")
    original_ids = {row["origin"]["source_id"] for row in sources}
    if len(original_ids) != 1:
        raise ValueError("A requires one original current-user source")
    filtered_again, gate_again = task_gate.task_sources([
        {"id": next(iter(original_ids)), "kind": "current_user", "text": raw}
    ])
    if filtered_again != sources or gate_again != gate:
        raise ValueError("A sources differ from the M45.1 prefilter")
    return sources


def _stage(record: dict | None) -> dict | None:
    if record is None:
        return None
    if not isinstance(record, dict):
        raise TypeError("raw stage record must be a dictionary")
    raw = record.get("raw_content")
    prompt_tokens = record.get("prompt_tokens")
    completion_tokens = record.get("completion_tokens")
    parsed = tx.parse_transaction_json(raw)
    return {
        "stage": record.get("stage"),
        "attempted": True,
        "raw_content": raw,
        "raw_content_digest": m45.digest(str(raw)),
        "json_ok": parsed is not None,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "tokens_complete": tx._valid_usage(prompt_tokens, completion_tokens),
        "request_body": deepcopy(record.get("request_body")),
        "options": deepcopy(record.get("options")),
        "wall_seconds": record.get("wall_seconds"),
        "model_digest": record.get("model_digest"),
        "http_identity": deepcopy(record.get("http_identity")),
        "transport_metadata": deepcopy(record.get("transport_metadata")),
        "parsed": parsed,
    }


def _source_pair_exact(batch: dict, sources: list[dict]) -> bool:
    return any(batch.get("sid") == source["id"] and batch.get("span") == source["text"]
               for source in sources)


def _review_source_exact(review: dict, plan: dict) -> bool:
    return (type(review.get("source_id")) is str
            and type(review.get("source_span")) is str
            and review["source_id"] == plan["goal_source_id"]
            and review["source_span"] == plan["goal_source_span"])


def build_a_observation(
    case: dict,
    generator_stage_record: dict,
    *,
    full_turn_seconds: object,
    reviewer_stage_record: dict | None = None,
    retries: object = 0,
) -> dict:
    """Build one A observation; the only acceptance input is raw JSON.

    A stage record carries original ``raw_content``, token usage, request_body,
    options, stage wall, model digest, and HTTP identity. ``reviewer_stage_record=None``
    means no review call. An empty raw_content denotes an attempted call with
    invalid JSON. Metadata is retained for audit but cannot grant acceptance;
    transport identity and measured wall values are the runner's responsibility.
    """

    legacy._require_isolated_modules()
    sources = _prepared(case)
    gen = _stage(generator_stage_record)
    if gen is None:
        raise ValueError("A requires a generator stage record")
    rev = _stage(reviewer_stage_record)
    review_attempted = rev is not None
    usage_stages = [gen, rev] if rev is not None else [gen]
    tokens_complete = all(stage["tokens_complete"] is True for stage in usage_stages)
    token_budget_ok = bool(
        tokens_complete and gen["completion_tokens"] <= 360
        and (rev is None or rev["completion_tokens"] <= 320)
    )
    stage_wall_complete = bool(
        tx._valid_seconds(full_turn_seconds)
        and all(tx._valid_seconds(stage["wall_seconds"]) for stage in usage_stages)
    )
    stage_wall_within_full_turn = bool(
        stage_wall_complete
        and all(stage["wall_seconds"] <= full_turn_seconds for stage in usage_stages)
        and sum(stage["wall_seconds"] for stage in usage_stages) <= full_turn_seconds + 0.01
    )
    gen_parsed = gen["parsed"]
    rev_parsed = rev["parsed"] if rev is not None else None
    gen_contract = bool(gen_parsed is not None and Draft202012Validator(
        m51._candidate_schema(sources)).is_valid(gen_parsed))
    gen_source = bool(gen_parsed is not None and _source_pair_exact(gen_parsed, sources))
    selection = None
    plan = None
    label_audit = None
    m39_trace = None
    m39_exact = False
    review_audit = None
    review_contract = None
    review_source = None
    guard: list[str] = []
    failure = "none"
    review_eligible = False

    if gen_parsed is None:
        failure = "generator_parse"
    elif not gen_source:
        failure = "generator_source"
        guard.append("invalid_exact_goal_source")
    elif not gen_contract:
        failure = "generator_contract"
    else:
        # M52 must select the exact same plan before either audit arm sees it.
        plan, selection = m52.select_candidate_batch_m52(deepcopy(gen_parsed), sources)
        guard, label_audit = legacy._guard(plan, sources)
        guarded_index = legacy._guarded_selection_index(gen_parsed, sources, selection)
        if guarded_index != selection["selected_index"]:
            guard.append("selection_guard_parity_mismatch")
        instruction = plan.get("instruction_jp")
        final, m39_trace = m39.verify_and_repair_surface_m39(
            case["raw_user_input"], instruction, tx.FIXED_COMPONENT_LOGIC)
        m39_exact = bool(m39_trace.get("action") == "accept" and final == instruction)
        if not m39_exact:
            guard.append("m39_surface_not_exactly_accepted")
        guard = sorted(set(guard))
        if guard:
            failure = "selection_guard"
        else:
            review_eligible = True
        if review_eligible and not review_attempted:
            failure = "review_missing"
        elif review_eligible and rev_parsed is None:
            failure = "review_parse"
        elif review_eligible:
            review_source = _review_source_exact(rev_parsed, plan)
            review_contract = Draft202012Validator(
                m46.review_schema(sources, plan)).is_valid(rev_parsed)
            if not review_source:
                failure = "review_source"
                guard.append("review_source_mismatch")
            elif not review_contract:
                failure = "review_contract"
            else:
                review_audit = m46.inspect_goal_progress(plan, sources, rev_parsed)
                if not (review_audit["content_passed"] is True
                        and review_audit["surface_passed"] is True):
                    failure = "review_reject"

    if review_attempted and failure in {
            "generator_parse", "generator_source", "generator_contract", "selection_guard"}:
        guard = sorted(set(guard + ["unexpected_reviewer_after_upstream_failure"]))

    accounting_violations = []
    if not tokens_complete:
        accounting_violations.append("stage_token_accounting_incomplete")
    elif not token_budget_ok:
        accounting_violations.append("stage_completion_token_budget_exceeded")
    if not stage_wall_within_full_turn:
        accounting_violations.append("stage_wall_not_within_full_turn")
    if accounting_violations:
        guard = sorted(set(guard + accounting_violations))
        if failure == "none":
            failure = "accounting_guard"

    required_review = review_eligible
    # Missing review after a valid plan is an incomplete *two-stage* JSON
    # observation. A deterministic reject requires no reviewer JSON.
    json_ok = bool(gen["json_ok"] and (not required_review or rev is not None)
                   and (rev is None or rev["json_ok"]))
    json_contract_ok = bool(gen_contract and (not required_review or review_contract is True)
                            and (review_eligible or not review_attempted))
    source_exact = bool(gen_source and (not required_review or review_source is True))
    prompt_tokens = (sum(stage["prompt_tokens"] for stage in usage_stages)
                     if tokens_complete else None)
    completion_tokens = (sum(stage["completion_tokens"] for stage in usage_stages)
                         if tokens_complete else None)
    deliver = failure == "none" and not guard and review_audit is not None
    if deliver:
        reason = "none"
    elif failure == "review_reject" and review_audit is not None:
        reason = _reason(review_audit["content_violations"]
                         + review_audit["surface_violations"], _REVIEW_REASONS)
    elif failure == "review_source":
        reason = "source_grounding"
    elif failure == "generator_source":
        reason = "source_grounding"
    elif guard:
        reason = _reason(guard, _GUARD_REASONS)
    else:
        reason = "unknown_reason"
    raw_stage_records = {
        "generator": {key: deepcopy(value) for key, value in gen.items() if key != "parsed"},
        "reviewer": ({key: deepcopy(value) for key, value in rev.items() if key != "parsed"}
                     if rev is not None else None),
    }
    return {
        "arm": "A_two_stage",
        "decision": "action" if deliver else "abstain",
        "failure_stage": failure,
        "reason_code": reason,
        "json_ok": json_ok,
        "json_contract_ok": json_contract_ok,
        "source_exact": source_exact,
        "tokens_complete": tokens_complete,
        "token_budget_ok": token_budget_ok,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "retries": retries,
        "full_turn_seconds": full_turn_seconds,
        "guard_violations": guard,
        "instruction_jp": plan["instruction_jp"] if deliver else None,
        "fallback_kind": None if deliver else "unavailable",
        "fallback_reply_jp": None if deliver else tx._fallback_reply("unavailable"),
        "raw_stage_records": raw_stage_records,
        "raw_stage_records_digest": m45.digest(raw_stage_records),
        "stage_wall_complete": stage_wall_complete,
        "stage_wall_within_full_turn": stage_wall_within_full_turn,
        "source_digest": m45.digest(sources),
        "raw_user_input_digest": m45.digest(case["raw_user_input"]),
        "generator_packet": deepcopy(gen_parsed),
        "m52_selection": deepcopy(selection),
        "selected_plan": deepcopy(plan),
        "selected_plan_digest": m45.digest(plan) if plan is not None else None,
        "label_authorization": deepcopy(label_audit),
        "m39_surface_trace": deepcopy(m39_trace),
        "m39_final_byte_identical": m39_exact,
        "review_packet": deepcopy(rev_parsed),
        "review_audit": deepcopy(review_audit),
        "review_schema_ok": review_contract,
        "review_source_exact": review_source,
        "model_calls_by_builder": 0,
        "semantic_gold_checked": False,
        "human_validated": False,
        "product_runtime_changed": False,
    }
