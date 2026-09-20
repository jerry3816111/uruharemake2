"""Product-only adapter for the frozen P4-C read-only function seam."""

from __future__ import annotations

from contextlib import nullcontext
from copy import deepcopy
import os
import tempfile
import time
from typing import Any, Callable

import uruha_read_only_function_calling_p4 as core


LABEL = "function_calling_p4_c"
_INSTALLED = False
_ORIGINAL_RUN_TURN = None
_PROVIDER_FACTORY: Callable[[], Any] | None = None


def _memory_isolation_from_environment(environ: dict[str, str] | None = None) -> str:
    environ = environ if environ is not None else os.environ
    required = (
        "URUHA_MEMORY_DB_PATH",
        "URUHA_WEB_SESSION_DB_PATH",
        "URUHA_WEB_LOG_JSONL_PATH",
        "URUHA_WEB_LOG_TXT_PATH",
    )
    if environ.get("URUHA_PRODUCT_WRITE_SANDBOX") == "1" and all(
        environ.get(name) for name in required
    ):
        return "isolated"
    return "unknown"


def read_product_runtime_status(runtime: Any) -> dict[str, Any]:
    """Read only bounded lifecycle counters; never initialize or inspect memory."""
    lock = getattr(runtime, "_lock", None)
    context = lock if hasattr(lock, "__enter__") else nullcontext()
    with context:
        brain_loaded = getattr(runtime, "_brain", None) is not None
        turn_count = int(getattr(runtime, "_turn_index", 0))
    return core.runtime_status_payload(
        brain_loaded=brain_loaded,
        turn_count=turn_count,
        memory_isolation=_memory_isolation_from_environment(),
    )


def _safe_function_summary(function_result: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "uruha_product_function_calling_p4_c",
        "status": function_result.get("status"),
        "gate_status": (function_result.get("gate") or {}).get("status"),
        "gate_language": (function_result.get("gate") or {}).get("language"),
        "model_call_count": int(function_result.get("model_call_count") or 0),
        "tool_execution_count": int(function_result.get("tool_execution_count") or 0),
        "tool_name": (
            core.TOOL_NAME
            if function_result.get("status") == "tool_call_complete"
            else None
        ),
        "read_only": True,
        "side_effect_count": 0,
        "raw_dialogue_or_provider_response_persisted": False,
    }


