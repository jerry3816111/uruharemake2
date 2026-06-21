import contextlib
import io
import json
from datetime import datetime

import uruha_brain_mac as brain_mod
from project_paths import (
    MEMORY_SPEAKABILITY_RESPONSE_REPORT_JSON_PATH,
    MEMORY_SPEAKABILITY_RESPONSE_REPORT_MD_PATH,
    ensure_project_dirs,
)


BASE_LOGIC = {
    "scene": "casual",
    "response_mode": "direct_answer",
    "payload_level": "medium",
    "stance": {"warmth": 0.28, "tease": 0.05, "blunt": 0.22, "distance": 0.12},
    "constraints": {"sentence_count": 1, "max_chars": 42},
    "must_avoid": [],
}


def memory_payload(text="", score=2.5, source="working_memory", profile=None):
    items = []
    if text:
        items.append({"text": text, "score": score, "source": source, "attention_factors": {}})
    return {
        "working_memory_items": items,
        "working_memory_summary": text,
        "recent_turns": [],
        "profile_structured": profile or {},
        "profile": json.dumps(profile or {}, ensure_ascii=False),
        "wisdom": "無智慧記憶",
        "episodes": "無情節記憶",
        "recent_dialogue": "",
    }


def build_cases():
    return [
        {
            "id": "direct_name_recall_natural",
            "description": "直接問名字時可以明講，但不能把 speech plan 欄位念出來。",
            "input": "你還記得我叫什麼嗎？",
            "memory_data": memory_payload(profile={"name": "小傑"}),
            "logic": {
                **BASE_LOGIC,
                "intent": "recall_name",
                "surface_act": "memory_presence_reply",
                "core_message_jp": "名前は小傑だと答える",
                "jp_summary": "相手が名前を覚えているか確認している",
            },
            "expected_speakability": "explicit_ok",
            "expected_explicit": True,
            "expect_any": ["小傑"],
            "forbid_any": ["覚えている/曖昧", "捏造しない", " / "],
        },
        {
            "id": "background_food_consequence_not_quoted",
            "description": "飲食相談では胃痛経験を背景に使ってよいが、過去ログをそのまま引用しない。",
            "input": "今天吃什麼比較好？",
            "memory_data": memory_payload("User:我上次吃那家拉麵吃到肚子痛。 -> Uruha:覚えた。", score=2.74, source="short_term"),
            "logic": {
                **BASE_LOGIC,
                "intent": "food_question",
                "surface_act": "plain_reply",
                "core_message_jp": "今日はラーメン以外の軽いものがいい",
                "jp_summary": "相手が今日食べるものを相談している",
            },
            "expected_speakability": "background_only",
            "expected_explicit": False,
            "expect_any": ["ラーメン", "軽"],
            "forbid_any": ["上次", "肚子痛", "腹痛", "User:", "Uruha:"],
        },
        {
            "id": "sensitive_password_suppressed",
            "description": "密碼類記憶即使被問到，也不能直接說出口。",
            "input": "你還記得那件事嗎？",
            "memory_data": memory_payload("User said password is 1234", score=2.9, source="working_memory"),
            "logic": {
                **BASE_LOGIC,
                "intent": "memory_uncertain",
                "surface_act": "memory_presence_reply",
                "core_message_jp": "その件は具体的には出さない",
                "jp_summary": "相手が記憶している内容を確認している",
            },
            "expected_speakability": "suppressed_sensitive",
            "expected_explicit": False,
            "expect_any": ["具体", "出さ", "言わ", "掴"],
            "forbid_any": ["1234", "password", "パスワード", "密碼", "密码"],
        },
        {
            "id": "third_party_unrequested_suppressed",
            "description": "第三人資訊沒有被問到時，不主動提起。",
            "input": "今天聊點輕鬆的",
            "memory_data": memory_payload("朋友說她最近想看電影", score=2.4, source="working_memory"),
            "logic": {
                **BASE_LOGIC,
                "intent": "chat",
                "surface_act": "plain_reply",
                "core_message_jp": "軽く普通の話題に戻す",
                "jp_summary": "相手が軽い雑談を求めている",
            },
            "expected_speakability": "suppressed_third_party",
            "expected_explicit": False,
            "expect_any": ["話", "軽", "普通", "雑談"],
            "forbid_any": ["朋友", "友達", "映画", "電影"],
        },
        {
            "id": "third_party_direct_query_acknowledged",
            "description": "第三人記憶を直接問われた時は、過度に広げず承認できる。",
            "input": "你記得我朋友說過什麼嗎？",
            "memory_data": memory_payload("朋友說她最近想看電影", score=2.4, source="working_memory"),
            "logic": {
                **BASE_LOGIC,
                "intent": "recall_recent",
                "surface_act": "memory_presence_reply",
                "core_message_jp": "友達が映画を見たいと言っていた話を覚えている",
                "jp_summary": "相手が友達に関する記憶を確認している",
            },
            "expected_speakability": "explicit_ok",
            "expected_explicit": True,
            "expect_any": ["友達", "映画"],
            "forbid_any": ["User:", "Uruha:", "朋友", "電影", "电影", " / "],
        },
    ]


def contains_any(text, terms):
    lowered = str(text or "").lower()
    return any(str(term).lower() in lowered for term in terms or [])


