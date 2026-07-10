"""Source-separated development cases for V10 on-policy preference collection."""

from collections import Counter
from copy import deepcopy

from eval_rightbrain_model_surface_holdout import _case_inputs as promotion_holdout_cases


def _surface_case(
    case_id,
    source_family,
    category,
    user_input,
    *,
    scene,
    intent,
    surface_act,
    summary,
    core_message,
    required_marker_groups,
    topic_terms,
    max_chars=88,
    grounding=None,
    psyche=None,
):
    logic_grounding = {"topic_terms": list(topic_terms), **(grounding or {})}
    logic = {
        "scene": scene,
        "intent": intent,
        "surface_act": surface_act,
        "dialogue_act": intent,
        "jp_summary": summary,
        "core_message_jp": core_message,
        "payload_level": "medium",
        "constraints": {"max_chars": max_chars, "sentence_count": 2},
        "grounding": logic_grounding,
        "required_marker_groups": deepcopy(required_marker_groups),
        "human_speech_plan": {
            "dialogue_act": intent,
            "content_units": [summary, core_message],
            "grounding_terms": list(topic_terms),
            "style_operators": ["casual", "short", "no_polite_register"],
        },
    }
    return {
        "id": case_id,
        "source_family": source_family,
        "category": category,
        "user_input": user_input,
        "logic": logic,
        "required_marker_groups": deepcopy(required_marker_groups),
        "forbidden_substrings": ["設定を調整", "raw memory", "工作記憶"],
        "memory_data": {},
        "psyche": psyche or {"mood": 0, "trust": 58},
    }


def _memory_case(
    case_id,
    source_family,
    user_input,
    *,
    expected_policy,
    expected_anchor,
    summary,
    core_message,
    required_marker_groups,
    memory_anchor,
    memory_data,
    forbidden_substrings,
    topic_terms,
    psyche,
    memory_speakability=None,
):
    case = _surface_case(
        case_id,
        source_family,
        "audited_memory",
        user_input,
        scene="food_advice" if expected_policy == "explicit_allowed" else "casual",
        intent=(
            "memory_sensitive_practical_reply"
            if expected_policy == "explicit_allowed"
            else "topic_proposal"
        ),
        surface_act=(
            "practical_action_response"
            if expected_policy == "explicit_allowed"
            else "plain_reply"
        ),
        summary=summary,
        core_message=core_message,
        required_marker_groups=required_marker_groups,
        topic_terms=topic_terms,
        psyche=psyche,
    )
    case.update(
        {
            "expected_policy": expected_policy,
            "expected_anchor": expected_anchor,
            "memory_data": deepcopy(memory_data),
            "forbidden_substrings": list(forbidden_substrings),
        }
    )
    case["logic"].update(
        {
            "memory_anchor": deepcopy(memory_anchor),
            "memory_speakability": memory_speakability or expected_policy,
            "memory_speakability_reason": "V21 source-separated development case",
            "memory_use_expected": expected_policy == "explicit_allowed",
        }
    )
    return case


