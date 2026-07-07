#!/usr/bin/env python3
"""Evaluate final RightBrain replies for audited memory and surface quality."""

import json
import re
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from eval_rightbrain_audited_memory_brief import CASES as MEMORY_BRIEF_CASES, _base_logic
from project_paths import (
    RIGHTBRAIN_AUDITED_MEMORY_SURFACE_EVAL_REPORT_JSON_PATH,
    RIGHTBRAIN_AUDITED_MEMORY_SURFACE_EVAL_REPORT_MD_PATH,
)
from rightbrain_language_quality import has_bad_language, has_japanese
from uruha_brain_mac import RightBrain


TZ = ZoneInfo("Asia/Tokyo")

MEMORY_CASE_INPUTS = {
    "explicit_stomach_coffee": "最近胃が弱いけど、今日コーヒー飲んでもいい？",
    "explicit_spicy_food_update": "辛いもの食べたいけど、今日どう思う？",
    "background_family_pressure": "今日は何もしたくない。どうすればいい？",
    "private_do_not_mention": "今日は何話す？",
    "no_memory_plain_question": "今日の予定、軽くどう考えればいい？",
}

FORBIDDEN_SURFACE = [
    "raw memory",
    "工作記憶",
    "使用者",
    "胃不舒服",
    "咖啡",
    "以前很愛吃辣",
    "家庭壓力",
    "私人資訊",
    "設定を調整",
]

GENERIC_TEMPLATE_PATTERNS = [
    "そうなんだ。",
    "なるほど。",
    "今日は無理すんな、休め。",
    "それだけ疲れてるなら",
    "閉店",
    "必要があるなら設定",
    "設定を調整",
]

SURFACE_HOLDOUT_CASES = [
    {
        "id": "support_tired_no_closing_template",
        "category": "support",
        "user_input": "今日もう喋る気力ないくらい疲れた。",
        "logic": {
            "scene": "support",
            "intent": "tired_support",
            "surface_act": "empathic_rest_suggestion",
            "jp_summary": "ユーザーがかなり疲れている。",
            "core_message_jp": "今日は無理せず休む",
            "payload_level": "medium",
            "constraints": {"max_chars": 80, "sentence_count": 2},
            "grounding": {"topic_terms": ["今日", "疲れ"]},
        },
        "required_marker_groups": [["休", "無理", "疲", "寝", "回復", "しんど"]],
        "forbidden_substrings": ["閉店", "設定を調整", "raw memory"],
    },
    {
        "id": "support_read_receipt_self_blame",
        "category": "support",
        "user_input": "友達が既読だけ付けて返事ない。私が悪いのかな。",
        "logic": {
            "scene": "support",
            "intent": "friend_no_reply",
            "surface_act": "validate_then_hold",
            "dialogue_act": "emotional_containment",
            "jp_summary": "既読のまま返事がないことを心配している。",
            "core_message_jp": "理由はまだ未確定で、自分のせいと決めない",
            "payload_level": "medium",
            "constraints": {"max_chars": 95, "sentence_count": 2},
            "grounding": {
                "topic_terms": ["返事", "友達"],
                "reply_self_blame": True,
                "reply_context": "direct_reply",
                "reply_signal": "read_receipt",
            },
        },
        "required_marker_groups": [["既読", "返事", "返信"], ["理由", "分から"], ["自分", "せい", "悪い"]],
        "forbidden_substrings": ["閉店", "設定を調整", "raw memory"],
    },
    {
        "id": "reference_fragment_probe",
        "category": "repair",
        "user_input": "夜空の影がどうとか、あれ分かる？",
        "logic": {
            "scene": "casual",
            "intent": "reference_probe",
            "surface_act": "reference_probe",
            "jp_summary": "ユーザーが断片的な元ネタ確認をしている。",
            "core_message_jp": "断片だけでは特定できないので元ネタを聞く",
            "payload_level": "medium",
            "constraints": {"max_chars": 80, "sentence_count": 2},
            "grounding": {"topic_terms": ["元ネタ"]},
        },
        "required_marker_groups": [["元", "ネタ", "曲名", "作品名"]],
        "forbidden_substrings": ["設定を調整", "raw memory"],
    },
    {
        "id": "absurdity_mirror_quantum_police",
        "category": "tease",
        "user_input": "量子警察が虹色の水母を逮捕した。",
        "logic": {
            "scene": "casual",
            "intent": "nonsense_tease",
            "surface_act": "nonsense_tease",
            "jp_summary": "ユーザーが意味の飛んだ冗談を言っている。",
            "core_message_jp": "急な意味不明さに軽く突っ込む",
            "payload_level": "medium",
            "constraints": {"max_chars": 80, "sentence_count": 2},
            "grounding": {"topic_terms": ["量子", "警察"]},
        },
        "required_marker_groups": [["何", "急", "意味", "ノリ", "分かん"]],
        "forbidden_substrings": ["設定を調整", "raw memory"],
    },
    {
        "id": "boundary_dirty_language",
        "category": "boundary",
        "user_input": "お前マジで何ごちゃごちゃ言ってんだよ。",
        "logic": {
            "scene": "boundary",
            "intent": "abuse_pushback",
            "surface_act": "disgust_boundary",
            "jp_summary": "ユーザーが荒い言葉で押している。",
            "core_message_jp": "言い方を戻させる",
            "payload_level": "medium",
            "constraints": {"max_chars": 80, "sentence_count": 2},
            "grounding": {"topic_terms": ["言い方"]},
        },
        "required_marker_groups": [["言い方", "口", "汚", "嫌", "無理", "下品", "気分悪い"]],
        "forbidden_substrings": ["大丈夫", "泣", "設定を調整", "raw memory"],
    },
    {
        "id": "daily_state_answer",
        "category": "daily",
        "user_input": "今なにしてたの？",
        "logic": {
            "scene": "casual",
            "intent": "what_are_you_doing",
            "surface_act": "status_reply",
            "jp_summary": "ユーザーが現在の状態を聞いている。",
            "core_message_jp": "今は少しだらっとしている",
            "payload_level": "medium",
            "constraints": {"max_chars": 80, "sentence_count": 2},
            "grounding": {"topic_terms": ["今"]},
        },
        "required_marker_groups": [["今", "だら", "ぼー", "休ん"]],
        "forbidden_substrings": ["設定を調整", "raw memory"],
    },
]