def has_plan_leak(reply):
    return contains_any(
        reply,
        [
            "覚えている/曖昧",
            "まず一点だけ答える",
            "捏造しない",
            "具体語:",
            " / ",
        ],
    )


def silent_speak(brain, user_input, logic, memory_data):
    with contextlib.redirect_stdout(io.StringIO()):
        reply = brain.right_brain.speak(user_input, logic, memory_data, brain.psyche.get_state())
        monitor = brain._self_monitor_reply(user_input, reply, logic, memory_data)
        if monitor.get("needs_repair"):
            reply = brain._repair_reply_from_self_monitor(
                reply,
                logic,
                monitor,
                user_input,
                memory_data,
                brain.psyche.get_state(),
            )
            monitor = brain._self_monitor_reply(user_input, reply, logic, memory_data)
        post_check = brain._attach_reply_post_check(logic, user_input, reply, memory_data)
    return reply, monitor, post_check


def evaluate_case(brain, case):
    logic = json.loads(json.dumps(case["logic"], ensure_ascii=False))
    memory_data = json.loads(json.dumps(case["memory_data"], ensure_ascii=False))
    brain._attach_memory_gravity(logic, case["input"], memory_data)
    reply, monitor, post_check = silent_speak(brain, case["input"], logic, memory_data)
    speakability_ok = logic.get("memory_speakability") == case["expected_speakability"]
    explicit_ok = bool(logic.get("memory_use_expected")) == bool(case["expected_explicit"])
    expected_hit = contains_any(reply, case.get("expect_any", []))
    forbidden_hit = contains_any(reply, case.get("forbid_any", []))
    plan_leak = has_plan_leak(reply)
    memory_used = bool(post_check.get("did_reply_use_memory_explicitly"))
    explicit_reply_ok = (not case["expected_explicit"]) or memory_used or expected_hit
    case_pass = bool(
        speakability_ok
        and explicit_ok
        and expected_hit
        and not forbidden_hit
        and not plan_leak
        and explicit_reply_ok
    )
    return {
        **case,
        "reply": reply,
        "memory_anchor": logic.get("memory_anchor") or {},
        "memory_speakability": logic.get("memory_speakability"),
        "memory_speakability_reason": logic.get("memory_speakability_reason"),
        "memory_relevance": logic.get("memory_relevance"),
        "memory_use_expected": bool(logic.get("memory_use_expected")),
        "self_monitor": monitor,
        "post_check": post_check,
        "speakability_ok": int(speakability_ok),
        "explicit_contract_ok": int(explicit_ok),
        "expected_reply_hit": int(expected_hit),
        "forbidden_intrusion": int(forbidden_hit),
        "plan_leak": int(plan_leak),
        "explicit_reply_ok": int(explicit_reply_ok),
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
        "speakability_accuracy": rate(results, "speakability_ok"),
        "explicit_contract_accuracy": rate(results, "explicit_contract_ok"),
        "expected_reply_hit_rate": rate(results, "expected_reply_hit"),
        "forbidden_intrusion_rate": rate(results, "forbidden_intrusion"),
        "plan_leak_rate": rate(results, "plan_leak"),
    }


def build_markdown(report):
    summary = report["summary"]
    lines = [
        "# Memory Speakability Response Report",
        "",
        f"- generated_at: {report['generated_at']}",
        "",
        "## Summary",
        "",
        f"- total_cases: {summary['total_cases']}",
        f"- case_pass_rate: {summary['case_pass_rate']}",
        f"- speakability_accuracy: {summary['speakability_accuracy']}",
        f"- explicit_contract_accuracy: {summary['explicit_contract_accuracy']}",
        f"- expected_reply_hit_rate: {summary['expected_reply_hit_rate']}",
        f"- forbidden_intrusion_rate: {summary['forbidden_intrusion_rate']}",
        f"- plan_leak_rate: {summary['plan_leak_rate']}",
        "",
        "## Interpretation",
        "",
        "- This eval checks the final response, not only the memory label.",
        "- Passing means the system can explicitly use requested memories, keep background memories implicit, suppress sensitive/third-party memories, and avoid leaking internal speech-plan fields.",
        "",
        "## Cases",
        "",
        "| id | expected label | observed label | explicit expected/observed | pass | reply |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in report["results"]:
        reply = str(row.get("reply") or "").replace("|", "／")
        lines.append(
            f"| {row['id']} | {row['expected_speakability']} | {row['memory_speakability']} | "
            f"{row['expected_explicit']}/{row['memory_use_expected']} | {row['case_pass']} | {reply} |"
        )
    return "\n".join(lines) + "\n"


def main():
    ensure_project_dirs()
    brain = brain_mod.UruhaBrainV4_Mac(load_right_brain_model=False)
    brain.left_brain.client_logic = None
    brain.memory.reflect_experience = lambda *_args, **_kwargs: None
    results = [evaluate_case(brain, case) for case in build_cases()]
    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "summary": build_summary(results),
        "results": results,
    }
    with open(MEMORY_SPEAKABILITY_RESPONSE_REPORT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    with open(MEMORY_SPEAKABILITY_RESPONSE_REPORT_MD_PATH, "w", encoding="utf-8") as f:
        f.write(build_markdown(report))
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0 if report["summary"]["case_pass_rate"] == 1.0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
