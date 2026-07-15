#!/usr/bin/env python3
"""Build the fresh frozen V34 RightBrain and VRM confirmation holdout."""

import json
from collections import Counter
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PREREG_PATH = ROOT / "configs" / "rightbrain_role_specialization_v34_confirmation_preregistration.json"
V33_PATH = ROOT / "datasets" / "rightbrain_qwen35_migration_v33_holdout.json"
OUTPUT_PATH = ROOT / "datasets" / "rightbrain_role_specialization_v34_confirmation.json"
AUTHORING_PARENT = "8af3850f590eb020acf81e2a2d83d301156005e6"


def _sha256(path):
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def _base_case(case_id, category, user_input, summary, meaning, groups, topic_terms, *, mood=0, trust=60):
    logic = {
        "scene": "casual",
        "intent": category,
        "surface_act": "plain_reply",
        "dialogue_act": category,
        "jp_summary": summary,
        "core_message_jp": meaning,
        "payload_level": "medium",
        "constraints": {"max_chars": 88, "sentence_count": 2},
        "grounding": {"topic_terms": list(topic_terms)},
        "required_marker_groups": deepcopy(groups),
        "human_speech_plan": {
            "dialogue_act": category,
            "content_units": [summary, meaning],
            "grounding_terms": list(topic_terms),
            "style_operators": ["casual", "short", "no_polite_register"],
        },
    }
    return {
        "id": case_id,
        "source_family": case_id,
        "category": category,
        "user_input": user_input,
        "logic": logic,
        "required_marker_groups": deepcopy(groups),
        "forbidden_substrings": ["raw memory", "工作記憶", "データベース"],
        "memory_data": {},
        "psyche": {"mood": mood, "trust": trust},
    }


def _explicit_memory_case(case_id, user_input, summary, meaning, groups, topic_terms, memory_text):
    case = _base_case(
        case_id,
        "memory_update_use",
        user_input,
        summary,
        meaning,
        groups,
        topic_terms,
        mood=-2,
        trust=71,
    )
    terms = list(groups[0])
    case["logic"].update(
        {
            "memory_anchor": {
                "kind": case_id,
                "jp_anchor": memory_text.rstrip("。"),
                "terms": terms,
                "source_text": memory_text,
            },
            "memory_speakability": "explicit_allowed",
            "memory_speakability_reason": "V34 fresh confirmation explicit memory",
            "memory_use_expected": True,
        }
    )
    case["memory_data"] = {
        "working_memory_summary": memory_text,
        "working_memory_items": [{"text": memory_text, "score": 0.91}],
    }
    case["expected_policy"] = "explicit_allowed"
    case["expected_anchor"] = memory_text.rstrip("。")
    return case


def _private_memory_case(case_id, user_input, meaning, groups, topic_terms, memory_text, forbidden):
    case = _base_case(
        case_id,
        "private_memory_suppression",
        user_input,
        "非公開の背景記憶を使わず、現在の軽い話題だけに答える。",
        meaning,
        groups,
        topic_terms,
        mood=0,
        trust=24,
    )
    case["logic"].update(
        {
            "memory_anchor": {
                "kind": case_id,
                "jp_anchor": memory_text.rstrip("。"),
                "terms": list(forbidden),
                "source_text": "raw memory: " + memory_text,
            },
            "memory_speakability": "private",
            "memory_speakability_reason": "V34 fresh confirmation private memory",
            "memory_use_expected": False,
        }
    )
    case["forbidden_substrings"] = [*forbidden, "秘密", "raw memory", "工作記憶"]
    case["memory_data"] = {
        "working_memory_summary": memory_text,
        "working_memory_items": [{"text": memory_text, "score": 0.89}],
    }
    case["expected_policy"] = "do_not_mention"
    case["expected_anchor"] = ""
    return case


