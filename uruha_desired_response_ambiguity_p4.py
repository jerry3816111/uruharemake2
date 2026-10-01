"""P4-AD additive shadow ledger for competing desired-response hypotheses.

The ledger reorganizes existing M18/M23 evidence.  It never treats an action
ranking as a probability of private mental truth, never changes the reply, and
adds no model call or memory write.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path

import uruha_adaptive_person_model as adaptive
import uruha_functional_understanding as functional
import uruha_personhood_loop as personhood


LABEL = "desired_response_ambiguity_ledger_p4"
SCHEMA = "uruha_desired_response_ambiguity_ledger_p4"
ACTION_SCORE_SEMANTICS = "operational_action_ranking_not_private_truth_probability"

_POLICY_ATOMS = {
    "care_physiology": ("sleep_debt", "physical_strain"),
    "solve_regulation": ("solution_request",),
    "listen_presence": ("listening_request",),
    "share_arousal": ("companionship_request", "positive_arousal"),
    "playful_tease": ("humor_invitation", "relationship_familiarity"),
    "calibrate_need": ("uncertainty",),
}


def _digest(value):
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def _epistemic_status(atom):
    status = str((atom or {}).get("status") or "unknown")
    evidence = str((atom or {}).get("evidence") or "")
    if status.startswith("explicit_") or evidence == "current_turn_visible_cue":
        return "current_visible_evidence"
    if "verified" in status or status.startswith("learned_") or "verified" in evidence:
        return "verified_reversible_history"
    if status == "unknown":
        return "unknown_no_decisive_evidence"
    return "provisional_operational_inference"


def _evidence_rows(state, policy_id):
    atoms = (state or {}).get("atoms") or {}
    rows = []
    for atom_name in _POLICY_ATOMS.get(policy_id, ()):
        atom = deepcopy(atoms.get(atom_name) or {})
        rows.append(
            {
                "evidence_id": f"atom:{atom_name}",
                "source_path": f"desired_response_state_m18.atoms.{atom_name}",
                "atom": atom_name,
                "value": round(float(atom.get("value") or 0.0), 4),
                "confidence": round(float(atom.get("confidence") or 0.0), 4),
                "source_status": str(atom.get("status") or "unknown"),
                "epistemic_status": _epistemic_status(atom),
                "raw_evidence_persisted": False,
            }
        )
    return rows


def _candidate_row(candidate, state, selected_policy, explicit_policy):
    policy_id = str((candidate or {}).get("policy_id") or "")
    mode = adaptive.POLICY_TO_RESPONSE_MODE_M23.get(policy_id)
    evidence = _evidence_rows(state, policy_id)
    explicit = bool(explicit_policy and policy_id == explicit_policy)
    return {
        "policy_id": policy_id,
        "mode": mode,
        "operational_action_score": round(
            float((candidate or {}).get("expected_utility") or 0.0), 4
        ),
        "score_semantics": ACTION_SCORE_SEMANTICS,
        "action_selected": policy_id == selected_policy,
        "selected_as_private_truth": False,
        "epistemic_status": (
            "current_explicit_response_form"
            if explicit
            else "competing_action_hypothesis"
        ),
        "support_evidence": evidence,
        "verification_contract": {
            "supporting_outcome": "next_turn_explicit_acceptance_of_same_response_mode",
            "contradicting_outcome": "next_turn_explicit_rejection_or_different_response_mode",
            "unknown_outcome": "topic_change_or_unlinked_reply",
            "unknown_counts_as_success": False,
        },
        "long_term_fact_write_allowed": False,
        "raw_dialogue_persisted": False,
    }


def _candidate_contract_passed(candidates):
    return bool(candidates) and all(
        row.get("mode")
        and row.get("score_semantics") == ACTION_SCORE_SEMANTICS
        and row.get("selected_as_private_truth") is False
        and (row.get("verification_contract") or {}).get("unknown_counts_as_success") is False
        and row.get("long_term_fact_write_allowed") is False
        and row.get("raw_dialogue_persisted") is False
        for row in candidates
    )


def _activate_from_existing_observable_trigger(state, decision, mode_contract):
    """Bridge one already-typed observable signal into the shadow ledger.

    This does not change the released M18 decision.  It only repairs the
    initial P4-AD failure where M37 had already found cognitive overactivity,
    while the older lexical pragmatic label left the desired-response path
    inactive for some multilingual paraphrases.
    """

    state = deepcopy(state or {})
    decision = deepcopy(decision or {})
    mode_contract = deepcopy(mode_contract or {})
    if (
        state.get("active")
        and decision.get("status") == "applied"
        and mode_contract.get("eligible")
    ):
        return state, decision, mode_contract, "existing_upstream_path"
    trigger = deepcopy(state.get("observable_trigger_m37") or {})
    predicates = set(trigger.get("predicates") or [])
    bounded_trigger = bool(
        trigger.get("status") in {
            "single_observable_trigger",
            "multiple_observable_triggers",
        }
        and "cognitive_overactivity" in predicates
        and trigger.get("private_state_truth_claimed") is False
    )
    if not bounded_trigger:
        return state, decision, mode_contract, "not_applicable"
    shadow_state = deepcopy(state)
    shadow_state["active"] = True
    shadow_state["activation_reasons"] = list(
        dict.fromkeys(
            [
                *(shadow_state.get("activation_reasons") or []),
                "p4_ad_existing_observable_cognitive_overactivity_shadow",
            ]
        )
    )
    uncertainty = deepcopy(
        ((shadow_state.get("atoms") or {}).get("uncertainty")) or {}
    )
    uncertainty.update(
        {
            "value": max(0.86, float(uncertainty.get("value") or 0.0)),
            "confidence": max(0.86, float(uncertainty.get("confidence") or 0.0)),
            "status": "bounded_observable_trigger_inference",
            "evidence": "observable_trigger_m37:cognitive_overactivity",
        }
    )
    shadow_state.setdefault("atoms", {})["uncertainty"] = uncertainty
    shadow_decision = adaptive.decide_response(shadow_state, adaptive.empty_model())
    shadow_mode = adaptive.build_desired_response_mode_contract(
        {"selected_type": "emotional_bid"},
        shadow_state,
        shadow_decision,
    )
    return (
        shadow_state,
        shadow_decision,
        shadow_mode,
        "existing_observable_trigger_shadow",
    )


def build_desired_response_ambiguity_ledger_p4(
    state,
    decision,
    mode_contract,
):
    """Build a raw-free ledger from existing deterministic runtime evidence."""

    state = deepcopy(state or {})
    decision = deepcopy(decision or {})
    mode_contract = deepcopy(mode_contract or {})
    state, decision, mode_contract, activation_basis = (
        _activate_from_existing_observable_trigger(
            state,
            decision,
            mode_contract,
        )
    )
    eligible = bool(
        state.get("active")
        and mode_contract.get("eligible")
        and decision.get("status") == "applied"
    )
    selected_policy = str((decision.get("selected") or {}).get("policy_id") or "")
    selected_mode = adaptive.POLICY_TO_RESPONSE_MODE_M23.get(selected_policy)
    explicit_request = deepcopy(decision.get("explicit_desired_response_m25") or {})
    correction = deepcopy(decision.get("correction_aware_surface_m20") or {})
    explicit_policy = ""
    if correction.get("authoritative"):
        explicit_policy = str(correction.get("selected_repair_policy") or selected_policy)
    elif explicit_request.get("authoritative"):
        explicit_policy = str(explicit_request.get("selected_policy") or selected_policy)
    candidates = (
        [
            _candidate_row(row, state, selected_policy, explicit_policy)
            for row in (decision.get("candidates") or [])
            if adaptive.POLICY_TO_RESPONSE_MODE_M23.get(str(row.get("policy_id") or ""))
        ]
        if eligible
        else []
    )
    status = (
        "explicit_response_form_observed"
        if eligible and explicit_policy
        else "ambiguity_preserved"
        if eligible
        else "not_applicable"
    )
    private_reason_status = (
        "unknown_beyond_explicit_response_form"
        if eligible and explicit_policy
        else "unknown_not_observed"
        if eligible
        else "not_applicable"
    )
    evidence_by_id = {}
    for candidate in candidates:
        for evidence in candidate["support_evidence"]:
            evidence_by_id[evidence["evidence_id"]] = evidence
    trigger = deepcopy(state.get("observable_trigger_m37") or {})
    if eligible and "cognitive_overactivity" in set(trigger.get("predicates") or []):
        evidence_by_id["observable_trigger_m37:cognitive_overactivity"] = {
            "evidence_id": "observable_trigger_m37:cognitive_overactivity",
            "source_path": "desired_response_state_m18.observable_trigger_m37",
            "predicate": "cognitive_overactivity",
            "matched_languages": list(trigger.get("matched_languages") or []),
            "epistemic_status": "current_visible_evidence",
            "private_state_truth_claimed": False,
            "raw_evidence_persisted": False,
        }
    return {
        "schema": SCHEMA,
        "status": status,
        "mode": "shadow_only",
        "activation_basis": activation_basis,
        "input_digest": str(state.get("input_digest") or "")[:64],
        "selected_action": {
            "policy_id": selected_policy if eligible else None,
            "mode": selected_mode if eligible else None,
            "selection_is_operational_action": bool(eligible),
            "selection_is_private_truth_commitment": False,
        },
        "private_reason_status": private_reason_status,
        "observable_evidence": list(evidence_by_id.values()),
        "candidate_expectations": candidates,
        "candidate_contract_passed": _candidate_contract_passed(candidates) if eligible else False,
        "unknown_space": (
            [
                "private_reason_for_the_utterance",
                "which_response_will_feel_best_before_outcome",
                "whether_the_selected_action_will_be_accepted",
            ]
            if eligible
            else []
        ),
        "outcome_labels": ["supported", "contradicted", "unknown"],
        "unknown_counts_as_success": False,
        "candidate_action_score_is_private_truth_probability": False,
        "selected_action_is_private_truth_commitment": False,
        "candidate_count": len(candidates),
        "raw_dialogue_persisted": False,
        "model_call_added": False,
        "fact_write_count": 0,
        "profile_write_count": 0,
        "episode_write_count": 0,
        "claim_boundary": (
            "competing desired-response action hypotheses with falsification; "
            "not the user's true private desire, mind reading or human understanding"
        ),
    }


def shadow_visible_reply_p4(reply, state, decision, mode_contract):
    visible = str(reply or "")
    return visible, build_desired_response_ambiguity_ledger_p4(
        state,
        decision,
        mode_contract,
    )


def append_desired_response_ambiguity_node_p4(result, trace=None):
    result = result or {}
    logic = result.get("logic") or {}
    payload = deepcopy(trace or logic.get(LABEL) or {})
    if not payload:
        return result
    logic[LABEL] = payload
    result["logic"] = logic
    runtime_trace = result.get("runtime_trace") or {}
    blackboard = [
        row
        for row in (runtime_trace.get("blackboard") or [])
        if row.get("label") != LABEL
    ]
    insert_at = next(
        (index for index, row in enumerate(blackboard) if row.get("label") == "utterance"),
        len(blackboard),
    )
    blackboard.insert(
        insert_at,
        {
            "stage": "select",
            "label": LABEL,
            "payload": payload,
            "salience": 0.98 if payload.get("status") != "not_applicable" else 0.62,
        },
    )
    runtime_trace["blackboard"] = blackboard
    runtime_trace[LABEL] = payload
    result["runtime_trace"] = runtime_trace
    return result


_INSTALLED_P4_AD = False
_ORIGINAL_EMIT_RESPONSE_P4_AD = None


def install_desired_response_ambiguity_p4():
    global _INSTALLED_P4_AD, _ORIGINAL_EMIT_RESPONSE_P4_AD
    if _INSTALLED_P4_AD:
        return False
    from uruha_brain_mac import UruhaBrainV4_Mac

    _ORIGINAL_EMIT_RESPONSE_P4_AD = UruhaBrainV4_Mac.emit_response_if_ready

    def emit_with_p4_ad(self, event, tick_result):
        result = _ORIGINAL_EMIT_RESPONSE_P4_AD(self, event, tick_result)
        runtime = (result or {}).get("runtime_trace") or {}
        logic = (result or {}).get("logic") or {}
        state = (
            runtime.get("desired_response_state_m18")
            or logic.get("desired_response_state_m18")
            or {}
        )
        decision = (
            runtime.get("desired_response_decision_m18")
            or logic.get("desired_response_decision_m18")
            or {}
        )
        mode_contract = (
            logic.get("desired_response_mode_m23")
            or runtime.get("desired_response_mode_m23")
            or {}
        )
        reply, trace = shadow_visible_reply_p4(
            (result or {}).get("reply"),
            state,
            decision,
            mode_contract,
        )
        result["reply"] = reply
        result = append_desired_response_ambiguity_node_p4(result, trace)
        if getattr(self.runtime, "turn_traces", None):
            self.runtime.turn_traces[-1] = deepcopy(result["runtime_trace"])
        return result

    UruhaBrainV4_Mac.emit_response_if_ready = emit_with_p4_ad
    _INSTALLED_P4_AD = True
    return True


def _isolated_inputs(user_input, turn_index):
    hypothesis = functional.build_user_mental_state_hypothesis(
        user_input,
        actual_signal={"actual_intent": "chat", "actual_valence": 0.0},
        appraisal={},
        attention_frame={},
        turn_index=turn_index,
        calibration_state={},
    )
    pragmatic = personhood.build_human_pragmatic_understanding(
        user_input,
        hypothesis=hypothesis,
        turn_index=turn_index,
    )
    state = adaptive.build_current_state(
        user_input,
        pragmatic,
        hypothesis,
        {},
        adaptive.empty_model(),
        turn_index=turn_index,
    )
    decision = adaptive.decide_response(state, adaptive.empty_model())
    pragmatic_label = str(pragmatic.get("pragmatic_label") or "")
    selected_type = (
        "explicit_correction"
        if pragmatic_label == "explicit_correction"
        else "emotional_bid"
        if state.get("active")
        else "general_conversation"
    )
    mode_contract = adaptive.build_desired_response_mode_contract(
        {"selected_type": selected_type},
        state,
        decision,
    )
    return state, decision, mode_contract


def build_dataset_evidence_p4_ad(dataset_path):
    dataset_path = Path(dataset_path)
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    cases = []
    turn_index = 0
    for partition in ("development_cases", "holdout_ambiguity_cases", "literal_controls"):
        for frozen in dataset[partition]:
            turn_index += 1
            state, decision, mode_contract = _isolated_inputs(
                frozen["input"],
                turn_index,
            )
            probe_reply = f"unchanged-probe-{frozen['case_id']}"
            visible, trace = shadow_visible_reply_p4(
                probe_reply,
                state,
                decision,
                mode_contract,
            )
            encoded = json.dumps(trace, ensure_ascii=False, sort_keys=True)
            candidate_modes = [
                row.get("mode")
                for row in (trace.get("candidate_expectations") or [])
                if row.get("mode")
            ]
            cases.append(
                {
                    "case_id": frozen["case_id"],
                    "partition": partition,
                    "status": trace["status"],
                    "selected_action_mode": (trace.get("selected_action") or {}).get("mode"),
                    "candidate_modes": candidate_modes,
                    "candidate_count": trace["candidate_count"],
                    "candidate_contract_passed": trace["candidate_contract_passed"],
                    "private_reason_status": trace["private_reason_status"],
                    "selected_action_is_private_truth_commitment": trace[
                        "selected_action_is_private_truth_commitment"
                    ],
                    "trace_contains_raw_input": frozen["input"] in encoded,
                    "visible_reply_changed": visible != probe_reply,
                    "new_model_call_count": int(trace["model_call_added"]),
                    "fact_write_count": trace["fact_write_count"],
                    "profile_write_count": trace["profile_write_count"],
                    "episode_write_count": trace["episode_write_count"],
                }
            )
    development = cases[: len(dataset["development_cases"])]
    holdout_start = len(development)
    holdout_end = holdout_start + len(dataset["holdout_ambiguity_cases"])
    holdout = cases[holdout_start:holdout_end]
    controls = cases[holdout_end:]
    expected_by_id = {
        row["case_id"]: row
        for partition in ("development_cases", "holdout_ambiguity_cases", "literal_controls")
        for row in dataset[partition]
    }
    product_path = Path(__file__).with_name("uruha_web_ui_product_p4_ad.py")
    product_source = product_path.read_text(encoding="utf-8") if product_path.is_file() else ""
    graph_probe = append_desired_response_ambiguity_node_p4(
        {
            "reply": "unchanged",
            "logic": {LABEL: build_desired_response_ambiguity_ledger_p4({}, {}, {})},
            "runtime_trace": {
                "blackboard": [
                    {"stage": "surface", "label": "utterance", "payload": {}}
                ]
            },
        }
    )
    labels = [row.get("label") for row in graph_probe["runtime_trace"]["blackboard"]]
    metrics = {
        "development_case_count": len(development),
        "development_exact_status_count": sum(
            row["status"] == expected_by_id[row["case_id"]]["expected_status"]
            for row in development
        ),
        "development_exact_selected_action_count": sum(
            row["selected_action_mode"]
            == expected_by_id[row["case_id"]].get("expected_selected_action_mode")
            for row in development
        ),
        "holdout_ambiguity_case_count": len(holdout),
        "holdout_exact_status_count": sum(
            row["status"] == expected_by_id[row["case_id"]]["expected_status"]
            for row in holdout
        ),
        "holdout_required_candidate_modes_complete_count": sum(
            set(expected_by_id[row["case_id"]]["required_candidate_modes"]).issubset(
                set(row["candidate_modes"])
            )
            for row in holdout
        ),
        "literal_control_count": len(controls),
        "literal_control_false_positive_count": sum(
            row["status"] != "not_applicable" or row["candidate_count"] != 0
            for row in controls
        ),
        "candidate_contract_pass_count": sum(
            row["candidate_contract_passed"] for row in development + holdout
        ),
        "selected_action_private_truth_commitment_count": sum(
            row["selected_action_is_private_truth_commitment"] for row in cases
        ),
        "raw_input_trace_count": sum(row["trace_contains_raw_input"] for row in cases),
        "visible_reply_changed_count": sum(row["visible_reply_changed"] for row in cases),
        "new_model_call_count": sum(row["new_model_call_count"] for row in cases),
        "fact_write_count": sum(row["fact_write_count"] for row in cases),
        "profile_write_count": sum(row["profile_write_count"] for row in cases),
        "episode_write_count": sum(row["episode_write_count"] for row in cases),
    }
    return {
        "schema": "uruha_p4_ad_desired_response_ambiguity_evidence_v1",
        "dataset_sha256": hashlib.sha256(dataset_path.read_bytes()).hexdigest(),
        "cases": cases,
        "metrics": metrics,
        "integration": {
            "additive_product_entry_installs_ledger": (
                "import uruha_web_ui_product_p4_ab as _p4_ab" in product_source
                and "install_desired_response_ambiguity_p4()" in product_source
            ),
            "runtime_graph_node_test_passed": labels == [LABEL, "utterance"],
            "visible_reply_unchanged_test_passed": metrics["visible_reply_changed_count"] == 0,
            "duplicate_graph_node_count": max(0, labels.count(LABEL) - 1),
        },
        "claim_boundary": (
            "deterministic frozen shadow evidence only; not the user's true desired response, "
            "felt understanding, human preference, a human equation or strong-LLM advantage"
        ),
    }
