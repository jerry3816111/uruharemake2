"""Pure-standard-library contracts for the bounded P3 product comparison.

This module deliberately contains no product, database, Ollama, Gradio, or Torch
imports.  Real transports and the product worker are injected by the CLI only
after a separately reviewed release exists.  P3-A uses deterministic fakes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import itertools
import json
from pathlib import Path
import random
import time
from typing import Any, Callable, Iterable, Mapping, MutableMapping


CONDITIONS = (
    "full_history_direct",
    "full_history_deliberate",
    "product_system",
)
DESIGN_SCHEMA = "uruha_p3_product_comparison_design_v1"
VIEW_SCHEMA = "uruha_p3_generation_view_v1"
MANIFEST_SCHEMA = "uruha_p3_contract_manifest_v1"
VIEW_KEYS = frozenset(
    {
        "schema",
        "condition",
        "visible_prefix",
        "current_input",
        "source_history_sha256",
        "input_sha256",
        "source_sha256",
        "view_sha256",
    }
)
ALLOWED_TURN_KEYS = frozenset({"turn_id", "session_id", "role", "content"})
ALLOWED_INPUT_KEYS = frozenset({"turn_id", "session_id", "content"})


class P3ContractError(ValueError):
    """A fail-closed P3 contract violation with a stable machine-readable code."""

    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}" if detail else code)


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _require_exact_int(value: Any, name: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise P3ContractError("invalid_integer", name)
    return value


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise P3ContractError("invalid_json", f"{path}: {exc}") from exc


def load_design(path: str | Path) -> dict[str, Any]:
    """Load and validate the frozen P3 design without mutating it."""

    design_path = Path(path)
    design = _load_json(design_path)
    if not isinstance(design, dict) or design.get("schema") != DESIGN_SCHEMA:
        raise P3ContractError("design_schema_mismatch", str(design_path))
    if tuple(design.get("conditions", ())) != CONDITIONS:
        raise P3ContractError("condition_set_mismatch")
    release = design.get("implementation_release")
    if not isinstance(release, dict) or release.get("stage") != "P3-A":
        raise P3ContractError("invalid_implementation_release")
    if release.get("real_generation_authorized") is not False:
        raise P3ContractError("p3a_real_generation_must_be_disabled")
    model = design.get("model")
    budget = design.get("budget")
    history = design.get("common_history")
    if not all(isinstance(item, dict) for item in (model, budget, history)):
        raise P3ContractError("missing_design_section")
    if model.get("generation_model") != "qwen2.5:7b":
        raise P3ContractError("generation_model_mismatch")
    if model.get("all_generation_routes_same_model") is not True:
        raise P3ContractError("model_route_lock_missing")
    if history.get("truncate_or_summarize") is not False:
        raise P3ContractError("history_truncation_not_forbidden")
    if history.get("include_all_prior_sessions") is not True:
        raise P3ContractError("all_prior_sessions_not_required")
    frozen = json.loads(json.dumps(design, ensure_ascii=False))
    frozen["_design_sha256"] = canonical_sha256(design)
    frozen["_design_path"] = str(design_path.resolve())
    return frozen


def _normalise_prefix(prefix: Iterable[Mapping[str, Any]]) -> list[dict[str, str]]:
    if isinstance(prefix, (str, bytes, Mapping)):
        raise P3ContractError("invalid_prefix_type")
    result: list[dict[str, str]] = []
    seen_turns: set[str] = set()
    for index, raw in enumerate(prefix):
        if not isinstance(raw, Mapping):
            raise P3ContractError("invalid_turn", str(index))
        extras = set(raw) - ALLOWED_TURN_KEYS
        missing = ALLOWED_TURN_KEYS - set(raw)
        if extras or missing:
            raise P3ContractError(
                "turn_allowlist_violation",
                f"index={index} extras={sorted(extras)} missing={sorted(missing)}",
            )
        turn = {key: raw[key] for key in ("turn_id", "session_id", "role", "content")}
        if not all(isinstance(value, str) and value for value in turn.values()):
            raise P3ContractError("invalid_turn_value", str(index))
        if turn["role"] not in {"user", "assistant"}:
            raise P3ContractError("invalid_visible_role", turn["role"])
        if turn["turn_id"] in seen_turns:
            raise P3ContractError("duplicate_turn_id", turn["turn_id"])
        seen_turns.add(turn["turn_id"])
        result.append(turn)
    return result


def _normalise_current_input(current_input: str | Mapping[str, Any]) -> dict[str, str]:
    if isinstance(current_input, str):
        if not current_input:
            raise P3ContractError("empty_current_input")
        return {"turn_id": "current", "session_id": "current", "content": current_input}
    if not isinstance(current_input, Mapping):
        raise P3ContractError("invalid_current_input")
    extras = set(current_input) - ALLOWED_INPUT_KEYS
    missing = ALLOWED_INPUT_KEYS - set(current_input)
    if extras or missing:
        raise P3ContractError(
            "input_allowlist_violation",
            f"extras={sorted(extras)} missing={sorted(missing)}",
        )
    result = {key: current_input[key] for key in ("turn_id", "session_id", "content")}
    if not all(isinstance(value, str) and value for value in result.values()):
        raise P3ContractError("invalid_current_input_value")
    return result


def freeze_common_source(
    prefix: Iterable[Mapping[str, Any]], current_input: str | Mapping[str, Any]
) -> dict[str, Any]:
    """Freeze the source before any condition runs."""

    clean_prefix = _normalise_prefix(prefix)
    clean_input = _normalise_current_input(current_input)
    if any(turn["turn_id"] == clean_input["turn_id"] for turn in clean_prefix):
        raise P3ContractError("current_reply_or_input_leaked", clean_input["turn_id"])
    source = {
        "prefix": clean_prefix,
        "current_input": clean_input,
    }
    return {
        "schema": "uruha_p3_common_source_v1",
        "source_history_sha256": canonical_sha256(clean_prefix),
        "input_sha256": canonical_sha256(clean_input),
        "source_sha256": canonical_sha256(source),
        "session_ids": list(dict.fromkeys(turn["session_id"] for turn in clean_prefix)),
        "turn_count": len(clean_prefix),
    }


def build_generation_view(
    prefix: Iterable[Mapping[str, Any]],
    current_input: str | Mapping[str, Any],
    condition: str,
) -> dict[str, Any]:
    """Build a new allowlisted view; never copy/pop a case object."""

    if condition not in CONDITIONS:
        raise P3ContractError("unknown_condition", condition)
    clean_prefix = _normalise_prefix(prefix)
    clean_input = _normalise_current_input(current_input)
    commitment = freeze_common_source(clean_prefix, clean_input)
    view = {
        "schema": VIEW_SCHEMA,
        "condition": condition,
        "visible_prefix": clean_prefix,
        "current_input": clean_input,
        "source_history_sha256": commitment["source_history_sha256"],
        "input_sha256": commitment["input_sha256"],
        "source_sha256": commitment["source_sha256"],
    }
    view["view_sha256"] = canonical_sha256(view)
    return view


def validate_common_views(
    views: Mapping[str, Mapping[str, Any]], source_commitment: Mapping[str, Any]
) -> None:
    if set(views) != set(CONDITIONS):
        raise P3ContractError("view_condition_set_mismatch")
    expected = (
        source_commitment.get("source_history_sha256"),
        source_commitment.get("input_sha256"),
        source_commitment.get("source_sha256"),
    )
    for condition in CONDITIONS:
        view = views[condition]
        validate_generation_view(view, condition)
        actual = (
            view.get("source_history_sha256"),
            view.get("input_sha256"),
            view.get("source_sha256"),
        )
        if actual != expected:
            raise P3ContractError("common_source_mismatch", condition)


def validate_generation_view(
    view: Mapping[str, Any], expected_condition: str | None = None
) -> None:
    if not isinstance(view, Mapping) or set(view) != VIEW_KEYS:
        raise P3ContractError("view_allowlist_violation")
    if view.get("schema") != VIEW_SCHEMA:
        raise P3ContractError("view_schema_mismatch")
    condition = view.get("condition")
    if condition not in CONDITIONS:
        raise P3ContractError("unknown_condition", str(condition))
    if expected_condition is not None and condition != expected_condition:
        raise P3ContractError("view_condition_mismatch", expected_condition)
    stored_hash = view.get("view_sha256")
    unhashed = dict(view)
    unhashed.pop("view_sha256", None)
    if stored_hash != canonical_sha256(unhashed):
        raise P3ContractError("view_digest_mismatch", str(condition))
    prefix = _normalise_prefix(view.get("visible_prefix"))
    current_input = _normalise_current_input(view.get("current_input"))
    commitment = freeze_common_source(prefix, current_input)
    for key in ("source_history_sha256", "input_sha256", "source_sha256"):
        if view.get(key) != commitment[key]:
            raise P3ContractError("view_source_digest_mismatch", key)


@dataclass
class BudgetState:
    condition: str
    generation_model: str
    model_options: dict[str, Any]
    aggregate_prompt_tokens_max: int
    aggregate_completion_tokens_max: int
    per_call_context_total_tokens_max: int
    common_history_tokens_max: int
    wall_seconds_max: float
    calls_max: int
    system_per_call_completion_max: int | None = None
    attempts: int = 0
    completed_calls: int = 0
    declared_prompt_tokens: int = 0
    allocated_completion_tokens: int = 0
    actual_prompt_tokens: int = 0
    actual_completion_tokens: int = 0
    wall_seconds: float = 0.0
    condition_wall_seconds: float = 0.0
    measured_transport_wall_seconds: float = 0.0
    terminal_failure: str | None = None
    reservations: MutableMapping[str, dict[str, Any]] = field(default_factory=dict)

    def snapshot(self) -> dict[str, Any]:
        return {
            "condition": self.condition,
            "attempts": self.attempts,
            "completed_calls": self.completed_calls,
            "declared_prompt_tokens": self.declared_prompt_tokens,
            "allocated_completion_tokens": self.allocated_completion_tokens,
            "actual_prompt_tokens": self.actual_prompt_tokens,
            "actual_completion_tokens": self.actual_completion_tokens,
            "wall_seconds": round(self.wall_seconds, 6),
            "condition_wall_seconds": round(self.condition_wall_seconds, 6),
            "terminal_failure": self.terminal_failure,
            "calls_max": self.calls_max,
            "aggregate_prompt_tokens_max": self.aggregate_prompt_tokens_max,
            "aggregate_completion_tokens_max": self.aggregate_completion_tokens_max,
            "common_history_tokens_max": self.common_history_tokens_max,
        }


def new_budget(design: Mapping[str, Any], condition: str) -> BudgetState:
    if condition not in CONDITIONS:
        raise P3ContractError("unknown_condition", condition)
    budget = design["budget"]
    turn = budget["per_condition_turn"]
    model = design["model"]
    calls_key = {
        "full_history_direct": "direct_calls_max",
        "full_history_deliberate": "deliberate_calls_max",
        "product_system": "system_calls_max",
    }[condition]
    options = {
        "temperature": model["temperature"],
        "seed": model["seed"],
        "top_p": model["top_p"],
        "num_ctx": model["num_ctx"],
        "think": model["think"],
    }
    return BudgetState(
        condition=condition,
        generation_model=model["generation_model"],
        model_options=options,
        aggregate_prompt_tokens_max=turn["aggregate_prompt_tokens_max"],
        aggregate_completion_tokens_max=turn["aggregate_completion_tokens_max"],
        per_call_context_total_tokens_max=budget["per_call_context_total_tokens_max"],
        common_history_tokens_max=budget["common_history_tokens_max"],
        wall_seconds_max=float(turn["wall_seconds_max"]),
        calls_max=budget[calls_key],
        system_per_call_completion_max=(
            budget["system_per_call_completion_max"]
            if condition == "product_system"
            else None
        ),
    )


def _request_commitment(request: Mapping[str, Any]) -> dict[str, Any]:
    messages = request.get("messages")
    if not isinstance(messages, list):
        raise P3ContractError("invalid_messages")
    message_commitments: list[dict[str, Any]] = []
    for message in messages:
        if not isinstance(message, Mapping) or set(message) != {"role", "content"}:
            raise P3ContractError("invalid_message_shape")
        role, content = message["role"], message["content"]
        if role not in {"system", "user", "assistant"} or not isinstance(content, str):
            raise P3ContractError("invalid_message_value")
        message_commitments.append(
            {"role": role, "content_sha256": canonical_sha256(content)}
        )
    return {
        "condition": request.get("condition"),
        "stage": request.get("stage"),
        "model": request.get("model"),
        "backend": request.get("backend"),
        "options": request.get("options"),
        "prompt_tokens": request.get("prompt_tokens"),
        "max_completion_tokens": request.get("max_completion_tokens"),
        "messages": message_commitments,
    }


def reserve_call(budget: BudgetState, request: Mapping[str, Any]) -> dict[str, Any]:
    """Reserve one logical provider call from the shared per-condition budget."""

    if budget.terminal_failure:
        raise P3ContractError("budget_terminal", budget.terminal_failure)
    if request.get("condition") != budget.condition:
        raise P3ContractError("request_condition_mismatch")
    if request.get("model") != budget.generation_model:
        raise P3ContractError("model_gate_rejected", str(request.get("model")))
    if request.get("options") != budget.model_options:
        raise P3ContractError("model_options_mismatch")
    if request.get("backend") not in {
        "fake_local",
        "openai_compatible_local",
        "native_ollama_chat",
    }:
        raise P3ContractError("backend_not_allowed", str(request.get("backend")))
    prompt = _require_exact_int(request.get("prompt_tokens"), "prompt_tokens")
    completion = _require_exact_int(
        request.get("max_completion_tokens"), "max_completion_tokens", minimum=1
    )
    if budget.system_per_call_completion_max is not None:
        if completion > budget.system_per_call_completion_max:
            raise P3ContractError("system_per_call_completion_exceeded")
    if budget.attempts + 1 > budget.calls_max:
        raise P3ContractError("call_budget_exceeded")
    if budget.declared_prompt_tokens + prompt > budget.aggregate_prompt_tokens_max:
        raise P3ContractError("aggregate_prompt_budget_exceeded")
    if (
        budget.allocated_completion_tokens + completion
        > budget.aggregate_completion_tokens_max
    ):
        raise P3ContractError("aggregate_completion_budget_exceeded")
    if prompt + completion > budget.per_call_context_total_tokens_max:
        raise P3ContractError("context_budget_exceeded_no_truncation")
    commitment = _request_commitment(request)
    reservation_id = canonical_sha256(
        {"sequence": budget.attempts + 1, "request": commitment}
    )
    if reservation_id in budget.reservations:
        raise P3ContractError("duplicate_reservation")
    reservation = {
        "reservation_id": reservation_id,
        "request_sha256": canonical_sha256(commitment),
        "prompt_tokens": prompt,
        "max_completion_tokens": completion,
        "recorded": False,
    }
    budget.reservations[reservation_id] = reservation
    budget.attempts += 1
    budget.declared_prompt_tokens += prompt
    budget.allocated_completion_tokens += completion
    return dict(reservation)


def record_usage(
    budget: BudgetState,
    provider_usage: Mapping[str, Any],
    reservation: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Record exact provider usage. Unknown counts are terminal, never estimated."""

    try:
        prompt = _require_exact_int(provider_usage.get("prompt_tokens"), "prompt_tokens")
        completion = _require_exact_int(
            provider_usage.get("completion_tokens"), "completion_tokens"
        )
        elapsed = provider_usage.get("wall_seconds")
        if isinstance(elapsed, bool) or not isinstance(elapsed, (int, float)) or elapsed < 0:
            raise P3ContractError("invalid_wall_seconds")
        if reservation is None:
            pending = [item for item in budget.reservations.values() if not item["recorded"]]
            if len(pending) != 1:
                raise P3ContractError("ambiguous_usage_reservation")
            reservation = pending[0]
        stored = budget.reservations.get(str(reservation.get("reservation_id")))
        if stored is None or stored.get("request_sha256") != reservation.get("request_sha256"):
            raise P3ContractError("unknown_usage_reservation")
        if stored["recorded"]:
            raise P3ContractError("usage_already_recorded")
        if completion > stored["max_completion_tokens"]:
            raise P3ContractError("actual_completion_exceeded_reservation")
        if prompt + stored["max_completion_tokens"] > budget.per_call_context_total_tokens_max:
            raise P3ContractError("actual_context_budget_exceeded")
        if budget.actual_prompt_tokens + prompt > budget.aggregate_prompt_tokens_max:
            raise P3ContractError("actual_prompt_budget_exceeded")
        if budget.actual_completion_tokens + completion > budget.aggregate_completion_tokens_max:
            raise P3ContractError("actual_completion_budget_exceeded")
        if budget.wall_seconds + float(elapsed) > budget.wall_seconds_max:
            raise P3ContractError("wall_budget_exceeded")
    except P3ContractError as exc:
        budget.terminal_failure = exc.code
        raise
    stored["recorded"] = True
    budget.completed_calls += 1
    budget.actual_prompt_tokens += prompt
    budget.actual_completion_tokens += completion
    budget.wall_seconds += float(elapsed)
    return {
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "wall_seconds": float(elapsed),
    }


