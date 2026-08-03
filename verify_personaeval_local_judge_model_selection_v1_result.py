#!/usr/bin/env python3
"""Independently verify the paired local-judge PersonaEval pilot."""

from __future__ import annotations

import hashlib
import json
import math
import re
import sys

import build_personaeval_local_judge_model_selection_v1 as construction
import build_personaeval_qwen3_official_pilot_v1 as base


if str(base.JSON_REPAIR_TARGET) not in sys.path:
    sys.path.insert(0, str(base.JSON_REPAIR_TARGET))
import json_repair  # noqa: E402


def _parse(response, options):
    matches = re.findall(r"```\s*(.+?)\s*```", response, re.DOTALL)
    parsed = json_repair.loads(matches[-1] if matches else response)
    if not isinstance(parsed, dict):
        raise ValueError("not an object")
    probabilities = {}
    for option in options:
        value = float(parsed[option])
        if not math.isfinite(value) or not 0.0 <= value <= 1.0:
            raise ValueError("not a probability")
        probabilities[option] = value
    if abs(sum(probabilities.values()) - 1.0) > 1e-5:
        raise ValueError("probability sum mismatch")
    return probabilities


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


def _aggregate(rows, prompts):
    parsed = sum(row["parse_success"] for row in rows)
    correct = sum(row["correct"] for row in rows)
    probabilities = [1.0 / prompts[row["row_id"]]["option_count"] for row in rows]
    return {
        "row_count": len(rows),
        "parsed_count": parsed,
        "correct_count": correct,
        "parse_success_rate": parsed / len(rows),
        "unconditional_top1_accuracy": correct / len(rows),
        "unconditional_top1_wilson_95": _wilson(correct, len(rows)),
        "random_choice_expected_accuracy": sum(probabilities) / len(rows),
        "exact_chance_superiority_p_value": _poisson_tail(probabilities, correct),
    }


def _repeat(primary, repeats, audit_ids, prompts):
    by_key = {(row["row_id"], row["repetition"]): row for row in primary + repeats}
    exact = 0
    prediction = 0
    for row_id in audit_ids:
        rows = [by_key[(row_id, repetition)] for repetition in (1, 2, 3)]
        exact += len({row["output_sha256"] for row in rows}) == 1
        predictions = []
        for row in rows:
            try:
                probabilities = _parse(row["output"], prompts[row_id]["options"])
                predictions.append(max(probabilities, key=probabilities.get))
            except Exception:
                predictions.append(None)
        prediction += None not in predictions and len(set(predictions)) == 1
    return {
        "row_count": len(audit_ids),
        "exact_output_agreement_count": exact,
        "prediction_agreement_count": prediction,
        "prediction_agreement_rate": prediction / len(audit_ids),
    }


def _paired(rows_a, rows_b):
    by_a = {row["row_id"]: bool(row["correct"]) for row in rows_a}
    by_b = {row["row_id"]: bool(row["correct"]) for row in rows_b}
    only_a = sum(by_a[row_id] and not by_b[row_id] for row_id in by_a)
    only_b = sum(by_b[row_id] and not by_a[row_id] for row_id in by_a)
    discordant = only_a + only_b
    if discordant:
        tail = sum(
            math.comb(discordant, k) for k in range(min(only_a, only_b) + 1)
        ) / (2**discordant)
        p_value = min(1.0, 2.0 * tail)
    else:
        p_value = 1.0
    return {
        "qwen3_4b_only_correct": only_a,
        "qwen25_7b_only_correct": only_b,
        "exact_two_sided_mcnemar_p_value": p_value,
        "accuracy_delta_qwen25_7b_minus_qwen3_4b": (only_b - only_a) / len(by_a),
    }


def _gate(prereg, metrics, repeat, lock_exact):
    rule = prereg["decision_rule"]
    checks = {
        "lock_exact": lock_exact,
        "parse_success_gate": metrics["parse_success_rate"]
        >= rule["per_model_minimum_parse_success_rate"],
        "above_chance_gate": metrics["exact_chance_superiority_p_value"]
        <= rule["per_model_maximum_chance_superiority_p_value"],
        "wilson_lower_above_random_gate": metrics["unconditional_top1_wilson_95"][0]
        > metrics["random_choice_expected_accuracy"],
        "prediction_repeat_gate": repeat["prediction_agreement_rate"]
        >= rule["per_model_minimum_prediction_repeat_agreement"],
    }
    return {"passed": all(checks.values()), "checks": checks}