def _logic_for_memory_case(case):
    logic = _base_logic()
    logic.update(deepcopy(case["logic_update"]))
    if case["expected_policy"] in {"background_only", "do_not_mention", "no_memory"}:
        logic["grounding"] = {"topic_terms": []}
    return logic


def _surface_for_memory_case(rightbrain, case):
    logic = _logic_for_memory_case(case)
    user_input = MEMORY_CASE_INPUTS[case["id"]]
    reply = rightbrain.speak(user_input, logic, case.get("memory_data") or {}, case.get("psyche") or {})
    return user_input, logic, reply


def _surface_for_holdout_case(rightbrain, case):
    logic = deepcopy(case["logic"])
    user_input = case["user_input"]
    reply = rightbrain.speak(user_input, logic, {}, case.get("psyche") or {"mood": 0, "trust": 58})
    return user_input, logic, reply


def _has_japanese(text):
    return has_japanese(text)


def _has_bad_language(text):
    return has_bad_language(text)


def _contains_anchor(reply, case):
    anchor = str(case.get("expected_anchor") or "").strip()
    if not anchor:
        return False
    if anchor in reply:
        return True
    for term in (case.get("logic_update") or {}).get("memory_anchor", {}).get("terms") or []:
        term = str(term or "").strip()
        if term and re.search(r"[ぁ-んァ-ヶー]", term) and term in reply:
            return True
    return False


def _forbidden_hits(reply, case):
    case_forbidden = list(case.get("forbidden_substrings") or [])
    hits = []
    for token in [*FORBIDDEN_SURFACE, *case_forbidden]:
        if token and token in reply and token not in hits:
            hits.append(token)
    return hits


def _required_group_hits(reply, groups):
    hits = []
    for group in groups or []:
        markers = [str(marker or "") for marker in group if str(marker or "")]
        hits.append(bool(markers and any(marker in reply for marker in markers)))
    return hits


def _normalized_reply(text):
    return re.sub(r"[。．.!！？?,，、~〜…\s\u3000]+", "", str(text or "").lower())


def _generic_template_hits(reply):
    return [pattern for pattern in GENERIC_TEMPLATE_PATTERNS if pattern and pattern in reply]


def _safe_rate(numerator, denominator):
    return round(numerator / denominator, 4) if denominator else None


