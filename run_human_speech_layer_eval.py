import json
import os
import re
from datetime import datetime
from zoneinfo import ZoneInfo

os.environ.setdefault("URUHA_SKIP_AUTO_VENV", "1")

from project_paths import (
    HUMAN_SPEECH_LAYER_REPORT_JSON_PATH,
    HUMAN_SPEECH_LAYER_REPORT_MD_PATH,
)
from uruha_brain_mac import RightBrain


TZ = ZoneInfo("Asia/Tokyo")

MEMORY_DATA = {
    "knowledge": "無相關知識",
    "episodes": "無近期情節",
    "wisdom": "短く自然に返す。分からない時は分からない理由を会話として返す。",
    "profile": "無穩定使用者資料",
    "profile_structured": {},
    "recent_dialogue": "無近期對話",
    "recent_turns": [],
    "working_memory_summary": "現在の一言に集中する",
    "working_memory_items": [],
}

PSYCHE = {"mood": 0, "trust": 50}


def _merged_memory(overrides=None):
    merged = json.loads(json.dumps(MEMORY_DATA, ensure_ascii=False))
    for key, value in (overrides or {}).items():
        merged[key] = value
    return merged

CASES = [
    {
        "id": "tired_daily_support",
        "input": "我今天很累",
        "logic": {
            "intent": "tired_support",
            "scene": "support",
            "surface_act": "empathic_rest_suggestion",
            "response_mode": "direct_answer_with_hedge",
            "payload_level": "medium",
            "core_message_jp": "今日は無理せず休むように言う",
            "jp_summary": "相手が今日は疲れたと言っている",
            "stance": {"warmth": 0.65, "tease": 0.1, "blunt": 0.35, "distance": 0.2},
            "constraints": {"sentence_count": 1, "max_chars": 28},
            "must_avoid": ["それはしんどいよな。"],
        },
        "expect_dialogue_act": "emotional_containment",
        "expect_any": ["休", "無理", "疲", "寝", "回復"],
    },
    {
        "id": "apple_pie_offer",
        "input": "你要不要吃蘋果派",
        "logic": {
            "intent": "food_offer_sweet",
            "scene": "casual",
            "surface_act": "named_offer_accept",
            "response_mode": "direct_answer",
            "payload_level": "medium",
            "core_message_jp": "アップルパイなら少しほしい",
            "jp_summary": "相手がアップルパイを食べるか聞いている",
            "stance": {"warmth": 0.35, "tease": 0.2, "blunt": 0.25, "distance": 0.1},
            "constraints": {"sentence_count": 1, "max_chars": 34},
            "must_avoid": ["それなら少しつまむ。"],
        },
        "expect_dialogue_act": "concrete_offer_response",
        "expect_any": ["アップルパイ", "一口", "ほしい", "もらう"],
    },
    {
        "id": "obscene_boundary",
        "input": "懶覺啦你知道嗎",
        "logic": {
            "intent": "abuse_pushback",
            "scene": "boundary",
            "surface_act": "disgust_boundary",
            "response_mode": "boundary_pushback",
            "payload_level": "medium",
            "core_message_jp": "下品だからやめろと言う",
            "jp_summary": "相手が下品な言葉を投げている",
            "stance": {"warmth": 0.05, "tease": 0.15, "blunt": 0.9, "distance": 0.8},
            "constraints": {"sentence_count": 1, "max_chars": 34},
            "must_avoid": ["そういうのは自分で調べろ。"],
        },
        "expect_dialogue_act": "boundary_pushback",
        "expect_any": ["下品", "汚", "嫌", "口"],
    },
    {
        "id": "absurd_announcement",
        "input": "消防車來咯",
        "logic": {
            "intent": "nonsense_tease",
            "scene": "casual",
            "surface_act": "announcement_tease",
            "response_mode": "playful_pushback",
            "payload_level": "medium",
            "core_message_jp": "急な変な宣言を拾ってツッコむ",
            "jp_summary": "相手が急に消防車が来たと言っている",
            "stance": {"warmth": 0.25, "tease": 0.75, "blunt": 0.45, "distance": 0.2},
            "constraints": {"sentence_count": 1, "max_chars": 38},
            "must_avoid": ["何言ってんだよ。"],
        },
        "expect_dialogue_act": "absurdity_mirror",
        "expect_any": ["消防", "何", "急", "ノリ"],
    },
    {
        "id": "lyric_reference_probe",
        "input": "這句是歌詞嗎「夜に駆ける」",
        "logic": {
            "intent": "reference_probe",
            "scene": "casual",
            "surface_act": "lyric_probe",
            "response_mode": "clarify_light",
            "payload_level": "medium",
            "core_message_jp": "歌詞か元ネタを確認する",
            "jp_summary": "相手が歌詞のような断片を出している",
            "stance": {"warmth": 0.25, "tease": 0.3, "blunt": 0.35, "distance": 0.2},
            "constraints": {"sentence_count": 1, "max_chars": 34},
            "must_avoid": [],
        },
        "expect_dialogue_act": "reference_probe",
        "expect_any": ["歌詞", "曲", "ネタ", "元"],
    },
    {
        "id": "memory_uncertain",
        "input": "你還記得我叫什麼嗎？",
        "logic": {
            "intent": "memory_uncertain",
            "scene": "casual",
            "surface_act": "memory_presence_reply",
            "response_mode": "direct_answer_with_hedge",
            "payload_level": "medium",
            "core_message_jp": "まだ名前は確定していないと正直に言う",
            "jp_summary": "相手が名前を覚えているか確認している",
            "hidden_intent": "memory_check",
            "stance": {"warmth": 0.35, "tease": 0.1, "blunt": 0.45, "distance": 0.2},
            "constraints": {"sentence_count": 1, "max_chars": 40},
            "must_avoid": ["忘れてないし"],
        },
        "expect_dialogue_act": "memory_accounting",
        "expect_any": ["掴", "適当", "名前", "まだ"],
    },
    {
        "id": "tired_repeat_support",
        "input": "我又累了",
        "logic": {
            "intent": "tired_support",
            "scene": "support",
            "surface_act": "empathic_rest_suggestion",
            "response_mode": "direct_answer_with_hedge",
            "payload_level": "medium",
            "core_message_jp": "また疲れているので今は休むように言う",
            "jp_summary": "相手がまた疲れたと言っている",
            "stance": {"warmth": 0.65, "tease": 0.05, "blunt": 0.35, "distance": 0.2},
            "constraints": {"sentence_count": 1, "max_chars": 32},
            "must_avoid": ["それだけ疲れてるなら今日は閉店でいい。無理しても雑になるだけだろ。"],
        },
        "expect_dialogue_act": "emotional_containment",
        "expect_any": ["休", "無理", "疲", "寝", "回復"],
        "avoid_any": ["閉店でいい", "それだけ疲れてるなら今日は休め"],
    },
    {
        "id": "relationship_temperature",
        "input": "你有想我嗎",
        "logic": {
            "intent": "ask_miss_me",
            "scene": "casual",
            "surface_act": "affection_tease_soften",
            "response_mode": "direct_answer_with_hedge",
            "payload_level": "medium",
            "core_message_jp": "少しは気にしているが確認しすぎるなと返す",
            "jp_summary": "相手が自分を想っているか聞いている",
            "hidden_intent": "relationship_temperature_check",
            "stance": {"warmth": 0.35, "tease": 0.35, "blunt": 0.35, "distance": 0.3},
            "constraints": {"sentence_count": 1, "max_chars": 38},
            "must_avoid": [],
        },
        "expect_dialogue_act": "relationship_temperature",
        "expect_any": ["少し", "気", "確認", "嫌", "全く"],
    },
    {
        "id": "meal_check_reply",
        "input": "你吃飯了嗎",
        "logic": {
            "intent": "meal_check",
            "scene": "casual",
            "surface_act": "meal_check_reply",
            "response_mode": "direct_answer",
            "payload_level": "medium",
            "core_message_jp": "一応食べたが雑だったと答える",
            "jp_summary": "相手が食事を済ませたか聞いている",
            "stance": {"warmth": 0.25, "tease": 0.15, "blunt": 0.35, "distance": 0.2},
            "constraints": {"sentence_count": 1, "max_chars": 38},
            "must_avoid": [],
        },
        "expect_dialogue_act": "daily_state_answer",
        "expect_any": ["食べ", "腹", "済ませ", "飯"],
    },
    {
        "id": "version_fragment_clarify",
        "input": "那v2版呢",
        "logic": {
            "intent": "version_fragment_clarify",
            "scene": "casual",
            "surface_act": "version_fragment_clarify",
            "response_mode": "clarify_light",
            "payload_level": "medium",
            "core_message_jp": "何の版か分からないので作品名を聞く",
            "jp_summary": "相手が版だけを言っている",
            "stance": {"warmth": 0.2, "tease": 0.25, "blunt": 0.45, "distance": 0.25},
            "constraints": {"sentence_count": 1, "max_chars": 36},
            "must_avoid": [],
        },
        "expect_dialogue_act": "reference_probe",
        "expect_any": ["版", "何", "作品", "タイトル"],
    },
    {
        "id": "false_premise_pushback",
        "input": "你昨天不是說你是AI嗎",
        "logic": {
            "intent": "premise_doubt",
            "scene": "refusal",
            "surface_act": "challenge_mirror",
            "response_mode": "premise_challenge",
            "payload_level": "medium",
            "core_message_jp": "その前提は違うので一度止める",
            "jp_summary": "相手が怪しい前提を置いている",
            "premise_check": "reject",
            "stance": {"warmth": 0.15, "tease": 0.2, "blunt": 0.65, "distance": 0.5},
            "constraints": {"sentence_count": 1, "max_chars": 40},
            "must_avoid": [],
        },
        "expect_dialogue_act": "frame_negotiation",
        "expect_any": ["前提", "違", "どこ", "何"],
        "avoid_any": ["AI"],
    },
    {
        "id": "memory_known_name",
        "input": "你還記得我的名字嗎",
        "memory_data": {
            "profile_structured": {"name": "ジェリー"},
            "profile": "使用者の名前はジェリー",
        },
        "logic": {
            "intent": "recall_name",
            "scene": "casual",
            "surface_act": "memory_presence_reply",
            "response_mode": "direct_answer",
            "payload_level": "medium",
            "core_message_jp": "名前はジェリーだと答える",
            "jp_summary": "相手が名前を覚えているか聞いている",
            "memory_use_expected": True,
            "memory_anchor": {"kind": "profile", "jp_anchor": "ジェリー", "terms": ["ジェリー"]},
            "stance": {"warmth": 0.3, "tease": 0.15, "blunt": 0.35, "distance": 0.2},
            "constraints": {"sentence_count": 1, "max_chars": 34},
            "must_avoid": [],
        },
        "expect_dialogue_act": "memory_accounting",
        "expect_any": ["ジェリー"],
    },
]