def mark_transport_failure(budget: BudgetState, code: str) -> None:
    budget.terminal_failure = code


def record_condition_wall(budget: BudgetState, elapsed: float) -> None:
    if isinstance(elapsed, bool) or not isinstance(elapsed, (int, float)) or elapsed < 0:
        budget.terminal_failure = "invalid_condition_wall_seconds"
        raise P3ContractError("invalid_condition_wall_seconds")
    budget.condition_wall_seconds = float(elapsed)
    if budget.condition_wall_seconds > budget.wall_seconds_max:
        budget.terminal_failure = "condition_wall_budget_exceeded"
        raise P3ContractError("condition_wall_budget_exceeded")


def build_balanced_condition_schedule(
    case_ids: Iterable[str], seed: int
) -> dict[str, list[str]]:
    """Precompute a deterministic schedule balanced across all six orders."""

    ids = list(case_ids)
    if len(ids) != len(set(ids)) or not all(isinstance(item, str) and item for item in ids):
        raise P3ContractError("invalid_schedule_case_ids")
    permutations = [list(order) for order in itertools.permutations(CONDITIONS)]
    random.Random(seed).shuffle(permutations)
    return {case_id: list(permutations[index % len(permutations)]) for index, case_id in enumerate(ids)}


class CaseWorkspaceRegistry:
    """Reject state path reuse between cases while allowing restarts within a case."""

    def __init__(self) -> None:
        self._path_to_case: dict[str, str] = {}
        self._case_to_path: dict[str, str] = {}

    def claim(self, case_id: str, state_path: str | Path) -> str:
        if not case_id or not isinstance(case_id, str):
            raise P3ContractError("invalid_case_id")
        resolved = str(Path(state_path).resolve())
        prior_case = self._path_to_case.get(resolved)
        if prior_case is not None and prior_case != case_id:
            raise P3ContractError("cross_case_state_reuse", f"{prior_case}->{case_id}")
        prior_path = self._case_to_path.get(case_id)
        if prior_path is not None and prior_path != resolved:
            raise P3ContractError("case_state_path_changed", case_id)
        self._path_to_case[resolved] = case_id
        self._case_to_path[case_id] = resolved
        return resolved


