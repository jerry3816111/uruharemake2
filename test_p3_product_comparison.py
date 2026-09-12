from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
import urllib.request

import pytest

from p3_product_comparison import (
    CONDITIONS,
    CaseWorkspaceRegistry,
    FakeExactTokenCounter,
    FakeTransport,
    P3ContractError,
    build_balanced_condition_schedule,
    build_generation_view,
    canonical_sha256,
    freeze_common_source,
    load_design,
    make_request,
    map_blind_scores,
    new_budget,
    record_usage,
    reserve_call,
    run_call_once,
    run_condition,
    validate_common_views,
    validate_run_manifest,
    write_new_json,
)
from run_p3_product_comparison import build_contract_manifest, main
from p3_product_worker import (
    ProductTransportGate,
    build_adapter_contract,
    build_native_call,
    build_openai_call,
    claim_case_workspace,
    install_product_transport_gate,
)


ROOT = Path(__file__).resolve().parent
DESIGN_PATH = ROOT / "configs" / "p3_product_comparison_v1.json"


def source_fixture():
    prefix = [
        {
            "turn_id": "a1",
            "session_id": "session-a",
            "role": "user",
            "content": "前の話を覚えてる？",
        },
        {
            "turn_id": "a2",
            "session_id": "session-a",
            "role": "assistant",
            "content": "うん、急がなくていいって話だろ。",
        },
        {
            "turn_id": "b1",
            "session_id": "session-b",
            "role": "user",
            "content": "今日はまだ決めてない。",
        },
    ]
    current = {
        "turn_id": "b2",
        "session_id": "session-b",
        "content": "今も答えを急がせないで。",
    }
    return prefix, current


def request_for(design, condition, *, stage="unit", prompt=100, cap=128, backend="fake_local"):
    return make_request(
        design=design,
        condition=condition,
        stage=stage,
        messages=[{"role": "user", "content": "fixture"}],
        prompt_tokens=prompt,
        max_completion_tokens=cap,
        backend=backend,
    )


def assert_code(code, callable_):
    with pytest.raises(P3ContractError) as caught:
        callable_()
    assert caught.value.code == code


def test_contract_manifest_runs_three_conditions_with_zero_real_calls():
    manifest = build_contract_manifest(DESIGN_PATH)
    validate_run_manifest(manifest)
    assert set(manifest["results"]) == set(CONDITIONS)
    assert manifest["real_model_calls"] == 0
    assert manifest["network_calls"] == 0
    assert manifest["paid_calls"] == 0
    assert manifest["fake_transport_attempts"] == 5
    assert manifest["contract_checks"]["completed_checkpoint_reused_without_transport"]
    assert manifest["token_evidence_kind"] == "fake_exact_fixture_count"


def test_missing_previous_session_fails_common_source_before_transport():
    prefix, current = source_fixture()
    source = freeze_common_source(prefix, current)
    views = {condition: build_generation_view(prefix, current, condition) for condition in CONDITIONS}
    views["full_history_direct"] = build_generation_view(
        [turn for turn in prefix if turn["session_id"] == "session-b"],
        current,
        "full_history_direct",
    )
    transport = FakeTransport()
    assert_code("common_source_mismatch", lambda: validate_common_views(views, source))
    assert transport.attempts == 0


def test_current_system_reply_or_same_turn_leak_is_rejected():
    prefix, current = source_fixture()
    leaked = prefix + [
        {
            "turn_id": current["turn_id"],
            "session_id": current["session_id"],
            "role": "assistant",
            "content": "当輪のsystem reply",
        }
    ]
    assert_code(
        "current_reply_or_input_leaked",
        lambda: build_generation_view(leaked, current, "full_history_direct"),
    )


@pytest.mark.parametrize("forbidden", ["future", "family", "expected_answer", "scorer"])
def test_generation_view_rejects_annotation_or_future_fields(forbidden):
    prefix, current = source_fixture()
    injected = [dict(prefix[0], **{forbidden: "secret"}), *prefix[1:]]
    assert_code(
        "turn_allowlist_violation",
        lambda: build_generation_view(injected, current, "product_system"),
    )


def test_current_input_annotation_fields_are_rejected():
    prefix, current = source_fixture()
    injected = dict(current, expected_answer="secret", family="hidden")
    assert_code(
        "input_allowlist_violation",
        lambda: build_generation_view(prefix, injected, "full_history_deliberate"),
    )


