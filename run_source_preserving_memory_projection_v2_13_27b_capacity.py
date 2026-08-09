#!/usr/bin/env python3
"""Run the exposed Qwen3.5 9B-to-27B model-capacity screen."""

from __future__ import annotations

import json
import os
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import build_source_preserving_memory_projection_v2_5_locomo_cases as v25
import run_source_preserving_memory_projection_v2_11_model_qa as v211
import run_source_preserving_memory_projection_v2_12_complete_session_ceiling as v212


ROOT = Path(__file__).resolve().parent
PREREG = ROOT / "configs/source_preserving_memory_projection_v2_13_27b_capacity_preregistration.json"
CONTROL = "qwen3.5:9b"
CANDIDATE = "qwen3.5:27b"


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_preregistration(path=PREREG):
    return load_json(path)


def verify_frozen_inputs(contract):
    for section in (
        "development_authorization",
        "frozen_case_and_prompt_implementation",
        "frozen_local_implementation",
    ):
        values = contract[section]
        for key, relative in values.items():
            if not key.endswith("_path"):
                continue
            expected = values[key.replace("_path", "_sha256")]
            if v25.file_sha256(ROOT / relative) != expected:
                raise ValueError(f"frozen artifact hash drift: {relative}")


def verify_candidate_model(contract):
    candidate = contract["candidate_model"]
    matched = next(
        (
            row
            for row in v211.installed_models(candidate["endpoint"])
            if row.get("name") == candidate["model"]
        ),
        None,
    )
    if not matched:
        raise ValueError(f"missing local model: {candidate['model']}")
    if matched.get("digest") != candidate["ollama_manifest_sha256"]:
        raise ValueError("candidate model digest drift")
    if matched.get("size") != candidate["model_size_bytes"]:
        raise ValueError("candidate model size drift")
    details = matched.get("details") or {}
    if details.get("parameter_size") != candidate["parameter_size"]:
        raise ValueError("candidate parameter-size drift")
    if details.get("quantization_level") != candidate["quantization"]:
        raise ValueError("candidate quantization drift")


def running_models(endpoint):
    url = endpoint.rsplit("/api/", 1)[0] + "/api/ps"
    with urllib.request.urlopen(url, timeout=30) as response:
        return json.load(response).get("models") or []


def verify_candidate_model_unloaded(contract):
    candidate = contract["candidate_model"]
    loaded = {
        str(row.get("name") or row.get("model") or "")
        for row in running_models(candidate["endpoint"])
    }
    if candidate["model"] in loaded:
        raise ValueError(
            "candidate model is already loaded; cold-start latency would be hidden"
        )


def reconstruct_cases_and_controls(contract):
    v212_contract = v212.load_preregistration(
        ROOT
        / contract["frozen_case_and_prompt_implementation"][
            "v2_12_preregistration_path"
        ]
    )
    data = v25.ensure_official_dataset(v25.load_preregistration())
    cases = v212.final_case_specs(data, v212_contract)
    report = load_json(ROOT / contract["development_authorization"]["v2_12_report_path"])
    controls = {
        row["case_id"]: row
        for row in report["rows"]
        if row["representation"] == "complete_session"
    }
    expected = contract["development_authorization"]["locked_control_case_count"]
    if len(cases) != expected or len(controls) != expected:
        raise ValueError("V2.13 case or historical-control count drift")
    v212_contract_hash = contract["frozen_case_and_prompt_implementation"][
        "v2_12_preregistration_sha256"
    ]
    for case in cases:
        control = controls[case["case_id"]]
        prompt = v212.build_prompt(case, "complete_session", v212_contract)
        if control["prompt_sha256"] != v25.text_sha256(prompt):
            raise ValueError(f"historical control prompt drift: {case['case_id']}")
        if control["official_answer_sha256"] != v25.text_sha256(case["answer"]):
            raise ValueError(f"historical control answer drift: {case['case_id']}")
        if control["contract_sha256"] != v212_contract_hash:
            raise ValueError(f"historical control contract drift: {case['case_id']}")
    return cases, controls, v212_contract


def post_json(url, payload, timeout):
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def call_candidate_model(prompt, contract):
    candidate = contract["candidate_model"]
    payload = {
        "model": candidate["model"],
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "think": candidate["think"],
        "keep_alive": candidate["keep_alive"],
        "options": {
            "temperature": candidate["temperature"],
            "seed": candidate["seed"],
            "num_ctx": candidate["num_ctx"],
            "num_predict": candidate["num_predict"],
        },
    }
    started = time.perf_counter()
    response = post_json(
        candidate["endpoint"], payload, candidate["timeout_seconds"]
    )
    elapsed = time.perf_counter() - started
    return {
        "prediction": str((response.get("message") or {}).get("content") or "").strip(),
        "prompt_eval_count": response.get("prompt_eval_count"),
        "eval_count": response.get("eval_count"),
        "load_duration_ns": response.get("load_duration"),
        "prompt_eval_duration_ns": response.get("prompt_eval_duration"),
        "eval_duration_ns": response.get("eval_duration"),
        "total_duration_ns": response.get("total_duration"),
        "latency_seconds": round(elapsed, 6),
    }


