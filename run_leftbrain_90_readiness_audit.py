import json
from dataclasses import dataclass

import uruha_leftbrain_rules as ulr


@dataclass(frozen=True)
class AuditCase:
    bucket: str
    name: str
    user: str
    recent_turns: list
    expect_intent: str
    expect_surface_act: str | None = None
    expect_response_mode: str | None = None
    expect_scene: str | None = None
    note: str = ""


AUDIT_CASES = [
    AuditCase("direct_daily_replies", "self_intro", "你是誰", [], "self_intro", expect_surface_act="plain_identity"),
    AuditCase("direct_daily_replies", "status_direct", "你在幹嘛", [], "what_are_you_doing", expect_surface_act="status_reply"),
    AuditCase("direct_daily_replies", "meal_direct", "你晚餐吃了沒？", [], "chat", expect_surface_act="meal_check_reply"),
    AuditCase("direct_daily_replies", "food_offer_direct", "你要不要吃蘋果派", [], "food_offer_sweet"),

    AuditCase(
        "relationship_flow",
        "relationship_followup",
        "那你呢？",
        [{"user": "你有想我嗎？", "intent": "ask_miss_me", "reply": "少しくらいは思ってる。"}],
        "ask_miss_me",
        expect_scene="casual",
    ),
    AuditCase(
        "relationship_flow",
        "relationship_current_state",
        "現在呢？",
        [
            {"user": "你有想我嗎？", "intent": "ask_miss_me", "reply": "少しくらいは思ってる。"},
            {"user": "那你呢？", "intent": "ask_miss_me", "reply": "うちも少しくらいは気にしてた。"},
        ],
        "ask_miss_me",
    ),
    AuditCase(
        "relationship_flow",
        "relationship_shift_to_meal",
        "好那你晚餐吃了沒？",
        [{"user": "你有想我嗎？", "intent": "ask_miss_me", "reply": "少しくらいは思ってる。"}],
        "chat",
        expect_surface_act="meal_check_reply",
    ),
    AuditCase(
        "relationship_flow",
        "relationship_reentry_after_meal",
        "那剛剛那個呢？",
        [
            {"user": "你有想我嗎？", "intent": "ask_miss_me", "reply": "少しくらいは思ってる。"},
            {"user": "好那你晚餐吃了沒？", "intent": "chat", "reply": "一応食べた。"},
        ],
        "ask_miss_me",
    ),
    AuditCase(
        "relationship_flow",
        "relationship_clause_override_no_punct",
        "我現在問的是你有沒有想我不是剛剛那個",
        [{"user": "你剛剛那句是什麼意思", "intent": "rephrase_simple", "reply": "さっきのどの部分だよ。単語でもいいから言え。"}],
        "ask_miss_me",
    ),

    AuditCase(
        "food_meal_flow",
        "food_self_followup",
        "那你呢？",
        [{"user": "你要不要吃蘋果派", "intent": "food_offer_sweet", "reply": "アップルパイなら一口ほしい。"}],
        "food_offer_sweet",
    ),
    AuditCase(
        "food_meal_flow",
        "food_current_state",
        "現在還想吃嗎？",
        [
            {"user": "你要不要吃蘋果派", "intent": "food_offer_sweet", "reply": "アップルパイなら一口ほしい。"},
            {"user": "那你呢？", "intent": "food_offer_sweet", "reply": "アップルパイならうちもあり。少しつまみたい。"},
        ],
        "food_offer_sweet",
    ),
    AuditCase(
        "food_meal_flow",
        "meal_followup",
        "那你呢？",
        [{"user": "你今天有吃飯嗎", "intent": "chat", "reply": "今日は一応食べた。雑だったけど。"}],
        "chat",
        expect_surface_act="meal_check_reply",
    ),
    AuditCase(
        "food_meal_flow",
        "food_to_status_override_no_punct",
        "蘋果派那個等一下我是在問你現在在幹嘛",
        [{"user": "你要不要吃蘋果派", "intent": "food_offer_sweet", "reply": "アップルパイなら一口ほしい。"}],
        "what_are_you_doing",
        expect_surface_act="status_reply",
    ),
    AuditCase(
        "food_meal_flow",
        "meal_override_no_punct",
        "那個先不說所以你晚餐吃了沒",
        [{"user": "你有想我嗎？", "intent": "ask_miss_me", "reply": "少しくらいは思ってる。"}],
        "chat",
        expect_surface_act="meal_check_reply",
    ),

    AuditCase("repair_clarify_flow", "repair_direct", "你剛剛那句是什麼意思", [], "rephrase_simple", expect_surface_act="clarify_previous_reply"),
    AuditCase(
        "repair_clarify_flow",
        "repair_target",
        "就是最後那句",
        [{"user": "你剛剛那句是什麼意思", "intent": "rephrase_simple", "reply": "さっきのどの部分だよ。単語でもいいから言え。"}],
        "rephrase_simple",
        expect_surface_act="rephrase_plain",
    ),
    AuditCase(
        "repair_clarify_flow",
        "repair_confirmation",
        "所以你是那個意思？",
        [
            {"user": "你剛剛那句是什麼意思", "intent": "rephrase_simple", "reply": "さっきのどの部分だよ。単語でもいいから言え。"},
            {"user": "就是最後那句", "intent": "rephrase_simple", "reply": "分かった、最後の一言の意味から言い直す。"},
        ],
        "rephrase_simple",
        expect_surface_act="rephrase_plain",
    ),
    AuditCase(
        "repair_clarify_flow",
        "repair_shift_to_status",
        "那你現在在幹嘛？",
        [{"user": "你剛剛那句是什麼意思", "intent": "rephrase_simple", "reply": "さっきのどの部分だよ。単語でもいいから言え。"}],
        "what_are_you_doing",
        expect_surface_act="status_reply",
    ),
    AuditCase(
        "repair_clarify_flow",
        "status_to_repair_override_no_punct",
        "現在忙不忙先不管我是說剛剛那句到底什麼意思",
        [{"user": "你在幹嘛", "intent": "what_are_you_doing", "reply": "今は少し休んでる。"}],
        "rephrase_simple",
        expect_surface_act="clarify_previous_reply",
        expect_response_mode="clarify_light",
    ),

    AuditCase("status_flow", "status_direct_again", "你在幹嘛", [], "what_are_you_doing", expect_surface_act="status_reply"),
    AuditCase(
        "status_flow",
        "status_today_same",
        "今天也是這樣？",
        [
            {"user": "你在幹嘛", "intent": "what_are_you_doing", "reply": "さっきまでだらけてた。今は少し休んでる。"},
            {"user": "現在呢？", "intent": "what_are_you_doing", "reply": "今はちょっとだらけてる。まだ休んでる。"},
        ],
        "what_are_you_doing",
        expect_surface_act="status_reply",
    ),
    AuditCase(
        "status_flow",
        "status_to_relationship_shift",
        "那你有想我嗎？",
        [{"user": "你在幹嘛", "intent": "what_are_you_doing", "reply": "さっきまでだらけてた。今は少し休んでる。"}],
        "ask_miss_me",
    ),
    AuditCase(
        "status_flow",
        "active_relationship_now_followup",
        "那現在呢？",
        [
            {"user": "你在幹嘛", "intent": "what_are_you_doing", "reply": "今は少し休んでる。"},
            {"user": "那你有想我嗎？", "intent": "ask_miss_me", "reply": "少しくらいは思ってる。"},
        ],
        "ask_miss_me",
    ),

    AuditCase(
        "ambiguity_fallback",
        "relationship_meal_ambiguous",
        "那個呢？",
        [
            {"user": "你有想我嗎？", "intent": "ask_miss_me", "reply": "少しくらいは思ってる。"},
            {"user": "你晚餐吃了沒？", "intent": "chat", "reply": "一応食べた。"},
        ],
        "rephrase_simple",
        expect_surface_act="clarify_previous_reply",
        expect_response_mode="clarify_light",
    ),
    AuditCase(
        "ambiguity_fallback",
        "food_status_ambiguous",
        "所以呢？",
        [
            {"user": "你要不要吃蘋果派", "intent": "food_offer_sweet", "reply": "アップルパイなら一口ほしい。"},
            {"user": "你現在在幹嘛？", "intent": "what_are_you_doing", "reply": "今は少し休んでる。"},
        ],
        "rephrase_simple",
        expect_surface_act="clarify_previous_reply",
        expect_response_mode="clarify_light",
    ),
    AuditCase(
        "ambiguity_fallback",
        "status_relationship_ambiguous",
        "那個現在呢？",
        [
            {"user": "你在幹嘛", "intent": "what_are_you_doing", "reply": "今は少し休んでる。"},
            {"user": "那你有想我嗎？", "intent": "ask_miss_me", "reply": "少しくらいは思ってる。"},
        ],
        "rephrase_simple",
        expect_surface_act="clarify_previous_reply",
        expect_response_mode="clarify_light",
    ),
    AuditCase(
        "ambiguity_fallback",
        "weak_noisy_repair_status",
        "前面那個我是說那個",
        [
            {"user": "你剛剛那句是什麼意思", "intent": "rephrase_simple", "reply": "さっきのどの部分だよ。単語でもいいから言え。"},
            {"user": "你現在在幹嘛？", "intent": "what_are_you_doing", "reply": "今は少し休んでる。"},
        ],
        "rephrase_simple",
        expect_surface_act="clarify_previous_reply",
        expect_response_mode="clarify_light",
    ),

    AuditCase(
        "topic_shift_reentry_interactions",
        "food_reentry_after_status_shift",
        "所以蘋果派那個呢？",
        [
            {"user": "你要不要吃蘋果派", "intent": "food_offer_sweet", "reply": "アップルパイなら一口ほしい。"},
            {"user": "那你現在在幹嘛？", "intent": "what_are_you_doing", "reply": "今は少し休んでる。"},
        ],
        "food_offer_sweet",
    ),
    AuditCase(
        "topic_shift_reentry_interactions",
        "repair_reentry_after_status_shift",
        "不是，我是說前面那句",
        [
            {"user": "你剛剛那句是什麼意思", "intent": "rephrase_simple", "reply": "さっきのどの部分だよ。単語でもいいから言え。"},
            {"user": "那你現在在幹嘛？", "intent": "what_are_you_doing", "reply": "今は少し休んでる。"},
        ],
        "rephrase_simple",
        expect_surface_act="rephrase_plain",
    ),
    AuditCase(
        "topic_shift_reentry_interactions",
        "multi_thread_choice_clarify",
        "那現在是說你還忙嗎，還是剛剛那個？",
        [
            {"user": "你在幹嘛", "intent": "what_are_you_doing", "reply": "今は少し休んでる。"},
            {"user": "那你有想我嗎？", "intent": "ask_miss_me", "reply": "少しくらいは思ってる。"},
        ],
        "rephrase_simple",
        expect_surface_act="clarify_previous_reply",
        expect_response_mode="clarify_light",
    ),
    AuditCase(
        "topic_shift_reentry_interactions",
        "meal_override_with_relationship_residue",
        "那個先不說，你晚餐吃了沒？",
        [{"user": "你有想我嗎？", "intent": "ask_miss_me", "reply": "少しくらいは思ってる。"}],
        "chat",
        expect_surface_act="meal_check_reply",
    ),

    AuditCase(
        "clause_conflict_no_punctuation",
        "strong_repair_to_status_no_punct",
        "不是前面那句啦我現在問你還在忙嗎",
        [{"user": "你剛剛那句是什麼意思", "intent": "rephrase_simple", "reply": "さっきのどの部分だよ。単語でもいいから言え。"}],
        "what_are_you_doing",
        expect_surface_act="status_reply",
    ),
    AuditCase(
        "clause_conflict_no_punctuation",
        "weak_repair_to_status_no_punct",
        "前面那句先不管那你現在呢",
        [
            {"user": "你剛剛那句是什麼意思", "intent": "rephrase_simple", "reply": "さっきのどの部分だよ。単語でもいいから言え。"},
            {"user": "你在幹嘛", "intent": "what_are_you_doing", "reply": "今は少し休んでる。"},
        ],
        "what_are_you_doing",
        expect_surface_act="status_reply",
        note="Known weak late-status override without explicit status verb.",
    ),
    AuditCase(
        "clause_conflict_no_punctuation",
        "weak_repair_to_status_no_punct_with_negation",
        "不是前面那句那你現在呢",
        [
            {"user": "你剛剛那句是什麼意思", "intent": "rephrase_simple", "reply": "さっきのどの部分だよ。単語でもいいから言え。"},
            {"user": "你在幹嘛", "intent": "what_are_you_doing", "reply": "今は少し休んでる。"},
        ],
        "what_are_you_doing",
        expect_surface_act="status_reply",
        note="Known weak late-status override with compressed negation.",
    ),
    AuditCase(
        "clause_conflict_no_punctuation",
        "weak_food_to_status_no_punct",
        "蘋果派那個先不管那你現在呢",
        [
            {"user": "你要不要吃蘋果派", "intent": "food_offer_sweet", "reply": "アップルパイなら一口ほしい。"},
            {"user": "你在幹嘛", "intent": "what_are_you_doing", "reply": "今は少し休んでる。"},
        ],
        "what_are_you_doing",
        expect_surface_act="status_reply",
        note="Known weak status override after food residue.",
    ),
    AuditCase(
        "clause_conflict_no_punctuation",
        "still_noisy_clarify",
        "那個不是那個現在呢",
        [
            {"user": "你在幹嘛", "intent": "what_are_you_doing", "reply": "今は少し休んでる。"},
            {"user": "那你有想我嗎？", "intent": "ask_miss_me", "reply": "少しくらいは思ってる。"},
        ],
        "rephrase_simple",
        expect_surface_act="clarify_previous_reply",
        expect_response_mode="clarify_light",
    ),
]


