#!/usr/bin/env python3
"""Probe local Ollama support for a conditional JSON Schema contract."""

import argparse
import json
import time
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DEFAULT_OUTPUT = ROOT / "reports" / "ollama_schema_compatibility_v40.json"
MODEL = "qwen3.5:4b"
EXPECTED_DIGEST = "2a654d98e6fba55d452b7043684e9b57a947e393bbffa62485a7aac05ee4eefd"

ONE_OF_SCHEMA = {
    "type": "object",
    "oneOf": [
        {
            "type": "object",
            "properties": {
                "kind": {"const": "cat"},
                "has_whiskers": {"type": "boolean"},
            },
            "required": ["kind", "has_whiskers"],
            "additionalProperties": False,
        },
        {
            "type": "object",
            "properties": {
                "kind": {"const": "dog"},
                "bark_volume": {"type": "integer", "minimum": 0, "maximum": 10},
            },
            "required": ["kind", "bark_volume"],
            "additionalProperties": False,
        },
    ],
}


def _request_json(url, payload=None):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="GET" if data is None else "POST",
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.load(response)


def _model_digest():
    payload = _request_json("http://127.0.0.1:11434/api/tags")
    models = {row["name"]: row for row in payload.get("models") or []}
    if MODEL not in models:
        raise RuntimeError(f"Missing Ollama model: {MODEL}")
    return models[MODEL].get("digest")


def _validate_expected_cat(payload):
    return (
        isinstance(payload, dict)
        and set(payload) == {"kind", "has_whiskers"}
        and payload.get("kind") == "cat"
        and payload.get("has_whiskers") is True
    )


def run_probe():
    digest = _model_digest()
    if digest != EXPECTED_DIGEST:
        raise RuntimeError("Ollama model digest changed")
    body = {
        "model": MODEL,
        "stream": False,
        "think": False,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Convert the observation to exactly one JSON object. "
                    "Do not add prose or Markdown."
                ),
            },
            {
                "role": "user",
                "content": "The observed animal is a cat and it has whiskers.",
            },
        ],
        "format": ONE_OF_SCHEMA,
        "options": {
            "temperature": 0.0,
            "top_p": 1.0,
            "seed": 20260740,
            "num_ctx": 2048,
            "num_predict": 128,
        },
    }
    started = time.monotonic()
    response = _request_json("http://127.0.0.1:11434/api/chat", body)
    elapsed = time.monotonic() - started
    raw = str((response.get("message") or {}).get("content") or "").strip()
    try:
        parsed = json.loads(raw)
        json_parse_success = True
    except json.JSONDecodeError:
        parsed = None
        json_parse_success = False
    return {
        "schema": "uruha_ollama_schema_compatibility_probe_v40",
        "scope": "infrastructure_only_unrelated_to_project_evaluation_data",
        "model": MODEL,
        "model_digest": digest,
        "schema_feature": "oneOf_with_const_and_branch_specific_required_fields",
        "request_schema": ONE_OF_SCHEMA,
        "raw_reply": raw,
        "parsed_reply": parsed,
        "json_parse_success": json_parse_success,
        "conditional_schema_obeyed": _validate_expected_cat(parsed),
        "elapsed_seconds": round(elapsed, 4),
        "conclusion": (
            "oneOf_supported_for_v40"
            if _validate_expected_cat(parsed)
            else "oneOf_not_reliable_for_v40_use_simple_schema"
        ),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = run_probe()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "conditional_schema_obeyed": report["conditional_schema_obeyed"],
        "conclusion": report["conclusion"],
    }, indent=2))


if __name__ == "__main__":
    main()
