"""Typed emission-contract evaluator, not an independent holdout or LLM test."""
from copy import deepcopy
import hashlib
import json
from statistics import median
import time

import uruha_adaptive_person_model as adaptive
from uruha_executed_action_receipt_m44 import register_executed_action_m44, observe_executed_action_m44, STORE


def fixture(policy="share_arousal", variant="valid"):
    source = "The report is stuck again."
    digest = hashlib.sha256(source.encode()).hexdigest()[:16]
    reply = "今はここにいる。" if policy == "share_arousal" else "方法は出さずに聞くから、そのまま話して。"
    model = adaptive.empty_model()
    model["revision_count"] = 4
    model["trigger_policy_relations_m37"] = [{"schema": adaptive.TRIGGER_RELATION_SCHEMA_M37,
        "relation_id": "m44-contract-relation", "trigger_predicate": "task_stall", "response_policy": policy,
        "status": "verified", "active": True, "confidence": 0.92, "source_kind": "verified_future_response_relation",
        "source_digest": "1234567890abcdef", "created_turn": 1, "updated_turn": 2, "updated_revision": 3,
        "ttl_revisions": 48, "verification_history": {"supported": 1, "contradicted": 0, "uncertain": 0},
        "raw_dialogue_persisted": False, "private_state_truth_claimed": False}]
    match = adaptive.match_verified_trigger_relation_m37(model, source)
    decision = {"prediction_id": "m44-contract-action", "status": "applied", "utility_margin": 0.1,
        "selected": {"policy_id": policy, "expected_utility": 0.7, "response_dimensions": {}, "realization": {}},
        "state": {"turn_index": 3, "input_digest": digest, "trigger_relation_match_m37": deepcopy(match)},
        "implicit_desired_response_m26": {"status": "verified_trigger_relation_authority_bypass",
            "implicit_top_policy": "calibrate_need", "top_probability": 0.3, "probability_margin": 0.02, "evidence_quality": 0}}
    logic = {"intent": "deterministic_semantic_commit_m32", "scene": "casual",
        "semantic_route_m22": {"selected_type": "general_conversation"},
        "semantic_commit_repair_m32": {"suppresses_new_pending_prediction": True},
        "pragmatic_trigger_relation_m37": {"authoritative": True, "match": deepcopy(match)},
        "desired_response_decision_m18": decision,
        "counterfactual_pragmatic_branch_m34": {"selected_branch": {"policy_id": policy}},
        "semantic_persona_surface_verifier_m39": {"status": "repaired_and_verified", "protected_route": False,
            "policy_act_match_after": True, "unresolved_violations": [], "selected_policy_id": policy,
            "final_reply_digest": hashlib.sha256(reply.encode()).hexdigest()[:16], "source_frame": {"source_digest": digest}}}
    audit = logic["semantic_persona_surface_verifier_m39"]
    relation = model["trigger_policy_relations_m37"][0]
    if variant == "accepted": audit["status"] = "accepted_verified_surface"
    elif variant == "no_relation": model["trigger_policy_relations_m37"] = []
    elif variant == "inactive_relation": relation["active"] = False
    elif variant == "expired_relation": model["revision_count"] = 100
    elif variant == "unverified_relation": relation["status"] = "candidate"
    elif variant == "input_digest": decision["state"]["input_digest"] = "bad"
    elif variant == "reply_digest": audit["final_reply_digest"] = "bad"
    elif variant == "m39_policy": audit["selected_policy_id"] = "solve_regulation"
    elif variant == "decision_policy": decision["selected"]["policy_id"] = "solve_regulation"
    elif variant == "branch_policy": logic["counterfactual_pragmatic_branch_m34"]["selected_branch"]["policy_id"] = "solve_regulation"
    elif variant == "unresolved": audit["unresolved_violations"] = ["selected_policy_not_realized"]
    elif variant == "not_performed": audit["policy_act_match_after"] = False
    elif variant == "protected": logic["semantic_route_m22"]["selected_type"] = "safety_sensitive"
    elif variant == "factual": logic["semantic_route_m22"]["selected_type"] = "factual_or_memory"
    elif variant == "no_suppression": logic["semantic_commit_repair_m32"]["suppresses_new_pending_prediction"] = False
    elif variant == "current_ack": logic["supported_feedback_closure_m43"] = {"authoritative": True}
    elif variant == "existing_pending": model["pending_prediction"] = {"prediction_id": "other-action", "policy_id": "calibrate_need"}
    elif variant == "resolved_ledger": model["outcome_calibration_ledger_m27"] = [{"prediction_id": decision["prediction_id"], "result_status": "supported"}]
    elif variant == "stale_cycle": decision["state"]["turn_index"] = 1
    elif variant == "empty_reply": reply = ""
    elif variant != "valid": raise ValueError(variant)
    return model, logic, source, reply, 3


