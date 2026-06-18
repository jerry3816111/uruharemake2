import contextlib
import io
import json
import re
import shutil
import tempfile
from datetime import datetime

import uruha_brain_mac as brain_mod
from project_paths import (
    MEMORY_CONTRADICTION_CORRECTION_REPORT_JSON_PATH,
    MEMORY_CONTRADICTION_CORRECTION_REPORT_MD_PATH,
    ensure_project_dirs,
)


def build_cases():
    return [
        {
            "id": "zh_like_then_not_like",
            "language": "zh",
            "category": "preference_negation",
            "seed_turns": ["我最喜歡咖啡。", "我現在不喜歡咖啡了。"],
            "query": "你還覺得我喜歡咖啡嗎？",
            "target_terms": ["咖啡", "コーヒー"],
        },
        {
            "id": "en_like_then_not_like",
            "language": "en",
            "category": "preference_negation",
            "seed_turns": ["My favorite drink is coffee.", "I don't like coffee anymore."],
            "query": "Do you still think coffee is my favorite drink?",
            "target_terms": ["coffee", "コーヒー"],
        },
        {
            "id": "ja_like_then_not_like",
            "language": "ja",
            "category": "preference_negation",
            "seed_turns": ["コーヒーが一番好き。", "コーヒーはもう好きじゃない。"],
            "query": "まだコーヒーが一番好きだと思ってる？",
            "target_terms": ["コーヒー"],
        },
        {
            "id": "zh_food_then_cannot_eat",
            "language": "zh",
            "category": "capability_negation",
            "seed_turns": ["我最喜歡拉麵。", "我現在不能吃拉麵了。"],
            "query": "你還覺得我喜歡拉麵嗎？",
            "target_terms": ["拉麵", "ラーメン"],
        },
        {
            "id": "en_food_then_cannot_eat",
            "language": "en",
            "category": "capability_negation",
            "seed_turns": ["My favorite food is ramen.", "I cannot eat ramen anymore."],
            "query": "Do you still think ramen is my favorite food?",
            "target_terms": ["ramen", "ラーメン"],
        },
    ]


def normalize(text):
    return re.sub(r"\s+", " ", str(text or "").strip().lower())


def contains_any(text, terms):
    lowered = normalize(text)
    return any(normalize(term) in lowered for term in terms or [])


def silent_template_reply(brain, logic, query, mems):
    with contextlib.redirect_stdout(io.StringIO()):
        return brain.right_brain._template_reply(
            logic,
            user_input=query,
            current_psyche=brain.psyche.get_state(),
            memory_data=mems,
        )


def simulate_user_turn(brain, utterance):
    brain.memory.save_episode(
        utterance,
        "",
        brain.psyche.get_state(),
        {"intent": "memory_contradiction_seed", "scene": "memory", "jp_summary": utterance},
    )


def evaluate_case(brain, case):
    tempdir = tempfile.mkdtemp(prefix="uruha_memory_contradiction_eval_")
    try:
        brain.reset_session(db_path=tempdir)
        brain.memory.reflect_experience = lambda *_args, **_kwargs: None

        for turn in case["seed_turns"]:
            simulate_user_turn(brain, turn)

        mems = brain.memory.query_all_layers(case["query"])
        logic = brain.left_brain._rule_based_plan(case["query"], brain.psyche.get_state(), mems)
        if logic is None:
            logic = {
                "intent": "rule_miss",
                "scene": "eval",
                "memory_anchor": {},
                "memory_speakability": "no_memory",
                "memory_use_expected": False,
                "memory_relevance": 0.0,
            }
        brain._attach_memory_gravity(logic, case["query"], mems)
        reply = silent_template_reply(brain, logic, case["query"], mems)
        profile = mems.get("profile_structured") or {}
        anchor = logic.get("memory_anchor") or {}

        positive_profile_text = json.dumps(
            {
                "favorites": profile.get("favorites") or [],
                "likes": profile.get("likes") or [],
            },
            ensure_ascii=False,
        )
        negative_profile_text = json.dumps(profile.get("dislikes") or [], ensure_ascii=False)
        anchor_text = json.dumps(anchor, ensure_ascii=False)
        correction_markers = ["じゃない", "違う", "更新", "not_current"]

        current_negative_profile = contains_any(negative_profile_text, case["target_terms"])
        stale_positive_profile = contains_any(positive_profile_text, case["target_terms"])
        correction_intent = logic.get("intent") == "memory_correction"
        current_anchor = anchor.get("kind") == "preference_correction" and contains_any(anchor_text, case["target_terms"])
        reply_mentions_target = contains_any(reply, case["target_terms"])
        reply_marks_correction = contains_any(reply, correction_markers)

        return {
            **case,
            "profile": profile,
            "memory_anchor": anchor,
            "logic_intent": logic.get("intent"),
            "memory_speakability": logic.get("memory_speakability"),
            "memory_use_expected": bool(logic.get("memory_use_expected")),
            "memory_relevance": logic.get("memory_relevance"),
            "reply": reply,
            "current_negative_profile": int(current_negative_profile),
            "stale_positive_profile": int(stale_positive_profile),
            "correction_intent": int(correction_intent),
            "current_anchor": int(current_anchor),
            "reply_mentions_target": int(reply_mentions_target),
            "reply_marks_correction": int(reply_marks_correction),
            "case_pass": int(
                current_negative_profile
                and not stale_positive_profile
                and correction_intent
                and current_anchor
                and reply_mentions_target
                and reply_marks_correction
            ),
        }
    finally:
        shutil.rmtree(tempdir, ignore_errors=True)


