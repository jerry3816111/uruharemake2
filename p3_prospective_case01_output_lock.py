#!/usr/bin/env python3
"""P3-B35 one-time execution wrapper for prospective case01 output lock."""

from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
from pathlib import Path
from typing import Any, Mapping

import p3_case03_dual_condition_output_lock as engine
import p3_case05_dual_condition_output_lock as helper
import p3_prospective_case01_output_lock_contract as contract
from p3_product_comparison import P3ContractError, write_new_json
from p3_product_worker import summarize_checkpoint_evidence


RELEASE_SCHEMA = "uruha_p3_prospective_case01_output_lock_release_v1"
RESULT_SCHEMA = "uruha_p3_prospective_case01_output_lock_result_v1"


def validate_release(path: str | Path, config: Mapping[str, Any]) -> dict[str, Any]:
    release_path = Path(path).resolve()
    release = helper._read(release_path)
    if (
        release.get("schema") != RELEASE_SCHEMA
        or release.get("phase") != "P3-B35"
        or release.get("status") != "released_for_prospective_case01_output_lock"
    ):
        raise P3ContractError("p3_b35_release_invalid")
    expected = {
        "config": "configs/p3_prospective_case01_output_lock_v1.json",
        "contract": "p3_prospective_case01_output_lock_contract.py",
        "wrapper": "p3_prospective_case01_output_lock.py",
        "engine": "p3_case03_dual_condition_output_lock.py",
        "accounting_helper": "p3_case05_dual_condition_output_lock.py",
        "tests": "test_p3_prospective_case01_output_lock.py",
        "preflight": "analysis/p3_b34_prospective_case01_output_lock_preflight_2026-09-17.json",
        "contract_freeze": "research/p3_b34_prospective_case01_output_lock_contract_freeze_2026-09-17.json",
    }
    if set(release.get("artifacts", {})) != set(expected):
        raise P3ContractError("p3_b35_release_artifacts_invalid")
    repo = release_path.parent.parent
    for name, relative in expected.items():
        actual = {
            "path": relative,
            "sha256": hashlib.sha256((repo / relative).read_bytes()).hexdigest(),
        }
        if release["artifacts"][name] != actual:
            raise P3ContractError("p3_b35_release_artifact_mismatch", name)
    if release.get("authorization") != {
        "run_id": "p3-b35-prospective-case01-output-lock-v1",
        "localhost_only": True,
        "model": "qwen2.5:7b",
        "model_digest": contract.MODEL_DIGEST,
        "case_id": contract.CASE_ID,
        "turn_ids": contract.TURN_IDS,
        "product_provider_calls_min": 0,
        "product_provider_calls_max": 16,
        "direct_provider_calls_exact": 4,
        "total_provider_calls_max": 20,
        "turn_intents_exact": 8,
        "completed_turn_records_exact": 8,
        "automatic_retry": False,
        "stop_on_first_failure": True,
        "checkpoint_root": "analysis/p3_b35_prospective_case01_output_lock_checkpoints_v1",
        "result_path": "analysis/p3_b35_prospective_case01_output_lock_result_2026-09-17.json",
        "annotation_access": False,
        "confirmation_access": False,
        "production_database_access": False,
        "external_deployment": False,
    }:
        raise P3ContractError("p3_b35_release_authorization_invalid")
    preflight = helper._read(repo / expected["preflight"])
    freeze = helper._read(repo / expected["contract_freeze"])
    if (
        preflight.get("status") != "ready_for_prospective_case01_output_lock_review"
        or not all((preflight.get("checks") or {}).values())
        or freeze.get("status") != "prospective_case01_output_lock_contract_frozen"
    ):
        raise P3ContractError("p3_b35_release_preflight_invalid")
    return release


def transform_result(result: Mapping[str, Any], evidence: Mapping[str, Any]) -> dict[str, Any]:
    transformed = deepcopy(dict(result))
    checks = dict(transformed.get("checks", {}))
    checks.pop("all_provider_calls_accounted", None)
    calls_ok, records_ok, product_count, direct_count = helper._actual_call_accounting(
        transformed,
        evidence,
    )
    checks["all_actual_provider_and_network_calls_accounted"] = calls_ok
    checks["all_eight_turn_intents_and_completions_accounted"] = records_ok
    transformed.update({
        "schema": RESULT_SCHEMA,
        "phase": "P3-B35",
        "status": "prospective_case01_outputs_locked" if all(checks.values())
        else "prospective_case01_output_lock_failed_retained",
        "case_id": contract.CASE_ID,
        "checks": checks,
        "checkpoint_evidence": dict(evidence),
        "product_provider_calls": product_count,
        "direct_provider_calls": direct_count,
        "provider_call_evidence": product_count + direct_count,
        "real_model_calls": product_count + direct_count,
        "network_calls": product_count + direct_count,
        "prior_case_calls_reused_or_counted": False,
        "annotations_accessed": 0,
        "confirmation_accessed": 0,
        "production_database_accessed": False,
        "formal_holdout": False,
        "quality_result": "not_evaluated_until_later_annotation_and_blind_grade",
        "claim_boundary": (
            "Prospective developer case01 outputs are locked before annotation access. This is "
            "generation evidence only, not a formal holdout, human preference, product advantage, "
            "or permission to inspect future case annotations."
        ),
    })
    transformed.pop("b15_calls_reused_or_counted", None)
    return transformed


def run_case(
    config_path: str | Path,
    release_path: str | Path,
    checkpoint_root: str | Path,
    result_path: str | Path | None = None,
) -> dict[str, Any]:
    config = contract.load_config(config_path)
    release = validate_release(release_path, config)
    repo = Path(release_path).resolve().parent.parent
    if result_path is not None and Path(result_path).resolve() != (
        repo / release["authorization"]["result_path"]
    ).resolve():
        raise P3ContractError("p3_b35_result_path_mismatch")
    original_load = engine.load_config
    original_validate = engine.validate_release
    engine.load_config = lambda _unused: config
    engine.validate_release = lambda _unused, _loaded: release
    try:
        result = engine.run_case(config_path, release_path, checkpoint_root)
    finally:
        engine.load_config = original_load
        engine.validate_release = original_validate
    return transform_result(result, summarize_checkpoint_evidence(checkpoint_root))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--release", required=True)
    parser.add_argument("--checkpoint-root", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = Path(args.output)
    if output.exists():
        return 2
    try:
        payload = run_case(
            args.config,
            args.release,
            args.checkpoint_root,
            output,
        )
    except P3ContractError as exc:
        evidence = summarize_checkpoint_evidence(args.checkpoint_root)
        payload = {
            "schema": "uruha_p3_prospective_case01_output_lock_failure_v1",
            "phase": "P3-B35",
            "status": "failed_after_transport_retained" if evidence["declared_invocation_intents"]
            else "refused_before_transport",
            "contract_code": exc.code,
            "checkpoint_evidence": evidence,
            "automatic_retry": False,
            "annotations_accessed": 0,
            "claim_boundary": "Failure retained; no quality, holdout, preference, or advantage claim is authorized.",
        }
    write_new_json(output, payload)
    return 0 if payload.get("status") == "prospective_case01_outputs_locked" else 1


if __name__ == "__main__":
    raise SystemExit(main())
