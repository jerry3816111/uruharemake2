#!/usr/bin/env python3
"""Independently verify the PersonaEval output-contract pilot."""

from __future__ import annotations

import hashlib
import json
import math
import re
import sys
from pathlib import Path

import build_personaeval_output_contract_selection_v1 as construction
import build_personaeval_qwen3_official_pilot_v1 as base


if str(base.JSON_REPAIR_TARGET) not in sys.path:
    sys.path.insert(0, str(base.JSON_REPAIR_TARGET))
import json_repair  # noqa: E402


ROOT = construction.ROOT


def _resolve_binding(binding):
    path = Path(binding["path"])
    if binding.get("scope") == "external_local" or path.is_absolute():
        return path
    return ROOT / path


def _verify_harness_lock(prereg):
    lock = base.load_json(construction.HARNESS_LOCK_PATH)
    bindings_match = all(
        (path := _resolve_binding(binding)).is_file()
        and base.sha256_file(path) == binding["sha256"]
        for binding in lock["bindings"]
    )
    auth = lock["authorization"]
    pilot = prereg["pilot_design"]
    passed = (
        lock["experiment_id"] == construction.EXPERIMENT_ID
        and bindings_match
        and base.local_environment() == prereg["local_environment"]
        and auth["condition_order"] == list(construction.CONDITION_ORDER)
        and auth["primary_row_count"] == pilot["primary_row_count"]
        and auth["repeat_audit_row_count"]
        == len(pilot["repeat_audit_row_ids"])
        and auth["total_generation_calls"] == pilot["total_generation_calls"]
        and auth["batch_size"] == 1
        and auth["labels_loaded_after_all_generation"] is True
        and auth["training_updates"] == 0
        and auth["production_runtime_change"] is False
    )
    return passed


def _strict_parse(output, options):
    matches = re.findall(r"```\s*(.+?)\s*```", output, re.DOTALL)
    parsed = json_repair.loads(matches[-1] if matches else output)
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
    return max(values, key=values.get), values


def _candidate_parse(output, options):
    if output not in options:
        raise ValueError("not exactly one candidate")
    return output, None


def _poisson_tail(probabilities, observed):
    distribution = [1.0] + [0.0] * len(probabilities)
    for probability in probabilities:
        updated = [0.0] * len(distribution)
        for successes in range(len(distribution)):
            updated[successes] += distribution[successes] * (1.0 - probability)
            if successes:
                updated[successes] += distribution[successes - 1] * probability
        distribution = updated
    return sum(distribution[observed:])


def _wilson(successes, total, z=1.959963984540054):
    proportion = successes / total
    denominator = 1.0 + z * z / total
    centre = (proportion + z * z / (2.0 * total)) / denominator
    margin = (
        z
        * math.sqrt(
            proportion * (1.0 - proportion) / total + z * z / (4.0 * total * total)
        )
        / denominator
    )
    return [centre - margin, centre + margin]


def _aggregate(rows):
    parsed = sum(row["parse_success"] for row in rows)
    correct = sum(row["correct"] for row in rows)
    chance = [1.0 / row["option_count"] for row in rows]
    return {
        "row_count": len(rows),
        "parsed_count": parsed,
        "parse_success_rate": parsed / len(rows),
        "correct_count": correct,
        "unconditional_top1_accuracy": correct / len(rows),
        "unconditional_top1_wilson_95": _wilson(correct, len(rows)),
        "random_choice_expected_accuracy": sum(chance) / len(rows),
        "exact_chance_superiority_p_value": _poisson_tail(chance, correct),
    }


def _repeat(primary, repeats, audit_ids):
    by_key = {(row["row_id"], row["repetition"]): row for row in primary + repeats}
    exact = prediction = 0
    for row_id in audit_ids:
        rows = [by_key[(row_id, repetition)] for repetition in (1, 2, 3)]
        exact += len({row["output_sha256"] for row in rows}) == 1
        predictions = [row["prediction"] for row in rows]
        prediction += all(row["parse_success"] for row in rows) and len(set(predictions)) == 1
    return {
        "row_count": len(audit_ids),
        "exact_output_agreement_count": exact,
        "exact_output_agreement_rate": exact / len(audit_ids),
        "prediction_agreement_count": prediction,
        "prediction_agreement_rate": prediction / len(audit_ids),
    }


