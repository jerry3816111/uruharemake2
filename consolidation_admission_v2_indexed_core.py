#!/usr/bin/env python3
"""Pure parsing, compilation, and scoring for indexed consolidation V2."""

from __future__ import annotations

import math
import statistics
from collections import Counter

from consolidation_admission_v1_core import parse_candidate_response


TARGETS = ("wisdom", "procedural", "none")
SCOPES = (
    "stable",
    "repeated",
    "recurring",
    "one_off",
    "transient",
    "third_party",
    "uncertain",
    "none",
)
OWNERS = ("user", "assistant", "third_party", "other", "none")
CONFIDENCE_BANDS = ("low", "medium", "high")
TOOL_NAME = "classify_memory_admission"
TOOL_KEYS = {
    "memory_kind",
    "scope",
    "owner",
    "evidence_user_turns",
    "confidence_band",
}


def _rate(numerator, denominator):
    return round(numerator / denominator, 4) if denominator else 0.0


def _p95(values):
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, math.ceil(0.95 * len(ordered)) - 1)
    return round(ordered[index], 4)


def _empty_parse(error, *, raw_content="", raw_tool_calls=None):
    return {
        "observed_target": "none",
        "parse_success": False,
        "index_contract_success": False,
        "parse_error": error,
        "memory_kind": None,
        "scope": None,
        "owner": None,
        "evidence_user_turns": [],
        "confidence_band": None,
        "payload": None,
        "raw_content": raw_content,
        "raw_tool_calls": raw_tool_calls or [],
    }


def compile_indexed_frame(frame, *, index_contract_success):
    """Fail closed unless the complete source-indexed frame is authorized."""
    if not index_contract_success:
        return "none"
    kind = frame["memory_kind"]
    scope = frame["scope"]
    owner = frame["owner"]
    evidence_count = len(frame["evidence_user_turns"])
    if (
        kind == "wisdom"
        and owner == "user"
        and scope in {"stable", "repeated"}
        and evidence_count >= (2 if scope == "repeated" else 1)
    ):
        return "wisdom"
    if (
        kind == "procedural"
        and owner == "assistant"
        and scope == "recurring"
        and evidence_count >= 1
    ):
        return "procedural"
    if kind == "none" and evidence_count == 0:
        return "none"
    return "none"


def _tool_shape_error(arguments):
    if set(arguments) != TOOL_KEYS:
        return "argument_keys"
    if arguments["memory_kind"] not in TARGETS:
        return "invalid_memory_kind"
    if arguments["scope"] not in SCOPES:
        return "invalid_scope"
    if arguments["owner"] not in OWNERS:
        return "invalid_owner"
    if arguments["confidence_band"] not in CONFIDENCE_BANDS:
        return "invalid_confidence_band"
    if not isinstance(arguments["evidence_user_turns"], list):
        return "evidence_user_turns_type"
    return None


def _index_contract(frame):
    indices = frame["evidence_user_turns"]
    if any(
        isinstance(index, bool)
        or not isinstance(index, int)
        or index not in {1, 2, 3}
        for index in indices
    ):
        return False
    if len(indices) != len(set(indices)):
        return False
    if frame["memory_kind"] == "none":
        return not indices
    return bool(indices)


