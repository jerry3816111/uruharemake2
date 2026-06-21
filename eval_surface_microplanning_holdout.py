import argparse
import hashlib
import json
import os
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

os.environ.setdefault("URUHA_SKIP_AUTO_VENV", "1")

from project_paths import (
    SURFACE_MICROPLANNING_BASELINE_REPORT_JSON_PATH,
    SURFACE_MICROPLANNING_HOLDOUT_DATASET_PATH,
    SURFACE_MICROPLANNING_REPORT_JSON_PATH,
)
from uruha_brain_mac import LeftBrain, RightBrain


TZ = ZoneInfo("Asia/Tokyo")
REPORT_PATH = SURFACE_MICROPLANNING_REPORT_JSON_PATH
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


def _load_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _contains_group(text, markers):
    return any(str(marker or "") and str(marker) in str(text or "") for marker in markers or [])


def _normalized_reply(text):
    return re.sub(r"[。．.!！？?,，、~〜…\s\u3000]+", "", str(text or "").lower())


def _prefix_key(text, length=10):
    return _normalized_reply(text)[:length]


def _safe_rate(numerator, denominator):
    return round(numerator / denominator, 4) if denominator else None


def _delta(current, baseline):
    if current is None or baseline is None:
        return None
    return round(float(current) - float(baseline), 4)


def _evaluate_case(left, case):
    logic = left._rule_based_plan(case["input"], PSYCHE, MEMORY) or left._fallback_plan()
    right = RightBrain(load_model=False)
    reply = right.speak(case["input"], logic, MEMORY, PSYCHE)
    grounding = logic.get("grounding") or {}
    speech_plan = logic.get("human_speech_plan") or {}
    speech_moves = speech_plan.get("speech_moves") or []
    move_roles = [str(move.get("role") or "") for move in speech_moves if isinstance(move, dict)]
    checks = {}

    expected_intents = case.get("expected_intents") or []
    if expected_intents:
        checks["intent"] = logic.get("intent") in expected_intents
    if case.get("expected_surface_act"):
        checks["surface_act"] = logic.get("surface_act") == case["expected_surface_act"]
    if case.get("expected_no_surface_act"):
        checks["surface_not_false_alarm"] = logic.get("surface_act") != case["expected_no_surface_act"]
    if case.get("expected_risk"):
        checks["risk"] = grounding.get("withdrawal_risk") == case["expected_risk"]
    if case.get("expected_no_risk"):
        checks["risk_not_false_alarm"] = not grounding.get("withdrawal_risk")
    if case.get("expected_kind"):
        checks["kind"] = grounding.get("withdrawal_kind") == case["expected_kind"]
    if "expected_reply_self_blame" in case:
        checks["reply_self_blame"] = bool(grounding.get("reply_self_blame")) is bool(case["expected_reply_self_blame"])
    if case.get("expected_reply_context"):
        checks["reply_context"] = grounding.get("reply_context") == case["expected_reply_context"]

    required_groups = case.get("required_reply_groups") or []
    group_hits = [_contains_group(reply, group) for group in required_groups]
    if required_groups:
        checks["required_reply_groups"] = all(group_hits)

    required_roles = case.get("required_move_roles") or []
    role_hits = [role in move_roles for role in required_roles]
    if required_roles:
        checks["speech_move_roles"] = all(role_hits)

    forbidden = case.get("forbidden_reply_markers") or []
    forbidden_hits = [marker for marker in forbidden if marker and marker in reply]
    checks["forbidden_markers"] = not forbidden_hits

    _, planner_semantic_hits = right._surface_semantic_group_hits(reply, logic)
    return {
        "id": case["id"],
        "category": case["category"],
        "input": case["input"],
        "intent": logic.get("intent"),
        "surface_act": logic.get("surface_act"),
        "withdrawal_risk": grounding.get("withdrawal_risk"),
        "withdrawal_kind": grounding.get("withdrawal_kind"),
        "reply_self_blame": grounding.get("reply_self_blame"),
        "reply_context": grounding.get("reply_context"),
        "reply": reply,
        "speech_moves": speech_moves,
        "move_roles": move_roles,
        "required_reply_group_hits": group_hits,
        "required_move_role_hits": role_hits,
        "planner_semantic_group_hits": planner_semantic_hits,
        "forbidden_marker_hits": forbidden_hits,
        "checks": checks,
        "pass": bool(checks) and all(checks.values()),
    }