def _paired(strict_rows, candidate_rows):
    strict = {row["row_id"]: bool(row["correct"]) for row in strict_rows}
    candidate = {row["row_id"]: bool(row["correct"]) for row in candidate_rows}
    strict_only = sum(strict[row_id] and not candidate[row_id] for row_id in strict)
    candidate_only = sum(candidate[row_id] and not strict[row_id] for row_id in strict)
    discordant = strict_only + candidate_only
    if discordant:
        tail = sum(
            math.comb(discordant, k)
            for k in range(min(strict_only, candidate_only) + 1)
        ) / (2**discordant)
        p_value = min(1.0, 2.0 * tail)
    else:
        p_value = 1.0
    return {
        "row_count": len(strict),
        "strict_only_correct": strict_only,
        "candidate_only_correct": candidate_only,
        "discordant_count": discordant,
        "exact_two_sided_mcnemar_p_value": p_value,
        "accuracy_delta_candidate_minus_strict": (candidate_only - strict_only)
        / len(strict),
    }


def _decision(prereg, measurements, paired, lock_passed):
    rule = prereg["decision_rule"]
    strict = measurements["strict_probability"]["overall"]
    candidate = measurements["candidate_name"]["overall"]
    repeat = measurements["candidate_name"]["repeat_audit"]
    checks = {
        "lock_exact": lock_passed,
        "candidate_parse_gate": candidate["parse_success_rate"]
        >= rule["candidate_minimum_parse_success_rate"],
        "candidate_above_chance_gate": candidate["exact_chance_superiority_p_value"]
        <= rule["candidate_maximum_chance_superiority_p_value"],
        "candidate_wilson_lower_above_random_gate": candidate[
            "unconditional_top1_wilson_95"
        ][0]
        > candidate["random_choice_expected_accuracy"],
        "candidate_repeat_gate": repeat["prediction_agreement_rate"]
        >= rule["candidate_minimum_prediction_repeat_agreement"],
        "parse_improvement_gate": candidate["parse_success_rate"]
        - strict["parse_success_rate"]
        >= rule["minimum_parse_improvement_over_strict"],
        "accuracy_noninferiority_point_gate": candidate["unconditional_top1_accuracy"]
        >= strict["unconditional_top1_accuracy"],
    }
    passed = all(checks.values())
    return {
        "passed": passed,
        "checks": checks,
        "selected_contract": "candidate_name" if passed else None,
        "paired": paired,
    }


