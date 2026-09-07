"""Product-only transport contract for three compact, real planner candidates.

Preserves the old model, input and Memory/Hard rules. The instrumented underlying
client records the real compact call, before expansion to the old internal schema.
No answer inventory, synthetic model response, or learning-outcome mutation.
"""
from contextvars import ContextVar
from copy import deepcopy
import json
import math

_CALL = ContextVar("compact_general_plan_p2", default=None)
_INSTALLED = False
_SCENES = {"casual", "support", "invite", "jealousy", "boundary", "refusal", "ooc_defense"}
_MODES = {"direct_answer", "direct_answer_with_hedge", "clarify_light", "premise_challenge", "reframe_large_question"}
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
    transformed["max_tokens"] = min(int(kwargs.get("max_tokens") or 256), 256)
    transformed["response_format"] = {"type": "json_object"}
    return transformed


def expand_compact_response(content, finish_reason):
    if finish_reason != "stop":
        raise ValueError("P2 compact planner did not finish a complete response")
    payload = json.loads(content)
    if not isinstance(payload, dict) or set(payload) != {"plans"}:
        raise ValueError("P2 compact planner has an unexpected schema")
    plans = payload["plans"]
    if not isinstance(plans, list) or len(plans) != 3:
        raise ValueError("P2 compact planner requires exactly three actual candidates")
    for plan in plans:
        if not isinstance(plan, dict) or set(plan) != {"scene", "core_message_jp", "response_mode"}:
            raise ValueError("P2 compact candidate has unexpected fields")
        core = plan["core_message_jp"]
        if (plan["scene"] not in _SCENES or plan["response_mode"] not in _MODES
                or not isinstance(core, str) or not core.strip() or len(core) > 32):
            raise ValueError("P2 compact candidate is invalid or over budget")
    if len({plan["core_message_jp"].strip() for plan in plans}) != 3:
        raise ValueError("P2 compact planner duplicated candidates")
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
            try:
                response = value(**request)
                expanded = expand_compact_response(response.choices[0].message.content, response.choices[0].finish_reason)
                converted = deepcopy(response)
                converted.choices[0].message.content = expanded
                context.update(completed=True, candidate_count=3)
                return converted
            except Exception as exc:
                context["failure_type"] = type(exc).__name__
                raise
        return create


def materialize_compact_trace(result):
    """Expose actual call metadata through the existing graph, not a new UI."""
    label = "compact_general_plan_p2"
    payload = ((result.get("logic") or {}).get("bounded_slow_path_m21") or {}).get(label)
    trace = result.setdefault("runtime_trace", {})
    rows = [row for row in trace.get("blackboard", []) if row.get("label") != label]
    if isinstance(payload, dict) and payload.get("schema") == "uruha_compact_general_plan_p2":
        index = next((i for i, row in enumerate(rows) if row.get("label") == "selected_plan"), len(rows))
        rows.insert(index, {"stage": "plan", "label": label, "payload": deepcopy(payload), "salience": 0.95})
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
