#!/usr/bin/env python3
"""Run the frozen paired local-model QA evaluation with resumable checkpoints."""

from __future__ import annotations

import json
import os
import random
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

import build_source_preserving_memory_projection_v2_5_locomo_cases as v25
import build_source_preserving_memory_projection_v2_10_final_reserve as v210


ROOT = Path(__file__).resolve().parent
PREREG = ROOT / "configs/source_preserving_memory_projection_v2_11_model_qa_preregistration.json"


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_preregistration(path=PREREG):
    return load_json(path)


def verify_frozen_inputs(contract):
    for section in (
        "deterministic_authorization",
        "frozen_case_reconstruction",
        "frozen_local_implementation",
    ):
        values = contract[section]
        for key, relative in values.items():
            if not key.endswith("_path"):
                continue
            expected = values[key.replace("_path", "_sha256")]
            if v25.file_sha256(ROOT / relative) != expected:
                raise ValueError(f"frozen artifact hash drift: {relative}")


def verify_official_scorer_runtime(contract):
    runtime = contract["official_scorer_runtime"]
    expected_python = Path(runtime["python"]).absolute()
    actual_python = Path(sys.executable).absolute()
    if actual_python != expected_python:
        raise ValueError(
            f"official scorer Python drift: expected {expected_python}, got {actual_python}"
        )
    for distribution in ("regex", "nltk", "numpy"):
        actual = version(distribution)
        expected = runtime[f"{distribution}_version"]
        if actual != expected:
            raise ValueError(
                f"official scorer runtime drift: {distribution} {actual} != {expected}"
            )


def installed_models(endpoint):
    url = endpoint.rsplit("/api/", 1)[0] + "/api/tags"
    with urllib.request.urlopen(url, timeout=30) as response:
        return json.load(response).get("models") or []


def verify_local_model(contract):
    model = contract["local_model"]
    matched = next(
        (row for row in installed_models(model["endpoint"]) if row.get("name") == model["model"]),
        None,
    )
    if not matched:
        raise ValueError(f"missing local model: {model['model']}")
    if matched.get("digest") != model["ollama_manifest_sha256"]:
        raise ValueError("local model digest drift")


def final_case_specs(data, contract):
    v210_prereg = v210.load_preregistration()
    final_samples, final_ids = v210.final_reserve_samples(data, v210_prereg)
    aliases = {
        f"final-reserve-{index + 1}": sample
        for index, sample in enumerate(final_samples)
    }
    frozen = load_json(ROOT / contract["deterministic_authorization"]["report_path"])
    specs = []
    for case in frozen["cases"]:
        sample = aliases[case["sample_id"]]
        qa = sample["qa"][case["qa_index"]]
        question = str(qa["question"])
        answer = str(qa["answer"])
        if v25.text_sha256(question) != case["question_sha256"]:
            raise ValueError(f"question hash drift: {case['case_id']}")
        contexts = {}
        for representation in ("isolated", "adjacency"):
            contexts[representation] = v25.serialize_session(
                sample["conversation"],
                case["target_session"],
                case[representation]["source_turn_indices"],
            )
            if v25.text_sha256(contexts[representation]) != case[representation][
                "projection_text_sha256"
            ]:
                raise ValueError(
                    f"projection hash drift: {case['case_id']}:{representation}"
                )
        specs.append(
            {
                "case_id": case["case_id"],
                "sample_alias": case["sample_id"],
                "qa_index": case["qa_index"],
                "question": question,
                "answer": answer,
                "speaker_a": str(sample["conversation"].get("speaker_a") or "Speaker A"),
                "speaker_b": str(sample["conversation"].get("speaker_b") or "Speaker B"),
                "contexts": contexts,
                "evidence_transition": (
                    "adjacency_only"
                    if case["adjacency"]["contains_all_official_evidence"]
                    and not case["isolated"]["contains_all_official_evidence"]
                    else "isolated_only"
                    if case["isolated"]["contains_all_official_evidence"]
                    and not case["adjacency"]["contains_all_official_evidence"]
                    else "both"
                    if case["isolated"]["contains_all_official_evidence"]
                    else "neither"
                ),
            }
        )
    if len(specs) != contract["deterministic_authorization"]["case_count"]:
        raise ValueError("frozen case count drift")
    if v25.canonical_sha256(final_ids) != frozen["scope"]["final_reserve_sample_ids_sha256"]:
        raise ValueError("final reserve ID hash drift")
    return specs


