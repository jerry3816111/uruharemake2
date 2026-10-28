"""Product-only truth repair for failed P4-C read-only status turns.

The frozen P4-C adapter already supplies the correct failure reply, summary,
and core graph nodes.  This overlay only aligns its success-labelled product
logic/debug projection with that same-turn failed-closed result.
"""

from __future__ import annotations

from typing import Any


_ROUTING_PATH = "product_function_calling_p4_c"
_SUMMARY_LABEL = "function_calling_p4_c"
_FAILURE_SURFACE_ACT = "read_only_status_failed_closed"
_FAILURE_GROUNDING = {
    "source": "failed_closed_read_only_status_attempt",
    "status": "failed_closed",
    "validated_tool_result": False,
}
_WRAPPER_MARKER = "_uruha_product_tool_failure_truth_p4"


def repair_product_tool_failure_truth_p4(base_module: Any, result: Any) -> Any:
    """Repair only a P4-C failed-closed projection; leave all other turns alone."""
    if not isinstance(result, dict):
        return result
    logic = result.get("logic")
    if not isinstance(logic, dict) or logic.get("routing_path") != _ROUTING_PATH:
        return result
    summary = logic.get(_SUMMARY_LABEL)
    if not isinstance(summary, dict) or summary.get("status") != "failed_closed":
        return result

    debug = result.get("debug")
    cognition = result.get("cognition_trace")
    if not isinstance(debug, dict) or not isinstance(cognition, dict):
        return result

    logic["surface_act"] = _FAILURE_SURFACE_ACT
    logic["grounding"] = dict(_FAILURE_GROUNDING)
    debug["surface_act"] = _FAILURE_SURFACE_ACT
    debug["grounding"] = dict(_FAILURE_GROUNDING)
    cognition["surface_act"] = _FAILURE_SURFACE_ACT
    cognition["grounding"] = dict(_FAILURE_GROUNDING)

    # Reuse the returned turn's trace and reply.  No node, model/tool attempt,
    # memory access, or visible surface is created by this projection repair.
    observatory = {
        "user_text": result.get("user_text") or "",
        "reply": result.get("reply") or "",
        "logic": logic,
        "memory_data": result.get("memory_snapshot") or {},
        "runtime_trace": cognition.get("runtime_trace") or {},
        "runtime_state": cognition.get("runtime_state") or {},
    }
    result["flow_html"] = base_module._render_flow_html(observatory)
    result["state_html"] = base_module._render_state_diff_html(observatory)
    return result


def install_product_tool_failure_truth_p4(base_module: Any) -> bool:
    """Wrap the current product turn once, after the P4-C adapter is installed."""
    previous_run_turn = base_module._run_turn
    if getattr(previous_run_turn, _WRAPPER_MARKER, False):
        return False

    def wrapped(*args: Any, **kwargs: Any) -> Any:
        return repair_product_tool_failure_truth_p4(
            base_module, previous_run_turn(*args, **kwargs)
        )

    setattr(wrapped, _WRAPPER_MARKER, True)
    base_module._run_turn = wrapped
    return True