def _write_new_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, sort_keys=True, indent=2)
            handle.write("\n")
    except FileExistsError as exc:
        raise P3ContractError("artifact_exists_no_overwrite", str(path)) from exc


def write_new_json(path: str | Path, value: Any) -> None:
    _write_new_json(Path(path), value)


def _verify_record(record: Mapping[str, Any], kind: str) -> None:
    expected = record.get("record_sha256")
    payload = dict(record)
    payload.pop("record_sha256", None)
    if not isinstance(expected, str) or expected != canonical_sha256(payload):
        raise P3ContractError(f"{kind}_digest_mismatch")


def run_call_once(
    *,
    budget: BudgetState,
    request: Mapping[str, Any],
    transport: Callable[[Mapping[str, Any]], Mapping[str, Any]],
    checkpoint_root: str | Path,
    item_id: str,
) -> dict[str, Any]:
    """Execute or reuse one immutable checkpoint; intent-only states are terminal."""

    commitment = _request_commitment(request)
    request_sha = canonical_sha256(commitment)
    safe_item = hashlib.sha256(item_id.encode("utf-8")).hexdigest()[:20]
    safe_stage = hashlib.sha256(str(request.get("stage", "stage")).encode("utf-8")).hexdigest()[:16]
    call_dir = Path(checkpoint_root) / safe_item / budget.condition / safe_stage
    intent_path = call_dir / "intent.json"
    complete_path = call_dir / "complete.json"
    failure_path = call_dir / "failure.json"

    if complete_path.exists():
        complete = _load_json(complete_path)
        if not isinstance(complete, dict):
            raise P3ContractError("complete_checkpoint_invalid")
        _verify_record(complete, "complete_checkpoint")
        if complete.get("request_sha256") != request_sha:
            raise P3ContractError("complete_checkpoint_source_mismatch")
        completed_result = complete.get("result")
        completed_usage = complete.get("usage")
        if not isinstance(completed_result, Mapping) or not isinstance(
            completed_usage, Mapping
        ):
            raise P3ContractError("complete_checkpoint_invalid")
        if completed_result.get("content_sha256") != canonical_sha256(
            completed_result.get("content")
        ):
            raise P3ContractError("complete_checkpoint_output_digest_mismatch")
        if completed_result.get("request_sha256") != request_sha:
            raise P3ContractError("complete_checkpoint_request_digest_mismatch")
        reservation = reserve_call(budget, request)
        record_usage(budget, completed_usage, reservation)
        return {"reused": True, **completed_result}
    if intent_path.exists():
        intent = _load_json(intent_path)
        if not isinstance(intent, dict):
            raise P3ContractError("intent_checkpoint_invalid")
        _verify_record(intent, "intent_checkpoint")
        if intent.get("request_sha256") != request_sha:
            raise P3ContractError("intent_checkpoint_source_mismatch")
        mark_transport_failure(budget, "intent_without_complete_no_retry")
        raise P3ContractError("intent_without_complete_no_retry")

    reservation = reserve_call(budget, request)
    intent: dict[str, Any] = {
        "schema": "uruha_p3_invocation_intent_v1",
        "item_id_sha256": canonical_sha256(item_id),
        "condition": budget.condition,
        "stage": request.get("stage"),
        "request_sha256": request_sha,
        "reservation": reservation,
    }
    intent["record_sha256"] = canonical_sha256(intent)
    _write_new_json(intent_path, intent)
    started = time.monotonic()
    try:
        response = transport(request)
    except Exception as exc:
        mark_transport_failure(budget, "transport_failure_no_retry")
        failure: dict[str, Any] = {
            "schema": "uruha_p3_terminal_failure_v1",
            "request_sha256": request_sha,
            "contract_code": "transport_failure_no_retry",
            "error_type": type(exc).__name__,
            "error_sha256": canonical_sha256(str(exc)),
        }
        failure["record_sha256"] = canonical_sha256(failure)
        _write_new_json(failure_path, failure)
        raise P3ContractError("transport_failure_no_retry", type(exc).__name__) from exc
    elapsed = time.monotonic() - started
    try:
        budget.measured_transport_wall_seconds += elapsed
        if budget.measured_transport_wall_seconds > budget.wall_seconds_max:
            raise P3ContractError("measured_transport_wall_budget_exceeded")
        if not isinstance(response, Mapping):
            raise P3ContractError("invalid_transport_response")
        if response.get("model") != budget.generation_model:
            raise P3ContractError("transport_model_mismatch")
        if response.get("backend") != request.get("backend"):
            raise P3ContractError("transport_backend_mismatch")
        content = response.get("content")
        usage = response.get("usage")
        if not isinstance(content, str) or not isinstance(usage, Mapping):
            raise P3ContractError("invalid_transport_payload")
        network_calls = _require_exact_int(
            response.get("network_calls"), "network_calls"
        )
        real_model_calls = _require_exact_int(
            response.get("real_model_calls"), "real_model_calls"
        )
        exact_usage = dict(usage)
        exact_usage.setdefault("wall_seconds", elapsed)
        recorded = record_usage(budget, exact_usage, reservation)
        result = {
            "content": content,
            "content_sha256": canonical_sha256(content),
            "request_sha256": request_sha,
            "usage": recorded,
            "max_completion_tokens": reservation["max_completion_tokens"],
            "model": response["model"],
            "backend": response["backend"],
            "network_calls": network_calls,
            "real_model_calls": real_model_calls,
        }
    except P3ContractError as exc:
        mark_transport_failure(budget, exc.code)
        failure = {
            "schema": "uruha_p3_terminal_failure_v1",
            "request_sha256": request_sha,
            "contract_code": exc.code,
            "error_type": type(exc).__name__,
            "error_sha256": canonical_sha256(exc.detail),
        }
        failure["record_sha256"] = canonical_sha256(failure)
        _write_new_json(failure_path, failure)
        raise
    complete: dict[str, Any] = {
        "schema": "uruha_p3_completed_checkpoint_v1",
        "request_sha256": request_sha,
        "usage": recorded,
        "result": result,
    }
    complete["record_sha256"] = canonical_sha256(complete)
    _write_new_json(complete_path, complete)
    return {"reused": False, **result}