def test_view_is_new_allowlisted_object_not_case_copy():
    prefix, current = source_fixture()
    view = build_generation_view(prefix, current, "product_system")
    assert set(view) == {
        "schema",
        "condition",
        "visible_prefix",
        "current_input",
        "source_history_sha256",
        "input_sha256",
        "source_sha256",
        "view_sha256",
    }
    assert view["visible_prefix"] is not prefix
    assert view["current_input"] is not current


def test_cross_case_state_path_reuse_is_rejected_but_restart_is_allowed(tmp_path):
    registry = CaseWorkspaceRegistry()
    path = tmp_path / "state"
    first = registry.claim("case-1", path)
    assert registry.claim("case-1", path) == first
    assert_code("cross_case_state_reuse", lambda: registry.claim("case-2", path))


def test_p3_product_worker_state_persists_only_for_the_same_case(tmp_path):
    root = tmp_path / "p3-worker-root"
    first = claim_case_workspace(root, "case-1", state_slot="shared-slot")
    state_probe = first["paths"]["memory"] / "restart-probe.txt"
    state_probe.write_text("kept", encoding="utf-8")
    second = claim_case_workspace(root, "case-1", state_slot="shared-slot")
    assert first["restart"] is False
    assert second["restart"] is True
    assert state_probe.read_text(encoding="utf-8") == "kept"
    assert_code(
        "cross_case_state_reuse",
        lambda: claim_case_workspace(root, "case-2", state_slot="shared-slot"),
    )


def test_p3_product_worker_rejects_existing_unsentinelled_root(tmp_path):
    root = tmp_path / "existing-root"
    root.mkdir()
    assert_code(
        "existing_worker_root_without_sentinel",
        lambda: claim_case_workspace(root, "case-1"),
    )


def test_p3_product_adapter_intercepts_both_routes_with_exact_fake_usage():
    result = build_adapter_contract(DESIGN_PATH)
    assert result["status"] == "offline_transport_contract_pass"
    assert [row["backend"] for row in result["interceptions"]] == [
        "openai_compatible_local",
        "native_ollama_chat",
    ]
    assert result["budget"]["completed_calls"] == 2
    assert result["network_calls"] == result["real_model_calls"] == 0


def test_p3_product_adapter_rejects_option_drift_before_transport():
    design = load_design(DESIGN_PATH)
    gate = ProductTransportGate(design, lambda messages: 100)
    call = build_openai_call(
        design,
        [{"role": "user", "content": "fixture"}],
        128,
    )
    call["temperature"] = 0.2
    attempts = []
    assert_code(
        "openai_product_options_mismatch",
        lambda: gate.intercept_openai(
            stage="option-drift",
            call_kwargs=call,
            transport=lambda kwargs: attempts.append(kwargs),
            contract_fake=True,
        ),
    )
    assert attempts == []
    assert gate.budget.attempts == 0


def test_p3_product_adapter_refuses_unreleased_real_transport_before_call():
    design = load_design(DESIGN_PATH)
    gate = ProductTransportGate(design, lambda messages: 100)
    attempts = []
    assert_code(
        "real_product_transport_not_released",
        lambda: gate.intercept_openai(
            stage="unreleased",
            call_kwargs=build_openai_call(
                design,
                [{"role": "user", "content": "fixture"}],
                128,
            ),
            transport=lambda kwargs: attempts.append(kwargs),
        ),
    )
    assert attempts == []
    assert gate.budget.attempts == 0


def test_p3_product_adapter_transport_failure_is_terminal_no_retry():
    design = load_design(DESIGN_PATH)
    gate = ProductTransportGate(design, lambda messages: 100)
    call = build_openai_call(
        design,
        [{"role": "user", "content": "fixture"}],
        128,
    )
    assert_code(
        "transport_failure_no_retry",
        lambda: gate.intercept_openai(
            stage="transport-failure",
            call_kwargs=call,
            transport=lambda kwargs: (_ for _ in ()).throw(TimeoutError("fixture")),
            contract_fake=True,
        ),
    )
    assert gate.budget.terminal_failure == "transport_failure_no_retry"
    assert_code(
        "budget_terminal",
        lambda: gate.intercept_openai(
            stage="no-retry",
            call_kwargs=call,
            transport=lambda kwargs: {},
            contract_fake=True,
        ),
    )


