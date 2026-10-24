"""Product-only transport contract for three compact, real planner candidates.

Preserves the old model, input and Memory/Hard rules. The instrumented underlying
client records the real compact call, before expansion to the old internal schema.
No answer inventory, synthetic model response, or learning-outcome mutation.
"""
from contextvars import ContextVar
from copy import deepcopy
import hashlib
import json
import math
import os

_CALL = ContextVar("compact_general_plan_p2", default=None)
_SOURCE_EVENT_CONSTRAINT = ContextVar("source_event_candidate_prompt_p4", default=None)
_INSTALLED = False
_SCENES = {"casual", "support", "invite", "jealousy", "boundary", "refusal", "ooc_defense"}
_MODES = {"direct_answer", "direct_answer_with_hedge", "clarify_light", "premise_challenge", "reframe_large_question"}
_PLAN_FIELDS = {"scene", "core_message_jp", "response_mode"}
_SCHEMA_ARM_ENV = "URUHA_P4_COMPACT_JSON_SCHEMA"
_SOURCE_EVENT_ARM_ENV = "URUHA_P4_SOURCE_EVENT_CANDIDATE_PROMPT"
_SOURCE_EVENT_RECEIPT_SCHEMA = "uruha_source_event_candidate_formation_p4_v1"
_SOURCE_EVENT_REASONS = {
    "invalid_source", "invalid_handoff", "unsupported_source_event",
    "relation_over_budget", "source_event_verified", "source_mismatch",
}
_REQUIRED_JSON_SCHEMA_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "uruha_compact_general_plan_p2",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {"plans": {
                "type": "array", "minItems": 3, "maxItems": 3,
                "items": {
                    "type": "object",
                    "properties": {
                        "scene": {"type": "string", "enum": sorted(_SCENES)},
                        "core_message_jp": {"type": "string", "minLength": 1, "maxLength": 32},
                        "response_mode": {"type": "string", "enum": sorted(_MODES)},
                    },
                    "required": ["scene", "core_message_jp", "response_mode"],
                    "additionalProperties": False,
                },
            }},
            "required": ["plans"],
            "additionalProperties": False,
        },
    },
}
_FORMAT = '''[Output JSON schema]
Return ONLY this compact JSON, no other fields or explanation:
{"plans":[{"scene":"casual","core_message_jp":"short Japanese meaning","response_mode":"direct_answer"},
{"scene":"casual","core_message_jp":"different softer meaning","response_mode":"direct_answer"},
{"scene":"casual","core_message_jp":"different sharper meaning","response_mode":"direct_answer"}]}
Exactly three distinct candidates. Each core_message_jp is at most 32 Japanese
characters. Use the earlier rules to select the scene and response_mode. Shared
constraints are supplied by the system; do not repeat them, a scratchpad, or the
user's input. This compact schema supersedes earlier instructions to output BDI
or internal_monologue fields. Never claim to know unobserved private facts.
'''


def product_planner_budget(value="20"):
    seconds = float(value)
    if not math.isfinite(seconds) or not 1 <= seconds <= 45:
        raise ValueError("Product planner budget must be finite and between 1 and 45 seconds")
    return seconds


def compact_request(kwargs):
    messages = kwargs.get("messages") or []
    if not messages or messages[0].get("role") != "system":
        return None
    prompt = messages[0].get("content")
    if not isinstance(prompt, str) or not prompt.lstrip().startswith("You are the Left Brain Planner for a dual-brain character system."):
        return None
    marker = "[Output JSON schema]"
    if marker not in prompt:
        return None
    transformed = deepcopy(kwargs)
    transformed["messages"][0]["content"] = prompt.split(marker, 1)[0] + _FORMAT
    source_constraint = _SOURCE_EVENT_CONSTRAINT.get()
    if (
        os.environ.get(_SOURCE_EVENT_ARM_ENV) == "1"
        and isinstance(source_constraint, dict)
        and isinstance(source_constraint.get("segment"), str)
        and source_constraint["segment"]
        and isinstance(source_constraint.get("receipt"), dict)
        and (receipt := _safe_source_event_receipt(source_constraint["receipt"])) is not None
        and receipt["constraint_available"] is True
        and _source_event_context_matches_user(kwargs, receipt)
    ):
        transformed["messages"][0]["content"] += source_constraint["segment"]
    transformed["max_tokens"] = min(int(kwargs.get("max_tokens") or 256), 256)
    transformed["response_format"] = (
        deepcopy(_REQUIRED_JSON_SCHEMA_FORMAT)
        if os.environ.get(_SCHEMA_ARM_ENV) == "1"
        else {"type": "json_object"}
    )
    return transformed


def _source_event_context_matches_user(kwargs, receipt):
    messages = kwargs.get("messages") or []
    if not isinstance(messages, list) or len(messages) < 2:
        return False
    user_message = messages[-1]
    if not isinstance(user_message, dict) or user_message.get("role") != "user":
        return False
    content = user_message.get("content")
    prefix = "User Input: "
    if not isinstance(content, str) or not content.startswith(prefix):
        return False
    source = content[len(prefix):]
    return hashlib.sha256(source.encode("utf-8")).hexdigest() == receipt.get("input_sha256")