def build_prompt(case, representation, contract):
    prompt = contract["prompt"]
    return (
        prompt["context_header"].format(case["speaker_a"], case["speaker_b"])
        + case["contexts"][representation]
        + prompt["qa_template"].format(case["question"])
    )


def post_json(url, payload, timeout):
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def call_model(prompt, contract):
    model = contract["local_model"]
    payload = {
        "model": model["model"],
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "think": model["think"],
        "options": {
            "temperature": model["temperature"],
            "seed": model["seed"],
            "num_ctx": model["num_ctx"],
            "num_predict": model["num_predict"],
        },
    }
    started = time.perf_counter()
    response = post_json(model["endpoint"], payload, model["timeout_seconds"])
    elapsed = time.perf_counter() - started
    return {
        "prediction": str((response.get("message") or {}).get("content") or "").strip(),
        "prompt_eval_count": response.get("prompt_eval_count"),
        "eval_count": response.get("eval_count"),
        "total_duration_ns": response.get("total_duration"),
        "latency_seconds": round(elapsed, 6),
    }


def official_f1(prediction, answer):
    from locomo_official_qa_f1 import f1_score

    return f1_score(prediction, answer)


def planned_calls(cases):
    calls = []
    for index, case in enumerate(cases):
        order = ("isolated", "adjacency") if index % 2 == 0 else ("adjacency", "isolated")
        for representation in order:
            calls.append((case, representation))
    return calls


def load_checkpoint(path):
    if not path.exists():
        return {}
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    by_id = {}
    for row in rows:
        call_id = row["call_id"]
        if call_id in by_id:
            raise ValueError(f"duplicate completed call ID: {call_id}")
        by_id[call_id] = row
    return by_id


def append_checkpoint(path, row):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def execute_calls(cases, contract, raw_path, model_call=call_model, score_fn=official_f1):
    completed = load_checkpoint(raw_path)
    contract_sha256 = v25.file_sha256(PREREG)
    for case, representation in planned_calls(cases):
        call_id = f"{case['case_id']}:{representation}"
        if call_id in completed:
            if completed[call_id]["contract_sha256"] != contract_sha256:
                raise ValueError(f"checkpoint contract drift: {call_id}")
            continue
        prompt = build_prompt(case, representation, contract)
        try:
            generated = model_call(prompt, contract)
            error = None
        except Exception as exc:
            generated = {
                "prediction": "",
                "prompt_eval_count": None,
                "eval_count": None,
                "total_duration_ns": None,
                "latency_seconds": None,
            }
            error = f"{type(exc).__name__}: {exc}"
        row = {
            "call_id": call_id,
            "case_id": case["case_id"],
            "sample_alias": case["sample_alias"],
            "qa_index": case["qa_index"],
            "representation": representation,
            "evidence_transition": case["evidence_transition"],
            "prompt_sha256": v25.text_sha256(prompt),
            "official_answer_sha256": v25.text_sha256(case["answer"]),
            "prediction": generated["prediction"],
            "official_f1": score_fn(generated["prediction"], case["answer"])
            if error is None
            else 0.0,
            "transport_error": error,
            "prompt_eval_count": generated["prompt_eval_count"],
            "eval_count": generated["eval_count"],
            "total_duration_ns": generated["total_duration_ns"],
            "latency_seconds": generated["latency_seconds"],
            "contract_sha256": contract_sha256,
            "production_memory_write_count": 0,
            "physical_vrm_action_count": 0,
        }
        append_checkpoint(raw_path, row)
        completed[call_id] = row
    return list(completed.values())


