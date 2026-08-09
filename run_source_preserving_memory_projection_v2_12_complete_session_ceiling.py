#!/usr/bin/env python3
"""Run the exposed paired complete-session capability-ceiling diagnostic."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import build_source_preserving_memory_projection_v2_5_locomo_cases as v25
import build_source_preserving_memory_projection_v2_10_final_reserve as v210
import run_source_preserving_memory_projection_v2_11_model_qa as v211


ROOT = Path(__file__).resolve().parent
PREREG = (
    ROOT
    / "configs/source_preserving_memory_projection_v2_12_complete_session_ceiling_preregistration.json"
)
CONDITIONS = ("adjacency", "complete_session")


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_preregistration(path=PREREG):
    return load_json(path)


def verify_frozen_inputs(contract):
    for section in (
        "development_authorization",
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


def final_case_specs(data, contract):
    v210_prereg = v210.load_preregistration()
    final_samples, final_ids = v210.final_reserve_samples(data, v210_prereg)
    aliases = {
        f"final-reserve-{index + 1}": sample
        for index, sample in enumerate(final_samples)
    }
    frozen = load_json(
        ROOT / contract["frozen_case_reconstruction"]["v2_10_report_path"]
    )
    specs = []
    for frozen_case in frozen["cases"]:
        sample = aliases[frozen_case["sample_id"]]
        qa = sample["qa"][frozen_case["qa_index"]]
        question = str(qa["question"])
        answer = str(qa["answer"])
        if v25.text_sha256(question) != frozen_case["question_sha256"]:
            raise ValueError(f"question hash drift: {frozen_case['case_id']}")
        session = sample["conversation"][frozen_case["target_session"]]
        adjacency = v25.serialize_session(
            sample["conversation"],
            frozen_case["target_session"],
            frozen_case["adjacency"]["source_turn_indices"],
        )
        complete_session = v25.serialize_session(
            sample["conversation"],
            frozen_case["target_session"],
            list(range(len(session))),
        )
        if v25.text_sha256(adjacency) != frozen_case["adjacency"][
            "projection_text_sha256"
        ]:
            raise ValueError(f"adjacency hash drift: {frozen_case['case_id']}")
        if len(complete_session) != frozen_case["adjacency"][
            "complete_character_count"
        ]:
            raise ValueError(
                f"complete-session character-count drift: {frozen_case['case_id']}"
            )
        evidence_transition = (
            "adjacency_only"
            if frozen_case["adjacency"]["contains_all_official_evidence"]
            and not frozen_case["isolated"]["contains_all_official_evidence"]
            else "isolated_only"
            if frozen_case["isolated"]["contains_all_official_evidence"]
            and not frozen_case["adjacency"]["contains_all_official_evidence"]
            else "both"
            if frozen_case["isolated"]["contains_all_official_evidence"]
            else "neither"
        )
        specs.append(
            {
                "case_id": frozen_case["case_id"],
                "sample_alias": frozen_case["sample_id"],
                "qa_index": frozen_case["qa_index"],
                "question": question,
                "answer": answer,
                "speaker_a": str(
                    sample["conversation"].get("speaker_a") or "Speaker A"
                ),
                "speaker_b": str(
                    sample["conversation"].get("speaker_b") or "Speaker B"
                ),
                "contexts": {
                    "adjacency": adjacency,
                    "complete_session": complete_session,
                },
                "evidence_transition": evidence_transition,
            }
        )
    expected_count = contract["development_authorization"]["v2_11_case_count"]
    if len(specs) != expected_count:
        raise ValueError("frozen case count drift")
    expected_ids_hash = frozen["scope"]["final_reserve_sample_ids_sha256"]
    if v25.canonical_sha256(final_ids) != expected_ids_hash:
        raise ValueError("final reserve ID hash drift")
    return specs


def build_prompt(case, representation, contract):
    prompt = contract["prompt"]
    return (
        prompt["context_header"].format(case["speaker_a"], case["speaker_b"])
        + case["contexts"][representation]
        + prompt["qa_template"].format(case["question"])
    )


def planned_calls(cases):
    calls = []
    for index, case in enumerate(cases):
        order = CONDITIONS if index % 2 == 0 else tuple(reversed(CONDITIONS))
        calls.extend((case, representation) for representation in order)
    return calls


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
            raise ValueError(f"duplicate completed call ID: {call_id}")
        completed[call_id] = row
    return completed


def append_checkpoint(path, row):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def execute_calls(
    cases,
    contract,
    raw_path,
    model_call=v211.call_model,
    score_fn=v211.official_f1,
):
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


def analyze_rows(rows, contract):
    by_case = {}
    for row in rows:
        by_case.setdefault(row["case_id"], {})[row["representation"]] = row
    complete_pairs = {
        case_id: conditions
        for case_id, conditions in by_case.items()
        if set(conditions) == set(CONDITIONS)
    }
    adjacency = [
        conditions["adjacency"]["official_f1"]
        for conditions in complete_pairs.values()
    ]
    complete_session = [
        conditions["complete_session"]["official_f1"]
        for conditions in complete_pairs.values()
    ]
    deltas = [
        full - adjacent for adjacent, full in zip(adjacency, complete_session)
    ]
    runtime = contract["official_scorer_runtime"]
    lower, upper = (
        v211.paired_bootstrap(
            deltas, runtime["bootstrap_samples"], runtime["bootstrap_seed"]
        )
        if deltas
        else (0.0, 0.0)
    )
    adjacency_mean = v211.mean(adjacency)
    complete_mean = v211.mean(complete_session)
    delta_mean = v211.mean(deltas)
    baseline = contract["development_authorization"]["v2_11_adjacency_mean_f1"]
    adjacency_drift = abs(adjacency_mean - baseline)
    prompt_counts = [
        row["prompt_eval_count"]
        for row in rows
        if row["prompt_eval_count"] is not None
    ]
    output_counts = [
        float(row["eval_count"])
        for row in rows
        if row["eval_count"] is not None
    ]
    prompt_counts_by_condition = {
        representation: [
            float(row["prompt_eval_count"])
            for row in rows
            if row["representation"] == representation
            and row["prompt_eval_count"] is not None
        ]
        for representation in CONDITIONS
    }
    output_counts_by_condition = {
        representation: [
            float(row["eval_count"])
            for row in rows
            if row["representation"] == representation
            and row["eval_count"] is not None
        ]
        for representation in CONDITIONS
    }
    latencies_by_condition = {
        representation: [
            float(row["latency_seconds"])
            for row in rows
            if row["representation"] == representation
            and row["latency_seconds"] is not None
        ]
        for representation in CONDITIONS
    }
    output_mean = v211.mean(output_counts)
    metrics = {
        "model_call_count": len(rows),
        "complete_pair_count": len(complete_pairs),
        "row_count_by_condition": {
            representation: sum(
                row["representation"] == representation for row in rows
            )
            for representation in CONDITIONS
        },
        "transport_error_count": sum(bool(row["transport_error"]) for row in rows),
        "nonempty_prediction_rate": round(
            v211.mean([float(bool(row["prediction"])) for row in rows]), 6
        ),
        "adjacency_rerun_mean_official_f1": round(adjacency_mean, 6),
        "v2_11_adjacency_mean_official_f1": baseline,
        "adjacency_rerun_mean_f1_absolute_drift_vs_v2_11": round(
            adjacency_drift, 6
        ),
        "complete_session_mean_official_f1": round(complete_mean, 6),
        "complete_session_mean_f1_delta_vs_adjacency": round(
            delta_mean, 6
        ),
        "paired_bootstrap_95_ci": [round(lower, 6), round(upper, 6)],
        "identical_prediction_pair_rate": round(
            v211.mean(
                [
                    float(
                        conditions["adjacency"]["prediction"]
                        == conditions["complete_session"]["prediction"]
                    )
                    for conditions in complete_pairs.values()
                ]
            ),
            6,
        ),
        "mean_prompt_eval_count_by_condition": {
            representation: round(v211.mean(values), 6)
            for representation, values in prompt_counts_by_condition.items()
        },
        "mean_output_tokens_by_condition": {
            representation: round(v211.mean(values), 6)
            for representation, values in output_counts_by_condition.items()
        },
        "mean_latency_seconds_by_condition": {
            representation: round(v211.mean(values), 6)
            for representation, values in latencies_by_condition.items()
        },
        "p95_latency_seconds_by_condition": {
            representation: round(v211.percentile(values, 0.95), 6)
            for representation, values in latencies_by_condition.items()
        },
        "max_prompt_eval_count": max(prompt_counts) if prompt_counts else 0,
        "mean_model_output_tokens": round(output_mean, 6),
        "production_memory_write_count": sum(
            row["production_memory_write_count"] for row in rows
        ),
        "physical_vrm_action_count": sum(
            row["physical_vrm_action_count"] for row in rows
        ),
    }
    thresholds = contract["success_gates"]
    checks = {
        "model_call_count_equals": metrics["model_call_count"]
        == thresholds["model_call_count_equals"],
        "row_count_per_condition_equals": all(
            count == thresholds["row_count_per_condition_equals"]
            for count in metrics["row_count_by_condition"].values()
        ),
        "complete_pair_count_equals": metrics["complete_pair_count"]
        == thresholds["complete_pair_count_equals"],
        "transport_error_count_equals": metrics["transport_error_count"]
        == thresholds["transport_error_count_equals"],
        "nonempty_prediction_rate_equals": metrics["nonempty_prediction_rate"]
        == thresholds["nonempty_prediction_rate_equals"],
        "adjacency_rerun_mean_f1_absolute_drift_vs_v2_11_at_most": adjacency_drift
        <= thresholds["adjacency_rerun_mean_f1_absolute_drift_vs_v2_11_at_most"],
        "complete_session_mean_official_f1_at_least": complete_mean
        >= thresholds["complete_session_mean_official_f1_at_least"],
        "complete_session_mean_f1_delta_vs_adjacency_at_least": delta_mean
        >= thresholds["complete_session_mean_f1_delta_vs_adjacency_at_least"],
        "paired_bootstrap_95_ci_lower_greater_than": lower
        > thresholds["paired_bootstrap_95_ci_lower_greater_than"],
        "max_prompt_eval_count_less_than": metrics["max_prompt_eval_count"]
        < thresholds["max_prompt_eval_count_less_than"],
        "mean_model_output_tokens_at_most": output_mean
        <= thresholds["mean_model_output_tokens_at_most"],
        "production_memory_write_count_equals": metrics[
            "production_memory_write_count"
        ]
        == thresholds["production_memory_write_count_equals"],
        "physical_vrm_action_count_equals": metrics["physical_vrm_action_count"]
        == thresholds["physical_vrm_action_count_equals"],
    }
    return metrics, checks


def classify_decision(metrics, gates, contract):
    integrity_names = (
        "model_call_count_equals",
        "row_count_per_condition_equals",
        "complete_pair_count_equals",
        "transport_error_count_equals",
        "nonempty_prediction_rate_equals",
        "adjacency_rerun_mean_f1_absolute_drift_vs_v2_11_at_most",
        "max_prompt_eval_count_less_than",
        "mean_model_output_tokens_at_most",
        "production_memory_write_count_equals",
        "physical_vrm_action_count_equals",
    )
    rules = contract["decision_rules"]
    if not all(gates[name] for name in integrity_names):
        return rules["any_integrity_gate_fails"]
    if not gates["complete_session_mean_official_f1_at_least"]:
        return rules["integrity_pass_but_complete_f1_below_0_45"]
    paired_names = (
        "complete_session_mean_f1_delta_vs_adjacency_at_least",
        "paired_bootstrap_95_ci_lower_greater_than",
    )
    if not all(gates[name] for name in paired_names):
        return rules["integrity_and_complete_f1_pass_but_paired_gain_fails"]
    if not all(gates.values()):
        raise ValueError("unclassified V2.12 gate combination")
    return rules["all_gates_pass"]


def write_final_outputs(
    rows, contract, raw_path, metadata_path, report_path, markdown_path
):
    metrics, gates = analyze_rows(rows, contract)
    decision = classify_decision(metrics, gates, contract)
    projection_localized = decision == contract["decision_rules"]["all_gates_pass"]
    low_complete_ceiling = decision == contract["decision_rules"][
        "integrity_pass_but_complete_f1_below_0_45"
    ]
    report = {
        "schema": "uruha_source_preserving_memory_projection_complete_session_ceiling_report_v2_12",
        "experiment_id": contract["experiment_id"],
        "decision": decision,
        "scope": contract["evidence_scope"],
        "model": contract["local_model"],
        "metrics": metrics,
        "gates": gates,
        "rows": sorted(rows, key=lambda row: row["call_id"]),
        "contains_official_questions": False,
        "contains_official_answers": False,
        "contains_source_context_text": False,
        "authorization": {
            "preregister_projection_coherence_development": projection_localized,
            "preregister_model_prompt_capacity_diagnostic": low_complete_ceiling,
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
        "schema": "uruha_source_preserving_memory_projection_complete_session_ceiling_run_metadata_v2_12",
        "experiment_id": contract["experiment_id"],
        "run_at": datetime.now(timezone.utc).isoformat(),
        "contract_sha256": v25.file_sha256(PREREG),
        "raw_checkpoint_sha256": v25.file_sha256(raw_path),
        "report_sha256": v25.file_sha256(report_path),
        "decision": decision,
        "model_call_count": metrics["model_call_count"],
    }
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    markdown_path.write_text(
        "\n".join(
            [
                "# V2.12 Complete-Session Capability Ceiling",
                "",
                f"**Decision: `{decision}`**",
                "",
                "| Measure | Adjacency rerun | Complete target session |",
                "|---|---:|---:|",
                f"| Mean official F1 | {metrics['adjacency_rerun_mean_official_f1']:.3f} | {metrics['complete_session_mean_official_f1']:.3f} |",
                f"| Paired delta | - | {metrics['complete_session_mean_f1_delta_vs_adjacency']:+.3f} |",
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
        raise SystemExit("V2.12 final output exists; refusing to rerun")
    verify_frozen_inputs(contract)
    v211.verify_official_scorer_runtime(contract)
    v211.verify_local_model(contract)
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