def _safe_source_event_receipt(value):
    """Project only bounded provenance metadata into audit/graph state."""
    if not isinstance(value, dict) or value.get("schema") != _SOURCE_EVENT_RECEIPT_SCHEMA:
        return None

    def safe_sha(key):
        candidate = value.get(key)
        return candidate if (
            isinstance(candidate, str) and len(candidate) == 64
            and all(char in "0123456789abcdef" for char in candidate)
        ) else None

    codepoints = value.get("relation_codepoints")
    if type(codepoints) is not int or not 0 <= codepoints <= 256:
        codepoints = None
    reason = value.get("reason")
    status = value.get("status")
    return {
        "schema": _SOURCE_EVENT_RECEIPT_SCHEMA,
        "status": status if isinstance(status, str) and status in {"abstained", "authorized", "prompt_injected"} else "abstained",
        "reason": reason if isinstance(reason, str) and reason in _SOURCE_EVENT_REASONS else "invalid_source",
        "input_sha256": safe_sha("input_sha256"),
        "event_sha256": safe_sha("event_sha256"),
        "object_sha256": safe_sha("object_sha256"),
        "action_sha256": safe_sha("action_sha256"),
        "relation_codepoints": codepoints,
        "first_time_observed": value.get("first_time_observed") if type(value.get("first_time_observed")) is bool else None,
        "constraint_available": value.get("constraint_available") is True,
        "prompt_injected": value.get("prompt_injected") is True,
        "raw_dialogue_persisted": False,
        "private_state_truth_claimed": False,
    }


def _source_event_request_receipt(original, transformed):
    if os.environ.get(_SOURCE_EVENT_ARM_ENV) != "1":
        return None
    source_constraint = _SOURCE_EVENT_CONSTRAINT.get()
    if not isinstance(source_constraint, dict) or not isinstance(source_constraint.get("receipt"), dict):
        return None
    receipt = _safe_source_event_receipt(source_constraint["receipt"])
    if receipt is None:
        return None
    segment = source_constraint.get("segment")
    injected = bool(
        isinstance(segment, str)
        and segment
        and receipt.get("constraint_available") is True
        and _source_event_context_matches_user(original, receipt)
        and transformed["messages"][0]["content"].endswith(segment)
    )
    receipt["prompt_injected"] = injected
    if injected:
        receipt["status"] = "prompt_injected"
    elif receipt.get("constraint_available") is True:
        receipt["status"] = "abstained"
        receipt["reason"] = "source_mismatch"
    return receipt


def _contract_error(message, code, *, candidate_index=None, missing_count=0, extra_count=0):
    """Attach only fixed, bounded shape metadata; never copy model text or keys."""
    error = ValueError(message)
    error.compact_failure = {"failure_code": code}
    if candidate_index is not None:
        error.compact_failure["candidate_index"] = candidate_index
    if missing_count:
        error.compact_failure["missing_field_count"] = min(missing_count, 99)
    if extra_count:
        error.compact_failure["extra_field_count"] = min(extra_count, 99)
    return error


def expand_compact_response(content, finish_reason):
    if finish_reason != "stop":
        raise _contract_error("P2 compact planner did not finish a complete response", "finish_incomplete")
    try:
        payload = json.loads(content)
    except (TypeError, ValueError) as exc:
        raise _contract_error("P2 compact planner returned invalid JSON", "json_invalid") from exc
    if not isinstance(payload, dict) or set(payload) != {"plans"}:
        raise _contract_error("P2 compact planner has an unexpected schema", "root_schema")
    plans = payload["plans"]
    if not isinstance(plans, list) or len(plans) != 3:
        raise _contract_error("P2 compact planner requires exactly three actual candidates", "candidate_count")
    for index, plan in enumerate(plans):
        if not isinstance(plan, dict):
            raise _contract_error("P2 compact candidate has unexpected fields", "candidate_not_object", candidate_index=index)
        fields = set(plan)
        if fields != _PLAN_FIELDS:
            missing, extra = len(_PLAN_FIELDS - fields), len(fields - _PLAN_FIELDS)
            code = ("candidate_missing_and_extra_fields" if missing and extra else
                    "candidate_missing_fields" if missing else "candidate_extra_fields")
            raise _contract_error("P2 compact candidate has unexpected fields", code,
                                  candidate_index=index, missing_count=missing, extra_count=extra)
        core = plan["core_message_jp"]
        if not isinstance(plan["scene"], str) or plan["scene"] not in _SCENES:
            raise _contract_error("P2 compact candidate is invalid or over budget", "scene_invalid", candidate_index=index)
        if not isinstance(plan["response_mode"], str) or plan["response_mode"] not in _MODES:
            raise _contract_error("P2 compact candidate is invalid or over budget", "mode_invalid", candidate_index=index)
        if not isinstance(core, str) or not core.strip():
            raise _contract_error("P2 compact candidate is invalid or over budget", "core_invalid", candidate_index=index)
        if len(core) > 32:
            raise _contract_error("P2 compact candidate is invalid or over budget", "core_over_budget", candidate_index=index)
    if len({plan["core_message_jp"].strip() for plan in plans}) != 3:
        raise _contract_error("P2 compact planner duplicated candidates", "candidate_duplicate")
    return json.dumps({"candidate_plans": plans}, ensure_ascii=False)


