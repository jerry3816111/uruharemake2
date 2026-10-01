#!/usr/bin/env python3
"""P3-B18 synthetic comparison of JSON object and JSON-schema judge constraints."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import time
from typing import Any, Mapping

from p3_case03_proxy_grade import (
    _ollama_model_metadata, _read, _signed, _write_checkpoint,
    build_messages, local_transport, validate_judgment,
)
from p3_product_comparison import P3ContractError, canonical_sha256, write_new_json
from p3_product_worker import localhost_network_only, summarize_checkpoint_evidence


SCHEMA = "uruha_p3_judge_json_conformance_probe_v1"
RELEASE_SCHEMA = "uruha_p3_judge_json_conformance_probe_release_v1"


def load_config(path: str | Path) -> dict[str, Any]:
    config_path = Path(path).resolve()
    raw = _read(config_path)
    if set(raw) != {
        "schema", "status", "purpose", "before_failure", "synthetic_fixture",
        "conditions", "judge", "response_formats", "execution_boundary", "success",
    } or raw.get("schema") != SCHEMA:
        raise P3ContractError("p3_b18_schema_mismatch")
    if raw.get("status") != "preregistered_not_executed" or raw.get("purpose") != "isolate_json_serialization_constraint_after_b17_truncation":
        raise P3ContractError("p3_b18_status_mismatch")
    repo = config_path.parent.parent
    before = raw.get("before_failure")
    if before != {
        "path": "analysis/p3_b17_case03_proxy_grade_result_2026-09-15.json",
        "sha256": "ee2e39a2ef8fed10b279b7df519c641667d49836eb8e812c68ca54fe06e6e3f4",
        "required_status": "failed_after_judge_intent_retained",
    }:
        raise P3ContractError("p3_b18_before_binding_invalid")
    before_path = (repo / before["path"]).resolve()
    if not before_path.is_file() or hashlib.sha256(before_path.read_bytes()).hexdigest() != before["sha256"] or _read(before_path).get("status") != before["required_status"]:
        raise P3ContractError("p3_b18_before_binding_invalid")
    fixture = raw.get("synthetic_fixture")
    if not isinstance(fixture, Mapping) or fixture.get("fixture_id") != "p3-b18-schema-only-01" or fixture.get("visible_history") != []:
        raise P3ContractError("p3_b18_fixture_invalid")
    if raw.get("conditions") != ["json_object", "json_schema"] or set(raw.get("response_formats", {})) != set(raw["conditions"]):
        raise P3ContractError("p3_b18_conditions_invalid")
    judge = raw.get("judge")
    if judge != {
        "model": "qwen3.5:9b", "digest": "dec52a44569a2a25341c4e4d3fee25846eed4f6f0b936278e3a3c900bb99d37c",
        "temperature": 0, "seed": 20260909, "top_p": 1, "num_ctx": 8192,
        "think": False, "max_completion_tokens": 384, "timeout_seconds": 30, "retries": 0,
    }:
        raise P3ContractError("p3_b18_judge_drift")
    if raw.get("execution_boundary") != {
        "calls_exact": 2, "one_call_per_condition": True, "automatic_retry": False,
        "continue_after_received_invalid_response": True, "stop_after_transport_uncertainty": True,
        "localhost_only": True, "developer_case_access": False, "annotation_file_access": False,
        "confirmation_access": False, "production_database_access": False,
        "remote_paid_calls": False, "real_model_calls_authorized_by_this_config": False,
        "separate_release_required": True,
    }:
        raise P3ContractError("p3_b18_boundary_drift")
    if raw.get("success") != {
        "json_schema_complete_and_strictly_valid": True, "both_conditions_exactly_accounted": True,
        "no_retry": True, "authorizes_case03_rerun": False, "authorizes_quality_claim": False,
    }:
        raise P3ContractError("p3_b18_success_drift")
    result = json.loads(json.dumps(raw, ensure_ascii=False))
    result.update({"_repo": repo, "_config_path": config_path, "_config_sha256": hashlib.sha256(config_path.read_bytes()).hexdigest()})
    return result


def synthetic_item(config: Mapping[str, Any]) -> dict[str, Any]:
    fixture = config["synthetic_fixture"]
    turn = fixture["current_turn"]
    return {
        "item_id": fixture["fixture_id"], "turn_id": turn["turn_id"], "order": "synthetic",
        "visible_history": fixture["visible_history"], "current_input": turn["content"],
        "annotation": fixture["annotation"], "anonymous_replies": fixture["anonymous_replies"],
        "currently_visible_turn_ids": [turn["turn_id"]],
    }


def build_preflight(config_path: str | Path) -> dict[str, Any]:
    config = load_config(config_path)
    metadata = _ollama_model_metadata(config["judge"]["model"])
    item = synthetic_item(config)
    messages = build_messages(item)
    object_format, schema_format = (config["response_formats"][x] for x in config["conditions"])
    checks = {
        "judge_digest_exact": metadata["digest"] == config["judge"]["digest"],
        "zero_generation_calls": metadata["generation_calls"] == 0,
        "same_synthetic_prompt_for_both_conditions": True,
        "only_response_format_changes": object_format == {"type": "json_object"} and schema_format.get("type") == "json_schema",
        "no_developer_or_annotation_data": config["execution_boundary"]["developer_case_access"] is config["execution_boundary"]["annotation_file_access"] is False,
    }
    return {
        "schema": "uruha_p3_judge_json_conformance_probe_preflight_v1", "phase": "P3-B18",
        "status": "ready_for_judge_conformance_review" if all(checks.values()) else "not_ready_for_judge_conformance_review",
        "config_sha256": config["_config_sha256"], "checks": checks, "judge_metadata": metadata,
        "synthetic_prompt_sha256": canonical_sha256(messages),
        "response_format_sha256": {k: canonical_sha256(v) for k, v in config["response_formats"].items()},
        "real_model_calls": 0, "network_calls": 0, "paid_calls": 0,
        "developer_case_accessed": 0, "annotation_turns_accessed": 0, "confirmation_accessed": 0,
        "claim_boundary": "Synthetic readiness only; no judge inference and no product-quality evidence.",
    }


def verify_release(config: Mapping[str, Any], release_path: str | Path, preflight_path: str | Path) -> None:
    release, preflight = _read(Path(release_path)), _read(Path(preflight_path))
    if release.get("schema") != RELEASE_SCHEMA or release.get("phase") != "P3-B18" or release.get("status") != "released_for_judge_conformance_probe":
        raise P3ContractError("p3_b18_release_invalid")
    expected = {
        "config": "configs/p3_judge_json_conformance_probe_v1.json",
        "implementation": "p3_judge_json_conformance_probe.py",
        "shared_judge": "p3_case03_proxy_grade.py",
        "tests": "test_p3_judge_json_conformance_probe.py",
        "preflight": "analysis/p3_b18_judge_json_conformance_preflight_2026-09-15.json",
    }
    if set(release.get("artifacts", {})) != set(expected):
        raise P3ContractError("p3_b18_release_artifacts_invalid")
    for name, relative in expected.items():
        path = config["_repo"] / relative
        if release["artifacts"][name] != {"path": relative, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}:
            raise P3ContractError("p3_b18_release_artifact_mismatch", name)
    if preflight.get("status") != "ready_for_judge_conformance_review":
        raise P3ContractError("p3_b18_preflight_invalid")
    if release.get("authorization") != {
        "calls_exact": 2, "automatic_retry": False, "localhost_only": True,
        "checkpoint_root": "analysis/p3_b18_judge_json_conformance_checkpoints_v1",
        "result_path": "analysis/p3_b18_judge_json_conformance_result_2026-09-15.json",
        "case03_rerun": False, "quality_claim": False,
    }:
        raise P3ContractError("p3_b18_authorization_invalid")


def failure_record(condition: str, exc: Exception, response: Mapping[str, Any] | None) -> dict[str, Any]:
    received = isinstance(response, Mapping) and isinstance(response.get("content"), str)
    return _signed({
        "schema": "uruha_p3_judge_json_conformance_failure_v1", "phase": "P3-B18",
        "item_id": condition, "error_type": type(exc).__name__,
        "contract_code": getattr(exc, "code", "transport_or_validation_failure"),
        "response_received": received,
        "raw_content_sha256": canonical_sha256(response["content"]) if received else None,
        "finish_reason": response.get("finish_reason") if received else None,
        "provider_actual_usage": ({
            "prompt_tokens": response.get("prompt_tokens"), "completion_tokens": response.get("completion_tokens"),
            "wall_seconds": response.get("wall_seconds"), "real_model_calls": response.get("real_model_calls"),
            "network_calls": response.get("network_calls"),
        } if received else None),
        "retry_performed": False,
    })


def run_probe(config_path: str | Path, release_path: str | Path, preflight_path: str | Path, checkpoint_root: str | Path) -> dict[str, Any]:
    config = load_config(config_path)
    verify_release(config, release_path, preflight_path)
    root = Path(checkpoint_root)
    if root.exists():
        raise P3ContractError("p3_b18_checkpoint_root_exists")
    item, messages = synthetic_item(config), None
    messages = build_messages(item)
    rows: list[dict[str, Any]] = []
    started = time.monotonic()
    with localhost_network_only() as attempts:
        for condition in config["conditions"]:
            folder = root / condition
            _write_checkpoint(folder / "intent.json", _signed({
                "schema": "uruha_p3_judge_json_conformance_intent_v1", "phase": "P3-B18",
                "item_id": condition, "prompt_sha256": canonical_sha256(messages),
                "response_format_sha256": canonical_sha256(config["response_formats"][condition]),
                "automatic_retry": False,
            }))
            response: dict[str, Any] | None = None
            try:
                response = local_transport(config, messages, response_format=config["response_formats"][condition])
                judgment = validate_judgment(response["content"], item)
            except Exception as exc:
                failure = failure_record(condition, exc, response)
                _write_checkpoint(folder / "failure.json", failure)
                rows.append({"condition": condition, "valid": False, "failure": {k: failure[k] for k in ("contract_code", "response_received", "raw_content_sha256", "finish_reason", "provider_actual_usage")}})
                if not failure["response_received"]:
                    break
                continue
            complete = _signed({
                "schema": "uruha_p3_judge_json_conformance_complete_v1", "phase": "P3-B18",
                "item_id": condition, "judgment": judgment, "raw_content_sha256": canonical_sha256(response["content"]),
                "finish_reason": response["finish_reason"], "usage": {k: response[k] for k in ("prompt_tokens", "completion_tokens", "wall_seconds")},
                "result": {"real_model_calls": response["real_model_calls"], "network_calls": response["network_calls"]},
                "retry_performed": False,
            })
            _write_checkpoint(folder / "complete.json", complete)
            rows.append({"condition": condition, "valid": True, "judgment": judgment, "finish_reason": response["finish_reason"], "usage": complete["usage"]})
    evidence = summarize_checkpoint_evidence(root)
    by_condition = {row["condition"]: row for row in rows}
    checks = {
        "two_conditions_attempted": set(by_condition) == set(config["conditions"]),
        "json_schema_complete_and_strictly_valid": by_condition.get("json_schema", {}).get("valid") is True,
        "both_conditions_exactly_accounted": evidence["provider_call_evidence"] == evidence["network_call_evidence"] == 2,
        "no_retry": evidence["declared_invocation_intents"] == 2,
        "localhost_only": all(x["loopback_allowed"] is True for x in attempts),
    }
    return {
        "schema": "uruha_p3_judge_json_conformance_probe_result_v1", "phase": "P3-B18",
        "status": "judge_json_schema_conformance_pass" if all(checks.values()) else "judge_json_conformance_failed_retained",
        "config_sha256": config["_config_sha256"], "release_sha256": hashlib.sha256(Path(release_path).read_bytes()).hexdigest(),
        "rows": rows, "checkpoint_evidence": evidence, "checks": checks, "network_attempts": attempts,
        "total_wall_seconds": round(time.monotonic() - started, 6), "paid_calls": 0,
        "developer_case_accessed": 0, "annotation_turns_accessed": 0, "confirmation_accessed": 0,
        "production_database_accessed": False, "case03_rerun": False,
        "claim_boundary": "A pass selects a bounded serialization constraint for a future fresh grading item only. It is not a case03 grade, product-quality result, holdout, or human preference evidence.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("preflight", "run"), required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--release")
    parser.add_argument("--preflight")
    parser.add_argument("--checkpoint-root")
    args = parser.parse_args()
    output = Path(args.output)
    if output.exists():
        return 2
    try:
        if args.mode == "preflight":
            result = build_preflight(args.config)
        else:
            if not args.release or not args.preflight or not args.checkpoint_root:
                raise P3ContractError("p3_b18_run_artifacts_required")
            result = run_probe(args.config, args.release, args.preflight, args.checkpoint_root)
    except P3ContractError as exc:
        result = {
            "schema": "uruha_p3_judge_json_conformance_probe_refusal_v1", "phase": "P3-B18",
            "status": "refused_or_failed_retained", "contract_code": exc.code,
            "checkpoint_evidence": summarize_checkpoint_evidence(args.checkpoint_root or ""),
            "automatic_retry": False, "claim_boundary": "No conformance or quality claim is authorized.",
        }
    write_new_json(output, result)
    return 0 if result.get("status") in {"ready_for_judge_conformance_review", "judge_json_schema_conformance_pass"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