def render_visible_messages(view: Mapping[str, Any]) -> list[dict[str, str]]:
    messages = [
        {"role": turn["role"], "content": turn["content"]}
        for turn in view["visible_prefix"]
    ]
    messages.append({"role": "user", "content": view["current_input"]["content"]})
    return messages


def make_request(
    *,
    design: Mapping[str, Any],
    condition: str,
    stage: str,
    messages: list[dict[str, str]],
    prompt_tokens: int,
    max_completion_tokens: int,
    backend: str = "fake_local",
) -> dict[str, Any]:
    model = design["model"]
    return {
        "condition": condition,
        "stage": stage,
        "model": model["generation_model"],
        "backend": backend,
        "options": {
            "temperature": model["temperature"],
            "seed": model["seed"],
            "top_p": model["top_p"],
            "num_ctx": model["num_ctx"],
            "think": model["think"],
        },
        "messages": messages,
        "prompt_tokens": prompt_tokens,
        "max_completion_tokens": max_completion_tokens,
    }


class FakeExactTokenCounter:
    """Deterministic contract-fixture counts, never used as real tokenizer evidence."""

    evidence_kind = "fake_exact_fixture_count"

    def __call__(self, messages: Iterable[Mapping[str, str]]) -> int:
        count = 8
        for message in messages:
            count += 3 + len(message["content"].encode("utf-8").split())
        return count