class _Proxy:
    def __init__(self, target, path=()):
        self._target = target
        self._path = path

    def __getattr__(self, name):
        value = getattr(self._target, name)
        if (*self._path, name) in {("chat",), ("chat", "completions")}:
            return _Proxy(value, (*self._path, name))
        if (*self._path, name) != ("chat", "completions", "create"):
            return value

        def create(*args, **kwargs):
            context = _CALL.get()
            request = compact_request(kwargs) if context is not None and not args else None
            if request is None:
                return value(*args, **kwargs)
            context.update(schema="uruha_compact_general_plan_p2", attempted=True, completed=False,
                           candidate_count=0, max_output_tokens=request["max_tokens"],
                           original_system_chars=len(kwargs["messages"][0]["content"]),
                           compact_system_chars=len(request["messages"][0]["content"]),
                           model=request.get("model"), actual_usage_recorded_by_underlying_ledger=True,
                           raw_prompt_or_response_persisted=False)
            source_event_receipt = _source_event_request_receipt(kwargs, request)
            if source_event_receipt is not None:
                context["source_event_candidate_prompt_p4"] = source_event_receipt
            response_received = False
            try:
                response = value(**request)
                response_received = True
                expanded = expand_compact_response(response.choices[0].message.content, response.choices[0].finish_reason)
                converted = deepcopy(response)
                converted.choices[0].message.content = expanded
                context.update(completed=True, candidate_count=3)
                return converted
            except Exception as exc:
                context["failure_type"] = type(exc).__name__
                context.update(getattr(exc, "compact_failure", {
                    "failure_code": "unexpected_response_shape" if response_received else "client_or_transport_exception"
                }))
                raise
        return create


def materialize_compact_trace(result):
    """Expose actual call metadata through the existing graph, not a new UI."""
    label = "compact_general_plan_p2"
    payload = ((result.get("logic") or {}).get("bounded_slow_path_m21") or {}).get(label)
    trace = result.setdefault("runtime_trace", {})
    rows = [
        row for row in trace.get("blackboard", [])
        if row.get("label") not in {label, "source_event_candidate_prompt_p4"}
    ]
    if isinstance(payload, dict) and payload.get("schema") == "uruha_compact_general_plan_p2":
        index = next((i for i, row in enumerate(rows) if row.get("label") == "selected_plan"), len(rows))
        safe_payload = deepcopy(payload)
        source_event_receipt = _safe_source_event_receipt(payload.get("source_event_candidate_prompt_p4"))
        if source_event_receipt is None:
            safe_payload.pop("source_event_candidate_prompt_p4", None)
        else:
            safe_payload["source_event_candidate_prompt_p4"] = source_event_receipt
        if source_event_receipt is not None:
            rows.insert(index, {
                "stage": "plan", "label": "source_event_candidate_prompt_p4",
                "payload": deepcopy(source_event_receipt), "salience": 0.95,
            })
            index += 1
        rows.insert(index, {"stage": "plan", "label": label, "payload": safe_payload, "salience": 0.95})
    trace["blackboard"] = rows


def install_compact_planner_p2():
    global _INSTALLED
    if _INSTALLED:
        return False
    from uruha_brain_mac import LeftBrain, UruhaBrainV4_Mac
    from uruha_trace_history_sync_m41_1 import sync_current_history_m41_1
    previous_init, previous_think = LeftBrain.__init__, LeftBrain.think
    previous_emit = UruhaBrainV4_Mac.emit_response_if_ready
    previous_run = UruhaBrainV4_Mac.run_turn_debug

    def init(self, *args, **kwargs):
        previous_init(self, *args, **kwargs)
        self.client_logic = _Proxy(self.client_logic)

    def think(self, *args, **kwargs):
        audit = {}
        token = _CALL.set(audit)
        try:
            result = previous_think(self, *args, **kwargs)
            if audit:
                result.setdefault("bounded_slow_path_m21", {})["compact_general_plan_p2"] = deepcopy(audit)
            return result
        finally:
            _CALL.reset(token)
    LeftBrain.__init__, LeftBrain.think = init, think

    def finish(self, result):
        materialize_compact_trace(result)
        self.runtime.blackboard = deepcopy(result["runtime_trace"]["blackboard"])
        sync_current_history_m41_1(result)
        if self.runtime.turn_traces and self.runtime.turn_traces[-1].get("cycle_index") == result["runtime_trace"].get("cycle_index"):
            self.runtime.turn_traces[-1] = deepcopy(result["runtime_trace"])
        return result

    def emit(self, event, tick_result):
        return finish(self, previous_emit(self, event, tick_result))

    def run(self, user_input, input_context=None):
        return finish(self, previous_run(self, user_input, input_context=input_context))

    UruhaBrainV4_Mac.emit_response_if_ready = emit
    UruhaBrainV4_Mac.run_turn_debug = run
    _INSTALLED = True
    return True
