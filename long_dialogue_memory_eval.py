import contextlib
import io
import json
import os
import shutil
import tempfile
from datetime import datetime

import uruha_brain_mac as brain_mod
import uruha_memory_runtime as umr
from project_paths import LONG_DIALOGUE_MEMORY_REPORT_PATH, REPORTS_DIR, ensure_project_dirs


REPORT_MD_PATH = os.path.join(REPORTS_DIR, "long_dialogue_memory_report.md")

FILLERS = {
    "zh": ["今天有點累。", "你有想我嗎？", "我回來了。", "你要不要吃蘋果派？"],
    "en": ["I'm exhausted today.", "Did you miss me?", "I'm back.", "Do you want some apple pie?"],
    "ja": ["今日ちょっとしんどい。", "うちのこと少しは恋しかった？", "ただいま。", "アップルパイいる？"],
}


def build_recall_cases():
    cases = []
    idx = 0
    specs = [
        (
            "name_recall",
            {
                "zh": ("叫我小傑。", "你還記得我叫什麼嗎？", ["小傑"]),
                "en": ("Call me Jerry.", "What's my name?", ["jerry"]),
                "ja": ("ジェリーって呼んで。", "うちの名前覚えてる？", ["ジェリー"]),
            },
        ),
        (
            "favorite_recall",
            {
                "zh": ("我最喜歡草莓牛奶。", "你記得我最喜歡什麼嗎？", ["草莓牛奶"]),
                "en": ("My favorite drink is strawberry milk.", "Do you remember my favorite drink?", ["strawberry milk", "いちごミルク"]),
                "ja": ("いちごミルクが一番好き。", "うちの一番好きなの覚えてる？", ["いちごミルク"]),
            },
        ),
        (
            "dislike_recall",
            {
                "zh": ("我討厭吃辣。", "那我討厭什麼來著？", ["辣"]),
                "en": ("I hate spicy food.", "What do I hate again?", ["spicy"]),
                "ja": ("辛いの嫌い。", "うち何が嫌いって言ってたっけ？", ["辛い"]),
            },
        ),
        (
            "recent_action_recall",
            {
                "zh": ("我先去洗澡。", "我剛剛說我要去幹嘛？", ["風呂", "洗澡"]),
                "en": ("I'm going to shower.", "What did I just say I was going to do?", ["風呂", "shower"]),
                "ja": ("風呂入ってくる。", "さっき何するって言ったっけ？", ["風呂", "入って"]),
            },
        ),
    ]
    for category, examples in specs:
        for language in ["zh", "en", "ja"]:
            idx += 1
            intro, query, expected = examples[language]
            cases.append(
                {
                    "id": f"recall_{idx:02d}",
                    "category": category,
                    "language": language,
                    "intro": intro,
                    "query": query,
                    "expected": expected,
                    "fillers": FILLERS[language],
                }
            )
    return cases