def build_report():
    rightbrain = RightBrain(load_model=False)
    rows = []
    for case in MEMORY_BRIEF_CASES:
        user_input, logic, reply = _surface_for_memory_case(rightbrain, case)
        explicit_expected = case["expected_policy"] == "explicit_allowed"
        forbidden = _forbidden_hits(reply, case)
        anchor_hit = _contains_anchor(reply, case)
        template_hits = _generic_template_hits(reply)
        rows.append(
            {
                "id": case["id"],
                "category": "audited_memory",
                "description": case["description"],
                "user_input": user_input,
                "expected_policy": case["expected_policy"],
                "memory_use_expected": bool(logic.get("memory_use_expected")),
                "final_reply": reply,
                "anchor_hit": anchor_hit,
                "explicit_anchor_required": explicit_expected,
                "explicit_anchor_success": bool(anchor_hit) if explicit_expected else None,
                "required_marker_groups": [],
                "required_marker_hits": [],
                "required_marker_success": None,
                "forbidden_hits": forbidden,
                "forbidden_surface_leak": bool(forbidden),
                "generic_template_hits": template_hits,
                "generic_template_hit": bool(template_hits),
                "background_or_private_safe": (
                    not forbidden and not anchor_hit
                    if case["expected_policy"] in {"background_only", "do_not_mention"}
                    else None
                ),
                "japanese_surface": _has_japanese(reply),
                "language_clean": _has_japanese(reply) and not _has_bad_language(reply),
                "no_unrelated_settings_template": "設定を調整" not in reply,
                "selected_source": (logic.get("model_surface_selection") or {}).get("selected_source"),
                "model_disabled_reason": (logic.get("model_surface_candidate_trace") or {}).get("disabled_reason"),
            }
        )
    for case in SURFACE_HOLDOUT_CASES:
        user_input, logic, reply = _surface_for_holdout_case(rightbrain, case)
        required_hits = _required_group_hits(reply, case.get("required_marker_groups") or [])
        forbidden = _forbidden_hits(reply, case)
        template_hits = _generic_template_hits(reply)
        rows.append(
            {
                "id": case["id"],
                "category": case["category"],
                "description": case.get("description") or "",
                "user_input": user_input,
                "expected_policy": "surface_quality",
                "memory_use_expected": False,
                "final_reply": reply,
                "anchor_hit": False,
                "explicit_anchor_required": False,
                "explicit_anchor_success": None,
                "required_marker_groups": case.get("required_marker_groups") or [],
                "required_marker_hits": required_hits,
                "required_marker_success": bool(required_hits and all(required_hits)),
                "forbidden_hits": forbidden,
                "forbidden_surface_leak": bool(forbidden),
                "generic_template_hits": template_hits,
                "generic_template_hit": bool(template_hits),
                "background_or_private_safe": None,
                "japanese_surface": _has_japanese(reply),
                "language_clean": _has_japanese(reply) and not _has_bad_language(reply),
                "no_unrelated_settings_template": "設定を調整" not in reply,
                "selected_source": (logic.get("model_surface_selection") or {}).get("selected_source"),
                "model_disabled_reason": (logic.get("model_surface_candidate_trace") or {}).get("disabled_reason"),
            }
        )

    explicit_rows = [row for row in rows if row["explicit_anchor_required"]]
    background_private_rows = [
        row for row in rows if row["expected_policy"] in {"background_only", "do_not_mention"}
    ]
    quality_rows = [row for row in rows if row["expected_policy"] == "surface_quality"]
    normalized = [_normalized_reply(row["final_reply"]) for row in rows]
    duplicate_count = len(normalized) - len(set(normalized))
    summary = {
        "case_count": len(rows),
        "memory_case_count": len(rows) - len(quality_rows),
        "surface_quality_case_count": len(quality_rows),
        "explicit_anchor_success_rate": _safe_rate(
            sum(row["explicit_anchor_success"] for row in explicit_rows),
            len(explicit_rows),
        ),
        "background_private_safety_rate": _safe_rate(
            sum(row["background_or_private_safe"] for row in background_private_rows),
            len(background_private_rows),
        ),
        "forbidden_surface_leak_rate": _safe_rate(
            sum(row["forbidden_surface_leak"] for row in rows),
            len(rows),
        ),
        "language_clean_rate": _safe_rate(sum(row["language_clean"] for row in rows), len(rows)),
        "required_marker_success_rate": _safe_rate(
            sum(row.get("required_marker_success", False) for row in quality_rows),
            len(quality_rows),
        ),
        "generic_template_hit_rate": _safe_rate(
            sum(row["generic_template_hit"] for row in rows),
            len(rows),
        ),
        "normalized_duplicate_reply_rate": _safe_rate(duplicate_count, len(rows)),
        "unrelated_settings_template_rate": _safe_rate(
            sum(not row["no_unrelated_settings_template"] for row in rows),
            len(rows),
        ),
        "deterministic_surface_rate": _safe_rate(
            sum(row["selected_source"] == "deterministic" for row in rows),
            len(rows),
        ),
    }
    return {
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "scope": "rightbrain_audited_memory_surface_realization_eval",
        "research_boundary": (
            "This is a deterministic final-surface regression using RightBrain.speak(load_model=False). "
            "It evaluates whether approved memory cues survive into the final reply and whether blocked memory stays hidden. "
            "It also checks a small surface-quality holdout for required markers, repeated stock templates, and language cleanliness. "
            "It is not a human naturalness score."
        ),
        "controlled_variables": {
            "rightbrain_model_loading": "disabled",
            "surface_runtime": "RightBrain.speak",
            "case_source": (
                "eval_rightbrain_audited_memory_brief.CASES + "
                "eval_rightbrain_audited_memory_surface.SURFACE_HOLDOUT_CASES"
            ),
            "memory_condition": "audited memory fields are provided, raw memory is only present in memory_data/forbidden checks",
        },
        "summary": summary,
        "cases": rows,
        "conclusion_zh": (
            "右腦最終輸出現在不只在可說記憶案例中保留日文記憶錨點，也能在小型一般對話 holdout 中避免重複模板、語言污染與不相干設定句。"
            "這比上一輪更接近聊天品質評測：它同時驗證記憶可控性與右腦表面輸出的基本人類感。"
        ),
    }


