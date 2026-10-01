#!/usr/bin/env python3
"""Run fresh synthetic semantic rolling-cutoff, seed, and history-scaling diagnostics."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import random
import sys
import time
from typing import Any, Callable, Mapping, Sequence

from longitudinal_human_model.baselines import OllamaProvider, ProviderError
from longitudinal_human_model.component_features import PREFERENCE_FEATURES, augment_component_features, fit_habit_centroids
from longitudinal_human_model.metrics import evaluate_predictions
from longitudinal_human_model.predictor import fit_softmax_classifier, predict_behavior
from longitudinal_human_model.registry import git_snapshot, load_json, runtime_snapshot, sha256_file, verify_lock, write_json_atomic
from longitudinal_human_model.rolling import available_events, materialize_cutoff, observable_memory_signals
from longitudinal_human_model.temporal import validate_temporal_dataset
from longitudinal_human_model.transitions import TransitionExample, extract_event_features, learned_transition
from run_m6_behavior_predictor import ALL_CONDITIONS, BaselineExecutionFailure, RecordingProvider, build_behavior_rows, run_baselines


ROOT = Path(__file__).resolve().parent


class M8ExecutionFailure(RuntimeError):
    def __init__(self, stage: str, completed: list[dict[str, Any]], cause: Exception):
        super().__init__(f"M8 failed during {stage}: {cause}")
        self.stage = stage
        self.completed = completed
        self.cause = cause


def validate_inputs(dataset: Mapping[str, Any], config: Mapping[str, Any]) -> dict[str, Any]:
    errors = []
    contract = config["engineering_contract"]
    if dataset.get("formal_target_claim") is not False or config.get("formal_target_claim") is not False:
        errors.append("M8 must refuse formal target claims")
    if config.get("retry_policy") != "no_retry_no_condition_fallback":
        errors.append("retry policy differs from preregistration")
    events = dataset.get("events") or []
    if len(events) != int(contract["event_count"]):
        errors.append("event count differs")
    if len({row.get("event_id") for row in events}) != len(events) or len({row.get("observable_text") for row in events}) != len(events):
        errors.append("event IDs and texts must be unique")
    leakage = []
    history_counts = []
    for cutoff_id in config["rolling_cutoffs"]:
        temporal = materialize_cutoff(dataset, cutoff_id)
        report = validate_temporal_dataset(temporal)
        leakage.extend(report.get("violations") or [])
        history_counts.append(len(temporal["history"]))
        if len(temporal["samples"]) != int(contract["test_count_per_cutoff"]):
            errors.append(f"{cutoff_id} test count differs")
    if history_counts != [8, 12, 16, 20]:
        errors.append(f"rolling history counts differ: {history_counts}")
    if len(dataset.get("history_volume_conditions") or []) != int(contract["history_volume_count"]):
        errors.append("history volume count differs")
    return {"valid":not errors,"errors":errors,"history_counts":history_counts,"future_leakage_violations":len(leakage),"leakage_details":leakage}


def _extract_all(dataset, config, provider):
    table, records = {}, []
    for row in dataset["events"]:
        try:
            result = extract_event_features(row["observable_text"], dataset["event_feature_names"], model=config["model"], provider=provider, options=config["provider_options"])
        except (ProviderError, KeyError, TypeError, ValueError) as exc:
            raise M8ExecutionFailure(f'feature_extraction::{row["event_id"]}', records, exc) from exc
        table[row["event_id"]] = result["features"]
        records.append({"event_id":row["event_id"],"rolling_group":row["rolling_group"],**result})
    return table, records


def _base_row(event, extracted, history, dataset, transition_model):
    memory = observable_memory_signals(extracted[event["event_id"]], history, extracted, dataset["event_feature_names"])
    example = TransitionExample(
        example_id=event["event_id"], split="rolling", event_text=event["observable_text"],
        previous_state={k:float(v) for k,v in event["previous_state"].items()},
        event_features={k:float(v) for k,v in event["event_features"].items()},
        memory_signals=memory,
        person_parameters={k:float(v) for k,v in event["person_parameters"].items()},
        next_state={k:float(v) for k,v in event["previous_state"].items()},
    )
    transition = learned_transition("T3_HYBRID", example, transition_model, dataset["state_dimensions"], event_features=extracted[event["event_id"]], feature_source="fresh_m8_qwen_event_extractor")
    features = {}
    features.update({f"state.{k}":v for k,v in transition["next_state"].items()})
    features.update({f"event.{k}":v for k,v in extracted[event["event_id"]].items()})
    features.update({f"memory.{k}":v for k,v in memory.items()})
    features.update({f"person.{k}":float(v) for k,v in event["person_parameters"].items()})
    return {"example_id":event["event_id"],"behavior_label":event["actual_observed_behavior"],"features":features,"previous_state":event["previous_state"],"event":event}


def _stratified_bootstrap(rows, labels, seed):
    rng = random.Random(int(seed))
    sampled = []
    for label in labels:
        members = [row for row in rows if row["behavior_label"] == label]
        sampled.extend(dict(rng.choice(members)) for _ in members)
    for index, row in enumerate(sampled):
        row["example_id"] = f'{row["example_id"]}::boot::{seed}::{index}'
    return sampled


def _metric_row(row, probabilities, condition="OURS_HYBRID"):
    sample_id=row.get("example_id") or row["sample_id"]
    actual=row.get("behavior_label") or row["actual_observed_behavior"]
    return {"sample_id":sample_id,"condition":condition,"actual_observed_behavior":actual,"acceptable_behavior_labels":[actual],"probabilities":probabilities,"language_realization_performed":False}


def _run_ours_condition(dataset, config, cutoff_id, volume, seed, extracted, m6_train, transition_model):
    labels = list(dataset["taxonomy"]["labels"])
    selected_history = available_events(dataset, cutoff_id, volume["max_m8_history_events"])
    selected_ids = {row["event_id"] for row in selected_history}
    history_rows = []
    for event in selected_history:
        prior = [row for row in selected_history if row["event_id"] in selected_ids and row["available_at"] < event["event_time"]]
        history_rows.append(_base_row(event, extracted, prior, dataset, transition_model))
    centroid_source = [*m6_train, *history_rows]
    centroids = fit_habit_centroids(centroid_source, labels, dataset["event_feature_names"])
    train = [{**row,"features":augment_component_features(row["features"],centroids,dataset["event_feature_names"])} for row in centroid_source]
    boot = _stratified_bootstrap(train, labels, seed)
    pconf = config["predictor"]
    model = fit_softmax_classifier(boot, labels, list(train[0]["features"]), l2_alpha=float(pconf["l2_alpha"]), learning_rate=float(pconf["learning_rate"]), epochs=int(pconf["epochs"]))
    cutoff = next(row for row in dataset["rolling_cutoffs"] if row["cutoff_id"] == cutoff_id)
    test_events = [row for row in dataset["events"] if row["event_id"] in cutoff["test_event_ids"]]
    base_tests = [_base_row(event, extracted, selected_history, dataset, transition_model) for event in test_events]
    tests = [{**row,"features":augment_component_features(row["features"],centroids,dataset["event_feature_names"])} for row in base_tests]
    outputs = []
    for row in tests:
        prediction = predict_behavior(model,row["features"],temperature=float(pconf["temperature"]),evidence={"cutoff_id":cutoff_id,"history_event_ids":[h["event_id"] for h in selected_history]})
        outputs.append({**_metric_row(row,prediction["probabilities"]),"cutoff_id":cutoff_id,"history_condition":volume["condition"],"seed":seed,"selected_behavior":prediction["selected_behavior"],"features":row["features"],"previous_state":row["previous_state"]})
    return outputs, model, centroids


def _aggregate_metrics(rows, labels, config):
    return evaluate_predictions(rows,labels,top_k=int(config["metrics"]["top_k"]),ece_bins=int(config["metrics"]["ece_bins"]))


def run_experiment(dataset, config, m5_dataset, m5_result, m6_overlay, *, provider: Callable[...,dict[str,Any]]):
    validation = validate_inputs(dataset,config)
    if not validation["valid"]:
        raise ValueError("invalid M8 inputs: "+"; ".join(validation["errors"]))
    labels = list(dataset["taxonomy"]["labels"])
    extracted, feature_records = _extract_all(dataset,config,provider)
    m6_rows, _ = build_behavior_rows(m6_overlay,m5_dataset,m5_result)
    m6_train = [row for row in m6_rows if row["split"] == "train"]
    transition_model = m5_result["selected_models"]["T3_HYBRID"]
    baseline_provider = RecordingProvider(provider)
    baseline_rows, summaries = [], {}
    for cutoff_id in config["rolling_cutoffs"]:
        temporal = materialize_cutoff(dataset,cutoff_id)
        try:
            rows, summary = run_baselines(temporal,config,provider=baseline_provider)
        except BaselineExecutionFailure as exc:
            raise M8ExecutionFailure(f"baseline::{cutoff_id}::{exc.condition}",feature_records+baseline_provider.records,exc) from exc
        baseline_rows.extend({**row,"cutoff_id":cutoff_id} for row in rows)
        summaries[cutoff_id] = summary
    primary_seed = int(config["bootstrap_seeds"][-1])
    volume_rows, full_contexts = {}, {}
    started = time.perf_counter()
    for volume in dataset["history_volume_conditions"]:
        combined = []
        for cutoff_id in config["rolling_cutoffs"]:
            rows, model, centroids = _run_ours_condition(dataset,config,cutoff_id,volume,primary_seed,extracted,m6_train,transition_model)
            combined.extend(rows)
            if volume["condition"] == "D7_ALL_AVAILABLE":
                full_contexts[cutoff_id] = {"rows":rows,"model":model,"centroids":centroids}
        volume_rows[volume["condition"]] = combined
    seed_rows = {str(primary_seed):volume_rows["D7_ALL_AVAILABLE"]}
    for seed in config["bootstrap_seeds"][:-1]:
        combined=[]
        volume=dataset["history_volume_conditions"][-1]
        for cutoff_id in config["rolling_cutoffs"]:
            rows,_,_= _run_ours_condition(dataset,config,cutoff_id,volume,int(seed),extracted,m6_train,transition_model)
            combined.extend(rows)
        seed_rows[str(seed)] = combined
    numeric_seconds = time.perf_counter()-started
    ours_rows = volume_rows["D7_ALL_AVAILABLE"]
    all_primary_rows = [*baseline_rows,*ours_rows]
    metrics = {condition:_aggregate_metrics([row for row in all_primary_rows if row["condition"]==condition],labels,config) for condition in ALL_CONDITIONS}
    rolling_metrics = {cutoff_id:_aggregate_metrics([row for row in ours_rows if row["cutoff_id"]==cutoff_id],labels,config) for cutoff_id in config["rolling_cutoffs"]}
    scaling_metrics = {name:_aggregate_metrics(rows,labels,config) for name,rows in volume_rows.items()}
    seed_metrics = {seed:_aggregate_metrics(rows,labels,config) for seed,rows in seed_rows.items()}
    ablation_rows={name:[] for name in ("temporal_dynamics","relationship","preference")}
    for cutoff_id,context in full_contexts.items():
        for row in context["rows"]:
            base={name:value for name,value in row["features"].items() if not name.startswith("preference.") and not name.startswith("habit.")}
            for component in ablation_rows:
                changed=dict(base)
                if component=="temporal_dynamics":
                    for name,value in row["previous_state"].items(): changed[f"state.{name}"]=float(value)
                elif component=="relationship":
                    changed["state.relationship_tension"]=0.0
                changed=augment_component_features(changed,context["centroids"],dataset["event_feature_names"])
                if component=="preference":
                    for name in PREFERENCE_FEATURES: changed[name]=0.0
                pred=predict_behavior(context["model"],changed,temperature=float(config["predictor"]["temperature"]),evidence={})
                ablation_rows[component].append(_metric_row(row,pred["probabilities"],f"OURS_MINUS_{component}"))
    ablations={}
    full=metrics["OURS_HYBRID"]
    for component,rows in ablation_rows.items():
        measured=_aggregate_metrics(rows,labels,config)
        ablations[component]={"metrics":measured,"delta_vs_full":{name:measured[name]-full[name] for name in ("top1_accuracy","brier_score","negative_log_likelihood","expected_calibration_error")}}
    best={"top1_accuracy":max(metrics[name]["top1_accuracy"] for name in ALL_CONDITIONS if name!="OURS_HYBRID"),"brier_score":min(metrics[name]["brier_score"] for name in ALL_CONDITIONS if name!="OURS_HYBRID")}
    hypotheses=config["falsifiable_diagnostic_hypotheses"]
    top1s=[row["top1_accuracy"] for row in rolling_metrics.values()]
    checks={
        "fresh_semantic_ours_top1_at_least_best_b0_b5":full["top1_accuracy"]>=best["top1_accuracy"],
        "fresh_semantic_ours_brier_below_best_b0_b5":full["brier_score"]<best["brier_score"],
        "d7_nll_not_worse_than_d0":scaling_metrics["D7_ALL_AVAILABLE"]["negative_log_likelihood"]<=scaling_metrics["D0_PROFILE_ONLY"]["negative_log_likelihood"],
        "last_history_increment_nll_gain_not_larger_than_first_increment":(scaling_metrics["D6_LAST_16"]["negative_log_likelihood"]-scaling_metrics["D7_ALL_AVAILABLE"]["negative_log_likelihood"]) <= (scaling_metrics["D0_PROFILE_ONLY"]["negative_log_likelihood"]-scaling_metrics["D1_LAST_2"]["negative_log_likelihood"]),
        "rolling_ours_top1_range_at_most":max(top1s)-min(top1s)<=float(hypotheses["rolling_ours_top1_range_at_most"]),
        "m7_temporal_removal_nll_improvement_replicates":ablations["temporal_dynamics"]["delta_vs_full"]["negative_log_likelihood"]<0,
        "m7_relationship_removal_nll_improvement_replicates":ablations["relationship"]["delta_vs_full"]["negative_log_likelihood"]<0,
        "m7_preference_removal_nll_improvement_replicates":ablations["preference"]["delta_vs_full"]["negative_log_likelihood"]<0,
    }
    feature_mae=sum(abs(extracted[row["event_id"]][name]-row["event_features"][name]) for row in dataset["events"] for name in dataset["event_feature_names"])/(len(dataset["events"])*len(dataset["event_feature_names"]))
    total_calls=len(feature_records)+len(baseline_provider.records)
    contract=config["engineering_contract"]
    engineering={
        "rolling_test_row_count":len(ours_rows)==int(contract["rolling_test_row_count"]),
        "feature_extractor_calls":len(feature_records)==int(contract["feature_extractor_calls"]),
        "baseline_prediction_rows":len(baseline_rows)==int(contract["baseline_prediction_rows"]),
        "baseline_model_calls":len(baseline_provider.records)==int(contract["baseline_model_calls"]),
        "total_model_calls":total_calls==int(contract["total_model_calls"]),
        "future_leakage_violations":validation["future_leakage_violations"]==int(contract["future_leakage_violations"]),
        "history_volume_count":len(scaling_metrics)==int(contract["history_volume_count"]),
        "bootstrap_seed_count":len(seed_metrics)==int(contract["bootstrap_seed_count"]),
        "language_realization_performed":not any(row.get("language_realization_performed") for row in all_primary_rows),
    }
    return {
        "schema":"ilhdt_m8_rolling_scaling_result_v1","status":"complete_hypothesis_run" if all(engineering.values()) else "failed_engineering_gate","recorded_at":datetime.now(timezone.utc).isoformat(),"claim_level":config["claim_level"],"formal_target_claim":False,
        "validation":validation,"feature_extraction":{"records":feature_records,"mean_absolute_error_vs_synthetic_features":feature_mae},"rows":all_primary_rows,"metrics":metrics,"rolling_metrics":rolling_metrics,"history_scaling_metrics":scaling_metrics,"seed_metrics":seed_metrics,"ablations":ablations,
        "diagnostic_hypothesis_checks":checks,"diagnostic_hypotheses_supported":all(checks.values()),"engineering_gate_checks":engineering,"engineering_gate_pass":all(engineering.values()),
        "baseline_summaries":summaries,"provider_records":{"feature_extractor":feature_records,"baselines":baseline_provider.records},
        "resources":{"feature_extractor_calls":len(feature_records),"baseline_model_calls":len(baseline_provider.records),"total_model_calls":total_calls,"prompt_tokens":sum(r["prompt_tokens"] for r in feature_records)+sum(r["prompt_tokens"] for r in baseline_provider.records),"completion_tokens":sum(r["completion_tokens"] for r in feature_records)+sum(r["completion_tokens"] for r in baseline_provider.records),"model_latency_seconds":sum(r["latency_seconds"] for r in feature_records)+sum(r["latency_seconds"] for r in baseline_provider.records),"numeric_fit_predict_seconds":numeric_seconds},
        "language_realization_performed":False,"limitations":list(config["non_claims"]),
    }


def parse_args(argv):
    parser=argparse.ArgumentParser(); parser.add_argument("--mode",choices=("validate","run"),default="validate"); parser.add_argument("--config",required=True); parser.add_argument("--lock",required=True); parser.add_argument("--output"); return parser.parse_args(argv)


def main(argv=None):
    args=parse_args(argv or sys.argv[1:]); config_path=ROOT/args.config; lock_path=ROOT/args.lock; config=load_json(config_path); lock=load_json(lock_path)
    names=("dataset","m5_dataset","m5_result","m6_overlay","m6_result","m71_result")
    loaded={name:load_json(ROOT/config[name]["path"]) for name in names}; validation=validate_inputs(loaded["dataset"],config); errors=verify_lock(lock,repo_root=ROOT)
    for name in names:
        if sha256_file(ROOT/config[name]["path"])!=config[name]["sha256"]: errors.append(f"{name} hash mismatch")
    frozen={"schema":"ilhdt_m8_validation_v1","valid":validation["valid"] and not errors,"inputs":validation,"lock_errors":errors,"config_sha256":sha256_file(config_path),"lock_sha256":sha256_file(lock_path)}
    if args.mode=="validate": print(json.dumps(frozen,ensure_ascii=False,indent=2,sort_keys=True)); return 0 if frozen["valid"] else 2
    if not frozen["valid"]: raise SystemExit("M8 frozen validation failed")
    if not args.output: raise SystemExit("--output is required")
    try:
        result=run_experiment(loaded["dataset"],config,loaded["m5_dataset"],loaded["m5_result"],loaded["m6_overlay"],provider=OllamaProvider(timeout=int(config["provider_timeout_seconds"])))
    except M8ExecutionFailure as exc:
        result={"schema":"ilhdt_m8_rolling_scaling_result_v1","status":"provider_failed_no_retry","failed_stage":exc.stage,"error":str(exc.cause),"completed_records":exc.completed,"engineering_gate_pass":False,"diagnostic_hypotheses_supported":False}
    result["validation"]=frozen; result["experiment_lock"]=lock; result["environment"]=runtime_snapshot(); result["git"]=git_snapshot(ROOT); write_json_atomic(ROOT/args.output,result)
    print(json.dumps({"output":str(ROOT/args.output),"status":result["status"],"diagnostic_hypotheses_supported":result.get("diagnostic_hypotheses_supported")},indent=2)); return 0 if result.get("engineering_gate_pass") else 3


if __name__=="__main__": raise SystemExit(main())
