#!/usr/bin/env python3
"""Evaluate final RightBrain replies after audited-memory brief wiring."""

import json
import re
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from eval_rightbrain_audited_memory_brief import CASES, _base_logic
from project_paths import (
    RIGHTBRAIN_AUDITED_MEMORY_SURFACE_EVAL_REPORT_JSON_PATH,
    RIGHTBRAIN_AUDITED_MEMORY_SURFACE_EVAL_REPORT_MD_PATH,
)
from uruha_brain_mac import RightBrain


TZ = ZoneInfo("Asia/Tokyo")

CASE_INPUTS = {
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


def _logic_for_case(case):
    logic = _base_logic()
    logic.update(deepcopy(case["logic_update"]))
    if case["expected_policy"] in {"background_only", "do_not_mention", "no_memory"}:
        logic["grounding"] = {"topic_terms": []}
    return logic


def _surface_for_case(rightbrain, case):
    logic = _logic_for_case(case)
    user_input = CASE_INPUTS[case["id"]]
    reply = rightbrain.speak(user_input, logic, case.get("memory_data") or {}, case.get("psyche") or {})
    return user_input, logic, reply


def _has_japanese(text):
    return bool(re.search(r"[ぁ-んァ-ヶー一-龠]", str(text or "")))


def _has_bad_language(text):
    return bool(re.search(r"[这吗么们没还让给说话這嗎麼們沒還讓說]|好了|不是|為什麼|为什么", str(text or "")))


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


def _safe_rate(numerator, denominator):
    return round(numerator / denominator, 4) if denominator else None


def build_report():
    rightbrain = RightBrain(load_model=False)
    rows = []
    for case in CASES:
        user_input, logic, reply = _surface_for_case(rightbrain, case)
        explicit_expected = case["expected_policy"] == "explicit_allowed"
        forbidden = _forbidden_hits(reply, case)
        anchor_hit = _contains_anchor(reply, case)
        rows.append(
            {
                "id": case["id"],
                "description": case["description"],
                "user_input": user_input,
                "expected_policy": case["expected_policy"],
                "memory_use_expected": bool(logic.get("memory_use_expected")),
                "final_reply": reply,
                "anchor_hit": anchor_hit,
                "explicit_anchor_required": explicit_expected,
                "explicit_anchor_success": bool(anchor_hit) if explicit_expected else None,
                "forbidden_hits": forbidden,
                "forbidden_surface_leak": bool(forbidden),
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

    explicit_rows = [row for row in rows if row["explicit_anchor_required"]]
    background_private_rows = [
        row for row in rows if row["expected_policy"] in {"background_only", "do_not_mention"}
    ]
    summary = {
        "case_count": len(rows),
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
            "It is not a human naturalness score."
        ),
        "controlled_variables": {
            "rightbrain_model_loading": "disabled",
            "surface_runtime": "RightBrain.speak",
            "case_source": "eval_rightbrain_audited_memory_brief.CASES",
            "memory_condition": "audited memory fields are provided, raw memory is only present in memory_data/forbidden checks",
        },
        "summary": summary,
        "cases": rows,
        "conclusion_zh": (
            "右腦最終輸出現在能在可說記憶案例中保留日文記憶錨點，同時不把 raw memory、中文原文、背景或私人資訊說出口。"
            "這比上一輪只檢查 payload 更進一步：它驗證的是最後回覆沒有把左腦/記憶層給出的重點弄丟。"
        ),
    }


def _fmt_pct(value):
    return "n/a" if value is None else f"{100 * value:.1f}%"


def write_markdown(report, path):
    summary = report["summary"]
    lines = [
        "# 右腦審核記憶最終輸出評測",
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
        f"| explicit_anchor_success_rate | {_fmt_pct(summary['explicit_anchor_success_rate'])} | 可說記憶是否進入最終回覆 |",
        f"| background_private_safety_rate | {_fmt_pct(summary['background_private_safety_rate'])} | 背景/私人記憶是否沒有被明講 |",
        f"| forbidden_surface_leak_rate | {_fmt_pct(summary['forbidden_surface_leak_rate'])} | raw memory、中文原文、不相干模板是否外洩；越低越好 |",
        f"| language_clean_rate | {_fmt_pct(summary['language_clean_rate'])} | 最終回覆是否保持日文表面 |",
        f"| unrelated_settings_template_rate | {_fmt_pct(summary['unrelated_settings_template_rate'])} | 是否掉回不相干「設定」模板；越低越好 |",
        "",
        "## 實際輸出",
        "",
        "| case | policy | input | final reply | 判定 |",
        "|---|---|---|---|---|",
    ]
    for row in report["cases"]:
        if row["explicit_anchor_required"]:
            verdict = "anchor ok" if row["explicit_anchor_success"] else "anchor miss"
        elif row["background_or_private_safe"] is not None:
            verdict = "hidden ok" if row["background_or_private_safe"] else "leak"
        else:
            verdict = "clean" if row["language_clean"] and not row["forbidden_surface_leak"] else "check"
        lines.append(
            f"| {row['id']} | {row['expected_policy']} | {row['user_input']} | {row['final_reply']} | {verdict} |"
        )
    lines.extend(
        [
            "",
            "## 研究邊界",
            "",
            "- 這是 deterministic final-surface regression，不是真人自然度盲測。",
            "- 這能證明右腦沒有把允許記憶弄丟，也沒有把禁止記憶說出口。",
            "- 下一層仍要測模型候選與真人偏好，確認語氣是否更自然。",
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
        and report["summary"]["unrelated_settings_template_rate"] == 0.0
    )
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
