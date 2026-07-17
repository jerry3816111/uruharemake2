"""Frozen local model adapter for the support-attributed runtime pilot."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request

from consolidation_support_attribution_v1_core import (
    parse_support_tool_response,
)


def _post_json(url, body, timeout):
    request = urllib.request.Request(
        url,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def _tool_contract(config):
    contract = config["fixed_support_contract"]
    valid_indices = contract["valid_indices"]
    return {
        "type": "function",
        "function": {
            "name": contract["tool_name"],
            "description": (
                "Return only source event indices that explicitly support "
                "the already-generated derived memory."
            ),
            "parameters": {
                "type": "object",
                "additionalProperties": False,
                "required": [contract["only_argument"]],
                "properties": {
                    contract["only_argument"]: {
                        "type": "array",
                        "description": (
                            "Unique chronological event numbers whose User "
                            "text explicitly supports the complete derived "
                            "memory; empty when unsupported."
                        ),
                        "items": {
                            "type": "integer",
                            "enum": valid_indices,
                        },
                        "uniqueItems": True,
                        "maxItems": len(valid_indices),
                    }
                },
            },
        },
    }


def _render_request(config, memory_kind, derived_memory, source_events):
    contract = config["fixed_support_contract"]
    lines = [
        f"Derived memory ({memory_kind}):",
        derived_memory,
        "",
        "Chronological source events:",
    ]
    template = contract["event_rendering"]
    for event in source_events:
        lines.append(
            template.format(
                index=event["index"],
                user=event["user"],
                assistant=event["assistant"],
            )
        )
    generation = config["generation"]
    return {
        "model": config["model"]["ollama_tag"],
        "messages": [
            {
                "role": "system",
                "content": contract["system_prompt"],
            },
            {
                "role": "user",
                "content": "\n".join(lines),
            },
        ],
        "tools": [_tool_contract(config)],
        "stream": False,
        "think": generation["thinking"],
        "keep_alive": generation["keep_alive"],
        "options": {
            "temperature": generation["temperature"],
            "top_p": generation["top_p"],
            "seed": generation["seed"],
            "num_ctx": generation["context_tokens"],
            "num_predict": generation["maximum_output_tokens"],
        },
    }


class FrozenRuntimeSupportAttributor:
    def __init__(self, config, model_snapshot):
        self.config = config
        self.model_snapshot = model_snapshot
        self.calls = []

    def attribute(
        self,
        *,
        case_id,
        memory_kind,
        derived_memory,
        source_events,
    ):
        if self.config["generation"]["transport_attempts"] != 1:
            raise ValueError("formal pilot forbids transport retries")
        body = _render_request(
            self.config,
            memory_kind,
            derived_memory,
            source_events,
        )
        started = time.perf_counter()
        response = None
        transport_error = None
        try:
            response = _post_json(
                self.config["local_runtime"]["endpoint"],
                body,
                self.config["generation"]["timeout_seconds"],
            )
            parsed = parse_support_tool_response(response)
        except (
            OSError,
            TimeoutError,
            urllib.error.URLError,
            json.JSONDecodeError,
        ) as exc:
            transport_error = f"{type(exc).__name__}: {exc}"
            parsed = parse_support_tool_response(
                {"message": {"content": "", "tool_calls": []}}
            )
        wall_seconds = round(time.perf_counter() - started, 6)
        call = {
            "case_id": case_id,
            "memory_kind": memory_kind,
            "condition": "support_attributed_runtime_candidate",
            **parsed,
            "wall_seconds": wall_seconds,
            "transport_attempts": 1,
            "transport_error": transport_error,
            "model_visible_request": body,
            "response": response,
        }
        self.calls.append(call)
        return {
            **parsed,
            "wall_seconds": wall_seconds,
            "transport_error": transport_error,
            "model_digest": self.model_snapshot["digest"],
            "contract_version": self.config[
                "fixed_support_contract"
            ]["version"],
        }
