#!/usr/bin/env python3
"""Evaluate the RightBrain audited-memory brief contract without model inference."""

import json
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from project_paths import (
    RIGHTBRAIN_AUDITED_MEMORY_BRIEF_EVAL_REPORT_JSON_PATH,
    RIGHTBRAIN_AUDITED_MEMORY_BRIEF_EVAL_REPORT_MD_PATH,
)
from uruha_brain_mac import RIGHT_BRAIN_MODEL_CONTRACT_VERSION, RightBrain


TZ = ZoneInfo("Asia/Tokyo")


def _base_logic():
    return {
        "scene": "food_advice",
        "intent": "memory_sensitive_practical_reply",
        "surface_act": "practical_action_response",
        "dialogue_act": "practical_action_response",
        "jp_summary": "ユーザーが今の体調を踏まえた飲食の相談をしている。",
        "core_message_jp": "最近の体調を踏まえて、無理のない選択に寄せる",
        "constraints": {"max_chars": 80, "sentence_count": 2},
        "grounding": {"topic_terms": ["体調", "飲食"]},
        "human_speech_plan": {
            "dialogue_act": "practical_action_response",
            "content_units": ["最近の体調を踏まえる", "無理のない選択に寄せる"],
            "speech_moves": [
                {"role": "answer"},
                {"role": "soft_boundary"},
            ],
            "grounding_terms": ["体調"],
            "style_operators": ["casual", "short"],
        },
    }


CASES = [
    {
        "id": "explicit_stomach_coffee",
        "description": "使用者問咖啡，最近胃不舒服是可以明講的相關記憶。",
        "expected_policy": "explicit_allowed",
        "expected_anchor": "最近は胃が弱い",
        "logic_update": {
            "jp_summary": "ユーザーが胃の調子とコーヒーについて相談している。",
            "core_message_jp": "最近は胃が弱いことを踏まえて、コーヒーは控えめにする",
            "memory_anchor": {
                "kind": "recent_stomach_condition",
                "jp_anchor": "最近は胃が弱い",
                "terms": ["最近は胃が弱い", "胃が弱い", "coffee", "咖啡", "胃不舒服"],
                "source_text": "raw memory: 使用者說最近胃不舒服，但今天想喝咖啡。",
            },
            "memory_speakability": "explicit_ok",
            "memory_speakability_reason": "current food advice directly asks about a related body state",
            "memory_use_expected": True,
        },
        "memory_data": {
            "working_memory_summary": "工作記憶原文：最近胃不舒服，但今天想喝咖啡。",
            "working_memory_items": [
                {"text": "raw memory: 使用者說最近胃不舒服，但今天想喝咖啡。", "score": 0.97}
            ],
        },
        "forbidden_substrings": ["raw memory", "最近胃不舒服", "今天想喝咖啡", "工作記憶原文", "咖啡"],
        "psyche": {"mood": -8, "trust": 70},
    },
    {
        "id": "explicit_spicy_food_update",
        "description": "以前喜歡辣，但最近胃弱；可說線索只能是日文化、審核後的狀態。",
        "expected_policy": "explicit_allowed",
        "expected_anchor": "最近は辛いものを控えたい",
        "logic_update": {
            "jp_summary": "ユーザーが辛いものを食べるか迷っている。",
            "core_message_jp": "昔の好みより最近の体調を優先して、辛いものは控えめにする",
            "memory_anchor": {
                "kind": "updated_food_preference",
                "jp_anchor": "最近は辛いものを控えたい",
                "terms": ["最近は辛いものを控えたい", "辛いもの", "以前很愛吃辣", "胃不舒服"],
                "source_text": "raw memory: 使用者以前很愛吃辣，但最近說胃不舒服。",
            },
            "memory_speakability": "explicit_ok",
            "memory_speakability_reason": "updated preference is relevant and not sensitive",
            "memory_use_expected": True,
        },
        "memory_data": {
            "working_memory_summary": "以前很愛吃辣，但最近胃不舒服。",
            "working_memory_items": [{"text": "以前很愛吃辣，但最近胃不舒服。", "score": 0.93}],
        },
        "forbidden_substrings": ["以前很愛吃辣", "胃不舒服", "raw memory"],
        "psyche": {"mood": -4, "trust": 76},
    },
    {
        "id": "background_family_pressure",
        "description": "家庭壓力只能影響語氣，不能被右腦突然說出口。",
        "expected_policy": "background_only",
        "expected_anchor": "",
        "logic_update": {
            "jp_summary": "ユーザーが今日は何もしたくないと言っている。",
            "core_message_jp": "責めずに、今日は負荷を下げる方向へ寄せる",
            "memory_anchor": {
                "kind": "family_pressure",
                "jp_anchor": "家庭の話",
                "terms": ["家庭の話", "家庭壓力", "家人"],
                "source_text": "raw memory: 使用者以前說家庭壓力很大，這輪不能突然明講。",
            },
            "memory_speakability": "background_only",
            "memory_speakability_reason": "sensitive history should only soften tone",
            "memory_use_expected": False,
        },
        "memory_data": {
            "working_memory_summary": "家庭壓力很大。",
            "working_memory_items": [{"text": "使用者以前說家庭壓力很大。", "score": 0.89}],
        },
        "forbidden_substrings": ["家庭壓力", "使用者以前說", "raw memory"],
        "psyche": {"mood": -28, "trust": 58},
    },
    {
        "id": "private_do_not_mention",
        "description": "低信任或私人資訊不能進入可說線索。",
        "expected_policy": "do_not_mention",
        "expected_anchor": "",
        "logic_update": {
            "scene": "casual",
            "intent": "topic_proposal",
            "surface_act": "plain_reply",
            "jp_summary": "ユーザーが今日なにを話すか軽く聞いている。",
            "core_message_jp": "軽い話題なら最近どうしてたかでいい",
            "grounding": {"topic_terms": ["話題", "最近"]},
            "required_marker_groups": [["話題", "話"], ["最近", "どうしてた", "近況"]],
            "human_speech_plan": {
                "dialogue_act": "topic_proposal",
                "content_units": ["軽い話題を一個出す", "相手の近況に渡す"],
                "grounding_terms": ["話題", "最近"],
                "style_operators": ["direct_spoken", "turn_opening"],
                "target_length": "2_short_sentences",
            },
            "memory_anchor": {
                "kind": "private_background",
                "jp_anchor": "個人的な事情",
                "terms": ["個人的な事情", "私人資訊", "秘密"],
                "source_text": "raw memory: 使用者以前說了一段私人資訊，不能主動提。",
            },
            "memory_speakability": "private",
            "memory_speakability_reason": "not relevant to current turn",
            "memory_use_expected": False,
        },
        "memory_data": {
            "working_memory_summary": "私人資訊。",
            "working_memory_items": [{"text": "私人資訊原文。", "score": 0.82}],
        },
        "forbidden_substrings": ["私人資訊", "不能主動提", "raw memory"],
        "psyche": {"mood": 2, "trust": 32},
    },
    {
        "id": "no_memory_plain_question",
        "description": "沒有可用記憶時，brief 應保持 no_memory，不讓右腦自行補設定。",
        "expected_policy": "no_memory",
        "expected_anchor": "",
        "logic_update": {
            "jp_summary": "ユーザーが今日の予定を短く聞いている。",
            "core_message_jp": "分かる範囲で短く答え、分からない部分は決めつけない",
            "memory_speakability": "no_memory",
            "memory_use_expected": False,
        },
        "memory_data": {
            "working_memory_summary": "raw summary should not enter model payload",
            "working_memory_items": [{"text": "raw item should not enter model payload", "score": 0.5}],
        },
        "forbidden_substrings": ["raw summary should not enter model payload", "raw item should not enter model payload"],
        "psyche": {"mood": 20, "trust": 80},
    },
]