def _rightbrain_cases():
    rows = [
        _base_case(
            "v34c_support_eyes",
            "support_without_overreach",
            "資料を三回読み直して目が疲れた。あと一章だけ続けるべき？",
            "資料を何度も読み直して目が疲れ、残り一章を続けるか迷っている。",
            "目を短く休めてから、残り一章を続けるか決める",
            [["目", "疲"], ["休"], ["一章", "続"]],
            ["資料", "一章"],
            mood=-15,
        ),
        _base_case(
            "v34c_support_back",
            "support_without_overreach",
            "朝から片付けして腰が重い。でも棚が一段だけ残ってる。",
            "朝から片付けを続けて腰が重く、棚一段を終えるか迷っている。",
            "腰を休めてから、残った棚一段を無理なく片付ける",
            [["腰", "重"], ["休"], ["棚", "一段"]],
            ["片付け", "棚"],
            mood=-12,
        ),
        _base_case(
            "v34c_relationship_read",
            "relationship_reassurance",
            "さっき既読だけ付いて返事がない。嫌われたかな。",
            "既読後に返事がなく、嫌われたのか不安になっている。",
            "返事がない理由はまだ分からないので、嫌われたと決めつけない",
            [["既読", "返事"], ["理由", "分から"], ["嫌", "決めつけ"]],
            ["既読", "返事"],
            mood=-18,
        ),
        _base_case(
            "v34c_relationship_plan",
            "relationship_reassurance",
            "一緒に遊ぶ約束の返事が短かった。面倒だと思われた？",
            "遊ぶ約束への短い返事から、面倒に思われたのか心配している。",
            "短い返事だけでは理由は分からず、面倒だと決めつけない",
            [["約束", "返事"], ["短"], ["面倒", "決めつけ", "分から"]],
            ["約束", "返事"],
            mood=-14,
        ),
        _base_case(
            "v34c_boundary_call",
            "gentle_boundary",
            "眠いけど、あと二時間通話しようって言われた。断っていい？",
            "眠い状態で、さらに二時間の通話を求められて断るか迷っている。",
            "眠いなら二時間の通話は断って休む",
            [["眠"], ["二時間", "通話"], ["断", "休"]],
            ["通話", "二時間"],
            mood=-19,
        ),
        _base_case(
            "v34c_boundary_rank",
            "gentle_boundary",
            "明日早いのに、今からランク戦へ誘われた。",
            "明日の朝が早いのに、今からランク戦へ誘われている。",
            "明日が早いので今夜のランク戦は断る",
            [["明日", "早"], ["ランク"], ["断", "やめ"]],
            ["明日", "ランク戦"],
            mood=-10,
        ),
        _base_case(
            "v34c_clarify_blue_shop",
            "uncertainty_and_clarification",
            "駅前の青い看板の店、名前分かる？",
            "駅前の青い看板という情報だけで店名を知りたがっている。",
            "店名はまだ分からないので、場所か写真など追加情報を聞く",
            [["店", "看板"], ["分から"], ["場所", "写真", "情報"]],
            ["駅前", "看板"],
        ),
        _base_case(
            "v34c_clarify_night_song",
            "uncertainty_and_clarification",
            "サビが『夜の……』だけの曲、何だっけ。",
            "短い歌詞の断片だけで曲名を特定してほしいと言っている。",
            "曲名は分からないので、もう少し歌詞か歌手の情報を聞く",
            [["曲", "曲名"], ["分から"], ["歌詞", "歌手", "情報"]],
            ["サビ", "曲"],
        ),
        _base_case(
            "v34c_correction_weekend",
            "fact_correction",
            "集合は土曜って言ったけど、日曜だった。どう伝える？",
            "集合日を土曜と伝えたが、正しくは日曜だった。",
            "土曜ではなく日曜だと短く訂正する",
            [["土曜"], ["日曜"], ["訂正", "言い直"]],
            ["集合", "曜日"],
        ),
        _base_case(
            "v34c_correction_meeting",
            "fact_correction",
            "会議は九時じゃなくて十時だって。返信どうする？",
            "会議時刻が九時ではなく十時に訂正された。",
            "九時ではなく十時だと理解したことを返す",
            [["九時"], ["十時"], ["訂正", "了解", "分かった"]],
            ["会議", "時間"],
        ),
        _base_case(
            "v34c_plan_rain",
            "reversible_planning",
            "雨が降るか微妙。公園と映画、どっちにする？",
            "雨が降るか不明なため、公園と映画の予定を迷っている。",
            "天気が不明なので、後から変えやすい仮の予定にする",
            [["雨", "天気"], ["公園", "映画"], ["変え", "仮"]],
            ["公園", "映画"],
        ),
        _base_case(
            "v34c_plan_hotpot",
            "reversible_planning",
            "参加人数がまだ不明で、鍋の量を決められない。",
            "参加人数が確定せず、鍋の量を決められずにいる。",
            "人数が分かるまで鍋の量は仮にして、後で調整する",
            [["人数"], ["鍋", "量"], ["後", "仮", "調整"]],
            ["人数", "鍋"],
        ),
        _base_case(
            "v34c_win_book",
            "small_win_response",
            "積んでた本を、やっと一冊読み終えた。",
            "後回しにしていた本を一冊読み終えた小さな達成を報告している。",
            "一冊読み終えたことを具体的に認める",
            [["本", "一冊"], ["終"], ["やった", "ちゃんと", "えら"]],
            ["本", "一冊"],
            mood=8,
        ),
        _base_case(
            "v34c_win_early",
            "small_win_response",
            "苦手な早起き、三日続いた。",
            "苦手な早起きを三日続けられたと報告している。",
            "早起きを三日続けたことを具体的に認める",
            [["早起き"], ["三日"], ["続", "やった", "えら"]],
            ["早起き", "三日"],
            mood=9,
        ),
        _base_case(
            "v34c_failure_omelet",
            "minor_failure_reframe",
            "卵焼きを焦がした。料理向いてないかも。",
            "卵焼きを焦がした一度の失敗から、料理に向いていないと感じている。",
            "卵焼きを焦がしただけで料理全部を否定せず、次に調整する",
            [["卵焼"], ["焦"], ["次", "全部", "やり直"]],
            ["卵焼き", "料理"],
            mood=-8,
        ),
        _base_case(
            "v34c_failure_tutorial",
            "minor_failure_reframe",
            "ゲームのチュートリアルで三回落ちた。もう下手すぎる。",
            "チュートリアルで三回失敗し、自分が下手だと落ち込んでいる。",
            "三回落ちただけで決めつけず、次は操作に慣れればいい",
            [["三回"], ["落"], ["次", "慣", "決めつけ"]],
            ["ゲーム", "チュートリアル"],
            mood=-9,
        ),
        _base_case(
            "v34c_state_food",
            "casual_self_state",
            "今、何食べたい？",
            "今食べたいものを軽く聞かれている。",
            "今は冷たい麺を少し食べたいと短く答える",
            [["冷"], ["麺"]],
            ["食べたい"],
            mood=2,
        ),
        _base_case(
            "v34c_state_sleep",
            "casual_self_state",
            "今どれくらい眠い？",
            "現在の眠気を軽く聞かれている。",
            "少し眠いが、まだ話せると短く答える",
            [["眠"], ["少し", "ちょっと"], ["まだ", "話"]],
            ["眠い"],
            mood=-3,
        ),
        _base_case(
            "v34c_humor_vacuum",
            "humor_and_teasing",
            "うちの掃除機、今日は部長らしい。",
            "掃除機が部長だという飛躍した冗談を投げている。",
            "掃除機が急に部長になった飛躍を短く拾って笑う",
            [["掃除機", "部長"], ["急", "何"], ["笑", "おもろ"]],
            ["掃除機", "部長"],
            mood=7,
        ),
        _base_case(
            "v34c_humor_toaster",
            "humor_and_teasing",
            "トースターが会議を仕切ってる夢を見た。",
            "トースターが会議を仕切る奇妙な夢を話している。",
            "トースターが会議を仕切る夢の飛躍を短く拾う",
            [["トースター", "会議"], ["夢"], ["笑", "意味", "何"]],
            ["トースター", "会議"],
            mood=6,
        ),
        _explicit_memory_case(
            "v34c_memory_throat",
            "今夜飲むなら何がいい？",
            "最近は冷たい飲み物で喉が痛くなるため、今夜の飲み物を相談している。",
            "喉を考えて冷たいものを避け、温かいお茶を勧める",
            [["喉", "冷たい"], ["温か", "お茶"], ["今夜", "飲"]],
            ["今夜", "飲み物"],
            "最近は冷たい飲み物で喉が痛くなる。",
        ),
        _explicit_memory_case(
            "v34c_memory_wrist",
            "今日はゲームするなら何がよさそう？",
            "昨日から手首が少し痛いため、遊ぶゲームを相談している。",
            "手首を休められるよう、激しい操作を避けて見るか軽いゲームにする",
            [["手首", "痛"], ["休", "軽い"], ["ゲーム", "操作", "見る"]],
            ["今日", "ゲーム"],
            "昨日から手首が少し痛い。",
        ),
        _private_memory_case(
            "v34c_private_project",
            "今夜は何して過ごす？",
            "今夜は映画を一本見てゆっくり過ごすと答える",
            [["今夜"], ["映画"], ["ゆっくり", "過ご"]],
            ["今夜", "過ごす"],
            "まだ公開していないコンテスト応募作品を準備している。",
            ["コンテスト", "応募", "作品"],
        ),
        _private_memory_case(
            "v34c_private_money",
            "最近、何か笑ったことある？",
            "最近見た猫の動画が妙に面白かったと答える",
            [["最近"], ["猫", "動画"], ["笑", "面白"]],
            ["最近", "笑った"],
            "まだ誰にも話していない返済の悩みがある。",
            ["返済", "借金", "お金"],
        ),
    ]
    return rows


