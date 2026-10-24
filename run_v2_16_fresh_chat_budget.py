#!/usr/bin/env python3
"""Reproducible runtime adapter for the frozen V2.16 harness.

The frozen harness pads the user message to the full 2,048-token ceiling while
Ollama reports the complete chat request, including its fixed system/template
overhead.  This adapter reserves a condition-independent 256 tokens for that
wrapper.  Semantic prompts, cases, equation weights, model settings, scoring,
and the frozen artifact hashes remain unchanged.  Ollama's own preflight still
enforces the final real-token ceiling and paired-token gate.
"""

from __future__ import annotations

import json
from copy import deepcopy

import desired_response_comparison_v2_16 as comparison


CHAT_WRAPPER_TOKEN_RESERVE = 256


class ChatBudgetTokenizer:
    """Count the model tokenizer plus a fixed chat-wrapper reserve."""

    def __init__(self, base_tokenizer, reserve=CHAT_WRAPPER_TOKEN_RESERVE):
        self.base_tokenizer = base_tokenizer
        self.reserve = int(reserve)

    def encode(self, text, add_special_tokens=False):
        token_ids = list(
            self.base_tokenizer.encode(
                str(text or ""),
                add_special_tokens=add_special_tokens,
            )
        )
        return ([-1] * self.reserve) + token_ids


def main():
    if comparison.RAW_PATH.exists():
        raise SystemExit("raw result already exists; refusing to overwrite frozen generation")
    lock_result = comparison.validate_lock()
    if not lock_result["passed"]:
        raise SystemExit(json.dumps(lock_result, ensure_ascii=False, indent=2))

    bundle = comparison.load_case_bundle()
    prereg = comparison.load_json(comparison.PREREG_PATH)
    design = comparison.validate_design(bundle, prereg)
    if not design["passed"]:
        raise SystemExit(json.dumps(design, ensure_ascii=False, indent=2))

    tokenizer = ChatBudgetTokenizer(comparison.load_local_tokenizer())
    rows = comparison.run_fresh(bundle, prereg, tokenizer=tokenizer)
    summary = comparison.summarize(rows, prereg)
    raw = {
        "schema": "uruha_v2_16_reference_person_equation_fresh_result",
        "status": "fresh_generation_complete_human_ratings_pending",
        "inputs": {
            "cases": comparison.relative_binding(comparison.CASE_PATH),
            "preregistration": comparison.relative_binding(comparison.PREREG_PATH),
            "lock": comparison.relative_binding(comparison.LOCK_PATH),
            "model": deepcopy(prereg["model"]),
            "runtime_adapter": comparison.relative_binding(__file__),
            "chat_wrapper_token_reserve": CHAT_WRAPPER_TOKEN_RESERVE,
        },
        "summary": summary,
        "rows": rows,
        "claims": {
            "deterministic_equation_supported": True,
            "narrow_proxy_supported": bool(summary["preregistered_proxy_success"]),
            "human_preference_supported": False,
            "system_better_than_llm": False,
            "reference_person_equals_real_person": False,
        },
        "runtime_note": (
            "The frozen harness initially failed before scored generation because "
            "Ollama counts fixed chat-wrapper tokens beyond the locally padded user "
            "message. This condition-independent reserve changes no semantic prompt; "
            "Ollama preflight remains the final token-parity authority."
        ),
    }
    comparison.RAW_PATH.write_text(
        json.dumps(raw, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    packet, key = comparison.build_blind_packet(rows)
    comparison.BLIND_PACKET_PATH.write_text(
        json.dumps(packet, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    comparison.BLIND_KEY_PATH.write_text(
        json.dumps(key, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
