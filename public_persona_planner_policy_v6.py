"""Compile V3 public-persona planning hypotheses into a speech-plan contract."""

from __future__ import annotations

from copy import deepcopy

import public_persona_contract_v3 as v3


SCHEMA = "uruha_public_persona_planner_policy_v6"


PLANNING_BLUEPRINTS = {
    "informal_public_self_introduction": {
        "ordered_content_units": [
            "公開しているゲーム・配信・雑談などの活動を先に述べる",
            "軽い自虐は必要な場合だけ一度までにする",
            "みんな・一緒・リスナーなどで聞き手との仲間距離を示す",
        ],
        "required_marker_groups": [["ゲーム", "配信", "雑談"], ["みんな", "一緒", "リスナー"]],
        "epistemic_boundary_jp": "非公開の身元や私生活を作らない",
        "target_length": "1_or_2_short_sentences",
    },
    "minor_delay_then_positive_promotion": {
        "ordered_content_units": [
            "遅れ・今さら・忘れ・待たせたことを一節だけ認める",
            "楽しむ・見る・聴く・一緒に参加する前向きな共有内容へ移る",
        ],
        "required_marker_groups": [["遅", "今さら", "忘れ", "待たせ"], ["楽し", "見て", "聴いて", "一緒"]],
        "epistemic_boundary_jp": "裏付けのない遅延理由や過剰な罪を作らない",
        "target_length": "1_or_2_short_sentences",
    },
    "fatigue_update_with_near_term_plan": {
        "ordered_content_units": [
            "眠い・疲れた・へとへと・へろへろ等の現在状態を先に述べる",
            "食べる・休む・戻る・寝る・ゲーム等の次の一行動を述べる",
        ],
        "required_marker_groups": [["眠", "疲", "へとへと", "へろへろ"], ["食べ", "ご飯", "休", "戻", "寝", "ゲーム"]],
        "epistemic_boundary_jp": "一時的な疲労を恒常的習慣や危機に広げない",
        "target_length": "1_or_2_short_sentences",
    },
    "minor_health_uncertainty_affecting_schedule": {
        "ordered_content_units": [
            "喉・頭・胃・調子など確認できる現在状態を述べる",
            "様子・まだ不明・かもしれない等の不確実性を明示する",
            "後で決める・待つ等で予定の決定余地を残す",
        ],
        "required_marker_groups": [["喉", "頭", "胃", "調子"], ["様子", "まだ", "分から", "かも"], ["後で", "決め", "待って"]],
        "epistemic_boundary_jp": "病名を診断せず回復や予定を断言しない",
        "target_length": "1_or_2_short_sentences",
    },
    "functional_stream_start_notification": {
        "ordered_content_units": [
            "始める・開始・開いた等で開始事実を述べる",
            "ゲーム・配信・ルーム・イベント・対戦等の対象を述べる",
            "見て・入って・参加・今から等で相手の入口を述べる",
        ],
        "required_marker_groups": [["始め", "開始", "開いた", "始ま"], ["ゲーム", "配信", "ルーム", "イベント", "対戦"], ["見て", "入って", "参加", "今から"]],
        "epistemic_boundary_jp": "与えられていない催事情報や背景を足さない",
        "target_length": "1_or_2_short_sentences",
    },
}


def _merge_groups(existing, additions):
    merged = [list(group) for group in (existing or []) if group]
    normalized = {tuple(group) for group in merged}
    for group in additions:
        candidate = tuple(group)
        if candidate not in normalized:
            merged.append(list(group))
            normalized.add(candidate)
    return merged


def apply_planning_policy(logic_data):
    """Return a copied logic object with only planner-owned fields changed."""
    logic = deepcopy(logic_data) if isinstance(logic_data, dict) else {}
    contract = v3.compile_persona_contract(logic)
    if contract["status"] != "active_development_hypothesis":
        return logic, {
            "schema": SCHEMA,
            "status": "inactive_no_supported_context",
            "context": contract["context"],
            "changed_fields": [],
            "runtime_authorized": False,
            "training_authorized": False,
        }

    context = contract["context"]
    blueprint = PLANNING_BLUEPRINTS[context]
    policy = contract["planning_policy"]
    speech_plan = deepcopy(logic.get("human_speech_plan") or {})
    speech_plan.update(
        {
            "dialogue_act": policy["dialogue_act"],
            "content_units": list(blueprint["ordered_content_units"]),
            "speech_moves": [
                {"role": slot, "order": index}
                for index, slot in enumerate(policy["content_order"], start=1)
            ],
            "target_length": blueprint["target_length"],
            "epistemic_boundary": policy["epistemic_boundary"],
            "epistemic_boundary_jp": blueprint["epistemic_boundary_jp"],
        }
    )
    logic["human_speech_plan"] = speech_plan
    logic["dialogue_act"] = policy["dialogue_act"]
    logic["required_marker_groups"] = _merge_groups(
        logic.get("required_marker_groups"),
        blueprint["required_marker_groups"],
    )
    must_avoid = list(logic.get("must_avoid") or [])
    if blueprint["epistemic_boundary_jp"] not in must_avoid:
        must_avoid.append(blueprint["epistemic_boundary_jp"])
    logic["must_avoid"] = must_avoid
    return logic, {
        "schema": SCHEMA,
        "status": "active_development_hypothesis",
        "context": context,
        "dialogue_act": policy["dialogue_act"],
        "content_order": list(policy["content_order"]),
        "epistemic_boundary": policy["epistemic_boundary"],
        "changed_fields": [
            "human_speech_plan.dialogue_act",
            "human_speech_plan.content_units",
            "human_speech_plan.speech_moves",
            "human_speech_plan.epistemic_boundary",
            "dialogue_act",
            "required_marker_groups",
            "must_avoid",
        ],
        "runtime_authorized": False,
        "training_authorized": False,
    }