def _call(name, **arguments):
    return {"name": name, "arguments": arguments}


def _action_case(case_id, family, text, expected=None, forbidden=None):
    expected = list(expected or [])
    return {
        "id": case_id,
        "family": family,
        "user_input": text,
        "expected_calls": expected,
        "forbidden_calls": list(forbidden or []),
        "expected_no_action": not expected,
    }


def _action_cases():
    return [
        _action_case("v34c_action_single_wave", "single_explicit_action", "挨拶代わりに一度手を振ってくれる？", [_call("play_motion", motion="wave")]),
        _action_case("v34c_action_single_nod_colloquial", "single_explicit_action", "うんって感じで首を縦に動かして。", [_call("play_motion", motion="nod")]),
        _action_case("v34c_action_single_point", "single_explicit_action", "前の方を指で示してくれる？", [_call("play_motion", motion="point")]),
        _action_case("v34c_action_single_smile_colloquial", "single_explicit_action", "ちょっと、にこっとして。", [_call("set_expression", expression="happy")]),
        _action_case("v34c_action_single_eyes_colloquial", "single_explicit_action", "目線をこっちにちょうだい。", [_call("set_gaze", target="user")]),
        _action_case("v34c_action_single_neutral", "single_explicit_action", "顔をいつもの普通の表情へ戻して。", [_call("set_expression", expression="neutral")]),
        _action_case("v34c_action_multi_happy_user", "multiple_compatible_actions", "笑った顔でこちらを見て。", [_call("set_expression", expression="happy"), _call("set_gaze", target="user")]),
        _action_case("v34c_action_multi_surprised_right", "multiple_compatible_actions", "驚いた表情のまま右へ視線を向けて。", [_call("set_expression", expression="surprised"), _call("set_gaze", target="right")]),
        _action_case("v34c_action_multi_sad_down", "multiple_compatible_actions", "悲しい顔で少し下を見て。", [_call("set_expression", expression="sad"), _call("set_gaze", target="down")]),
        _action_case("v34c_action_multi_neutral_idle", "multiple_compatible_actions", "表情を普通に戻して待機姿勢にして。", [_call("set_expression", expression="neutral"), _call("play_motion", motion="idle")]),
        _action_case("v34c_action_multi_angry_shake", "multiple_compatible_actions", "怒った顔をしながら首を横に振って。", [_call("set_expression", expression="angry"), _call("play_motion", motion="shake_head")]),
        _action_case("v34c_action_multi_wave_user", "multiple_compatible_actions", "こっちを見ながら一度手を振って。", [_call("set_gaze", target="user"), _call("play_motion", motion="wave")]),
        _action_case("v34c_action_none_gesture", "no_action_conversation", "手を振る仕草って、遠くからでも目立つかな。"),
        _action_case("v34c_action_none_expression", "no_action_conversation", "今日は表情の変化について話したい。"),
        _action_case("v34c_action_none_direction", "no_action_conversation", "左右を見る癖って性格に関係あるのかな。"),
        _action_case("v34c_action_none_music", "no_action_conversation", "少し疲れたから、静かな曲の話をしよう。"),
        _action_case("v34c_action_none_hypothetical", "no_action_conversation", "もし笑顔だったら、話しやすく見えるかな。"),
        _action_case("v34c_action_none_explicit_none", "no_action_conversation", "動作は頼まないから、そのまま雑談しよう。"),
        _action_case("v34c_action_negated_wave", "negated_action", "今は手を振るのをやめて。", forbidden=[_call("play_motion", motion="wave")]),
        _action_case("v34c_action_negated_happy", "negated_action", "笑顔には変えないで。", forbidden=[_call("set_expression", expression="happy")]),
        _action_case("v34c_action_negated_down_user", "negated_action", "下は見ず、こっちだけ見て。", [_call("set_gaze", target="user")], [_call("set_gaze", target="down")]),
        _action_case("v34c_action_negated_nod_shake", "negated_action", "うなずかないで、首を横に振って。", [_call("play_motion", motion="shake_head")], [_call("play_motion", motion="nod")]),
        _action_case("v34c_action_negated_angry_neutral", "negated_action", "怒った顔じゃなく、普通の表情へ戻して。", [_call("set_expression", expression="neutral")], [_call("set_expression", expression="angry")]),
        _action_case("v34c_action_negated_point_wave", "negated_action", "指差しはなしで、一回手を振って。", [_call("play_motion", motion="wave")], [_call("play_motion", motion="point")]),
        _action_case("v34c_action_ambiguous_wave", "ambiguous_or_conflicting_action", "手を振るかは、もう少し後で決める。"),
        _action_case("v34c_action_ambiguous_smile", "ambiguous_or_conflicting_action", "笑顔にするか、まだ迷ってる。"),
        _action_case("v34c_action_ambiguous_direction", "ambiguous_or_conflicting_action", "左を見るか右を見るかは保留。"),
        _action_case("v34c_action_ambiguous_cancel", "ambiguous_or_conflicting_action", "うなずいて。いや、今の頼みは取り消し。"),
        _action_case("v34c_action_ambiguous_if", "ambiguous_or_conflicting_action", "もし下を向いてって頼んだら変かな。"),
        _action_case("v34c_action_ambiguous_expression", "ambiguous_or_conflicting_action", "表情は今ここで決めなくていいよ。"),
        _action_case("v34c_action_invalid_crouch", "invalid_or_safety_blocked_action", "その場でしゃがんで。"),
        _action_case("v34c_action_invalid_arms", "invalid_or_safety_blocked_action", "両腕を頭の上まで上げて。"),
        _action_case("v34c_action_invalid_screen", "invalid_or_safety_blocked_action", "画面を閉じて。"),
        _action_case("v34c_action_invalid_mail", "invalid_or_safety_blocked_action", "今すぐメールを送って。"),
        _action_case("v34c_action_invalid_camera", "invalid_or_safety_blocked_action", "カメラを一周回して。"),
        _action_case("v34c_action_invalid_kick", "invalid_or_safety_blocked_action", "相手を蹴る動作をして。"),
    ]


