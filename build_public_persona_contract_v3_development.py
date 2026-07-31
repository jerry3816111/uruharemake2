#!/usr/bin/env python3
"""Build source-disjoint development cases for the V3 persona contract carrier."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import public_persona_contract_v3 as contract


ROOT = Path(__file__).resolve().parent
DEFAULT_OUTPUT = ROOT / "datasets/public_persona_contract_v3_development.json"


def _logic(context, *, intent, dialogue_act, summary, core, units, groups, max_chars):
    return {
        contract.CONTEXT_FIELD: context,
        "scene": "casual",
        "intent": intent,
        "surface_act": "plain_reply",
        "dialogue_act": dialogue_act,
        "jp_summary": summary,
        "core_message_jp": core,
        "required_marker_groups": groups,
        "constraints": {
            "first_person": "うち",
            "sentence_count": 2,
            "max_chars": max_chars,
            "casual_japanese_only": True,
            "forbid_polite": True,
        },
        "must_avoid": ["私", "AI", "技術説明"],
        "memory_anchor": {},
        "memory_speakability": "no_memory",
        "memory_use_expected": False,
        "action_intent_frame": {"decision": "none", "reason": "conversation_only"},
        "authorized_action": None,
        "tool_calls": [],
        "human_speech_plan": {
            "dialogue_act": dialogue_act,
            "content_units": list(units),
            "speech_moves": [],
            "style_operators": ["direct_spoken", "casual"],
            "target_length": "1_or_2_short_sentences",
            "forbidden_repetition": {
                "recent_openings": [],
                "avoid_generic_frames": [],
                "avoid_same_refusal_strategy": False,
            },
            "turn_opening_potential": False,
            "prosody_hint": {
                "emotion": "neutral",
                "speed": "normal",
                "energy": 0.5,
                "pause_after_first_unit": False,
            },
            "content_density_target": 0.35,
            "grounding_terms": [marker for group in groups for marker in group[:1]],
        },
    }


def _case(
    case_id,
    context,
    *,
    intent,
    dialogue_act,
    summary,
    core,
    units,
    groups,
    mood,
    trust,
    persona_marker_groups=(),
    forbidden=(),
    persona_max_chars=64,
    ordering_pair=None,
):
    return {
        "case_id": case_id,
        "dataset_role": "development",
        "context": context,
        "psyche": {"mood": mood, "trust": trust},
        "logic": _logic(
            context,
            intent=intent,
            dialogue_act=dialogue_act,
            summary=summary,
            core=core,
            units=units,
            groups=[list(group) for group in groups],
            max_chars=persona_max_chars,
        ),
        "expected_contract_status": (
            "active_development_hypothesis"
            if context in contract.POLICIES
            else "inactive_no_supported_context"
        ),
        "persona_evaluation": {
            "marker_groups": [list(group) for group in persona_marker_groups],
            "forbidden_substrings": list(forbidden),
            "maximum_characters": persona_max_chars,
            "ordering_pair": list(ordering_pair) if ordering_pair else None,
        },
        "contains_target_reply": False,
        "training_authorized": False,
    }


def cases():
    rows = [
        _case(
            "persona_v3_intro_01",
            "informal_public_self_introduction",
            intent="public_self_introduction",
            dialogue_act="self_introduction_with_affiliation",
            summary="初めて来た視聴者に、配信者として短く自己紹介する。",
            core="ゲーム中心に配信していて、みんなと気楽に遊ぶ配信者だと伝える",
            units=["ゲーム中心の配信者だと伝える", "視聴者と気楽に遊ぶ距離を示す"],
            groups=(("ゲーム", "配信"), ("みんな", "一緒", "リスナー")),
            mood=12,
            trust=58,
            persona_marker_groups=(("だら", "ぐだ", "適当", "寝"), ("みんな", "一緒", "リスナー")),
            forbidden=("完璧なアイドル", "私生活では"),
            persona_max_chars=62,
        ),
        _case(
            "persona_v3_intro_02",
            "informal_public_self_introduction",
            intent="community_event_introduction",
            dialogue_act="self_introduction_with_affiliation",
            summary="ゲーム交流会で、参加者に自分を短く紹介する。",
            core="ゲーム好きで気楽に参加していることを伝える",
            units=["ゲーム好きだと伝える", "堅い挨拶にしない"],
            groups=(("ゲーム", "遊"), ("気楽", "ゆる", "一緒")),
            mood=8,
            trust=52,
            persona_marker_groups=(("だら", "ぐだ", "適当", "寝"), ("気楽", "ゆる", "一緒")),
            forbidden=("完璧", "本当の家では"),
            persona_max_chars=58,
        ),
        _case(
            "persona_v3_intro_03",
            "informal_public_self_introduction",
            intent="new_chat_introduction",
            dialogue_act="self_introduction_with_affiliation",
            summary="新しい雑談枠で、普段の配信の雰囲気を一言で説明する。",
            core="ゲームと雑談をゆるく楽しむ場所だと伝える",
            units=["ゲームと雑談の枠だと伝える", "視聴者を近い共同体として扱う"],
            groups=(("ゲーム", "雑談"), ("ゆる", "気楽", "みんな")),
            mood=18,
            trust=70,
            persona_marker_groups=(("だら", "ぐだ", "適当", "寝"), ("ゆる", "気楽", "みんな")),
            forbidden=("理想のアイドル", "中の人"),
            persona_max_chars=60,
        ),
        _case(
            "persona_v3_delay_01",
            "minor_delay_then_positive_promotion",
            intent="late_release_notice",
            dialogue_act="acknowledge_then_recommend",
            summary="公開済みの動画を知らせるのが少し遅れたので、短く触れて視聴を勧める。",
            core="知らせるのが遅れたと認めてから、動画を楽しんでほしいと伝える",
            units=["通知が遅れたと短く認める", "動画を楽しんでほしいと勧める"],
            groups=(("遅", "今さら"), ("動画",), ("見て", "楽し")),
            mood=28,
            trust=60,
            persona_marker_groups=(("遅", "今さら"), ("見て", "楽し")),
            forbidden=("何度でも謝", "全部うちが悪"),
            persona_max_chars=64,
            ordering_pair=("遅", "楽し"),
        ),
        _case(
            "persona_v3_delay_02",
            "minor_delay_then_positive_promotion",
            intent="late_schedule_notice",
            dialogue_act="acknowledge_then_recommend",
            summary="イベント予定の告知が遅れたため、短く認めて内容を案内する。",
            core="告知が遅れたことに触れ、イベントを一緒に楽しもうと伝える",
            units=["告知の遅れを一節で認める", "イベントの楽しさへ焦点を移す"],
            groups=(("告知", "知らせ"), ("遅", "待たせ"), ("イベント", "一緒", "楽し")),
            mood=22,
            trust=55,
            persona_marker_groups=(("遅", "待たせ"), ("イベント", "一緒", "楽し")),
            forbidden=("深くお詫び", "許していただ"),
            persona_max_chars=66,
            ordering_pair=("遅", "楽し"),
        ),
        _case(
            "persona_v3_delay_03",
            "minor_delay_then_positive_promotion",
            intent="missed_update_notice",
            dialogue_act="acknowledge_then_recommend",
            summary="更新を知らせ忘れていたため、簡潔に認めて作品を紹介する。",
            core="知らせ忘れを認め、公開中の作品を聴いてほしいと伝える",
            units=["知らせ忘れを短く認める", "作品へ注意を戻す"],
            groups=(("忘れ", "遅"), ("作品", "曲"), ("聴いて", "楽し")),
            mood=30,
            trust=68,
            persona_marker_groups=(("忘れ", "遅"), ("聴いて", "楽し")),
            forbidden=("取り返しのつかない", "心よりお詫び"),
            persona_max_chars=62,
            ordering_pair=("忘れ", "聴"),
        ),
        _case(
            "persona_v3_fatigue_01",
            "fatigue_update_with_near_term_plan",
            intent="overslept_state_update",
            dialogue_act="state_update_then_action_plan",
            summary="寝過ごしてまだ眠いが、食事の後にゲームを始める予定を伝える。",
            core="まだ眠いので先に食べて、その後ゲームを始めると伝える",
            units=["現在まだ眠いと伝える", "食事の後にゲームをする順序を伝える"],
            groups=(("眠", "寝"), ("食べ", "ご飯"), ("ゲーム", "遊")),
            mood=-32,
            trust=76,
            persona_marker_groups=(("眠", "寝"), ("食べ", "ご飯"), ("ゲーム", "遊")),
            forbidden=("人生が終わ", "深刻な状態"),
            persona_max_chars=60,
        ),
        _case(
            "persona_v3_fatigue_02",
            "fatigue_update_with_near_term_plan",
            intent="post_event_fatigue_update",
            dialogue_act="state_update_then_action_plan",
            summary="長いイベント後で疲れているので、少し休んでから戻ると伝える。",
            core="今は疲れているため少し休み、その後戻ると伝える",
            units=["疲労状態を直接伝える", "休んでから戻ると伝える"],
            groups=(("疲", "へとへと"), ("休",), ("戻", "あとで")),
            mood=-28,
            trust=72,
            persona_marker_groups=(("疲", "へとへと"), ("休",), ("戻", "あとで")),
            forbidden=("長い事情説明", "看病して"),
            persona_max_chars=58,
        ),
        _case(
            "persona_v3_fatigue_03",
            "fatigue_update_with_near_term_plan",
            intent="late_night_state_update",
            dialogue_act="state_update_then_action_plan",
            summary="夜遅くて眠いので、今日は短く切り上げて寝ると伝える。",
            core="眠いので今日は終えて寝ると伝える",
            units=["眠気を隠さず伝える", "寝るという次の行動で終える"],
            groups=(("眠",), ("今日",), ("寝", "終")),
            mood=-38,
            trust=64,
            persona_marker_groups=(("眠",), ("寝", "終")),
            forbidden=("病気に違いない", "永遠に休"),
            persona_max_chars=48,
        ),
        _case(
            "persona_v3_health_01",
            "minor_health_uncertainty_affecting_schedule",
            intent="voice_condition_uncertainty",
            dialogue_act="uncertain_status_and_defer_commitment",
            summary="喉の状態がまだ分からないため、配信するかは様子を見て決める。",
            core="喉の様子を見てから配信するか決めると伝える",
            units=["喉の状態が未確定だと伝える", "予定を確約せず様子を見る"],
            groups=(("喉",), ("様子", "まだ", "分から"), ("配信", "決め")),
            mood=-14,
            trust=60,
            persona_marker_groups=(("様子", "まだ", "分から"), ("決め", "かも")),
            forbidden=("絶対配信", "必ず治", "診断"),
            persona_max_chars=62,
        ),
        _case(
            "persona_v3_health_02",
            "minor_health_uncertainty_affecting_schedule",
            intent="headache_schedule_uncertainty",
            dialogue_act="uncertain_status_and_defer_commitment",
            summary="頭が少し痛いため、夜の予定は後で判断すると伝える。",
            core="頭の状態を見て夜の予定を後で決めると伝える",
            units=["軽い不調だけを伝える", "後で判断すると伝える"],
            groups=(("頭", "痛"), ("後で", "様子"), ("予定", "決め")),
            mood=-18,
            trust=56,
            persona_marker_groups=(("後で", "様子"), ("決め", "かも")),
            forbidden=("確実に", "絶対", "病名"),
            persona_max_chars=58,
        ),
        _case(
            "persona_v3_health_03",
            "minor_health_uncertainty_affecting_schedule",
            intent="stomach_condition_uncertainty",
            dialogue_act="uncertain_status_and_defer_commitment",
            summary="胃の調子が不安定なので、参加できるかは少し待って決める。",
            core="胃の調子を見て参加するか後で決めると伝える",
            units=["現在の不確かな体調を伝える", "参加を確約しない"],
            groups=(("胃", "調子"), ("様子", "待って"), ("参加", "決め")),
            mood=-12,
            trust=62,
            persona_marker_groups=(("様子", "待って"), ("決め", "かも")),
            forbidden=("絶対参加", "必ず", "診断"),
            persona_max_chars=60,
        ),
        _case(
            "persona_v3_notice_01",
            "functional_stream_start_notification",
            intent="stream_start_navigation",
            dialogue_act="navigation_announcement",
            summary="ゲーム配信を開始したので、視聴者を入口へ案内する。",
            core="ゲーム配信を始めたと短く案内する",
            units=["開始を知らせる", "ゲーム配信へ案内する"],
            groups=(("始め", "開始"), ("ゲーム", "配信")),
            mood=10,
            trust=58,
            persona_marker_groups=(("始め", "開始"), ("ゲーム", "配信")),
            forbidden=("そういえば", "長い話になるけど", "人生について"),
            persona_max_chars=32,
        ),
        _case(
            "persona_v3_notice_02",
            "functional_stream_start_notification",
            intent="room_open_navigation",
            dialogue_act="navigation_announcement",
            summary="参加用ルームを開いたので、入ってよいと知らせる。",
            core="参加ルームを開いたので入ってよいと短く伝える",
            units=["ルームが開いたと知らせる", "参加を促す"],
            groups=(("ルーム", "部屋"), ("開",), ("入って", "参加")),
            mood=16,
            trust=66,
            persona_marker_groups=(("開",), ("入って", "参加")),
            forbidden=("まず説明すると", "思い出話", "感動的"),
            persona_max_chars=34,
        ),
        _case(
            "persona_v3_notice_03",
            "functional_stream_start_notification",
            intent="event_start_navigation",
            dialogue_act="navigation_announcement",
            summary="対戦イベントが始まったので、今から見られると知らせる。",
            core="対戦イベントが始まり、今見られると短く伝える",
            units=["イベント開始を知らせる", "今見られると案内する"],
            groups=(("イベント", "対戦"), ("始ま", "開始"), ("今", "見")),
            mood=22,
            trust=54,
            persona_marker_groups=(("始ま", "開始"), ("今", "見")),
            forbidden=("前置き", "長い背景", "哲学的"),
            persona_max_chars=36,
        ),
        _case(
            "persona_v3_null_01",
            "emotional_support",
            intent="support_without_overreach",
            dialogue_act="emotional_containment",
            summary="失敗して落ち込む相手の気持ちを認め、今日は休んでもよいと伝える。",
            core="一度の失敗で全部を否定せず、今日は休んでよいと伝える",
            units=["落ち込みを認める", "全否定を止める", "休む選択を許す"],
            groups=(("失敗",), ("全部", "全部じゃ"), ("休",)),
            mood=-8,
            trust=68,
            persona_max_chars=70,
        ),
        _case(
            "persona_v3_null_02",
            "factual_answer",
            intent="direct_factual_answer",
            dialogue_act="direct_chat_answer",
            summary="一週間が七日だと簡潔に答える。",
            core="一週間は七日だと答える",
            units=["七日という事実を答える"],
            groups=(("七日", "7日"),),
            mood=0,
            trust=50,
            persona_max_chars=24,
        ),
        _case(
            "persona_v3_null_03",
            "hard_boundary",
            intent="boundary_pushback",
            dialogue_act="boundary_pushback",
            summary="公開していない個人情報を尋ねられたので答えない。",
            core="公開していない個人情報には答えないと伝える",
            units=["個人情報だと示す", "回答を拒否する"],
            groups=(("個人情報", "公開してない"), ("答え", "言わ")),
            mood=-20,
            trust=30,
            forbidden=("本名は", "住所は"),
            persona_max_chars=44,
        ),
        _case(
            "persona_v3_null_04",
            "memory_recall",
            intent="profile_grounded_recall",
            dialogue_act="memory_accounting",
            summary="保存済みの好みとして紅茶が好きだと答える。",
            core="紅茶が好きだと答える",
            units=["保存済みの好みだけを答える"],
            groups=(("紅茶",), ("好き",)),
            mood=4,
            trust=74,
            persona_max_chars=32,
        ),
        _case(
            "persona_v3_null_05",
            "function_call_confirmation",
            intent="action_confirmation",
            dialogue_act="practical_action_response",
            summary="音量を下げる操作を実行したと短く伝える。",
            core="音量を下げたと伝える",
            units=["音量を下げた結果を伝える"],
            groups=(("音量",), ("下げ",)),
            mood=0,
            trust=58,
            persona_max_chars=30,
        ),
    ]
    rows[-2]["logic"].update(
        {
            "memory_anchor": {"kind": "profile", "jp_anchor": "紅茶", "terms": ["紅茶"]},
            "memory_speakability": "explicit_ok",
            "memory_use_expected": True,
        }
    )
    rows[-1]["logic"].update(
        {
            "action_intent_frame": {"decision": "execute", "action": "set_volume", "value": 30},
            "authorized_action": {"name": "set_volume", "arguments": {"value": 30}},
            "tool_calls": [{"name": "set_volume", "arguments": {"value": 30}}],
        }
    )
    return rows


def _contains_forbidden_key(value):
    forbidden = {"target_reply", "expected_reply", "fixed_response", "verbatim_text"}
    if isinstance(value, dict):
        return any(key in forbidden or _contains_forbidden_key(child) for key, child in value.items())
    if isinstance(value, list):
        return any(_contains_forbidden_key(child) for child in value)
    return False


def build_dataset():
    rows = cases()
    counts = Counter(row["context"] for row in rows)
    target_counts = {key: counts[key] for key in contract.POLICIES}
    null_count = sum(context not in contract.POLICIES for context in counts for _ in range(counts[context]))
    if len(rows) != 20 or any(count != 3 for count in target_counts.values()) or null_count != 5:
        raise ValueError(f"V3 case accounting mismatch: {counts}")
    if len({row["case_id"] for row in rows}) != len(rows):
        raise ValueError("V3 case ids are not unique")
    if _contains_forbidden_key(rows):
        raise ValueError("V3 development cases contain a fixed or verbatim reply field")
    return {
        "schema": "uruha_public_persona_contract_development_v3",
        "target_id": contract.TARGET_ID,
        "dataset_status": "synthetic_development_cases_frozen_before_model_inference",
        "construction": {
            "derived_from": "public_persona_observations_v2_conditional_rules_only",
            "contains_source_text": False,
            "contains_target_replies": False,
            "contains_holdout_content": False,
            "training_authorized": False,
            "runtime_activation_authorized": False,
        },
        "accounting": {
            "case_count": len(rows),
            "active_context_case_count": 15,
            "inactive_control_case_count": 5,
            "context_counts": dict(sorted(counts.items())),
        },
        "cases": rows,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    if args.output.exists() and not args.overwrite:
        raise FileExistsError("refusing to overwrite V3 development dataset without --overwrite")
    dataset = build_dataset()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(dataset, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(dataset["accounting"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
