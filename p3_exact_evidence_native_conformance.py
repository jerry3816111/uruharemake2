#!/usr/bin/env python3
"""P3-B32 native conformance canary for the frozen exact-evidence schema."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import time
from typing import Any, Callable, Mapping
import urllib.request

from p3_case03_proxy_grade import _read, _signed, _write_checkpoint
from p3_native_judge_schema_probe import ollama_version
from p3_product_comparison import P3ContractError, canonical_sha256, write_new_json
from p3_product_worker import (
    _ollama_model_metadata,
    localhost_network_only,
    summarize_checkpoint_evidence,
)
import p3_exact_evidence_judge_contract as exact


SCHEMA = "uruha_p3_exact_evidence_native_conformance_v1"
RELEASE_SCHEMA = "uruha_p3_exact_evidence_native_conformance_release_v1"
RESULT_SCHEMA = "uruha_p3_exact_evidence_native_conformance_result_v1"


def _reference(repo: Path, value: Mapping[str, Any], expected: Mapping[str, Any], code: str) -> Path:
    if value != expected:
        raise P3ContractError(code)
    path = (repo / str(value["path"])).resolve()
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != value["sha256"]:
        raise P3ContractError(code)
    return path


def load_config(path: str | Path) -> dict[str, Any]:
    config_path = Path(path).resolve()
    raw = _read(config_path)
    expected_root = {
        "schema", "phase", "status", "purpose", "before_failure", "frozen_contract",
        "single_variable", "transport", "judge", "synthetic_fixture",
        "execution_boundary", "success",
    }
    if set(raw) != expected_root or raw.get("schema") != SCHEMA or raw.get("phase") != "P3-B32":
        raise P3ContractError("p3_b32_schema_mismatch")
    if raw.get("status") != "preregistered_not_executed" or raw.get("purpose") != (
        "prospective_native_conformance_canary_for_frozen_exact_evidence_schema"
    ):
        raise P3ContractError("p3_b32_status_mismatch")
    repo = config_path.parent.parent
    before_path = _reference(repo, raw["before_failure"], {
        "path": "analysis/p3_b29_case06_native_diagnostic_grade_result_2026-09-17.json",
        "sha256": "f17edab479026d58d0ecc0c2f57c1cb77e34462c42ade2a1caf171d849dfe5b7",
        "required_status": "case06_native_diagnostic_inconclusive_retained",
        "required_contract_code": "p3_b17_quote_invalid",
    }, "p3_b32_before_failure_mismatch")
    frozen_path = _reference(repo, raw["frozen_contract"], {
        "path": "research/p3_b30_exact_evidence_judge_contract_freeze_2026-09-17.json",
        "sha256": "7695d2c8836f10c226ea207ce085488560f1c90be51c32465ca16f15ea805484",
        "required_status": "prospective_exact_evidence_contract_frozen",
        "implementation_path": "p3_exact_evidence_judge_contract.py",
        "implementation_sha256": "f2d8f101d980df0129fbcdd3707e97b117d1a81d4fd8726d2969c73149adc252",
    }, "p3_b32_frozen_contract_mismatch")
    before = _read(before_path)
    frozen = _read(frozen_path)
    if (
        before.get("status") != raw["before_failure"]["required_status"]
        or (before.get("failure") or {}).get("contract_code")
        != raw["before_failure"]["required_contract_code"]
    ):
        raise P3ContractError("p3_b32_before_failure_mismatch")
    if frozen.get("status") != raw["frozen_contract"]["required_status"]:
        raise P3ContractError("p3_b32_frozen_contract_mismatch")
    implementation = repo / raw["frozen_contract"]["implementation_path"]
    if (
        not implementation.is_file()
        or hashlib.sha256(implementation.read_bytes()).hexdigest()
        != raw["frozen_contract"]["implementation_sha256"]
        or (frozen.get("artifacts") or {}).get("implementation", {}).get("sha256")
        != raw["frozen_contract"]["implementation_sha256"]
    ):
        raise P3ContractError("p3_b32_frozen_implementation_mismatch")
    if raw.get("single_variable") != (
        "old_nonempty_quote_schema_to_frozen_slot_bound_entire_reply_enum_schema"
    ):
        raise P3ContractError("p3_b32_variable_mismatch")
    if raw.get("transport") != {
        "backend": "native_ollama_chat",
        "url": "http://127.0.0.1:11434/api/chat",
        "ollama_version": "0.33.3",
        "format": "direct_per_item_json_schema",
    }:
        raise P3ContractError("p3_b32_transport_mismatch")
    if raw.get("judge") != {
        "model": "qwen3.5:9b",
        "digest": "dec52a44569a2a25341c4e4d3fee25846eed4f6f0b936278e3a3c900bb99d37c",
        "temperature": 0,
        "seed": 20260909,
        "top_p": 1,
        "num_ctx": 8192,
        "think": False,
        "max_completion_tokens": 384,
        "timeout_seconds": 30,
        "orders": ["AB", "BA"],
        "retries": 0,
        "condition_names_hidden": True,
    }:
        raise P3ContractError("p3_b32_judge_mismatch")
    fixture = raw.get("synthetic_fixture") or {}
    if fixture != {
        "fixture_id": "p3-b32-exact-evidence-schema-only-01",
        "turn_id": "p3-b32-synthetic-u1",
        "current_input": "いまは短く返して。",
        "annotation": {
            "correction_eligible": False,
            "acceptable_behavior": ["respond briefly without inventing context"],
            "forbidden_behavior": ["add unsupported personal facts"],
        },
        "reply_one": "うん、短く返す。",
        "reply_two": "了解。",
    }:
        raise P3ContractError("p3_b32_fixture_mismatch")
    if raw.get("execution_boundary") != {
        "judge_calls_exact": 2,
        "automatic_retry": False,
        "stop_on_first_transport_or_validation_failure": True,
        "concurrency": 1,
        "localhost_only": True,
        "developer_case_access": False,
        "annotation_file_access": False,
        "generation_rerun": False,
        "b29_regrade": False,
        "confirmation_access": False,
        "production_database_access": False,
        "remote_paid_calls": False,
        "real_model_calls_authorized_by_this_config": False,
        "separate_release_required": True,
    }:
        raise P3ContractError("p3_b32_boundary_mismatch")
    if raw.get("success") != {
        "both_orders_strictly_valid": True,
        "entire_reply_exact_for_both_slots": True,
        "done_reason_not_length": True,
        "provider_usage_exactly_accounted": True,
        "no_retry": True,
        "authorizes_only_prospective_case_judge_transport": True,
        "authorizes_quality_claim": False,
        "authorizes_b29_regrade": False,
    }:
        raise P3ContractError("p3_b32_success_mismatch")
    result = json.loads(json.dumps(raw, ensure_ascii=False))
    result.update({
        "_repo": repo,
        "_config_path": config_path,
        "_config_sha256": hashlib.sha256(config_path.read_bytes()).hexdigest(),
        "_before_path": before_path,
        "_frozen_path": frozen_path,
    })
    return result


def build_items(config: Mapping[str, Any]) -> list[dict[str, Any]]:
    fixture = config["synthetic_fixture"]
    replies = {
        "synthetic_reply_one": fixture["reply_one"],
        "synthetic_reply_two": fixture["reply_two"],
    }
    items = []
    for order in config["judge"]["orders"]:
        slots = (
            {"A": "synthetic_reply_one", "B": "synthetic_reply_two"}
            if order == "AB"
            else {"A": "synthetic_reply_two", "B": "synthetic_reply_one"}
        )
        items.append({
            "item_id": f"{fixture['fixture_id']}:{order}",
            "turn_id": fixture["turn_id"],
            "order": order,
            "visible_history": [],
            "current_input": fixture["current_input"],
            "annotation": fixture["annotation"],
            "slot_to_condition": slots,
            "anonymous_replies": {slot: replies[name] for slot, name in slots.items()},
            "currently_visible_turn_ids": [fixture["turn_id"]],
        })
    return items


def native_transport(
    config: Mapping[str, Any],
    item: Mapping[str, Any],
) -> dict[str, Any]:
    body = exact.native_body(config, item)
    request = urllib.request.Request(
        config["transport"]["url"],
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
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
        raise P3ContractError("p3_b32_native_payload_invalid") from exc
    if (
        payload.get("model") != config["judge"]["model"]
        or payload.get("done") is not True
        or not isinstance(content, str)
    ):
        raise P3ContractError("p3_b32_native_payload_invalid")
    return {
        "content": content,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "wall_seconds": round(elapsed, 6),
        "model": payload["model"],
        "finish_reason": done_reason,
        "real_model_calls": 1,
        "network_calls": 1,
    }


def failure_record(item_id: str, exc: Exception, response: Mapping[str, Any] | None) -> dict[str, Any]:
    received = isinstance(response, Mapping) and isinstance(response.get("content"), str)
    return _signed({
        "schema": "uruha_p3_exact_evidence_native_conformance_failure_v1",
        "phase": "P3-B32",
        "item_id": item_id,
        "error_type": type(exc).__name__,
        "contract_code": getattr(exc, "code", "transport_or_validation_failure"),
        "response_received": received,
        "raw_content_sha256": canonical_sha256(response["content"]) if received else None,
        "finish_reason": response.get("finish_reason") if received else None,
        "provider_actual_usage": ({
            key: response.get(key)
            for key in (
                "prompt_tokens", "completion_tokens", "wall_seconds",
                "real_model_calls", "network_calls",
            )
        } if received else None),
        "retry_performed": False,
    })


def build_preflight(config_path: str | Path) -> dict[str, Any]:
    config = load_config(config_path)
    items = build_items(config)
    metadata = _ollama_model_metadata(config["judge"]["model"])
    version = ollama_version()
    schemas = [exact.judgment_schema(item) for item in items]
    checks = {
        "b29_failure_immutable_and_bound": hashlib.sha256(config["_before_path"].read_bytes()).hexdigest()
        == config["before_failure"]["sha256"],
        "b30_frozen_contract_bound": hashlib.sha256(config["_frozen_path"].read_bytes()).hexdigest()
        == config["frozen_contract"]["sha256"],
        "judge_digest_exact": metadata["digest"] == config["judge"]["digest"],
        "ollama_version_exact": version == config["transport"]["ollama_version"],
        "exact_ab_ba_pairing": [item["order"] for item in items] == ["AB", "BA"],
        "keyed_scores_and_no_oneof": all(
            schema["properties"]["scores"]["required"] == ["A", "B"]
            and "oneOf" not in json.dumps(schema)
            for schema in schemas
        ),
        "entire_reply_enum_swaps_with_order": (
            schemas[0]["properties"]["scores"]["properties"]["A"]["properties"]["reply_quote"]["enum"]
            == schemas[1]["properties"]["scores"]["properties"]["B"]["properties"]["reply_quote"]["enum"]
        ),
        "zero_generation_or_judge_calls": metadata["generation_calls"] == 0,
        "zero_case_annotation_or_production_access": True,
    }
    return {
        "schema": "uruha_p3_exact_evidence_native_conformance_preflight_v1",
        "phase": "P3-B32",
        "status": "ready_for_exact_evidence_native_conformance_review" if all(checks.values())
        else "not_ready_for_exact_evidence_native_conformance_review",
        "config_sha256": config["_config_sha256"],
        "checks": checks,
        "judge_metadata": metadata,
        "ollama_version": version,
        "item_manifest": [
            {
                "item_id": item["item_id"],
                "prompt_sha256": canonical_sha256(exact.build_exact_evidence_messages(item)),
                "schema_sha256": canonical_sha256(schema),
                "native_body_sha256": canonical_sha256(exact.native_body(config, item)),
            }
            for item, schema in zip(items, schemas)
        ],
        "real_model_calls": 0,
        "network_calls": 0,
        "paid_calls": 0,
        "developer_case_accessed": 0,
        "annotation_files_accessed": 0,
        "b29_regraded": False,
        "claim_boundary": (
            "Readiness only. No native judge inference, product-quality result, human preference, "
            "holdout evidence, or advantage claim exists."
        ),
    }


def verify_release(
    config: Mapping[str, Any],
    release_path: str | Path,
    preflight_path: str | Path,
) -> None:
    release_path = Path(release_path).resolve()
    preflight_path = Path(preflight_path).resolve()
    release = _read(release_path)
    preflight = _read(preflight_path)
    if (
        release.get("schema") != RELEASE_SCHEMA
        or release.get("phase") != "P3-B32"
        or release.get("status") != "released_for_two_call_exact_evidence_native_conformance"
    ):
        raise P3ContractError("p3_b32_release_invalid")
    expected = {
        "config": "configs/p3_exact_evidence_native_conformance_v1.json",
        "implementation": "p3_exact_evidence_native_conformance.py",
        "shared_contract": "p3_exact_evidence_judge_contract.py",
        "tests": "test_p3_exact_evidence_native_conformance.py",
        "preflight": "analysis/p3_b32_exact_evidence_native_conformance_preflight_2026-09-17.json",
    }
    if set(release.get("artifacts", {})) != set(expected):
        raise P3ContractError("p3_b32_release_artifacts_invalid")
    for name, relative in expected.items():
        binding = {
            "path": relative,
            "sha256": hashlib.sha256((config["_repo"] / relative).read_bytes()).hexdigest(),
        }
        if release["artifacts"][name] != binding:
            raise P3ContractError("p3_b32_release_artifact_mismatch", name)
    if (
        preflight_path != (config["_repo"] / expected["preflight"]).resolve()
        or preflight.get("status") != "ready_for_exact_evidence_native_conformance_review"
    ):
        raise P3ContractError("p3_b32_preflight_invalid")
    if release.get("authorization") != {
        "judge_model": "qwen3.5:9b",
        "judge_calls_exact": 2,
        "automatic_retry": False,
        "localhost_only": True,
        "checkpoint_root": "analysis/p3_b32_exact_evidence_native_conformance_checkpoints_v1",
        "result_path": "analysis/p3_b32_exact_evidence_native_conformance_result_2026-09-17.json",
        "developer_case_access": False,
        "annotation_file_access": False,
        "b29_regrade": False,
        "quality_claim": False,
    }:
        raise P3ContractError("p3_b32_authorization_invalid")


def run_probe(
    config_path: str | Path,
    release_path: str | Path,
    preflight_path: str | Path,
    checkpoint_root: str | Path,
    transport: Callable[[Mapping[str, Any], Mapping[str, Any]], Mapping[str, Any]] = native_transport,
) -> dict[str, Any]:
    config = load_config(config_path)
    verify_release(config, release_path, preflight_path)
    root = Path(checkpoint_root).resolve()
    if root.exists():
        raise P3ContractError("p3_b32_checkpoint_root_exists")
    rows: list[dict[str, Any]] = []
    failure: dict[str, Any] | None = None
    started = time.monotonic()
    with localhost_network_only() as network_attempts:
        for item in build_items(config):
            item_root = root / item["order"]
            messages = exact.build_exact_evidence_messages(item)
            schema = exact.judgment_schema(item)
            body = exact.native_body(config, item)
            _write_checkpoint(item_root / "intent.json", _signed({
                "schema": "uruha_p3_exact_evidence_native_conformance_intent_v1",
                "phase": "P3-B32",
                "item_id": item["item_id"],
                "prompt_sha256": canonical_sha256(messages),
                "anonymous_replies_sha256": canonical_sha256(item["anonymous_replies"]),
                "format_schema_sha256": canonical_sha256(schema),
                "native_body_sha256": canonical_sha256(body),
                "judge_model": config["judge"]["model"],
                "automatic_retry": False,
            }))
            response: dict[str, Any] | None = None
            try:
                response = dict(transport(config, item))
                judgment = exact.validate_exact_evidence_judgment(response["content"], item)
                if response["finish_reason"] == "length":
                    raise P3ContractError("p3_b32_native_length_stop")
            except Exception as exc:
                failure = failure_record(item["item_id"], exc, response)
                _write_checkpoint(item_root / "failure.json", failure)
                break
            complete = _signed({
                "schema": "uruha_p3_exact_evidence_native_conformance_complete_v1",
                "phase": "P3-B32",
                "item_id": item["item_id"],
                "judgment": judgment,
                "raw_content_sha256": canonical_sha256(response["content"]),
                "finish_reason": response["finish_reason"],
                "usage": {
                    key: response[key]
                    for key in ("prompt_tokens", "completion_tokens", "wall_seconds")
                },
                "result": {"real_model_calls": 1, "network_calls": 1},
                "retry_performed": False,
            })
            _write_checkpoint(item_root / "complete.json", complete)
            rows.append({
                "item_id": item["item_id"],
                "order": item["order"],
                "slot_to_condition": item["slot_to_condition"],
                "anonymous_replies": item["anonymous_replies"],
                "judgment": judgment,
                "finish_reason": response["finish_reason"],
                "usage": complete["usage"],
                "real_model_calls": 1,
                "network_calls": 1,
            })
    evidence = summarize_checkpoint_evidence(root)
    checks = {
        "both_orders_strictly_valid": len(rows) == 2 and failure is None,
        "entire_reply_exact_for_both_slots": len(rows) == 2 and all(
            score["reply_quote"] == row["anonymous_replies"][score["reply_slot"]]
            for row in rows
            for score in row["judgment"]["scores"]
        ),
        "done_reason_not_length": len(rows) == 2 and all(
            row["finish_reason"] != "length" for row in rows
        ),
        "provider_usage_exactly_accounted": (
            evidence["provider_call_evidence"]
            == evidence["network_call_evidence"]
            == evidence["declared_invocation_intents"]
            == 2
        ),
        "no_retry": evidence["declared_invocation_intents"] == len(rows) + int(failure is not None) <= 2,
        "localhost_only": all(attempt["loopback_allowed"] is True for attempt in network_attempts),
        "b29_unchanged_and_not_regraded": (
            hashlib.sha256(config["_before_path"].read_bytes()).hexdigest()
            == config["before_failure"]["sha256"]
        ),
        "zero_case_annotation_or_production_access": True,
    }
    status = (
        "exact_evidence_native_conformance_pass"
        if all(checks.values())
        else "exact_evidence_native_conformance_failed_retained"
    )
    return {
        "schema": RESULT_SCHEMA,
        "phase": "P3-B32",
        "status": status,
        "config_sha256": config["_config_sha256"],
        "release_sha256": hashlib.sha256(Path(release_path).read_bytes()).hexdigest(),
        "rows": rows,
        "failure": failure,
        "checks": checks,
        "judge_calls": evidence["provider_call_evidence"],
        "judge_prompt_tokens": evidence["provider_prompt_tokens_observed"],
        "judge_completion_tokens": evidence["provider_completion_tokens_observed"],
        "judge_wall_seconds": round(
            sum(row["usage"]["wall_seconds"] for row in rows)
            + ((failure.get("provider_actual_usage") or {}).get("wall_seconds", 0) if failure else 0),
            6,
        ),
        "checkpoint_evidence": evidence,
        "total_runner_wall_seconds": round(time.monotonic() - started, 6),
        "network_attempts": network_attempts,
        "paid_calls": 0,
        "developer_case_accessed": 0,
        "annotation_files_accessed": 0,
        "b29_regraded": False,
        "generation_rerun": False,
        "production_database_accessed": False,
        "quality_result": "not_evaluated",
        "human_preference": "unavailable",
        "claim_boundary": (
            "This two-call synthetic result can validate only native compatibility with the frozen "
            "exact-evidence schema. It cannot establish product quality, human preference, holdout "
            "validity, comparative advantage, or repair the permanently inconclusive B29 result."
        ),
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
            payload = build_preflight(args.config)
        else:
            if not args.release or not args.preflight or not args.checkpoint_root:
                raise P3ContractError("p3_b32_run_artifacts_required")
            payload = run_probe(
                args.config,
                args.release,
                args.preflight,
                args.checkpoint_root,
            )
    except P3ContractError as exc:
        evidence = summarize_checkpoint_evidence(args.checkpoint_root or "")
        payload = {
            "schema": "uruha_p3_exact_evidence_native_conformance_refusal_v1",
            "phase": "P3-B32",
            "status": "refused_before_transport" if evidence["declared_invocation_intents"] == 0
            else "failed_after_transport_retained",
            "contract_code": exc.code,
            "checkpoint_evidence": evidence,
            "automatic_retry": False,
            "claim_boundary": "No native-conformance or quality claim is authorized.",
        }
    write_new_json(output, payload)
    return 0 if payload.get("status") in {
        "ready_for_exact_evidence_native_conformance_review",
        "exact_evidence_native_conformance_pass",
    } else 1


if __name__ == "__main__":
    raise SystemExit(main())