def _expected_selection(gates, paired):
    passing = [model_id for model_id, gate in gates.items() if gate["passed"]]
    if len(passing) == 1:
        return passing[0]
    if len(passing) == 2:
        if (
            paired["exact_two_sided_mcnemar_p_value"] <= 0.05
            and paired["accuracy_delta_qwen25_7b_minus_qwen3_4b"] != 0.0
        ):
            return (
                "qwen25_7b"
                if paired["accuracy_delta_qwen25_7b_minus_qwen3_4b"] > 0
                else "qwen3_4b"
            )
        return "qwen3_4b"
    return None


def verify():
    prereg = base.load_json(construction.PREREGISTRATION_PATH)
    prompts_payload = base.load_json(construction.PROMPTS_PATH)
    labels_payload = base.load_json(construction.LABELS_PATH)
    raw = base.load_json(construction.RAW_RESULT_PATH)
    result = base.load_json(construction.RESULT_PATH)
    prompts = {row["row_id"]: row for row in prompts_payload["rows"]}
    labels = {row["row_id"]: row for row in labels_payload["rows"]}
    checks = {}

    checks["source_and_model_revisions_exact"] = (
        prereg["official_provenance"]["dataset_commit"] == base.HF_DATASET_COMMIT
        and prereg["official_provenance"]["code_commit"]
        == base.OFFICIAL_REPOSITORY_COMMIT
        and all(
            prereg["model_contracts"][model_id]["snapshot_revision"]
            == construction.MODEL_CONTRACTS[model_id]["revision"]
            for model_id in construction.MODEL_ORDER
        )
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
    checks["labels_absent_and_holdout_disjoint"] = (
        len(prompts) == 30
        and set(prompts) == set(labels)
        and all(
            "gt" not in row and "ground_truth" not in row and "label_sha256" not in row
            for row in prompts.values()
        )
        and not {
            (row["track"], row["source_row_index"]) for row in prompts.values()
        }
        & {
            (row["track"], row["source_row_index"])
            for row in base.load_json(base.PROMPTS_PATH)["rows"]
        }
    )
    runtime = raw["runtime_contract"]
    checks["generation_isolation_exact"] = (
        runtime["model_order"] == list(construction.MODEL_ORDER)
        and runtime["system_message"] == construction.SYSTEM_MESSAGE
        and runtime["official_user_prompt_changed"] is False
        and runtime["batch_size"] == 1
        and runtime["temperature"] == 0.0
        and runtime["generation_calls"] == 96
        and runtime["optimizer_created"] is False
        and runtime["optimizer_updates"] == 0
        and runtime["adapter_initialized"] is False
        and runtime["memory_loaded"] is False
        and runtime["persona_prompt_loaded"] is False
        and runtime["labels_loaded_after_both_models_finish"] is True
        and runtime["ground_truth_passed_to_model"] is False
        and runtime["event_order"].index("both_models_all_generation_complete")
        < runtime["event_order"].index("labels_loaded_after_both_models_all_generation")
    )

    recomputed_metrics = {}
    recomputed_repeats = {}
    row_scores_exact = True
    audit_ids = prereg["pilot_design"]["repeat_audit_row_ids"]
    for model_id in construction.MODEL_ORDER:
        primary = raw["models"][model_id]["primary"]
        repeats = raw["models"][model_id]["repeat_audit"]
        if (
            len(primary) != 30
            or {row["row_id"] for row in primary} != set(prompts)
            or len(repeats) != 18
        ):
            row_scores_exact = False
        for row in primary + repeats:
            prompt = prompts[row["row_id"]]
            label = labels[row["row_id"]]
            try:
                probabilities = _parse(row["output"], prompt["options"])
                prediction = max(probabilities, key=probabilities.get)
                parsed = True
            except Exception:
                probabilities = None
                prediction = None
                parsed = False
            correct = prediction == label["ground_truth"]
            if not (
                row["prompt_sha256"] == prompt["prompt_sha256"]
                and row["output_sha256"]
                == hashlib.sha256(row["output"].encode("utf-8")).hexdigest()
                and row["ground_truth"] == label["ground_truth"]
                and row["label_sha256"] == label["label_sha256"]
                and row["parse_success"] == parsed
                and row["prediction"] == prediction
                and row["correct"] == correct
                and row["probabilities"] == probabilities
            ):
                row_scores_exact = False
        recomputed_metrics[model_id] = _aggregate(primary, prompts)
        recomputed_repeats[model_id] = _repeat(primary, repeats, audit_ids, prompts)
    checks["row_scores_exact"] = row_scores_exact

    aggregate_exact = True
    for model_id in construction.MODEL_ORDER:
        stored = result["measurements"]["models"][model_id]["overall"]
        expected = recomputed_metrics[model_id]
        for key, value in expected.items():
            stored_value = stored[key]
            if isinstance(value, list):
                if any(
                    not math.isclose(a, b, abs_tol=1e-12)
                    for a, b in zip(stored_value, value)
                ):
                    aggregate_exact = False
            elif isinstance(value, float):
                if not math.isclose(stored_value, value, abs_tol=1e-12):
                    aggregate_exact = False
            elif stored_value != value:
                aggregate_exact = False
        stored_repeat = result["measurements"]["models"][model_id]["repeat_audit"]
        expected_repeat = recomputed_repeats[model_id]
        for key, value in expected_repeat.items():
            if isinstance(value, float):
                if not math.isclose(stored_repeat[key], value, abs_tol=1e-12):
                    aggregate_exact = False
            elif stored_repeat[key] != value:
                aggregate_exact = False
    checks["aggregate_and_repeat_metrics_exact"] = aggregate_exact

    paired = _paired(
        raw["models"]["qwen3_4b"]["primary"],
        raw["models"]["qwen25_7b"]["primary"],
    )
    stored_paired = result["measurements"]["paired"]
    checks["paired_statistics_exact"] = all(
        math.isclose(stored_paired[key], value, abs_tol=1e-12)
        if isinstance(value, float)
        else stored_paired[key] == value
        for key, value in paired.items()
    )
    gates = {
        model_id: _gate(
            prereg,
            recomputed_metrics[model_id],
            recomputed_repeats[model_id],
            True,
        )
        for model_id in construction.MODEL_ORDER
    }
    selection = _expected_selection(gates, paired)
    decision = result["decision"]
    checks["decision_exact_and_narrow"] = (
        decision["model_gates"] == gates
        and decision["selected_model_for_larger_validation"] == selection
        and decision["passed"] == (selection is not None)
        and decision["authorize_larger_disjoint_official_evaluator_validation"]
        == (selection is not None)
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
        "schema": "personaeval_local_judge_model_selection_verification_v1",
        "experiment_id": construction.EXPERIMENT_ID,
        "passed": passed,
        "checks": checks,
        "recomputed": {
            "models": {
                model_id: {
                    **recomputed_metrics[model_id],
                    "repeat_prediction_agreement": recomputed_repeats[model_id][
                        "prediction_agreement_rate"
                    ],
                }
                for model_id in construction.MODEL_ORDER
            },
            "paired": paired,
            "model_gates": gates,
            "selected_model": selection,
        },
        "verified_authorization": {
            "larger_disjoint_official_evaluator_validation": selection is not None,
            "target_person_judging": False,
            "human_rater_replacement": False,
            "training": False,
            "production": False,
        },
    }
    base.atomic_json(construction.VERIFICATION_JSON_PATH, verification)
    lines = [
        "# PersonaEval local judge model-selection verification",
        "",
        f"- Independent verification passed: `{passed}`",
    ]
    for model_id in construction.MODEL_ORDER:
        metrics = recomputed_metrics[model_id]
        repeat = recomputed_repeats[model_id]
        lines.extend(
            [
                f"- `{model_id}` parse: `{metrics['parsed_count']}/30`",
                f"- `{model_id}` correct: `{metrics['correct_count']}/30`",
                f"- `{model_id}` repeat agreement: `{repeat['prediction_agreement_count']}/9`",
            ]
        )
    lines.extend(
        [
            f"- Selected model: `{selection}`",
            "- Target-person / human replacement / training / production: `False`",
            "",
        ]
    )
    base.atomic_text(construction.VERIFICATION_MD_PATH, "\n".join(lines))
    return verification


def main():
    result = verify()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
