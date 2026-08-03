#!/usr/bin/env python3
"""Independently verify the frozen PersonaEval pilot result and authorization."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path

import build_personaeval_qwen3_official_pilot_v1 as construction


ROOT = Path(__file__).resolve().parent
VERIFICATION_JSON = (
    ROOT / "reports/personaeval_qwen3_official_pilot_v1_verification.json"
)
VERIFICATION_MD = (
    ROOT / "reports/personaeval_qwen3_official_pilot_v1_verification.md"
)

if str(construction.JSON_REPAIR_TARGET) not in sys.path:
    sys.path.insert(0, str(construction.JSON_REPAIR_TARGET))
import json_repair  # noqa: E402


def _parse(response, options):
    matches = re.findall(r"```\s*(.+?)\s*```", response, re.DOTALL)
    parsed = json_repair.loads(matches[-1] if matches else response)
    if not isinstance(parsed, dict):
        raise ValueError("not an object")
    values = {}
    for option in options:
        value = float(parsed[option])
        if not math.isfinite(value) or not 0.0 <= value <= 1.0:
            raise ValueError("not a probability")
        values[option] = value
    if abs(sum(values.values()) - 1.0) > 1e-5:
        raise ValueError("probability sum mismatch")
    return values


def _poisson_tail(probabilities, observed):
    distribution = [1.0] + [0.0] * len(probabilities)
    for probability in probabilities:
        next_distribution = [0.0] * len(distribution)
        for successes in range(len(distribution)):
            next_distribution[successes] += distribution[successes] * (1.0 - probability)
            if successes:
                next_distribution[successes] += distribution[successes - 1] * probability
        distribution = next_distribution
    return sum(distribution[observed:])


def verify():
    prereg = construction.load_json(construction.PREREGISTRATION_PATH)
    prompts_payload = construction.load_json(construction.PROMPTS_PATH)
    labels_payload = construction.load_json(construction.LABELS_PATH)
    raw = construction.load_json(construction.RAW_RESULT_PATH)
    result = construction.load_json(construction.RESULT_PATH)
    prompts = {row["row_id"]: row for row in prompts_payload["rows"]}
    labels = {row["row_id"]: row for row in labels_payload["rows"]}
    primary = raw["primary"]
    repeat = raw["repeat_audit"]
    checks = {}

    checks["source_commits_exact"] = (
        prereg["official_provenance"]["dataset_commit"]
        == construction.HF_DATASET_COMMIT
        and prereg["official_provenance"]["code_commit"]
        == construction.OFFICIAL_REPOSITORY_COMMIT
    )
    checks["prompt_label_hashes_exact"] = (
        prereg["dataset_contract"]["prompts"]["sha256"]
        == construction.sha256_file(construction.PROMPTS_PATH)
        and prereg["dataset_contract"]["labels"]["sha256"]
        == construction.sha256_file(construction.LABELS_PATH)
        and prereg["dataset_contract"]["prompt_rows_sha256"]
        == construction.canonical_json_sha256(prompts_payload["rows"])
        and prereg["dataset_contract"]["label_rows_sha256"]
        == construction.canonical_json_sha256(labels_payload["rows"])
    )
    checks["labels_absent_from_prompt_rows"] = all(
        "gt" not in row and "ground_truth" not in row and "label_sha256" not in row
        for row in prompts.values()
    )
    checks["row_sets_exact"] = (
        len(prompts) == 60
        and set(prompts) == set(labels)
        and len(primary) == 60
        and {row["row_id"] for row in primary} == set(prompts)
        and len(repeat) == 24
    )
    runtime = raw["runtime_contract"]
    checks["generation_isolation_exact"] = (
        runtime["system_message"] == construction.SYSTEM_MESSAGE
        and runtime["generic_json_only_transport_adapter"] is True
        and runtime["official_prompt_changed"] is False
        and runtime["generation_calls"] == 84
        and runtime["optimizer_created"] is False
        and runtime["optimizer_updates"] == 0
        and runtime["adapter_initialized"] is False
        and runtime["memory_loaded"] is False
        and runtime["persona_prompt_loaded"] is False
        and runtime["labels_loaded_after_all_generation_calls"] is True
        and runtime["ground_truth_passed_to_model"] is False
        and runtime["event_order"].index("all_generation_calls_complete")
        < runtime["event_order"].index("labels_loaded_after_all_generation_calls")
    )

    parse_count = correct_count = 0
    recomputed = {}
    for row in primary:
        row_id = row["row_id"]
        prompt = prompts[row_id]
        label = labels[row_id]
        output_hash = hashlib.sha256(row["output"].encode("utf-8")).hexdigest()
        try:
            probabilities = _parse(row["output"], prompt["options"])
            prediction = max(probabilities, key=probabilities.get)
            parsed = True
        except Exception:
            probabilities = None
            prediction = None
            parsed = False
        correct = prediction == label["ground_truth"]
        parse_count += parsed
        correct_count += correct
        recomputed[row_id] = {
            "parsed": parsed,
            "prediction": prediction,
            "correct": correct,
            "probabilities": probabilities,
        }
        if not (
            row["prompt_sha256"] == prompt["prompt_sha256"]
            and row["output_sha256"] == output_hash
            and row["ground_truth"] == label["ground_truth"]
            and row["label_sha256"] == label["label_sha256"]
            and row["parse_success"] == parsed
            and row["prediction"] == prediction
            and row["correct"] == correct
        ):
            checks["row_scores_exact"] = False
            break
    else:
        checks["row_scores_exact"] = True

    overall = result["measurements"]["overall_balanced_pilot"]
    chance_probabilities = [1.0 / prompts[row["row_id"]]["option_count"] for row in primary]
    chance_p = _poisson_tail(chance_probabilities, correct_count)
    checks["aggregate_counts_exact"] = (
        overall["row_count"] == 60
        and overall["parsed_count"] == parse_count
        and overall["correct_count"] == correct_count
        and math.isclose(overall["parse_success_rate"], parse_count / 60, abs_tol=1e-12)
        and math.isclose(
            overall["unconditional_top1_accuracy"], correct_count / 60, abs_tol=1e-12
        )
        and math.isclose(
            overall["exact_chance_superiority_p_value"], chance_p, abs_tol=1e-12
        )
    )

    audit_ids = prereg["pilot_design"]["repeat_audit_row_ids"]
    all_rows = primary + repeat
    by_key = {(row["row_id"], row["repetition"]): row for row in all_rows}
    exact_count = prediction_count = 0
    for row_id in audit_ids:
        rows = [by_key[(row_id, repetition)] for repetition in (1, 2, 3)]
        exact_count += len({row["output_sha256"] for row in rows}) == 1
        predictions = []
        for row in rows:
            try:
                probabilities = _parse(row["output"], prompts[row_id]["options"])
                predictions.append(max(probabilities, key=probabilities.get))
            except Exception:
                predictions.append(None)
        prediction_count += None not in predictions and len(set(predictions)) == 1
    repeat_result = result["measurements"]["repeat_audit"]
    checks["repeat_metrics_exact"] = (
        repeat_result["row_count"] == 12
        and repeat_result["exact_output_agreement_count"] == exact_count
        and repeat_result["prediction_agreement_count"] == prediction_count
        and math.isclose(
            repeat_result["prediction_agreement_rate"], prediction_count / 12, abs_tol=1e-12
        )
    )

    gate = prereg["decision_gate"]
    expected_pass = (
        parse_count / 60 >= gate["minimum_parse_success_rate"]
        and chance_p <= gate["maximum_chance_superiority_p_value"]
        and overall["unconditional_top1_wilson_95"][0]
        > overall["random_choice_expected_accuracy"]
        and prediction_count / 12 >= gate["minimum_prediction_repeat_agreement"]
    )
    decision = result["decision"]
    checks["decision_exact_and_narrow"] = (
        decision["passed"] == expected_pass
        and decision["authorize_larger_official_validation"] == expected_pass
        and decision["authorize_target_person_judging"] is False
        and decision["authorize_human_rater_replacement"] is False
        and decision["authorize_training"] is False
        and decision["authorize_production"] is False
    )
    checks["raw_result_binding_exact"] = (
        result["raw_result"]["sha256"]
        == construction.sha256_file(construction.RAW_RESULT_PATH)
    )
    passed = all(checks.values())
    verification = {
        "schema": "personaeval_qwen3_official_pilot_verification_v1",
        "experiment_id": construction.EXPERIMENT_ID,
        "passed": passed,
        "checks": checks,
        "recomputed": {
            "parsed_count": parse_count,
            "correct_count": correct_count,
            "unconditional_top1_accuracy": correct_count / 60,
            "exact_chance_superiority_p_value": chance_p,
            "repeat_exact_output_count": exact_count,
            "repeat_prediction_agreement_count": prediction_count,
            "expected_gate_pass": expected_pass,
        },
        "verified_authorization": {
            "larger_official_validation": expected_pass,
            "target_person_judging": False,
            "human_rater_replacement": False,
            "training": False,
            "production": False,
        },
    }
    construction.atomic_json(VERIFICATION_JSON, verification)
    construction.atomic_text(
        VERIFICATION_MD,
        "\n".join(
            [
                "# PersonaEval Qwen3 official pilot verification",
                "",
                f"- Independent verification passed: `{passed}`",
                f"- Recomputed parse count: `{parse_count}/60`",
                f"- Recomputed correct count: `{correct_count}/60`",
                f"- Recomputed repeat prediction agreement: `{prediction_count}/12`",
                f"- Target-person judging / human replacement / training / production: `False`",
                "",
            ]
        ),
    )
    return verification


def main():
    parser = argparse.ArgumentParser()
    parser.parse_args()
    result = verify()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