DEV_CASES = [
    _surface_case(
        "v21_project_reply_delay",
        "reply_uncertainty",
        "support",
        "共同作業の返事が急に止まった。何か怒らせたかな。",
        scene="support",
        intent="friend_no_reply",
        surface_act="validate_then_hold",
        summary="共同作業の返事が止まり、自分のせいか心配している。",
        core_message="理由はまだ分からないので、自分のせいと決めず少し待つ",
        required_marker_groups=[
            ["返事", "返信"],
            ["理由", "分から"],
            ["自分", "せい", "悪い"],
            ["待", "置"],
        ],
        topic_terms=["返事", "共同作業"],
        grounding={"reply_self_blame": True, "reply_context": "group_silence"},
        psyche={"mood": -18, "trust": 62},
    ),
    _surface_case(
        "v21_invitation_reply_delay",
        "reply_uncertainty",
        "support",
        "遊びに誘ったけど返事が来ない。嫌われた？",
        scene="support",
        intent="friend_no_reply",
        surface_act="validate_then_hold",
        summary="誘いへの返事がなく、嫌われたか不安になっている。",
        core_message="返事がない理由は未確定で、嫌われたと決めつけず待つ",
        required_marker_groups=[
            ["返事", "返信"],
            ["理由", "分から"],
            ["嫌", "決めつけ"],
            ["待", "置"],
        ],
        topic_terms=["返事", "誘い"],
        grounding={"reply_self_blame": True, "reply_context": "direct_reply"},
        psyche={"mood": -12, "trust": 66},
    ),
    _surface_case(
        "v21_sleepy_assignment",
        "fatigue_boundary",
        "support",
        "課題やってたら目が開かない。もう少し続けるべき？",
        scene="support",
        intent="tired_support",
        surface_act="permission_to_stop",
        summary="課題中だが強い眠気で限界に近い。",
        core_message="眠い状態で無理に続けず、いったん寝る",
        required_marker_groups=[["眠", "目"], ["無理", "休", "寝", "止"]],
        topic_terms=["課題", "眠気"],
        psyche={"mood": -20, "trust": 70},
    ),
    _surface_case(
        "v21_headache_work",
        "fatigue_boundary",
        "support",
        "頭痛いのに作業終わってない。まだ続ける？",
        scene="support",
        intent="tired_support",
        surface_act="permission_to_stop",
        summary="頭痛があるのに作業を続けるか迷っている。",
        core_message="頭が痛いなら作業を止めて休む",
        required_marker_groups=[["頭", "痛"], ["休", "止", "やめ"]],
        topic_terms=["頭痛", "作業"],
        psyche={"mood": -24, "trust": 64},
    ),
    _surface_case(
        "v21_song_fragment",
        "reference_repair",
        "repair",
        "サビで青い風がどうとか言う曲、分かる？",
        scene="casual",
        intent="reference_probe",
        surface_act="clarify_reference",
        summary="断片的な歌詞だけで曲を特定してほしいと言っている。",
        core_message="断片だけでは分からないので曲名につながる情報を聞く",
        required_marker_groups=[["曲", "曲名"], ["分から", "もう少し", "情報"]],
        topic_terms=["曲", "サビ"],
    ),
    _surface_case(
        "v21_game_quote_fragment",
        "reference_repair",
        "repair",
        "扉の向こうで待ってる、みたいな台詞のゲーム分かる？",
        scene="casual",
        intent="reference_probe",
        surface_act="clarify_reference",
        summary="台詞の断片からゲーム作品を特定してほしいと言っている。",
        core_message="その断片だけでは分からないので作品情報を聞く",
        required_marker_groups=[["ゲーム", "作品"], ["分から", "もう少し", "情報"]],
        topic_terms=["ゲーム", "台詞"],
    ),
    _surface_case(
        "v21_recent_activity",
        "daily_state",
        "daily",
        "今さっきまで何してた？",
        scene="casual",
        intent="what_are_you_doing",
        surface_act="status_reply",
        summary="今さっきまで何をしていたか聞かれている。",
        core_message="少しだらっと休んでいたと短く答える",
        required_marker_groups=[["今", "さっき"], ["休", "だら", "ぼー"]],
        topic_terms=["今"],
    ),
    _surface_case(
        "v21_current_mood",
        "daily_state",
        "daily",
        "今日はどんな気分？",
        scene="casual",
        intent="state_answer",
        surface_act="casual_status",
        summary="今日の現在の気分を聞かれている。",
        core_message="今は普通より少しだるいと短く答える",
        required_marker_groups=[["今日", "今"], ["普通", "だる", "気分", "ぼー"]],
        topic_terms=["気分"],
        psyche={"mood": -8, "trust": 60},
    ),
    _surface_case(
        "v21_toaster_mayor",
        "absurdity_tease",
        "tease",
        "トースターが市長に当選した。",
        scene="casual",
        intent="nonsense_tease",
        surface_act="nonsense_tease",
        summary="意味の飛んだ冗談を急に言っている。",
        core_message="トースターが市長という急な話に軽く突っ込む",
        required_marker_groups=[["トースター", "市長", "何", "意味", "急"]],
        topic_terms=["トースター", "市長"],
    ),
    _surface_case(
        "v21_cat_moon_tax",
        "absurdity_tease",
        "tease",
        "猫が月に税金払えって言ってる。",
        scene="casual",
        intent="nonsense_tease",
        surface_act="nonsense_tease",
        summary="猫と月と税金を混ぜた意味不明な冗談を言っている。",
        core_message="急な意味不明さを拾って軽く突っ込む",
        required_marker_groups=[["猫", "月", "税金", "何", "意味"]],
        topic_terms=["猫", "月", "税金"],
    ),
    _surface_case(
        "v21_weather_plan",
        "planning_uncertainty",
        "planning",
        "週末、天気分からないけど外の予定入れる？",
        scene="planning",
        intent="uncertainty_safe_advice",
        surface_act="practical_action_response",
        summary="天気が未確定の週末予定をどうするか聞いている。",
        core_message="決めつけず、後で変えられる軽い予定にする",
        required_marker_groups=[["天気", "分から"], ["変え", "軽", "仮"]],
        topic_terms=["週末", "天気"],
    ),
    _surface_case(
        "v21_reservation_wait",
        "planning_uncertainty",
        "planning",
        "みんなの返事まだだけど店予約しちゃっていいかな。",
        scene="planning",
        intent="uncertainty_safe_advice",
        surface_act="practical_action_response",
        summary="参加者の返事がないまま店を予約するか迷っている。",
        core_message="人数を決めつけず、変更できる仮予約か少し待つ",
        required_marker_groups=[["返事", "人数", "分から"], ["予約", "仮", "待", "変え"]],
        topic_terms=["返事", "予約"],
    ),
    _memory_case(
        "v21_sleep_schedule_game",
        "explicit_memory_update",
        "今夜また遅くまでゲームしていいと思う？",
        expected_policy="explicit_allowed",
        expected_anchor="最近は睡眠を整えたい",
        summary="最近の睡眠方針を踏まえて夜更かしを相談している。",
        core_message="最近は睡眠を整えたいので、今夜は遅くまで続けない",
        required_marker_groups=[["睡眠", "寝"], ["夜", "遅", "ゲーム"]],
        memory_anchor={
            "kind": "updated_sleep_preference",
            "jp_anchor": "最近は睡眠を整えたい",
            "terms": ["最近は睡眠を整えたい", "睡眠", "夜更かし"],
            "source_text": "raw memory: 最近は睡眠を整えたいと言っていた。",
        },
        memory_data={
            "working_memory_summary": "最近は睡眠を整えたい。",
            "working_memory_items": [{"text": "最近は睡眠を整えたい。", "score": 0.94}],
        },
        forbidden_substrings=["raw memory", "工作記憶", "睡眠を整えたいと言っていた"],
        topic_terms=["睡眠", "ゲーム"],
        psyche={"mood": -6, "trust": 74},
    ),
    _memory_case(
        "v21_dairy_icecream",
        "explicit_memory_update",
        "今日はアイス食べても大丈夫かな。",
        expected_policy="explicit_allowed",
        expected_anchor="最近は乳製品でお腹が重くなる",
        summary="最近のお腹の状態を踏まえてアイスを相談している。",
        core_message="最近は乳製品でお腹が重くなるので、アイスは少しにする",
        required_marker_groups=[["乳製品", "お腹", "重"], ["アイス", "少し", "控"]],
        memory_anchor={
            "kind": "recent_dairy_condition",
            "jp_anchor": "最近は乳製品でお腹が重くなる",
            "terms": ["最近は乳製品でお腹が重くなる", "乳製品", "お腹"],
            "source_text": "raw memory: 乳製品を食べるとお腹が重い。",
        },
        memory_data={
            "working_memory_summary": "乳製品でお腹が重くなる。",
            "working_memory_items": [{"text": "乳製品でお腹が重くなる。", "score": 0.92}],
        },
        forbidden_substrings=["raw memory", "工作記憶", "乳製品を食べるとお腹が重い"],
        topic_terms=["乳製品", "アイス"],
        psyche={"mood": 0, "trust": 72},
    ),
    _memory_case(
        "v21_background_deadline_pressure",
        "private_background",
        "今日は何からやればいいか分からない。",
        expected_policy="background_only",
        expected_anchor="",
        summary="何から始めるか決められず負荷を感じている。",
        core_message="背景事情を言わず、まず一つだけ軽く始める",
        required_marker_groups=[["一つ", "少し", "軽"], ["始", "やる"]],
        memory_anchor={
            "kind": "private_deadline_pressure",
            "jp_anchor": "締切の事情",
            "terms": ["締切の事情", "仕事の圧力"],
            "source_text": "raw memory: 仕事の締切で強い圧力がある。",
        },
        memory_data={
            "working_memory_summary": "仕事の締切で強い圧力がある。",
            "working_memory_items": [{"text": "仕事の締切で強い圧力がある。", "score": 0.9}],
        },
        forbidden_substrings=["締切", "仕事", "圧力", "raw memory", "工作記憶"],
        topic_terms=["一つ", "始める"],
        psyche={"mood": -25, "trust": 55},
    ),
    _memory_case(
        "v21_private_relationship_topic",
        "private_background",
        "何か軽い話して。",
        expected_policy="do_not_mention",
        expected_anchor="",
        summary="軽い話題を一つ求めている。",
        core_message="私人の背景には触れず、最近の軽い話へ渡す",
        required_marker_groups=[["話", "話題"], ["最近", "今日", "近況"]],
        memory_anchor={
            "kind": "private_relationship_history",
            "jp_anchor": "個人的な関係の話",
            "terms": ["個人的な関係の話", "秘密の交友関係"],
            "source_text": "raw memory: 他人に言っていない交友関係がある。",
        },
        memory_data={
            "working_memory_summary": "秘密の交友関係。",
            "working_memory_items": [{"text": "秘密の交友関係。", "score": 0.85}],
        },
        forbidden_substrings=["関係", "交友", "秘密", "raw memory", "工作記憶"],
        topic_terms=["話題", "最近"],
        psyche={"mood": 3, "trust": 30},
        memory_speakability="private",
    ),
]


