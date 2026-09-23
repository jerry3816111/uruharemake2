"""P4-AF additive eligibility guard for the P4-AD ambiguity ledger."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path

import uruha_desired_response_ambiguity_p4 as ambiguity


SCHEMA = "uruha_desired_response_eligibility_guard_p4"
_ORIGINAL_LEDGER = ambiguity.build_desired_response_ambiguity_ledger_p4

_BOUNDED_EMOTIONAL_REASONS = {
    "ambiguous_arousal_requires_bounded_response_choice",
    "ambiguous_arousal_with_learned_response_preference",
    "possible_indirect_support_request",
    "explicit_positive_arousal",
}


def determine_eligibility_authority_p4(state, decision):
    state = state or {}
    decision = decision or {}
    correction = decision.get("correction_aware_surface_m20") or {}
    explicit = decision.get("explicit_desired_response_m25") or {}
    trigger_relation = decision.get("trigger_relation_m37") or {}
    if correction.get("authoritative") or explicit.get("authoritative"):
        return {
            "authorized": True,
            "authority": "current_explicit_response_form",
            "evidence_path": (
                "desired_response_decision_m18.correction_aware_surface_m20"
                if correction.get("authoritative")
                else "desired_response_decision_m18.explicit_desired_response_m25"
            ),
        }
    if trigger_relation.get("authoritative"):
        return {
            "authorized": True,
            "authority": "matched_verified_trigger_relation",
            "evidence_path": "desired_response_decision_m18.trigger_relation_m37",
        }
    trigger = state.get("observable_trigger_m37") or {}
    if (
        trigger.get("status") in {
            "single_observable_trigger",
            "multiple_observable_triggers",
        }
        and "cognitive_overactivity" in set(trigger.get("predicates") or [])
        and trigger.get("private_state_truth_claimed") is False
    ):
        return {
            "authorized": True,
            "authority": "typed_cognitive_overactivity",
            "evidence_path": "desired_response_state_m18.observable_trigger_m37",
        }
    reasons = set(state.get("activation_reasons") or [])
    matched_reasons = sorted(reasons.intersection(_BOUNDED_EMOTIONAL_REASONS))
    if matched_reasons:
        return {
            "authorized": True,
            "authority": "bounded_emotional_or_support_signal",
            "evidence_path": "desired_response_state_m18.activation_reasons",
            "matched_reasons": matched_reasons,
        }
    return {
        "authorized": False,
        "authority": "none_topic_only",
        "evidence_path": None,
        "rejected_solo_authorities": [
            "task_topic",
            "task_pressure_atom",
            "domain_label",
            "unverified_historical_preference",
        ],
    }


def _ranking_signature(trace):
    return [
        (
            row.get("policy_id"),
            row.get("mode"),
            row.get("operational_action_score"),
        )
        for row in (trace.get("candidate_expectations") or [])
    ]


def build_desired_response_eligibility_guard_p4(state, decision, mode_contract):
    base = _ORIGINAL_LEDGER(state, decision, mode_contract)
    authority = determine_eligibility_authority_p4(state, decision)
    guarded = deepcopy(base)
    base_signature = _ranking_signature(base)
    if not authority["authorized"]:
        guarded.update(
            {
                "status": "not_applicable",
                "selected_action": {
                    "policy_id": None,
                    "mode": None,
                    "selection_is_operational_action": False,
                    "selection_is_private_truth_commitment": False,
                },
                "private_reason_status": "not_applicable",
                "candidate_expectations": [],
                "candidate_contract_passed": False,
                "unknown_space": [],
                "candidate_count": 0,
            }
        )
    guarded.update(
        {
            "schema": SCHEMA,
            "predecessor_schema": base.get("schema"),
            "eligibility": {
                **authority,
                "topic_only_authorized": False,
                "task_pressure_atom_present": "task_pressure" in (
                    (state or {}).get("atoms") or {}
                )
                and float(
                    (((state or {}).get("atoms") or {}).get("task_pressure") or {}).get("value")
                    or 0.0
                )
                > 0.5,
                "claim_boundary": "current interaction authority, not private desire truth",
            },
            "candidate_ranking_unchanged": (
                _ranking_signature(guarded) == base_signature
                if authority["authorized"]
                else None
            ),
            "suppressed_predecessor_candidate_count": (
                len(base_signature) if not authority["authorized"] else 0
            ),
            "visible_reply_changed": False,
            "model_call_added": False,
            "fact_write_count": 0,
            "profile_write_count": 0,
            "episode_write_count": 0,
            "claim_boundary": (
                "bounded current-interaction eligibility for a desired-response ledger; "
                "not private desire truth, reply-quality proof or human understanding"
            ),
        }
    )
    return guarded


def shadow_visible_reply_p4(reply, state, decision, mode_contract):
    return str(reply or ""), build_desired_response_eligibility_guard_p4(
        state,
        decision,
        mode_contract,
    )


_INSTALLED_P4_AF = False


def install_desired_response_eligibility_p4():
    global _INSTALLED_P4_AF
    if _INSTALLED_P4_AF:
        return False
    ambiguity.build_desired_response_ambiguity_ledger_p4 = (
        build_desired_response_eligibility_guard_p4
    )
    _INSTALLED_P4_AF = True
    return True


def build_dataset_evidence_p4_af(dataset_path):
    dataset_path = Path(dataset_path)
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    cases = []
    turn_index = 200
    for partition in (
        "development_cases",
        "fresh_positive_cases",
        "fresh_negative_cases",
    ):
        for frozen in dataset[partition]:
            turn_index += 1
            state, decision, mode = ambiguity._isolated_inputs(
                frozen["input"],
                turn_index,
            )
            base = _ORIGINAL_LEDGER(state, decision, mode)
            probe = f"unchanged-p4-af-{frozen['case_id']}"
            visible, trace = shadow_visible_reply_p4(probe, state, decision, mode)
            cases.append(
                {
                    "case_id": frozen["case_id"],
                    "partition": partition,
                    "status": trace["status"],
                    "eligibility_authority": (trace.get("eligibility") or {}).get("authority"),
                    "selected_action_mode": (trace.get("selected_action") or {}).get("mode"),
                    "candidate_count": trace["candidate_count"],
                    "candidate_ranking_unchanged": (
                        _ranking_signature(trace) == _ranking_signature(base)
                        if frozen.get("expected_selected_action_mode") is not None
                        else False
                    ),
                    "topic_only_authorized": (trace.get("eligibility") or {}).get("topic_only_authorized"),
                    "visible_reply_changed": visible != probe or trace["visible_reply_changed"],
                    "new_model_call_count": int(trace["model_call_added"]),
                    "fact_write_count": trace["fact_write_count"],
                    "profile_write_count": trace["profile_write_count"],
                    "episode_write_count": trace["episode_write_count"],
                }
            )
    dev_count = len(dataset["development_cases"])
    positive_count = len(dataset["fresh_positive_cases"])
    development = cases[:dev_count]
    positives = cases[dev_count : dev_count + positive_count]
    negatives = cases[dev_count + positive_count :]
    expected = {
        row["case_id"]: row
        for partition in (
            "development_cases",
            "fresh_positive_cases",
            "fresh_negative_cases",
        )
        for row in dataset[partition]
    }
    product_path = Path(__file__).with_name("uruha_web_ui_product_p4_af.py")
    product_source = product_path.read_text(encoding="utf-8") if product_path.is_file() else ""
    probe_trace = build_desired_response_eligibility_guard_p4({}, {}, {})
    graph_probe = ambiguity.append_desired_response_ambiguity_node_p4(
        {
            "reply": "unchanged",
            "logic": {},
            "runtime_trace": {
                "blackboard": [
                    {"stage": "surface", "label": "utterance", "payload": {}}
                ]
            },
        },
        probe_trace,
    )
    labels = [row.get("label") for row in graph_probe["runtime_trace"]["blackboard"]]
    eligible = [
        row
        for row in cases
        if expected[row["case_id"]].get("expected_selected_action_mode") is not None
    ]
    return {
        "schema": "uruha_p4_af_desired_response_eligibility_evidence_v1",
        "dataset_sha256": hashlib.sha256(dataset_path.read_bytes()).hexdigest(),
        "cases": cases,
        "metrics": {
            "development_case_count": len(development),
            "development_exact_status_count": sum(row["status"] == expected[row["case_id"]]["expected_status"] for row in development),
            "development_exact_authority_count": sum(row["eligibility_authority"] == expected[row["case_id"]]["expected_authority"] for row in development),
            "development_exact_selected_action_count": sum(row["selected_action_mode"] == expected[row["case_id"]].get("expected_selected_action_mode") for row in development),
            "fresh_positive_case_count": len(positives),
            "fresh_positive_exact_status_count": sum(row["status"] == expected[row["case_id"]]["expected_status"] for row in positives),
            "fresh_positive_exact_authority_count": sum(row["eligibility_authority"] == expected[row["case_id"]]["expected_authority"] for row in positives),
            "fresh_positive_exact_selected_action_count": sum(row["selected_action_mode"] == expected[row["case_id"]].get("expected_selected_action_mode") for row in positives),
            "fresh_negative_case_count": len(negatives),
            "fresh_negative_exact_status_count": sum(row["status"] == expected[row["case_id"]]["expected_status"] for row in negatives),
            "fresh_negative_exact_authority_count": sum(row["eligibility_authority"] == expected[row["case_id"]]["expected_authority"] for row in negatives),
            "eligible_candidate_ranking_unchanged_count": sum(row["candidate_ranking_unchanged"] for row in eligible),
            "topic_only_authorization_count": sum(row["topic_only_authorized"] for row in cases),
            "visible_reply_changed_count": sum(row["visible_reply_changed"] for row in cases),
            "new_model_call_count": sum(row["new_model_call_count"] for row in cases),
            "fact_write_count": sum(row["fact_write_count"] for row in cases),
            "profile_write_count": sum(row["profile_write_count"] for row in cases),
            "episode_write_count": sum(row["episode_write_count"] for row in cases),
        },
        "integration": {
            "additive_product_entry_installs_guard": (
                "import uruha_web_ui_product_p4_ad as _p4_ad" in product_source
                and "install_desired_response_eligibility_p4()" in product_source
            ),
            "single_graph_node_test_passed": labels == [ambiguity.LABEL, "utterance"],
            "visible_reply_unchanged_test_passed": all(not row["visible_reply_changed"] for row in cases),
        },
        "claim_boundary": dataset["claim_boundary"],
    }