def load_checkpoint(path):
    if not path.exists():
        return {}
    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]
    completed = {}
    for row in rows:
        call_id = row["call_id"]
        if call_id in completed:
            raise ValueError(f"duplicate completed candidate call ID: {call_id}")
        completed[call_id] = row
    return completed


def append_checkpoint(path, row):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def execute_candidate_calls(
    cases,
    contract,
    v212_contract,
    raw_path,
    model_call=call_candidate_model,
    score_fn=v211.official_f1,
):
    completed = load_checkpoint(raw_path)
    contract_sha256 = v25.file_sha256(PREREG)
    for case in cases:
        call_id = f"{case['case_id']}:{CANDIDATE}"
        if call_id in completed:
            if completed[call_id]["contract_sha256"] != contract_sha256:
                raise ValueError(f"checkpoint contract drift: {call_id}")
            continue
        prompt = v212.build_prompt(case, "complete_session", v212_contract)
        try:
            generated = model_call(prompt, contract)
            error = None
        except Exception as exc:
            generated = {
                "prediction": "",
                "prompt_eval_count": None,
                "eval_count": None,
                "load_duration_ns": None,
                "prompt_eval_duration_ns": None,
                "eval_duration_ns": None,
                "total_duration_ns": None,
                "latency_seconds": None,
            }
            error = f"{type(exc).__name__}: {exc}"
        row = {
            "call_id": call_id,
            "case_id": case["case_id"],
            "sample_alias": case["sample_alias"],
            "qa_index": case["qa_index"],
            "model_condition": CANDIDATE,
            "row_source": "fresh_v2_13_candidate_call",
            "representation": "complete_session",
            "prompt_sha256": v25.text_sha256(prompt),
            "official_answer_sha256": v25.text_sha256(case["answer"]),
            "prediction": generated["prediction"],
            "official_f1": score_fn(generated["prediction"], case["answer"])
            if error is None
            else 0.0,
            "transport_error": error,
            "prompt_eval_count": generated["prompt_eval_count"],
            "eval_count": generated["eval_count"],
            "load_duration_ns": generated["load_duration_ns"],
            "prompt_eval_duration_ns": generated["prompt_eval_duration_ns"],
            "eval_duration_ns": generated["eval_duration_ns"],
            "total_duration_ns": generated["total_duration_ns"],
            "latency_seconds": generated["latency_seconds"],
            "contract_sha256": contract_sha256,
            "production_memory_write_count": 0,
            "physical_vrm_action_count": 0,
        }
        append_checkpoint(raw_path, row)
        completed[call_id] = row
    return list(completed.values())


def combined_rows(cases, controls, candidate_rows, contract):
    candidate_by_case = {row["case_id"]: row for row in candidate_rows}
    rows = []
    for case in cases:
        control = dict(controls[case["case_id"]])
        control.update(
            {
                "model_condition": CONTROL,
                "row_source": "locked_v2_12_historical_control",
            }
        )
        rows.extend((control, candidate_by_case[case["case_id"]]))
    return rows


