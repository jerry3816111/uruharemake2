#!/usr/bin/env python3
"""Diagnose failed PersonaEval repeat rows with batch size one and no labels."""

from __future__ import annotations

import copy
import json
import resource
import time
from pathlib import Path

import mlx.core as mx
from mlx_lm import load

import build_personaeval_qwen3_official_pilot_v1 as construction
import run_personaeval_qwen3_official_pilot_v1 as runner


ROOT = Path(__file__).resolve().parent
DIAGNOSTIC_PATH = (
    ROOT / "reports/personaeval_qwen3_official_pilot_v1_batch1_diagnostic.json"
)
DIAGNOSTIC_MD_PATH = (
    ROOT / "reports/personaeval_qwen3_official_pilot_v1_batch1_diagnostic.md"
)


def _diagnose_output(output, prompt):
    try:
        probabilities = runner.parse_official_probability_response(
            output["output"], prompt["options"]
        )
        return {
            **output,
            "parse_success": True,
            "parse_error": None,
            "prediction": runner._prediction(probabilities),
            "probabilities": probabilities,
        }
    except Exception as exc:
        return {
            **output,
            "parse_success": False,
            "parse_error": f"{type(exc).__name__}: {exc}",
            "prediction": None,
            "probabilities": None,
        }


def run():
    if DIAGNOSTIC_PATH.exists() or DIAGNOSTIC_MD_PATH.exists():
        raise RuntimeError("refusing to overwrite existing batch-one diagnostic")
    formal_result = construction.load_json(construction.RESULT_PATH)
    prompts_payload = construction.load_json(construction.PROMPTS_PATH)
    if any("ground_truth" in row or "gt" in row for row in prompts_payload["rows"]):
        raise RuntimeError("prompt file unexpectedly contains labels")
    prompts = {row["row_id"]: runner._prompt_case(row) for row in prompts_payload["rows"]}
    failed_repeat_rows = [
        row
        for row in formal_result["measurements"]["repeat_audit"]["details"]
        if not row["prediction_agreement"]
    ]
    if not failed_repeat_rows:
        raise RuntimeError("formal result has no failed repeat rows to diagnose")

    preregistration = construction.load_json(construction.PREREGISTRATION_PATH)
    diagnostic_preregistration = copy.deepcopy(preregistration)
    diagnostic_preregistration["controlled_variables"]["batch_size"] = 1
    mx.set_default_device(mx.gpu)
    mx.set_memory_limit(32212254720)
    mx.set_wired_limit(22906503168)
    mx.reset_peak_memory()
    model, tokenizer = load(
        preregistration["model_contract"]["snapshot_root"],
        tokenizer_config={"trust_remote_code": True},
    )
    model.eval()
    mx.eval(model.parameters())

    started = time.perf_counter()
    generated = []
    for repetition in range(1, 4):
        for failed in failed_repeat_rows:
            row_id = failed["row_id"]
            output = runner._generate_cases(
                model,
                tokenizer,
                [prompts[row_id]],
                diagnostic_preregistration,
                phase="posthoc_batch1_diagnostic",
                repetition=repetition,
            )[0]
            generated.append(_diagnose_output(output, prompts[row_id]))

    rows = []
    for failed in failed_repeat_rows:
        row_id = failed["row_id"]
        repeats = [row for row in generated if row["row_id"] == row_id]
        hashes = [row["output_sha256"] for row in repeats]
        predictions = [row["prediction"] for row in repeats]
        all_parsed = all(row["parse_success"] for row in repeats)
        exact_output_agreement = len(set(hashes)) == 1
        prediction_agreement = all_parsed and len(set(predictions)) == 1
        rows.append(
            {
                "row_id": row_id,
                "track": prompts[row_id]["track"],
                "formal_batch_size_4": {
                    "exact_output_agreement": failed["exact_output_agreement"],
                    "all_repetitions_parsed": failed["all_repetitions_parsed"],
                    "prediction_agreement": failed["prediction_agreement"],
                    "predictions": failed["predictions"],
                    "output_sha256": failed["output_sha256"],
                },
                "diagnostic_batch_size_1": {
                    "exact_output_agreement": exact_output_agreement,
                    "all_repetitions_parsed": all_parsed,
                    "prediction_agreement": prediction_agreement,
                    "predictions": predictions,
                    "output_sha256": hashes,
                    "repetitions": repeats,
                },
                "batch_composition_effect_supported": (
                    not failed["prediction_agreement"] and prediction_agreement
                ),
                "persistent_output_contract_failure": (
                    exact_output_agreement and not all_parsed
                ),
            }
        )

    report = {
        "schema": "personaeval_qwen3_batch1_diagnostic_v1",
        "experiment_id": construction.EXPERIMENT_ID,
        "status": "posthoc_diagnostic_not_formal_rescoring",
        "trigger": "all formal repeat-audit rows with prediction_agreement=false",
        "independent_variable": "batch_size_4_to_1",
        "controls_held_constant": [
            "model snapshot",
            "official user prompt",
            "generic JSON-only system transport adapter",
            "greedy decoding",
            "maximum_new_tokens=256",
            "prompt rows",
            "parser",
        ],
        "formal_result_sha256": construction.sha256_file(construction.RESULT_PATH),
        "formal_result_modified": False,
        "labels_loaded": False,
        "ground_truth_passed_to_model": False,
        "training_updates": 0,
        "diagnostic_repetitions": 3,
        "rows": rows,
        "summary": {
            "diagnosed_row_count": len(rows),
            "batch_composition_effect_rows": sum(
                row["batch_composition_effect_supported"] for row in rows
            ),
            "persistent_output_contract_failure_rows": sum(
                row["persistent_output_contract_failure"] for row in rows
            ),
            "authorizes_formal_score_change": False,
            "authorizes_larger_personaeval_validation": False,
            "authorizes_target_person_judging": False,
        },
        "resource": {
            "duration_seconds": round(time.perf_counter() - started, 3),
            "mlx_peak_memory_bytes": mx.get_peak_memory(),
            "process_peak_resident_memory_bytes": resource.getrusage(
                resource.RUSAGE_SELF
            ).ru_maxrss,
        },
    }
    construction.atomic_json(DIAGNOSTIC_PATH, report)
    markdown = [
        "# PersonaEval batch-size diagnostic",
        "",
        "- This is a post-hoc mechanism diagnostic, not a formal rescore.",
        "- Only batch size changed from 4 to 1; labels were not loaded.",
        f"- Diagnosed failed repeat rows: `{len(rows)}`",
        f"- Batch-composition effect supported: `{report['summary']['batch_composition_effect_rows']}`",
        f"- Persistent output-contract failure: `{report['summary']['persistent_output_contract_failure_rows']}`",
        "- Formal score and authorization remain unchanged.",
        "",
    ]
    for row in rows:
        markdown.append(
            f"- `{row['row_id']}`: batch-effect=`{row['batch_composition_effect_supported']}`, "
            f"persistent-contract-failure=`{row['persistent_output_contract_failure']}`"
        )
    markdown.append("")
    construction.atomic_text(DIAGNOSTIC_MD_PATH, "\n".join(markdown))
    return report


def main():
    report = run()
    print(json.dumps(report["summary"], indent=2))


if __name__ == "__main__":
    main()
