"""V2.16 bounded reference-person desired-response equation.

This module is an operational research model, not a claim that its variables
are literal neural states.  It keeps the general equation replaceable while
using public-evidence-grounded Ichinose Uruha parameters as the primary
reference-person instantiation.  It never opens or writes production memory.
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CASE_PATH = ROOT / "datasets/v2_16_reference_person_equation_cases.json"

REFERENCE_PERSON = {
    "id": "ichinose_uruha_public_reference_person_v1",
    "role": "replaceable public-evidence-grounded reference-person parameterization",
    "positioning": "research model of a public observable plane; not the real person",
    "parameters": {
        "direct_unsugarcoated_delivery": 0.88,
        "familiar_group_straight_man_role": 0.84,
        "guarded_with_unfamiliar_people": 0.82,
        "sustained_everyday_talk": 0.76,
        "uncertainty_honesty": 0.90,
        "care_without_overmedicalizing": 0.70,
    },
    "evidence_refs": [
        "datasets/public_persona_evidence_v1.json#persona_dev_v1_001",
        "datasets/public_persona_evidence_v1.json#persona_dev_v1_002",
        "datasets/public_persona_evidence_v1.json#persona_dev_v1_003",
        "datasets/public_persona_evidence_v1.json#persona_dev_v1_006",
    ],
    "evidence_role": "development_only_not_independent_persona_holdout",
    "unknown_space": [
        "private_mental_state",
        "childhood_and_unpublished_experience",
        "unobserved_private_relationships",
    ],
}

POLICIES = {
    "care_physiology": {
        "label": "先照顧身體",
        "icon": "♡",
        "persona_fit": 0.74,
        "persona_refs": ["persona_dev_v1_002", "persona_dev_v1_003"],
        "instruction": "先接住可觀察的睡眠或身體負荷，只給一個低壓的照顧步驟，不做診斷。",
        "core_message_jp": "寝不足やカフェインが関係してるなら、まず水飲んで少し休も。",
    },
    "solve_regulation": {
        "label": "給一個現在能做的步驟",
        "icon": "→",
        "persona_fit": 0.76,
        "persona_refs": ["persona_dev_v1_002"],
        "instruction": "直接給一個現在可執行的降載步驟，不加長篇說教。",
        "core_message_jp": "今すぐなら、頭の中を一回メモに全部出して、五分だけ呼吸整えよ。",
    },
    "listen_presence": {
        "label": "不要解法，只留下來聽",
        "icon": "∞",
        "persona_fit": 0.73,
        "persona_refs": ["persona_dev_v1_002", "persona_dev_v1_006"],
        "instruction": "反映對方承受的狀態，明確不急著給方法，讓對方繼續說。",
        "core_message_jp": "今日はずっとそれに付き合わされてんのか。方法は出さずに聞くから、そのまま話して。",
    },
    "share_arousal": {
        "label": "一起進入興奮節奏",
        "icon": "↗",
        "persona_fit": 0.78,
        "persona_refs": ["persona_dev_v1_002", "persona_dev_v1_006"],
        "instruction": "不要把正向高喚起當焦慮處理，短短地一起分享期待。",
        "core_message_jp": "そりゃ頭止まんねえわ。結果来るまでうちも一緒にそわそわしとく。",
    },
    "playful_tease": {
        "label": "接受邀請，熟人式吐槽",
        "icon": "⚡",
        "persona_fit": 0.86,
        "persona_refs": ["persona_dev_v1_001", "persona_dev_v1_002"],
        "instruction": "只有在熟悉關係且明確邀請玩笑時，給一句輕微吐槽；不得使用診斷或疾病標籤。",
        "core_message_jp": "朝から脳内だけ二十四時間営業かよ。止まる気ゼロじゃん。",
    },
    "calibrate_need": {
        "label": "資訊不足，確認真正想要的接法",
        "icon": "?",
        "persona_fit": 0.82,
        "persona_refs": ["persona_dev_v1_002", "persona_dev_v1_003"],
        "instruction": "只指出最關鍵的一個歧義，短問一次；不能把問問題本身當理解成功。",
        "core_message_jp": "寝てないのか、考え事で止まんないのか、まずそこだけどっち？",
    },
}


def _clip(value):
    return max(0.0, min(1.0, float(value or 0.0)))


def load_case_bundle(path=CASE_PATH):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_case(case_id, path=CASE_PATH):
    bundle = load_case_bundle(path)
    for case in bundle.get("cases") or []:
        if case.get("case_id") == case_id:
            payload = deepcopy(case)
            payload["current_input"] = bundle["shared_current_input"]
            return payload
    raise KeyError(f"unknown V2.16 equation case: {case_id}")


def case_choices(path=CASE_PATH):
    bundle = load_case_bundle(path)
    return [(case["label"], case["case_id"]) for case in bundle.get("cases") or []]


def state_from_case(case):
    return {
        "schema": "uruha_desired_response_state_v2_16",
        "case_id": case["case_id"],
        "current_input": case["current_input"],
        "context_history": deepcopy(case.get("context_history") or []),
        "atoms": deepcopy(case.get("state_atoms") or {}),
        "reference_person": deepcopy(REFERENCE_PERSON),
        "feedback_history": [],
        "intervention_history": [],
        "production_memory_write_count": 0,
    }


def _atom(state, key, field="value", fallback=0.0):
    return _clip(((state.get("atoms") or {}).get(key) or {}).get(field, fallback))


def _mean_confidence(state):
    atoms = list((state.get("atoms") or {}).values())
    if not atoms:
        return 0.0
    return sum(_clip(atom.get("confidence")) for atom in atoms) / len(atoms)


def _desired_response_fits(state):
    sleep = _atom(state, "sleep_debt")
    physical = _atom(state, "physical_strain")
    solution = _atom(state, "solution_request")
    listening = _atom(state, "listening_request")
    positive = _atom(state, "positive_arousal")
    humor = _atom(state, "humor_invitation")
    familiar = _atom(state, "relationship_familiarity")
    companionship = _atom(state, "companionship_request")
    task = _atom(state, "task_pressure")
    uncertainty = _atom(state, "uncertainty")
    clear_need = max(solution, listening, positive, humor, sleep)
    low_confidence = 1.0 - _mean_confidence(state)
    return {
        "care_physiology": _clip(0.55 * sleep + 0.35 * physical + 0.10 * (1.0 - positive)),
        "solve_regulation": _clip(0.58 * solution + 0.20 * task + 0.12 * physical + 0.10 * (1.0 - listening)),
        "listen_presence": _clip(0.58 * listening + 0.25 * companionship + 0.12 * physical + 0.05 * (1.0 - solution)),
        "share_arousal": _clip(0.58 * positive + 0.30 * companionship + 0.08 * familiar + 0.04 * (1.0 - uncertainty)),
        "playful_tease": _clip(0.52 * humor + 0.28 * familiar + 0.12 * positive + 0.08 * (1.0 - physical) - 0.35 * physical - 0.15 * sleep),
        "calibrate_need": _clip(uncertainty * (1.0 - 0.75 * clear_need) + 0.18 * low_confidence),
    }


def _policy_penalty(state, policy_id):
    sleep = _atom(state, "sleep_debt")
    physical = _atom(state, "physical_strain")
    solution = _atom(state, "solution_request")
    listening = _atom(state, "listening_request")
    positive = _atom(state, "positive_arousal")
    humor = _atom(state, "humor_invitation")
    familiar = _atom(state, "relationship_familiarity")
    uncertainty = _atom(state, "uncertainty")
    if policy_id == "playful_tease":
        return _clip(0.35 * physical + 0.20 * sleep + 0.24 * (1.0 - familiar) + 0.16 * (1.0 - humor))
    if policy_id == "solve_regulation":
        return _clip(0.32 * listening + 0.12 * uncertainty)
    if policy_id == "care_physiology":
        return _clip(0.25 * positive + 0.12 * (1.0 - physical) * (1.0 - sleep))
    if policy_id == "listen_presence":
        return _clip(0.30 * solution)
    if policy_id == "share_arousal":
        return _clip(0.28 * solution + 0.20 * physical)
    if policy_id == "calibrate_need":
        return _clip(0.28 * (1.0 - uncertainty))
    return 0.0


def _evidence_quality(state, policy_id):
    relevant = {
        "care_physiology": ("sleep_debt", "physical_strain"),
        "solve_regulation": ("solution_request", "task_pressure"),
        "listen_presence": ("listening_request", "companionship_request"),
        "share_arousal": ("positive_arousal", "companionship_request"),
        "playful_tease": ("humor_invitation", "relationship_familiarity"),
        "calibrate_need": ("uncertainty",),
    }[policy_id]
    return sum(_atom(state, key, "confidence") for key in relevant) / len(relevant)


def score_candidates(state, reference_person=None):
    """Return inspectable candidates; no model call and no hidden global score."""
    reference_person = reference_person or state.get("reference_person") or REFERENCE_PERSON
    fits = _desired_response_fits(state)
    candidates = []
    for policy_id, policy in POLICIES.items():
        desired_fit = fits[policy_id]
        persona_fit = _clip(policy["persona_fit"])
        evidence_quality = _evidence_quality(state, policy_id)
        penalty = _policy_penalty(state, policy_id)
        expected_utility = _clip(
            0.68 * desired_fit + 0.22 * persona_fit + 0.10 * evidence_quality - 0.42 * penalty
        )
        candidates.append(
            {
                "policy_id": policy_id,
                "label": policy["label"],
                "icon": policy["icon"],
                "desired_response_fit": round(desired_fit, 4),
                "reference_person_fit": round(persona_fit, 4),
                "evidence_quality": round(evidence_quality, 4),
                "risk_penalty": round(penalty, 4),
                "expected_utility": round(expected_utility, 4),
                "instruction": policy["instruction"],
                "core_message_jp": policy["core_message_jp"],
                "persona_evidence_refs": deepcopy(policy["persona_refs"]),
            }
        )
    return sorted(candidates, key=lambda row: (-row["expected_utility"], row["policy_id"]))


def solve_equation(state):
    candidates = score_candidates(state)
    selected = candidates[0]
    runner_up = candidates[1]
    return {
        "schema": "uruha_reference_person_desired_response_solution_v2_16",
        "equation": "r*=argmax_r P(desired_response|human_state)*fit(theta_Uruha)-risk",
        "state": deepcopy(state),
        "candidates": candidates,
        "selected": deepcopy(selected),
        "runner_up": deepcopy(runner_up),
        "utility_margin": round(selected["expected_utility"] - runner_up["expected_utility"], 4),
        "fact_claim": "operational latent-state hypothesis, not literal human neural state",
        "production_memory_write_count": 0,
    }


def intervene_atom(state, key, value, confidence=1.0, evidence="counterfactual intervention"):
    updated = deepcopy(state)
    before = deepcopy((updated.get("atoms") or {}).get(key))
    updated.setdefault("atoms", {})[key] = {
        "value": _clip(value),
        "confidence": _clip(confidence),
        "status": "counterfactual_intervention",
        "evidence": evidence,
    }
    updated.setdefault("intervention_history", []).append(
        {"atom": key, "before": before, "after": deepcopy(updated["atoms"][key])}
    )
    return updated


def _feedback_assignments(feedback_text):
    text = str(feedback_text or "").lower()
    assignments = {}
    if any(token in text for token in ("吐槽", "開玩笑", "tease", "joke")):
        assignments.update(
            {
                "humor_invitation": (0.98, 0.99, "explicit_feedback"),
                "relationship_familiarity": (0.92, 0.94, "explicit_feedback"),
                "solution_request": (0.04, 0.92, "explicit_feedback"),
                "physical_strain": (0.08, 0.82, "explicit_feedback"),
                "uncertainty": (0.06, 0.96, "derived_after_feedback"),
            }
        )
    if any(token in text for token in ("方法", "怎麼停", "solution", "method")) and not any(
        token in text for token in ("不要方法", "不用方法", "不是要方法")
    ):
        assignments.update(
            {
                "solution_request": (0.98, 0.99, "explicit_feedback"),
                "uncertainty": (0.05, 0.96, "derived_after_feedback"),
            }
        )
    if any(token in text for token in ("只想說", "只想有人聽", "listen", "不要方法", "不用方法")):
        assignments.update(
            {
                "listening_request": (0.98, 0.99, "explicit_feedback"),
                "solution_request": (0.03, 0.98, "explicit_feedback"),
                "uncertainty": (0.05, 0.96, "derived_after_feedback"),
            }
        )
    if any(token in text for token in ("不是緊張", "期待", "興奮", "excited")):
        assignments.update(
            {
                "positive_arousal": (0.98, 0.99, "explicit_feedback"),
                "companionship_request": (0.90, 0.90, "bounded_feedback_inference"),
                "uncertainty": (0.05, 0.96, "derived_after_feedback"),
            }
        )
    if any(token in text for token in ("沒睡", "沒有睡", "not sleep", "didn't sleep")):
        assignments.update(
            {
                "sleep_debt": (0.98, 0.99, "explicit_feedback"),
                "uncertainty": (0.08, 0.94, "derived_after_feedback"),
            }
        )
    return assignments


def apply_user_feedback(state, feedback_text):
    """Update named atoms from explicit feedback, retaining before/after history."""
    updated = deepcopy(state)
    assignments = _feedback_assignments(feedback_text)
    changes = []
    for key, (value, confidence, status) in assignments.items():
        before = deepcopy((updated.get("atoms") or {}).get(key))
        after = {
            "value": _clip(value),
            "confidence": _clip(confidence),
            "status": status,
            "evidence": str(feedback_text),
        }
        updated.setdefault("atoms", {})[key] = after
        changes.append({"atom": key, "before": before, "after": deepcopy(after)})
    updated.setdefault("feedback_history", []).append(
        {"feedback": str(feedback_text), "changes": changes, "changed_atom_count": len(changes)}
    )
    return updated, changes


def build_case_solution(case_id):
    case = load_case(case_id)
    return case, solve_equation(state_from_case(case))