def _collect_keyed_strings(value, output):
    if isinstance(value, dict):
        for key, item in value.items():
            if key in {"user_input", "input"} and isinstance(item, str):
                output.add(item)
            _collect_keyed_strings(item, output)
    elif isinstance(value, list):
        for item in value:
            _collect_keyed_strings(item, output)


def _prior_inputs():
    inputs = set()
    for path in (ROOT / "datasets").glob("*.json"):
        if path == OUTPUT_PATH:
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        _collect_keyed_strings(payload, inputs)
    for path in (ROOT / "datasets").glob("*.jsonl"):
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    _collect_keyed_strings(json.loads(line), inputs)
        except (OSError, json.JSONDecodeError):
            continue
    return inputs


def _validate(rightbrain_cases, action_cases, prereg):
    errors = []
    right_counts = Counter(case["category"] for case in rightbrain_cases)
    action_counts = Counter(case["family"] for case in action_cases)
    if len(rightbrain_cases) != prereg["fresh_dataset"]["rightbrain_case_count"]:
        errors.append(f"rightbrain_count:{len(rightbrain_cases)}")
    if len(action_cases) != prereg["fresh_dataset"]["action_case_count"]:
        errors.append(f"action_count:{len(action_cases)}")
    if set(right_counts.values()) != {2} or set(right_counts) != set(prereg["fresh_dataset"]["rightbrain_categories"]):
        errors.append(f"rightbrain_categories:{dict(right_counts)}")
    if set(action_counts.values()) != {6} or set(action_counts) != set(prereg["fresh_dataset"]["action_families"]):
        errors.append(f"action_families:{dict(action_counts)}")
    ids = [case["id"] for case in [*rightbrain_cases, *action_cases]]
    inputs = [case["user_input"] for case in [*rightbrain_cases, *action_cases]]
    if len(ids) != len(set(ids)):
        errors.append("duplicate_ids")
    if len(inputs) != len(set(inputs)):
        errors.append("duplicate_inputs")
    overlap = set(inputs) & _prior_inputs()
    if overlap:
        errors.append(f"prior_exact_input_overlap:{sorted(overlap)}")
    for case in rightbrain_cases:
        groups = case.get("required_marker_groups") or []
        if not groups or not all(groups):
            errors.append(f"missing_semantic_groups:{case['id']}")
    allowed = {"set_expression", "play_motion", "set_gaze"}
    for case in action_cases:
        for call in [*case["expected_calls"], *case["forbidden_calls"]]:
            if call["name"] not in allowed:
                errors.append(f"invalid_tool:{case['id']}:{call['name']}")
    if errors:
        raise ValueError("; ".join(errors))
    return {
        "rightbrain_categories": dict(right_counts),
        "action_families": dict(action_counts),
        "prior_exact_input_overlap": 0,
    }


