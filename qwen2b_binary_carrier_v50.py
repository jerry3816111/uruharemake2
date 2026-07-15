#!/usr/bin/env python3
"""Strict carrier prompts and parsers for the V50 Qwen2B format probe."""

import json


DECISIONS = ("execute", "do_not_execute")


def carrier_instruction(config, carrier):
    definition = config["carriers"][carrier]
    return (
        definition["instruction"]
        + "\nExact carrier schema:\n"
        + json.dumps(definition["schema"], ensure_ascii=False, sort_keys=True)
    )


def parse_carrier_response(config, carrier, response):
    message = (response or {}).get("message") or {}
    content = message.get("content")
    tool_calls = message.get("tool_calls") or []
    errors = []
    unexpected_content = bool(tool_calls)
    if tool_calls:
        errors.append("unexpected_tool_call")
    try:
        payload = json.loads(content) if isinstance(content, str) else None
    except json.JSONDecodeError:
        payload = None
        errors.append("invalid_json")

    decision = None
    result_count = 0
    if carrier == "scalar_enum_candidate":
        result_count = int(payload is not None)
        decision = payload
    elif carrier == "boolean_two_field_control":
        result_count = int(isinstance(payload, dict))
        if not isinstance(payload, dict):
            errors.append("root_not_object")
        else:
            if set(payload) != {"execute_now", "contract_ack"}:
                errors.append("root_fields_mismatch")
            if payload.get("contract_ack") != "v50":
                errors.append("contract_ack_mismatch")
            execute_now = payload.get("execute_now")
            if type(execute_now) is not bool:
                errors.append("execute_now_not_boolean")
            else:
                decision = "execute" if execute_now else "do_not_execute"
    elif carrier == "enum_two_field_candidate":
        result_count = int(isinstance(payload, dict))
        if not isinstance(payload, dict):
            errors.append("root_not_object")
        else:
            if set(payload) != {"decision", "contract_ack"}:
                errors.append("root_fields_mismatch")
            if payload.get("contract_ack") != "v50":
                errors.append("contract_ack_mismatch")
            decision = payload.get("decision")
    elif carrier == "enum_single_field_candidate":
        result_count = int(isinstance(payload, dict))
        if not isinstance(payload, dict):
            errors.append("root_not_object")
        else:
            if set(payload) != {"decision"}:
                errors.append("root_fields_mismatch")
            decision = payload.get("decision")
    else:
        raise ValueError(f"Unknown V50 carrier: {carrier}")

    if not isinstance(decision, str) or decision not in DECISIONS:
        errors.append("invalid_decision")
    errors = list(dict.fromkeys(errors))
    return {
        "parse_success": not errors,
        "errors": errors,
        "decision": decision,
        "result_count": result_count,
        "single_result": result_count == 1,
        "unexpected_content": unexpected_content,
    }