def evaluate_cases(cases):
    rows = []
    for case in cases:
        model, logic, source, reply, turn = fixture(case["policy"], case["variant"])
        originals = deepcopy((model, logic, source, reply))
        new, trace = register_executed_action_m44(model, logic, source, reply, turn)
        registered = trace["status"] == "registered_for_next_user_turn"
        target = case.get("next_outcome")
        next_text = {"supported": "その通り、ありがとう。", "contradicted": "You misunderstood; give me one practical step I can take now.", "uncertain": "The package arrives tomorrow."}.get(target)
        baseline_feedback = system_feedback = None
        if next_text:
            _, baseline_feedback = observe_executed_action_m44(model, next_text, turn_index=4)
            _, system_feedback = observe_executed_action_m44(new, next_text, turn_index=4)
        rows.append({"case_id": case["id"], "expected_registration": case["expected_registration"],
            "registered": registered, "registration_correct": registered == case["expected_registration"],
            "baseline_registered": bool(model.get("pending_prediction")) if case["expected_registration"] else False,
            "arguments_unchanged": originals == (model, logic, source, reply),
            "non_registration_state_unchanged": registered or new == model,
            "relation_unchanged": new.get("trigger_policy_relations_m37") == model.get("trigger_policy_relations_m37"),
            "old_ledger_preserved": new.get("outcome_calibration_ledger_m27", [])[:len(model.get("outcome_calibration_ledger_m27", []))] == model.get("outcome_calibration_ledger_m27", []),
            "raw_trace_or_store": any(text and text in json.dumps([trace, new], ensure_ascii=False) for text in (source, reply, next_text)),
            "expected_next_outcome": target, "baseline_feedback_status": (baseline_feedback or {}).get("status"),
            "system_feedback_status": (system_feedback or {}).get("status"),
            "system_feedback_linked": bool((system_feedback or {}).get("feedback_linked_to_previous_prediction")),
            "outcome_correct": target is None or (system_feedback or {}).get("status") == target,
            "trace": trace})
    costs = sorted(r["trace"]["added_seconds"] for r in rows)
    gates = {"registration_all_correct": all(r["registration_correct"] for r in rows),
        "false_registration_zero": not any(r["registered"] and not r["expected_registration"] for r in rows),
        "upstream_and_unrelated_preserved": all(r["arguments_unchanged"] and r["non_registration_state_unchanged"] and r["relation_unchanged"] and r["old_ledger_preserved"] for r in rows),
        "outcomes_correct": all(r["outcome_correct"] for r in rows),
        "no_raw_or_mental_facts": not any(r["raw_trace_or_store"] or r["trace"]["mental_fact_write_count"] for r in rows),
        "no_implicit_calibration_inflation": not any(r["trace"].get("eligible_for_implicit_calibration") for r in rows),
        "no_added_model_calls": not any(r["trace"]["added_model_calls"] for r in rows)}
    return {"schema": "uruha_m44_contract_result_v1", "status": "PASS" if all(gates.values()) else "FAIL",
        "scope": "author-written supplied-emission contracts; not upstream truth, LLM superiority or human ratings",
        "gates": gates, "summary": {"cases": len(rows), "registration_correct": sum(r["registration_correct"] for r in rows),
            "baseline_registration_correct": sum(not r["expected_registration"] for r in rows),
            "positive_registered": sum(r["registered"] and r["expected_registration"] for r in rows),
            "positive_total": sum(r["expected_registration"] for r in rows),
            "median_added_seconds": median(costs), "p95_added_seconds": costs[min(len(costs)-1, int(0.95*len(costs)))]}, "rows": rows}
