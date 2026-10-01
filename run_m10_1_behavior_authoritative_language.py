#!/usr/bin/env python3
"""Run M10.1 with only the frozen classifier-key alias remediation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from longitudinal_human_model.realization_parser_v1_1 import ClassifierAliasParser
from longitudinal_human_model.registry import (
    git_snapshot,
    load_json,
    runtime_snapshot,
    sha256_file,
    verify_lock,
    write_json_atomic,
)
import run_m10_behavior_authoritative_language as base


ROOT = Path(__file__).resolve().parent


def run_remediation(dataset, m9_result, persona, persona_lock, config, *, text_provider, classifier_provider):
    parser = ClassifierAliasParser()
    original = base.parse_classifier_reply
    base.parse_classifier_reply = parser
    try:
        result = base.run_experiment(
            dataset,
            m9_result,
            persona,
            persona_lock,
            config,
            text_provider=text_provider,
            classifier_provider=classifier_provider,
        )
    finally:
        base.parse_classifier_reply = original
    result["schema"] = "ilhdt_m10_1_behavior_authoritative_language_result_v1"
    result["summary_parser_remediation"] = {
        "single_change": "classification alias accepted as probabilities",
        "normalization_count": len(parser.normalizations),
        "normalizations": parser.normalizations,
        "prompt_changed": False,
        "data_changed": False,
        "hypotheses_changed": False,
        "retry_within_first_run": False,
    }
    return result


def parse_args(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("validate", "run"), default="validate")
    parser.add_argument("--amendment", required=True)
    parser.add_argument("--lock", required=True)
    parser.add_argument("--output")
    parser.add_argument("--blind-packet")
    parser.add_argument("--blind-key")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv or sys.argv[1:])
    amendment_path, lock_path = ROOT / args.amendment, ROOT / args.lock
    amendment, lock = load_json(amendment_path), load_json(lock_path)
    config_path = ROOT / amendment["base_config"]["path"]
    config = load_json(config_path)
    loaded = {
        name: load_json(ROOT / record["path"])
        for name, record in config["inputs"].items()
    }
    validation = base.validate_inputs(
        loaded["second_person_dataset"],
        loaded["m9_result"],
        loaded["persona_evidence"],
        loaded["persona_evidence_result_lock"],
        config,
    )
    errors = verify_lock(lock, repo_root=ROOT)
    for key in ("base_config", "base_lock", "first_failure", "first_failure_lock"):
        record = amendment[key]
        expected = record["sha256"]
        if expected != "TO_BE_BOUND_IN_M10_1_LOCK" and sha256_file(ROOT / record["path"]) != expected:
            errors.append(f"amendment hash mismatch: {key}")
    validation["lock_errors"] = errors
    validation["valid"] = validation["valid"] and not errors
    validation["amendment_sha256"] = sha256_file(amendment_path)
    validation["lock_sha256"] = sha256_file(lock_path)
    if args.mode == "validate":
        print(json.dumps(validation, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if validation["valid"] else 2
    if not validation["valid"]:
        raise SystemExit("M10.1 frozen validation failed")
    if not args.output or not args.blind_packet or not args.blind_key:
        raise SystemExit("--output, --blind-packet, and --blind-key are required")
    provider = base.OllamaTextProvider(timeout=int(config["provider_timeout_seconds"]))
    try:
        result = run_remediation(
            loaded["second_person_dataset"],
            loaded["m9_result"],
            loaded["persona_evidence"],
            loaded["persona_evidence_result_lock"],
            config,
            text_provider=provider,
            classifier_provider=provider,
        )
    except base.M10ExecutionFailure as exc:
        result = {
            "schema": "ilhdt_m10_1_behavior_authoritative_language_result_v1",
            "status": "provider_failed_no_retry",
            "failed_stage": exc.stage,
            "error": str(exc.cause),
            "completed_records": exc.completed,
            "all_hypotheses_supported": False,
            "human_preference_supported": False,
        }
    result["validation"] = validation
    result["amendment"] = amendment
    result["experiment_lock"] = lock
    result["environment"] = runtime_snapshot()
    result["git"] = git_snapshot(ROOT)
    write_json_atomic(ROOT / args.output, result)
    if result.get("status") == "complete_hypothesis_run":
        packet, key = base.build_blind_packet(result, seed=int(config["generation_options"]["seed"]))
        write_json_atomic(ROOT / args.blind_packet, packet)
        write_json_atomic(ROOT / args.blind_key, key)
    print(json.dumps({
        "output": str(ROOT / args.output),
        "status": result["status"],
        "all_hypotheses_supported": result.get("all_hypotheses_supported"),
        "alias_normalizations": (result.get("summary_parser_remediation") or {}).get("normalization_count"),
        "resources": result.get("resources"),
    }, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "complete_hypothesis_run" else 3


if __name__ == "__main__":
    raise SystemExit(main())