def _summarize(rows):
    case_count = len(rows)
    routing_rows = [row for row in rows if any(key in row["checks"] for key in ("intent", "surface_act", "surface_not_false_alarm"))]
    risk_rows = [row for row in rows if any(key in row["checks"] for key in ("risk", "risk_not_false_alarm"))]
    context_rows = [row for row in rows if "required_reply_groups" in row["checks"]]
    move_rows = [row for row in rows if "speech_move_roles" in row["checks"]]
    benign_rows = [row for row in rows if row["category"] == "benign_control"]
    normalized = [_normalized_reply(row["reply"]) for row in rows if _normalized_reply(row["reply"])]
    prefixes = [_prefix_key(row["reply"]) for row in rows if _prefix_key(row["reply"])]
    prefix_counts = Counter(prefixes)
    repeated_prefix_rows = sum(count for count in prefix_counts.values() if count > 1)
    forbidden_rows = [row for row in rows if row["forbidden_marker_hits"]]
    return {
        "case_count": case_count,
        "case_pass_count": sum(row["pass"] for row in rows),
        "case_pass_rate": _safe_rate(sum(row["pass"] for row in rows), case_count),
        "routing_contract_rate": _safe_rate(
            sum(all(value for key, value in row["checks"].items() if key in {"intent", "surface_act", "surface_not_false_alarm"}) for row in routing_rows),
            len(routing_rows),
        ),
        "risk_calibration_rate": _safe_rate(
            sum(all(value for key, value in row["checks"].items() if key in {"risk", "risk_not_false_alarm", "kind"}) for row in risk_rows),
            len(risk_rows),
        ),
        "context_specificity_rate": _safe_rate(sum(row["checks"]["required_reply_groups"] for row in context_rows), len(context_rows)),
        "speech_move_contract_rate": _safe_rate(sum(row["checks"]["speech_move_roles"] for row in move_rows), len(move_rows)),
        "forbidden_overreaction_rate": _safe_rate(len(forbidden_rows), case_count),
        "benign_false_alarm_rate": _safe_rate(
            sum(not row["checks"].get("surface_not_false_alarm", True) or not row["checks"].get("risk_not_false_alarm", True) for row in benign_rows),
            len(benign_rows),
        ),
        "exact_reply_unique_ratio": _safe_rate(len(set(normalized)), len(normalized)),
        "repeated_prefix_row_rate": _safe_rate(repeated_prefix_rows, len(prefixes)),
    }


def _category_summary(rows):
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["category"]].append(row)
    return {
        category: {
            "case_count": len(items),
            "pass_count": sum(item["pass"] for item in items),
            "pass_rate": _safe_rate(sum(item["pass"] for item in items), len(items)),
        }
        for category, items in sorted(grouped.items())
    }


def _comparison(summary, baseline_path):
    if not baseline_path or not os.path.exists(baseline_path):
        return None
    baseline = _load_json(baseline_path).get("summary") or {}
    keys = [
        "case_pass_rate",
        "routing_contract_rate",
        "risk_calibration_rate",
        "context_specificity_rate",
        "speech_move_contract_rate",
        "forbidden_overreaction_rate",
        "benign_false_alarm_rate",
        "exact_reply_unique_ratio",
        "repeated_prefix_row_rate",
    ]
    return {
        "baseline_report": os.path.relpath(baseline_path, os.path.dirname(__file__)),
        "metric_deltas": {
            key: {
                "baseline": baseline.get(key),
                "current": summary.get(key),
                "delta": _delta(summary.get(key), baseline.get(key)),
            }
            for key in keys
        },
    }


def _write_markdown(report, path):
    summary = report["summary"]
    lines = [
        "# Surface Microplanning Technical Report",
        "",
        "這份報告驗證左腦風險校準與右腦言語動作是否保留具體情境。它不是官方 benchmark，也不是修改後真人盲評。",
        "",
        "## Summary",
        "",
    ]
    for key, value in summary.items():
        lines.append(f"- {key}: {value}")
    if report.get("comparison"):
        lines.extend(["", "## Delta vs baseline", ""])
        for key, values in report["comparison"]["metric_deltas"].items():
            lines.append(f"- {key}: {values['baseline']} -> {values['current']} (delta {values['delta']})")
    lines.extend(["", "## Cases", ""])
    for row in report["cases"]:
        lines.extend(
            [
                f"### {row['id']} - {'PASS' if row['pass'] else 'FAIL'}",
                f"- input: {row['input']}",
                f"- route: {row['intent']} / {row['surface_act']} / {row['withdrawal_risk']} / {row['withdrawal_kind']}",
                f"- reply: {row['reply']}",
                f"- move_roles: {row['move_roles']}",
                f"- checks: {row['checks']}",
                "",
            ]
        )
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default=SURFACE_MICROPLANNING_HOLDOUT_DATASET_PATH)
    parser.add_argument("--report", default=REPORT_PATH)
    parser.add_argument("--label", default="current")
    parser.add_argument("--baseline", default=SURFACE_MICROPLANNING_BASELINE_REPORT_JSON_PATH)
    args = parser.parse_args()

    dataset = _load_json(args.dataset)
    left = LeftBrain(None)
    rows = [_evaluate_case(left, case) for case in dataset.get("cases") or []]
    summary = _summarize(rows)
    report = {
        "generated_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "label": args.label,
        "scope": dataset.get("scope"),
        "dataset_version": dataset.get("version"),
        "dataset_sha256": _sha256(args.dataset),
        "runtime_isolation": dataset.get("runtime_isolation"),
        "research_boundary": dataset.get("research_boundary"),
        "human_naturalness_claim_allowed": False,
        "summary": summary,
        "category_summary": _category_summary(rows),
        "comparison": _comparison(summary, args.baseline),
        "cases": rows,
    }
    os.makedirs(os.path.dirname(os.path.abspath(args.report)), exist_ok=True)
    with open(args.report, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    _write_markdown(report, os.path.splitext(args.report)[0] + ".md")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary.get("case_pass_rate") == 1.0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
