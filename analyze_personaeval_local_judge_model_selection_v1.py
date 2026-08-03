#!/usr/bin/env python3
"""Produce a post-hoc failure analysis without modifying formal scores."""

from __future__ import annotations

import json
import math
import re
import sys

import build_personaeval_local_judge_model_selection_v1 as construction
import build_personaeval_qwen3_official_pilot_v1 as base


ANALYSIS_JSON_PATH = (
    construction.ROOT
    / "reports/personaeval_local_judge_model_selection_v1_failure_analysis.json"
)
ANALYSIS_MD_PATH = (
    construction.ROOT
    / "reports/personaeval_local_judge_model_selection_v1_failure_analysis.md"
)

if str(base.JSON_REPAIR_TARGET) not in sys.path:
    sys.path.insert(0, str(base.JSON_REPAIR_TARGET))
import json_repair  # noqa: E402


def _json_object(output):
    matches = re.findall(r"```\s*(.+?)\s*```", output, re.DOTALL)
    value = json_repair.loads(matches[-1] if matches else output)
    if not isinstance(value, dict):
        raise ValueError("not an object")
    return value


def _lenient_rank(row, prompt, label):
    try:
        value = _json_object(row["output"])
        scores = {option: float(value[option]) for option in prompt["options"]}
        if not all(math.isfinite(score) for score in scores.values()):
            raise ValueError("non-finite score")
        prediction = max(scores, key=scores.get)
        return {
            "available": True,
            "prediction": prediction,
            "correct": prediction == label["ground_truth"],
            "official_option_score_sum": sum(scores.values()),
            "extra_keys": sorted(set(value) - set(prompt["options"])),
        }
    except Exception as exc:
        return {
            "available": False,
            "prediction": None,
            "correct": False,
            "error": f"{type(exc).__name__}: {exc}",
        }


def _failure_category(row, lenient):
    if row["parse_success"]:
        return None
    if not lenient["available"]:
        return "non_object_missing_key_or_truncated"
    if lenient.get("extra_keys"):
        return "probability_sum_mismatch_with_extra_keys"
    return "probability_sum_mismatch"


def analyze():
    raw = base.load_json(construction.RAW_RESULT_PATH)
    formal = base.load_json(construction.RESULT_PATH)
    prompts = {
        row["row_id"]: row for row in base.load_json(construction.PROMPTS_PATH)["rows"]
    }
    labels = {
        row["row_id"]: row for row in base.load_json(construction.LABELS_PATH)["rows"]
    }
    models = {}
    for model_id in construction.MODEL_ORDER:
        rows = raw["models"][model_id]["primary"]
        diagnostics = []
        categories = {}
        for row in rows:
            lenient = _lenient_rank(row, prompts[row["row_id"]], labels[row["row_id"]])
            category = _failure_category(row, lenient)
            if category:
                categories[category] = categories.get(category, 0) + 1
            diagnostics.append(
                {
                    "row_id": row["row_id"],
                    "track": row["track"],
                    "strict_parse_success": row["parse_success"],
                    "strict_correct": row["correct"],
                    "strict_parse_error": row["parse_error"],
                    "failure_category": category,
                    "lenient_rank_diagnostic": lenient,
                }
            )
        repeat = formal["measurements"]["models"][model_id]["repeat_audit"]
        resource = formal["measurements"]["models"][model_id]["resource"]
        models[model_id] = {
            "formal": {
                "parsed_count": sum(row["parse_success"] for row in rows),
                "correct_count": sum(row["correct"] for row in rows),
                "accuracy": sum(row["correct"] for row in rows) / len(rows),
                "gate_passed": formal["decision"]["model_gates"][model_id]["passed"],
            },
            "posthoc_lenient_rank_diagnostic": {
                "available_count": sum(
                    row["lenient_rank_diagnostic"]["available"] for row in diagnostics
                ),
                "correct_count": sum(
                    row["lenient_rank_diagnostic"]["correct"] for row in diagnostics
                ),
                "accuracy_all_primary_rows": sum(
                    row["lenient_rank_diagnostic"]["correct"] for row in diagnostics
                )
                / len(rows),
                "changes_formal_score": False,
            },
            "strict_parse_failure_categories": categories,
            "repeat": {
                "exact_output_agreement": repeat["exact_output_agreement_rate"],
                "strict_prediction_agreement": repeat["prediction_agreement_rate"],
            },
            "resource": {
                "duration_seconds": resource["duration_seconds"],
                "peak_memory_bytes": resource["mlx_peak_memory_bytes"],
            },
            "rows": diagnostics,
        }
    report = {
        "schema": "personaeval_local_judge_model_selection_failure_analysis_v1",
        "experiment_id": construction.EXPERIMENT_ID,
        "status": "posthoc_diagnostic_not_formal_rescoring",
        "formal_result_sha256": base.sha256_file(construction.RESULT_PATH),
        "formal_result_modified": False,
        "models": models,
        "paired_formal": {
            key: formal["measurements"]["paired"][key]
            for key in (
                "both_correct",
                "qwen3_4b_only_correct",
                "qwen25_7b_only_correct",
                "neither_correct",
                "exact_two_sided_mcnemar_p_value",
                "accuracy_delta_qwen25_7b_minus_qwen3_4b",
            )
        },
        "findings": [
            "Increasing parameters from 4B to 7B did not improve formal accuracy.",
            "Both models produced deterministic repeated text on all nine audit rows.",
            "Strict prediction agreement failed because one deterministic output per model was unparseable.",
            "Most strict parser failures retained all official candidate scores and therefore support testing an answer-ranking interface on a new disjoint holdout.",
        ],
        "next_experiment_boundary": {
            "recommended_independent_variable": "strict_probability_contract_vs_preregistered_candidate_rank_contract",
            "must_use_new_disjoint_rows": True,
            "may_not_change_formal_scores": True,
            "may_not_authorize_target_person_judging": True,
        },
    }
    base.atomic_json(ANALYSIS_JSON_PATH, report)
    lines = [
        "# PersonaEval local judge model-selection failure analysis",
        "",
        "This is a post-hoc diagnostic. Formal scores and gates are unchanged.",
        "",
    ]
    for model_id in construction.MODEL_ORDER:
        model = models[model_id]
        lines.extend(
            [
                f"- `{model_id}` formal: `{model['formal']['correct_count']}/30`",
                f"- `{model_id}` strict parse: `{model['formal']['parsed_count']}/30`",
                f"- `{model_id}` post-hoc rank diagnostic: `{model['posthoc_lenient_rank_diagnostic']['correct_count']}/30`",
                f"- `{model_id}` exact repeated text: `{model['repeat']['exact_output_agreement']:.3f}`",
            ]
        )
    lines.extend(
        [
            "- Formal selected model: `None`",
            "- Next valid experiment: new disjoint rows with one preregistered answer-ranking contract.",
            "- Target-person / human replacement / training / production authorization: `False`",
            "",
        ]
    )
    base.atomic_text(ANALYSIS_MD_PATH, "\n".join(lines))
    return report


def main():
    report = analyze()
    print(
        json.dumps(
            {
                model_id: report["models"][model_id][
                    "posthoc_lenient_rank_diagnostic"
                ]
                for model_id in construction.MODEL_ORDER
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
