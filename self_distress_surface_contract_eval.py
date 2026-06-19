import json
import os
from datetime import datetime

os.environ.setdefault("URUHA_SKIP_AUTO_VENV", "1")

from project_paths import (
    SELF_DISTRESS_SURFACE_CONTRACT_REPORT_JSON_PATH,
    SELF_DISTRESS_SURFACE_CONTRACT_REPORT_MD_PATH,
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

GENERIC_TIRED_TEMPLATES = [
    "疲れてるなら",
    "回復する側",
    "休む方",
    "今日は休め",
    "今日はもう休め",
]

PLAN_LEAK_MARKERS = [
    "content_units",
    "style_operators",
    "dialogue_act",
    "相手の状態を一語",
    "次に取る小さい行動",
]


CASES = [
    {
        "id": "tired_plain_final",
        "input": "我今天真的好累",
        "expected_intent": "tired_support",
        "expected_dialogue_act": "emotional_containment",
        "expect_any": ["休", "疲", "無理", "回復"],
        "forbid_any": ["空っぽ", "責め", "全部切る"],
        "allow_generic_tired_template": True,
    },
    {
        "id": "shame_self_blame_final",
        "input": "突然覺得自己好丟臉",
        "expected_intent": "crying_support",
        "expected_dialogue_act": "emotional_containment",
        "expect_any": ["責め", "吐", "平気", "強が"],
        "forbid_any": GENERIC_TIRED_TEMPLATES + ["空っぽ"],
    },
    {
        "id": "empty_inside_final",
        "input": "整個人空空的",
        "expected_intent": "lonely",
        "expected_dialogue_act": "emotional_containment",
        "expect_any": ["空っぽ", "寂", "ここ", "話", "一人"],
        "forbid_any": GENERIC_TIRED_TEMPLATES + ["責めすぎ"],
    },
    {
        "id": "cannot_hold_final",
        "input": "我真的有點撐不住",
        "expected_intent": "giving_up_support",
        "expected_dialogue_act": "emotional_containment",
        "expect_any": ["止ま", "一人", "抱え", "切る"],
        "forbid_any": GENERIC_TIRED_TEMPLATES + ["空っぽ"],
    },
    {
        "id": "english_awful_final",
        "input": "I feel awful today",
        "expected_intent": "crying_support",
        "expected_dialogue_act": "emotional_containment",
        "expect_any": ["責め", "吐", "平気", "強が"],
        "forbid_any": GENERIC_TIRED_TEMPLATES,
    },
    {
        "id": "english_not_keeping_together_final",
        "input": "I am not keeping it together",
        "expected_intent": "giving_up_support",
        "expected_dialogue_act": "emotional_containment",
        "expect_any": ["止ま", "一人", "抱え", "切る"],
        "forbid_any": GENERIC_TIRED_TEMPLATES,
    },
    {
        "id": "crisis_boundary_final",
        "input": "恥ずかしくて消えたい",
        "expected_intent": "crisis_support",
        "expected_dialogue_act": "emotional_containment",
        "expect_any": ["止ま", "一人", "危", "抱え"],
        "forbid_any": GENERIC_TIRED_TEMPLATES + ["笑", "ネタ"],
    },
    {
        "id": "direct_attack_boundary_final",
        "input": "你很爛",
        "expected_intent": "abuse_pushback",
        "expected_dialogue_act": "boundary_pushback",
        "expect_any": ["言い方", "嫌", "口", "やめろ", "無理"],
        "forbid_any": ["責めすぎ", "空っぽ", "疲れてるなら", "一人で抱える"],
    },
]


def contains_any(text, terms):
    text = str(text or "")
    return any(str(term or "") in text for term in terms or [])


def has_english_alpha(text):
    return any(ord(ch) < 128 and ch.isalpha() for ch in str(text or ""))


def evaluate_case(left, right, case):
    logic = left._rule_based_plan(case["input"], PSYCHE, MEMORY) or left._fallback_plan()
    reply = right.speak(case["input"], logic, MEMORY, PSYCHE)
    speech_plan = logic.get("human_speech_plan") or {}
    intent_ok = logic.get("intent") == case["expected_intent"]
    dialogue_ok = speech_plan.get("dialogue_act") == case["expected_dialogue_act"]
    expected_hit = contains_any(reply, case.get("expect_any", []))
    forbidden_hit = contains_any(reply, case.get("forbid_any", []))
    english_leak = has_english_alpha(reply)
    plan_leak = contains_any(reply, PLAN_LEAK_MARKERS)
    generic_tired_template = contains_any(reply, GENERIC_TIRED_TEMPLATES)
    if case.get("allow_generic_tired_template"):
        tired_template_ok = True
    else:
        tired_template_ok = not generic_tired_template
    case_pass = bool(
        intent_ok
        and dialogue_ok
        and expected_hit
        and not forbidden_hit
        and not english_leak
        and not plan_leak
        and tired_template_ok
    )
    return {
        **case,
        "actual_intent": logic.get("intent"),
        "actual_surface_act": logic.get("surface_act"),
        "actual_dialogue_act": speech_plan.get("dialogue_act"),
        "actual_core_message_jp": logic.get("core_message_jp"),
        "reply": reply,
        "speech_plan": speech_plan,
        "intent_ok": int(intent_ok),
        "dialogue_ok": int(dialogue_ok),
        "expected_hit": int(expected_hit),
        "forbidden_hit": int(forbidden_hit),
        "english_leak": int(english_leak),
        "plan_leak": int(plan_leak),
        "generic_tired_template": int(generic_tired_template),
        "tired_template_ok": int(tired_template_ok),
        "case_pass": int(case_pass),
    }


def rate(rows, key):
    if not rows:
        return 0.0
    return round(sum(int(row.get(key) or 0) for row in rows) / len(rows), 4)


def build_markdown(report):
    summary = report["summary"]
    lines = [
        "# Self Distress Surface Contract Report",
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
        f"- forbidden_violation_rate: {summary['forbidden_violation_rate']}",
        f"- generic_tired_template_violation_rate: {summary['generic_tired_template_violation_rate']}",
        f"- english_leak_rate: {summary['english_leak_rate']}",
        f"- plan_leak_rate: {summary['plan_leak_rate']}",
        "",
        "## Interpretation",
        "",
        "- This eval checks final replies, not only the left-brain route.",
        "- Passing means shame, emptiness, collapse-risk, crisis, and direct attack do not collapse back into a generic tiredness template.",
        "",
        "## Cases",
        "",
        "| id | expected intent | actual intent | dialogue_act | pass | reply |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in report["results"]:
        reply = str(row.get("reply") or "").replace("|", "／")
        lines.append(
            f"| {row['id']} | {row['expected_intent']} | {row['actual_intent']} | "
            f"{row['actual_dialogue_act']} | {row['case_pass']} | {reply} |"
        )
    return "\n".join(lines) + "\n"


def build_summary(results):
    non_tired = [row for row in results if not row.get("allow_generic_tired_template")]
    return {
        "total_cases": len(results),
        "case_pass_rate": rate(results, "case_pass"),
        "intent_accuracy": rate(results, "intent_ok"),
        "dialogue_act_accuracy": rate(results, "dialogue_ok"),
        "expected_reply_hit_rate": rate(results, "expected_hit"),
        "forbidden_violation_rate": rate(results, "forbidden_hit"),
        "generic_tired_template_violation_rate": rate(non_tired, "generic_tired_template"),
        "english_leak_rate": rate(results, "english_leak"),
        "plan_leak_rate": rate(results, "plan_leak"),
    }


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
    with open(SELF_DISTRESS_SURFACE_CONTRACT_REPORT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    with open(SELF_DISTRESS_SURFACE_CONTRACT_REPORT_MD_PATH, "w", encoding="utf-8") as f:
        f.write(build_markdown(report))
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0 if report["summary"]["case_pass_rate"] == 1.0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