def _rate(rows, key):
    if not rows:
        return 0.0
    return round(sum(int(row.get(key) or 0) for row in rows) / len(rows), 4)


def build_summary(results):
    summary = {
        "total_cases": len(results),
        "case_pass_rate": _rate(results, "case_pass"),
        "current_negative_profile_rate": _rate(results, "current_negative_profile"),
        "stale_positive_profile_rate": _rate(results, "stale_positive_profile"),
        "correction_intent_rate": _rate(results, "correction_intent"),
        "current_anchor_rate": _rate(results, "current_anchor"),
        "reply_correction_rate": _rate(results, "reply_marks_correction"),
        "by_category": {},
        "by_language": {},
    }
    for category in sorted({row["category"] for row in results}):
        rows = [row for row in results if row["category"] == category]
        summary["by_category"][category] = {
            "count": len(rows),
            "case_pass_rate": _rate(rows, "case_pass"),
            "stale_positive_profile_rate": _rate(rows, "stale_positive_profile"),
            "reply_correction_rate": _rate(rows, "reply_marks_correction"),
        }
    for language in sorted({row["language"] for row in results}):
        rows = [row for row in results if row["language"] == language]
        summary["by_language"][language] = {
            "count": len(rows),
            "case_pass_rate": _rate(rows, "case_pass"),
            "correction_intent_rate": _rate(rows, "correction_intent"),
        }
    return summary


def build_markdown(report):
    summary = report["summary"]
    lines = [
        "# Memory Contradiction / Correction Report",
        "",
        f"- generated_at: {report['generated_at']}",
        "",
        "## Summary",
        "",
        f"- total_cases: {summary['total_cases']}",
        f"- case_pass_rate: {summary['case_pass_rate']}",
        f"- current_negative_profile_rate: {summary['current_negative_profile_rate']}",
        f"- stale_positive_profile_rate: {summary['stale_positive_profile_rate']}",
        f"- correction_intent_rate: {summary['correction_intent_rate']}",
        f"- current_anchor_rate: {summary['current_anchor_rate']}",
        f"- reply_correction_rate: {summary['reply_correction_rate']}",
        "",
        "## Interpretation",
        "",
        "- This eval checks whether explicit negation updates the current profile state without deleting historical episodes.",
        "- Passing means the system can keep old memories as history while answering from the newer current-state memory.",
        "",
        "## Cases",
        "",
        "| id | lang | category | current_negative_profile | stale_positive_profile | intent | anchor | reply_correction | pass | reply_text |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in report["results"]:
        reply = str(row.get("reply") or "").replace("|", "／")
        lines.append(
            f"| {row['id']} | {row['language']} | {row['category']} | "
            f"{row['current_negative_profile']} | {row['stale_positive_profile']} | {row['correction_intent']} | "
            f"{row['current_anchor']} | {row['reply_marks_correction']} | {row['case_pass']} | {reply} |"
        )
    return "\n".join(lines) + "\n"


def main():
    ensure_project_dirs()
    brain = brain_mod.UruhaBrainV4_Mac(load_right_brain_model=False)
    brain.memory.reflect_experience = lambda *_args, **_kwargs: None
    results = [evaluate_case(brain, case) for case in build_cases()]
    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "summary": build_summary(results),
        "results": results,
    }
    with open(MEMORY_CONTRADICTION_CORRECTION_REPORT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    with open(MEMORY_CONTRADICTION_CORRECTION_REPORT_MD_PATH, "w", encoding="utf-8") as f:
        f.write(build_markdown(report))
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0 if report["summary"]["case_pass_rate"] == 1.0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
