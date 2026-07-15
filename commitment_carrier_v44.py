#!/usr/bin/env python3
"""Strict carrier schemas and parsers for the V44 format probe."""

import json

from action_selective_deliberation_v37 import COMMITMENTS


CARRIERS = (
    "scalar_enum_schema",
    "two_field_object_schema",
    "nested_label_schema",
    "tool_call_schema",
)

SCHEMAS = {
    "scalar_enum_schema": {
        "type": "string",
        "enum": sorted(COMMITMENTS),
    },
    "two_field_object_schema": {
        "type": "object",
        "properties": {
            "commitment": {"type": "string", "enum": sorted(COMMITMENTS)},
            "contract_ack": {"type": "string", "enum": ["v44"]},
        },
        "required": ["commitment", "contract_ack"],
        "additionalProperties": False,
    },
    "nested_label_schema": {
        "type": "object",
        "properties": {
            "classification": {
                "type": "object",
                "properties": {
                    "commitment": {
                        "type": "string",
                        "enum": sorted(COMMITMENTS),
                    }
                },
                "required": ["commitment"],
                "additionalProperties": False,
            }
        },
        "required": ["classification"],
        "additionalProperties": False,
    },
}

TOOL = {
    "type": "function",
    "function": {
        "name": "record_commitment",
        "description": "Record one internal pragmatic commitment label. This never executes a VRM action.",
        "parameters": {
            "type": "object",
            "properties": {
                "commitment": {
                    "type": "string",
                    "enum": sorted(COMMITMENTS),
                }
            },
            "required": ["commitment"],
            "additionalProperties": False,
        },
    },
}


def carrier_instruction(carrier):
    if carrier == "tool_call_schema":
        contract = TOOL
        action = (
            "Call record_commitment exactly once with source_label as its commitment "
            "argument. Return no explanatory content."
        )
    else:
        contract = SCHEMAS[carrier]
        action = (
            "Copy source_label into the exact JSON carrier below. Return only that "
            "JSON value and no explanation or Markdown."
        )
    return (
        "This is a non-semantic transport-format probe. Do not interpret the label. "
        f"{action}\nExact carrier schema:\n"
        + json.dumps(contract, ensure_ascii=False, sort_keys=True)
    )


def _valid_label(value):
    return isinstance(value, str) and value in COMMITMENTS


def parse_carrier_response(carrier, response):
    message = (response or {}).get("message") or {}
    content = str(message.get("content") or "").strip()
    tool_calls = message.get("tool_calls") or []
    errors = []
    commitment = None
    result_count = 0
    unexpected_content = False

    if carrier == "tool_call_schema":
        result_count = len(tool_calls)
        if result_count != 1:
            errors.append("tool_call_count_mismatch")
        if content:
            unexpected_content = True
            errors.append("unexpected_content")
        if result_count == 1:
            function = tool_calls[0].get("function") or {}
            if function.get("name") != "record_commitment":
                errors.append("tool_name_mismatch")
            arguments = function.get("arguments")
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except json.JSONDecodeError:
                    arguments = None
            if not isinstance(arguments, dict):
                errors.append("tool_arguments_not_object")
            else:
                if set(arguments) != {"commitment"}:
                    errors.append("tool_argument_fields_mismatch")
                commitment = arguments.get("commitment")
        if not _valid_label(commitment):
            errors.append("invalid_commitment")
    else:
        if tool_calls:
            unexpected_content = True
            errors.append("unexpected_tool_call")
        try:
            payload = json.loads(content)
        except (TypeError, json.JSONDecodeError):
            payload = None
            errors.append("invalid_json")
        if carrier == "scalar_enum_schema":
            result_count = 1 if payload is not None else 0
            commitment = payload
        elif carrier == "two_field_object_schema":
            result_count = 1 if isinstance(payload, dict) else 0
            if not isinstance(payload, dict):
                errors.append("root_not_object")
            else:
                if set(payload) != {"commitment", "contract_ack"}:
                    errors.append("root_fields_mismatch")
                if payload.get("contract_ack") != "v44":
                    errors.append("contract_ack_mismatch")
                commitment = payload.get("commitment")
        elif carrier == "nested_label_schema":
            result_count = 1 if isinstance(payload, dict) else 0
            if not isinstance(payload, dict):
                errors.append("root_not_object")
            else:
                if set(payload) != {"classification"}:
                    errors.append("root_fields_mismatch")
                classification = payload.get("classification")
                if not isinstance(classification, dict):
                    errors.append("classification_not_object")
                else:
                    if set(classification) != {"commitment"}:
                        errors.append("classification_fields_mismatch")
                    commitment = classification.get("commitment")
        else:
            raise ValueError(f"Unknown V44 carrier: {carrier}")
        if not _valid_label(commitment):
            errors.append("invalid_commitment")

    errors = list(dict.fromkeys(errors))
    return {
        "parse_success": not errors,
        "errors": errors,
        "commitment": commitment,
        "result_count": result_count,
        "single_result": result_count == 1,
        "unexpected_content": unexpected_content,
    }