def analyze_rows(rows, contract):
    by_case = {}
    for row in rows:
        by_case.setdefault(row["case_id"], {})[row["model_condition"]] = row
    complete_pairs = {
        case_id: conditions
        for case_id, conditions in by_case.items()
        if set(conditions) == {CONTROL, CANDIDATE}
    }
    control_scores = [
        conditions[CONTROL]["official_f1"] for conditions in complete_pairs.values()
    ]
    candidate_scores = [
        conditions[CANDIDATE]["official_f1"] for conditions in complete_pairs.values()
    ]
    deltas = [
        candidate - control
        for control, candidate in zip(control_scores, candidate_scores)
    ]
    candidate_rows = [row for row in rows if row["model_condition"] == CANDIDATE]
    control_rows = [row for row in rows if row["model_condition"] == CONTROL]
    candidate_latencies = [
        float(row["latency_seconds"])
        for row in candidate_rows
        if row["latency_seconds"] is not None
    ]
    prompt_counts = [
        row["prompt_eval_count"]
        for row in candidate_rows
        if row["prompt_eval_count"] is not None
    ]
    output_counts = [
        float(row["eval_count"])
        for row in candidate_rows
        if row["eval_count"] is not None
    ]
    candidate_mean = v211.mean(candidate_scores)
    control_mean = v211.mean(control_scores)
    delta_mean = v211.mean(deltas)
    latency_mean = v211.mean(candidate_latencies)
    latency_p95 = v211.percentile(candidate_latencies, 0.95)
    latency_max = max(candidate_latencies) if candidate_latencies else 0.0
    output_mean = v211.mean(output_counts)
    runtime = contract["official_scorer_runtime"]
    lower, upper = (
        v211.paired_bootstrap(
            deltas, runtime["bootstrap_samples"], runtime["bootstrap_seed"]
        )
        if deltas
        else (0.0, 0.0)
    )
    metrics = {
        "new_candidate_model_call_count": len(candidate_rows),
        "historical_control_row_count": len(control_rows),
        "combined_row_count": len(rows),
        "complete_pair_count": len(complete_pairs),
        "candidate_transport_error_count": sum(
            bool(row["transport_error"]) for row in candidate_rows
        ),
        "candidate_nonempty_prediction_rate": round(
            v211.mean([float(bool(row["prediction"])) for row in candidate_rows]), 6
        ),
        "locked_9b_mean_official_f1": round(control_mean, 6),
        "candidate_27b_mean_official_f1": round(candidate_mean, 6),
        "candidate_mean_f1_delta_vs_locked_9b": round(delta_mean, 6),
        "paired_bootstrap_95_ci": [round(lower, 6), round(upper, 6)],
        "candidate_max_prompt_eval_count": max(prompt_counts) if prompt_counts else 0,
        "candidate_mean_output_tokens": round(output_mean, 6),
        "candidate_mean_latency_seconds": round(latency_mean, 6),
        "candidate_p95_latency_seconds": round(latency_p95, 6),
        "candidate_max_latency_seconds": round(latency_max, 6),
        "candidate_model_size_bytes": contract["candidate_model"]["model_size_bytes"],
        "production_memory_write_count": sum(
            row["production_memory_write_count"] for row in rows
        ),
        "physical_vrm_action_count": sum(
            row["physical_vrm_action_count"] for row in rows
        ),
    }
    thresholds = contract["success_gates"]
    gates = {
        "new_candidate_model_call_count_equals": metrics[
            "new_candidate_model_call_count"
        ]
        == thresholds["new_candidate_model_call_count_equals"],
        "historical_control_row_count_equals": metrics["historical_control_row_count"]
        == thresholds["historical_control_row_count_equals"],
        "combined_row_count_equals": metrics["combined_row_count"]
        == thresholds["combined_row_count_equals"],
        "complete_pair_count_equals": metrics["complete_pair_count"]
        == thresholds["complete_pair_count_equals"],
        "candidate_transport_error_count_equals": metrics[
            "candidate_transport_error_count"
        ]
        == thresholds["candidate_transport_error_count_equals"],
        "candidate_nonempty_prediction_rate_equals": metrics[
            "candidate_nonempty_prediction_rate"
        ]
        == thresholds["candidate_nonempty_prediction_rate_equals"],
        "candidate_mean_official_f1_at_least": candidate_mean
        >= thresholds["candidate_mean_official_f1_at_least"],
        "candidate_mean_f1_delta_vs_locked_9b_at_least": delta_mean
        >= thresholds["candidate_mean_f1_delta_vs_locked_9b_at_least"],
        "paired_bootstrap_95_ci_lower_greater_than": lower
        > thresholds["paired_bootstrap_95_ci_lower_greater_than"],
        "candidate_max_prompt_eval_count_less_than": metrics[
            "candidate_max_prompt_eval_count"
        ]
        < thresholds["candidate_max_prompt_eval_count_less_than"],
        "candidate_mean_output_tokens_at_most": output_mean
        <= thresholds["candidate_mean_output_tokens_at_most"],
        "candidate_mean_latency_seconds_at_most": latency_mean
        <= thresholds["candidate_mean_latency_seconds_at_most"],
        "candidate_p95_latency_seconds_at_most": latency_p95
        <= thresholds["candidate_p95_latency_seconds_at_most"],
        "candidate_max_latency_seconds_at_most": latency_max
        <= thresholds["candidate_max_latency_seconds_at_most"],
        "production_memory_write_count_equals": metrics[
            "production_memory_write_count"
        ]
        == thresholds["production_memory_write_count_equals"],
        "physical_vrm_action_count_equals": metrics["physical_vrm_action_count"]
        == thresholds["physical_vrm_action_count_equals"],
    }
    return metrics, gates


