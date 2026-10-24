#!/usr/bin/env python3
"""Run the one-change M8.1 bounded-numeric parser remediation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from longitudinal_human_model.baselines import OllamaProvider
from longitudinal_human_model.registry import git_snapshot, load_json, runtime_snapshot, sha256_file, verify_lock, write_json_atomic
from longitudinal_human_model.rolling_parser_v1_1 import extract_event_features_bounded
import run_m8_rolling_scaling as base_runner


ROOT = Path(__file__).resolve().parent


def run_remediation(dataset, config, m5_dataset, m5_result, m6_overlay, *, provider):
    original = base_runner.extract_event_features
    base_runner.extract_event_features = extract_event_features_bounded
    try:
        result = base_runner.run_experiment(dataset, config, m5_dataset, m5_result, m6_overlay, provider=provider)
    finally:
        base_runner.extract_event_features = original
    records = result["feature_extraction"]["records"]
    normalizations = [
        {"event_id": row["event_id"], **change}
        for row in records for change in row.get("numeric_boundary_normalizations", [])
    ]
    result["schema"] = "ilhdt_m8_1_rolling_scaling_result_v1"
    result["claim_level"] = config["claim_level"]
    result["parser_remediation"] = {
        "single_change": "finite numeric boundary clamp only",
        "normalization_count": len(normalizations),
        "normalizations": normalizations,
        "prompt_changed": False,
        "data_changed": False,
        "hypotheses_changed": False,
        "retry_within_run": False,
    }
    return result


def parse_args(argv):
    parser=argparse.ArgumentParser(); parser.add_argument("--mode",choices=("validate","run"),default="validate"); parser.add_argument("--amendment",required=True); parser.add_argument("--lock",required=True); parser.add_argument("--output"); return parser.parse_args(argv)


def main(argv=None):
    args=parse_args(argv or sys.argv[1:]); amendment_path=ROOT/args.amendment; lock_path=ROOT/args.lock; amendment=load_json(amendment_path); lock=load_json(lock_path)
    base_path=ROOT/amendment["base_config"]["path"]; config=load_json(base_path); config=dict(config); config["claim_level"]=amendment["claim_level"]
    names=("dataset","m5_dataset","m5_result","m6_overlay","m6_result","m71_result")
    loaded={name:load_json(ROOT/config[name]["path"]) for name in names}; input_validation=base_runner.validate_inputs(loaded["dataset"],config); errors=verify_lock(lock,repo_root=ROOT)
    if sha256_file(base_path)!=amendment["base_config"]["sha256"]: errors.append("base config hash mismatch")
    failure_path=ROOT/amendment["first_failure"]["path"]
    if sha256_file(failure_path)!=amendment["first_failure"]["sha256"]: errors.append("first failure hash mismatch")
    for name in names:
        if sha256_file(ROOT/config[name]["path"])!=config[name]["sha256"]: errors.append(f"{name} hash mismatch")
    validation={"schema":"ilhdt_m8_1_validation_v1","valid":input_validation["valid"] and not errors,"inputs":input_validation,"lock_errors":errors,"amendment_sha256":sha256_file(amendment_path),"base_config_sha256":sha256_file(base_path),"lock_sha256":sha256_file(lock_path)}
    if args.mode=="validate": print(json.dumps(validation,ensure_ascii=False,indent=2,sort_keys=True)); return 0 if validation["valid"] else 2
    if not validation["valid"]: raise SystemExit("M8.1 frozen validation failed")
    if not args.output: raise SystemExit("--output is required")
    try:
        result=run_remediation(loaded["dataset"],config,loaded["m5_dataset"],loaded["m5_result"],loaded["m6_overlay"],provider=OllamaProvider(timeout=int(config["provider_timeout_seconds"])))
    except base_runner.M8ExecutionFailure as exc:
        result={"schema":"ilhdt_m8_1_rolling_scaling_result_v1","status":"provider_failed_no_retry","failed_stage":exc.stage,"error":str(exc.cause),"completed_records":exc.completed,"engineering_gate_pass":False,"diagnostic_hypotheses_supported":False}
    result["validation"]=validation; result["amendment"]=amendment; result["experiment_lock"]=lock; result["environment"]=runtime_snapshot(); result["git"]=git_snapshot(ROOT); write_json_atomic(ROOT/args.output,result)
    print(json.dumps({"output":str(ROOT/args.output),"status":result["status"],"diagnostic_hypotheses_supported":result.get("diagnostic_hypotheses_supported"),"normalization_count":result.get("parser_remediation",{}).get("normalization_count")},indent=2)); return 0 if result.get("engineering_gate_pass") else 3


if __name__=="__main__": raise SystemExit(main())