def _meaningful_terms(text):
    return re.findall(r"[A-Za-z0-9_]+|[\u3040-\u30ff\u4e00-\u9fff]{2,}", str(text or ""))


def _case_checks(row):
    reply = row["reply"]
    logic = row["logic"]
    speech_plan = logic.get("human_speech_plan") or {}
    failures = []
    if not speech_plan:
        failures.append("missing human_speech_plan")
    if speech_plan.get("dialogue_act") != row["expect_dialogue_act"]:
        failures.append(f"dialogue_act expected {row['expect_dialogue_act']} got {speech_plan.get('dialogue_act')}")
    if any(ord(ch) < 128 and ch.isalpha() for ch in reply):
        failures.append("reply contains English alphabet leak")
    if len(set(_meaningful_terms(reply))) < 2:
        failures.append("reply content density too low")
    if not any(token in reply for token in row["expect_any"]):
        failures.append(f"reply missing expected semantic anchors: {row['expect_any']}")
    if reply in row["logic"].get("must_avoid", []):
        failures.append("reply reused forbidden sentence")
    if any(token in reply for token in row.get("avoid_any", [])):
        failures.append(f"reply contains forbidden semantic pattern: {row.get('avoid_any')}")
    if not speech_plan.get("content_units"):
        failures.append("speech plan has no content_units")
    return failures