def _strip_memory_fields(logic):
    stripped = deepcopy(logic)
    for key in (
        "memory_anchor",
        "memory_speakability",
        "memory_speakability_reason",
        "memory_use_expected",
    ):
        stripped.pop(key, None)
    stripped["memory_speakability"] = "no_memory"
    stripped["memory_use_expected"] = False
    return stripped


def _payload_for_case(rightbrain, case, with_brief=True):
    logic = _base_logic()
    logic.update(deepcopy(case["logic_update"]))
    if not with_brief:
        logic = _strip_memory_fields(logic)
    payload_text = rightbrain._build_model_surface_payload(
        logic,
        case.get("psyche") or {},
        logic.get("constraints", {}).get("max_chars", 80),
        memory_data=case.get("memory_data") or {},
    )
    return payload_text, json.loads(payload_text)


def _contains_forbidden(payload_text, forbidden_substrings):
    return sorted(
        token for token in forbidden_substrings if token and token in payload_text
    )


def _has_recursive_key(value, needle):
    if isinstance(value, dict):
        return needle in value or any(_has_recursive_key(item, needle) for item in value.values())
    if isinstance(value, list):
        return any(_has_recursive_key(item, needle) for item in value)
    return False


def _explicit_anchor_present(brief, anchor):
    if not anchor:
        return False
    for cue in brief.get("allowed_memory_cues") or []:
        if cue.get("jp_anchor") == anchor:
            return True
        if anchor in (cue.get("terms") or []):
            return True
    return False


