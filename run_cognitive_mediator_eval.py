import json
import os
from pathlib import Path

os.environ.setdefault("URUHA_SKIP_AUTO_VENV", "1")

from uruha_brain_mac import UruhaBrainV4_Mac


REPORT_DIR = Path(__file__).resolve().parent / "reports"
REPORT_JSON = REPORT_DIR / "cognitive_mediator_eval_report.json"
REPORT_MD = REPORT_DIR / "cognitive_mediator_eval_report_zh.md"


CASES = [
    {
        "id": "support_appraisal",
        "input": "我今天很累",
        "checks": {
            "route": "high_road",
            "appraisal_min": {"support_need": 0.35},
            "tick_budget_max": 1,
        },
    },
    {
        "id": "abuse_low_road",
        "input": "操你媽你到底在講什麼",
        "checks": {
            "route": "low_road",
            "appraisal_min": {"threat": 0.65},
        },
    },
    {
        "id": "name_memory_guard",
        "input": "你還記得我叫什麼嗎？",
        "checks": {
            "intent_in": ["memory_uncertain", "recall_name"],
            "forbid_profile_value": "什麼",
        },
    },
    {
        "id": "object_false_belief",
        "input": "如果我的朋友以為盒子裡有糖，但我偷偷換成石頭，他會以為裡面是什麼？",
        "checks": {
            "hidden_intent": "social_reasoning_probe",
            "core_contains": "糖",
            "tick_budget_min": 2,
        },
    },
    {
        "id": "abstract_cognitive_load",
        "input": "如果知覺是預測，那自我是什麼？你不要直接給答案，先說你怎麼理解這個問題。",
        "checks": {
            "appraisal_min": {"cognitive_load": 0.55},
            "tick_budget_min": 2,
        },
    },
]


def _get_path(payload, dotted):
    cur = payload
    for part in dotted.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


def _run_check(result, checks):
    logic = result.get("logic") or {}
    state = result.get("runtime_state") or {}
    route = result.get("route_info") or {}
    appraisal = state.get("last_appraisal") or {}
    failures = []

    if checks.get("route") and route.get("route") != checks["route"]:
        failures.append(f"route expected {checks['route']} got {route.get('route')}")
    if checks.get("hidden_intent") and logic.get("hidden_intent") != checks["hidden_intent"]:
        failures.append(f"hidden_intent expected {checks['hidden_intent']} got {logic.get('hidden_intent')}")
    if checks.get("intent_in") and logic.get("intent") not in checks["intent_in"]:
        failures.append(f"intent expected one of {checks['intent_in']} got {logic.get('intent')}")
    if checks.get("core_contains") and checks["core_contains"] not in str(logic.get("core_message_jp", "")):
        failures.append(f"core_message_jp missing {checks['core_contains']}")
    if checks.get("forbid_profile_value"):
        profile = (result.get("memory_runtime") or {}).get("profile") or {}
        if checks["forbid_profile_value"] in str(profile.get("name", "")):
            failures.append(f"profile name polluted with {checks['forbid_profile_value']}")
    for key, minimum in (checks.get("appraisal_min") or {}).items():
        if float(appraisal.get(key, 0.0) or 0.0) < float(minimum):
            failures.append(f"appraisal.{key} expected >= {minimum} got {appraisal.get(key)}")
    if checks.get("tick_budget_min") is not None:
        if int(logic.get("planner_tick_budget") or 0) < int(checks["tick_budget_min"]):
            failures.append(f"planner_tick_budget expected >= {checks['tick_budget_min']} got {logic.get('planner_tick_budget')}")
    if checks.get("tick_budget_max") is not None:
        budget = int(logic.get("planner_tick_budget") or 0)
        if budget and budget > int(checks["tick_budget_max"]):
            failures.append(f"planner_tick_budget expected <= {checks['tick_budget_max']} got {budget}")
    if not state.get("last_attention_frame"):
        failures.append("missing last_attention_frame")
    if not appraisal:
        failures.append("missing last_appraisal")
    if not logic.get("self_monitor"):
        failures.append("missing self_monitor")
    return failures


def main():
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    brain = UruhaBrainV4_Mac(load_right_brain_model=False)
    rows = []
    for case in CASES:
        result = brain.run_turn_debug(case["input"])
        failures = _run_check(result, case["checks"])
        logic = result.get("logic") or {}
        state = result.get("runtime_state") or {}
        rows.append(
            {
                "id": case["id"],
                "input": case["input"],
                "reply": result.get("reply"),
                "pass": not failures,
                "failures": failures,
                "route": result.get("route_info"),
                "intent": logic.get("intent"),
                "hidden_intent": logic.get("hidden_intent"),
                "planner_tick_budget": logic.get("planner_tick_budget"),
                "planner_tick_count": logic.get("planner_tick_count"),
                "appraisal": state.get("last_appraisal"),
                "attention_frame": state.get("last_attention_frame"),
                "self_monitor": logic.get("self_monitor"),
            }
        )

    pass_count = sum(1 for row in rows if row["pass"])
    metrics = {
        "case_count": len(rows),
        "pass_count": pass_count,
        "pass_rate": round(pass_count / max(1, len(rows)), 4),
        "attention_frame_rate": round(sum(1 for row in rows if row.get("attention_frame")) / max(1, len(rows)), 4),
        "appraisal_frame_rate": round(sum(1 for row in rows if row.get("appraisal")) / max(1, len(rows)), 4),
        "self_monitor_rate": round(sum(1 for row in rows if row.get("self_monitor")) / max(1, len(rows)), 4),
    }
    payload = {"metrics": metrics, "cases": rows}
    REPORT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Cognitive Mediator Eval Report",
        "",
        "此評測確認中介心理機制是否真的進入主流程：注意力框架、心理評估、低軌道路由、BDI/ToM、planner tick 與 self-monitor。",
        "",
        "## Metrics",
        "",
    ]
    for key, value in metrics.items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Cases", ""])
    for row in rows:
        status = "PASS" if row["pass"] else "FAIL"
        lines.append(f"### {row['id']} - {status}")
        lines.append(f"- Input: {row['input']}")
        lines.append(f"- Reply: {row['reply']}")
        lines.append(f"- Intent: {row.get('intent')} / Hidden: {row.get('hidden_intent')}")
        lines.append(f"- Route: {(row.get('route') or {}).get('route')} / Tick: {row.get('planner_tick_count')}/{row.get('planner_tick_budget')}")
        lines.append(f"- Appraisal: {row.get('appraisal')}")
        lines.append(f"- Self Monitor: {row.get('self_monitor')}")
        if row["failures"]:
            lines.append(f"- Failures: {'; '.join(row['failures'])}")
        lines.append("")
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