def percentile(values, quantile):
    ordered = sorted(values)
    if not ordered:
        return 0.0
    position = (len(ordered) - 1) * quantile
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def paired_bootstrap(deltas, samples, seed):
    randomizer = random.Random(seed)
    means = []
    for _ in range(samples):
        means.append(sum(randomizer.choice(deltas) for _ in deltas) / len(deltas))
    return percentile(means, 0.025), percentile(means, 0.975)


def mean(values):
    return sum(values) / len(values) if values else 0.0


def analyze_rows(rows, contract):
    by_case = {}
    for row in rows:
        by_case.setdefault(row["case_id"], {})[row["representation"]] = row
    complete = {
        case_id: conditions
        for case_id, conditions in by_case.items()
        if set(conditions) == {"isolated", "adjacency"}
    }
    deltas = [
        conditions["adjacency"]["official_f1"]
        - conditions["isolated"]["official_f1"]
        for conditions in complete.values()
    ]
    isolated = [conditions["isolated"]["official_f1"] for conditions in complete.values()]
    adjacency = [conditions["adjacency"]["official_f1"] for conditions in complete.values()]
    subgroup = [
        delta
        for delta, conditions in zip(deltas, complete.values())
        if conditions["adjacency"]["evidence_transition"] == "adjacency_only"
    ]
    runtime = contract["official_scorer_runtime"]
    lower, upper = paired_bootstrap(
        deltas, runtime["bootstrap_samples"], runtime["bootstrap_seed"]
    ) if deltas else (0.0, 0.0)
    metrics = {
        "model_call_count": len(rows),
        "complete_pair_count": len(complete),
        "row_count_by_condition": {
            representation: sum(row["representation"] == representation for row in rows)
            for representation in ("isolated", "adjacency")
        },
        "transport_error_count": sum(bool(row["transport_error"]) for row in rows),
        "nonempty_prediction_rate": mean([float(bool(row["prediction"])) for row in rows]),
        "isolated_mean_official_f1": round(mean(isolated), 6),
        "adjacency_mean_official_f1": round(mean(adjacency), 6),
        "adjacency_mean_f1_delta_vs_isolated": round(mean(deltas), 6),
        "paired_bootstrap_95_ci": [round(lower, 6), round(upper, 6)],
        "adjacency_only_evidence_gain_subgroup_count": len(subgroup),
        "adjacency_only_evidence_gain_subgroup_f1_delta": round(mean(subgroup), 6),
        "mean_model_output_tokens": round(
            mean([float(row["eval_count"]) for row in rows if row["eval_count"] is not None]),
            6,
        ),
        "production_memory_write_count": sum(
            row["production_memory_write_count"] for row in rows
        ),
        "physical_vrm_action_count": sum(row["physical_vrm_action_count"] for row in rows),
    }
    gates = contract["success_gates"]
    checks = {
        "model_call_count_equals": metrics["model_call_count"]
        == gates["model_call_count_equals"],
        "row_count_per_condition_equals": all(
            count == gates["row_count_per_condition_equals"]
            for count in metrics["row_count_by_condition"].values()
        ),
        "complete_pair_count_equals": metrics["complete_pair_count"]
        == gates["complete_pair_count_equals"],
        "transport_error_count_equals": metrics["transport_error_count"]
        == gates["transport_error_count_equals"],
        "nonempty_prediction_rate_equals": metrics["nonempty_prediction_rate"]
        == gates["nonempty_prediction_rate_equals"],
        "adjacency_mean_official_f1_at_least": metrics["adjacency_mean_official_f1"]
        >= gates["adjacency_mean_official_f1_at_least"],
        "adjacency_mean_f1_delta_vs_isolated_at_least": metrics[
            "adjacency_mean_f1_delta_vs_isolated"
        ]
        >= gates["adjacency_mean_f1_delta_vs_isolated_at_least"],
        "paired_bootstrap_95_ci_lower_greater_than": lower
        > gates["paired_bootstrap_95_ci_lower_greater_than"],
        "adjacency_only_evidence_gain_subgroup_count_equals": metrics[
            "adjacency_only_evidence_gain_subgroup_count"
        ]
        == gates["adjacency_only_evidence_gain_subgroup_count_equals"],
        "adjacency_only_evidence_gain_subgroup_f1_delta_at_least": metrics[
            "adjacency_only_evidence_gain_subgroup_f1_delta"
        ]
        >= gates["adjacency_only_evidence_gain_subgroup_f1_delta_at_least"],
        "mean_model_output_tokens_at_most": metrics["mean_model_output_tokens"]
        <= gates["mean_model_output_tokens_at_most"],
        "production_memory_write_count_equals": metrics["production_memory_write_count"]
        == gates["production_memory_write_count_equals"],
        "physical_vrm_action_count_equals": metrics["physical_vrm_action_count"]
        == gates["physical_vrm_action_count_equals"],
    }
    return metrics, checks