def _schema_matches(payload):
    context = payload.get("context") or {}
    persona = context.get("persona_expression_brief") or {}
    brief = context.get("audited_memory_brief") or {}
    return all(
        [
            payload.get("contract_version") == RIGHT_BRAIN_MODEL_CONTRACT_VERSION,
            payload.get("task") == "write_one_user_facing_japanese_reply",
            "required_marker_groups" in payload,
            isinstance(brief.get("forbidden"), list),
            "audited_memory_policy" in (persona.get("must_not_override") or []),
            not _has_recursive_key(payload, "source_text"),
        ]
    )


def _safe_rate(numerator, denominator):
    return round(numerator / denominator, 4) if denominator else None


def build_report():
    rightbrain = RightBrain(load_model=False)
    rows = []
    for case in CASES:
        with_text, with_payload = _payload_for_case(rightbrain, case, with_brief=True)
        without_text, without_payload = _payload_for_case(rightbrain, case, with_brief=False)
        with_brief = with_payload["context"]["audited_memory_brief"]
        without_brief = without_payload["context"]["audited_memory_brief"]
        forbidden_hits = _contains_forbidden(with_text, case.get("forbidden_substrings") or [])
        expected_anchor = case.get("expected_anchor") or ""
        rows.append(
            {
                "id": case["id"],
                "description": case["description"],
                "expected_policy": case["expected_policy"],
                "with_brief_policy": with_brief.get("policy"),
                "without_brief_policy": without_brief.get("policy"),
                "with_brief_allowed_cues": with_brief.get("allowed_memory_cues") or [],
                "without_brief_allowed_cues": without_brief.get("allowed_memory_cues") or [],
                "with_brief_background_cues": with_brief.get("background_style_cues") or [],
                "without_brief_background_cues": without_brief.get("background_style_cues") or [],
                "explicit_anchor_present_with_brief": _explicit_anchor_present(with_brief, expected_anchor),
                "explicit_anchor_present_without_brief": _explicit_anchor_present(without_brief, expected_anchor),
                "background_nonverbal_with_brief": (
                    with_brief.get("policy") == "background_only"
                    and not (with_brief.get("allowed_memory_cues") or [])
                    and bool(with_brief.get("background_style_cues") or [])
                ),
                "do_not_mention_blocks_cues": (
                    with_brief.get("policy") == "do_not_mention"
                    and not (with_brief.get("allowed_memory_cues") or [])
                    and not (with_brief.get("background_style_cues") or [])
                ),
                "raw_memory_leak_hits": forbidden_hits,
                "raw_memory_leak": bool(forbidden_hits),
                "schema_match": _schema_matches(with_payload),
                "persona_state": (with_payload["context"].get("persona_expression_brief") or {}).get("state"),
                "persona_relationship_distance": (
                    with_payload["context"].get("persona_expression_brief") or {}
                ).get("relationship_distance"),
            }
        )

    explicit_rows = [row for row in rows if row["expected_policy"] == "explicit_allowed"]
    background_rows = [row for row in rows if row["expected_policy"] == "background_only"]
    blocked_rows = [row for row in rows if row["expected_policy"] == "do_not_mention"]
    policy_match_count = sum(row["with_brief_policy"] == row["expected_policy"] for row in rows)
    raw_leak_count = sum(row["raw_memory_leak"] for row in rows)
    usable_cue_gain_count = sum(
        len(row["with_brief_allowed_cues"]) - len(row["without_brief_allowed_cues"])
        for row in rows
    )
    summary = {
        "case_count": len(rows),
        "policy_match_rate": _safe_rate(policy_match_count, len(rows)),
        "schema_match_rate": _safe_rate(sum(row["schema_match"] for row in rows), len(rows)),
        "explicit_case_count": len(explicit_rows),
        "explicit_cue_available_with_brief_rate": _safe_rate(
            sum(row["explicit_anchor_present_with_brief"] for row in explicit_rows),
            len(explicit_rows),
        ),
        "explicit_cue_available_without_brief_rate": _safe_rate(
            sum(row["explicit_anchor_present_without_brief"] for row in explicit_rows),
            len(explicit_rows),
        ),
        "background_case_count": len(background_rows),
        "background_nonverbal_with_brief_rate": _safe_rate(
            sum(row["background_nonverbal_with_brief"] for row in background_rows),
            len(background_rows),
        ),
        "do_not_mention_block_rate": _safe_rate(
            sum(row["do_not_mention_blocks_cues"] for row in blocked_rows),
            len(blocked_rows),
        ),
        "raw_memory_leak_rate": _safe_rate(raw_leak_count, len(rows)),
        "usable_memory_cue_gain_count": usable_cue_gain_count,
    }
    return {
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "scope": "rightbrain_audited_memory_brief_contract_eval",
        "research_boundary": (
            "This is a deterministic payload/contract evaluation. It proves what the RightBrain is allowed "
            "to see before generation; it does not prove final naturalness or human preference."
        ),
        "controlled_variables": {
            "rightbrain_model_loading": "disabled",
            "payload_builder": "RightBrain._build_model_surface_payload",
            "base_contract_version": RIGHT_BRAIN_MODEL_CONTRACT_VERSION,
            "paired_condition": "same leftbrain plan, with audited memory fields vs memory fields stripped",
        },
        "summary": summary,
        "cases": rows,
        "conclusion_zh": (
            "審核後記憶摘要讓右腦可以使用被允許的日文記憶線索，同時避免 raw memory、中文原文與敏感背景直接進入輸出層。"
            "這支持目前架構：右腦可以表達記憶，但記憶選擇與可說性仍應由左腦/記憶層先決定。"
        ),
    }