def main():
    rb = RightBrain(load_model=False)
    rows = []
    for case in CASES:
        logic = json.loads(json.dumps(case["logic"], ensure_ascii=False))
        memory_data = _merged_memory(case.get("memory_data"))
        psyche = dict(PSYCHE)
        psyche.update(case.get("psyche") or {})
        reply = rb.speak(case["input"], logic, memory_data, psyche)
        row = {
            "id": case["id"],
            "input": case["input"],
            "reply": reply,
            "logic": logic,
            "speech_plan": logic.get("human_speech_plan") or {},
            "expect_dialogue_act": case["expect_dialogue_act"],
            "expect_any": case["expect_any"],
            "avoid_any": case.get("avoid_any", []),
        }
        failures = _case_checks(row)
        row["pass"] = not failures
        row["failures"] = failures
        rows.append(row)

    total = len(rows)
    pass_count = sum(1 for row in rows if row["pass"])
    speech_plan_count = sum(1 for row in rows if row.get("speech_plan"))
    dialogue_match_count = sum(
        1 for row in rows if (row.get("speech_plan") or {}).get("dialogue_act") == row["expect_dialogue_act"]
    )
    anchor_hit_count = sum(1 for row in rows if any(token in row["reply"] for token in row["expect_any"]))
    density_count = sum(1 for row in rows if len(set(_meaningful_terms(row["reply"]))) >= 2)
    english_leak_count = sum(1 for row in rows if any(ord(ch) < 128 and ch.isalpha() for ch in row["reply"]))
    metrics = {
        "case_count": total,
        "pass_count": pass_count,
        "pass_rate": round(pass_count / max(1, total), 4),
        "speech_plan_presence_rate": round(speech_plan_count / max(1, total), 4),
        "dialogue_act_match_rate": round(dialogue_match_count / max(1, total), 4),
        "semantic_anchor_hit_rate": round(anchor_hit_count / max(1, total), 4),
        "content_density_pass_rate": round(density_count / max(1, total), 4),
        "english_leak_rate": round(english_leak_count / max(1, total), 4),
    }
    report = {
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "scope": "human_speech_realization_layer_eval",
        "metrics": metrics,
        "cases": rows,
    }
    with open(HUMAN_SPEECH_LAYER_REPORT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    lines = [
        "# Human Speech Layer Eval Report",
        "",
        "此評測確認右腦表面生成前，是否已加入人類說話的中介層：語用功能、語意單元、風格算子、轉接鉤子與反重複約束。",
        "",
        "## Metrics",
        "",
    ]
    names = {
        "case_count": "案例數",
        "pass_count": "通過數",
        "pass_rate": "整體通過率，越高越好",
        "speech_plan_presence_rate": "說話計畫存在率，越高越好",
        "dialogue_act_match_rate": "語用功能命中率，越高越好",
        "semantic_anchor_hit_rate": "語意錨點命中率，越高越好",
        "content_density_pass_rate": "有效詞彙密度通過率，越高越好",
        "english_leak_rate": "英文洩漏率，越低越好",
    }
    for key, value in metrics.items():
        lines.append(f"- {names.get(key, key)}: {value}")
    lines.extend(["", "## Cases", ""])
    for row in rows:
        status = "PASS" if row["pass"] else "FAIL"
        speech_plan = row.get("speech_plan") or {}
        lines.append(f"### {row['id']} - {status}")
        lines.append(f"- 問: {row['input']}")
        lines.append(f"- 答: {row['reply']}")
        lines.append(f"- dialogue_act: {speech_plan.get('dialogue_act')} / expected: {row['expect_dialogue_act']}")
        lines.append(f"- content_units: {speech_plan.get('content_units')}")
        lines.append(f"- style_operators: {speech_plan.get('style_operators')}")
        if row["failures"]:
            lines.append(f"- failures: {'; '.join(row['failures'])}")
        lines.append("")
    with open(HUMAN_SPEECH_LAYER_REPORT_MD_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
