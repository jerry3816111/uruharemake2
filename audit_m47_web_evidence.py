"""Audit one isolated M47 Web log without upgrading route wins to action wins."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re


LABEL = "crosslingual_help_routing_m47"

EXPECTED = (
    ("本棚が散らかってる。今できる手順を一つだけ教えて。",
     "practical_help_authorized", "solve_regulation", True),
    ("抽屜裡有信件和收據，現在混在一起。給我一個現在能做的步驟。",
     "practical_help_authorized", "solve_regulation", True),
    ("方法はいらない。ただ聞いてほしい。",
     "practical_help_forbidden", "listen_presence", False),
    ("不要給我方法，我只是在抱怨。",
     "practical_help_forbidden", None, False),
    ("The report is blank. Give me one practical step.",
     "practical_help_authorized", "solve_regulation", True),
    ("我昨天看過這個方法，但還沒決定。",
     "no_explicit_help_route", None, False),
)


def digest(text):
    return hashlib.sha256(str(text or "").encode("utf-8")).hexdigest()[:16]


def japanese_visible(text):
    return bool(re.search(r"[ぁ-ヿ]", str(text or ""))
                and not re.search(r"[A-Za-z]{3,}", str(text or "")))


def audit(path):
    rows = [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines()
            if line.strip()]
    turns = []
    for index, expected in enumerate(EXPECTED):
        text, expected_status, expected_policy, expected_m46 = expected
        row = rows[index] if index < len(rows) else {}
        logic = row.get("logic") or {}
        route = logic.get(LABEL) or {}
        delivery = logic.get("actionable_help_delivery_m45") or {}
        m46 = delivery.get("goal_progress_delivery_m46") or {}
        desired = route.get("desired_response_span") or {}
        start, end = desired.get("start"), desired.get("end")
        geometry_ok = bool(
            isinstance(start, int) and isinstance(end, int)
            and 0 <= start < end <= len(text)
            and digest(text[start:end]) == desired.get("span_digest")
        ) if route.get("detected") else desired in ({}, None)
        actual_policy = logic.get("desired_response_policy_m18")
        expected_policy_ok = (
            actual_policy == expected_policy if expected_policy
            else actual_policy != "solve_regulation"
        )
        m46_ok = bool(route.get("m46_did_intervene")) == expected_m46
        no_method_surface_respected = None
        if expected_status == "practical_help_forbidden":
            reply = str(row.get("assistant_reply") or "")
            no_method_surface_respected = not bool(
                re.search(r"(?:方法と.*聞いて|方法.*どっち|どっち.*方法)", reply)
            )
        turns.append({
            "turn_index": row.get("turn_index"),
            "input_digest": digest(text),
            "input_matches_script": row.get("user_text") == text,
            "route_status": route.get("status"),
            "route_status_pass": route.get("status") == expected_status,
            "actual_policy": actual_policy,
            "policy_pass": expected_policy_ok,
            "route_consistent": route.get("route_consistent") is True,
            "geometry_pass": geometry_ok,
            "m46_should_intervene": route.get("m46_should_intervene"),
            "m46_did_intervene": route.get("m46_did_intervene"),
            "m46_intervention_pass": m46_ok,
            "m46_delivery_status": delivery.get("status") or "not_applicable",
            "m46_goal_progress_status": m46.get("status") or "not_applicable",
            "action_delivered": delivery.get("delivered") is True,
            "visible_japanese_pass": japanese_visible(row.get("assistant_reply")),
            "no_method_surface_respected": no_method_surface_respected,
            "raw_dialogue_duplicated_in_route": text in json.dumps(route, ensure_ascii=False),
            "long_term_memory_write": route.get("long_term_memory_write"),
        })

    route_pass = [
        t["input_matches_script"] and t["route_status_pass"] and t["policy_pass"]
        and t["route_consistent"] and t["geometry_pass"] and t["m46_intervention_pass"]
        and not t["raw_dialogue_duplicated_in_route"] and t["long_term_memory_write"] is False
        for t in turns
    ]
    positive = [t for t in turns if t["m46_should_intervene"]]
    negative = [t for t in turns if not t["m46_should_intervene"]]
    forbidden = [t for t in turns if t["route_status"] == "practical_help_forbidden"]
    return {
        "schema": "uruha_m47_isolated_web_audit",
        "source_log": str(Path(path)),
        "session_ids": sorted({row.get("session_id") for row in rows if row.get("session_id")}),
        "observed_turns": len(rows),
        "expected_turns": len(EXPECTED),
        "route_pass_count": sum(route_pass),
        "route_total": len(EXPECTED),
        "route_gate_passed": len(rows) == len(EXPECTED) and all(route_pass),
        "visible_japanese_count": sum(t["visible_japanese_pass"] for t in turns),
        "positive_m46_intervention_count": sum(bool(t["m46_did_intervene"]) for t in positive),
        "positive_total": len(positive),
        "nonpositive_m46_avoidance_count": sum(not bool(t["m46_did_intervene"]) for t in negative),
        "nonpositive_total": len(negative),
        "action_delivery_count": sum(t["action_delivered"] for t in positive),
        "action_delivery_total": len(positive),
        "forbidden_surface_respected_count": sum(t["no_method_surface_respected"] is True for t in forbidden),
        "forbidden_surface_total": len(forbidden),
        "turns": turns,
        "claim_boundary": (
            "scripted isolated Safari route evidence; action delivery, holdout generalisation, "
            "latency, and human felt-understanding are separate gates"
        ),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("log")
    parser.add_argument("--output")
    args = parser.parse_args()
    result = audit(args.log)
    payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(payload, encoding="utf-8")
    print(payload, end="")
    raise SystemExit(0 if result["route_gate_passed"] else 1)


if __name__ == "__main__":
    main()
