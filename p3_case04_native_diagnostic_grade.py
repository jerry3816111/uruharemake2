#!/usr/bin/env python3
"""P3-B21 native blind diagnostic grading for immutable case-04 outputs."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import time
from typing import Any, Callable, Mapping
import urllib.request

from p3_case03_proxy_grade import (
    _costs,
    _read,
    _signed,
    _write_checkpoint,
    build_messages,
    summarize,
    validate_judgment,
)
from p3_native_judge_schema_probe import ollama_version
from p3_product_comparison import P3ContractError, canonical_sha256, write_new_json
from p3_product_worker import (
    _ollama_model_metadata,
    localhost_network_only,
    summarize_checkpoint_evidence,
)


SCHEMA = "uruha_p3_case04_native_diagnostic_grade_v1"
RELEASE_SCHEMA = "uruha_p3_case04_native_diagnostic_grade_release_v1"
RESULT_SCHEMA = "uruha_p3_case04_native_diagnostic_grade_result_v1"
CASE_ID = "p3-smoke-humor-boundary-zh"


def _ref(repo: Path, value: Any, expected: Mapping[str, Any], code: str) -> Path:
    if value != expected:
        raise P3ContractError(code)
    path = (repo / str(expected["path"])).resolve()
    try:
        path.relative_to(repo)
    except ValueError as exc:
        raise P3ContractError(code) from exc
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected["sha256"]:
        raise P3ContractError(code)
    return path


def load_config(path: str | Path) -> dict[str, Any]:
    config_path = Path(path).resolve()
    raw = _read(config_path)
    expected_root = {
        "schema", "phase", "status", "purpose", "comparison_design",
        "locked_outputs", "case_source", "annotations", "native_conformance",
        "conditions", "transport", "judge", "rubric", "execution_boundary", "success",
    }
    if set(raw) != expected_root or raw.get("schema") != SCHEMA or raw.get("phase") != "P3-B21":
        raise P3ContractError("p3_b21_schema_mismatch")
    if raw.get("status") != "preregistered_not_executed" or raw.get("purpose") != "blind_native_ab_ba_diagnosis_of_immutable_case04_outputs_after_generation_gate_failure":
        raise P3ContractError("p3_b21_status_mismatch")
    repo = config_path.parent.parent
    design_path = _ref(repo, raw["comparison_design"], {
        "path": "configs/p3_product_comparison_v1.json",
        "sha256": "1e6d3b0600740b3dee7207ffc5c4f9cc9247a5feba2b967bdab4586522f7b836",
    }, "p3_b21_design_mismatch")
    lock_path = _ref(repo, raw["locked_outputs"], {
        "path": "analysis/p3_b20_case04_output_lock_result_2026-09-15.json",
        "sha256": "1b437bb2890372b8734953cd748f04d55ebc1a0d4026c8f1f8507e6ce35994d1",
        "required_status": "case04_output_lock_failed_retained",
        "locked_commit": "264d568b930d8b836a1e00208e493c8bc1146ee9",
        "only_failed_check": "all_provider_calls_accounted",
        "actual_product_calls": 3,
        "actual_direct_calls": 4,
        "actual_total_calls": 7,
    }, "p3_b21_lock_mismatch")
    source_path = _ref(repo, raw["case_source"], {
        "path": "datasets/p3_case04_generation_source_v1.json",
        "sha256": "033c5c5de3e6b05dcf7a8fa45930fd7da9dced6f9b1e1f4bbf686509edacde66",
    }, "p3_b21_source_mismatch")
    annotation_path = _ref(repo, raw["annotations"], {
        "path": "datasets/p3_developer_smoke_annotations_v1.json",
        "sha256": "aec1f4fbd88a96b180ad5c90f8f2f7a362a01b57d0d26a22b26af3ff25a5a3ea",
        "case_id": CASE_ID,
        "role": "developer_proxy_rubric_not_gold_reply_or_human_preference",
        "case_turns_used": 4,
        "other_case_annotations_used": 0,
        "opened_only_after_locked_output_commit": True,
    }, "p3_b21_annotation_mismatch")
    conformance_path = _ref(repo, raw["native_conformance"], {
        "path": "analysis/p3_b19_native_judge_schema_result_2026-09-15.json",
        "sha256": "5b01e324116123ceacca0f44eb39bac05cae56b595ec953bd25c00e58b4de6d1",
        "required_status": "native_judge_schema_conformance_pass",
    }, "p3_b21_conformance_mismatch")
    design, locked, source, annotations, conformance = map(
        _read, (design_path, lock_path, source_path, annotation_path, conformance_path)
    )
    expected_checks = {
        "all_condition_turn_budgets_valid": True,
        "all_eight_shared_surface_pass": True,
        "all_eight_visible_outputs_nonempty": True,
        "all_four_view_pairs_share_source_and_prefix": True,
        "all_provider_calls_accounted": False,
        "localhost_only": True,
        "product_state_isolated_and_workspace_removed": True,
        "session_restart_preserves_case_paths": True,
        "zero_annotation_or_production_access": True,
    }
    if locked.get("status") != raw["locked_outputs"]["required_status"] or locked.get("checks") != expected_checks:
        raise P3ContractError("p3_b21_lock_failure_shape_invalid")
    if locked.get("case_id") != CASE_ID or locked.get("annotations_accessed") != 0 or locked.get("future_turns_accessed") != 0:
        raise P3ContractError("p3_b21_lock_blindness_invalid")
    product_calls = sum(len(x.get("calls", [])) for x in locked.get("product_turns", []))
    direct_calls = sum(len(x.get("calls", [])) for x in locked.get("direct_turns", []))
    if (product_calls, direct_calls, locked.get("real_model_calls"), locked.get("network_calls")) != (3, 4, 7, 7):
        raise P3ContractError("p3_b21_lock_accounting_invalid")
    if source.get("case_id") != CASE_ID or len(source.get("turns", [])) != 4:
        raise P3ContractError("p3_b21_source_case_invalid")
    case_annotations = [x for x in annotations.get("cases", []) if x.get("case_id") == CASE_ID]
    if len(case_annotations) != 1 or len(case_annotations[0].get("turns", [])) != 4:
        raise P3ContractError("p3_b21_case_annotation_invalid")
    if annotations.get("annotation_role") != raw["annotations"]["role"]:
        raise P3ContractError("p3_b21_annotation_role_invalid")
    if conformance.get("status") != raw["native_conformance"]["required_status"]:
        raise P3ContractError("p3_b21_conformance_status_invalid")
    if raw.get("conditions") != ["product_system", "full_history_direct"]:
        raise P3ContractError("p3_b21_conditions_invalid")
    if raw.get("transport") != {
        "backend": "native_ollama_chat", "url": "http://127.0.0.1:11434/api/chat",
        "ollama_version": "0.33.3", "format": "direct_per_item_json_schema",
        "correction_schema_follows_annotation_eligibility": True,
    }:
        raise P3ContractError("p3_b21_transport_drift")
    frozen = design["grading"]
    if raw.get("judge") != {
        "model": frozen["judge_model"], "digest": "dec52a44569a2a25341c4e4d3fee25846eed4f6f0b936278e3a3c900bb99d37c",
        "temperature": frozen["judge_temperature"], "seed": frozen["judge_seed"],
        "top_p": 1, "num_ctx": frozen["judge_num_ctx"], "think": False,
        "max_completion_tokens": frozen["judge_output_tokens_max"],
        "timeout_seconds": frozen["judge_timeout_seconds"], "orders": frozen["judge_orders"],
        "retries": frozen["judge_retries"], "condition_names_hidden": frozen["judge_condition_names_hidden"],
    }:
        raise P3ContractError("p3_b21_judge_drift")
    if raw.get("rubric") != {
        "dimensions": frozen["dimensions"], "scale": frozen["scale"],
        "correction_only_if_eligible": frozen["correction_only_if_eligible"],
        "unsupported_assertion_boolean": True, "japanese_issue_boolean": True,
        "identity_issue_boolean": True, "reply_quote_must_be_exact_span": True,
        "evidence_turn_ids_must_be_currently_visible": True,
    }:
        raise P3ContractError("p3_b21_rubric_drift")
    if raw.get("execution_boundary") != {
        "judge_calls_exact": 8, "automatic_retry": False,
        "stop_on_first_transport_or_validation_failure": True, "concurrency": 1,
        "localhost_only": True, "generation_outputs_mutable": False,
        "generation_rerun": False, "future_turn_access": False,
        "confirmation_access": False, "production_database_access": False,
        "remote_paid_calls": False, "other_case_annotations_used": 0,
        "real_model_calls_authorized_by_this_config": False, "separate_release_required": True,
    }:
        raise P3ContractError("p3_b21_boundary_drift")
    if raw.get("success") != {
        "all_eight_judgments_valid": True,
        "minimum_grading_coverage": frozen["minimum_grading_coverage"],
        "minimum_order_agreement": frozen["minimum_order_agreement"],
        "locked_generation_failure_remains_failed": True, "diagnostic_only": True,
        "single_case_can_pass_quality_gate": False, "human_preference_claim_allowed": False,
        "formal_advantage_claim_allowed": False,
    }:
        raise P3ContractError("p3_b21_success_drift")
    result = json.loads(json.dumps(raw, ensure_ascii=False))
    result.update({
        "_repo": repo, "_config_path": config_path,
        "_config_sha256": hashlib.sha256(config_path.read_bytes()).hexdigest(),
        "_locked": locked, "_source": source, "_case_annotations": case_annotations[0],
    })
    return result


def _direct_text(row: Mapping[str, Any]) -> str:
    final = row.get("final")
    if not isinstance(final, Mapping) or not isinstance(final.get("content"), str):
        raise P3ContractError("p3_b21_direct_output_invalid")
    return final["content"]


def build_items(config: Mapping[str, Any]) -> list[dict[str, Any]]:
    turns = config["_source"]["turns"]
    product = {x["turn_id"]: x for x in config["_locked"]["product_turns"]}
    direct = {x["turn_id"]: x for x in config["_locked"]["direct_turns"]}
    annotations = {x["turn_id"]: x for x in config["_case_annotations"]["turns"]}
    prefix: list[dict[str, str]] = []
    items: list[dict[str, Any]] = []
    visible_user_ids: list[str] = []
    for turn in turns:
        turn_id = turn["turn_id"]
        if turn_id not in product or turn_id not in direct or turn_id not in annotations:
            raise P3ContractError("p3_b21_turn_alignment_invalid")
        visible_user_ids.append(turn_id)
        replies = {
            "product_system": product[turn_id]["visible_reply"],
            "full_history_direct": _direct_text(direct[turn_id]),
        }
        if any(not isinstance(x, str) or not x.strip() for x in replies.values()):
            raise P3ContractError("p3_b21_locked_reply_invalid")
        for order in config["judge"]["orders"]:
            mapping = (
                {"A": "product_system", "B": "full_history_direct"}
                if order == "AB" else
                {"A": "full_history_direct", "B": "product_system"}
            )
            items.append({
                "item_id": f"{turn_id}:{order}", "turn_id": turn_id, "order": order,
                "visible_history": json.loads(json.dumps(prefix, ensure_ascii=False)),
                "current_input": turn["content"], "annotation": annotations[turn_id],
                "slot_to_condition": mapping,
                "anonymous_replies": {slot: replies[condition] for slot, condition in mapping.items()},
                "currently_visible_turn_ids": list(visible_user_ids),
            })
        prefix.extend([
            {"turn_id": turn_id, "role": "user", "content": turn["content"]},
            {"turn_id": f"{turn_id}-system-reply", "role": "assistant", "content": replies["product_system"]},
        ])
    return items


def judgment_schema(item: Mapping[str, Any]) -> dict[str, Any]:
    score_keys = [
        "reply_slot", "attunement", "grounding", "correction", "continuity",
        "unsupported_assertion", "japanese_issue", "identity_issue",
        "evidence_turn_ids", "reply_quote",
    ]
    score_properties: dict[str, Any] = {
        "reply_slot": {"type": "string", "enum": ["A", "B"]},
        "attunement": {"type": "integer", "enum": [0, 1, 2]},
        "grounding": {"type": "integer", "enum": [0, 1, 2]},
        "correction": (
            {"type": "integer", "enum": [0, 1, 2]}
            if item["annotation"]["correction_eligible"] else {"type": "null"}
        ),
        "continuity": {"type": "integer", "enum": [0, 1, 2]},
        "unsupported_assertion": {"type": "boolean"},
        "japanese_issue": {"type": "boolean"},
        "identity_issue": {"type": "boolean"},
        "evidence_turn_ids": {
            "type": "array", "minItems": 1,
            "items": {"type": "string", "enum": item["currently_visible_turn_ids"]},
        },
        "reply_quote": {"type": "string", "minLength": 1},
    }
    return {
        "type": "object", "additionalProperties": False,
        "required": ["scores", "preference"],
        "properties": {
            "scores": {
                "type": "array", "minItems": 2, "maxItems": 2,
                "items": {
                    "type": "object", "additionalProperties": False,
                    "required": score_keys, "properties": score_properties,
                },
            },
            "preference": {"type": "string", "enum": ["A", "B", "tie"]},
        },
    }


def native_body(config: Mapping[str, Any], item: Mapping[str, Any], messages: list[dict[str, str]]) -> dict[str, Any]:
    judge = config["judge"]
    return {
        "model": judge["model"], "messages": messages, "stream": False,
        "format": judgment_schema(item), "think": judge["think"],
        "options": {
            "temperature": judge["temperature"], "seed": judge["seed"],
            "top_p": judge["top_p"], "num_ctx": judge["num_ctx"],
            "num_predict": judge["max_completion_tokens"],
        },
    }


def native_transport(config: Mapping[str, Any], item: Mapping[str, Any], messages: list[dict[str, str]]) -> dict[str, Any]:
    request = urllib.request.Request(
        config["transport"]["url"],
        data=json.dumps(native_body(config, item, messages), ensure_ascii=False).encode("utf-8"),
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
        raise P3ContractError("p3_b21_native_payload_invalid") from exc
    if payload.get("model") != config["judge"]["model"] or payload.get("done") is not True or not isinstance(content, str):
        raise P3ContractError("p3_b21_native_payload_invalid")
    return {
        "content": content, "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens, "wall_seconds": round(elapsed, 6),
        "model": payload["model"], "finish_reason": done_reason,
        "real_model_calls": 1, "network_calls": 1,
    }


def failure_record(item_id: str, exc: Exception, response: Mapping[str, Any] | None) -> dict[str, Any]:
    received = isinstance(response, Mapping) and isinstance(response.get("content"), str)
    return _signed({
        "schema": "uruha_p3_case04_native_diagnostic_grade_failure_v1", "phase": "P3-B21",
        "item_id": item_id, "error_type": type(exc).__name__,
        "contract_code": getattr(exc, "code", "transport_or_validation_failure"),
        "response_received": received,
        "raw_content_sha256": canonical_sha256(response["content"]) if received else None,
        "finish_reason": response.get("finish_reason") if received else None,
        "provider_actual_usage": ({
            "prompt_tokens": response.get("prompt_tokens"),
            "completion_tokens": response.get("completion_tokens"),
            "wall_seconds": response.get("wall_seconds"),
            "real_model_calls": response.get("real_model_calls"),
            "network_calls": response.get("network_calls"),
        } if received else None),
        "retry_performed": False,
    })


def build_preflight(config_path: str | Path) -> dict[str, Any]:
    config = load_config(config_path)
    items = build_items(config)
    metadata = _ollama_model_metadata(config["judge"]["model"])
    version = ollama_version()
    schemas = {item["item_id"]: judgment_schema(item) for item in items}
    checks = {
        "locked_outputs_immutable_and_failure_retained": config["_locked"]["status"] == "case04_output_lock_failed_retained",
        "only_known_b20_check_failed": [k for k, value in config["_locked"]["checks"].items() if not value] == ["all_provider_calls_accounted"],
        "all_eight_locked_replies_present": len(items) == 8,
        "exact_ab_ba_pairing": [x["order"] for x in items] == ["AB", "BA"] * 4,
        "correction_schema_tracks_eligibility": all(
            schema["properties"]["scores"]["items"]["properties"]["correction"]["type"]
            == ("integer" if item["annotation"]["correction_eligible"] else "null")
            for item, schema in zip(items, schemas.values())
        ),
        "judge_digest_exact": metadata["digest"] == config["judge"]["digest"],
        "ollama_version_exact": version == config["transport"]["ollama_version"],
        "zero_generation_or_judge_calls": metadata["generation_calls"] == 0,
        "diagnostic_only_boundary_frozen": config["success"]["diagnostic_only"] is True,
    }
    return {
        "schema": "uruha_p3_case04_native_diagnostic_grade_preflight_v1", "phase": "P3-B21",
        "status": "ready_for_case04_native_diagnostic_review" if all(checks.values()) else "not_ready_for_case04_native_diagnostic_review",
        "config_sha256": config["_config_sha256"], "checks": checks,
        "judge_metadata": metadata, "ollama_version": version,
        "item_manifest": [{
            "item_id": item["item_id"],
            "prompt_sha256": canonical_sha256(build_messages(item)),
            "schema_sha256": canonical_sha256(schemas[item["item_id"]]),
        } for item in items],
        "annotation_file_accessed": True, "case04_annotation_turns_used": 4,
        "other_case_annotations_used": 0, "generation_outputs_mutated": False,
        "generation_rerun": False, "real_model_calls": 0, "network_calls": 0,
        "paid_calls": 0,
        "claim_boundary": "Readiness only. B20 remains failed; no judge inference, quality advantage, holdout, or human preference result exists.",
    }


def verify_release(config: Mapping[str, Any], release_path: str | Path, preflight_path: str | Path) -> None:
    release_path, preflight_path = Path(release_path).resolve(), Path(preflight_path).resolve()
    release, preflight = _read(release_path), _read(preflight_path)
    if release.get("schema") != RELEASE_SCHEMA or release.get("phase") != "P3-B21" or release.get("status") != "released_for_case04_native_diagnostic_grade":
        raise P3ContractError("p3_b21_release_invalid")
    expected = {
        "config": "configs/p3_case04_native_diagnostic_grade_v1.json",
        "implementation": "p3_case04_native_diagnostic_grade.py",
        "shared_judge": "p3_case03_proxy_grade.py",
        "native_reference": "p3_native_judge_schema_probe.py",
        "tests": "test_p3_case04_native_diagnostic_grade.py",
        "preflight": "analysis/p3_b21_case04_native_diagnostic_grade_preflight_2026-09-15.json",
    }
    if set(release.get("artifacts", {})) != set(expected):
        raise P3ContractError("p3_b21_release_artifacts_invalid")
    for name, relative in expected.items():
        expected_binding = {
            "path": relative,
            "sha256": hashlib.sha256((config["_repo"] / relative).read_bytes()).hexdigest(),
        }
        if release["artifacts"][name] != expected_binding:
            raise P3ContractError("p3_b21_release_artifact_mismatch", name)
    if preflight_path != (config["_repo"] / expected["preflight"]).resolve() or preflight.get("status") != "ready_for_case04_native_diagnostic_review":
        raise P3ContractError("p3_b21_preflight_invalid")
    if release.get("authorization") != {
        "judge_model": "qwen3.5:9b", "judge_calls_exact": 8,
        "automatic_retry": False, "localhost_only": True,
        "checkpoint_root": "analysis/p3_b21_case04_native_diagnostic_grade_checkpoints_v1",
        "result_path": "analysis/p3_b21_case04_native_diagnostic_grade_result_2026-09-15.json",
        "generation_rerun": False, "diagnostic_only": True,
        "human_preference_claim": False, "formal_advantage_claim": False,
    }:
        raise P3ContractError("p3_b21_authorization_invalid")


def run_grade(
    config_path: str | Path, release_path: str | Path, preflight_path: str | Path,
    checkpoint_root: str | Path,
    transport: Callable[[Mapping[str, Any], Mapping[str, Any], list[dict[str, str]]], Mapping[str, Any]] = native_transport,
) -> dict[str, Any]:
    config = load_config(config_path)
    verify_release(config, release_path, preflight_path)
    root = Path(checkpoint_root).resolve()
    if root.exists():
        raise P3ContractError("p3_b21_checkpoint_root_exists")
    rows: list[dict[str, Any]] = []
    failure: dict[str, Any] | None = None
    started = time.monotonic()
    with localhost_network_only() as network_attempts:
        for item in build_items(config):
            item_root = root / item["turn_id"] / item["order"]
            messages = build_messages(item)
            schema = judgment_schema(item)
            body = native_body(config, item, messages)
            _write_checkpoint(item_root / "intent.json", _signed({
                "schema": "uruha_p3_case04_native_diagnostic_grade_intent_v1",
                "phase": "P3-B21", "item_id": item["item_id"],
                "prompt_sha256": canonical_sha256(messages),
                "anonymous_replies_sha256": canonical_sha256(item["anonymous_replies"]),
                "format_schema_sha256": canonical_sha256(schema),
                "native_body_sha256": canonical_sha256(body),
                "judge_model": config["judge"]["model"], "automatic_retry": False,
            }))
            response: dict[str, Any] | None = None
            try:
                response = dict(transport(config, item, messages))
                judgment = validate_judgment(response["content"], item)
                if response["finish_reason"] == "length":
                    raise P3ContractError("p3_b21_native_length_stop")
            except Exception as exc:
                failure = failure_record(item["item_id"], exc, response)
                _write_checkpoint(item_root / "failure.json", failure)
                break
            complete = _signed({
                "schema": "uruha_p3_case04_native_diagnostic_grade_complete_v1",
                "phase": "P3-B21", "item_id": item["item_id"],
                "judgment": judgment,
                "raw_content_sha256": canonical_sha256(response["content"]),
                "finish_reason": response["finish_reason"],
                "usage": {k: response[k] for k in ("prompt_tokens", "completion_tokens", "wall_seconds")},
                "result": {"real_model_calls": 1, "network_calls": 1},
                "retry_performed": False,
            })
            _write_checkpoint(item_root / "complete.json", complete)
            rows.append({
                "item_id": item["item_id"], "turn_id": item["turn_id"], "order": item["order"],
                "slot_to_condition": item["slot_to_condition"],
                "anonymous_replies": item["anonymous_replies"], "judgment": judgment,
                "finish_reason": response["finish_reason"], "usage": complete["usage"],
                "real_model_calls": 1, "network_calls": 1,
            })
    evidence = summarize_checkpoint_evidence(root)
    score_summary = summarize(rows, config) if rows else None
    coverage = len(rows) / 8
    checks = {
        "all_eight_judgments_valid": len(rows) == 8 and failure is None,
        "grading_coverage_at_least_95pct": coverage >= config["success"]["minimum_grading_coverage"],
        "order_agreement_at_least_90pct": score_summary is not None and score_summary["order_agreement_rate"] >= config["success"]["minimum_order_agreement"],
        "all_invoked_calls_accounted_once": evidence["provider_call_evidence"] == evidence["network_call_evidence"] == evidence["declared_invocation_intents"],
        "exactly_eight_calls_if_complete": len(rows) != 8 or evidence["provider_call_evidence"] == 8,
        "no_retry": evidence["declared_invocation_intents"] == len(rows) + int(failure is not None) <= 8,
        "localhost_only": all(x["loopback_allowed"] is True for x in network_attempts),
        "locked_outputs_unchanged": hashlib.sha256((config["_repo"] / config["locked_outputs"]["path"]).read_bytes()).hexdigest() == config["locked_outputs"]["sha256"],
        "locked_generation_failure_remains_failed": config["_locked"]["status"] == "case04_output_lock_failed_retained",
    }
    status = (
        "case04_native_diagnostic_grade_complete"
        if all(checks.values()) else "case04_native_diagnostic_inconclusive_retained"
    )
    return {
        "schema": RESULT_SCHEMA, "phase": "P3-B21", "status": status,
        "config_sha256": config["_config_sha256"],
        "release_sha256": hashlib.sha256(Path(release_path).read_bytes()).hexdigest(),
        "locked_output_sha256": config["locked_outputs"]["sha256"],
        "case_id": CASE_ID, "rows": rows, "failure": failure,
        "summary": score_summary, "generation_costs_from_b20": _costs(config["_locked"]),
        "checks": checks, "grading_coverage": round(coverage, 4),
        "judge_calls": evidence["provider_call_evidence"],
        "judge_prompt_tokens": evidence["provider_prompt_tokens_observed"],
        "judge_completion_tokens": evidence["provider_completion_tokens_observed"],
        "judge_wall_seconds": round(sum(x["usage"]["wall_seconds"] for x in rows) + (
            (failure.get("provider_actual_usage") or {}).get("wall_seconds", 0) if failure else 0
        ), 6),
        "checkpoint_evidence": evidence,
        "total_runner_wall_seconds": round(time.monotonic() - started, 6),
        "network_attempts": network_attempts, "paid_calls": 0,
        "annotation_file_accessed": True, "case04_annotation_turns_used": 4,
        "other_case_annotations_used": 0, "generation_outputs_mutated": False,
        "generation_rerun": False, "future_turns_accessed": 0,
        "confirmation_accessed": 0, "production_database_accessed": False,
        "human_preference": "unavailable",
        "formal_quality_gate": "not_evaluable_after_b20_generation_gate_failure",
        "claim_boundary": "This is an eight-call maximum, one-case, one-model developer-proxy diagnosis of immutable failed-gate generation outputs. It cannot establish product advantage, human preference, holdout validity, or the formal quality gate.",
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
                raise P3ContractError("p3_b21_run_artifacts_required")
            payload = run_grade(args.config, args.release, args.preflight, args.checkpoint_root)
    except P3ContractError as exc:
        evidence = summarize_checkpoint_evidence(args.checkpoint_root or "")
        payload = {
            "schema": "uruha_p3_case04_native_diagnostic_grade_refusal_v1",
            "phase": "P3-B21", "status": "refused_or_failed_retained",
            "contract_code": exc.code, "checkpoint_evidence": evidence,
            "real_model_calls": evidence["provider_call_evidence"],
            "automatic_retry": False, "paid_calls": 0,
            "claim_boundary": "Failure is retained; no diagnostic, quality, or advantage conclusion is authorized.",
        }
    write_new_json(output, payload)
    return 0 if payload.get("status") in {
        "ready_for_case04_native_diagnostic_review",
        "case04_native_diagnostic_grade_complete",
    } else 1


if __name__ == "__main__":
    raise SystemExit(main())
