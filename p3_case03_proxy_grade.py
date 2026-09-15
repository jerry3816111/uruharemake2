#!/usr/bin/env python3
"""P3-B17 blind AB/BA proxy grading for immutable case-03 outputs."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import time
from typing import Any, Callable, Mapping
import urllib.request

from p3_product_comparison import P3ContractError, canonical_sha256, write_new_json
from p3_product_worker import _ollama_model_metadata, localhost_network_only, summarize_checkpoint_evidence


SCHEMA = "uruha_p3_case03_proxy_grade_v1"
RELEASE_SCHEMA = "uruha_p3_case03_proxy_grade_release_v1"
RESULT_SCHEMA = "uruha_p3_case03_proxy_grade_result_v1"
SCORE_KEYS = {
    "reply_slot", "attunement", "grounding", "correction", "continuity",
    "unsupported_assertion", "japanese_issue", "identity_issue",
    "evidence_turn_ids", "reply_quote",
}


def _read(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise P3ContractError("p3_b17_invalid_json", str(path)) from exc
    if not isinstance(value, dict):
        raise P3ContractError("p3_b17_invalid_json", str(path))
    return value


def _ref(repo: Path, value: Any, expected: Mapping[str, Any], code: str) -> Path:
    if not isinstance(value, Mapping) or any(value.get(k) != v for k, v in expected.items()):
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
        "schema", "status", "purpose", "comparison_design", "locked_outputs",
        "case_source", "annotations", "conditions", "judge", "rubric",
        "execution_boundary", "success",
    }
    if set(raw) != expected_root or raw.get("schema") != SCHEMA:
        raise P3ContractError("p3_b17_schema_mismatch")
    if raw.get("status") != "preregistered_not_executed" or raw.get("purpose") != "blind_ab_ba_proxy_grade_of_locked_case03_outputs":
        raise P3ContractError("p3_b17_status_mismatch")
    repo = config_path.parent.parent
    design_path = _ref(repo, raw["comparison_design"], {
        "path": "configs/p3_product_comparison_v1.json",
        "sha256": "1e6d3b0600740b3dee7207ffc5c4f9cc9247a5feba2b967bdab4586522f7b836",
    }, "p3_b17_design_mismatch")
    lock_path = _ref(repo, raw["locked_outputs"], {
        "path": "analysis/p3_b16_case03_output_lock_result_2026-09-15.json",
        "sha256": "cb1284cee5ac3e847302d62528a2dc4dbb9fc33d43e1361dee92348a29461c93",
        "required_status": "case03_outputs_locked",
        "locked_commit": "b8758b0",
    }, "p3_b17_lock_mismatch")
    source_path = _ref(repo, raw["case_source"], {
        "path": "datasets/p3_case03_generation_source_v1.json",
        "sha256": "cfae115a29453d51db948c39be2caf7c8d686dbda942ef0e45a591c31706a01a",
    }, "p3_b17_source_mismatch")
    annotation_path = _ref(repo, raw["annotations"], {
        "path": "datasets/p3_developer_smoke_annotations_v1.json",
        "sha256": "aec1f4fbd88a96b180ad5c90f8f2f7a362a01b57d0d26a22b26af3ff25a5a3ea",
        "case_id": "p3-smoke-emotional-bid-ja",
        "role": "developer_proxy_rubric_not_gold_reply_or_human_preference",
        "case_turns_used": 4,
        "other_case_annotations_used": 0,
    }, "p3_b17_annotation_mismatch")
    design, locked, source, annotations = map(_read, (design_path, lock_path, source_path, annotation_path))
    if locked.get("status") != "case03_outputs_locked" or locked.get("case_id") != raw["annotations"]["case_id"]:
        raise P3ContractError("p3_b17_lock_status_invalid")
    if locked.get("annotations_accessed") != 0 or locked.get("future_turns_accessed") != 0:
        raise P3ContractError("p3_b17_lock_was_not_blind")
    if source.get("case_id") != locked.get("case_id") or len(source.get("turns", [])) != 4:
        raise P3ContractError("p3_b17_source_case_invalid")
    case_annotations = [x for x in annotations.get("cases", []) if x.get("case_id") == locked["case_id"]]
    if len(case_annotations) != 1 or len(case_annotations[0].get("turns", [])) != 4:
        raise P3ContractError("p3_b17_case_annotation_invalid")
    if annotations.get("annotation_role") != raw["annotations"]["role"]:
        raise P3ContractError("p3_b17_annotation_role_invalid")
    if raw.get("conditions") != ["product_system", "full_history_direct"]:
        raise P3ContractError("p3_b17_conditions_invalid")
    frozen_grading = design["grading"]
    if raw.get("judge") != {
        "model": frozen_grading["judge_model"],
        "digest": "dec52a44569a2a25341c4e4d3fee25846eed4f6f0b936278e3a3c900bb99d37c",
        "temperature": frozen_grading["judge_temperature"],
        "seed": frozen_grading["judge_seed"],
        "top_p": 1,
        "num_ctx": 8192,
        "think": False,
        "max_completion_tokens": frozen_grading["judge_output_tokens_max"],
        "timeout_seconds": frozen_grading["judge_timeout_seconds"],
        "orders": frozen_grading["judge_orders"],
        "retries": frozen_grading["judge_retries"],
        "condition_names_hidden": frozen_grading["judge_condition_names_hidden"],
    }:
        raise P3ContractError("p3_b17_judge_drift")
    if raw.get("rubric") != {
        "dimensions": frozen_grading["dimensions"], "scale": frozen_grading["scale"],
        "correction_only_if_eligible": frozen_grading["correction_only_if_eligible"],
        "unsupported_assertion_boolean": True, "japanese_issue_boolean": True,
        "identity_issue_boolean": True, "reply_quote_must_be_exact_span": True,
        "evidence_turn_ids_must_be_currently_visible": True,
    }:
        raise P3ContractError("p3_b17_rubric_drift")
    if raw.get("execution_boundary") != {
        "judge_calls_exact": 8, "automatic_retry": False, "concurrency": 1,
        "localhost_only": True, "generation_outputs_mutable": False,
        "future_turn_access": False, "confirmation_access": False,
        "production_database_access": False, "remote_paid_calls": False,
        "real_model_calls_authorized_by_this_config": False,
        "separate_release_required": True,
    }:
        raise P3ContractError("p3_b17_boundary_drift")
    if raw.get("success") != {
        "all_eight_judgments_valid": True,
        "minimum_grading_coverage": frozen_grading["minimum_grading_coverage"],
        "minimum_order_agreement": frozen_grading["minimum_order_agreement"],
        "single_case_can_pass_24_case_quality_gate": False,
        "human_preference_claim_allowed": False,
        "formal_advantage_claim_allowed": False,
    }:
        raise P3ContractError("p3_b17_success_drift")
    result = json.loads(json.dumps(raw, ensure_ascii=False))
    result.update({
        "_repo": repo, "_config_path": config_path,
        "_config_sha256": hashlib.sha256(config_path.read_bytes()).hexdigest(),
        "_locked": locked, "_source": source,
        "_case_annotations": case_annotations[0],
    })
    return result


def _direct_text(row: Mapping[str, Any]) -> str:
    final = row.get("final")
    if not isinstance(final, Mapping) or not isinstance(final.get("content"), str):
        raise P3ContractError("p3_b17_direct_output_invalid")
    return final["content"]


def build_items(config: Mapping[str, Any]) -> list[dict[str, Any]]:
    locked = config["_locked"]
    turns = config["_source"]["turns"]
    product = {x["turn_id"]: x for x in locked["product_turns"]}
    direct = {x["turn_id"]: x for x in locked["direct_turns"]}
    annotations = {x["turn_id"]: x for x in config["_case_annotations"]["turns"]}
    prefix: list[dict[str, str]] = []
    items: list[dict[str, Any]] = []
    for turn in turns:
        turn_id = turn["turn_id"]
        if turn_id not in product or turn_id not in direct or turn_id not in annotations:
            raise P3ContractError("p3_b17_turn_alignment_invalid")
        replies = {
            "product_system": product[turn_id]["visible_reply"],
            "full_history_direct": _direct_text(direct[turn_id]),
        }
        for value in replies.values():
            if not isinstance(value, str) or not value.strip():
                raise P3ContractError("p3_b17_locked_reply_invalid")
        for order in config["judge"]["orders"]:
            slot_to_condition = (
                {"A": "product_system", "B": "full_history_direct"}
                if order == "AB" else
                {"A": "full_history_direct", "B": "product_system"}
            )
            items.append({
                "item_id": f"{turn_id}:{order}", "turn_id": turn_id,
                "order": order, "visible_history": json.loads(json.dumps(prefix, ensure_ascii=False)),
                "current_input": turn["content"], "annotation": annotations[turn_id],
                "slot_to_condition": slot_to_condition,
                "anonymous_replies": {slot: replies[condition] for slot, condition in slot_to_condition.items()},
                "currently_visible_turn_ids": [x["turn_id"] for x in turns if turns.index(x) <= turns.index(turn)],
            })
        prefix.extend([
            {"turn_id": turn_id, "role": "user", "content": turn["content"]},
            {"turn_id": f"{turn_id}-system-reply", "role": "assistant", "content": replies["product_system"]},
        ])
    return items


def build_messages(item: Mapping[str, Any]) -> list[dict[str, str]]:
    system = (
        "You are a strict blinded dialogue-response evaluator. Judge only the visible history, current input, "
        "and supplied developer proxy rubric. The rubric describes acceptable behaviors, not a gold sentence. "
        "Do not infer condition identity. Scores are integers 0, 1, or 2. attunement: 0 ignores or violates the "
        "visible need, 1 partly addresses it or asks an unnecessary generic question, 2 responds to the grounded "
        "purpose or clarifies uncertainty well. grounding: 0 fabricates or misattributes, 1 mostly grounded but "
        "imprecise, 2 preserves facts, speakers, and unknown boundaries. correction: 0 continues a withdrawn "
        "assumption, 1 acknowledges but mixes it back in, 2 naturally yields and respects the new information; "
        "use null when correction_eligible is false. continuity: 0 contradicts or forces irrelevant history, "
        "1 partly maintains it, 2 preserves and updates only relevant history. unsupported_assertion, "
        "japanese_issue, and identity_issue are booleans. evidence_turn_ids must use only visible user turn IDs. "
        "reply_quote must be a non-empty exact substring of that reply. preference is A, B, or tie. Return exactly "
        "one JSON object with keys scores and preference; scores must contain exactly A and B and no extra keys."
    )
    payload = {
        "visible_history": item["visible_history"],
        "current_turn": {"turn_id": item["turn_id"], "content": item["current_input"]},
        "developer_proxy_rubric": item["annotation"],
        "anonymous_replies": item["anonymous_replies"],
        "required_schema": {
            "scores": [{
                "reply_slot": "A_or_B", "attunement": "0_1_2", "grounding": "0_1_2",
                "correction": "0_1_2_or_null", "continuity": "0_1_2",
                "unsupported_assertion": "boolean", "japanese_issue": "boolean",
                "identity_issue": "boolean", "evidence_turn_ids": ["visible_user_turn_id"],
                "reply_quote": "exact_nonempty_reply_span",
            }],
            "preference": "A_or_B_or_tie",
        },
    }
    return [{"role": "system", "content": system}, {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}]


def validate_judgment(raw_text: str, item: Mapping[str, Any]) -> dict[str, Any]:
    try:
        value = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise P3ContractError("p3_b17_judge_json_invalid") from exc
    if not isinstance(value, Mapping) or set(value) != {"scores", "preference"}:
        raise P3ContractError("p3_b17_judge_schema_invalid")
    if value["preference"] not in {"A", "B", "tie"}:
        raise P3ContractError("p3_b17_preference_invalid")
    scores = value["scores"]
    if not isinstance(scores, list) or len(scores) != 2:
        raise P3ContractError("p3_b17_scores_invalid")
    by_slot: dict[str, dict[str, Any]] = {}
    correction_eligible = item["annotation"]["correction_eligible"]
    visible = set(item["currently_visible_turn_ids"])
    for score in scores:
        if not isinstance(score, Mapping) or set(score) != SCORE_KEYS:
            raise P3ContractError("p3_b17_score_schema_invalid")
        slot = score["reply_slot"]
        if slot not in {"A", "B"} or slot in by_slot:
            raise P3ContractError("p3_b17_reply_slot_invalid")
        if any(score[k] not in {0, 1, 2} for k in ("attunement", "grounding", "continuity")):
            raise P3ContractError("p3_b17_score_range_invalid")
        correction = score["correction"]
        if (correction_eligible and correction not in {0, 1, 2}) or (not correction_eligible and correction is not None):
            raise P3ContractError("p3_b17_correction_applicability_invalid")
        if any(type(score[k]) is not bool for k in ("unsupported_assertion", "japanese_issue", "identity_issue")):
            raise P3ContractError("p3_b17_issue_type_invalid")
        evidence = score["evidence_turn_ids"]
        if not isinstance(evidence, list) or not evidence or not all(isinstance(x, str) for x in evidence) or set(evidence) - visible:
            raise P3ContractError("p3_b17_evidence_invalid")
        quote = score["reply_quote"]
        if not isinstance(quote, str) or not quote or quote not in item["anonymous_replies"][slot]:
            raise P3ContractError("p3_b17_quote_invalid")
        by_slot[slot] = dict(score)
    if set(by_slot) != {"A", "B"}:
        raise P3ContractError("p3_b17_reply_slot_invalid")
    return {"scores": [by_slot["A"], by_slot["B"]], "preference": value["preference"]}


def _signed(value: Mapping[str, Any]) -> dict[str, Any]:
    result = dict(value)
    result["record_sha256"] = canonical_sha256(result)
    return result


def _write_checkpoint(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise P3ContractError("p3_b17_checkpoint_exists", str(path))
    path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def local_transport(config: Mapping[str, Any], messages: list[dict[str, str]]) -> dict[str, Any]:
    judge = config["judge"]
    body = {
        "model": judge["model"], "messages": messages,
        "temperature": judge["temperature"], "seed": judge["seed"],
        "top_p": judge["top_p"], "max_tokens": judge["max_completion_tokens"],
        "stream": False, "think": judge["think"],
        "options": {"num_ctx": judge["num_ctx"]},
        "response_format": {"type": "json_object"},
    }
    request = urllib.request.Request(
        "http://127.0.0.1:11434/v1/chat/completions",
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST",
    )
    started = time.monotonic()
    with urllib.request.urlopen(request, timeout=judge["timeout_seconds"]) as response:
        payload = json.loads(response.read().decode("utf-8"))
    elapsed = time.monotonic() - started
    try:
        content = payload["choices"][0]["message"]["content"]
        prompt_tokens = payload["usage"]["prompt_tokens"]
        completion_tokens = payload["usage"]["completion_tokens"]
    except (KeyError, IndexError, TypeError) as exc:
        raise P3ContractError("p3_b17_provider_payload_invalid") from exc
    if payload.get("model") != judge["model"] or not isinstance(content, str):
        raise P3ContractError("p3_b17_provider_model_or_content_invalid")
    return {
        "content": content, "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens, "wall_seconds": round(elapsed, 6),
        "model": payload.get("model"), "network_calls": 1, "real_model_calls": 1,
    }


def _mapped_preference(judgment: Mapping[str, Any], mapping: Mapping[str, str]) -> str:
    value = judgment["preference"]
    return "tie" if value == "tie" else mapping[value]


def summarize(rows: list[dict[str, Any]], config: Mapping[str, Any]) -> dict[str, Any]:
    conditions = config["conditions"]
    dimensions = config["rubric"]["dimensions"]
    scores: dict[str, dict[str, list[float]]] = {
        c: {d: [] for d in dimensions} for c in conditions
    }
    issues = {c: {k: 0 for k in ("unsupported_assertion", "japanese_issue", "identity_issue")} for c in conditions}
    preferences = {c: 0 for c in conditions} | {"tie": 0}
    by_turn: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        mapping = row["slot_to_condition"]
        preferences[_mapped_preference(row["judgment"], mapping)] += 1
        by_turn.setdefault(row["turn_id"], []).append(row)
        for score in row["judgment"]["scores"]:
            condition = mapping[score["reply_slot"]]
            for dimension in dimensions:
                if score[dimension] is not None:
                    scores[condition][dimension].append(score[dimension])
            for issue in issues[condition]:
                issues[condition][issue] += int(score[issue])
    means = {
        c: {d: round(sum(v) / len(v), 4) if v else None for d, v in ds.items()}
        for c, ds in scores.items()
    }
    rates = {
        c: {k: round(v / len(rows), 4) for k, v in counts.items()}
        for c, counts in issues.items()
    }
    turn_agreements = {}
    for turn_id, pair in by_turn.items():
        mapped = [_mapped_preference(x["judgment"], x["slot_to_condition"]) for x in pair]
        turn_agreements[turn_id] = {"mapped_preferences": mapped, "agrees": len(mapped) == 2 and mapped[0] == mapped[1]}
    agreement = sum(x["agrees"] for x in turn_agreements.values()) / len(turn_agreements)
    deltas = {
        d: round(means["product_system"][d] - means["full_history_direct"][d], 4)
        if means["product_system"][d] is not None and means["full_history_direct"][d] is not None else None
        for d in dimensions
    }
    return {
        "mean_scores": means, "product_minus_direct": deltas,
        "issue_rates": rates, "mapped_preference_counts": preferences,
        "order_agreement_by_turn": turn_agreements,
        "order_agreement_rate": round(agreement, 4),
    }


def _costs(locked: Mapping[str, Any]) -> dict[str, Any]:
    product_calls = [call for row in locked["product_turns"] for call in row["calls"]]
    direct_calls = [call for row in locked["direct_turns"] for call in row["calls"]]
    def one(calls: list[Mapping[str, Any]], rows: list[Mapping[str, Any]]) -> dict[str, Any]:
        return {
            "provider_calls": len(calls),
            "prompt_tokens": sum(x["usage"]["prompt_tokens"] for x in calls),
            "completion_tokens": sum(x["usage"]["completion_tokens"] for x in calls),
            "generation_tokens": sum(x["usage"]["prompt_tokens"] + x["usage"]["completion_tokens"] for x in calls),
            "turn_wall_seconds": round(sum(x["turn_wall_seconds"] for x in rows), 6),
        }
    return {
        "product_system": one(product_calls, locked["product_turns"]),
        "full_history_direct": one(direct_calls, locked["direct_turns"]),
    }


def build_preflight(config_path: str | Path) -> dict[str, Any]:
    config = load_config(config_path)
    metadata = _ollama_model_metadata(config["judge"]["model"])
    items = build_items(config)
    checks = {
        "locked_outputs_complete_before_annotation_access": config["_locked"]["status"] == "case03_outputs_locked",
        "exact_eight_blinded_ordered_items": len(items) == 8 and all(set(x["anonymous_replies"]) == {"A", "B"} for x in items),
        "judge_digest_exact": metadata["digest"] == config["judge"]["digest"],
        "zero_generation_calls": metadata["generation_calls"] == 0,
        "single_case_cannot_pass_formal_gate": config["success"]["single_case_can_pass_24_case_quality_gate"] is False,
    }
    return {
        "schema": "uruha_p3_case03_proxy_grade_preflight_v1", "phase": "P3-B17",
        "status": "ready_for_case03_proxy_grade_review" if all(checks.values()) else "not_ready_for_case03_proxy_grade_review",
        "config_sha256": config["_config_sha256"], "checks": checks,
        "judge_metadata": metadata,
        "item_manifest": [{"item_id": x["item_id"], "prompt_sha256": canonical_sha256(build_messages(x))} for x in items],
        "annotation_file_accessed": True, "case03_annotation_turns_used": 4,
        "other_case_annotations_used": 0, "generation_outputs_mutated": False,
        "real_model_calls": 0, "network_calls": 0, "paid_calls": 0,
        "claim_boundary": "Readiness only. Annotation access occurred after the immutable B16 commit; no judge inference or quality result exists yet.",
    }


def verify_release(config: Mapping[str, Any], release_path: str | Path, preflight_path: str | Path) -> dict[str, Any]:
    release_file, preflight_file = Path(release_path).resolve(), Path(preflight_path).resolve()
    release, preflight = _read(release_file), _read(preflight_file)
    repo = config["_repo"]
    if release.get("schema") != RELEASE_SCHEMA or release.get("phase") != "P3-B17" or release.get("status") != "released_for_case03_proxy_grade":
        raise P3ContractError("p3_b17_release_invalid")
    bindings = release.get("artifacts")
    expected_paths = {
        "config": "configs/p3_case03_proxy_grade_v1.json",
        "implementation": "p3_case03_proxy_grade.py",
        "tests": "test_p3_case03_proxy_grade.py",
        "preflight": "analysis/p3_b17_case03_proxy_grade_preflight_2026-09-15.json",
    }
    if not isinstance(bindings, Mapping) or set(bindings) != set(expected_paths):
        raise P3ContractError("p3_b17_release_artifacts_invalid")
    for name, relative in expected_paths.items():
        expected = (repo / relative).resolve()
        binding = bindings[name]
        if binding != {"path": relative, "sha256": hashlib.sha256(expected.read_bytes()).hexdigest()}:
            raise P3ContractError("p3_b17_release_artifact_mismatch", name)
    if preflight_file != (repo / expected_paths["preflight"]).resolve() or preflight.get("status") != "ready_for_case03_proxy_grade_review":
        raise P3ContractError("p3_b17_preflight_invalid")
    if release.get("authorization") != {
        "judge_model": "qwen3.5:9b", "judge_calls_exact": 8,
        "automatic_retry": False, "localhost_only": True,
        "checkpoint_root": "analysis/p3_b17_case03_proxy_grade_checkpoints_v1",
        "result_path": "analysis/p3_b17_case03_proxy_grade_result_2026-09-15.json",
        "human_preference_claim": False, "formal_advantage_claim": False,
    }:
        raise P3ContractError("p3_b17_authorization_invalid")
    return release


def run_grade(
    config_path: str | Path, release_path: str | Path, preflight_path: str | Path,
    checkpoint_root: str | Path,
    transport: Callable[[Mapping[str, Any], list[dict[str, str]]], Mapping[str, Any]] = local_transport,
) -> dict[str, Any]:
    config = load_config(config_path)
    release = verify_release(config, release_path, preflight_path)
    root = Path(checkpoint_root).resolve()
    if root.exists():
        raise P3ContractError("p3_b17_checkpoint_root_exists")
    rows: list[dict[str, Any]] = []
    network_attempts: list[dict[str, Any]] = []
    started = time.monotonic()
    with localhost_network_only() as network_attempts:
        for item in build_items(config):
            item_root = root / item["turn_id"] / item["order"]
            messages = build_messages(item)
            intent = _signed({
                "schema": "uruha_p3_case03_proxy_grade_intent_v1", "phase": "P3-B17",
                "item_id": item["item_id"], "prompt_sha256": canonical_sha256(messages),
                "anonymous_replies_sha256": canonical_sha256(item["anonymous_replies"]),
                "judge_model": config["judge"]["model"], "automatic_retry": False,
            })
            _write_checkpoint(item_root / "intent.json", intent)
            try:
                response = dict(transport(config, messages))
                judgment = validate_judgment(response["content"], item)
            except Exception as exc:
                failure = _signed({
                    "schema": "uruha_p3_case03_proxy_grade_failure_v1", "phase": "P3-B17",
                    "item_id": item["item_id"], "error_type": type(exc).__name__,
                    "contract_code": getattr(exc, "code", "transport_or_validation_failure"),
                    "retry_performed": False,
                })
                _write_checkpoint(item_root / "failure.json", failure)
                raise P3ContractError("p3_b17_judge_failure_no_retry", item["item_id"]) from exc
            complete = _signed({
                "schema": "uruha_p3_case03_proxy_grade_complete_v1", "phase": "P3-B17",
                "item_id": item["item_id"], "judgment": judgment,
                "raw_content_sha256": canonical_sha256(response["content"]),
                "usage": {k: response[k] for k in ("prompt_tokens", "completion_tokens", "wall_seconds")},
                "model": response["model"], "real_model_calls": response["real_model_calls"],
                "network_calls": response["network_calls"], "retry_performed": False,
            })
            _write_checkpoint(item_root / "complete.json", complete)
            rows.append({
                "item_id": item["item_id"], "turn_id": item["turn_id"], "order": item["order"],
                "slot_to_condition": item["slot_to_condition"], "anonymous_replies": item["anonymous_replies"],
                "judgment": judgment, "usage": complete["usage"],
                "real_model_calls": response["real_model_calls"], "network_calls": response["network_calls"],
            })
    summary = summarize(rows, config)
    checks = {
        "all_eight_judgments_valid": len(rows) == 8,
        "grading_coverage_at_least_95pct": len(rows) / 8 >= config["success"]["minimum_grading_coverage"],
        "order_agreement_at_least_90pct": summary["order_agreement_rate"] >= config["success"]["minimum_order_agreement"],
        "all_calls_accounted_once": sum(x["real_model_calls"] for x in rows) == sum(x["network_calls"] for x in rows) == 8,
        "localhost_only": all(x["loopback_allowed"] is True for x in network_attempts),
        "locked_outputs_unchanged": hashlib.sha256((config["_repo"] / config["locked_outputs"]["path"]).read_bytes()).hexdigest() == config["locked_outputs"]["sha256"],
    }
    return {
        "schema": RESULT_SCHEMA, "phase": "P3-B17",
        "status": "case03_proxy_grade_complete" if all(checks.values()) else "case03_proxy_grade_inconclusive_retained",
        "config_sha256": config["_config_sha256"],
        "release_sha256": hashlib.sha256(Path(release_path).read_bytes()).hexdigest(),
        "locked_output_sha256": config["locked_outputs"]["sha256"],
        "case_id": config["annotations"]["case_id"], "rows": rows,
        "summary": summary, "generation_costs_from_b16": _costs(config["_locked"]),
        "checks": checks, "judge_calls": len(rows),
        "judge_prompt_tokens": sum(x["usage"]["prompt_tokens"] for x in rows),
        "judge_completion_tokens": sum(x["usage"]["completion_tokens"] for x in rows),
        "judge_wall_seconds": round(sum(x["usage"]["wall_seconds"] for x in rows), 6),
        "total_runner_wall_seconds": round(time.monotonic() - started, 6),
        "network_attempts": network_attempts, "paid_calls": 0,
        "annotation_file_accessed": True, "case03_annotation_turns_used": 4,
        "other_case_annotations_used": 0, "future_turns_accessed": 0,
        "confirmation_accessed": 0, "production_database_accessed": False,
        "human_preference": "unavailable", "formal_24_case_gate": "not_evaluable_from_one_developer_case",
        "claim_boundary": "This is an eight-call, one-case, one-model developer proxy grade. It is not a human preference result, independent holdout, formal 24-case gate, or general product-advantage conclusion.",
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
                raise P3ContractError("p3_b17_run_artifacts_required")
            payload = run_grade(args.config, args.release, args.preflight, args.checkpoint_root)
    except P3ContractError as exc:
        evidence = summarize_checkpoint_evidence(args.checkpoint_root or "")
        payload = {
            "schema": "uruha_p3_case03_proxy_grade_failure_v1", "phase": "P3-B17",
            "status": "failed_after_judge_intent_retained" if evidence["declared_invocation_intents"] else "refused_before_judge",
            "contract_code": exc.code, "checkpoint_evidence": evidence,
            "real_model_calls": evidence["provider_call_evidence"], "paid_calls": 0,
            "automatic_retry": False,
            "claim_boundary": "Failure is retained; no quality or advantage conclusion is authorized.",
        }
    write_new_json(output, payload)
    return 0 if payload.get("status") in {"ready_for_case03_proxy_grade_review", "case03_proxy_grade_complete"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