def parse_indexed_tool_response(response):
    message = response.get("message") or {}
    content = str(message.get("content") or "")
    calls = message.get("tool_calls")
    if content.strip():
        return _empty_parse(
            "narrative_content",
            raw_content=content,
            raw_tool_calls=calls if isinstance(calls, list) else [],
        )
    if not isinstance(calls, list) or len(calls) != 1:
        return _empty_parse(
            "tool_call_count",
            raw_content=content,
            raw_tool_calls=calls if isinstance(calls, list) else [],
        )
    function = calls[0].get("function") if isinstance(calls[0], dict) else None
    if not isinstance(function, dict):
        return _empty_parse(
            "function_shape", raw_content=content, raw_tool_calls=calls
        )
    if function.get("name") != TOOL_NAME:
        return _empty_parse(
            "function_name", raw_content=content, raw_tool_calls=calls
        )
    arguments = function.get("arguments")
    if not isinstance(arguments, dict):
        return _empty_parse(
            "arguments_type", raw_content=content, raw_tool_calls=calls
        )
    shape_error = _tool_shape_error(arguments)
    if shape_error:
        return _empty_parse(
            shape_error, raw_content=content, raw_tool_calls=calls
        )
    frame = {
        "memory_kind": arguments["memory_kind"],
        "scope": arguments["scope"],
        "owner": arguments["owner"],
        "evidence_user_turns": list(arguments["evidence_user_turns"]),
        "confidence_band": arguments["confidence_band"],
    }
    index_success = _index_contract(frame)
    return {
        "observed_target": compile_indexed_frame(
            frame, index_contract_success=index_success
        ),
        "parse_success": True,
        "index_contract_success": index_success,
        "parse_error": None if index_success else "index_contract",
        **frame,
        "payload": arguments,
        "raw_content": content,
        "raw_tool_calls": calls,
    }


def _map_quotes_to_user_turns(quotes, user_utterances):
    mapped = []
    for quote in quotes:
        matches = [
            index
            for index, utterance in enumerate(user_utterances, start=1)
            if quote == utterance
        ]
        if len(matches) != 1:
            return [], False
        mapped.append(matches[0])
    return mapped, len(mapped) == len(set(mapped))


def parse_v1_control_response(response, user_utterances, v1_condition):
    """Run the frozen V1 parser, then map its exact quotes to fixed turn IDs."""
    parsed = parse_candidate_response(
        response, user_utterances, v1_condition
    )
    payload = parsed.get("payload")
    if not parsed["parse_success"] or not isinstance(payload, dict):
        return {
            **parsed,
            "index_contract_success": False,
            "memory_kind": None,
            "scope": None,
            "owner": None,
            "evidence_user_turns": [],
            "confidence_band": None,
        }
    indices, mapping_success = _map_quotes_to_user_turns(
        payload["evidence_quotes"], user_utterances
    )
    index_success = (
        parsed["evidence_contract_success"] and mapping_success
    )
    return {
        **parsed,
        "index_contract_success": index_success,
        "memory_kind": payload["candidate_kind"],
        "scope": payload["scope"],
        "owner": payload["target"],
        "evidence_user_turns": indices,
        "confidence_band": None,
    }


def evidence_grounded(case, row):
    if not row.get("index_contract_success"):
        return False
    predicted = set(row.get("evidence_user_turns") or [])
    required = set(case["required_evidence_user_turns"])
    allowed = set(case["allowed_evidence_user_turns"])
    if case["expected_memory_kind"] == "none":
        return predicted == set()
    return required <= predicted <= allowed


def _condition_summary(rows):
    elapsed = [float(row["wall_seconds"]) for row in rows]
    correct = sum(bool(row["correct"]) for row in rows)
    parse_count = sum(bool(row["parse_success"]) for row in rows)
    return {
        "correct_count": correct,
        "accuracy": _rate(correct, len(rows)),
        "observed_target_counts": dict(
            sorted(Counter(row["observed_target"] for row in rows).items())
        ),
        "parse_success_count": parse_count,
        "parse_success_rate": _rate(parse_count, len(rows)),
        "median_wall_seconds": (
            round(statistics.median(elapsed), 4) if elapsed else 0.0
        ),
        "warm_p95_wall_seconds": _p95(elapsed[1:]),
    }


