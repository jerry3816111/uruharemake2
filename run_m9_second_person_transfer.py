#!/usr/bin/env python3
"""Run second-person transfer without changing the M8 core model logic."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import sys
import time
from typing import Any, Callable, Mapping

from longitudinal_human_model.baselines import OllamaProvider
from longitudinal_human_model.metrics import evaluate_predictions
from longitudinal_human_model.registry import git_snapshot, load_json, runtime_snapshot, sha256_file, verify_lock, write_json_atomic
from longitudinal_human_model.rolling import available_events, materialize_cutoff
from longitudinal_human_model.rolling_parser_v1_1 import extract_event_features_bounded
from longitudinal_human_model.temporal import validate_temporal_dataset
from run_m6_behavior_predictor import ALL_CONDITIONS, BaselineExecutionFailure, RecordingProvider, build_behavior_rows, run_baselines
import run_m8_rolling_scaling as m8_core


ROOT=Path(__file__).resolve().parent
TRANSFER_CONDITIONS=("REN_ZERO_SHOT","MIRA_PARAMETER_SWAP","MIRA_FULL_ADAPTATION")


class M9ExecutionFailure(RuntimeError):
    def __init__(self,stage,completed,cause): super().__init__(f"M9 failed during {stage}: {cause}"); self.stage=stage; self.completed=completed; self.cause=cause


def validate_inputs(mira,ren,source_result,config):
    errors=[]; contract=config["engineering_contract"]
    if mira.get("formal_target_claim") is not False or config.get("formal_target_claim") is not False: errors.append("M9 must refuse formal claims")
    for key in ("schema","taxonomy","event_feature_names","state_dimensions","memory_signal_names","person_parameter_names"):
        if mira.get(key)!=ren.get(key): errors.append(f"second-person {key} differs from source schema")
    if mira.get("target",{}).get("target_id")==ren.get("target",{}).get("target_id"): errors.append("second person target id must differ")
    if len(mira.get("events") or [])!=int(contract["event_count"]): errors.append("second-person event count differs")
    if {row["observable_text"] for row in mira["events"]}&{row["observable_text"] for row in ren["events"]}: errors.append("second-person text overlaps source person")
    if len(source_result.get("feature_extraction",{}).get("records") or [])!=24: errors.append("source result lacks 24 frozen feature records")
    violations=[]; counts=[]
    for cutoff in config["rolling_cutoffs"]:
        temporal=materialize_cutoff(mira,cutoff); report=validate_temporal_dataset(temporal); violations.extend(report.get("violations") or []); counts.append(len(temporal["history"]))
    if counts!=[8,12,16,20]: errors.append(f"second-person history counts differ: {counts}")
    return {"valid":not errors,"errors":errors,"history_counts":counts,"future_leakage_violations":len(violations)}


def _source_extracted(source_result):
    return {row["event_id"]:{name:float(value) for name,value in row["features"].items()} for row in source_result["feature_extraction"]["records"]}


def _hybrid_dataset(ren,mira,cutoff_id,use_mira_parameters):
    source_history=available_events(ren,cutoff_id,None)
    cutoff=next(row for row in mira["rolling_cutoffs"] if row["cutoff_id"]==cutoff_id)
    tests=[copy.deepcopy(row) for row in mira["events"] if row["event_id"] in cutoff["test_event_ids"]]
    if not use_mira_parameters:
        source_parameters=dict(ren["events"][0]["person_parameters"])
        for row in tests: row["person_parameters"]=source_parameters
    return {**mira,"dataset_id":f'm9_transfer_hybrid::{cutoff_id}::{"parameter_swap" if use_mira_parameters else "zero_shot"}',"events":[*copy.deepcopy(source_history),*tests],"rolling_cutoffs":[copy.deepcopy(cutoff)],"history_volume_conditions":[{"condition":"D7_ALL_AVAILABLE","max_m8_history_events":None}]}


def _rename(rows,condition):
    return [{**row,"condition":condition,"transfer_condition":condition} for row in rows]


def _metrics(rows,labels,config):
    return evaluate_predictions(rows,labels,top_k=int(config["metrics"]["top_k"]),ece_bins=int(config["metrics"]["ece_bins"]))


def run_experiment(mira,ren,source_result,config,m5_dataset,m5_result,m6_overlay,*,provider:Callable[...,dict[str,Any]]):
    validation=validate_inputs(mira,ren,source_result,config)
    if not validation["valid"]: raise ValueError("invalid M9 inputs: "+"; ".join(validation["errors"]))
    original=m8_core.extract_event_features; m8_core.extract_event_features=extract_event_features_bounded
    try: mira_extracted,feature_records=m8_core._extract_all(mira,config,provider)
    except m8_core.M8ExecutionFailure as exc: raise M9ExecutionFailure(exc.stage,exc.completed,exc) from exc
    finally: m8_core.extract_event_features=original
    ren_extracted=_source_extracted(source_result); combined_extracted={**ren_extracted,**mira_extracted}
    m6_rows,_=build_behavior_rows(m6_overlay,m5_dataset,m5_result); m6_train=[row for row in m6_rows if row["split"]=="train"]
    transition_model=m5_result["selected_models"]["T3_HYBRID"]
    volume={"condition":"D7_ALL_AVAILABLE","max_m8_history_events":None}; seed=int(config["bootstrap_seed"])
    transfer_rows=[]; numeric_started=time.perf_counter()
    for cutoff_id in config["rolling_cutoffs"]:
        zero_dataset=_hybrid_dataset(ren,mira,cutoff_id,False)
        zero_rows,_,_=m8_core._run_ours_condition(zero_dataset,config,cutoff_id,volume,seed,combined_extracted,m6_train,transition_model)
        transfer_rows.extend(_rename(zero_rows,"REN_ZERO_SHOT"))
        parameter_dataset=_hybrid_dataset(ren,mira,cutoff_id,True)
        parameter_rows,_,_=m8_core._run_ours_condition(parameter_dataset,config,cutoff_id,volume,seed,combined_extracted,m6_train,transition_model)
        transfer_rows.extend(_rename(parameter_rows,"MIRA_PARAMETER_SWAP"))
        adapted_rows,_,_=m8_core._run_ours_condition(mira,config,cutoff_id,volume,seed,mira_extracted,m6_train,transition_model)
        transfer_rows.extend(_rename(adapted_rows,"MIRA_FULL_ADAPTATION"))
    numeric_seconds=time.perf_counter()-numeric_started
    recording=RecordingProvider(provider); baseline_rows=[]; summaries={}
    for cutoff_id in config["rolling_cutoffs"]:
        try: rows,summary=run_baselines(materialize_cutoff(mira,cutoff_id),config,provider=recording)
        except BaselineExecutionFailure as exc: raise M9ExecutionFailure(f"baseline::{cutoff_id}::{exc.condition}",feature_records+recording.records,exc) from exc
        baseline_rows.extend({**row,"cutoff_id":cutoff_id} for row in rows); summaries[cutoff_id]=summary
    labels=list(mira["taxonomy"]["labels"]); all_rows=[*baseline_rows,*transfer_rows]
    conditions=(*ALL_CONDITIONS[:-1],*TRANSFER_CONDITIONS)
    metrics={condition:_metrics([row for row in all_rows if row["condition"]==condition],labels,config) for condition in conditions}
    rolling_metrics={cutoff:_metrics([row for row in transfer_rows if row["condition"]=="MIRA_FULL_ADAPTATION" and row["cutoff_id"]==cutoff],labels,config) for cutoff in config["rolling_cutoffs"]}
    best={"top1_accuracy":max(metrics[name]["top1_accuracy"] for name in ALL_CONDITIONS[:-1]),"brier_score":min(metrics[name]["brier_score"] for name in ALL_CONDITIONS[:-1])}
    full=metrics["MIRA_FULL_ADAPTATION"]; zero=metrics["REN_ZERO_SHOT"]; parameter=metrics["MIRA_PARAMETER_SWAP"]; top1s=[row["top1_accuracy"] for row in rolling_metrics.values()]
    checks={"full_adaptation_top1_at_least_zero_shot":full["top1_accuracy"]>=zero["top1_accuracy"],"full_adaptation_brier_below_zero_shot":full["brier_score"]<zero["brier_score"],"parameter_swap_top1_at_least_zero_shot":parameter["top1_accuracy"]>=zero["top1_accuracy"],"full_adaptation_top1_at_least_parameter_swap":full["top1_accuracy"]>=parameter["top1_accuracy"],"full_adaptation_top1_at_least_best_b0_b5":full["top1_accuracy"]>=best["top1_accuracy"],"full_adaptation_brier_below_best_b0_b5":full["brier_score"]<best["brier_score"],"full_adaptation_rolling_top1_range_at_most":max(top1s)-min(top1s)<=float(config["falsifiable_hypotheses"]["full_adaptation_rolling_top1_range_at_most"])}
    core_hashes={path:sha256_file(ROOT/path) for path in config["core_logic_files"]}; person_specific_mentions={path:sum((ROOT/path).read_text(encoding="utf-8").count(token) for token in ("synthetic_mira","synthetic_ren")) for path in config["core_logic_files"]}
    normalizations=[{"event_id":row["event_id"],**change} for row in feature_records for change in row.get("numeric_boundary_normalizations",[])]
    contract=config["engineering_contract"]; total_calls=len(feature_records)+len(recording.records)
    engineering={"rolling_test_row_count":sum(row["condition"]=="MIRA_FULL_ADAPTATION" for row in transfer_rows)==int(contract["rolling_test_row_count"]),"transfer_condition_count":len({row["condition"] for row in transfer_rows})==int(contract["transfer_condition_count"]),"transfer_prediction_rows":len(transfer_rows)==int(contract["transfer_prediction_rows"]),"baseline_prediction_rows":len(baseline_rows)==int(contract["baseline_prediction_rows"]),"feature_extractor_calls":len(feature_records)==int(contract["feature_extractor_calls"]),"baseline_model_calls":len(recording.records)==int(contract["baseline_model_calls"]),"total_model_calls":total_calls==int(contract["total_model_calls"]),"future_leakage_violations":validation["future_leakage_violations"]==int(contract["future_leakage_violations"]),"person_specific_core_changes":sum(person_specific_mentions.values())==int(contract["person_specific_core_changes"]),"language_realization_performed":not any(row.get("language_realization_performed") for row in all_rows)}
    return {"schema":"ilhdt_m9_second_person_transfer_result_v1","status":"complete_hypothesis_run" if all(engineering.values()) else "failed_engineering_gate","claim_level":config["claim_level"],"formal_target_claim":False,"validation":validation,"rows":all_rows,"metrics":metrics,"rolling_metrics":rolling_metrics,"transfer_hypothesis_checks":checks,"transfer_hypotheses_supported":all(checks.values()),"engineering_gate_checks":engineering,"engineering_gate_pass":all(engineering.values()),"core_logic_hashes":core_hashes,"person_specific_core_mentions":person_specific_mentions,"parser_normalizations":normalizations,"feature_extraction_records":feature_records,"baseline_summaries":summaries,"provider_records":{"feature_extractor":feature_records,"baselines":recording.records},"resources":{"feature_extractor_calls":len(feature_records),"baseline_model_calls":len(recording.records),"total_model_calls":total_calls,"prompt_tokens":sum(r["prompt_tokens"] for r in feature_records)+sum(r["prompt_tokens"] for r in recording.records),"completion_tokens":sum(r["completion_tokens"] for r in feature_records)+sum(r["completion_tokens"] for r in recording.records),"model_latency_seconds":sum(r["latency_seconds"] for r in feature_records)+sum(r["latency_seconds"] for r in recording.records),"numeric_transfer_seconds":numeric_seconds},"language_realization_performed":False,"limitations":list(config["non_claims"])}


def parse_args(argv):
    p=argparse.ArgumentParser(); p.add_argument("--mode",choices=("validate","run"),default="validate"); p.add_argument("--config",required=True); p.add_argument("--lock",required=True); p.add_argument("--output"); return p.parse_args(argv)


def main(argv=None):
    args=parse_args(argv or sys.argv[1:]); cp=ROOT/args.config; lp=ROOT/args.lock; config=load_json(cp); lock=load_json(lp); names=("second_person_dataset","source_person_dataset","source_person_result","m5_dataset","m5_result","m6_overlay"); loaded={name:load_json(ROOT/config[name]["path"]) for name in names}; inputs=validate_inputs(loaded["second_person_dataset"],loaded["source_person_dataset"],loaded["source_person_result"],config); errors=verify_lock(lock,repo_root=ROOT)
    for name in names:
        if sha256_file(ROOT/config[name]["path"])!=config[name]["sha256"]: errors.append(f"{name} hash mismatch")
    validation={"schema":"ilhdt_m9_validation_v1","valid":inputs["valid"] and not errors,"inputs":inputs,"lock_errors":errors,"config_sha256":sha256_file(cp),"lock_sha256":sha256_file(lp)}
    if args.mode=="validate": print(json.dumps(validation,ensure_ascii=False,indent=2,sort_keys=True)); return 0 if validation["valid"] else 2
    if not validation["valid"]: raise SystemExit("M9 frozen validation failed")
    if not args.output: raise SystemExit("--output required")
    try: result=run_experiment(loaded["second_person_dataset"],loaded["source_person_dataset"],loaded["source_person_result"],config,loaded["m5_dataset"],loaded["m5_result"],loaded["m6_overlay"],provider=OllamaProvider(timeout=int(config["provider_timeout_seconds"])))
    except M9ExecutionFailure as exc: result={"schema":"ilhdt_m9_second_person_transfer_result_v1","status":"provider_failed_no_retry","failed_stage":exc.stage,"error":str(exc.cause),"completed_records":exc.completed,"engineering_gate_pass":False,"transfer_hypotheses_supported":False}
    result["validation"]=validation; result["experiment_lock"]=lock; result["environment"]=runtime_snapshot(); result["git"]=git_snapshot(ROOT); write_json_atomic(ROOT/args.output,result); print(json.dumps({"output":str(ROOT/args.output),"status":result["status"],"transfer_hypotheses_supported":result.get("transfer_hypotheses_supported")},indent=2)); return 0 if result.get("engineering_gate_pass") else 3


if __name__=="__main__": raise SystemExit(main())
