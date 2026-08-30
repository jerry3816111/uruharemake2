"""Frozen controlled evaluation for M29 literal-topic projection fidelity.

This module is an engineering validation harness.  It scores observable
semantic slots and fail-closed behavior; it is not a professional translation
metric or human naturalness evaluation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from openai import OpenAI

import uruha_adaptive_person_model as uapm
import uruha_brain_mac as brain_runtime
import uruha_personhood_loop as upl


ROOT = Path(__file__).resolve().parent
DEFAULT_PROTOCOL_PATH = ROOT / "research/m30_cross_lingual_literal_fidelity_protocol.json"
DEFAULT_OUTPUT_PATH = ROOT / "analysis/m30_cross_lingual_literal_fidelity_raw_2026-08-25.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_frozen_protocol(path: Path = DEFAULT_PROTOCOL_PATH):
    protocol_path = Path(path)
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    holdout_path = ROOT / protocol["holdout"]["path"]
    actual_hash = _sha256(holdout_path)
    expected_hash = protocol["holdout"]["sha256"]
    if actual_hash != expected_hash:
        raise ValueError(
            f"M30 holdout hash mismatch: expected {expected_hash}, got {actual_hash}"
        )
    holdout = json.loads(holdout_path.read_text(encoding="utf-8"))
    cases = holdout.get("cases") or []
    ids = [case.get("case_id") for case in cases]
    if len(cases) != int(protocol["holdout"]["case_count"]):
        raise ValueError("M30 case count does not match frozen protocol")
    if len(ids) != len(set(ids)) or any(not case_id for case_id in ids):
        raise ValueError("M30 case IDs must be unique and non-empty")
    language_counts = Counter(case.get("language") for case in cases)
    if language_counts != Counter({"zh": 6, "en": 6, "ja": 6}):
        raise ValueError(f"M30 language balance changed: {dict(language_counts)}")
    return protocol, holdout, protocol_path, holdout_path


def build_actual_left_brain():
    client = OpenAI(
        base_url=brain_runtime.OLLAMA_URL,
        api_key=brain_runtime.OLLAMA_API_KEY,
        max_retries=0,
    )
    client.models.list()
    return brain_runtime.LeftBrain(client)


def _candidate_for_case(text: str):
    feedback = {
        "status": "uncertain",
        "reason": "m30_frozen_unlinked_current_topic",
        "previous_prediction_id": "m30-frozen-previous-prediction",
        "feedback_linked_to_previous_prediction": False,
        "causal_outcome_calibration_m27": {
            "status": "resolved_unknown_excluded"
        },
    }
    pragmatic = upl.build_human_pragmatic_understanding(text, turn_index=2)
    transition = uapm.build_feedback_topic_transition_m28(
        text,
        feedback,
        pragmatic,
    )
    candidate = uapm.build_literal_topic_projection_candidate_m29(
        text,
        feedback,
        pragmatic,
        transition,
    )
    return candidate, pragmatic, transition


def _projection_text(contract) -> str:
    fields = [
        contract.get("subject_jp"),
        contract.get("predicate_jp"),
        contract.get("time_jp"),
        contract.get("literal_summary_jp"),
        contract.get("response_jp"),
    ]
    return "\n".join(str(value or "") for value in fields)


def score_case(case, candidate, contract):
    authority = bool(contract.get("surface_authority"))
    authority_expected = bool(case.get("authority_expected"))
    projection_text = _projection_text(contract)
    group_results = []
    for group in case.get("required_japanese_groups") or []:
        alternatives = [str(value) for value in group.get("any_of") or []]
        hits = [value for value in alternatives if value in projection_text]
        group_results.append(
            {
                "label": group.get("label"),
                "passed": bool(hits),
                "matched": hits[:2],
            }
        )
    semantic_groups_passed = all(row["passed"] for row in group_results)
    expected_polarity = str(case.get("expected_polarity") or "unknown")
    polarity_observed = str(contract.get("polarity") or "unknown")
    polarity_passed = (
        polarity_observed == expected_polarity if authority_expected else True
    )
    faithful = bool(
        authority_expected
        and authority
        and semantic_groups_passed
        and polarity_passed
    )
    if faithful:
        outcome = "faithful_authority"
    elif authority_expected and authority:
        outcome = "false_authority"
    elif authority_expected:
        outcome = "false_reject"
    elif authority:
        outcome = "unsafe_incomplete_authority"
    else:
        outcome = "true_abstention"
    return {
        "case_id": case["case_id"],
        "language": case["language"],
        "category": case["category"],
        "input_digest": hashlib.sha256(case["input"].encode("utf-8")).hexdigest()[:16],
        "authority_expected": authority_expected,
        "candidate_status": candidate.get("status"),
        "candidate_reason": candidate.get("reason"),
        "projection_status": contract.get("status"),
        "projection_reason": contract.get("reason"),
        "surface_authority": authority,
        "outcome": outcome,
        "group_results": group_results,
        "semantic_groups_passed": semantic_groups_passed,
        "expected_polarity": expected_polarity,
        "observed_polarity": polarity_observed,
        "polarity_passed": polarity_passed,
        "subject_jp": contract.get("subject_jp"),
        "predicate_jp": contract.get("predicate_jp"),
        "time_jp": contract.get("time_jp"),
        "literal_summary_jp": contract.get("literal_summary_jp"),
        "response_jp": contract.get("response_jp"),
        "validation_checks": contract.get("validation_checks") or {},
        "elapsed_seconds": float(contract.get("elapsed_seconds") or 0.0),
        "raw_dialogue_persisted": bool(contract.get("raw_dialogue_persisted")),
        "model_response_raw_persisted": bool(
            contract.get("model_response_raw_persisted")
        ),
    }


def _rate(numerator, denominator):
    return round(numerator / denominator, 4) if denominator else None


def _p95(values):
    ordered = sorted(values)
    if not ordered:
        return None
    index = max(0, math.ceil(0.95 * len(ordered)) - 1)
    return round(float(ordered[index]), 4)


def summarize(rows, gates):
    valid = [row for row in rows if row["authority_expected"]]
    incomplete = [row for row in rows if not row["authority_expected"]]
    outcome_counts = Counter(row["outcome"] for row in rows)
    by_language = {}
    for language in ("zh", "en", "ja"):
        language_valid = [row for row in valid if row["language"] == language]
        language_faithful = sum(
            row["outcome"] == "faithful_authority" for row in language_valid
        )
        by_language[language] = {
            "valid_count": len(language_valid),
            "faithful_count": language_faithful,
            "faithful_rate": _rate(language_faithful, len(language_valid)),
        }
    negation = [
        row for row in valid if row["expected_polarity"] == "negated"
    ]
    latency = [row["elapsed_seconds"] for row in rows if row["elapsed_seconds"] > 0]
    metrics = {
        "case_count": len(rows),
        "valid_count": len(valid),
        "incomplete_count": len(incomplete),
        "outcome_counts": dict(sorted(outcome_counts.items())),
        "overall_faithful_valid_rate": _rate(
            outcome_counts["faithful_authority"], len(valid)
        ),
        "false_authority_valid_rate": _rate(
            outcome_counts["false_authority"], len(valid)
        ),
        "false_reject_valid_rate": _rate(
            outcome_counts["false_reject"], len(valid)
        ),
        "unsafe_incomplete_authority_count": outcome_counts[
            "unsafe_incomplete_authority"
        ],
        "negation_polarity_accuracy": _rate(
            sum(row["polarity_passed"] for row in negation), len(negation)
        ),
        "by_language": by_language,
        "median_projection_seconds": (
            round(float(statistics.median(latency)), 4) if latency else None
        ),
        "p95_projection_seconds": _p95(latency),
        "raw_dialogue_persisted_count": sum(
            row["raw_dialogue_persisted"] for row in rows
        ),
        "model_response_raw_persisted_count": sum(
            row["model_response_raw_persisted"] for row in rows
        ),
    }
    gate_results = {
        "overall_faithful_valid_rate_min": metrics[
            "overall_faithful_valid_rate"
        ]
        >= gates["overall_faithful_valid_rate_min"],
        "per_language_faithful_valid_rate_min": all(
            item["faithful_rate"] is not None
            and item["faithful_rate"] >= gates["per_language_faithful_valid_rate_min"]
            for item in by_language.values()
        ),
        "false_authority_valid_rate_max": metrics["false_authority_valid_rate"]
        <= gates["false_authority_valid_rate_max"],
        "false_reject_valid_rate_max": metrics["false_reject_valid_rate"]
        <= gates["false_reject_valid_rate_max"],
        "unsafe_incomplete_authority_count_max": metrics[
            "unsafe_incomplete_authority_count"
        ]
        <= gates["unsafe_incomplete_authority_count_max"],
        "negation_polarity_accuracy_min": (
            metrics["negation_polarity_accuracy"] is not None
            and metrics["negation_polarity_accuracy"]
            >= gates["negation_polarity_accuracy_min"]
        ),
        "median_projection_seconds_max": (
            metrics["median_projection_seconds"] is not None
            and metrics["median_projection_seconds"]
            <= gates["median_projection_seconds_max"]
        ),
        "p95_projection_seconds_max": (
            metrics["p95_projection_seconds"] is not None
            and metrics["p95_projection_seconds"]
            <= gates["p95_projection_seconds_max"]
        ),
    }
    return metrics, gate_results


def run_frozen_evaluation(protocol_path=DEFAULT_PROTOCOL_PATH):
    protocol, holdout, resolved_protocol, holdout_path = load_frozen_protocol(
        Path(protocol_path)
    )
    left_brain = build_actual_left_brain()
    rows = []
    for case in holdout["cases"]:
        candidate, _pragmatic, _transition = _candidate_for_case(case["input"])
        if candidate.get("projection_required"):
            _plan, contract = left_brain.project_literal_topic_m29(
                case["input"], candidate
            )
        else:
            contract = {
                **candidate,
                "status": "projection_not_attempted",
                "reason": candidate.get("reason") or "candidate_gate_not_passed",
                "surface_authority": False,
                "raw_dialogue_persisted": False,
                "model_response_raw_persisted": False,
            }
        rows.append(score_case(case, candidate, contract))
    metrics, gate_results = summarize(
        rows, protocol["frozen_success_gates"]
    )
    return {
        "schema": "uruha_cross_lingual_literal_fidelity_result_m30_v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "protocol_path": str(resolved_protocol.relative_to(ROOT)),
        "protocol_sha256": _sha256(resolved_protocol),
        "holdout_path": str(holdout_path.relative_to(ROOT)),
        "holdout_sha256": _sha256(holdout_path),
        "model": "qwen2.5:7b",
        "decision": "pass_all_frozen_gates" if all(gate_results.values()) else "fail_one_or_more_frozen_gates",
        "metrics": metrics,
        "gate_results": gate_results,
        "rows": rows,
        "claim_boundary": protocol["claim_boundary"],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    args = parser.parse_args()
    result = run_frozen_evaluation(args.protocol)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"decision": result["decision"], **result["metrics"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
