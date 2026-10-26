"""Opt-in, fail-closed pre-send admission for the single P4 B M21 attempt.

This is a mechanical gate, not a tokenizer oracle or a Web deadline. Production
has no verified Ollama 0.34.4 prompt bound wired yet, so it must not enable a
real B Send on the strength of this module alone.
"""

from __future__ import annotations

import threading
import math
from copy import deepcopy


class P4BResourceGateError(RuntimeError):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


class P4BResourceGate:
    """Authorize at most one exact M21 request before any model invocation.

    ``prompt_token_upper_bound`` is deliberately absent by default. Its future
    production binding must prove the *transformed* request's actual Ollama
    prompt-token upper bound and model/template identity. A test callback alone
    is not such proof.
    """

    def __init__(self, *, prompt_token_upper_bound=None):
        self._prompt_token_upper_bound = prompt_token_upper_bound
        self._lock = threading.Lock()
        self._attempted_provider_calls = 0
        self._denied_attempt_count = 0
        self._terminal_reason = ""
        self._admitted_prompt_upper_bound = None
        self._actual_total_tokens = None

    def _deny(self, reason):
        self._denied_attempt_count += 1
        if not self._terminal_reason:
            self._terminal_reason = reason
        raise P4BResourceGateError(reason)

    def admit_openai(self, stage, request):
        """Run on the inner ledger proxy, after P2 compact request rewriting."""
        from uruha_compact_planner_p2 import _REQUIRED_JSON_SCHEMA_FORMAT

        with self._lock:
            if self._terminal_reason:
                self._denied_attempt_count += 1
                raise P4BResourceGateError(self._terminal_reason)
            if self._attempted_provider_calls:
                self._deny("extra_generation_attempt")
            if stage != "leftbrain_general_plan":
                self._deny("unexpected_generation_stage")
            messages = request.get("messages") if isinstance(request, dict) else None
            if (
                not isinstance(request, dict)
                or set(request) != {
                    "model", "messages", "temperature", "timeout",
                    "max_tokens", "response_format",
                }
                or request.get("model") != "qwen2.5:7b"
                or request.get("temperature") != 0.1
                or type(request.get("timeout")) not in (int, float)
                or not math.isfinite(request["timeout"])
                or request["timeout"] != 20.0
                or type(request.get("max_tokens")) is not int
                or request.get("max_tokens") != 256
                or request.get("response_format") != _REQUIRED_JSON_SCHEMA_FORMAT
                or not isinstance(messages, list)
                or len(messages) != 2
                or any(not isinstance(message, dict) or set(message) != {"role", "content"}
                       for message in messages)
                or messages[0].get("role") != "system"
                or messages[1].get("role") != "user"
                or not isinstance(messages[0].get("content"), str)
                or not messages[0]["content"].startswith(
                    "You are the Left Brain Planner for a dual-brain character system."
                )
                or not isinstance(messages[1].get("content"), str)
                or not messages[1]["content"].startswith("User Input: ")
            ):
                self._deny("m21_request_drift")
            counter = self._prompt_token_upper_bound
            if not callable(counter):
                self._deny("prompt_upper_bound_unavailable")
            try:
                # A caller-supplied counter must not be able to rewrite the
                # exact transformed request that the inner proxy will send.
                bound = counter(deepcopy(request))
            except Exception:
                self._deny("prompt_upper_bound_unavailable")
            if type(bound) is not int or bound < 0:
                self._deny("prompt_upper_bound_unavailable")
            if bound + 256 > 2000:
                self._deny("token_budget_exceeded")
            self._attempted_provider_calls = 1
            self._admitted_prompt_upper_bound = bound

    def deny_other_generation(self, backend):
        """Native Ollama and local RightBrain have no B allowlist entry."""
        with self._lock:
            self._deny("unexpected_generation_backend")

    def record_pre_provider_revalidation_failure(self):
        """Close a reserved admission that failed identity before SDK create.

        No provider call occurred, so actual usage must remain unknown. This
        diagnostic terminal is deliberately not a durable Web turn receipt.
        """
        with self._lock:
            if (self._attempted_provider_calls == 1
                    and self._admitted_prompt_upper_bound is not None
                    and self._actual_total_tokens is None
                    and not self._terminal_reason):
                self._terminal_reason = "pre_provider_revalidation_failed"

    def observe_openai_result(self, response, error):
        """Post-call usage audit; it does not retroactively guarantee a hard cap."""
        with self._lock:
            if error is not None:
                if not self._terminal_reason:
                    self._terminal_reason = "provider_error_or_missing_usage"
                return
            usage = getattr(response, "usage", None)
            prompt = getattr(usage, "prompt_tokens", None)
            completion = getattr(usage, "completion_tokens", None)
            total = getattr(usage, "total_tokens", None)
            if (
                type(prompt) is not int or prompt < 0
                or type(completion) is not int or completion < 0
                or type(total) is not int or total != prompt + completion
            ):
                if not self._terminal_reason:
                    self._terminal_reason = "missing_provider_usage"
                return
            self._actual_total_tokens = total
            if not self._terminal_reason:
                if prompt > self._admitted_prompt_upper_bound:
                    self._terminal_reason = "actual_prompt_exceeded_upper_bound"
                elif completion > 256:
                    self._terminal_reason = "actual_completion_exceeded_output_cap"
                elif total > 2000:
                    self._terminal_reason = "actual_token_budget_exceeded"

    def require_nonterminal_result(self):
        """Reject an audited B response whose result is terminal.

        Called only after the physical SDK call and ledger audit complete; it
        cannot retroactively prevent that call or establish a hard token cap.
        """
        with self._lock:
            if self._terminal_reason:
                raise P4BResourceGateError(self._terminal_reason)

    def snapshot(self):
        """Raw-free local diagnostic state; not a B authorization receipt."""
        with self._lock:
            return {
                "schema": "uruha_p4_b_resource_gate_mechanical_v1",
                "attempted_provider_calls": self._attempted_provider_calls,
                "denied_attempt_count": self._denied_attempt_count,
                "admitted_prompt_upper_bound": self._admitted_prompt_upper_bound,
                "actual_total_tokens": self._actual_total_tokens,
                "terminal_reason": self._terminal_reason,
                "contains_raw_prompt_or_reply": False,
            }