def test_p3_product_gate_is_bound_to_the_actual_product_global_seams():
    design = load_design(DESIGN_PATH)
    calls = {"openai": 0, "models": 0, "native": 0}

    class DummyCompletions:
        def create(self, **kwargs):
            calls["openai"] += 1
            return {}

    class DummyModels:
        def list(self):
            calls["models"] += 1
            return {}

    def openai_factory(*args, **kwargs):
        return SimpleNamespace(
            chat=SimpleNamespace(completions=DummyCompletions()),
            models=DummyModels(),
        )

    def native_opener(*args, **kwargs):
        calls["native"] += 1
        return None

    brain = SimpleNamespace(
        OpenAI=openai_factory,
        urllib=SimpleNamespace(request=SimpleNamespace(urlopen=native_opener)),
        M31_SEMANTIC_VERIFIER_MODEL="qwen2.5:7b",
        M31_SEMANTIC_VERIFIER_URL="http://localhost:11434/api/chat",
    )
    gate = ProductTransportGate(design, lambda messages: 100)
    binding = install_product_transport_gate(brain, gate)
    assert binding["openai_global_guarded"]
    assert binding["native_urlopen_global_guarded"]

    client = brain.OpenAI(base_url="http://localhost:11434/v1", max_retries=0)
    assert client.models.list()["source"] == "reviewed_preflight_metadata"
    assert calls["models"] == 0
    messages = [{"role": "user", "content": "fixture"}]
    assert_code(
        "real_product_transport_not_released",
        lambda: client.chat.completions.create(
            **build_openai_call(design, messages, 128)
        ),
    )
    native_request = urllib.request.Request(
        brain.M31_SEMANTIC_VERIFIER_URL,
        data=json.dumps(build_native_call(design, messages, 128)).encode("utf-8"),
        method="POST",
    )
    assert_code(
        "real_product_transport_not_released",
        lambda: brain.urllib.request.urlopen(native_request, timeout=18),
    )
    assert calls == {"openai": 0, "models": 0, "native": 0}


def test_p3_product_worker_real_entry_import_is_lazy_and_offline(tmp_path):
    product_python = ROOT / ".venv/product_checks/bin/python"
    output = tmp_path / "p3-b1-preflight.json"
    exit_code = main(
        [
            "--mode",
            "product-dry-run",
            "--design",
            str(DESIGN_PATH),
            "--product-python",
            str(product_python),
            "--output",
            str(output),
        ]
    )
    assert exit_code == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["status"] == "p3_b1_contract_pass"
    assert payload["network_calls"] == payload["real_model_calls"] == 0
    assert all(payload["checks"].values())
    assert payload["first_import"]["brain_instances"] == 0
    assert payload["restart_import"]["restart"] is True
    assert payload["cross_case_refusal"]["contract_code"] == "cross_case_state_reuse"


def test_native_m31_wrong_model_is_rejected_before_transport():
    design = load_design(DESIGN_PATH)
    budget = new_budget(design, "product_system")
    request = request_for(
        design,
        "product_system",
        stage="native_m31",
        backend="native_ollama_chat",
        cap=128,
    )
    request["model"] = "qwen3.5:9b"
    assert_code("model_gate_rejected", lambda: reserve_call(budget, request))
    assert budget.attempts == 0


@pytest.mark.parametrize(
    ("condition", "backend"),
    [
        ("full_history_direct", "openai_compatible_local"),
        ("product_system", "native_ollama_chat"),
    ],
)
def test_both_local_transport_routes_share_the_same_model_gate(
    tmp_path, condition, backend
):
    design = load_design(DESIGN_PATH)
    request = request_for(
        design,
        condition,
        stage=f"route-{backend}",
        backend=backend,
        cap=128,
    )
    transport = FakeTransport()
    result = run_call_once(
        budget=new_budget(design, condition),
        request=request,
        transport=transport,
        checkpoint_root=tmp_path,
        item_id=backend,
    )
    assert result["model"] == "qwen2.5:7b"
    assert result["backend"] == backend
    assert result["real_model_calls"] == 0
    assert transport.attempts == 1


def test_shared_completion_budget_cannot_reset_per_system_call():
    design = load_design(DESIGN_PATH)
    budget = new_budget(design, "product_system")
    reserve_call(budget, request_for(design, "product_system", stage="one", cap=320))
    reserve_call(budget, request_for(design, "product_system", stage="two", cap=320))
    assert_code(
        "aggregate_completion_budget_exceeded",
        lambda: reserve_call(
            budget, request_for(design, "product_system", stage="three", cap=320)
        ),
    )
    assert budget.attempts == 2
    assert budget.allocated_completion_tokens == 640