def analyze_indexed_conditions(cases, control_rows, candidate_rows, gates):
    case_by_id = {case["id"]: case for case in cases}
    control_by_id = {row["id"]: row for row in control_rows}
    candidate_by_id = {row["id"]: row for row in candidate_rows}
    if len(case_by_id) != len(cases):
        raise ValueError("duplicate dataset case IDs")
    if len(control_by_id) != len(control_rows):
        raise ValueError("duplicate control case IDs")
    if len(candidate_by_id) != len(candidate_rows):
        raise ValueError("duplicate candidate case IDs")
    if set(control_by_id) != set(case_by_id):
        raise ValueError("control rows do not exactly match dataset cases")
    if set(candidate_by_id) != set(case_by_id):
        raise ValueError("candidate rows do not exactly match dataset cases")

    normalized_control = []
    normalized_candidate = []
    matched_rows = []
    for case in cases:
        expected = case["expected_memory_kind"]
        control = control_by_id[case["id"]]
        candidate = candidate_by_id[case["id"]]
        if control["observed_target"] not in TARGETS:
            raise ValueError(f"invalid control target: {case['id']}")
        if candidate["observed_target"] not in TARGETS:
            raise ValueError(f"invalid candidate target: {case['id']}")
        control_correct = control["observed_target"] == expected
        candidate_correct = candidate["observed_target"] == expected
        candidate_frame_exact = (
            candidate.get("parse_success", False)
            and candidate.get("memory_kind") == expected
            and candidate.get("scope") == case["expected_scope"]
            and candidate.get("owner") == case["expected_owner"]
        )
        candidate_evidence_grounded = evidence_grounded(case, candidate)
        normalized_control.append({**control, "correct": control_correct})
        normalized_candidate.append(
            {
                **candidate,
                "correct": candidate_correct,
                "frame_exact": candidate_frame_exact,
                "evidence_grounded": candidate_evidence_grounded,
            }
        )
        matched_rows.append(
            {
                "id": case["id"],
                "language": case["language"],
                "expected_target": expected,
                "control_target": control["observed_target"],
                "candidate_target": candidate["observed_target"],
                "control_correct": control_correct,
                "candidate_correct": candidate_correct,
                "candidate_frame_exact": candidate_frame_exact,
                "candidate_evidence_grounded": candidate_evidence_grounded,
            }
        )

    control_summary = _condition_summary(normalized_control)
    candidate_summary = _condition_summary(normalized_candidate)
    class_metrics = {}
    for target in TARGETS:
        selected = [
            row for row in matched_rows if row["expected_target"] == target
        ]
        correct = sum(row["candidate_correct"] for row in selected)
        class_metrics[target] = {
            "total": len(selected),
            "candidate_correct": correct,
            "candidate_accuracy": _rate(correct, len(selected)),
        }

    newly_correct = [
        row["id"]
        for row in matched_rows
        if row["candidate_correct"] and not row["control_correct"]
    ]
    regressions = [
        row["id"]
        for row in matched_rows
        if row["control_correct"] and not row["candidate_correct"]
    ]
    false_writes = [
        row["id"]
        for row in matched_rows
        if row["expected_target"] == "none"
        and row["candidate_target"] != "none"
    ]
    missed_writes = [
        row["id"]
        for row in matched_rows
        if row["expected_target"] != "none"
        and row["candidate_target"] == "none"
    ]
    frame_exact_count = sum(
        row["candidate_frame_exact"] for row in matched_rows
    )
    evidence_count = sum(
        row["candidate_evidence_grounded"] for row in matched_rows
    )
    positive_evidence_count = sum(
        row["candidate_evidence_grounded"]
        for row in matched_rows
        if row["expected_target"] != "none"
    )
    index_count = sum(
        bool(row.get("index_contract_success")) for row in candidate_rows
    )
    net_gain = (
        candidate_summary["correct_count"] - control_summary["correct_count"]
    )
    total_calls = len(control_rows) + len(candidate_rows)
    candidate_parse_rate = candidate_summary["parse_success_rate"]
    candidate_index_rate = _rate(index_count, len(candidate_rows))

    checks = {
        "candidate_correct_count_min": candidate_summary["correct_count"]
        >= gates["candidate_correct_count_min"],
        "candidate_accuracy_min": candidate_summary["accuracy"]
        >= gates["candidate_accuracy_min"],
        "candidate_wisdom_correct_min": class_metrics["wisdom"][
            "candidate_correct"
        ]
        >= gates["candidate_wisdom_correct_min"],
        "candidate_procedural_correct_min": class_metrics["procedural"][
            "candidate_correct"
        ]
        >= gates["candidate_procedural_correct_min"],
        "candidate_none_correct_min": class_metrics["none"][
            "candidate_correct"
        ]
        >= gates["candidate_none_correct_min"],
        "candidate_frame_exact_count_min": frame_exact_count
        >= gates["candidate_frame_exact_count_min"],
        "candidate_evidence_grounded_count_min": evidence_count
        >= gates["candidate_evidence_grounded_count_min"],
        "candidate_positive_evidence_grounded_count_min": positive_evidence_count
        >= gates["candidate_positive_evidence_grounded_count_min"],
        "newly_correct_vs_control_min": len(newly_correct)
        >= gates["newly_correct_vs_control_min"],
        "regression_vs_control_max": len(regressions)
        <= gates["regression_vs_control_max"],
        "net_correct_gain_vs_control_min": net_gain
        >= gates["net_correct_gain_vs_control_min"],
        "candidate_false_long_term_write_count_max": len(false_writes)
        <= gates["candidate_false_long_term_write_count_max"],
        "candidate_missed_long_term_write_count_max": len(missed_writes)
        <= gates["candidate_missed_long_term_write_count_max"],
        "candidate_tool_parse_success_rate_min": candidate_parse_rate
        >= gates["candidate_tool_parse_success_rate_min"],
        "candidate_index_contract_success_rate_min": candidate_index_rate
        >= gates["candidate_index_contract_success_rate_min"],
        "model_call_count_exact": total_calls
        == gates["model_call_count_exact"],
        "control_median_wall_seconds_max": control_summary[
            "median_wall_seconds"
        ]
        <= gates["control_median_wall_seconds_max"],
        "candidate_median_wall_seconds_max": candidate_summary[
            "median_wall_seconds"
        ]
        <= gates["candidate_median_wall_seconds_max"],
        "control_warm_p95_wall_seconds_max": control_summary[
            "warm_p95_wall_seconds"
        ]
        <= gates["control_warm_p95_wall_seconds_max"],
        "candidate_warm_p95_wall_seconds_max": candidate_summary[
            "warm_p95_wall_seconds"
        ]
        <= gates["candidate_warm_p95_wall_seconds_max"],
    }
    return {
        "case_count": len(cases),
        "model_call_count": total_calls,
        "control": control_summary,
        "candidate": {
            **candidate_summary,
            "frame_exact_count": frame_exact_count,
            "frame_exact_rate": _rate(frame_exact_count, len(cases)),
            "evidence_grounded_count": evidence_count,
            "evidence_grounded_rate": _rate(evidence_count, len(cases)),
            "positive_evidence_grounded_count": positive_evidence_count,
            "positive_evidence_grounded_rate": _rate(
                positive_evidence_count,
                sum(
                    case["expected_memory_kind"] != "none"
                    for case in cases
                ),
            ),
            "index_contract_success_count": index_count,
            "index_contract_success_rate": candidate_index_rate,
        },
        "accuracy_delta_vs_control": round(
            candidate_summary["accuracy"] - control_summary["accuracy"], 4
        ),
        "net_correct_gain_vs_control": net_gain,
        "class_metrics": class_metrics,
        "newly_correct_count": len(newly_correct),
        "newly_correct_case_ids": newly_correct,
        "regression_count": len(regressions),
        "regression_case_ids": regressions,
        "candidate_false_long_term_write_count": len(false_writes),
        "candidate_false_long_term_write_case_ids": false_writes,
        "candidate_missed_long_term_write_count": len(missed_writes),
        "candidate_missed_long_term_write_case_ids": missed_writes,
        "gate_checks": checks,
        "all_gates_pass": all(checks.values()),
        "matched_rows": matched_rows,
    }