def write_final_outputs(rows, contract, raw_path, metadata_path, report_path, markdown_path):
    metrics, gates = analyze_rows(rows, contract)
    passed = all(gates.values())
    report = {
        "schema": "uruha_source_preserving_memory_projection_model_qa_report_v2_11",
        "experiment_id": contract["experiment_id"],
        "decision": "model_qa_pass_authorize_full_pipeline_preregistration_only"
        if passed
        else "model_qa_reject_adjacency_answer_quality_gain",
        "model": contract["local_model"],
        "official_scoring": contract["official_source"],
        "metrics": metrics,
        "gates": gates,
        "rows": sorted(rows, key=lambda row: row["call_id"]),
        "contains_official_questions": False,
        "contains_official_answers": False,
        "contains_source_context_text": False,
        "authorization": {
            "preregister_full_pipeline_memory_intervention": passed,
            "runtime_change": False,
            "runtime_shadow": False,
            "production_enablement": False,
        },
        "evidence_boundary": contract["evidence_boundary"],
    }
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    metadata = {
        "schema": "uruha_source_preserving_memory_projection_model_qa_run_metadata_v2_11",
        "experiment_id": contract["experiment_id"],
        "run_at": datetime.now(timezone.utc).isoformat(),
        "contract_sha256": v25.file_sha256(PREREG),
        "raw_checkpoint_sha256": v25.file_sha256(raw_path),
        "report_sha256": v25.file_sha256(report_path),
        "decision": report["decision"],
        "model_call_count": metrics["model_call_count"],
    }
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    markdown_path.write_text(
        "\n".join(
            [
                "# V2.11 Paired Local-Model QA",
                "",
                f"**Decision: `{report['decision']}`**",
                "",
                "| Measure | Isolated Top-3 | Adjacency |",
                "|---|---:|---:|",
                f"| Mean official F1 | {metrics['isolated_mean_official_f1']:.3f} | {metrics['adjacency_mean_official_f1']:.3f} |",
                f"| Paired delta | - | {metrics['adjacency_mean_f1_delta_vs_isolated']:+.3f} |",
                f"| 95% bootstrap CI | - | [{metrics['paired_bootstrap_95_ci'][0]:+.3f}, {metrics['paired_bootstrap_95_ci'][1]:+.3f}] |",
                "",
                contract["evidence_boundary"],
                "",
            ]
        ),
        encoding="utf-8",
    )
    return metadata


def main():
    contract = load_preregistration()
    execution = contract["execution"]
    raw_path = ROOT / execution["raw_checkpoint_path"]
    metadata_path = ROOT / execution["metadata_path"]
    report_path = ROOT / execution["report_json_path"]
    markdown_path = ROOT / execution["report_markdown_path"]
    if metadata_path.exists() or report_path.exists() or markdown_path.exists():
        raise SystemExit("V2.11 final output exists; refusing to rerun")
    verify_frozen_inputs(contract)
    verify_official_scorer_runtime(contract)
    verify_local_model(contract)
    source_prereg = v25.load_preregistration()
    data = v25.ensure_official_dataset(source_prereg)
    cases = final_case_specs(data, contract)
    rows = execute_calls(cases, contract, raw_path)
    metadata = write_final_outputs(
        rows, contract, raw_path, metadata_path, report_path, markdown_path
    )
    print(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
