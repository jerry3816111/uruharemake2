#!/usr/bin/env python3
"""P3-B19 final synthetic native Ollama structured-output probe."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time
from typing import Any, Mapping
import urllib.request

from p3_case03_proxy_grade import (
    _ollama_model_metadata, _read, _signed, _write_checkpoint,
    build_messages, validate_judgment,
)
from p3_judge_json_conformance_probe import load_config as load_parent, synthetic_item
from p3_product_comparison import P3ContractError, canonical_sha256, write_new_json
from p3_product_worker import localhost_network_only, summarize_checkpoint_evidence


SCHEMA = "uruha_p3_native_judge_schema_probe_v1"
RELEASE_SCHEMA = "uruha_p3_native_judge_schema_probe_release_v1"


def ollama_version() -> str:
    try:
        result = subprocess.run(["ollama", "--version"], capture_output=True, text=True, check=False, timeout=10)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise P3ContractError("p3_b19_ollama_version_unavailable") from exc
    prefix = "ollama version is "
    value = result.stdout.strip()
    if result.returncode != 0 or not value.startswith(prefix):
        raise P3ContractError("p3_b19_ollama_version_unavailable")
    return value[len(prefix):]


def load_config(path: str | Path) -> dict[str, Any]:
    config_path = Path(path).resolve()
    raw = _read(config_path)
    if set(raw) != {
        "schema", "status", "purpose", "before_failure", "synthetic_parent",
        "single_variable", "transport", "judge", "execution_boundary", "success",
    } or raw.get("schema") != SCHEMA:
        raise P3ContractError("p3_b19_schema_mismatch")
    if raw.get("status") != "preregistered_not_executed" or raw.get("purpose") != "final_bounded_native_format_probe_after_openai_compatible_failure":
        raise P3ContractError("p3_b19_status_mismatch")
    repo = config_path.parent.parent
    before = raw.get("before_failure")
    if before != {
        "path": "analysis/p3_b18_judge_json_conformance_result_2026-09-15.json",
        "sha256": "01ac5ace960f1f1e052360f5ad3c9e6b20d8cb8e9a95cca8dc61250927dbaecb",
        "required_status": "judge_json_conformance_failed_retained",
    }:
        raise P3ContractError("p3_b19_before_invalid")
    before_path = repo / before["path"]
    if not before_path.is_file() or hashlib.sha256(before_path.read_bytes()).hexdigest() != before["sha256"] or _read(before_path).get("status") != before["required_status"]:
        raise P3ContractError("p3_b19_before_invalid")
    parent = raw.get("synthetic_parent")
    if parent != {
        "path": "configs/p3_judge_json_conformance_probe_v1.json",
        "sha256": "3c8a2d6daef397eac8edcb1c16e5e138d25ec0b9b09f77e8a3b236adabd421e4",
        "fixture_id": "p3-b18-schema-only-01",
    }:
        raise P3ContractError("p3_b19_parent_invalid")
    parent_path = repo / parent["path"]
    if not parent_path.is_file() or hashlib.sha256(parent_path.read_bytes()).hexdigest() != parent["sha256"]:
        raise P3ContractError("p3_b19_parent_invalid")
    parent_config = load_parent(parent_path)
    if parent_config["synthetic_fixture"]["fixture_id"] != parent["fixture_id"]:
        raise P3ContractError("p3_b19_fixture_drift")
    if raw.get("single_variable") != "openai_compatible_response_format_to_native_api_chat_direct_format":
        raise P3ContractError("p3_b19_variable_drift")
    if raw.get("transport") != {
        "backend": "native_ollama_chat", "url": "http://127.0.0.1:11434/api/chat",
        "ollama_version": "0.33.3", "format_source": "synthetic_parent.response_formats.json_schema.json_schema.schema",
    }:
        raise P3ContractError("p3_b19_transport_drift")
    if raw.get("judge") != parent_config["judge"]:
        raise P3ContractError("p3_b19_judge_drift")
    if raw.get("execution_boundary") != {
        "calls_exact": 1, "automatic_retry": False, "localhost_only": True,
        "developer_case_access": False, "annotation_file_access": False,
        "confirmation_access": False, "production_database_access": False,
        "remote_paid_calls": False, "case03_rerun": False,
        "real_model_calls_authorized_by_this_config": False, "separate_release_required": True,
    }:
        raise P3ContractError("p3_b19_boundary_drift")
    if raw.get("success") != {
        "strict_judgment_valid": True, "done_reason_not_length": True,
        "provider_usage_exactly_accounted": True, "no_retry": True,
        "authorizes_only_future_fresh_case_judge_transport": True,
        "authorizes_quality_claim": False,
    }:
        raise P3ContractError("p3_b19_success_drift")
    result = json.loads(json.dumps(raw, ensure_ascii=False))
    result.update({
        "_repo": repo, "_config_path": config_path,
        "_config_sha256": hashlib.sha256(config_path.read_bytes()).hexdigest(),
        "_parent": parent_config,
    })
    return result


def schema(config: Mapping[str, Any]) -> dict[str, Any]:
    return config["_parent"]["response_formats"]["json_schema"]["json_schema"]["schema"]


def native_body(config: Mapping[str, Any], messages: list[dict[str, str]]) -> dict[str, Any]:
    judge = config["judge"]
    return {
        "model": judge["model"], "messages": messages, "stream": False,
        "format": schema(config), "think": judge["think"],
        "options": {
            "temperature": judge["temperature"], "seed": judge["seed"],
            "top_p": judge["top_p"], "num_ctx": judge["num_ctx"],
            "num_predict": judge["max_completion_tokens"],
        },
    }


def native_transport(config: Mapping[str, Any], messages: list[dict[str, str]]) -> dict[str, Any]:
    request = urllib.request.Request(
        config["transport"]["url"],
        data=json.dumps(native_body(config, messages), ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST",
    )
    started = time.monotonic()
    with urllib.request.urlopen(request, timeout=config["judge"]["timeout_seconds"]) as response:
        payload = json.loads(response.read().decode("utf-8"))
    elapsed = time.monotonic() - started
    try:
        content = payload["message"]["content"]
        prompt_tokens = payload["prompt_eval_count"]
        completion_tokens = payload["eval_count"]
        done_reason = payload["done_reason"]
    except (KeyError, TypeError) as exc:
        raise P3ContractError("p3_b19_native_payload_invalid") from exc
    if payload.get("model") != config["judge"]["model"] or payload.get("done") is not True or not isinstance(content, str):
        raise P3ContractError("p3_b19_native_payload_invalid")
    return {
        "content": content, "prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens,
        "wall_seconds": round(elapsed, 6), "model": payload["model"],
        "finish_reason": done_reason, "real_model_calls": 1, "network_calls": 1,
    }


def failure_record(exc: Exception, response: Mapping[str, Any] | None) -> dict[str, Any]:
    received = isinstance(response, Mapping) and isinstance(response.get("content"), str)
    return _signed({
        "schema": "uruha_p3_native_judge_schema_failure_v1", "phase": "P3-B19",
        "item_id": "native_json_schema", "error_type": type(exc).__name__,
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


def build_preflight(config_path: str | Path) -> dict[str, Any]:
    config = load_config(config_path)
    item = synthetic_item(config["_parent"])
    messages = build_messages(item)
    metadata, version = _ollama_model_metadata(config["judge"]["model"]), ollama_version()
    body = native_body(config, messages)
    checks = {
        "before_failure_bound": True,
        "judge_digest_exact": metadata["digest"] == config["judge"]["digest"],
        "ollama_version_exact": version == config["transport"]["ollama_version"],
        "direct_schema_format_present": body["format"] == schema(config),
        "same_synthetic_prompt": canonical_sha256(messages) == "671b1cc82c129f3c6f0b35905631c6083c2d8f8ceaf137826ae51d59923ad8d3",
        "zero_generation_calls": metadata["generation_calls"] == 0,
        "zero_case_or_annotation_access": True,
    }
    return {
        "schema": "uruha_p3_native_judge_schema_probe_preflight_v1", "phase": "P3-B19",
        "status": "ready_for_native_schema_review" if all(checks.values()) else "not_ready_for_native_schema_review",
        "config_sha256": config["_config_sha256"], "checks": checks,
        "model_metadata": metadata, "ollama_version": version,
        "prompt_sha256": canonical_sha256(messages), "native_body_sha256": canonical_sha256(body),
        "format_schema_sha256": canonical_sha256(schema(config)),
        "real_model_calls": 0, "network_calls": 0, "paid_calls": 0,
        "developer_case_accessed": 0, "annotation_turns_accessed": 0,
        "claim_boundary": "Native schema readiness only; no inference or product-quality evidence.",
    }


def verify_release(config: Mapping[str, Any], release_path: str | Path, preflight_path: str | Path) -> None:
    release, preflight = _read(Path(release_path)), _read(Path(preflight_path))
    if release.get("schema") != RELEASE_SCHEMA or release.get("phase") != "P3-B19" or release.get("status") != "released_for_native_schema_probe":
        raise P3ContractError("p3_b19_release_invalid")
    expected = {
        "config": "configs/p3_native_judge_schema_probe_v1.json",
        "implementation": "p3_native_judge_schema_probe.py",
        "tests": "test_p3_native_judge_schema_probe.py",
        "preflight": "analysis/p3_b19_native_judge_schema_preflight_2026-09-15.json",
    }
    if set(release.get("artifacts", {})) != set(expected):
        raise P3ContractError("p3_b19_release_artifacts_invalid")
    for name, relative in expected.items():
        if release["artifacts"][name] != {"path": relative, "sha256": hashlib.sha256((config["_repo"] / relative).read_bytes()).hexdigest()}:
            raise P3ContractError("p3_b19_release_artifact_mismatch", name)
    if preflight.get("status") != "ready_for_native_schema_review":
        raise P3ContractError("p3_b19_preflight_invalid")
    if release.get("authorization") != {
        "calls_exact": 1, "automatic_retry": False, "localhost_only": True,
        "checkpoint_root": "analysis/p3_b19_native_judge_schema_checkpoint_v1",
        "result_path": "analysis/p3_b19_native_judge_schema_result_2026-09-15.json",
        "case03_rerun": False, "quality_claim": False,
    }:
        raise P3ContractError("p3_b19_authorization_invalid")


def run_probe(config_path: str | Path, release_path: str | Path, preflight_path: str | Path, checkpoint_root: str | Path) -> dict[str, Any]:
    config = load_config(config_path)
    verify_release(config, release_path, preflight_path)
    root = Path(checkpoint_root)
    if root.exists():
        raise P3ContractError("p3_b19_checkpoint_exists")
    item = synthetic_item(config["_parent"])
    messages = build_messages(item)
    _write_checkpoint(root / "intent.json", _signed({
        "schema": "uruha_p3_native_judge_schema_intent_v1", "phase": "P3-B19",
        "item_id": "native_json_schema", "prompt_sha256": canonical_sha256(messages),
        "native_body_sha256": canonical_sha256(native_body(config, messages)),
        "automatic_retry": False,
    }))
    started = time.monotonic()
    response: dict[str, Any] | None = None
    with localhost_network_only() as attempts:
        try:
            response = native_transport(config, messages)
            judgment = validate_judgment(response["content"], item)
            if response["finish_reason"] == "length":
                raise P3ContractError("p3_b19_native_length_stop")
        except Exception as exc:
            _write_checkpoint(root / "failure.json", failure_record(exc, response))
        else:
            _write_checkpoint(root / "complete.json", _signed({
                "schema": "uruha_p3_native_judge_schema_complete_v1", "phase": "P3-B19",
                "item_id": "native_json_schema", "judgment": judgment,
                "raw_content_sha256": canonical_sha256(response["content"]),
                "finish_reason": response["finish_reason"],
                "usage": {k: response[k] for k in ("prompt_tokens", "completion_tokens", "wall_seconds")},
                "result": {"real_model_calls": 1, "network_calls": 1}, "retry_performed": False,
            }))
    evidence = summarize_checkpoint_evidence(root)
    complete_path = root / "complete.json"
    complete = _read(complete_path) if complete_path.exists() else None
    checks = {
        "strict_judgment_valid": complete is not None,
        "done_reason_not_length": complete is not None and complete.get("finish_reason") != "length",
        "provider_usage_exactly_accounted": evidence["provider_call_evidence"] == evidence["network_call_evidence"] == 1,
        "no_retry": evidence["declared_invocation_intents"] == 1,
        "localhost_only": all(x["loopback_allowed"] is True for x in attempts),
    }
    return {
        "schema": "uruha_p3_native_judge_schema_probe_result_v1", "phase": "P3-B19",
        "status": "native_judge_schema_conformance_pass" if all(checks.values()) else "native_judge_schema_failed_retained",
        "config_sha256": config["_config_sha256"], "release_sha256": hashlib.sha256(Path(release_path).read_bytes()).hexdigest(),
        "judgment": complete.get("judgment") if complete else None,
        "finish_reason": complete.get("finish_reason") if complete else None,
        "usage": complete.get("usage") if complete else None,
        "checkpoint_evidence": evidence, "checks": checks, "network_attempts": attempts,
        "total_wall_seconds": round(time.monotonic() - started, 6), "paid_calls": 0,
        "developer_case_accessed": 0, "annotation_turns_accessed": 0,
        "confirmation_accessed": 0, "production_database_accessed": False,
        "case03_rerun": False,
        "claim_boundary": "A pass validates one synthetic native structured-output call and authorizes only a future fresh-case transport design. It is not a product-quality result, holdout, or human preference evidence.",
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
                raise P3ContractError("p3_b19_run_artifacts_required")
            result = run_probe(args.config, args.release, args.preflight, args.checkpoint_root)
    except P3ContractError as exc:
        result = {
            "schema": "uruha_p3_native_judge_schema_refusal_v1", "phase": "P3-B19",
            "status": "refused_or_failed_retained", "contract_code": exc.code,
            "checkpoint_evidence": summarize_checkpoint_evidence(args.checkpoint_root or ""),
            "automatic_retry": False, "claim_boundary": "No conformance or quality claim is authorized.",
        }
    write_new_json(output, result)
    return 0 if result.get("status") in {"ready_for_native_schema_review", "native_judge_schema_conformance_pass"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
