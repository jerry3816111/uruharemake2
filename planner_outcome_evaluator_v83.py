"""Deterministic outcome evaluator for planner-to-surface causal experiments."""

from __future__ import annotations

import hashlib
import json
from collections import Counter

from rightbrain_language_quality import (
    ASCII_SYMBOL_ARTIFACT_RE,
    ASCII_WORD_RE,
    AUDITED_CHINESE_SPECIFIC_RE,
    AUDITED_NONSTANDARD_CJK_RE,
    CHINESE_SPECIFIC_RE,
    FOREIGN_SCRIPT_RE,
    JAPANESE_RE,
    NONSTANDARD_CJK_RE,
    UNICODE_REPLACEMENT_CHAR,
)


FAILURE_CODE_ORDER = (
    "empty_reply",
    "missing_japanese_surface",
    "cjk_language_leak",
    "foreign_script_leak",
    "unexpected_ascii_leak",
    "ascii_symbol_artifact",
    "unicode_replacement_character",
    "required_semantic_missing",
    "forbidden_semantic_present",
    "private_memory_intrusion",
    "over_max_chars",
    "malformed_action",
    "required_action_missing",
    "forbidden_action_present",
    "unexpected_action",
    "too_many_actions",
)


def canonical_sha256(value):
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def file_sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _marker_hit(reply, marker):
    marker = str(marker or "").strip()
    if not marker:
        return False
    compact_reply = "".join(str(reply or "").split())
    compact_marker = "".join(marker.split())
    return marker in reply or (compact_marker and compact_marker in compact_reply)


def _language_failure(reply):
    if (
        CHINESE_SPECIFIC_RE.search(reply)
        or NONSTANDARD_CJK_RE.search(reply)
        or AUDITED_CHINESE_SPECIFIC_RE.search(reply)
        or AUDITED_NONSTANDARD_CJK_RE.search(reply)
    ):
        return "cjk_language_leak"
    if FOREIGN_SCRIPT_RE.search(reply):
        return "foreign_script_leak"
    if ASCII_WORD_RE.search(reply):
        return "unexpected_ascii_leak"
    if ASCII_SYMBOL_ARTIFACT_RE.search(reply):
        return "ascii_symbol_artifact"
    if UNICODE_REPLACEMENT_CHAR in reply:
        return "unicode_replacement_character"
    return ""


def _action_observation(actions):
    malformed = False
    names = []
    if not isinstance(actions, list):
        return [], True
    for action in actions:
        if not isinstance(action, dict):
            malformed = True
            continue
        name = action.get("name")
        arguments = action.get("arguments")
        if not isinstance(name, str) or not name.strip() or not isinstance(arguments, dict):
            malformed = True
            continue
        names.append(name.strip())
    return names, malformed


def evaluate_outcome(case, outcome):
    """Score only externally observable reply and action behavior."""
    contract = case["outcome_contract"]
    reply = str((outcome or {}).get("reply") or "").strip()
    failures = []
    details = {}

    if not reply:
        failures.append("empty_reply")
    else:
        if not JAPANESE_RE.search(reply):
            failures.append("missing_japanese_surface")
        language_failure = _language_failure(reply)
        if language_failure:
            failures.append(language_failure)

        required_groups = contract.get("required_semantic_groups") or []
        missing_groups = [
            index
            for index, group in enumerate(required_groups)
            if not any(_marker_hit(reply, marker) for marker in group)
        ]
        if missing_groups:
            failures.append("required_semantic_missing")
            details["missing_required_group_indexes"] = missing_groups

        forbidden_hits = [
            marker
            for marker in contract.get("forbidden_markers") or []
            if _marker_hit(reply, marker)
        ]
        if forbidden_hits:
            failures.append("forbidden_semantic_present")
            details["forbidden_marker_hit_count"] = len(forbidden_hits)

        private_hits = [
            marker
            for marker in contract.get("private_memory_terms") or []
            if _marker_hit(reply, marker)
        ]
        if private_hits:
            failures.append("private_memory_intrusion")
            details["private_memory_hit_count"] = len(private_hits)

        maximum_reply_chars = int(contract.get("maximum_reply_chars") or 0)
        if maximum_reply_chars and len(reply) > maximum_reply_chars:
            failures.append("over_max_chars")
            details["reply_chars"] = len(reply)

    action_contract = contract.get("action_contract") or {}
    action_names, malformed_action = _action_observation((outcome or {}).get("actions", []))
    if malformed_action:
        failures.append("malformed_action")

    required_actions = set(action_contract.get("required_action_names") or [])
    forbidden_actions = set(action_contract.get("forbidden_action_names") or [])
    allowed_actions = set(action_contract.get("allowed_action_names") or [])
    observed_actions = set(action_names)
    if required_actions - observed_actions:
        failures.append("required_action_missing")
    if forbidden_actions & observed_actions:
        failures.append("forbidden_action_present")
    unexpected = observed_actions - allowed_actions - forbidden_actions
    if unexpected:
        failures.append("unexpected_action")
    maximum_actions = int(action_contract.get("maximum_action_count") or 0)
    if len(action_names) > maximum_actions:
        failures.append("too_many_actions")

    ordered_failures = [code for code in FAILURE_CODE_ORDER if code in set(failures)]
    return {
        "passed": not ordered_failures,
        "failure_codes": ordered_failures,
        "details": details,
        "reply_sha256": hashlib.sha256(reply.encode("utf-8")).hexdigest(),
        "reply_chars": len(reply),
        "action_names": action_names,
    }


def evaluate_calibration(dataset):
    rows = []
    for case in dataset["cases"]:
        valid_result = evaluate_outcome(case, case["valid_outcome"])
        rows.append(
            {
                "case_id": case["id"],
                "scenario_family": case["scenario_family"],
                "variant": "valid",
                "target_failure_code": "none",
                "result": valid_result,
            }
        )
        for mutation in case["mutations"]:
            rows.append(
                {
                    "case_id": case["id"],
                    "scenario_family": case["scenario_family"],
                    "variant": mutation["id"],
                    "target_failure_code": mutation["target_failure_code"],
                    "result": evaluate_outcome(case, mutation["outcome"]),
                }
            )
    return rows


def summarize_calibration(rows):
    valid_rows = [row for row in rows if row["variant"] == "valid"]
    mutation_rows = [row for row in rows if row["variant"] != "valid"]
    target_hits = sum(
        row["target_failure_code"] in row["result"]["failure_codes"]
        for row in mutation_rows
    )
    isolated_hits = sum(
        row["result"]["failure_codes"] == [row["target_failure_code"]]
        for row in mutation_rows
    )
    return {
        "valid_case_count": len(valid_rows),
        "mutation_count": len(mutation_rows),
        "valid_accept_count": sum(row["result"]["passed"] for row in valid_rows),
        "valid_accept_rate": sum(row["result"]["passed"] for row in valid_rows) / max(1, len(valid_rows)),
        "mutation_reject_count": sum(not row["result"]["passed"] for row in mutation_rows),
        "mutation_reject_rate": sum(not row["result"]["passed"] for row in mutation_rows) / max(1, len(mutation_rows)),
        "target_failure_hit_count": target_hits,
        "target_failure_recall": target_hits / max(1, len(mutation_rows)),
        "isolated_failure_count": isolated_hits,
        "isolated_failure_rate": isolated_hits / max(1, len(mutation_rows)),
        "failure_code_counts": dict(
            sorted(Counter(code for row in mutation_rows for code in row["result"]["failure_codes"]).items())
        ),
    }