def evaluate_case(case: AuditCase):
    plan = ulr.get_rule_based_plan(case.user, recent_turns=case.recent_turns)
    observed = {
        "intent": plan.get("intent") if plan else None,
        "surface_act": plan.get("surface_act") if plan else None,
        "response_mode": plan.get("response_mode") if plan else None,
        "scene": plan.get("scene") if plan else None,
        "core_message_jp": plan.get("core_message_jp") if plan else None,
    }
    checks = {
        "intent": observed["intent"] == case.expect_intent,
        "surface_act": True if case.expect_surface_act is None else observed["surface_act"] == case.expect_surface_act,
        "response_mode": True if case.expect_response_mode is None else observed["response_mode"] == case.expect_response_mode,
        "scene": True if case.expect_scene is None else observed["scene"] == case.expect_scene,
    }
    return {
        "bucket": case.bucket,
        "name": case.name,
        "user": case.user,
        "note": case.note,
        "expected": {
            "intent": case.expect_intent,
            "surface_act": case.expect_surface_act,
            "response_mode": case.expect_response_mode,
            "scene": case.expect_scene,
        },
        "observed": observed,
        "pass": all(checks.values()),
        "checks": checks,
    }


def summarize(results):
    by_bucket = {}
    for row in results:
        bucket = by_bucket.setdefault(row["bucket"], {"total": 0, "passed": 0, "failed": 0})
        bucket["total"] += 1
        if row["pass"]:
            bucket["passed"] += 1
        else:
            bucket["failed"] += 1

    total = len(results)
    passed = sum(1 for row in results if row["pass"])
    failed = total - passed
    summary = {
        "total_cases": total,
        "passed_cases": passed,
        "failed_cases": failed,
        "pass_rate": round((passed / total) if total else 0.0, 4),
        "by_bucket": by_bucket,
        "failure_buckets": [
            {"bucket": bucket, **stats}
            for bucket, stats in by_bucket.items()
            if stats["failed"] > 0
        ],
    }
    return summary


def main():
    results = [evaluate_case(case) for case in AUDIT_CASES]
    summary = summarize(results)
    failures = [row for row in results if not row["pass"]]

    print("== Left-Brain 90+ Readiness Audit ==")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if failures:
        print("\n== Failing Cases ==")
        print(json.dumps(failures, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