def test_deliberate_allocations_share_exact_768_total(tmp_path):
    design = load_design(DESIGN_PATH)
    prefix, current = source_fixture()
    view = build_generation_view(prefix, current, "full_history_deliberate")
    transport = FakeTransport()
    result = run_condition(
        condition="full_history_deliberate",
        view=view,
        design=design,
        transport=transport,
        checkpoint_root=tmp_path,
        item_id="item",
        token_counter=FakeExactTokenCounter(),
    )
    assert result["budget"]["allocated_completion_tokens"] == 768
    assert result["budget"]["attempts"] == 3
    assert transport.attempts == 3
    # Draft and critique appear only in later private request scratch, never in source view.
    assert len(view["visible_prefix"]) == 3
    assert result["private_scratch_written_to_visible_history"] is False


def test_condition_runner_revalidates_view_digest_before_transport(tmp_path):
    design = load_design(DESIGN_PATH)
    prefix, current = source_fixture()
    view = build_generation_view(prefix, current, "full_history_direct")
    view["visible_prefix"][0]["content"] = "tampered after freeze"
    transport = FakeTransport()
    assert_code(
        "view_digest_mismatch",
        lambda: run_condition(
            condition="full_history_direct",
            view=view,
            design=design,
            transport=transport,
            checkpoint_root=tmp_path,
            item_id="tampered-view",
            token_counter=FakeExactTokenCounter(),
        ),
    )
    assert transport.attempts == 0


def test_condition_runner_rejects_rehashed_extra_view_fields(tmp_path):
    design = load_design(DESIGN_PATH)
    prefix, current = source_fixture()
    view = build_generation_view(prefix, current, "product_system")
    view["scorer_annotation"] = "must not reach a condition"
    unhashed = dict(view)
    unhashed.pop("view_sha256")
    view["view_sha256"] = canonical_sha256(unhashed)
    transport = FakeTransport()
    assert_code(
        "view_allowlist_violation",
        lambda: run_condition(
            condition="product_system",
            view=view,
            design=design,
            transport=transport,
            checkpoint_root=tmp_path,
            item_id="extra-field",
            token_counter=FakeExactTokenCounter(),
            product_worker=lambda **kwargs: {},
        ),
    )
    assert transport.attempts == 0


def test_contract_retains_exact_per_call_usage_for_budget_audit():
    manifest = build_contract_manifest(DESIGN_PATH)
    for result in manifest["results"].values():
        assert all("request_sha256" in call for call in result["calls"])
        assert all("usage" in call for call in result["calls"])
        assert sum(call["usage"]["prompt_tokens"] for call in result["calls"]) == result[
            "budget"
        ]["actual_prompt_tokens"]
        assert sum(
            call["usage"]["completion_tokens"] for call in result["calls"]
        ) == result["budget"]["actual_completion_tokens"]


def test_condition_wall_includes_non_transport_work_and_fails_closed(tmp_path):
    design = load_design(DESIGN_PATH)
    prefix, current = source_fixture()
    view = build_generation_view(prefix, current, "full_history_direct")
    ticks = iter([100.0, 161.0])
    transport = FakeTransport()
    assert_code(
        "condition_wall_budget_exceeded",
        lambda: run_condition(
            condition="full_history_direct",
            view=view,
            design=design,
            transport=transport,
            checkpoint_root=tmp_path,
            item_id="wall-overflow",
            token_counter=FakeExactTokenCounter(),
            clock=lambda: next(ticks),
        ),
    )
    assert transport.attempts == 1


def test_context_overflow_fails_without_truncation():
    design = load_design(DESIGN_PATH)
    budget = new_budget(design, "full_history_direct")
    request = request_for(design, "full_history_direct", prompt=8000, cap=768)
    assert_code(
        "context_budget_exceeded_no_truncation",
        lambda: reserve_call(budget, request),
    )
    assert budget.attempts == 0


def test_common_history_overflow_fails_without_truncation_or_transport(tmp_path):
    design = load_design(DESIGN_PATH)
    prefix, current = source_fixture()
    view = build_generation_view(prefix, current, "full_history_direct")
    transport = FakeTransport()
    assert_code(
        "common_history_budget_exceeded_no_truncation",
        lambda: run_condition(
            condition="full_history_direct",
            view=view,
            design=design,
            transport=transport,
            checkpoint_root=tmp_path,
            item_id="history-overflow",
            token_counter=lambda messages: 6001,
        ),
    )
    assert transport.attempts == 0


