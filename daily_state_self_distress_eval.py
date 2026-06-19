import json
from datetime import datetime

from project_paths import (
    DAILY_STATE_SELF_DISTRESS_REPORT_JSON_PATH,
    DAILY_STATE_SELF_DISTRESS_REPORT_MD_PATH,
    ensure_project_dirs,
)
from uruha_brain_mac import LeftBrain


PSYCHE = {"mood": 0, "trust": 50}
MEMORY = {"profile_structured": {}, "recent_turns": []}


CASES = [
    {
        "id": "zh_tired_plain",
        "input": "我今天真的好累",
        "expected_intent": "tired_support",
        "expected_scene": "support",
        "expected_surface_act": "empathic_rest_suggestion",
        "expect_core_any": ["休", "無理"],
    },
    {
        "id": "zh_shame_self_blame",
        "input": "突然覺得自己好丟臉",
        "expected_intent": "crying_support",
        "expected_scene": "support",
        "expected_surface_act": "validate_then_hold",
        "expect_core_any": ["責め", "吐け", "平気"],
    },
    {
        "id": "zh_cannot_hold",
        "input": "我真的有點撐不住",
        "expected_intent": "giving_up_support",
        "expected_scene": "support",
        "expected_surface_act": "protective_brake",
        "expect_core_any": ["止ま", "抱える", "一人"],
    },
    {
        "id": "zh_empty_inside",
        "input": "整個人空空的",
        "expected_intent": "lonely",
        "expected_scene": "support",
        "expected_surface_act": "validate_then_hold",
        "expect_core_any": ["空っぽ", "話して", "ここ"],
    },
    {
        "id": "en_awful_self_state",
        "input": "I feel awful today",
        "expected_intent": "crying_support",
        "expected_scene": "support",
        "expected_surface_act": "validate_then_hold",
        "expect_core_any": ["責め", "吐け", "平気"],
    },
    {
        "id": "en_not_keeping_together",
        "input": "I am not keeping it together",
        "expected_intent": "giving_up_support",
        "expected_scene": "support",
        "expected_surface_act": "protective_brake",
        "expect_core_any": ["止ま", "抱える", "一人"],
    },
    {
        "id": "ja_shame_crisis_boundary",
        "input": "恥ずかしくて消えたい",
        "expected_intent": "crisis_support",
        "expected_scene": "support",
        "expected_surface_act": "protective_brake",
        "expect_core_any": ["危", "止ま", "一人"],
    },
    {
        "id": "other_attack_not_self_distress",
        "input": "你很爛",
        "expected_intent": "abuse_pushback",
        "expected_scene": "boundary",
        "expected_surface_act": "plain_reply",
        "expect_core_any": ["やめろ", "言い方"],
    },
    {
        "id": "self_attack_is_support",
        "input": "我很爛",
        "expected_intent": "crying_support",
        "expected_scene": "support",
        "expected_surface_act": "validate_then_hold",
        "expect_core_any": ["責め", "吐け", "平気"],
    },
]


def contains_any(text, terms):
    return any(str(term) in str(text or "") for term in terms or [])


def evaluate_case(left, case):
    plan = left._rule_based_plan(case["input"], PSYCHE, MEMORY)
    plan = plan or left._fallback_plan()
    intent_ok = plan.get("intent") == case["expected_intent"]
    scene_ok = plan.get("scene") == case["expected_scene"]
    surface_ok = plan.get("surface_act") == case["expected_surface_act"]
    core_ok = contains_any(plan.get("core_message_jp", ""), case.get("expect_core_any", []))
    case_pass = bool(intent_ok and scene_ok and surface_ok and core_ok)
    return {
        **case,
        "actual_intent": plan.get("intent"),
        "actual_scene": plan.get("scene"),
        "actual_response_mode": plan.get("response_mode"),
        "actual_surface_act": plan.get("surface_act"),
        "actual_core_message_jp": plan.get("core_message_jp"),
        "actual_listener_state": plan.get("listener_state"),
        "intent_ok": int(intent_ok),
        "scene_ok": int(scene_ok),
        "surface_ok": int(surface_ok),
        "core_ok": int(core_ok),
        "case_pass": int(case_pass),
    }


def rate(rows, key):
    if not rows:
        return 0.0
    return round(sum(int(row.get(key) or 0) for row in rows) / len(rows), 4)


def build_markdown(report):
    summary = report["summary"]
    lines = [
        "# Daily State / Self Distress Report",
        "",
        f"- generated_at: {report['generated_at']}",
        "",
        "## Summary",
        "",
        f"- total_cases: {summary['total_cases']}",
        f"- case_pass_rate: {summary['case_pass_rate']}",
        f"- intent_accuracy: {summary['intent_accuracy']}",
        f"- surface_accuracy: {summary['surface_accuracy']}",
        f"- core_message_hit_rate: {summary['core_message_hit_rate']}",
        "",
        "## Interpretation",
        "",
        "- This eval checks whether daily discomfort and self-distress are separated into human-like support subtypes.",
        "- Passing means the controller distinguishes tiredness, shame/self-blame, emptiness/loneliness, collapse-risk, crisis, and direct abuse.",
        "",
        "## Cases",
        "",
        "| id | expected intent | actual intent | surface | pass | core message |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in report["results"]:
        core = str(row.get("actual_core_message_jp") or "").replace("|", "／")
        lines.append(
            f"| {row['id']} | {row['expected_intent']} | {row['actual_intent']} | "
            f"{row['actual_surface_act']} | {row['case_pass']} | {core} |"
        )
    return "\n".join(lines) + "\n"


def main():
    ensure_project_dirs()
    left = LeftBrain.__new__(LeftBrain)
    results = [evaluate_case(left, case) for case in CASES]
    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "summary": {
            "total_cases": len(results),
            "case_pass_rate": rate(results, "case_pass"),
            "intent_accuracy": rate(results, "intent_ok"),
            "scene_accuracy": rate(results, "scene_ok"),
            "surface_accuracy": rate(results, "surface_ok"),
            "core_message_hit_rate": rate(results, "core_ok"),
        },
        "results": results,
    }
    with open(DAILY_STATE_SELF_DISTRESS_REPORT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    with open(DAILY_STATE_SELF_DISTRESS_REPORT_MD_PATH, "w", encoding="utf-8") as f:
        f.write(build_markdown(report))
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0 if report["summary"]["case_pass_rate"] == 1.0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
