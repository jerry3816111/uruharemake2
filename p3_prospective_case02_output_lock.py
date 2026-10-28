#!/usr/bin/env python3
"""P3-B38 one-time execution wrapper for prospective case02 strict output lock."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
from typing import Any, Mapping

import p3_case03_dual_condition_output_lock as engine
import p3_case05_dual_condition_output_lock as helper
import p3_prospective_case01_output_lock as prior
import p3_prospective_case02_output_lock_contract as contract
from p3_product_comparison import P3ContractError, write_new_json
from p3_product_worker import summarize_checkpoint_evidence


RELEASE_SCHEMA = "uruha_p3_prospective_case02_output_lock_release_v1"
RESULT_SCHEMA = "uruha_p3_prospective_case02_output_lock_result_v1"


def validate_release(path: str | Path, config: Mapping[str, Any]) -> dict[str, Any]:
    release_path = Path(path).resolve()
    release = helper._read(release_path)
    if (
        release.get("schema") != RELEASE_SCHEMA
        or release.get("phase") != "P3-B38"
        or release.get("status") != "released_for_prospective_case02_strict_output_lock"
    ):
        raise P3ContractError("p3_b38_release_invalid")
    expected = {
        "config": "configs/p3_prospective_case02_output_lock_v1.json",
        "contract": "p3_prospective_case02_output_lock_contract.py",
        "wrapper": "p3_prospective_case02_output_lock.py",
        "strict_surface": "p3_strict_visible_surface.py",
        "engine": "p3_case03_dual_condition_output_lock.py",
        "accounting_helper": "p3_case05_dual_condition_output_lock.py",
        "tests": "test_p3_prospective_case02_output_lock.py",
        "preflight": "analysis/p3_b37_prospective_case02_output_lock_preflight_2026-09-17.json",
        "contract_freeze": "research/p3_b37_prospective_case02_output_lock_contract_freeze_2026-09-17.json",
    }
    if set(release.get("artifacts", {})) != set(expected):
        raise P3ContractError("p3_b38_release_artifacts_invalid")
    repo = release_path.parent.parent
    for name, relative in expected.items():
        actual = {"path": relative, "sha256": hashlib.sha256((repo / relative).read_bytes()).hexdigest()}
        if release["artifacts"][name] != actual:
            raise P3ContractError("p3_b38_release_artifact_mismatch", name)
    if release.get("authorization") != {
        "run_id": "p3-b38-prospective-case02-strict-output-lock-v1",
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
        "strict_japanese_surface_required": True,
        "automatic_retry": False,
        "stop_on_first_failure": True,
        "checkpoint_root": "analysis/p3_b38_prospective_case02_output_lock_checkpoints_v1",
        "result_path": "analysis/p3_b38_prospective_case02_output_lock_result_2026-09-17.json",
        "annotation_access": False,
        "confirmation_access": False,
        "production_database_access": False,
        "external_deployment": False,
    }:
        raise P3ContractError("p3_b38_release_authorization_invalid")
    preflight = helper._read(repo / expected["preflight"])
    freeze = helper._read(repo / expected["contract_freeze"])
    if (
        preflight.get("status") != "ready_for_prospective_case02_output_lock_review"
        or not all((preflight.get("checks") or {}).values())
        or freeze.get("status") != "prospective_case02_strict_output_lock_contract_frozen"
        or config.get("strict_surface_contract", {}).get("required_status")
        != "b35_surface_gate_failure_frozen"
    ):
        raise P3ContractError("p3_b38_release_preflight_invalid")
    return release


def transform_result(result: Mapping[str, Any], evidence: Mapping[str, Any]) -> dict[str, Any]:
    transformed = prior.transform_result(result, evidence)
    checks = dict(transformed["checks"])
    strict_pass = checks.pop("all_eight_shared_surface_pass", False)
    checks["all_eight_strict_japanese_surface_pass"] = strict_pass
    transformed.update({
        "schema": RESULT_SCHEMA,
        "phase": "P3-B38",
        "status": "prospective_case02_outputs_locked" if all(checks.values())
        else "prospective_case02_output_lock_failed_retained",
        "case_id": contract.CASE_ID,
        "checks": checks,
        "formal_holdout": False,
        "quality_result": "not_evaluated_until_later_predeclared_grade",
        "claim_boundary": (
            "Second source-order prospective developer case outputs are locked before annotation. "
            "This is strict-surface generation evidence only, not a holdout, preference, or advantage result."
        ),
    })
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
        raise P3ContractError("p3_b38_result_path_mismatch")
    original_load, original_validate = engine.load_config, engine.validate_release
    engine.load_config = lambda _unused: config
    engine.validate_release = lambda _unused, _loaded: release
    try:
        result = engine.run_case(config_path, release_path, checkpoint_root)
    finally:
        engine.load_config, engine.validate_release = original_load, original_validate
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
        payload = run_case(args.config, args.release, args.checkpoint_root, output)
    except P3ContractError as exc:
        evidence = summarize_checkpoint_evidence(args.checkpoint_root)
        payload = {
            "schema": "uruha_p3_prospective_case02_output_lock_failure_v1",
            "phase": "P3-B38",
            "status": "failed_after_transport_retained" if evidence["declared_invocation_intents"]
            else "refused_before_transport",
            "contract_code": exc.code,
            "checkpoint_evidence": evidence,
            "automatic_retry": False,
            "annotations_accessed": 0,
            "claim_boundary": "Failure retained; no quality, preference, or advantage claim is authorized.",
        }
    write_new_json(output, payload)
    return 0 if payload.get("status") == "prospective_case02_outputs_locked" else 1


if __name__ == "__main__":
    raise SystemExit(main())