def test_unknown_actual_usage_is_terminal_and_never_character_estimated():
    design = load_design(DESIGN_PATH)
    budget = new_budget(design, "full_history_direct")
    reservation = reserve_call(
        budget, request_for(design, "full_history_direct", prompt=100, cap=128)
    )
    assert_code(
        "invalid_integer",
        lambda: record_usage(
            budget, {"prompt_tokens": None, "completion_tokens": 10, "wall_seconds": 0.1}, reservation
        ),
    )
    assert budget.terminal_failure == "invalid_integer"
    assert_code(
        "budget_terminal",
        lambda: reserve_call(
            budget, request_for(design, "full_history_direct", stage="again", cap=128)
        ),
    )


def test_actual_usage_over_reservation_is_invalid():
    design = load_design(DESIGN_PATH)
    budget = new_budget(design, "product_system")
    reservation = reserve_call(
        budget, request_for(design, "product_system", prompt=100, cap=128)
    )
    assert_code(
        "actual_completion_exceeded_reservation",
        lambda: record_usage(
            budget,
            {"prompt_tokens": 100, "completion_tokens": 129, "wall_seconds": 0.1},
            reservation,
        ),
    )
    assert budget.terminal_failure == "actual_completion_exceeded_reservation"


def test_unavailable_token_counter_stops_before_transport(tmp_path):
    design = load_design(DESIGN_PATH)
    prefix, current = source_fixture()
    view = build_generation_view(prefix, current, "full_history_direct")
    transport = FakeTransport()
    assert_code(
        "token_count_unavailable",
        lambda: run_condition(
            condition="full_history_direct",
            view=view,
            design=design,
            transport=transport,
            checkpoint_root=tmp_path,
            item_id="item",
            token_counter=lambda messages: None,
        ),
    )
    assert transport.attempts == 0


def test_missing_provider_usage_is_persisted_and_never_retried(tmp_path):
    design = load_design(DESIGN_PATH)
    request = request_for(design, "product_system", stage="usage-missing", cap=128)

    class MissingUsageTransport:
        attempts = 0

        def __call__(self, raw_request):
            self.attempts += 1
            return {
                "content": "fixture",
                "usage": {"completion_tokens": 4, "wall_seconds": 0.001},
                "model": raw_request["model"],
                "backend": raw_request["backend"],
                "network_calls": 0,
                "real_model_calls": 0,
            }

    missing = MissingUsageTransport()
    assert_code(
        "invalid_integer",
        lambda: run_call_once(
            budget=new_budget(design, "product_system"),
            request=request,
            transport=missing,
            checkpoint_root=tmp_path,
            item_id="usage-item",
        ),
    )
    failure = json.loads(next(tmp_path.rglob("failure.json")).read_text(encoding="utf-8"))
    assert failure["contract_code"] == "invalid_integer"
    retry = FakeTransport()
    assert_code(
        "intent_without_complete_no_retry",
        lambda: run_call_once(
            budget=new_budget(design, "product_system"),
            request=request,
            transport=retry,
            checkpoint_root=tmp_path,
            item_id="usage-item",
        ),
    )
    assert retry.attempts == 0


def test_transport_timeout_leaves_intent_and_retry_makes_no_call(tmp_path):
    design = load_design(DESIGN_PATH)
    request = request_for(design, "full_history_direct", stage="direct", cap=128)
    failing = FakeTransport(fail_stage="direct")
    assert_code(
        "transport_failure_no_retry",
        lambda: run_call_once(
            budget=new_budget(design, "full_history_direct"),
            request=request,
            transport=failing,
            checkpoint_root=tmp_path,
            item_id="timeout-item",
        ),
    )
    assert failing.attempts == 1
    retry = FakeTransport()
    assert_code(
        "intent_without_complete_no_retry",
        lambda: run_call_once(
            budget=new_budget(design, "full_history_direct"),
            request=request,
            transport=retry,
            checkpoint_root=tmp_path,
            item_id="timeout-item",
        ),
    )
    assert retry.attempts == 0