def verify():
    prereg = base.load_json(construction.PREREGISTRATION_PATH)
    prompts_payload = base.load_json(construction.PROMPTS_PATH)
    labels_payload = base.load_json(construction.LABELS_PATH)
    raw = base.load_json(construction.RAW_RESULT_PATH)
    result = base.load_json(construction.RESULT_PATH)
    prompts = {row["row_id"]: row for row in prompts_payload["rows"]}
    labels = {row["row_id"]: row for row in labels_payload["rows"]}
    checks = {}

    lock_passed = _verify_harness_lock(prereg)
    checks["harness_lock_exact"] = lock_passed

    checks["source_and_model_revision_exact"] = (
        prereg["official_provenance"]["dataset_commit"] == base.HF_DATASET_COMMIT
        and prereg["official_provenance"]["code_commit"]
        == base.OFFICIAL_REPOSITORY_COMMIT
        and prereg["model_contract"]["snapshot_revision"] == base.MODEL_SNAPSHOT.name
    )
    checks["prompt_label_hashes_exact"] = (
        prereg["dataset_contract"]["prompts"]["sha256"]
        == base.sha256_file(construction.PROMPTS_PATH)
        and prereg["dataset_contract"]["labels"]["sha256"]
        == base.sha256_file(construction.LABELS_PATH)
        and prereg["dataset_contract"]["prompt_rows_sha256"]
        == base.canonical_json_sha256(prompts_payload["rows"])
        and prereg["dataset_contract"]["label_rows_sha256"]
        == base.canonical_json_sha256(labels_payload["rows"])
    )
    previous = set()
    for path in construction.PREVIOUS_PROMPT_PATHS:
        previous.update(
            (row["track"], row["source_row_index"])
            for row in base.load_json(path)["rows"]
        )
    current = {
        (row["track"], row["source_row_index"]) for row in prompts.values()
    }
    checks["labels_absent_and_holdout_disjoint"] = (
        len(prompts) == 30
        and set(prompts) == set(labels)
        and not previous & current
        and all(
            "gt" not in row and "ground_truth" not in row and "label_sha256" not in row
            for row in prompts.values()
        )
    )
    runtime = raw["runtime_contract"]
    checks["generation_isolation_exact"] = (
        raw["preregistration_sha256"]
        == base.sha256_file(construction.PREREGISTRATION_PATH)
        and raw["harness_lock_sha256"]
        == base.sha256_file(construction.HARNESS_LOCK_PATH)
        and runtime["condition_order"] == list(construction.CONDITION_ORDER)
        and runtime["system_messages"] == construction.SYSTEM_MESSAGES
        and runtime["official_user_prompt_changed"] is False
        and runtime["batch_size"] == 1
        and runtime["temperature"] == 0.0
        and runtime["generation_calls"] == 96
        and runtime["optimizer_created"] is False
        and runtime["optimizer_updates"] == 0
        and runtime["adapter_initialized"] is False
        and runtime["memory_loaded"] is False
        and runtime["persona_prompt_loaded"] is False
        and runtime["labels_loaded_after_both_conditions_finish"] is True
        and runtime["ground_truth_passed_to_model"] is False
        and runtime["event_order"].index("both_conditions_all_generation_complete")
        < runtime["event_order"].index(
            "labels_loaded_after_both_conditions_all_generation"
        )
    )

    row_scores_exact = True
    recomputed_metrics = {}
    recomputed_repeats = {}
    audit_ids = prereg["pilot_design"]["repeat_audit_row_ids"]
    for condition in construction.CONDITION_ORDER:
        primary = raw["conditions"][condition]["primary"]
        repeats = raw["conditions"][condition]["repeat_audit"]
        primary_ids = [row["row_id"] for row in primary]
        repeat_keys = [(row["row_id"], row["repetition"]) for row in repeats]
        expected_repeat_keys = [
            (row_id, repetition)
            for repetition in (2, 3)
            for row_id in audit_ids
        ]
        if (
            len(primary) != 30
            or primary_ids != prereg["pilot_design"]["primary_row_ids"]
            or len(repeats) != 18
            or sorted(repeat_keys) != sorted(expected_repeat_keys)
            or any(row["phase"] != "primary" or row["repetition"] != 1 for row in primary)
            or any(row["phase"] != "repeat_audit" for row in repeats)
        ):
            row_scores_exact = False
        for row in primary + repeats:
            prompt = prompts[row["row_id"]]
            label = labels[row["row_id"]]
            try:
                if condition == "strict_probability":
                    prediction, probabilities = _strict_parse(
                        row["output"], prompt["options"]
                    )
                else:
                    prediction, probabilities = _candidate_parse(
                        row["output"], prompt["options"]
                    )
                parsed = True
            except Exception:
                prediction = None
                probabilities = None
                parsed = False
            correct = prediction == label["ground_truth"]
            if not (
                row["condition"] == condition
                and row["prompt_sha256"] == prompt["prompt_sha256"]
                and row["output_sha256"]
                == hashlib.sha256(row["output"].encode("utf-8")).hexdigest()
                and row["ground_truth"] == label["ground_truth"]
                and row["label_sha256"] == label["label_sha256"]
                and row["parse_success"] == parsed
                and row["probabilities"] == probabilities
                and row["prediction"] == prediction
                and row["correct"] == correct
            ):
                row_scores_exact = False
        recomputed_metrics[condition] = _aggregate(primary)
        recomputed_repeats[condition] = _repeat(primary, repeats, audit_ids)
    checks["row_scores_exact"] = row_scores_exact

    aggregate_exact = True
    for condition in construction.CONDITION_ORDER:
        stored = result["measurements"]["conditions"][condition]["overall"]
        for key, expected in recomputed_metrics[condition].items():
            actual = stored[key]
            if isinstance(expected, list):
                if any(
                    not math.isclose(a, b, abs_tol=1e-12)
                    for a, b in zip(actual, expected)
                ):
                    aggregate_exact = False
            elif isinstance(expected, float):
                if not math.isclose(actual, expected, abs_tol=1e-12):
                    aggregate_exact = False
            elif actual != expected:
                aggregate_exact = False
        stored_repeat = result["measurements"]["conditions"][condition][
            "repeat_audit"
        ]
        for key, expected in recomputed_repeats[condition].items():
            actual = stored_repeat[key]
            if isinstance(expected, float):
                if not math.isclose(actual, expected, abs_tol=1e-12):
                    aggregate_exact = False
            elif actual != expected:
                aggregate_exact = False
    checks["aggregate_and_repeat_metrics_exact"] = aggregate_exact

    paired = _paired(
        raw["conditions"]["strict_probability"]["primary"],
        raw["conditions"]["candidate_name"]["primary"],
    )
    stored_paired = result["measurements"]["paired"]
    checks["paired_statistics_exact"] = all(
        math.isclose(stored_paired[key], expected, abs_tol=1e-12)
        if isinstance(expected, float)
        else stored_paired[key] == expected
        for key, expected in paired.items()
    )
    expected_decision = _decision(
        prereg,
        {
            condition: {
                "overall": recomputed_metrics[condition],
                "repeat_audit": recomputed_repeats[condition],
            }
            for condition in construction.CONDITION_ORDER
        },
        paired,
        lock_passed,
    )
    decision = result["decision"]
    checks["decision_exact_and_narrow"] = (
        decision["passed"] == expected_decision["passed"]
        and decision["checks"] == expected_decision["checks"]
        and decision["selected_contract_for_larger_validation"]
        == expected_decision["selected_contract"]
        and decision["authorize_larger_disjoint_adapted_evaluator_validation"]
        == expected_decision["passed"]
        and decision["authorize_target_person_judging"] is False
        and decision["authorize_human_rater_replacement"] is False
        and decision["authorize_training"] is False
        and decision["authorize_production"] is False
    )
    checks["raw_result_binding_exact"] = (
        result["raw_result"]["sha256"] == base.sha256_file(construction.RAW_RESULT_PATH)
    )
    passed = all(checks.values())
    verification = {
        "schema": "personaeval_output_contract_selection_verification_v1",
        "experiment_id": construction.EXPERIMENT_ID,
        "passed": passed,
        "checks": checks,
        "recomputed": {
            "conditions": {
                condition: {
                    **recomputed_metrics[condition],
                    "repeat_prediction_agreement": recomputed_repeats[condition][
                        "prediction_agreement_rate"
                    ],
                }
                for condition in construction.CONDITION_ORDER
            },
            "paired": paired,
            "expected_decision": expected_decision,
        },
        "verified_authorization": {
            "larger_disjoint_adapted_evaluator_validation": expected_decision[
                "passed"
            ],
            "target_person_judging": False,
            "human_rater_replacement": False,
            "training": False,
            "production": False,
        },
    }
    base.atomic_json(construction.VERIFICATION_JSON_PATH, verification)
    lines = [
        "# PersonaEval output-contract selection verification",
        "",
        f"- Independent verification passed: `{passed}`",
    ]
    for condition in construction.CONDITION_ORDER:
        metrics = recomputed_metrics[condition]
        repeat = recomputed_repeats[condition]
        lines.extend(
            [
                f"- `{condition}` parse: `{metrics['parsed_count']}/30`",
                f"- `{condition}` correct: `{metrics['correct_count']}/30`",
                f"- `{condition}` repeat agreement: `{repeat['prediction_agreement_count']}/9`",
            ]
        )
    lines.extend(
        [
            f"- Candidate contract selected: `{expected_decision['passed']}`",
            "- Target-person / human replacement / training / production: `False`",
            "",
        ]
    )
    base.atomic_text(construction.VERIFICATION_MD_PATH, "\n".join(lines))
    return verification


def main():
    verification = verify()
    print(json.dumps(verification, ensure_ascii=False, indent=2))
    raise SystemExit(0 if verification["passed"] else 1)


if __name__ == "__main__":
    main()
