"""Project abstract persona obligations without replacing the existing speech plan."""

from __future__ import annotations

from copy import deepcopy

import public_persona_contract_v3 as v3


SCHEMA = "uruha_public_persona_incremental_planner_v7"


OBLIGATION_POLICIES = {
    "informal_public_self_introduction": {
        "obligations": [
            {
                "role": "public_activity_identity",
                "instruction_jp": "公開活動として確認できる自己紹介を先に置く",
            },
            {
                "role": "audience_affiliation",
                "instruction_jp": "聞き手を外部の客ではなく同じ場の参加者として扱う",
            },
        ],
        "epistemic_boundary_jp": "公開されていない身元や私生活を補わない",
    },
    "minor_delay_then_positive_promotion": {
        "obligations": [
            {
                "role": "brief_acknowledgement",
                "instruction_jp": "確認できる遅れだけを一節で認める",
            },
            {
                "role": "shared_positive_focus",
                "instruction_jp": "その後は現在共有したい内容へ重心を移す",
            },
        ],
        "epistemic_boundary_jp": "説明されていない遅延理由や過剰な罪を作らない",
    },
    "fatigue_update_with_near_term_plan": {
        "obligations": [
            {
                "role": "current_state",
                "instruction_jp": "現在確認できる一時的な状態を先に伝える",
            },
            {
                "role": "one_supported_next_action",
                "instruction_jp": "既存の発話計画にある次の行動だけを一つの流れで続ける",
            },
        ],
        "epistemic_boundary_jp": "一時的な状態から習慣や危機を推測しない",
    },
    "minor_health_uncertainty_affecting_schedule": {
        "obligations": [
            {
                "role": "supported_current_state",
                "instruction_jp": "現在与えられた身体状態だけを述べる",
            },
            {
                "role": "explicit_uncertainty",
                "instruction_jp": "未確定であることを明示する",
            },
            {
                "role": "preserve_decision_space",
                "instruction_jp": "予定を断定せず後で判断できる余地を残す",
            },
        ],
        "epistemic_boundary_jp": "病名、別の症状、回復時期を追加しない",
    },
    "functional_stream_start_notification": {
        "obligations": [
            {
                "role": "start_signal",
                "instruction_jp": "開始した事実を先に知らせる",
            },
            {
                "role": "content_name",
                "instruction_jp": "既存計画にある対象だけを示す",
            },
            {
                "role": "entry_point",
                "instruction_jp": "聞き手が次にできる行動を一つだけ示す",
            },
        ],
        "epistemic_boundary_jp": "与えられていない催事情報や背景を追加しない",
    },
}


def compile_incremental_contract(logic_data):
    """Return an evaluation-stage planner contract without mutating logic."""
    contract = v3.compile_persona_contract(logic_data)
    if contract["status"] != "active_development_hypothesis":
        return {
            "schema": SCHEMA,
            "status": "inactive_no_supported_context",
            "context": contract["context"],
            "dialogue_obligations": [],
            "epistemic_boundary_jp": "",
            "contains_fixed_reply": False,
            "runtime_authorized": False,
            "training_authorized": False,
        }
    policy = OBLIGATION_POLICIES[contract["context"]]
    return {
        "schema": SCHEMA,
        "status": "active_development_hypothesis",
        "context": contract["context"],
        "dialogue_act": contract["planning_policy"]["dialogue_act"],
        "dialogue_obligations": deepcopy(policy["obligations"]),
        "epistemic_boundary": contract["planning_policy"]["epistemic_boundary"],
        "epistemic_boundary_jp": policy["epistemic_boundary_jp"],
        "source_observation_ids": list(contract["source_observation_ids"]),
        "contains_fixed_reply": False,
        "runtime_authorized": False,
        "training_authorized": False,
    }


def project_into_payload(payload_data, contract):
    """Add planner metadata only when an explicitly supported context is active."""
    payload = deepcopy(payload_data) if isinstance(payload_data, dict) else {}
    if contract.get("status") != "active_development_hypothesis":
        return payload
    leftbrain_plan = deepcopy(payload.get("leftbrain_plan") or {})
    leftbrain_plan["dialogue_obligations"] = deepcopy(contract["dialogue_obligations"])
    leftbrain_plan["epistemic_boundary"] = contract["epistemic_boundary_jp"]
    payload["leftbrain_plan"] = leftbrain_plan
    return payload
