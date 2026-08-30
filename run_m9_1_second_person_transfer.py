#!/usr/bin/env python3
"""Run the one-key B4 summary alias remediation for M9.1."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from longitudinal_human_model.baselines import OllamaProvider
from longitudinal_human_model.registry import git_snapshot, load_json, runtime_snapshot, sha256_file, verify_lock, write_json_atomic
from longitudinal_human_model.summary_parser_v1_1 import SummaryAliasProvider
import run_m9_second_person_transfer as base


ROOT=Path(__file__).resolve().parent


def run_remediation(mira,ren,source,config,m5d,m5r,overlay,*,provider):
    wrapped=SummaryAliasProvider(provider)
    result=base.run_experiment(mira,ren,source,config,m5d,m5r,overlay,provider=wrapped)
    result["schema"]="ilhdt_m9_1_second_person_transfer_result_v1"; result["claim_level"]=config["claim_level"]
    result["summary_parser_remediation"]={"single_change":"behavior_prediction_summary alias accepted for B4 summary","normalization_count":len(wrapped.normalizations),"normalizations":wrapped.normalizations,"prompt_changed":False,"data_changed":False,"hypotheses_changed":False,"retry_within_run":False}
    return result


def parse_args(argv):
    p=argparse.ArgumentParser(); p.add_argument("--mode",choices=("validate","run"),default="validate"); p.add_argument("--amendment",required=True); p.add_argument("--lock",required=True); p.add_argument("--output"); return p.parse_args(argv)


def main(argv=None):
    args=parse_args(argv or sys.argv[1:]); ap=ROOT/args.amendment; lp=ROOT/args.lock; amendment=load_json(ap); lock=load_json(lp); bp=ROOT/amendment["base_config"]["path"]; config=load_json(bp); config=dict(config); config["claim_level"]=amendment["claim_level"]
    names=("second_person_dataset","source_person_dataset","source_person_result","m5_dataset","m5_result","m6_overlay"); loaded={name:load_json(ROOT/config[name]["path"]) for name in names}; inputs=base.validate_inputs(loaded["second_person_dataset"],loaded["source_person_dataset"],loaded["source_person_result"],config); errors=verify_lock(lock,repo_root=ROOT)
    if sha256_file(bp)!=amendment["base_config"]["sha256"]: errors.append("base config hash mismatch")
    fp=ROOT/amendment["first_failure"]["path"]
    if sha256_file(fp)!=amendment["first_failure"]["sha256"]: errors.append("first failure hash mismatch")
    for name in names:
        if sha256_file(ROOT/config[name]["path"])!=config[name]["sha256"]: errors.append(f"{name} hash mismatch")
    validation={"schema":"ilhdt_m9_1_validation_v1","valid":inputs["valid"] and not errors,"inputs":inputs,"lock_errors":errors,"amendment_sha256":sha256_file(ap),"base_config_sha256":sha256_file(bp),"lock_sha256":sha256_file(lp)}
    if args.mode=="validate": print(json.dumps(validation,ensure_ascii=False,indent=2,sort_keys=True)); return 0 if validation["valid"] else 2
    if not validation["valid"]: raise SystemExit("M9.1 frozen validation failed")
    if not args.output: raise SystemExit("--output required")
    try: result=run_remediation(loaded["second_person_dataset"],loaded["source_person_dataset"],loaded["source_person_result"],config,loaded["m5_dataset"],loaded["m5_result"],loaded["m6_overlay"],provider=OllamaProvider(timeout=int(config["provider_timeout_seconds"])))
    except base.M9ExecutionFailure as exc: result={"schema":"ilhdt_m9_1_second_person_transfer_result_v1","status":"provider_failed_no_retry","failed_stage":exc.stage,"error":str(exc.cause),"completed_records":exc.completed,"engineering_gate_pass":False,"transfer_hypotheses_supported":False}
    result["validation"]=validation; result["amendment"]=amendment; result["experiment_lock"]=lock; result["environment"]=runtime_snapshot(); result["git"]=git_snapshot(ROOT); write_json_atomic(ROOT/args.output,result); print(json.dumps({"output":str(ROOT/args.output),"status":result["status"],"transfer_hypotheses_supported":result.get("transfer_hypotheses_supported"),"summary_alias_normalizations":result.get("summary_parser_remediation",{}).get("normalization_count")},indent=2)); return 0 if result.get("engineering_gate_pass") else 3


if __name__=="__main__": raise SystemExit(main())
