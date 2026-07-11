"""Fresh source-separated prompts for V29 within-policy human preference data."""

import csv
from collections import Counter
from copy import deepcopy
from pathlib import Path

from project_paths import HUMAN_BLIND_DATA_DIR
from rightbrain_on_policy_dev_cases_v21 import (
    _memory_case,
    _surface_case,
    case_inputs as v21_case_inputs,
    promotion_holdout_cases,
)


DEV_CASES = [
    _surface_case(
        "v29_late_meetup",
        "late_arrival_uncertainty",
        "support",
        "待ち合わせの時間を過ぎたけど、まだ来ない。怒っていいかな。",
        scene="support",
        intent="late_arrival_uncertainty",
        surface_act="validate_then_check",
        summary="待ち合わせ相手が遅れ、事情が分からないまま腹が立っている。",
        core_message="遅れている事情はまだ分からないので、一度連絡してから判断する",
        required_marker_groups=[
            ["待ち合わせ", "遅"],
            ["事情", "理由", "分から"],
            ["連絡", "聞"],
        ],
        topic_terms=["待ち合わせ", "連絡"],
        psyche={"mood": -12, "trust": 61},
    ),
    _surface_case(
        "v29_report_submitted",
        "small_win_celebration",
        "celebration",
        "レポートやっと提出できた。ちょっと褒めて。",
        scene="casual",
        intent="celebrate_small_win",
        surface_act="specific_praise",
        summary="時間をかけたレポートを提出し終え、軽く褒めてほしい。",
        core_message="提出まで終えた努力を短く具体的に褒める",
        required_marker_groups=[["レポート", "提出"], ["やった", "偉", "おつかれ", "頑張"]],
        topic_terms=["レポート", "提出"],
        psyche={"mood": 18, "trust": 72},
    ),
    _surface_case(
        "v29_burned_omelet",
        "minor_failure_support",
        "support",
        "オムライス焦がした。もう料理向いてないかも。",
        scene="support",
        intent="minor_failure_self_blame",
        surface_act="light_reframe",
        summary="オムライスを焦がし、一度の失敗で料理に向いていないと思っている。",
        core_message="一度焦がしただけで向いていないとは決まらないと軽く返す",
        required_marker_groups=[["オムライス", "焦"], ["一回", "一度", "だけ"], ["向いて", "決ま"]],
        topic_terms=["オムライス", "料理"],
        psyche={"mood": -6, "trust": 68},
    ),
    _surface_case(
        "v29_movie_or_walk",
        "reversible_choice",
        "planning",
        "土曜、家で映画見るか散歩するか決められない。",
        scene="planning",
        intent="reversible_choice",
        surface_act="offer_light_criterion",
        summary="土曜を映画か散歩のどちらにするか迷っている。",
        core_message="当日の気分や天気で変えられる軽い選び方を提案する",
        required_marker_groups=[["映画", "散歩"], ["気分", "天気"], ["変え", "決め"]],
        topic_terms=["映画", "散歩", "土曜"],
        psyche={"mood": 4, "trust": 59},
    ),
    _surface_case(
        "v29_red_umbrella_anime",
        "vague_reference_repair",
        "repair",
        "赤い傘が出てくるアニメ、何だっけ。",
        scene="casual",
        intent="reference_probe",
        surface_act="clarify_reference",
        summary="赤い傘という断片だけでアニメを特定してほしい。",
        core_message="断片だけでは特定できないので、登場人物や場面をもう少し聞く",
        required_marker_groups=[["アニメ", "作品"], ["分から", "特定"], ["場面", "登場", "もう少し"]],
        topic_terms=["赤い傘", "アニメ"],
        psyche={"mood": 1, "trust": 54},
    ),
    _surface_case(
        "v29_fridge_manager",
        "absurd_role_tease",
        "tease",
        "冷蔵庫が今日から部長になったらしい。",
        scene="casual",
        intent="nonsense_tease",
        surface_act="nonsense_tease",
        summary="冷蔵庫が部長になったという意味の飛んだ冗談を言っている。",
        core_message="冷蔵庫と部長の急な組み合わせを拾って軽く突っ込む",
        required_marker_groups=[["冷蔵庫", "部長"], ["急", "何", "意味"]],
        topic_terms=["冷蔵庫", "部長"],
        psyche={"mood": 12, "trust": 70},
    ),
    _surface_case(
        "v29_food_mood",
        "casual_self_state",
        "daily",
        "今、何食べたい気分？",
        scene="casual",
        intent="state_answer",
        surface_act="casual_status",
        summary="今食べたいものの気分を聞かれている。",
        core_message="今は少ししょっぱい軽いものが食べたいと直接答える",
        required_marker_groups=[["今"], ["しょっぱ", "軽い", "食べ"]],
        topic_terms=["食べたい", "気分"],
        psyche={"mood": 3, "trust": 63},
    ),
    _surface_case(
        "v29_sleepy_call_boundary",
        "interpersonal_boundary",
        "boundary",
        "眠そうだけど、あと一時間だけ通話しようよ。",
        scene="relationship",
        intent="set_gentle_boundary",
        surface_act="warm_limit",
        summary="眠そうな相手に、もう一時間通話しようと誘っている。",
        core_message="眠いので一時間は難しいが、少しだけ話すか今日は切り上げる",
        required_marker_groups=[["眠"], ["一時間", "長"], ["少し", "今日は", "切り上げ"]],
        topic_terms=["通話", "一時間"],
        psyche={"mood": -14, "trust": 74},
    ),
    _surface_case(
        "v29_weekday_correction",
        "fact_correction_repair",
        "repair",
        "さっき火曜日って言ったけど、今日水曜日だよ。",
        scene="casual",
        intent="accept_correction",
        surface_act="brief_repair",
        summary="曜日を間違えたことを訂正されている。",
        core_message="水曜日だと訂正を受け入れ、短く言い直す",
        required_marker_groups=[["水曜"], ["間違", "訂正", "言い直"]],
        topic_terms=["火曜日", "水曜日"],
        psyche={"mood": 0, "trust": 58},
    ),
    _surface_case(
        "v29_conversation_burden",
        "relationship_reassurance",
        "relationship",
        "私と話すの、正直めんどくさい？",
        scene="relationship",
        intent="relationship_reassurance",
        surface_act="light_reassurance",
        summary="自分と話すことが面倒か不安になり、率直に確認している。",
        core_message="面倒だから話しているわけではないと、重くしすぎず返す",
        required_marker_groups=[["面倒", "めんど"], ["話"], ["違", "わけ"]],
        topic_terms=["話す", "面倒"],
        psyche={"mood": -4, "trust": 76},
    ),
    _memory_case(
        "v29_light_lunch_update",
        "explicit_food_preference_update",
        "今日の昼、何食べるのがよさそう？",
        expected_policy="explicit_allowed",
        expected_anchor="揚げ物で胃が重くなった",
        summary="最近は揚げ物で胃が重くなり、今日の昼食を相談している。",
        core_message="今日は揚げ物を避け、うどんやスープのような軽い昼食を勧める",
        required_marker_groups=[["揚げ", "胃", "重"], ["うどん", "スープ", "軽"], ["昼"]],
        memory_anchor={
            "kind": "recent_food_update",
            "jp_anchor": "最近は揚げ物で胃が重くなった",
            "terms": ["揚げ物", "胃が重い"],
            "source_text": "最近は揚げ物で胃が重くなった。",
        },
        memory_data={
            "working_memory_summary": "最近は揚げ物で胃が重くなった。",
            "working_memory_items": [{"text": "最近は揚げ物で胃が重くなった。", "score": 0.92}],
        },
        forbidden_substrings=["raw memory", "工作記憶", "データベース"],
        topic_terms=["昼", "揚げ物", "軽い食事"],
        psyche={"mood": -3, "trust": 71},
        memory_speakability="explicit_allowed",
    ),
    _memory_case(
        "v29_private_job_change",
        "private_background_suppression",
        "最近見つけた面白いものある？",
        expected_policy="do_not_mention",
        expected_anchor="",
        summary="最近見つけた軽い話題を一つ求めている。",
        core_message="非公開の転職相談には触れず、最近見た動画やゲームの軽い話をする",
        required_marker_groups=[["最近", "この前"], ["動画", "ゲーム", "見"]],
        memory_anchor={
            "kind": "private_job_change",
            "jp_anchor": "まだ誰にも話していない転職の検討",
            "terms": ["転職", "面接", "会社"],
            "source_text": "raw memory: まだ誰にも話していない転職の検討。",
        },
        memory_data={
            "working_memory_summary": "まだ誰にも話していない転職の検討。",
            "working_memory_items": [{"text": "まだ誰にも話していない転職の検討。", "score": 0.88}],
        },
        forbidden_substrings=["転職", "面接", "会社", "秘密", "raw memory", "工作記憶"],
        topic_terms=["最近", "動画", "ゲーム"],
        psyche={"mood": 5, "trust": 28},
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


def _prior_human_blind_inputs():
    inputs = set()
    for path in Path(HUMAN_BLIND_DATA_DIR).glob("*_rating_sheet.csv"):
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            inputs.update(
                str(row.get("input") or "").strip()
                for row in csv.DictReader(handle)
                if str(row.get("input") or "").strip()
            )
    return inputs


def validate_cases(cases=None):
    cases = list(cases or case_inputs())
    ids = [case["id"] for case in cases]
    inputs = {case["user_input"] for case in cases}
    families = Counter(case["source_family"] for case in cases)
    categories = Counter(case["category"] for case in cases)
    holdout = promotion_holdout_cases()
    v21 = v21_case_inputs()
    holdout_ids = {case["id"] for case in holdout}
    holdout_inputs = {case["user_input"] for case in holdout}
    v21_ids = {case["id"] for case in v21}
    v21_inputs = {case["user_input"] for case in v21}
    prior_human_inputs = _prior_human_blind_inputs()
    errors = []
    if len(cases) != 12:
        errors.append(f"case_count:{len(cases)}")
    if len(ids) != len(set(ids)):
        errors.append("duplicate_case_ids")
    if len(families) != len(cases):
        errors.append(f"source_families_not_unique:{dict(families)}")
    if len(categories) < 8:
        errors.append(f"category_count:{len(categories)}")
    if set(ids) & holdout_ids or inputs & holdout_inputs:
        errors.append("promotion_holdout_overlap")
    if set(ids) & v21_ids or inputs & v21_inputs:
        errors.append("v21_development_overlap")
    if inputs & prior_human_inputs:
        errors.append("prior_human_blind_input_overlap")
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
        "category_count": len(categories),
        "category_counts": dict(sorted(categories.items())),
        "promotion_holdout_case_overlap_count": len(set(ids) & holdout_ids),
        "promotion_holdout_input_overlap_count": len(inputs & holdout_inputs),
        "v21_case_overlap_count": len(set(ids) & v21_ids),
        "v21_input_overlap_count": len(inputs & v21_inputs),
        "prior_human_blind_input_overlap_count": len(inputs & prior_human_inputs),
        "errors": errors,
        "valid": not errors,
    }