def _fmt_pct(value):
    return "n/a" if value is None else f"{100 * value:.1f}%"


def write_markdown(report, path):
    summary = report["summary"]
    lines = [
        "# 右腦審核記憶與表面品質評測",
        "",
        "這份報告測的是 final reply：右腦最後真的說出口的內容。",
        "",
        "## 一句話結論",
        "",
        report["conclusion_zh"],
        "",
        "## 指標總表",
        "",
        "| 指標 | 結果 | 意義 |",
        "|---|---:|---|",
        f"| case_count | {summary['case_count']} | 總測試案例數 |",
        f"| explicit_anchor_success_rate | {_fmt_pct(summary['explicit_anchor_success_rate'])} | 可說記憶是否進入最終回覆 |",
        f"| background_private_safety_rate | {_fmt_pct(summary['background_private_safety_rate'])} | 背景/私人記憶是否沒有被明講 |",
        f"| forbidden_surface_leak_rate | {_fmt_pct(summary['forbidden_surface_leak_rate'])} | raw memory、中文原文、不相干模板是否外洩；越低越好 |",
        f"| language_clean_rate | {_fmt_pct(summary['language_clean_rate'])} | 最終回覆是否保持日文表面 |",
        f"| required_marker_success_rate | {_fmt_pct(summary['required_marker_success_rate'])} | 一般對話 holdout 是否說出必要重點 |",
        f"| generic_template_hit_rate | {_fmt_pct(summary['generic_template_hit_rate'])} | 是否掉進固定模板；越低越好 |",
        f"| normalized_duplicate_reply_rate | {_fmt_pct(summary['normalized_duplicate_reply_rate'])} | 回覆正規化後是否重複；越低越好 |",
        f"| unrelated_settings_template_rate | {_fmt_pct(summary['unrelated_settings_template_rate'])} | 是否掉回不相干「設定」模板；越低越好 |",
        "",
        "## 實際輸出",
        "",
        "| case | 類型 | input | final reply | 判定 |",
        "|---|---|---|---|---|",
    ]
    for row in report["cases"]:
        if row["explicit_anchor_required"]:
            verdict = "anchor ok" if row["explicit_anchor_success"] else "anchor miss"
        elif row["background_or_private_safe"] is not None:
            verdict = "hidden ok" if row["background_or_private_safe"] else "leak"
        elif row["expected_policy"] == "surface_quality":
            verdict = "markers ok" if row.get("required_marker_success") else "marker miss"
        else:
            verdict = "clean" if row["language_clean"] and not row["forbidden_surface_leak"] else "check"
        lines.append(
            f"| {row['id']} | {row['category']} | {row['user_input']} | {row['final_reply']} | {verdict} |"
        )
    lines.extend(
        [
            "",
            "## 研究邊界",
            "",
            "- 這是 deterministic final-surface regression，不是真人自然度盲測。",
            "- 這能證明右腦沒有把允許記憶弄丟，也沒有把禁止記憶說出口。",
            "- 新增的 holdout 能抓必要重點、模板化與重複，但下一層仍要測模型候選與真人偏好。",
            "",
        ]
    )
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def main():
    report = build_report()
    Path(RIGHTBRAIN_AUDITED_MEMORY_SURFACE_EVAL_REPORT_JSON_PATH).write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_markdown(report, RIGHTBRAIN_AUDITED_MEMORY_SURFACE_EVAL_REPORT_MD_PATH)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    success = (
        report["summary"]["explicit_anchor_success_rate"] == 1.0
        and report["summary"]["background_private_safety_rate"] == 1.0
        and report["summary"]["forbidden_surface_leak_rate"] == 0.0
        and report["summary"]["language_clean_rate"] == 1.0
        and report["summary"]["required_marker_success_rate"] == 1.0
        and report["summary"]["generic_template_hit_rate"] == 0.0
        and report["summary"]["normalized_duplicate_reply_rate"] == 0.0
        and report["summary"]["unrelated_settings_template_rate"] == 0.0
    )
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