def classify_decision(gates, contract):
    integrity_and_resource = (
        "new_candidate_model_call_count_equals",
        "historical_control_row_count_equals",
        "combined_row_count_equals",
        "complete_pair_count_equals",
        "candidate_transport_error_count_equals",
        "candidate_nonempty_prediction_rate_equals",
        "candidate_max_prompt_eval_count_less_than",
        "candidate_mean_output_tokens_at_most",
        "candidate_mean_latency_seconds_at_most",
        "candidate_p95_latency_seconds_at_most",
        "candidate_max_latency_seconds_at_most",
        "production_memory_write_count_equals",
        "physical_vrm_action_count_equals",
    )
    rules = contract["decision_rules"]
    if not all(gates[name] for name in integrity_and_resource):
        return rules["any_integrity_or_resource_gate_fails"]
    if not gates["candidate_mean_official_f1_at_least"]:
        return rules["integrity_pass_but_candidate_f1_below_0_45"]
    paired = (
        "candidate_mean_f1_delta_vs_locked_9b_at_least",
        "paired_bootstrap_95_ci_lower_greater_than",
    )
    if not all(gates[name] for name in paired):
        return rules["integrity_and_candidate_f1_pass_but_paired_gain_fails"]
    if not all(gates.values()):
        raise ValueError("unclassified V2.13 gate combination")
    return rules["all_gates_pass"]


def write_final_outputs(
    rows, candidate_rows, contract, raw_path, metadata_path, report_path, markdown_path
):
    metrics, gates = analyze_rows(rows, contract)
    decision = classify_decision(gates, contract)
    capacity_pass = decision == contract["decision_rules"]["all_gates_pass"]
    capacity_insufficient = decision == contract["decision_rules"][
        "integrity_pass_but_candidate_f1_below_0_45"
    ]
    report = {
        "schema": "uruha_source_preserving_memory_projection_model_capacity_report_v2_13",
        "experiment_id": contract["experiment_id"],
        "decision": decision,
        "scope": contract["evidence_scope"],
        "historical_control_model": contract["historical_control_model"],
        "candidate_model": contract["candidate_model"],
        "metrics": metrics,
        "gates": gates,
        "rows": sorted(rows, key=lambda row: (row["case_id"], row["model_condition"])),
        "contains_official_questions": False,
        "contains_official_answers": False,
        "contains_source_context_text": False,
        "authorization": {
            "preregister_new_external_dataset_capacity_validation": capacity_pass,
            "preregister_prompt_carrier_diagnostic": capacity_insufficient,
            "preregister_full_pipeline_memory_intervention": False,
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
        "schema": "uruha_source_preserving_memory_projection_model_capacity_run_metadata_v2_13",
        "experiment_id": contract["experiment_id"],
        "run_at": datetime.now(timezone.utc).isoformat(),
        "contract_sha256": v25.file_sha256(PREREG),
        "raw_candidate_checkpoint_sha256": v25.file_sha256(raw_path),
        "report_sha256": v25.file_sha256(report_path),
        "decision": decision,
        "new_candidate_model_call_count": len(candidate_rows),
    }
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    markdown_path.write_text(
        "\n".join(
            [
                "# V2.13 Qwen3.5 Model-Capacity Screen",
                "",
                f"**Decision: `{decision}`**",
                "",
                "| Measure | Locked 9B control | Fresh 27B candidate |",
                "|---|---:|---:|",
                f"| Mean official F1 | {metrics['locked_9b_mean_official_f1']:.3f} | {metrics['candidate_27b_mean_official_f1']:.3f} |",
                f"| Paired delta | - | {metrics['candidate_mean_f1_delta_vs_locked_9b']:+.3f} |",
                f"| 95% bootstrap CI | - | [{metrics['paired_bootstrap_95_ci'][0]:+.3f}, {metrics['paired_bootstrap_95_ci'][1]:+.3f}] |",
                f"| Mean latency | historical {contract['development_authorization']['locked_control_model']} | {metrics['candidate_mean_latency_seconds']:.3f}s |",
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
        raise SystemExit("V2.13 final output exists; refusing to rerun")
    verify_frozen_inputs(contract)
    v211.verify_official_scorer_runtime(contract)
    verify_candidate_model(contract)
    verify_candidate_model_unloaded(contract)
    cases, controls, v212_contract = reconstruct_cases_and_controls(contract)
    candidate_rows = execute_candidate_calls(
        cases, contract, v212_contract, raw_path
    )
    rows = combined_rows(cases, controls, candidate_rows, contract)
    metadata = write_final_outputs(
        rows,
        candidate_rows,
        contract,
        raw_path,
        metadata_path,
        report_path,
        markdown_path,
    )
    print(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