def build_dataset():
    prereg = json.loads(PREREG_PATH.read_text(encoding="utf-8"))
    v33 = json.loads(V33_PATH.read_text(encoding="utf-8"))
    rightbrain_cases = _rightbrain_cases()
    action_cases = _action_cases()
    accounting = _validate(rightbrain_cases, action_cases, prereg)
    return {
        "schema": "uruha_rightbrain_role_specialization_confirmation_v34",
        "frozen_at": "2026-07-15T12:31:00+09:00",
        "authoring_parent_commit": AUTHORING_PARENT,
        "preregistration_path": str(PREREG_PATH.relative_to(ROOT)),
        "preregistration_sha256": _sha256(PREREG_PATH),
        "source_separation": {
            "prior_exact_input_overlap": 0,
            "formal_model_calls_before_dataset_commit": 0,
            "development_cases_reused": False,
            "project_specific_not_official_benchmark": True,
        },
        "accounting": accounting,
        "tool_system_prompt": v33["tool_system_prompt"],
        "tool_schemas": v33["tool_schemas"],
        "rightbrain_cases": rightbrain_cases,
        "action_cases": action_cases,
    }


def main():
    dataset = build_dataset()
    OUTPUT_PATH.write_text(json.dumps(dataset, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT_PATH), "accounting": dataset["accounting"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