class FakeTransport:
    """Deterministic zero-network transport for P3-A wiring evidence."""

    def __init__(self, *, fail_stage: str | None = None) -> None:
        self.attempts = 0
        self.fail_stage = fail_stage
        self.requests: list[Mapping[str, Any]] = []

    def __call__(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        self.attempts += 1
        self.requests.append(request)
        if request.get("stage") == self.fail_stage:
            raise TimeoutError("injected contract timeout")
        outputs = {
            "direct": "その話なら、もう少し聞かせて。",
            "draft": "うん、今は無理に決めなくていいんじゃない。",
            "critique": "断定を避け、直前の訂正を優先する。",
            "revise": "そっか。じゃあ今は無理に決めなくていいよ。",
            "product": "分かった。今は答えを急がなくていいよ。",
        }
        stage = str(request.get("stage"))
        content = outputs.get(stage, "確認用の返答。")
        return {
            "content": content,
            "usage": {
                "prompt_tokens": request["prompt_tokens"],
                "completion_tokens": min(24, request["max_completion_tokens"]),
                "wall_seconds": 0.001,
            },
            "model": request["model"],
            "backend": request["backend"],
            "network_calls": 0,
            "real_model_calls": 0,
        }


def run_condition(
    *,
    condition: str,
    view: Mapping[str, Any],
    design: Mapping[str, Any],
    transport: Callable[[Mapping[str, Any]], Mapping[str, Any]],
    checkpoint_root: str | Path,
    item_id: str,
    token_counter: Callable[[Iterable[Mapping[str, str]]], int],
    product_worker: Callable[..., Mapping[str, Any]] | None = None,
    clock: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    """Run one condition using injected token evidence, transport, and worker."""

    validate_generation_view(view, condition)
    started = clock()
    budget = new_budget(design, condition)
    persona = design["persona"]["shared_contract"]
    visible = render_visible_messages(view)
    prefix_token_count = token_counter(visible[:-1])
    if not isinstance(prefix_token_count, int) or isinstance(prefix_token_count, bool):
        raise P3ContractError("token_count_unavailable")
    if prefix_token_count > budget.common_history_tokens_max:
        raise P3ContractError("common_history_budget_exceeded_no_truncation")
    calls: list[dict[str, Any]] = []

    def execute(stage: str, instruction: str, scratch: list[dict[str, str]], cap: int) -> dict[str, Any]:
        messages = [{"role": "system", "content": persona + "\n" + instruction}]
        messages.extend(visible)
        messages.extend(scratch)
        count = token_counter(messages)
        if not isinstance(count, int) or isinstance(count, bool):
            raise P3ContractError("token_count_unavailable")
        request = make_request(
            design=design,
            condition=condition,
            stage=stage,
            messages=messages,
            prompt_tokens=count,
            max_completion_tokens=cap,
        )
        result = run_call_once(
            budget=budget,
            request=request,
            transport=transport,
            checkpoint_root=checkpoint_root,
            item_id=item_id,
        )
        calls.append({"stage": stage, **result})
        return result

    if condition == "full_history_direct":
        final = execute("direct", design["baselines"]["direct_instruction"], [], 768)
        private_scratch_count = 0
        worker_evidence: dict[str, Any] | None = None
    elif condition == "full_history_deliberate":
        instructions = design["baselines"]["deliberate_instructions"]
        allocations = design["budget"]["deliberate_completion_allocations"]
        draft = execute("draft", instructions[0], [], allocations[0])
        critique = execute(
            "critique",
            instructions[1],
            [{"role": "assistant", "content": draft["content"]}],
            allocations[1],
        )
        final = execute(
            "revise",
            instructions[2],
            [
                {"role": "assistant", "content": draft["content"]},
                {"role": "assistant", "content": critique["content"]},
            ],
            allocations[2],
        )
        private_scratch_count = 2
        worker_evidence = None
    else:
        if product_worker is None:
            raise P3ContractError("product_worker_required")
        worker_result = product_worker(
            view=view,
            execute=execute,
            design=design,
            item_id=item_id,
        )
        if not isinstance(worker_result, Mapping) or not isinstance(
            worker_result.get("final"), Mapping
        ):
            raise P3ContractError("invalid_product_worker_result")
        final = dict(worker_result["final"])
        private_scratch_count = int(worker_result.get("private_scratch_count", 0))
        worker_evidence = dict(worker_result.get("evidence", {}))

    record_condition_wall(budget, clock() - started)
    return {
        "condition": condition,
        "source_history_sha256": view["source_history_sha256"],
        "input_sha256": view["input_sha256"],
        "final": final,
        "calls": calls,
        "private_scratch_count": private_scratch_count,
        "private_scratch_written_to_visible_history": False,
        "budget": budget.snapshot(),
        "common_history_tokens": prefix_token_count,
        "worker_evidence": worker_evidence,
    }


def map_blind_scores(order: str, left: float, right: float, a: str, b: str) -> dict[str, float]:
    if order not in {"AB", "BA"} or a == b:
        raise P3ContractError("invalid_blind_mapping")
    if order == "AB":
        return {a: left, b: right}
    return {b: left, a: right}


def validate_run_manifest(manifest: Mapping[str, Any]) -> None:
    """Validate P3-A contract output without making quality claims."""

    expected_manifest_sha = manifest.get("manifest_sha256")
    if expected_manifest_sha is not None:
        unhashed_manifest = dict(manifest)
        unhashed_manifest.pop("manifest_sha256", None)
        if expected_manifest_sha != canonical_sha256(unhashed_manifest):
            raise P3ContractError("manifest_digest_mismatch")
    if manifest.get("schema") != MANIFEST_SCHEMA:
        raise P3ContractError("manifest_schema_mismatch")
    if manifest.get("phase") != "P3-A":
        raise P3ContractError("manifest_phase_mismatch")
    if manifest.get("evidence_scope") != "offline_fake_contract_only":
        raise P3ContractError("manifest_scope_mismatch")
    if manifest.get("real_model_calls") != 0 or manifest.get("network_calls") != 0:
        raise P3ContractError("p3a_nonzero_external_call")
    results = manifest.get("results")
    if not isinstance(results, Mapping) or set(results) != set(CONDITIONS):
        raise P3ContractError("manifest_condition_set_mismatch")
    source_hashes = {result.get("source_history_sha256") for result in results.values()}
    input_hashes = {result.get("input_sha256") for result in results.values()}
    if len(source_hashes) != 1 or len(input_hashes) != 1 or None in source_hashes | input_hashes:
        raise P3ContractError("manifest_common_source_mismatch")
    for condition, result in results.items():
        if result.get("condition") != condition:
            raise P3ContractError("manifest_condition_mismatch", condition)
        budget = result.get("budget")
        if not isinstance(budget, Mapping) or budget.get("terminal_failure") is not None:
            raise P3ContractError("manifest_budget_invalid", condition)
        if budget.get("attempts") != budget.get("completed_calls"):
            raise P3ContractError("manifest_incomplete_calls", condition)
        calls = result.get("calls", [])
        if not isinstance(calls, list) or len(calls) != budget.get("completed_calls"):
            raise P3ContractError("manifest_call_count_mismatch", condition)
        prompt_total = 0
        completion_total = 0
        allocation_total = 0
        for call in calls:
            if call.get("content_sha256") != canonical_sha256(call.get("content")):
                raise P3ContractError("manifest_output_digest_mismatch", condition)
            request_sha = call.get("request_sha256")
            if not isinstance(request_sha, str) or len(request_sha) != 64:
                raise P3ContractError("manifest_request_digest_missing", condition)
            usage = call.get("usage")
            if not isinstance(usage, Mapping):
                raise P3ContractError("manifest_call_usage_missing", condition)
            prompt_total += _require_exact_int(
                usage.get("prompt_tokens"), "prompt_tokens"
            )
            completion_total += _require_exact_int(
                usage.get("completion_tokens"), "completion_tokens"
            )
            allocation_total += _require_exact_int(
                call.get("max_completion_tokens"),
                "max_completion_tokens",
                minimum=1,
            )
            if call.get("model") != "qwen2.5:7b":
                raise P3ContractError("manifest_model_mismatch", condition)
            if call.get("network_calls") != 0 or call.get("real_model_calls") != 0:
                raise P3ContractError("manifest_nonzero_call", condition)
        if prompt_total != budget.get("actual_prompt_tokens"):
            raise P3ContractError("manifest_prompt_total_mismatch", condition)
        if completion_total != budget.get("actual_completion_tokens"):
            raise P3ContractError("manifest_completion_total_mismatch", condition)
        if allocation_total != budget.get("allocated_completion_tokens"):
            raise P3ContractError("manifest_allocation_total_mismatch", condition)
    checks = manifest.get("contract_checks")
    if not isinstance(checks, Mapping) or not all(value is True for value in checks.values()):
        raise P3ContractError("manifest_contract_check_failed")


def design_without_metadata(design: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in design.items() if not key.startswith("_")}