def test_mutated_complete_checkpoint_is_rejected_without_transport(tmp_path):
    design = load_design(DESIGN_PATH)
    request = request_for(design, "full_history_direct", stage="direct", cap=128)
    run_call_once(
        budget=new_budget(design, "full_history_direct"),
        request=request,
        transport=FakeTransport(),
        checkpoint_root=tmp_path,
        item_id="complete-item",
    )
    complete_path = next(tmp_path.rglob("complete.json"))
    payload = json.loads(complete_path.read_text(encoding="utf-8"))
    payload["result"]["content"] = "mutated"
    unsigned = dict(payload)
    unsigned.pop("record_sha256")
    payload["record_sha256"] = canonical_sha256(unsigned)
    complete_path.write_text(json.dumps(payload), encoding="utf-8")
    transport = FakeTransport()
    assert_code(
        "complete_checkpoint_output_digest_mismatch",
        lambda: run_call_once(
            budget=new_budget(design, "full_history_direct"),
            request=request,
            transport=transport,
            checkpoint_root=tmp_path,
            item_id="complete-item",
        ),
    )
    assert transport.attempts == 0


def test_mutated_source_request_does_not_reuse_checkpoint(tmp_path):
    design = load_design(DESIGN_PATH)
    first = request_for(design, "full_history_direct", stage="direct", cap=128)
    run_call_once(
        budget=new_budget(design, "full_history_direct"),
        request=first,
        transport=FakeTransport(),
        checkpoint_root=tmp_path,
        item_id="source-item",
    )
    changed = request_for(design, "full_history_direct", stage="direct", cap=128)
    changed["messages"] = [{"role": "user", "content": "changed source"}]
    transport = FakeTransport()
    assert_code(
        "complete_checkpoint_source_mismatch",
        lambda: run_call_once(
            budget=new_budget(design, "full_history_direct"),
            request=changed,
            transport=transport,
            checkpoint_root=tmp_path,
            item_id="source-item",
        ),
    )
    assert transport.attempts == 0


def test_output_artifact_is_immutable(tmp_path):
    output = tmp_path / "result.json"
    write_new_json(output, {"value": 1})
    assert_code("artifact_exists_no_overwrite", lambda: write_new_json(output, {"value": 2}))
    assert json.loads(output.read_text(encoding="utf-8")) == {"value": 1}


def test_run_mode_without_releases_refuses_before_transport(tmp_path):
    output = tmp_path / "run-refusal.json"
    exit_code = main(
        ["--mode", "run", "--design", str(DESIGN_PATH), "--output", str(output)]
    )
    assert exit_code != 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["status"] == "refused_before_transport"
    assert payload["transport_attempts"] == 0
    assert payload["real_model_calls"] == 0
    assert "review_release_missing" in payload["reasons"]


def test_contract_cli_refuses_to_overwrite_existing_output(tmp_path):
    output = tmp_path / "contract.json"
    assert main(
        ["--mode", "contract", "--design", str(DESIGN_PATH), "--output", str(output)]
    ) == 0
    first_sha = canonical_sha256(json.loads(output.read_text(encoding="utf-8")))
    assert main(
        ["--mode", "contract", "--design", str(DESIGN_PATH), "--output", str(output)]
    ) != 0
    assert canonical_sha256(json.loads(output.read_text(encoding="utf-8"))) == first_sha


def test_anonymous_ab_ba_mapping_and_numeric_direction_are_symmetric():
    ab = map_blind_scores("AB", 2.0, 1.0, "product_system", "full_history_direct")
    ba = map_blind_scores("BA", 1.0, 2.0, "product_system", "full_history_direct")
    assert ab == ba == {"product_system": 2.0, "full_history_direct": 1.0}
    assert (2.0 - 1.0) == -(1.0 - 2.0)


def test_six_case_schedule_balances_every_condition_in_every_position():
    case_ids = [f"case-{index}" for index in range(6)]
    schedule = build_balanced_condition_schedule(case_ids, 20260909)
    assert schedule == build_balanced_condition_schedule(case_ids, 20260909)
    assert all(set(order) == set(CONDITIONS) for order in schedule.values())
    for position in range(3):
        counts = {condition: 0 for condition in CONDITIONS}
        for order in schedule.values():
            counts[order[position]] += 1
        assert set(counts.values()) == {2}


def test_manifest_detects_output_tampering_even_if_outer_hash_is_recomputed():
    manifest = build_contract_manifest(DESIGN_PATH)
    manifest["results"]["full_history_direct"]["calls"][0]["content"] = "mutated"
    unsigned = dict(manifest)
    unsigned.pop("manifest_sha256")
    manifest["manifest_sha256"] = canonical_sha256(unsigned)
    assert_code("manifest_output_digest_mismatch", lambda: validate_run_manifest(manifest))