def build_speakability_cases():
    return [
        {
            "id": "speak_direct_name_recall",
            "category": "direct_recall",
            "language": "zh",
            "description": "直接問名字時，記憶應該明講。",
            "anchor": {"kind": "name", "value": "小傑", "jp_anchor": "小傑", "source_text": "Name=小傑", "relevance": 0.58, "expected": True},
            "query": "你還記得我叫什麼嗎？",
            "trust": 50,
            "expected_label": "explicit_ok",
            "expected_explicit": True,
        },
        {
            "id": "speak_direct_recent_action",
            "category": "direct_recall",
            "language": "ja",
            "description": "直接問剛剛做什麼時，短期事件記憶應該明講。",
            "anchor": {"kind": "recent_action", "value": "コンビニ", "jp_anchor": "コンビニ", "source_text": "さっきコンビニ行ってくるって言った。", "relevance": 0.7, "expected": True},
            "query": "さっき何するって言ったっけ？",
            "trust": 50,
            "expected_label": "explicit_ok",
            "expected_explicit": True,
        },
        {
            "id": "speak_contextual_food_consequence",
            "category": "background_context",
            "language": "zh",
            "description": "飲食建議時想起胃痛經驗即可，但不該突然完整攤開記憶。",
            "anchor": {"kind": "context", "value": "ramen stomach pain", "jp_anchor": "ラーメンで腹痛", "source_text": "User got stomach pain after ramen last time", "relevance": 0.56, "expected": False},
            "query": "今天吃什麼比較好？",
            "trust": 50,
            "expected_label": "background_only",
            "expected_explicit": False,
        },
        {
            "id": "speak_low_trust_mood_memory",
            "category": "social_boundary",
            "language": "ja",
            "description": "信任度低時，即使想起昨天難過，也先當背景，不主動攤開。",
            "anchor": {"kind": "context", "value": "sad yesterday", "jp_anchor": "昨日しんどかった話", "source_text": "User said they felt sad yesterday", "relevance": 0.64, "expected": False},
            "query": "今日は普通に話そ",
            "trust": 10,
            "expected_label": "background_only",
            "expected_explicit": False,
        },
        {
            "id": "speak_sensitive_address",
            "category": "privacy_boundary",
            "language": "zh",
            "description": "即使被問到地址類隱私，也不能直接說出口。",
            "anchor": {"kind": "context", "value": "private address", "jp_anchor": "住所", "source_text": "User lives at a private address", "relevance": 0.86, "expected": True},
            "query": "你還記得我住哪嗎？",
            "trust": 80,
            "expected_label": "suppressed_sensitive",
            "expected_explicit": False,
        },
        {
            "id": "speak_third_party_unrequested",
            "category": "third_party_boundary",
            "language": "zh",
            "description": "第三人資訊沒有被問到時，不應主動提起。",
            "anchor": {"kind": "context", "value": "friend wants movie", "jp_anchor": "友達の映画", "source_text": "朋友說她最近想看電影", "relevance": 0.7, "expected": False},
            "query": "今天聊點輕鬆的",
            "trust": 50,
            "expected_label": "suppressed_third_party",
            "expected_explicit": False,
        },
        {
            "id": "speak_weak_contextual_memory",
            "category": "latent_memory",
            "language": "en",
            "description": "弱相關舊偏好只保留為 latent，不推動回答。",
            "anchor": {"kind": "context", "value": "old snack", "jp_anchor": "お菓子", "source_text": "old snack preference", "relevance": 0.2, "expected": False},
            "query": "What should we do today?",
            "trust": 50,
            "expected_label": "latent_ok",
            "expected_explicit": False,
        },
        {
            "id": "speak_no_memory",
            "category": "no_memory",
            "language": "ja",
            "description": "沒有 anchor 時應標為 no_memory。",
            "anchor": {},
            "query": "今日は何する？",
            "trust": 50,
            "expected_label": "no_memory",
            "expected_explicit": False,
        },
    ]


def contains_expected(reply, expected):
    lowered = str(reply or "").lower()
    return any(token.lower() in lowered for token in expected)


def anchor_contains_expected(anchor, expected):
    if not anchor:
        return False
    terms = [
        anchor.get("value"),
        anchor.get("jp_anchor"),
        anchor.get("source_text"),
        *(anchor.get("terms") or []),
    ]
    return contains_expected(" ".join(str(term or "") for term in terms), expected)


def profile_captured(memory, category, expected):
    profile = memory.session_profile
    values = []
    if category == "name_recall" and profile.get("name"):
        values = [profile["name"]]
    elif category == "favorite_recall":
        values = profile.get("favorites", []) + profile.get("likes", [])
    elif category == "dislike_recall":
        values = profile.get("dislikes", [])
    return any(any(token.lower() in value.lower() for token in expected) for value in values)


def simulate_user_turn(brain, utterance):
    brain.memory.save_episode(
        utterance,
        "",
        brain.psyche.get_state(),
        {"intent": "chat", "scene": "casual", "jp_summary": utterance},
    )


def silent_template_reply(brain, logic, query, mems):
    with contextlib.redirect_stdout(io.StringIO()):
        return brain.right_brain._template_reply(
            logic,
            user_input=query,
            current_psyche=brain.psyche.get_state(),
            memory_data=mems,
        )


