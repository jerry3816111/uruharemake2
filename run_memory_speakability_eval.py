import json
import os
from datetime import datetime

import uruha_memory_runtime as umr
from project_paths import REPORTS_DIR, ensure_project_dirs


REPORT_JSON_PATH = os.path.join(REPORTS_DIR, "memory_speakability_eval_report.json")
REPORT_MD_PATH = os.path.join(REPORTS_DIR, "memory_speakability_eval_report.md")


def build_cases():
    return [
        {
            "id": "direct_name_recall",
            "description": "使用者直接問名字，記憶可以明講。",
            "anchor": {"kind": "name", "value": "Jerry", "jp_anchor": "Jerry", "source_text": "Name=Jerry", "relevance": 0.5, "expected": True},
            "user_input": "你還記得我叫什麼嗎？",
            "trust": 50,
            "expected_label": "explicit_ok",
            "expected_explicit": True,
        },
        {
            "id": "direct_recent_action",
            "description": "使用者直接問剛剛說過的事，可以明講。",
            "anchor": {"kind": "recent_action", "value": "コンビニ", "jp_anchor": "コンビニ", "source_text": "さっきコンビニ行ってくるって言った。", "relevance": 0.68, "expected": True},
            "user_input": "さっき何するって言ってたっけ？",
            "trust": 50,
            "expected_label": "explicit_ok",
            "expected_explicit": True,
        },
        {
            "id": "contextual_food_memory",
            "description": "相關但未被直接問，應作為背景，不要突然明講。",
            "anchor": {"kind": "context", "value": "ramen", "jp_anchor": "ラーメン", "source_text": "User once had stomach pain after ramen", "relevance": 0.55, "expected": False},
            "user_input": "今日は何食べようかな",
            "trust": 50,
            "expected_label": "background_only",
            "expected_explicit": False,
        },
        {
            "id": "low_trust_memory",
            "description": "信任度很低時，即使想起來也先不要主動攤開。",
            "anchor": {"kind": "context", "value": "sad conversation", "jp_anchor": "しんどい話", "source_text": "User said they felt sad yesterday", "relevance": 0.6, "expected": False},
            "user_input": "今日は普通に話そ",
            "trust": 10,
            "expected_label": "background_only",
            "expected_explicit": False,
        },
        {
            "id": "sensitive_password",
            "description": "密碼類資訊不能直接說出口。",
            "anchor": {"kind": "context", "value": "password is 1234", "jp_anchor": "password", "source_text": "User told a password is 1234", "relevance": 0.9, "expected": True},
            "user_input": "你記得那件事嗎？",
            "trust": 80,
            "expected_label": "suppressed_sensitive",
            "expected_explicit": False,
        },
        {
            "id": "sensitive_address",
            "description": "地址類隱私不能直接說出口。",
            "anchor": {"kind": "context", "value": "address", "jp_anchor": "住所", "source_text": "User lives at a private address", "relevance": 0.82, "expected": True},
            "user_input": "你還記得我住哪嗎？",
            "trust": 80,
            "expected_label": "suppressed_sensitive",
            "expected_explicit": False,
        },
        {
            "id": "third_party_unrequested",
            "description": "第三人資訊沒有被問到時不要主動提。",
            "anchor": {"kind": "context", "value": "friend wants movie", "jp_anchor": "友達の映画", "source_text": "朋友說她最近想看電影", "relevance": 0.7, "expected": False},
            "user_input": "今天聊點輕鬆的",
            "trust": 50,
            "expected_label": "suppressed_third_party",
            "expected_explicit": False,
        },
        {
            "id": "third_party_direct_query",
            "description": "直接問到第三人相關記憶時，可以承認有脈絡，但由上層決定怎麼措辭。",
            "anchor": {"kind": "context", "value": "friend said movie", "jp_anchor": "友達の映画", "source_text": "朋友說想看電影", "relevance": 0.72, "expected": True},
            "user_input": "你記得我朋友說過什麼嗎？",
            "trust": 50,
            "expected_label": "explicit_ok",
            "expected_explicit": True,
        },
        {
            "id": "weak_contextual_memory",
            "description": "弱相關記憶只保留為 latent，不推動回答。",
            "anchor": {"kind": "context", "value": "old snack", "jp_anchor": "お菓子", "source_text": "old snack preference", "relevance": 0.2, "expected": False},
            "user_input": "今日は何する？",
            "trust": 50,
            "expected_label": "latent_ok",
            "expected_explicit": False,
        },
        {
            "id": "no_memory",
            "description": "沒有記憶 anchor 時應回傳 no_memory。",
            "anchor": {},
            "user_input": "今日は何する？",
            "trust": 50,
            "expected_label": "no_memory",
            "expected_explicit": False,
        },
    ]


def evaluate_case(case):
    result = umr.assess_memory_speakability(case["anchor"], user_input=case["user_input"], trust=case["trust"])
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


def build_summary(results):
    return {
        "total_cases": len(results),
        "label_accuracy": _rate(results, "label_ok"),
        "explicit_contract_accuracy": _rate(results, "explicit_contract_ok"),
        "case_pass_rate": _rate(results, "case_pass"),
        "passed_cases": sum(int(row.get("case_pass") or 0) for row in results),
    }


def write_report(payload):
    ensure_project_dirs()
    with open(REPORT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    lines = [
        "# Memory Speakability Eval Report",
        "",
        f"- generated_at: {payload['generated_at']}",
        f"- total_cases: {payload['summary']['total_cases']}",
        f"- label_accuracy: {payload['summary']['label_accuracy']}",
        f"- explicit_contract_accuracy: {payload['summary']['explicit_contract_accuracy']}",
        f"- case_pass_rate: {payload['summary']['case_pass_rate']}",
        "",
        "## Cases",
        "",
        "| id | expected | observed | explicit expected/observed | pass |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in payload["results"]:
        lines.append(
            "| {id} | {expected_label} | {observed_label} | {expected_explicit}/{observed_should_use_explicitly} | {case_pass} |".format(**row)
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- This eval checks whether remembered content should be spoken explicitly, kept as background, or suppressed.",
            "- It is not a benchmark-answer shortcut; it measures conversational memory hygiene.",
        ]
    )
    with open(REPORT_MD_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main():
    results = [evaluate_case(case) for case in build_cases()]
    payload = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": build_summary(results),
        "results": results,
    }
    write_report(payload)
    print(json.dumps(payload["summary"], ensure_ascii=False, indent=2))
    return 0 if payload["summary"]["case_pass_rate"] == 1.0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
