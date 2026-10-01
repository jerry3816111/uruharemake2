#!/usr/bin/env python3
"""Prospective P3 native-judge contract with slot-bound exact reply evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

from p3_case03_proxy_grade import SCORE_KEYS, build_messages, validate_judgment
from p3_product_comparison import P3ContractError, canonical_sha256, write_new_json


SCHEMA = "uruha_p3_exact_evidence_judge_contract_v1"


def _score_schema(item: Mapping[str, Any], slot: str) -> dict[str, Any]:
    correction = (
        {"type": "integer", "enum": [0, 1, 2]}
        if item["annotation"]["correction_eligible"]
        else {"type": "null"}
    )
    return {
        "type": "object",
        "additionalProperties": False,
        "required": sorted(SCORE_KEYS),
        "properties": {
            "reply_slot": {"type": "string", "enum": [slot]},
            "attunement": {"type": "integer", "enum": [0, 1, 2]},
            "grounding": {"type": "integer", "enum": [0, 1, 2]},
            "correction": correction,
            "continuity": {"type": "integer", "enum": [0, 1, 2]},
            "unsupported_assertion": {"type": "boolean"},
            "japanese_issue": {"type": "boolean"},
            "identity_issue": {"type": "boolean"},
            "evidence_turn_ids": {
                "type": "array",
                "minItems": 1,
                "items": {"type": "string", "enum": item["currently_visible_turn_ids"]},
            },
            "reply_quote": {"type": "string", "enum": [item["anonymous_replies"][slot]]},
        },
    }


def judgment_schema(item: Mapping[str, Any]) -> dict[str, Any]:
    """Use simple keyed objects and one-value enums; avoid unreliable oneOf branches."""

    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["scores", "preference"],
        "properties": {
            "scores": {
                "type": "object",
                "additionalProperties": False,
                "required": ["A", "B"],
                "properties": {
                    "A": _score_schema(item, "A"),
                    "B": _score_schema(item, "B"),
                },
            },
            "preference": {"type": "string", "enum": ["A", "B", "tie"]},
        },
    }


def build_exact_evidence_messages(item: Mapping[str, Any]) -> list[dict[str, str]]:
    messages = build_messages(item)
    system = messages[0]["content"].replace(
        "reply_quote must be a non-empty exact substring of that reply.",
        "reply_quote must copy that slot's entire anonymous reply exactly; do not shorten or paraphrase it.",
    )
    payload = json.loads(messages[1]["content"])
    payload["required_schema"]["scores"] = {
        "A": {
            "reply_slot": "A",
            "reply_quote": "entire_reply_A_exactly",
            "other_fields": "same_frozen_rubric_fields",
        },
        "B": {
            "reply_slot": "B",
            "reply_quote": "entire_reply_B_exactly",
            "other_fields": "same_frozen_rubric_fields",
        },
    }
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
    ]


def validate_exact_evidence_judgment(raw_text: str, item: Mapping[str, Any]) -> dict[str, Any]:
    try:
        value = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise P3ContractError("p3_b30_judge_json_invalid") from exc
    if not isinstance(value, Mapping) or set(value) != {"scores", "preference"}:
        raise P3ContractError("p3_b30_judge_schema_invalid")
    scores = value["scores"]
    if not isinstance(scores, Mapping) or set(scores) != {"A", "B"}:
        raise P3ContractError("p3_b30_scores_invalid")
    normalized = []
    for slot in ("A", "B"):
        score = scores[slot]
        if not isinstance(score, Mapping) or set(score) != SCORE_KEYS:
            raise P3ContractError("p3_b30_score_schema_invalid", slot)
        if score.get("reply_slot") != slot:
            raise P3ContractError("p3_b30_slot_binding_invalid", slot)
        if score.get("reply_quote") != item["anonymous_replies"][slot]:
            raise P3ContractError("p3_b30_exact_reply_evidence_invalid", slot)
        normalized.append(dict(score))
    return validate_judgment(
        json.dumps({"scores": normalized, "preference": value["preference"]}, ensure_ascii=False),
        item,
    )


def native_body(config: Mapping[str, Any], item: Mapping[str, Any]) -> dict[str, Any]:
    judge = config["judge"]
    return {
        "model": judge["model"],
        "messages": build_exact_evidence_messages(item),
        "stream": False,
        "format": judgment_schema(item),
        "think": judge["think"],
        "options": {
            "temperature": judge["temperature"],
            "seed": judge["seed"],
            "top_p": judge["top_p"],
            "num_ctx": judge["num_ctx"],
            "num_predict": judge["max_completion_tokens"],
        },
    }


def _fixture(order: str) -> dict[str, Any]:
    product = "その話は置いておこう。猫のことを思って。"
    direct = "猫が箱を落としたの、想像したらちょっと笑う。"
    mapping = {"A": product, "B": direct} if order == "AB" else {"A": direct, "B": product}
    return {
        "item_id": f"prospective:{order}",
        "turn_id": "prospective-u1",
        "order": order,
        "visible_history": [],
        "current_input": "別に困ってない、ただ笑ってほしかっただけ。",
        "annotation": {"correction_eligible": True},
        "slot_to_condition": (
            {"A": "product_system", "B": "full_history_direct"}
            if order == "AB" else {"A": "full_history_direct", "B": "product_system"}
        ),
        "anonymous_replies": mapping,
        "currently_visible_turn_ids": ["prospective-u1"],
    }


def _valid(item: Mapping[str, Any]) -> dict[str, Any]:
    scores = {}
    for slot in ("A", "B"):
        scores[slot] = {
            "reply_slot": slot,
            "attunement": 2,
            "grounding": 2,
            "correction": 2,
            "continuity": 2,
            "unsupported_assertion": False,
            "japanese_issue": False,
            "identity_issue": False,
            "evidence_turn_ids": ["prospective-u1"],
            "reply_quote": item["anonymous_replies"][slot],
        }
    return {"scores": scores, "preference": "tie"}


def build_preflight() -> dict[str, Any]:
    items = [_fixture("AB"), _fixture("BA")]
    schemas = [judgment_schema(item) for item in items]
    validations = [validate_exact_evidence_judgment(json.dumps(_valid(item), ensure_ascii=False), item) for item in items]
    checks = {
        "simple_schema_avoids_oneof": all("oneOf" not in json.dumps(schema) for schema in schemas),
        "scores_are_slot_keyed": all(schema["properties"]["scores"]["required"] == ["A", "B"] for schema in schemas),
        "exact_reply_enums_swap_with_ab_ba": (
            schemas[0]["properties"]["scores"]["properties"]["A"]["properties"]["reply_quote"]["enum"]
            == schemas[1]["properties"]["scores"]["properties"]["B"]["properties"]["reply_quote"]["enum"]
        ),
        "valid_ab_ba_normalize_to_frozen_score_shape": all([score["reply_slot"] for score in value["scores"]] == ["A", "B"] for value in validations),
        "prompt_requires_entire_exact_reply": all("entire anonymous reply exactly" in build_exact_evidence_messages(item)[0]["content"] for item in items),
        "no_model_or_network_call": True,
    }
    return {
        "schema": "uruha_p3_exact_evidence_judge_contract_preflight_v1",
        "phase": "P3-B30",
        "status": "ready_for_prospective_exact_evidence_freeze" if all(checks.values()) else "not_ready_for_prospective_exact_evidence_freeze",
        "checks": checks,
        "manifest": [{
            "item_id": item["item_id"],
            "schema_sha256": canonical_sha256(schema),
            "prompt_sha256": canonical_sha256(build_exact_evidence_messages(item)),
        } for item, schema in zip(items, schemas)],
        "real_model_calls": 0,
        "network_calls": 0,
        "paid_calls": 0,
        "b29_retried_or_modified": False,
        "claim_boundary": "Offline prospective contract proof only. Native-model conformance remains a future preflight gate; B29 stays inconclusive and product quality is unchanged.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = Path(args.output)
    if output.exists():
        return 2
    payload = build_preflight()
    write_new_json(output, payload)
    return 0 if payload["status"] == "ready_for_prospective_exact_evidence_freeze" else 1


if __name__ == "__main__":
    raise SystemExit(main())