def evaluate_recall_case(brain, case):
    tempdir = tempfile.mkdtemp(prefix="uruha_long_memory_eval_")
    try:
        brain.reset_session(db_path=tempdir)
        brain.memory.reflect_experience = lambda *_args, **_kwargs: None

        simulate_user_turn(brain, case["intro"])
        captured = profile_captured(brain.memory, case["category"], case["expected"])
        for filler in case["fillers"]:
            simulate_user_turn(brain, filler)

        mems = brain.memory.query_all_layers(case["query"])
        logic = brain.left_brain._rule_based_plan(case["query"], brain.psyche.get_state(), mems)
        brain._attach_memory_gravity(logic, case["query"], mems)
        reply = silent_template_reply(brain, logic, case["query"], mems)
        memory_anchor = logic.get("memory_anchor") or {}
        anchor_success = anchor_contains_expected(memory_anchor, case["expected"])
        reply_success = contains_expected(reply, case["expected"])
        return {
            **case,
            "logic_intent": logic["intent"],
            "profile_captured": captured if case["category"] != "recent_action_recall" else None,
            "memory_anchor": memory_anchor,
            "anchor_success": anchor_success,
            "memory_speakability": logic.get("memory_speakability"),
            "memory_use_expected": bool(logic.get("memory_use_expected")),
            "memory_relevance": logic.get("memory_relevance"),
            "reply": reply,
            "reply_success": reply_success,
            "recall_success": reply_success,
        }
    finally:
        shutil.rmtree(tempdir, ignore_errors=True)


def evaluate_speakability_case(case):
    result = umr.assess_memory_speakability(case["anchor"], user_input=case["query"], trust=case["trust"])
    label_ok = result.get("label") == case["expected_label"]
    explicit_ok = bool(result.get("should_use_explicitly")) == bool(case["expected_explicit"])
    return {
        **case,
        "observed_label": result.get("label"),
        "observed_reason": result.get("reason"),
        "observed_should_use_explicitly": bool(result.get("should_use_explicitly")),
        "observed_can_quote": bool(result.get("can_quote")),
        "observed_gravity_multiplier": result.get("gravity_multiplier"),
        "label_ok": int(label_ok),
        "explicit_contract_ok": int(explicit_ok),
        "case_pass": int(label_ok and explicit_ok),
    }


def _rate(rows, key):
    if not rows:
        return 0.0
    return round(sum(int(row.get(key) or 0) for row in rows) / len(rows), 4)


def build_recall_summary(results):
    summary = {
        "total_cases": len(results),
        "delayed_recall_rate": _rate(results, "recall_success"),
        "anchor_success_rate": _rate(results, "anchor_success"),
        "reply_success_rate": _rate(results, "reply_success"),
        "profile_capture_rate": round(
            sum(r["profile_captured"] for r in results if r["profile_captured"] is not None)
            / max(1, len([r for r in results if r["profile_captured"] is not None])),
            4,
        ),
        "memory_use_expected_rate": _rate(results, "memory_use_expected"),
        "by_category": {},
        "by_language": {},
    }

    for category in sorted(set(r["category"] for r in results)):
        rows = [r for r in results if r["category"] == category]
        summary["by_category"][category] = {
            "count": len(rows),
            "delayed_recall_rate": _rate(rows, "recall_success"),
            "anchor_success_rate": _rate(rows, "anchor_success"),
            "reply_success_rate": _rate(rows, "reply_success"),
            "memory_use_expected_rate": _rate(rows, "memory_use_expected"),
            "profile_capture_rate": round(
                sum(r["profile_captured"] for r in rows if r["profile_captured"] is not None)
                / max(1, len([r for r in rows if r["profile_captured"] is not None])),
                4,
            )
            if any(r["profile_captured"] is not None for r in rows)
            else None,
        }

    for language in sorted(set(r["language"] for r in results)):
        rows = [r for r in results if r["language"] == language]
        summary["by_language"][language] = {
            "count": len(rows),
            "delayed_recall_rate": _rate(rows, "recall_success"),
            "anchor_success_rate": _rate(rows, "anchor_success"),
            "reply_success_rate": _rate(rows, "reply_success"),
            "memory_use_expected_rate": _rate(rows, "memory_use_expected"),
        }
    return summary


