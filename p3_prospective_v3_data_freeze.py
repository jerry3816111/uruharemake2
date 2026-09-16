#!/usr/bin/env python3
"""Validate and freeze prospective v3 source/rubric before generation."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import unicodedata
from typing import Any

from p3_product_comparison import write_new_json


SOURCE_SCHEMA = "uruha_p3_prospective_developer_source_v3"
ANNOTATION_SCHEMA = "uruha_p3_prospective_developer_annotations_v3"
PRODUCT_COMMIT = "0cab07b44aa47adb3866a9ba1aa317b71a5d3091"
FORBIDDEN_SOURCE_KEYS = {"reply", "output", "answer", "score", "winner", "gold", "rubric", "annotation"}
FORBIDDEN_ANNOTATION_KEYS = {"target_reply", "model_output", "condition_winner"}


class FreezeError(ValueError):
    pass


def _read(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _hash(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _normalize(text: str) -> str:
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", str(text or "")).lower())


def _walk_keys(value: Any) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        keys.update(str(key).lower() for key in value)
        for child in value.values(): keys.update(_walk_keys(child))
    elif isinstance(value, list):
        for child in value: keys.update(_walk_keys(child))
    return keys


def build_validation(source_path: str | Path, annotation_path: str | Path, repo: str | Path = ".") -> dict[str, Any]:
    repo_path = Path(repo).resolve()
    source, annotations = _read(source_path), _read(annotation_path)
    source_hash, annotation_hash = _hash(source_path), _hash(annotation_path)
    if source.get("schema") != SOURCE_SCHEMA or annotations.get("schema") != ANNOTATION_SCHEMA:
        raise FreezeError("schema_mismatch")
    if annotations.get("source_manifest_sha256") != source_hash:
        raise FreezeError("annotation_source_hash_mismatch")
    if source.get("product_snapshot") != {
        "commit": PRODUCT_COMMIT,
        "frozen_before_source_generation": True,
        "post_source_product_tuning_allowed_before_first_run": False,
    }:
        raise FreezeError("product_snapshot_mismatch")
    cases = source.get("cases")
    annotation_cases = annotations.get("cases")
    if not isinstance(cases, list) or len(cases) != 3 or source.get("case_count") != 3 or source.get("turns_per_case") != 4:
        raise FreezeError("source_case_shape_invalid")
    if not isinstance(annotation_cases, list) or len(annotation_cases) != 3:
        raise FreezeError("annotation_case_shape_invalid")
    if _walk_keys(source) & FORBIDDEN_SOURCE_KEYS:
        raise FreezeError("source_contains_label_or_output_key")
    if _walk_keys(annotations) & FORBIDDEN_ANNOTATION_KEYS:
        raise FreezeError("annotation_contains_target_output")
    if source.get("annotations_included") is not False or source.get("generation_executed") is not False:
        raise FreezeError("source_access_boundary_invalid")
    if annotations.get("generation_prompt_access") is not False or annotations.get("generation_visibility") != "forbidden_until_all_condition_outputs_are_immutably_locked":
        raise FreezeError("annotation_access_boundary_invalid")
    languages = [case.get("language") for case in cases]
    if languages != ["zh", "en", "ja"]:
        raise FreezeError("language_order_invalid")

    prior_texts: set[str] = set()
    for relative in (
        "datasets/p3_developer_smoke_source_v1.json",
        "datasets/p3_prospective_developer_source_v2.json",
    ):
        prior = _read(repo_path / relative)
        for case in prior.get("cases", []):
            for turn in case.get("turns", []):
                prior_texts.add(_normalize(turn.get("content", "")))
    annotation_by_case = {case["case_id"]: case for case in annotation_cases}
    visibility = []
    all_turn_ids: list[str] = []
    overlap_count = 0
    for case in cases:
        turns = case.get("turns")
        sessions = case.get("sessions")
        if not isinstance(turns, list) or len(turns) != 4 or not isinstance(sessions, list) or len(sessions) != 2:
            raise FreezeError("case_turn_or_session_shape_invalid")
        if len({turn["turn_id"] for turn in turns}) != 4 or len({turn["session_id"] for turn in turns}) != 2:
            raise FreezeError("case_identity_duplicate")
        for turn in turns:
            if hashlib.sha256(turn["content"].encode("utf-8")).hexdigest() != turn["content_sha256"]:
                raise FreezeError("turn_content_hash_mismatch")
            all_turn_ids.append(turn["turn_id"])
            overlap_count += int(_normalize(turn["content"]) in prior_texts)
        annotation = annotation_by_case.get(case["case_id"])
        if not annotation or len(annotation.get("turns", [])) != 4:
            raise FreezeError("annotation_turns_missing")
        ann_by_turn = {row["turn_id"]: row for row in annotation["turns"]}
        for index, turn in enumerate(turns):
            row = ann_by_turn.get(turn["turn_id"])
            required = {"turn_id", "evidence_turn_ids", "required_semantic_acts", "acceptable_alternatives", "forbidden_semantic_acts", "uncertainty_boundary"}
            if not row or set(row) != required:
                raise FreezeError("annotation_turn_contract_invalid")
            visible_ids = [item["turn_id"] for item in turns[:index + 1]]
            if not row["required_semantic_acts"] or not row["forbidden_semantic_acts"] or not set(row["evidence_turn_ids"]).issubset(visible_ids):
                raise FreezeError("annotation_evidence_or_act_invalid")
            visibility.append({
                "case_id": case["case_id"], "turn_id": turn["turn_id"],
                "visible_turn_ids": visible_ids,
                "locked_future_turn_ids": [item["turn_id"] for item in turns[index + 1:]],
                "annotation_visible_to_generation": False,
            })
    scoring = annotations.get("scoring_contract") or {}
    expected_dimensions = [
        "required_semantic_acts_present", "forbidden_semantic_acts_absent",
        "source_grounding_correct", "uncertainty_boundary_respected", "natural_japanese_surface",
    ]
    if scoring.get("dimensions") != expected_dimensions or scoring.get("dimension_values") != [0, 1] or scoring.get("case_primary_turn") != "u4":
        raise FreezeError("scoring_contract_invalid")
    checks = {
        "source_and_annotation_schemas_valid": True,
        "source_hash_bound_by_annotation": True,
        "product_snapshot_frozen_before_cases": True,
        "three_cases_four_turns_each": len(all_turn_ids) == 12,
        "languages_exactly_zh_en_ja": languages == ["zh", "en", "ja"],
        "source_contains_no_labels_outputs_or_scores": True,
        "annotation_contains_no_target_reply_or_winner": True,
        "all_turn_hashes_valid": True,
        "all_twelve_rubrics_predeclared": sum(len(case["turns"]) for case in annotation_cases) == 12,
        "annotation_evidence_never_uses_future_turn": True,
        "annotation_hidden_from_generation": True,
        "exact_normalized_overlap_with_b2_b33_is_zero": overlap_count == 0,
        "no_generation_executed": True,
    }
    return {
        "schema": "uruha_p3_prospective_v3_data_freeze_validation_v1",
        "phase": "P3-B44", "status": "prospective_v3_data_ready_to_freeze" if all(checks.values()) else "prospective_v3_data_not_ready",
        "source": {"path": str(source_path), "sha256": source_hash},
        "annotations": {"path": str(annotation_path), "sha256": annotation_hash},
        "product_snapshot_commit": PRODUCT_COMMIT, "checks": checks,
        "case_ids": [case["case_id"] for case in cases], "turn_ids": all_turn_ids,
        "turn_visibility_manifest": visibility, "normalized_prior_overlap_count": overlap_count,
        "real_model_calls": 0, "network_calls": 0, "paid_calls": 0,
        "annotations_read_by_validator": 1, "annotations_exposed_to_generation": 0,
        "claim_boundary": "Data and rubric validation before generation; same-project developer cases, not formal temporal holdout or human preference evidence.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True); parser.add_argument("--annotations", required=True)
    parser.add_argument("--output", required=True); parser.add_argument("--repo", default=".")
    args = parser.parse_args(); output = Path(args.output)
    if output.exists(): return 2
    try: payload = build_validation(args.source, args.annotations, args.repo)
    except FreezeError as exc:
        payload = {"schema": "uruha_p3_prospective_v3_data_freeze_refusal_v1", "phase": "P3-B44", "status": "prospective_v3_data_refused", "contract_code": str(exc), "real_model_calls": 0, "network_calls": 0}
    write_new_json(output, payload)
    return 0 if payload.get("status") == "prospective_v3_data_ready_to_freeze" else 1


if __name__ == "__main__": raise SystemExit(main())