def _product_turn_result(
    base_module: Any,
    *,
    user_text: str,
    function_result: dict[str, Any],
    auto_tts: bool,
    frontend_enqueue_started: float,
    handler_started: float,
) -> dict[str, Any]:
    reply = str(function_result.get("reply") or "").strip()
    now = time.perf_counter()
    handler_started = float(handler_started or now)
    frontend_enqueue_started = float(frontend_enqueue_started or handler_started)
    latency = {
        "schema": "uruha_runtime_latency_m19",
        "frontend_queue_wait_seconds": round(
            max(0.0, handler_started - frontend_enqueue_started), 4
        ),
        "runtime_lock_wait_seconds": 0.0,
        "cold_brain_initialization_seconds": 0.0,
        "request_wait_for_brain_seconds": 0.0,
        "brain_work_seconds": round(max(0.0, now - handler_started), 4),
        "surface_stream_seconds": 0.0,
        "handler_total_seconds": round(max(0.0, now - handler_started), 4),
        "end_to_end_after_enqueue_seconds": round(
            max(0.0, now - frontend_enqueue_started), 4
        ),
        "user_wait_seconds": round(max(0.0, now - frontend_enqueue_started), 4),
        "delivery_complete": False,
        "target_seconds": 20.0,
        "contains_raw_dialogue": False,
    }
    latency["target_met"] = latency["user_wait_seconds"] <= latency["target_seconds"]
    summary = _safe_function_summary(function_result)
    blackboard = deepcopy(function_result.get("trace") or [])
    blackboard.append(
        {
            "stage": "observe",
            "label": "runtime_latency_m19",
            "payload": deepcopy(latency),
            "salience": 0.94,
        }
    )
    runtime_trace = {
        "schema": "uruha_product_function_calling_trace_p4_c",
        "cycle_index": int(getattr(base_module.RUNTIME, "_turn_index", 0)) + 1,
        "focus": {"label": "explicit runtime status request"},
        "goal": {"kind": "read_only_runtime_status"},
        "blackboard": blackboard,
        LABEL: deepcopy(summary),
        "runtime_latency_m19": deepcopy(latency),
    }
    runtime_state = {
        "cycle_index": runtime_trace["cycle_index"],
        "current_focus": "explicit runtime status request",
        "active_goal": "read_only_runtime_status",
        "open_loops": [],
        "last_state_diff": {},
    }
    logic = {
        "intent": "runtime_status",
        "scene": "casual",
        "response_mode": "direct_answer",
        "surface_act": "read_only_status_report",
        "payload_level": "low",
        "routing_path": "product_function_calling_p4_c",
        "visible_language_guard": {
            "status": "matched",
            "language": "ja",
            "final_reply_sha256": core.sha256_text(reply),
        },
        LABEL: deepcopy(summary),
        "runtime_latency_m19": deepcopy(latency),
    }
    turn = {
        "user_text": user_text,
        "reply": reply,
        "logic": logic,
        "memory_data": {},
        "runtime_trace": runtime_trace,
        "runtime_state": runtime_state,
        "reflection": None,
        "memory_runtime": {
            "read_only_status_turn": True,
            "memory_content_read_count": 0,
            "memory_write_count": 0,
        },
    }
    audio_path = None
    if auto_tts:
        temporary = tempfile.NamedTemporaryFile(
            prefix="uruha_web_reply_", suffix=".wav", delete=False
        )
        temporary.close()
        audio_path = base_module.RUNTIME.get_mouth().synthesize_to_file(
            reply, output_file=temporary.name
        )
    debug = {
        "intent": logic["intent"],
        "scene": logic["scene"],
        "response_mode": logic["response_mode"],
        "surface_act": logic["surface_act"],
        "planner_tick_count": 0,
        "self_correction_applied": False,
        "payload_level": logic["payload_level"],
        "core_message_jp": reply,
        "grounding": {"source": "validated_read_only_tool_result"},
        "routing_path": logic["routing_path"],
        "internal_monologue": None,
    }
    cognition = base_module._extract_trace_payload(turn)
    memory = base_module._extract_memory_payload(turn)
    observatory = {
        "user_text": user_text,
        "reply": reply,
        "logic": logic,
        "memory_data": memory,
        "runtime_trace": runtime_trace,
        "runtime_state": runtime_state,
    }
    return {
        "user_text": user_text,
        "reply": reply,
        "audio_path": audio_path,
        "debug": debug,
        "logic": logic,
        "memory_snapshot": memory,
        "cognition_trace": cognition,
        "flow_html": base_module._render_flow_html(observatory),
        "state_html": base_module._render_state_diff_html(observatory),
    }


def run_product_turn_p4_c(
    base_module: Any,
    original_run_turn: Callable[..., Any],
    user_text: str,
    auto_tts: bool,
    input_mode: str = "text",
    acoustic_summary: Any = None,
    frontend_enqueue_started: float = 0.0,
    handler_started: float = 0.0,
    *,
    provider: Any = None,
) -> Any:
    text = str(user_text or "").strip()
    gate = core.classify_runtime_status_request(text)
    if not gate.get("selected"):
        return original_run_turn(
            user_text,
            auto_tts,
            input_mode=input_mode,
            acoustic_summary=acoustic_summary,
            frontend_enqueue_started=frontend_enqueue_started,
            handler_started=handler_started,
        )
    base_module.RUNTIME.mark_activity()
    started = time.perf_counter()
    function_result = core.run_function_call_turn(
        text,
        provider=provider or (_PROVIDER_FACTORY or core.LocalOllamaToolsProvider)(),
        status_reader=lambda: read_product_runtime_status(base_module.RUNTIME),
    )
    return _product_turn_result(
        base_module,
        user_text=text,
        function_result=function_result,
        auto_tts=auto_tts,
        frontend_enqueue_started=frontend_enqueue_started,
        handler_started=float(handler_started or started),
    )


def install_product_function_calling_p4(
    base_module: Any, *, provider_factory: Callable[[], Any] | None = None
) -> bool:
    global _INSTALLED, _ORIGINAL_RUN_TURN, _PROVIDER_FACTORY
    if _INSTALLED:
        return False
    _ORIGINAL_RUN_TURN = base_module._run_turn
    _PROVIDER_FACTORY = provider_factory or core.LocalOllamaToolsProvider

    def wrapped(
        user_text,
        auto_tts,
        input_mode="text",
        acoustic_summary=None,
        frontend_enqueue_started=0.0,
        handler_started=0.0,
    ):
        return run_product_turn_p4_c(
            base_module,
            _ORIGINAL_RUN_TURN,
            user_text,
            auto_tts,
            input_mode=input_mode,
            acoustic_summary=acoustic_summary,
            frontend_enqueue_started=frontend_enqueue_started,
            handler_started=handler_started,
        )

    base_module._run_turn = wrapped
    _INSTALLED = True
    return True