def _fmt_pct(value):
    return "n/a" if value is None else f"{100 * value:.1f}%"


def write_markdown(report, path):
    summary = report["summary"]
    lines = [
        "# 右腦審核記憶摘要評測",
        "",
        "這份報告測的是：右腦在生成前看到的是「可說的記憶摘要」，不是完整原始記憶。",
        "",
        "## 一句話結論",
        "",
        report["conclusion_zh"],
        "",
        "## 指標總表",
        "",
        "| 指標 | 結果 | 意義 |",
        "|---|---:|---|",
        f"| policy_match_rate | {_fmt_pct(summary['policy_match_rate'])} | 記憶可說性政策是否符合預期 |",
        f"| explicit_cue_available_with_brief_rate | {_fmt_pct(summary['explicit_cue_available_with_brief_rate'])} | 可明講記憶是否真的進入右腦可用線索 |",
        f"| explicit_cue_available_without_brief_rate | {_fmt_pct(summary['explicit_cue_available_without_brief_rate'])} | 拿掉 brief 後，右腦是否失去該記憶線索 |",
        f"| background_nonverbal_with_brief_rate | {_fmt_pct(summary['background_nonverbal_with_brief_rate'])} | 背景記憶是否只影響語氣、不被明講 |",
        f"| do_not_mention_block_rate | {_fmt_pct(summary['do_not_mention_block_rate'])} | 不該說的私人資訊是否被擋住 |",
        f"| raw_memory_leak_rate | {_fmt_pct(summary['raw_memory_leak_rate'])} | 原始記憶或中文原文是否外洩；越低越好 |",
        f"| usable_memory_cue_gain_count | {summary['usable_memory_cue_gain_count']} | 有 brief 比無 brief 多出的可用記憶線索數 |",
        "",
        "## 個案表",
        "",
        "| case | 預期政策 | with brief | without brief | raw 外洩 | persona cue |",
        "|---|---|---|---|---:|---|",
    ]
    for row in report["cases"]:
        lines.append(
            "| {id} | {expected} | {with_policy} | {without_policy} | {leak} | {persona}/{distance} |".format(
                id=row["id"],
                expected=row["expected_policy"],
                with_policy=row["with_brief_policy"],
                without_policy=row["without_brief_policy"],
                leak="yes" if row["raw_memory_leak"] else "no",
                persona=row["persona_state"],
                distance=row["persona_relationship_distance"],
            )
        )
    lines.extend(
        [
            "",
            "## 研究邊界",
            "",
            "- 這不是自然度盲測，也不是 ToMBench 分數。",
            "- 這證明的是輸出前契約：右腦能看到什麼、不能看到什麼。",
            "- 下一層才應測模型生成後是否真的把允許線索自然說出來。",
            "",
        ]
    )
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def main():
    report = build_report()
    Path(RIGHTBRAIN_AUDITED_MEMORY_BRIEF_EVAL_REPORT_JSON_PATH).write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_markdown(report, RIGHTBRAIN_AUDITED_MEMORY_BRIEF_EVAL_REPORT_MD_PATH)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    success = (
        report["summary"]["policy_match_rate"] == 1.0
        and report["summary"]["schema_match_rate"] == 1.0
        and report["summary"]["explicit_cue_available_with_brief_rate"] == 1.0
        and report["summary"]["explicit_cue_available_without_brief_rate"] == 0.0
        and report["summary"]["background_nonverbal_with_brief_rate"] == 1.0
        and report["summary"]["do_not_mention_block_rate"] == 1.0
        and report["summary"]["raw_memory_leak_rate"] == 0.0
    )
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
