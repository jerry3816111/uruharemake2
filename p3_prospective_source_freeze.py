#!/usr/bin/env python3
"""Validate and manifest the P3-B33 source-only prospective case freeze."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import unicodedata
from typing import Any, Mapping

from p3_product_comparison import P3ContractError, canonical_sha256, write_new_json


SCHEMA = "uruha_p3_prospective_developer_source_v2"
RESULT_SCHEMA = "uruha_p3_prospective_source_freeze_validation_v1"
FORBIDDEN_CASE_KEYS = {
    "gold_reply",
    "score",
    "scores",
    "rubric",
    "condition_preference",
    "preference",
    "winner",
    "solution_rule",
    "expected_reply",
    "annotation",
    "annotations",
}


def _read(path: str | Path) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise P3ContractError("p3_b33_json_unavailable") from exc
    if not isinstance(value, dict):
        raise P3ContractError("p3_b33_json_invalid")
    return value


def _digest_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _normalized(value: str) -> str:
    text = unicodedata.normalize("NFKC", value).casefold()
    return re.sub(r"[^\w\u3040-\u30ff\u3400-\u9fff]+", "", text)


def _walk_keys(value: Any):
    if isinstance(value, Mapping):
        for key, nested in value.items():
            yield str(key)
            yield from _walk_keys(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _walk_keys(nested)


def _verify_reference(repo: Path, value: Mapping[str, Any], expected_keys: set[str], code: str) -> None:
    if not isinstance(value, Mapping) or set(value) != expected_keys:
        raise P3ContractError(code)
    path = (repo / str(value["path"])).resolve()
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != value["sha256"]:
        raise P3ContractError(code)


def validate_source(source_path: str | Path, parent_source_path: str | Path) -> dict[str, Any]:
    source_path = Path(source_path).resolve()
    parent_path = Path(parent_source_path).resolve()
    source = _read(source_path)
    parent = _read(parent_path)
    expected_root = {
        "schema", "split", "evidence_scope", "author_role", "created_on",
        "product_freeze", "judge_transport_freeze", "source_only_boundary",
        "surface_safety_expectation", "case_count", "turns_per_case", "cases",
    }
    if set(source) != expected_root or source.get("schema") != SCHEMA:
        raise P3ContractError("p3_b33_source_schema_invalid")
    if (
        source.get("split") != "prospective_developer"
        or source.get("evidence_scope")
        != "developer_authored_after_b31_and_b32_not_formal_or_temporal_holdout"
        or source.get("author_role") != "codex_implementation_task"
        or source.get("created_on") != "2026-09-17"
    ):
        raise P3ContractError("p3_b33_source_scope_invalid")
    repo = parent_path.parent.parent
    _verify_reference(
        repo,
        source["product_freeze"],
        {"commit", "path", "sha256"},
        "p3_b33_product_freeze_invalid",
    )
    _verify_reference(
        repo,
        source["judge_transport_freeze"],
        {"commit", "path", "sha256"},
        "p3_b33_judge_freeze_invalid",
    )
    if source["product_freeze"]["commit"] != "9fb38c66d2d6f6b9ccdf0eb1ad152f1a5c77ecfa":
        raise P3ContractError("p3_b33_product_freeze_invalid")
    if source["judge_transport_freeze"]["commit"] != "8587e1cc2dd9eea8e5979959dbb087d6569cc300":
        raise P3ContractError("p3_b33_judge_freeze_invalid")
    boundary = source.get("source_only_boundary")
    if boundary != {
        "annotations_status": "not_created_or_accessed",
        "generation_status": "not_executed",
        "judge_status": "not_executed",
        "real_model_calls": 0,
        "network_calls": 0,
        "paid_calls": 0,
        "future_turn_policy": "only_current_and_prior_user_turns_visible_during_generation",
        "forbidden_case_payloads": [
            "gold_reply", "score", "rubric", "condition_preference", "winner", "solution_rule",
        ],
    }:
        raise P3ContractError("p3_b33_source_boundary_invalid")
    if source.get("surface_safety_expectation") != {
        "visible_language": "natural_japanese",
        "persona_boundary": "public_evidence_only",
        "unknown_private_state": "must_not_be_invented",
        "internal_analysis": "must_not_be_dumped_to_user",
    }:
        raise P3ContractError("p3_b33_surface_boundary_invalid")
    cases = source.get("cases")
    if not isinstance(cases, list) or source.get("case_count") != 3 or len(cases) != 3:
        raise P3ContractError("p3_b33_case_count_invalid")
    if source.get("turns_per_case") != 4:
        raise P3ContractError("p3_b33_turn_count_invalid")

    parent_turns = [
        turn
        for case in (parent.get("cases") or [])
        for turn in (case.get("turns") or [])
    ]
    parent_exact = {str(turn.get("content") or "") for turn in parent_turns}
    parent_normalized = {_normalized(text) for text in parent_exact}
    source_ids: set[str] = set()
    case_ids: set[str] = set()
    session_ids: set[str] = set()
    turn_ids: set[str] = set()
    contents: set[str] = set()
    normalized_contents: set[str] = set()
    manifests: list[dict[str, Any]] = []
    languages: list[str] = []
    family_count: dict[str, int] = {}
    for case in cases:
        if not isinstance(case, Mapping) or FORBIDDEN_CASE_KEYS & set(_walk_keys(case)):
            raise P3ContractError("p3_b33_forbidden_case_payload")
        expected_case = {
            "source_id", "case_id", "family", "language", "exposure_status",
            "derivation", "sessions", "turns",
        }
        if set(case) != expected_case:
            raise P3ContractError("p3_b33_case_schema_invalid")
        if case["exposure_status"] != "source_only_frozen_before_generation_and_annotations":
            raise P3ContractError("p3_b33_exposure_status_invalid")
        if case["source_id"] in source_ids or case["case_id"] in case_ids:
            raise P3ContractError("p3_b33_case_id_duplicate")
        source_ids.add(case["source_id"])
        case_ids.add(case["case_id"])
        languages.append(case["language"])
        family_count[case["family"]] = family_count.get(case["family"], 0) + 1
        derivation = case["derivation"]
        if derivation.get("kind") != "new_prospective_developer_authored" or any(
            derivation.get(key) is not None for key in ("parent_source_id", "translation_of")
        ) or derivation.get("prior_development_case_reuse") is not False:
            raise P3ContractError("p3_b33_derivation_invalid")
        sessions = case["sessions"]
        turns = case["turns"]
        if not isinstance(sessions, list) or len(sessions) != 2 or not isinstance(turns, list) or len(turns) != 4:
            raise P3ContractError("p3_b33_session_or_turn_count_invalid")
        local_sessions = [row["session_id"] for row in sessions]
        if len(set(local_sessions)) != 2 or set(local_sessions) & session_ids:
            raise P3ContractError("p3_b33_session_id_duplicate")
        session_ids.update(local_sessions)
        if [row["starts_at_turn_id"] for row in sessions] != [turns[0]["turn_id"], turns[2]["turn_id"]]:
            raise P3ContractError("p3_b33_session_boundary_invalid")
        if [turn["session_id"] for turn in turns] != [local_sessions[0], local_sessions[0], local_sessions[1], local_sessions[1]]:
            raise P3ContractError("p3_b33_turn_session_invalid")
        for index, turn in enumerate(turns):
            if set(turn) != {"turn_id", "session_id", "content", "content_sha256"}:
                raise P3ContractError("p3_b33_turn_schema_invalid")
            content = turn["content"]
            normalized = _normalized(content)
            if not isinstance(content, str) or not content.strip() or turn["content_sha256"] != _digest_text(content):
                raise P3ContractError("p3_b33_turn_hash_invalid")
            if turn["turn_id"] in turn_ids or content in contents or normalized in normalized_contents:
                raise P3ContractError("p3_b33_turn_duplicate")
            if content in parent_exact or normalized in parent_normalized:
                raise P3ContractError("p3_b33_parent_text_reuse")
            turn_ids.add(turn["turn_id"])
            contents.add(content)
            normalized_contents.add(normalized)
            manifests.append({
                "view_id": f"{case['case_id']}:{turn['turn_id']}",
                "case_id": case["case_id"],
                "turn_id": turn["turn_id"],
                "session_id": turn["session_id"],
                "visible_turn_ids": [row["turn_id"] for row in turns[: index + 1]],
                "locked_future_turn_ids": [row["turn_id"] for row in turns[index + 1 :]],
                "current_content_sha256": turn["content_sha256"],
            })
    checks = {
        "source_schema_exact": True,
        "three_cases_and_twelve_turns": len(cases) == 3 and len(turn_ids) == 12,
        "one_case_each_zh_en_ja": sorted(languages) == ["en", "ja", "zh"],
        "three_distinct_families": len(family_count) == 3 and all(value == 1 for value in family_count.values()),
        "all_ids_and_texts_unique": len(source_ids) == len(case_ids) == 3 and len(contents) == 12,
        "no_exact_or_normalized_b2_text_reuse": True,
        "no_gold_score_rubric_preference_or_annotation_payload": True,
        "future_turns_locked_in_all_twelve_views": all(
            len(row["visible_turn_ids"]) + len(row["locked_future_turn_ids"]) == 4
            and row["turn_id"] == row["visible_turn_ids"][-1]
            for row in manifests
        ),
        "source_only_zero_call_boundary": boundary["real_model_calls"] == boundary["network_calls"] == 0,
    }
    return {
        "schema": RESULT_SCHEMA,
        "phase": "P3-B33",
        "status": "prospective_source_only_ready_to_freeze" if all(checks.values())
        else "prospective_source_only_not_ready",
        "source_path": str(source_path.relative_to(repo)),
        "source_sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
        "parent_source_path": str(parent_path.relative_to(repo)),
        "parent_source_sha256": hashlib.sha256(parent_path.read_bytes()).hexdigest(),
        "checks": checks,
        "counts": {
            "cases": len(cases),
            "turns": len(turn_ids),
            "sessions": len(session_ids),
            "languages": {language: languages.count(language) for language in sorted(set(languages))},
            "families": family_count,
            "allowlisted_views": len(manifests),
        },
        "turn_visibility_manifest": manifests,
        "annotations_created_or_accessed": 0,
        "generation_calls": 0,
        "network_calls": 0,
        "paid_calls": 0,
        "claim_boundary": (
            "Source-only prospective developer data, authored after B31/B32 and therefore not a "
            "formal or temporal holdout. No outputs, annotations, preferences, or quality results exist."
        ),
        "validation_sha256": canonical_sha256({"checks": checks, "manifest": manifests}),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--parent-source", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = Path(args.output)
    if output.exists():
        return 2
    try:
        payload = validate_source(args.source, args.parent_source)
    except P3ContractError as exc:
        payload = {
            "schema": "uruha_p3_prospective_source_freeze_refusal_v1",
            "phase": "P3-B33",
            "status": "prospective_source_only_refused",
            "contract_code": exc.code,
            "generation_calls": 0,
            "network_calls": 0,
            "claim_boundary": "No source freeze or quality claim is authorized.",
        }
    write_new_json(output, payload)
    return 0 if payload.get("status") == "prospective_source_only_ready_to_freeze" else 1


if __name__ == "__main__":
    raise SystemExit(main())
