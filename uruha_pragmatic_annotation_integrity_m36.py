#!/usr/bin/env python3
"""M36 pragmatic annotation-integrity gate.

The gate is intentionally independent from the runtime desired-response
classifier.  It checks only explicit, observable response-form requests in an
evaluation row.  It does not infer private intent, grade naturalness, or copy
raw feedback into its persisted audit rows.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


SCHEMA_M36 = "uruha_pragmatic_annotation_integrity_m36_v1"
ALLOWED_POLICIES_M36 = {
    "playful_tease",
    "solve_regulation",
    "listen_presence",
    "share_arousal",
    "calibrate_need",
}
DECISIVE_OUTCOMES_M36 = {"supported", "contradicted", "uncertain"}


def _digest(value):
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()[:16]


def _matches_any(text, patterns):
    return [rule_id for rule_id, pattern in patterns if re.search(pattern, text, re.I)]


_POSITIVE_PATTERNS = {
    "listen_presence": (
        ("zh_listen_direct", r"(?:先|只|就)?(?:聽|听)(?:我)?.{0,6}(?:說|说|講|讲|完)"),
        ("en_hear_out", r"\bhear\s+(?:me|this)\s+out\b"),
        ("en_listen_direct", r"\b(?:just\s+)?listen\s+to\s+me\b"),
        ("en_let_talk", r"\blet\s+me\s+(?:talk|finish|say\s+it)\b"),
        ("ja_listen_direct", r"(?:話|はなし).{0,8}(?:聞いて|きいて)"),
        ("ja_just_listen", r"(?:まず|ただ|そのまま).{0,5}(?:聞いて|きいて)"),
    ),
    "solve_regulation": (
        ("zh_one_step", r"(?:給|给|告訴|告诉).{0,12}(?:一個|一个|一步|方法|步驟|步骤)"),
        ("zh_what_first", r"(?:先|第一步).{0,8}(?:做什麼|做什么|怎麼做|怎么做)"),
        ("en_give_step", r"\bgive\s+me\s+(?:(?:one|a|the)\s+)?(?:[a-z-]+\s+){0,3}(?:step|method|thing\s+to\s+do)\b"),
        ("en_tell_do", r"\btell\s+me\s+(?:what|how).{0,24}\bdo\b"),
        ("en_what_first", r"\bwhat\s+should\s+i\s+do\s+first\b"),
        ("ja_one_step", r"(?:一つ|ひとつ|一個).{0,10}(?:方法|やること|手順).{0,8}(?:教えて|決めて)"),
        ("ja_how_to", r"(?:どうすれば|まず何を).{0,12}(?:いい|教えて|すればいい)"),
    ),
    "playful_tease": (
        ("zh_tease", r"(?:吐槽|虧|亏|開.*玩笑|开.*玩笑).{0,5}(?:我|一下)?"),
        ("en_tease", r"\b(?:tease|roast|make\s+fun\s+of)\s+me\b"),
        ("ja_tease", r"(?:ツッコんで|いじって|からかって|軽く煽って)"),
    ),
    "share_arousal": (
        ("zh_stay", r"(?:陪|待在.{0,4}陪)(?:我)?(?:一下|一會|一会)?"),
        ("en_stay", r"\b(?:stay|sit|be)\s+(?:here\s+)?with\s+me\b"),
        ("en_company", r"\bkeep\s+me\s+company\b"),
        ("ja_stay", r"(?:そば|ここ|一緒).{0,5}(?:いて|居て)"),
    ),
    "calibrate_need": (
        ("zh_ask_first", r"(?:先問|先问|先確認|先确认).{0,8}(?:我|要什麼|要什么)"),
        ("en_ask_first", r"\b(?:ask|check|clarify).{0,12}\bfirst\b"),
        ("ja_ask_first", r"先に.{0,8}(?:聞いて|確認して)"),
    ),
}

_NEGATIVE_PATTERNS = {
    "listen_presence": (
        r"(?:不要|別|别).{0,4}(?:只)?(?:聽|听)",
        r"\b(?:do\s+not|don't)\s+just\s+listen\b",
        r"聞くだけじゃなく",
    ),
    "solve_regulation": (
        r"(?:不要|不用|不是要|不想要).{0,5}(?:方法|建議|建议|解決|解决)",
        r"\b(?:no|don't\s+give\s+me|do\s+not\s+give\s+me)\s+(?:any\s+)?advice\b",
        r"\bnot\s+asking\s+for\s+(?:a\s+)?solution\b",
        r"(?:解決策|方法).{0,4}(?:いらない|要らない|ほしくない)",
    ),
    "playful_tease": (
        r"(?:不要|不是要|別|别).{0,4}(?:吐槽|開玩笑|开玩笑)",
        r"\b(?:don't|do\s+not)\s+(?:tease|roast)\b",
        r"(?:ツッコミ|いじり).{0,4}(?:いらない|要らない)",
    ),
    "share_arousal": (
        r"(?:不要|不用|別|别).{0,4}陪",
        r"\b(?:don't|do\s+not)\s+stay\s+with\s+me\b",
        r"(?:そば|一緒).{0,5}いなくていい",
    ),
    "calibrate_need": (
        r"(?:不要|不用|別|别).{0,4}(?:問|确认|確認)",
        r"\b(?:don't|do\s+not)\s+ask\b|\bno\s+questions\b",
        r"(?:質問|確認).{0,5}(?:しないで|いらない)",
    ),
}


def classify_explicit_feedback_target_m36(feedback_input):
    """Return an independent explicit response-form target, or no target.

    Multiple non-negated targets are treated as ambiguous instead of resolving
    them with ordering heuristics.  That makes the annotation gate fail closed.
    """

    text = str(feedback_input or "").strip()
    lowered = text.lower()
    negated = {
        policy
        for policy, patterns in _NEGATIVE_PATTERNS.items()
        if any(re.search(pattern, lowered, re.I) for pattern in patterns)
    }
    matched = {}
    for policy, patterns in _POSITIVE_PATTERNS.items():
        if policy in negated:
            continue
        rule_ids = _matches_any(lowered, patterns)
        if rule_ids:
            matched[policy] = rule_ids
    if len(matched) == 1:
        policy = next(iter(matched))
        status = "explicit_target"
    elif len(matched) > 1:
        policy = None
        status = "ambiguous_multiple_targets"
    else:
        policy = None
        status = "no_explicit_target"
    return {
        "schema": SCHEMA_M36,
        "status": status,
        "policy": policy,
        "matched_policy_rule_ids": matched,
        "negated_policies": sorted(negated),
        "feedback_digest": _digest(text),
        "raw_feedback_persisted": False,
    }


def validate_annotation_rows_m36(cases):
    """Validate outcome/policy scoring before a reserve can be sealed."""

    errors = []
    audits = []
    case_ids = []
    for row in cases or []:
        case_id = str(row.get("case_id") or "")
        case_ids.append(case_id)
        outcome = str(row.get("expected_feedback_outcome") or "")
        expected_policy = row.get("expected_feedback_policy")
        scoring = str(row.get("feedback_policy_scoring") or "")
        current_policy = str(row.get("expected_current_policy") or "")
        target = classify_explicit_feedback_target_m36(row.get("feedback_input"))
        row_errors = []
        if not case_id:
            row_errors.append("missing_case_id")
        if outcome not in DECISIVE_OUTCOMES_M36:
            row_errors.append("invalid_feedback_outcome")
        if outcome == "contradicted":
            if scoring != "scored":
                row_errors.append("contradiction_feedback_policy_must_be_scored")
            if expected_policy not in ALLOWED_POLICIES_M36:
                row_errors.append("contradiction_expected_policy_invalid")
            if target.get("status") != "explicit_target":
                row_errors.append("contradiction_requires_one_explicit_replacement")
            elif expected_policy != target.get("policy"):
                row_errors.append("contradiction_expected_policy_target_mismatch")
            if expected_policy == current_policy:
                row_errors.append("contradiction_replacement_equals_current_policy")
        else:
            if scoring != "not_scored":
                row_errors.append("noncontradiction_feedback_policy_must_be_not_scored")
            if expected_policy not in {None, "not_scored"}:
                row_errors.append("noncontradiction_expected_policy_must_be_not_scored")
        errors.extend(f"{case_id or 'missing'}:{item}" for item in row_errors)
        audits.append(
            {
                "case_id": case_id or None,
                "expected_feedback_outcome": outcome,
                "feedback_policy_scoring": scoring,
                "independent_explicit_target_status": target.get("status"),
                "independent_explicit_target_policy": target.get("policy"),
                "independent_rule_ids": target.get("matched_policy_rule_ids"),
                "feedback_digest": target.get("feedback_digest"),
                "errors": row_errors,
                "raw_feedback_persisted": False,
            }
        )
    if len(case_ids) != len(set(case_ids)):
        errors.append("dataset:duplicate_case_id")
    return {
        "schema": SCHEMA_M36,
        "passed": not errors,
        "case_count": len(case_ids),
        "error_count": len(errors),
        "errors": errors,
        "audits": audits,
        "raw_feedback_persisted": False,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()
    dataset_path = Path(args.dataset)
    payload = json.loads(dataset_path.read_text(encoding="utf-8"))
    result = validate_annotation_rows_m36(payload.get("cases") or [])
    result["dataset_sha256"] = hashlib.sha256(dataset_path.read_bytes()).hexdigest()
    rendered = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