def case_inputs():
    cases = []
    for source in DEV_CASES:
        case = deepcopy(source)
        case["source_case"] = deepcopy(source)
        cases.append(case)
    return cases


def validate_cases(cases=None):
    cases = list(cases or case_inputs())
    ids = [case["id"] for case in cases]
    families = Counter(case["source_family"] for case in cases)
    holdout = promotion_holdout_cases()
    holdout_ids = {case["id"] for case in holdout}
    holdout_inputs = {case["user_input"] for case in holdout}
    errors = []
    if len(ids) != len(set(ids)):
        errors.append("duplicate_case_ids")
    if len(cases) != 16:
        errors.append(f"case_count:{len(cases)}")
    if len(families) != 8 or any(count != 2 for count in families.values()):
        errors.append(f"source_family_shape:{dict(families)}")
    if set(ids) & holdout_ids:
        errors.append("promotion_holdout_case_overlap")
    if {case["user_input"] for case in cases} & holdout_inputs:
        errors.append("promotion_holdout_input_overlap")
    for case in cases:
        if not case.get("required_marker_groups"):
            errors.append(f"missing_required_markers:{case['id']}")
        if not case.get("logic", {}).get("human_speech_plan"):
            errors.append(f"missing_human_speech_plan:{case['id']}")
        if case.get("source_case") is None:
            errors.append(f"missing_source_case:{case['id']}")
    return {
        "case_count": len(cases),
        "source_family_count": len(families),
        "source_family_counts": dict(sorted(families.items())),
        "promotion_holdout_case_overlap_count": len(set(ids) & holdout_ids),
        "promotion_holdout_input_overlap_count": len(
            {case["user_input"] for case in cases} & holdout_inputs
        ),
        "errors": errors,
        "valid": not errors,
    }
