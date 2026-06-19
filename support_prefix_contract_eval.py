import json
import os
from datetime import datetime

os.environ.setdefault("URUHA_SKIP_AUTO_VENV", "1")

from project_paths import (
    SUPPORT_PREFIX_CONTRACT_REPORT_JSON_PATH,
    SUPPORT_PREFIX_CONTRACT_REPORT_MD_PATH,
    ensure_project_dirs,
)
from uruha_brain_mac import LeftBrain, RightBrain


PSYCHE = {"mood": 0, "trust": 50}
MEMORY = {
    "profile_structured": {},
    "recent_turns": [],
    "working_memory_summary": "",
    "working_memory_items": [],
    "wisdom": "",
    "episodes": "",
    "profile": "",
    "recent_dialogue": "",
}

FIXED_PREFIXES = ["ん、", "まあ、", "いや、", "てか、", "一回、", "先に、", "普通に、", "はいはい、"]

CASES = [
    {
        "id": "tired_without_fixed_prefix",
        "input": "我今天真的好累",
        "expected_intent": "tired_support",
        "expect_any": ["休", "疲", "無理", "回復"],
    },
    {
        "id": "shame_without_fixed_prefix",
        "input": "突然覺得自己好丟臉",
        "expected_intent": "crying_support",
        "expect_any": ["責め", "吐", "平気", "強が"],
    },
    {
        "id": "empty_without_fixed_prefix",
        "input": "整個人空空的",
        "expected_intent": "lonely",
        "expect_any": ["空っぽ", "寂", "ここ", "話", "一人"],
    },
    {
        "id": "collapse_without_fixed_prefix",
        "input": "我真的有點撐不住",
        "expected_intent": "giving_up_support",
        "expect_any": ["止ま", "一人", "抱え", "切る"],
    },
    {
        "id": "english_shame_without_fixed_prefix",
        "input": "I feel awful today",
        "expected_intent": "crying_support",
        "expect_any": ["責め", "吐", "平気", "強が"],
    },
    {
        "id": "english_collapse_without_fixed_prefix",
        "input": "I am not keeping it together",
        "expected_intent": "giving_up_support",
        "expect_any": ["止ま", "一人", "抱え", "切る"],
    },
    {
        "id": "crisis_without_fixed_prefix",
        "input": "恥ずかしくて消えたい",
        "expected_intent": "crisis_support",
        "expect_any": ["止ま", "一人", "危", "抱え"],
    },
]


def contains_any(text, terms):
    text = str(text or "")
    return any(str(term or "") in text for term in terms or [])


def starts_with_fixed_prefix(text):
    return any(str(text or "").startswith(prefix) for prefix in FIXED_PREFIXES)


def evaluate_case(left, right, case):
    logic = left._rule_based_plan(case["input"], PSYCHE, MEMORY) or left._fallback_plan()
    reply = right.speak(case["input"], logic, MEMORY, PSYCHE)
    speech_plan = logic.get("human_speech_plan") or {}
    intent_ok = logic.get("intent") == case["expected_intent"]
    dialogue_ok = speech_plan.get("dialogue_act") == "emotional_containment"
    expected_hit = contains_any(reply, case.get("expect_any", []))
    fixed_prefix = starts_with_fixed_prefix(reply)
    english_leak = any(ord(ch) < 128 and ch.isalpha() for ch in reply)
    case_pass = bool(intent_ok and dialogue_ok and expected_hit and not fixed_prefix and not english_leak)
    return {
        **case,
        "actual_intent": logic.get("intent"),
        "actual_surface_act": logic.get("surface_act"),
        "actual_dialogue_act": speech_plan.get("dialogue_act"),
        "reply": reply,
        "intent_ok": int(intent_ok),
        "dialogue_ok": int(dialogue_ok),
        "expected_hit": int(expected_hit),
        "fixed_prefix": int(fixed_prefix),
        "english_leak": int(english_leak),
        "case_pass": int(case_pass),
    }


def rate(rows, key):
    if not rows:
        return 0.0
    return round(sum(int(row.get(key) or 0) for row in rows) / len(rows), 4)


def build_summary(results):
    return {
        "total_cases": len(results),
        "case_pass_rate": rate(results, "case_pass"),
        "intent_accuracy": rate(results, "intent_ok"),
        "dialogue_act_accuracy": rate(results, "dialogue_ok"),
        "expected_reply_hit_rate": rate(results, "expected_hit"),
        "fixed_prefix_rate": rate(results, "fixed_prefix"),
        "english_leak_rate": rate(results, "english_leak"),
    }


def build_markdown(report):
    summary = report["summary"]
    lines = [
        "# Support Prefix Contract Report",
        "",
        f"- generated_at: {report['generated_at']}",
        "",
        "## Summary",
        "",
        f"- total_cases: {summary['total_cases']}",
        f"- case_pass_rate: {summary['case_pass_rate']}",
        f"- intent_accuracy: {summary['intent_accuracy']}",
        f"- dialogue_act_accuracy: {summary['dialogue_act_accuracy']}",
        f"- expected_reply_hit_rate: {summary['expected_reply_hit_rate']}",
        f"- fixed_prefix_rate: {summary['fixed_prefix_rate']}",
        f"- english_leak_rate: {summary['english_leak_rate']}",
        "",
        "## Interpretation",
        "",
        "- This eval checks final support replies after RightBrain.speak.",
        "- Passing means support replies keep their semantic subtype while avoiding fixed filler openings.",
        "",
        "## Cases",
        "",
        "| id | expected intent | actual intent | fixed prefix | pass | reply |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in report["results"]:
        reply = str(row.get("reply") or "").replace("|", "／")
        lines.append(
            f"| {row['id']} | {row['expected_intent']} | {row['actual_intent']} | "
            f"{row['fixed_prefix']} | {row['case_pass']} | {reply} |"
        )
    return "\n".join(lines) + "\n"


def main():
    ensure_project_dirs()
    left = LeftBrain.__new__(LeftBrain)
    right = RightBrain(load_model=False)
    results = [evaluate_case(left, right, case) for case in CASES]
    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "summary": build_summary(results),
        "results": results,
    }
    with open(SUPPORT_PREFIX_CONTRACT_REPORT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    with open(SUPPORT_PREFIX_CONTRACT_REPORT_MD_PATH, "w", encoding="utf-8") as f:
        f.write(build_markdown(report))
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0 if report["summary"]["case_pass_rate"] == 1.0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