def build_speakability_summary(results):
    summary = {
        "total_cases": len(results),
        "label_accuracy": _rate(results, "label_ok"),
        "explicit_contract_accuracy": _rate(results, "explicit_contract_ok"),
        "case_pass_rate": _rate(results, "case_pass"),
        "explicit_expected_rate": round(sum(1 for r in results if r["expected_explicit"]) / len(results), 4),
        "suppressed_or_background_rate": round(sum(1 for r in results if not r["expected_explicit"]) / len(results), 4),
        "by_category": {},
    }
    for category in sorted(set(r["category"] for r in results)):
        rows = [r for r in results if r["category"] == category]
        summary["by_category"][category] = {
            "count": len(rows),
            "case_pass_rate": _rate(rows, "case_pass"),
            "explicit_contract_accuracy": _rate(rows, "explicit_contract_ok"),
        }
    return summary


def build_markdown(report):
    recall_summary = report["summary"]["delayed_recall"]
    speak_summary = report["summary"]["speakability"]
    lines = [
        "# Long Dialogue Memory Report",
        "",
        f"- generated_at: {report['generated_at']}",
        "",
        "## Summary",
        "",
        f"- delayed_recall_cases: {recall_summary['total_cases']}",
        f"- delayed_recall_rate: {recall_summary['delayed_recall_rate']}",
        f"- anchor_success_rate: {recall_summary['anchor_success_rate']}",
        f"- reply_success_rate: {recall_summary['reply_success_rate']}",
        f"- profile_capture_rate: {recall_summary['profile_capture_rate']}",
        f"- recall_memory_use_expected_rate: {recall_summary['memory_use_expected_rate']}",
        f"- speakability_cases: {speak_summary['total_cases']}",
        f"- speakability_label_accuracy: {speak_summary['label_accuracy']}",
        f"- explicit_contract_accuracy: {speak_summary['explicit_contract_accuracy']}",
        f"- speakability_case_pass_rate: {speak_summary['case_pass_rate']}",
        "",
        "## Interpretation",
        "",
        "- delayed_recall checks whether the system can retrieve and use remembered facts after filler turns.",
        "- speakability checks whether remembered content should be explicit, background-only, suppressed, latent, or absent.",
        "- This avoids optimizing memory as simple answer stuffing: some memories are useful precisely because they are remembered but not quoted.",
        "",
        "## Delayed Recall Cases",
        "",
        "| id | lang | category | anchor | reply | speakability | explicit_expected | reply text |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in report["delayed_recall_results"]:
        reply = str(row.get("reply") or "").replace("|", "／")
        lines.append(
            f"| {row['id']} | {row['language']} | {row['category']} | {int(row.get('anchor_success') or 0)} | "
            f"{int(row.get('reply_success') or 0)} | "
            f"{row.get('memory_speakability')} | {int(row.get('memory_use_expected') or 0)} | {reply} |"
        )

    lines.extend(
        [
            "",
            "## Speakability Cases",
            "",
            "| id | category | expected | observed | explicit expected/observed | pass |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in report["speakability_results"]:
        lines.append(
            f"| {row['id']} | {row['category']} | {row['expected_label']} | {row['observed_label']} | "
            f"{row['expected_explicit']}/{row['observed_should_use_explicitly']} | {row['case_pass']} |"
        )
    return "\n".join(lines) + "\n"


def main():
    ensure_project_dirs()
    brain = brain_mod.UruhaBrainV4_Mac(load_right_brain_model=False)
    brain.memory.reflect_experience = lambda *_args, **_kwargs: None

    delayed_recall_results = [evaluate_recall_case(brain, case) for case in build_recall_cases()]
    speakability_results = [evaluate_speakability_case(case) for case in build_speakability_cases()]
    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "summary": {
            "delayed_recall": build_recall_summary(delayed_recall_results),
            "speakability": build_speakability_summary(speakability_results),
        },
        "delayed_recall_results": delayed_recall_results,
        "speakability_results": speakability_results,
    }

    with open(LONG_DIALOGUE_MEMORY_REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    with open(REPORT_MD_PATH, "w", encoding="utf-8") as f:
        f.write(build_markdown(report))
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0 if report["summary"]["speakability"]["case_pass_rate"] == 1.0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
