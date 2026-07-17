#!/usr/bin/env python3
"""Pure helpers for atomic reflection-fidelity and Japanese-surface auditing."""

from __future__ import annotations

import json
import re

import pyopenjtalk

from rightbrain_language_quality import (
    ASCII_WORD_RE,
    AUDITED_CHINESE_SPECIFIC_RE,
    AUDITED_NONSTANDARD_CJK_RE,
    CHINESE_SPECIFIC_RE,
    FOREIGN_SCRIPT_RE,
    NONSTANDARD_CJK_RE,
    UNICODE_REPLACEMENT_CHAR,
    has_japanese,
)


RELATIONS = ("entailed", "contradicted", "missing")
CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
SYSTEM_PROMPT = """You are a strict multilingual semantic entailment classifier.
For each atomic claim, compare only the candidate text.
- entailed: explicitly stated or necessarily implied by the candidate.
- contradicted: the candidate states the opposite.
- missing: neither entailed nor contradicted. Do not guess from plausibility.
Examples:
Candidate: 雨が好き。 Claims: a=likes rain; b=hates wind. Output: a=entailed; b=missing.
Candidate: 雨は好きではない。 Claim: a=likes rain. Output: a=contradicted.
Follow the JSON schema exactly."""


def response_schema(case):
    claim_ids = [claim["id"] for claim in case["claims"]]
    return {
        "type": "object",
        "properties": {
            claim_id: {"type": "string", "enum": list(RELATIONS)}
            for claim_id in claim_ids
        },
        "required": claim_ids,
        "additionalProperties": False,
    }


def judge_prompt(case):
    claims = "\n".join(
        f"- {claim['id']}: {claim['statement_en']}" for claim in case["claims"]
    )
    return (
        f"Candidate: {case['candidate_jp']}\n"
        f"Atomic claims:\n{claims}\n"
        "For every claim, output exactly entailed, contradicted, or missing."
    )


def parse_judgments(raw_text, case):
    try:
        payload = json.loads(str(raw_text or ""))
    except json.JSONDecodeError as exc:
        raise ValueError("invalid_json") from exc
    expected = {claim["id"] for claim in case["claims"]}
    if not isinstance(payload, dict) or set(payload) != expected:
        raise ValueError("schema_keys")
    if any(value not in RELATIONS for value in payload.values()):
        raise ValueError("invalid_relation")
    return payload


def _source_external_matches(pattern, text, source):
    return [
        match.group(0)
        for match in pattern.finditer(text)
        if match.group(0) and match.group(0) not in source
    ]


def _unknown_cjk_fragments(text, source):
    fragments = []
    for token in pyopenjtalk.run_frontend(str(text or "")):
        surface = str(token.get("string") or "")
        if (
            CJK_RE.search(surface)
            and token.get("pos") == "記号"
            and token.get("pos_group1") == "一般"
            and surface not in source
        ):
            fragments.append(surface)
    return fragments


def japanese_surface_report(candidate, source):
    text = str(candidate or "")
    source = str(source or "")
    reasons = []
    if not has_japanese(text):
        reasons.append("missing_japanese")
    external = []
    for pattern in (
        CHINESE_SPECIFIC_RE,
        NONSTANDARD_CJK_RE,
        AUDITED_CHINESE_SPECIFIC_RE,
        AUDITED_NONSTANDARD_CJK_RE,
        FOREIGN_SCRIPT_RE,
        ASCII_WORD_RE,
    ):
        external.extend(_source_external_matches(pattern, text, source))
    external.extend(_unknown_cjk_fragments(text, source))
    if UNICODE_REPLACEMENT_CHAR in text:
        external.append(UNICODE_REPLACEMENT_CHAR)
    if external:
        reasons.append("source_external_language:" + "|".join(dict.fromkeys(external)))
    return {
        "clean": not reasons,
        "reasons": reasons,
        "unknown_cjk_fragments": _unknown_cjk_fragments(text, source),
    }


def score_rows(rows):
    scored = []
    for row in rows:
        case = row["case"]
        observed = row.get("judgments") or {}
        surface = japanese_surface_report(case["candidate_jp"], case["source_text"])
        claims = []
        for claim in case["claims"]:
            relation = observed.get(claim["id"])
            claims.append(
                {
                    **claim,
                    "observed_relation": relation,
                    "correct": relation == claim["gold_relation"],
                    "critical_false_entailment": bool(
                        claim["critical"]
                        and claim["gold_relation"] != "entailed"
                        and relation == "entailed"
                    ),
                }
            )
        observed_accept = bool(
            row.get("schema_valid")
            and surface["clean"]
            and claims
            and all(claim["observed_relation"] == "entailed" for claim in claims)
        )
        scored.append(
            {
                "id": case["id"],
                "pair_id": case["pair_id"],
                "family": case["family"],
                "source_language": case["source_language"],
                "schema_valid": bool(row.get("schema_valid")),
                "claims": claims,
                "surface_report": surface,
                "expected_surface_clean": case["expected_surface_clean"],
                "expected_accept": case["expected_accept"],
                "observed_accept": observed_accept,
                "acceptance_correct": observed_accept == case["expected_accept"],
                "raw_response": row.get("raw_response") or "",
            }
        )
    return scored


def _rate(items, predicate):
    if not items:
        return 0.0
    return round(sum(1 for item in items if predicate(item)) / len(items), 4)


def summarize(scored, config, model_call_count):
    claims = [claim for row in scored for claim in row["claims"]]
    surface_negative = [row for row in scored if not row["expected_surface_clean"]]
    summary = {
        "case_count": len(scored),
        "atomic_claim_count": len(claims),
        "schema_parse_rate": _rate(scored, lambda row: row["schema_valid"]),
        "atomic_relation_accuracy": _rate(claims, lambda claim: claim["correct"]),
        "critical_false_entailment_count": sum(
            claim["critical_false_entailment"] for claim in claims
        ),
        "candidate_acceptance_accuracy": _rate(
            scored, lambda row: row["acceptance_correct"]
        ),
        "accepted_surface_specificity": _rate(
            surface_negative, lambda row: not row["surface_report"]["clean"]
        ),
        "model_call_count": model_call_count,
        "accepted_case_count": sum(row["observed_accept"] for row in scored),
    }
    gates = config["success_gates"]
    checks = {
        "schema_parse_rate": summary["schema_parse_rate"]
        >= gates["schema_parse_rate_min"],
        "atomic_relation_accuracy": summary["atomic_relation_accuracy"]
        >= gates["atomic_relation_accuracy_min"],
        "critical_false_entailment_count": summary[
            "critical_false_entailment_count"
        ]
        <= gates["critical_false_entailment_count_max"],
        "candidate_acceptance_accuracy": summary["candidate_acceptance_accuracy"]
        >= gates["candidate_acceptance_accuracy_min"],
        "accepted_surface_specificity": summary["accepted_surface_specificity"]
        >= gates["accepted_surface_specificity_min"],
        "model_call_count": model_call_count == gates["model_call_count_exact"],
    }
    summary["gate_checks"] = checks
    summary["all_gates_pass"] = all(checks.values())
    return summary
