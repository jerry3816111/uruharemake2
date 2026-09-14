from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
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
    build_smoke_generation_view,
    canonical_sha256,
    freeze_common_source,
    load_design,
    load_developer_smoke_manifests,
    load_product_canary,
    load_tokenizer_binding_probe,
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
    ProductCallShapeObserver,
    build_adapter_contract,
    build_native_call,
    build_openai_call,
    build_tokenizer_probe_contract,
    build_tokenizer_probe_preflight,
    build_stage_tokenizer_probe_contract,
    build_stage_tokenizer_probe_preflight,
    build_canary_baselines_preflight,
    build_product_canary_preflight,
    claim_case_workspace,
    execute_tokenizer_binding_probe,
    execute_stage_tokenizer_binding_probe,
    execute_canary_baselines,
    install_product_transport_gate,
    normalize_product_native_call,
    normalize_product_openai_call,
    load_canary_baselines,
    load_stage_tokenizer_binding_probe,
    summarize_checkpoint_evidence,
)


ROOT = Path(__file__).resolve().parent
DESIGN_PATH = ROOT / "configs" / "p3_product_comparison_v1.json"
SMOKE_SOURCE_PATH = ROOT / "datasets" / "p3_developer_smoke_source_v1.json"
SMOKE_ANNOTATION_PATH = ROOT / "datasets" / "p3_developer_smoke_annotations_v1.json"
TOKEN_PROBE_PATH = ROOT / "configs" / "p3_tokenizer_binding_probe_v1.json"
TOKEN_PROBE_RELEASE_PATH = (
    ROOT / "research" / "p3_b3_tokenizer_binding_probe_execution_release_2026-09-14.json"
)
TOKEN_PROBE_RESULT_PATH = (
    ROOT / "analysis" / "p3_b3_tokenizer_binding_probe_result_2026-09-14.json"
)
PRODUCT_CANARY_PATH = ROOT / "configs" / "p3_product_canary_v1.json"
CANARY_BASELINES_PATH = ROOT / "configs" / "p3_canary_baselines_v1.json"
STAGE_TOKEN_PROBE_PATH = (
    ROOT / "configs" / "p3_stage_tokenizer_binding_probe_v1.json"
)


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


def write_smoke_pair(tmp_path, source, annotations):
    repo = tmp_path / "repo"
    datasets = repo / "datasets"
    research = repo / "research"
    datasets.mkdir(parents=True)
    research.mkdir(parents=True)
    release_name = "p3_b1_product_worker_release_2026-09-13.json"
    (research / release_name).write_bytes((ROOT / "research" / release_name).read_bytes())
    source_path = datasets / "p3_developer_smoke_source_v1.json"
    annotation_path = datasets / "p3_developer_smoke_annotations_v1.json"
    source_path.write_text(
        json.dumps(source, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    annotations["source_manifest_sha256"] = hashlib.sha256(
        source_path.read_bytes()
    ).hexdigest()
    annotation_path.write_text(
        json.dumps(annotations, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return source_path, annotation_path


def write_token_probe(tmp_path, config):
    repo = tmp_path / "repo"
    configs = repo / "configs"
    research = repo / "research"
    configs.mkdir(parents=True)
    research.mkdir(parents=True)
    (configs / "p3_product_comparison_v1.json").write_bytes(DESIGN_PATH.read_bytes())
    freeze_name = "p3_b2_developer_smoke_data_freeze_2026-09-13.json"
    (research / freeze_name).write_bytes((ROOT / "research" / freeze_name).read_bytes())
    probe_path = configs / "p3_tokenizer_binding_probe_v1.json"
    probe_path.write_text(
        json.dumps(config, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return probe_path


def write_product_canary(tmp_path, config):
    repo = tmp_path / "repo"
    for folder in ("configs", "datasets", "analysis"):
        (repo / folder).mkdir(parents=True, exist_ok=True)
    (repo / "configs" / "p3_product_comparison_v1.json").write_bytes(
        DESIGN_PATH.read_bytes()
    )
    (repo / "datasets" / "p3_product_canary_source_v1.json").write_bytes(
        (ROOT / "datasets" / "p3_product_canary_source_v1.json").read_bytes()
    )
    (repo / "analysis" / "p3_b3_tokenizer_binding_probe_result_2026-09-14.json").write_bytes(
        TOKEN_PROBE_RESULT_PATH.read_bytes()
    )
    path = repo / "configs" / "p3_product_canary_v1.json"
    path.write_text(
        json.dumps(config, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


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
        "openai_product_temperature_mismatch",
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


def test_p3_product_gate_rejects_provider_prompt_count_drift():
    design = load_design(DESIGN_PATH)
    gate = ProductTransportGate(design, lambda messages: 100)
    messages = [{"role": "user", "content": "fixture"}]
    assert_code(
        "provider_prompt_count_mismatch",
        lambda: gate.intercept_native(
            stage="provider-count-drift",
            request_body=build_native_call(design, messages, 128),
            transport=lambda body: {
                "model": "qwen2.5:7b",
                "message": {"content": "うん。"},
                "prompt_eval_count": 101,
                "eval_count": 1,
            },
            contract_fake=True,
        ),
    )
    assert gate.budget.terminal_failure == "provider_prompt_count_mismatch"


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


def test_p3_native_bound_seam_sends_the_normalized_body_to_transport():
    design = load_design(DESIGN_PATH)
    captured = {}

    class Response:
        def __init__(self, payload):
            self.payload = payload

        def read(self):
            return self.payload

        def close(self):
            pass

    def native_opener(request, **kwargs):
        captured["body"] = json.loads(request.data.decode("utf-8"))
        return Response(
            json.dumps(
                {
                    "model": "qwen2.5:7b",
                    "message": {"content": "うん。"},
                    "prompt_eval_count": 100,
                    "eval_count": 1,
                }
            ).encode("utf-8")
        )

    brain = SimpleNamespace(
        OpenAI=lambda *args, **kwargs: None,
        urllib=SimpleNamespace(request=SimpleNamespace(urlopen=native_opener)),
        M31_SEMANTIC_VERIFIER_MODEL="qwen2.5:7b",
        M31_SEMANTIC_VERIFIER_URL="http://localhost:11434/api/chat",
    )
    gate = ProductTransportGate(
        design,
        lambda messages: 100,
        allow_real_transport=True,
        provider_binding_verified=True,
    )
    install_product_transport_gate(brain, gate)
    messages = [{"role": "user", "content": "fixture"}]
    original = {
        "model": "qwen2.5:7b",
        "messages": messages,
        "stream": False,
        "think": False,
        "options": {"temperature": 0, "num_predict": 128},
    }
    request = urllib.request.Request(
        brain.M31_SEMANTIC_VERIFIER_URL,
        data=json.dumps(original).encode("utf-8"),
        method="POST",
    )
    response = brain.urllib.request.urlopen(request, timeout=18)
    assert json.loads(response.read().decode("utf-8"))["message"]["content"] == "うん。"
    assert captured["body"] == build_native_call(design, messages, 128)
    assert gate.interceptions[0]["normalization"]["inserted_fields"] == [
        "options.seed",
        "options.top_p",
        "options.num_ctx",
    ]


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


def test_p3_smoke_source_and_annotations_are_balanced_and_separate():
    loaded = load_developer_smoke_manifests(
        SMOKE_SOURCE_PATH,
        SMOKE_ANNOTATION_PATH,
        load_design(DESIGN_PATH),
    )
    summary = loaded["summary"]
    assert summary["case_count"] == 6
    assert summary["turn_count"] == 24
    assert summary["session_count"] == 12
    assert set(summary["family_counts"].values()) == {1}
    assert summary["language_counts"] == {"en": 2, "ja": 2, "zh": 2}
    assert summary["content_hash_count"] == 24
    assert summary["scenario_concept_count"] == 6


def test_p3_smoke_generation_views_use_only_visible_source_and_system_prefix():
    loaded = load_developer_smoke_manifests(
        SMOKE_SOURCE_PATH,
        SMOKE_ANNOTATION_PATH,
        load_design(DESIGN_PATH),
    )
    for case in loaded["source"]["cases"]:
        prior = {}
        for turn_number, turn in enumerate(case["turns"], 1):
            views = {
                condition: build_smoke_generation_view(
                    case,
                    turn_number,
                    condition,
                    prior,
                )
                for condition in CONDITIONS
            }
            commitment = freeze_common_source(
                views["product_system"]["visible_prefix"],
                views["product_system"]["current_input"],
            )
            validate_common_views(views, commitment)
            assert all(
                len(view["visible_prefix"]) == 2 * (turn_number - 1)
                for view in views.values()
            )
            serialized = json.dumps(views, ensure_ascii=False)
            assert "preferred_response_behaviors" not in serialized
            assert "unacceptable_unsupported_claims" not in serialized
            assert "pragmatic_possibilities" not in serialized
            prior[turn["turn_id"]] = f"検証用の過去返答{turn_number}。"


def test_p3_smoke_source_rejects_gold_or_future_field_even_with_rebound_hash(tmp_path):
    source = json.loads(SMOKE_SOURCE_PATH.read_text(encoding="utf-8"))
    annotations = json.loads(SMOKE_ANNOTATION_PATH.read_text(encoding="utf-8"))
    source["cases"][0]["expected_answer"] = "leak"
    source_path, annotation_path = write_smoke_pair(tmp_path, source, annotations)
    assert_code(
        "smoke_source_case_allowlist",
        lambda: load_developer_smoke_manifests(
            source_path, annotation_path, load_design(DESIGN_PATH)
        ),
    )


def test_p3_smoke_source_rejects_changed_content_with_stale_digest(tmp_path):
    source = json.loads(SMOKE_SOURCE_PATH.read_text(encoding="utf-8"))
    annotations = json.loads(SMOKE_ANNOTATION_PATH.read_text(encoding="utf-8"))
    source["cases"][0]["turns"][0]["content"] += " tampered"
    source_path, annotation_path = write_smoke_pair(tmp_path, source, annotations)
    assert_code(
        "smoke_turn_content_digest_mismatch",
        lambda: load_developer_smoke_manifests(
            source_path, annotation_path, load_design(DESIGN_PATH)
        ),
    )


def test_p3_smoke_view_rechecks_source_digest_after_load():
    loaded = load_developer_smoke_manifests(
        SMOKE_SOURCE_PATH,
        SMOKE_ANNOTATION_PATH,
        load_design(DESIGN_PATH),
    )
    case = loaded["source"]["cases"][0]
    case["turns"][0]["content"] += " tampered after validation"
    assert_code(
        "smoke_turn_content_digest_mismatch",
        lambda: build_smoke_generation_view(case, 1, "product_system", {}),
    )


def test_p3_smoke_annotations_reject_future_evidence(tmp_path):
    source = json.loads(SMOKE_SOURCE_PATH.read_text(encoding="utf-8"))
    annotations = json.loads(SMOKE_ANNOTATION_PATH.read_text(encoding="utf-8"))
    annotations["cases"][0]["turns"][0]["visible_evidence_turn_ids"].append(
        "p3-smoke-01-u2"
    )
    source_path, annotation_path = write_smoke_pair(tmp_path, source, annotations)
    assert_code(
        "smoke_annotation_future_evidence",
        lambda: load_developer_smoke_manifests(
            source_path, annotation_path, load_design(DESIGN_PATH)
        ),
    )


def test_p3_smoke_annotations_reject_span_not_in_visible_source(tmp_path):
    source = json.loads(SMOKE_SOURCE_PATH.read_text(encoding="utf-8"))
    annotations = json.loads(SMOKE_ANNOTATION_PATH.read_text(encoding="utf-8"))
    annotations["cases"][0]["turns"][0]["exact_source_spans"] = [
        "not present in any visible source"
    ]
    source_path, annotation_path = write_smoke_pair(tmp_path, source, annotations)
    assert_code(
        "smoke_annotation_span_not_in_source",
        lambda: load_developer_smoke_manifests(
            source_path, annotation_path, load_design(DESIGN_PATH)
        ),
    )


def test_p3_smoke_rejects_translation_reskin_declaration(tmp_path):
    source = json.loads(SMOKE_SOURCE_PATH.read_text(encoding="utf-8"))
    annotations = json.loads(SMOKE_ANNOTATION_PATH.read_text(encoding="utf-8"))
    source["cases"][1]["derivation"]["translation_of"] = "p3-smoke-source-01"
    source_path, annotation_path = write_smoke_pair(tmp_path, source, annotations)
    assert_code(
        "smoke_derivation_not_disjoint",
        lambda: load_developer_smoke_manifests(
            source_path, annotation_path, load_design(DESIGN_PATH)
        ),
    )


def test_p3_smoke_rejects_annotation_cross_case_identity(tmp_path):
    source = json.loads(SMOKE_SOURCE_PATH.read_text(encoding="utf-8"))
    annotations = json.loads(SMOKE_ANNOTATION_PATH.read_text(encoding="utf-8"))
    annotations["cases"][0]["case_id"] = "p3-smoke-tentative-refusal-en"
    source_path, annotation_path = write_smoke_pair(tmp_path, source, annotations)
    assert_code(
        "smoke_annotation_identity_mismatch",
        lambda: load_developer_smoke_manifests(
            source_path, annotation_path, load_design(DESIGN_PATH)
        ),
    )


def test_p3_smoke_view_rejects_future_system_reply():
    loaded = load_developer_smoke_manifests(
        SMOKE_SOURCE_PATH,
        SMOKE_ANNOTATION_PATH,
        load_design(DESIGN_PATH),
    )
    case = loaded["source"]["cases"][0]
    assert_code(
        "smoke_prior_system_reply_set_mismatch",
        lambda: build_smoke_generation_view(
            case,
            1,
            "product_system",
            {case["turns"][0]["turn_id"]: "future leak"},
        ),
    )


def test_p3_smoke_data_validation_cli_builds_all_views_without_generation(tmp_path):
    output = tmp_path / "p3-b2-data-validation.json"
    exit_code = main(
        [
            "--mode",
            "smoke-data-validate",
            "--design",
            str(DESIGN_PATH),
            "--smoke-source",
            str(SMOKE_SOURCE_PATH),
            "--smoke-annotations",
            str(SMOKE_ANNOTATION_PATH),
            "--output",
            str(output),
        ]
    )
    assert exit_code == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["status"] == "p3_b2_data_contract_pass"
    assert payload["generation_view_count"] == 72
    assert payload["network_calls"] == payload["real_model_calls"] == 0
    assert all(payload["checks"].values())


def test_p3_tokenizer_binding_probe_is_fixed_and_non_authorizing():
    probe = load_tokenizer_binding_probe(TOKEN_PROBE_PATH)
    assert probe["status"] == "preregistered_not_executed"
    assert len(probe["fixtures"]) == 4
    assert [fixture["role"] for fixture in probe["fixtures"]] == [
        "fit",
        "fit",
        "fit",
        "verification",
    ]
    assert probe["execution_boundary"]["expected_provider_calls"] == 8
    assert probe["execution_boundary"]["real_model_calls_authorized_by_this_config"] is False
    assert probe["fit_and_verification"]["tolerance_tokens"] == 0


def test_p3_tokenizer_binding_probe_result_is_bound_to_frozen_release_and_scope():
    release = json.loads(TOKEN_PROBE_RELEASE_PATH.read_text(encoding="utf-8"))
    result = json.loads(TOKEN_PROBE_RESULT_PATH.read_text(encoding="utf-8"))
    assert release["authorization"]["provider_calls_exact"] == 8
    assert release["authorization"]["developer_smoke_access"] is False
    assert release["authorization"]["production_database_access"] is False
    assert result["release_sha256"] == hashlib.sha256(
        TOKEN_PROBE_RELEASE_PATH.read_bytes()
    ).hexdigest()
    assert result["status"] == "provider_binding_pass"
    assert result["provider_call_evidence"] == 8


def test_p3_product_canary_is_first_turn_fixed_and_non_authorizing():
    canary = load_product_canary(PRODUCT_CANARY_PATH)
    assert canary["selection"] == {
        "rule": "first_case_first_turn_in_frozen_source_manifest",
        "case_id": "p3-smoke-need-change-zh",
        "turn_id": "p3-smoke-01-u1",
        "content_sha256": "75701b9635c545bb6ec8a36d1f4d26be2981ccc6c21dfc9c0ca7eb65b236d55e",
    }
    assert canary["_source"]["visible_prefix"] == []
    assert canary["_source"]["future_turns_included"] is False
    assert canary["_source"]["annotations_included"] is False
    assert canary["access_boundary"]["real_model_calls_authorized_by_this_config"] is False


def test_p3_product_canary_rejects_selection_or_authorization_drift(tmp_path):
    config = json.loads(PRODUCT_CANARY_PATH.read_text(encoding="utf-8"))
    config["selection"]["turn_id"] = "p3-smoke-01-u2"
    path = write_product_canary(tmp_path / "selection", config)
    assert_code("product_canary_selection_mismatch", lambda: load_product_canary(path))

    config = json.loads(PRODUCT_CANARY_PATH.read_text(encoding="utf-8"))
    config["access_boundary"]["real_model_calls_authorized_by_this_config"] = True
    path = write_product_canary(tmp_path / "authorization", config)
    assert_code(
        "product_canary_access_boundary_mismatch",
        lambda: load_product_canary(path),
    )


def test_p3_product_canary_preflight_reads_no_annotations_or_generation():
    preflight = build_product_canary_preflight(PRODUCT_CANARY_PATH)
    assert preflight["status"] == "ready_for_single_product_canary_review"
    assert preflight["annotations_accessed"] is False
    assert preflight["runtime_future_turn_access_authorized"] is False
    assert preflight["network_calls"] == preflight["real_model_calls"] == 0
    assert all(preflight["checks"].values())


def test_p3_canary_baselines_are_fixed_same_model_and_non_authorizing():
    config = load_canary_baselines(CANARY_BASELINES_PATH)
    assert config["conditions"] == [
        "full_history_direct",
        "full_history_deliberate",
    ]
    assert config["generation"]["model"] == config["_design"]["model"][
        "generation_model"
    ]
    assert config["generation"]["direct_completion_cap"] == 768
    assert sum(config["generation"]["deliberate_completion_caps"]) == 768
    assert config["execution_boundary"]["provider_calls_exact"] == 4
    assert config["execution_boundary"][
        "real_model_calls_authorized_by_this_config"
    ] is False


def test_p3_canary_baselines_preflight_reads_no_labels_or_generation():
    preflight = build_canary_baselines_preflight(CANARY_BASELINES_PATH)
    assert preflight["status"] == "ready_for_canary_baselines_review"
    assert preflight["network_calls"] == preflight["real_model_calls"] == 0
    assert preflight["future_turns_accessed"] == 0
    assert preflight["annotations_accessed"] == 0
    assert preflight["empty_visible_prefix_tokens"] == 0
    assert len(set(preflight["view_sha256"].values())) == 2
    assert all(preflight["checks"].values())


def test_p3_canary_baselines_contract_uses_four_crash_safe_calls(tmp_path):
    config = load_canary_baselines(CANARY_BASELINES_PATH)

    class ExactZeroNetworkTransport:
        def __init__(self):
            self.requests = []

        def __call__(self, request):
            self.requests.append(request)
            return {
                "content": f"固定出力-{request['stage']}",
                "usage": {
                    "prompt_tokens": request["prompt_tokens"],
                    "completion_tokens": 4,
                    "wall_seconds": 0.001,
                },
                "model": request["model"],
                "backend": request["backend"],
                "network_calls": 0,
                "real_model_calls": 0,
            }

    transport = ExactZeroNetworkTransport()
    result = execute_canary_baselines(
        config=config,
        token_counter=FakeExactTokenCounter(),
        transport=transport,
        checkpoint_root=tmp_path,
        evidence_kind="contract_fake",
    )
    assert result["status"] == "offline_canary_baselines_contract_pass"
    assert [request["stage"] for request in transport.requests] == [
        "direct",
        "draft",
        "critique",
        "revise",
    ]
    assert result["provider_call_evidence"] == 0
    assert result["real_model_calls"] == result["network_calls"] == 0
    assert len(list(tmp_path.rglob("intent.json"))) == 4
    assert len(list(tmp_path.rglob("complete.json"))) == 4
    assert all(result["checks"].values())


def test_provider_prompt_drift_is_terminal_before_completion(tmp_path):
    design = load_design(DESIGN_PATH)
    request = request_for(
        design,
        "full_history_direct",
        stage="prompt-drift",
        backend="openai_compatible_local",
    )

    def drift(raw_request):
        return {
            "content": "fixture",
            "usage": {
                "prompt_tokens": raw_request["prompt_tokens"] + 1,
                "completion_tokens": 4,
                "wall_seconds": 0.001,
            },
            "model": raw_request["model"],
            "backend": raw_request["backend"],
            "network_calls": 0,
            "real_model_calls": 0,
        }

    assert_code(
        "provider_prompt_count_mismatch",
        lambda: run_call_once(
            budget=new_budget(design, "full_history_direct"),
            request=request,
            transport=drift,
            checkpoint_root=tmp_path,
            item_id="prompt-drift",
        ),
    )
    failure = json.loads(next(tmp_path.rglob("failure.json")).read_text(encoding="utf-8"))
    assert failure["contract_code"] == "provider_prompt_count_mismatch"
    assert failure["transport_attempted"] is True
    assert failure["response_received"] is True
    assert failure["declared_reservation"] == {
        "prompt_tokens": request["prompt_tokens"],
        "max_completion_tokens": request["max_completion_tokens"],
    }
    assert failure["provider_actual_usage"] == {
        "prompt_tokens": request["prompt_tokens"] + 1,
        "completion_tokens": 4,
        "measured_wall_seconds": failure["provider_actual_usage"][
            "measured_wall_seconds"
        ],
        "network_calls": 0,
        "real_model_calls": 0,
    }
    summary = summarize_checkpoint_evidence(tmp_path)
    assert summary["declared_invocation_intents"] == 1
    assert summary["completed_calls"] == 0
    assert summary["terminal_failures"] == 1
    assert summary["post_transport_failures"] == 1
    assert summary["declared_prompt_tokens"] == request["prompt_tokens"]
    assert summary["provider_prompt_tokens_observed"] == request["prompt_tokens"] + 1
    assert summary["provider_completion_tokens_observed"] == 4
    assert not list(tmp_path.rglob("complete.json"))


def test_p3_tokenizer_binding_probe_rejects_remote_transport(tmp_path):
    config = json.loads(TOKEN_PROBE_PATH.read_text(encoding="utf-8"))
    config["transports"][0]["url"] = "https://example.com/v1/chat/completions"
    path = write_token_probe(tmp_path, config)
    assert_code(
        "token_probe_transport_mismatch",
        lambda: load_tokenizer_binding_probe(path),
    )


def test_p3_tokenizer_binding_probe_rejects_fixture_change_after_freeze(tmp_path):
    config = json.loads(TOKEN_PROBE_PATH.read_text(encoding="utf-8"))
    config["fixtures"][3]["messages"][-1]["content"] += " changed"
    path = write_token_probe(tmp_path, config)
    assert_code(
        "token_probe_messages_digest_mismatch",
        lambda: load_tokenizer_binding_probe(path),
    )


def test_p3_tokenizer_binding_probe_rejects_tolerance_or_fit_change(tmp_path):
    config = json.loads(TOKEN_PROBE_PATH.read_text(encoding="utf-8"))
    config["fit_and_verification"]["tolerance_tokens"] = 1
    path = write_token_probe(tmp_path, config)
    assert_code(
        "token_probe_fit_contract_mismatch",
        lambda: load_tokenizer_binding_probe(path),
    )


def test_p3_tokenizer_binding_probe_rejects_self_authorized_generation(tmp_path):
    config = json.loads(TOKEN_PROBE_PATH.read_text(encoding="utf-8"))
    config["execution_boundary"]["real_model_calls_authorized_by_this_config"] = True
    path = write_token_probe(tmp_path, config)
    assert_code(
        "token_probe_execution_boundary_mismatch",
        lambda: load_tokenizer_binding_probe(path),
    )


def test_p3_tokenizer_probe_preflight_counts_all_fixtures_without_generation():
    preflight = build_tokenizer_probe_preflight(TOKEN_PROBE_PATH)
    assert preflight["status"] == "ready_for_execution_review"
    assert len(preflight["fixture_counts"]) == 4
    assert all(row["hf_prompt_tokens"] > 0 for row in preflight["fixture_counts"])
    assert preflight["model_metadata"]["digest"] == (
        "2bada8a7450677000f678be90653b85d364de7db25eb5ea54136ada5f3933730"
    )
    assert preflight["real_model_calls"] == preflight["network_generation_calls"] == 0
    assert all(preflight["checks"].values())


def test_p3_stage_tokenizer_probe_preflight_covers_assistant_continuations():
    preflight = build_stage_tokenizer_probe_preflight(STAGE_TOKEN_PROBE_PATH)
    assert preflight["status"] == "ready_for_stage_tokenizer_probe_review"
    assert [row["stage"] for row in preflight["fixture_counts"]] == [
        "direct", "draft", "critique", "revise"
    ]
    assert {
        row["stage"]: row["candidate_correction_tokens"]
        for row in preflight["fixture_counts"]
    } == {"direct": 0, "draft": 0, "critique": -5, "revise": -5}
    assert preflight["real_model_calls"] == preflight["network_calls"] == 0
    assert all(preflight["checks"].values())


def test_p3_stage_tokenizer_probe_fake_contract_is_exact_and_raw_text_free(
    tmp_path,
):
    result = build_stage_tokenizer_probe_contract(
        STAGE_TOKEN_PROBE_PATH, tmp_path / "stage-checkpoints"
    )
    assert result["status"] == "offline_stage_tokenizer_contract_pass"
    assert result["stage_offsets"] == {
        "critique": 0,
        "direct": 0,
        "draft": 0,
        "revise": 0,
    }
    assert result["declared_invocation_intents"] == 4
    assert result["completed_calls"] == 4
    assert result["real_model_calls"] == result["network_calls"] == 0
    assert all(result["checks"].values())
    checkpoint_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (tmp_path / "stage-checkpoints").rglob("*.json")
    )
    assert "discard-stage" not in checkpoint_text


def test_p3_stage_tokenizer_probe_retains_one_shape_mismatch(tmp_path):
    probe = load_stage_tokenizer_binding_probe(STAGE_TOKEN_PROBE_PATH)

    def counter(messages):
        return 100 + len(messages)

    def drift(fixture, raw_probe):
        extra = 1 if fixture["stage"] == "revise" else 0
        return {
            "backend": "openai_compatible_local",
            "model": raw_probe["model"]["ollama_model"],
            "prompt_tokens": counter(fixture["messages"]) + extra,
            "completion_tokens": 1,
            "content": "discarded",
            "real_model_calls": 0,
            "network_calls": 0,
        }

    result = execute_stage_tokenizer_binding_probe(
        probe=probe,
        token_counter=counter,
        transport=drift,
        checkpoint_root=tmp_path / "stage-mismatch",
        evidence_kind="contract_fake",
    )
    assert result["status"] == "stage_binding_failed_retained"
    assert result["checks"]["fit_rows_exact"] is True
    assert result["checks"]["verification_row_exact"] is False
    assert result["stage_offsets"]["revise"] == 1
    assert result["binding_verified"] is False


def test_p3_tokenizer_probe_fake_contract_is_exact_and_raw_text_free(tmp_path):
    result = build_tokenizer_probe_contract(TOKEN_PROBE_PATH, tmp_path / "checkpoints")
    assert result["status"] == "offline_tokenizer_contract_pass"
    assert result["transport_offsets"] == {
        "openai_compatible_local": 2,
        "native_ollama_chat": 2,
    }
    assert result["real_model_calls"] == result["network_calls"] == 0
    assert len(result["rows"]) == 8
    assert all("content" not in row for row in result["rows"])
    checkpoint_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (tmp_path / "checkpoints").rglob("*.json")
    )
    assert "contract-output" not in checkpoint_text


def test_p3_tokenizer_probe_retains_nonconstant_offset_as_failed_result(tmp_path):
    probe = load_tokenizer_binding_probe(TOKEN_PROBE_PATH)

    def counter(messages):
        return 100 + len(messages)

    verification_id = probe["fit_and_verification"]["verification_fixture_ids"][0]

    def fake(backend):
        def transport(fixture, raw_probe):
            extra = 3 if fixture["fixture_id"] == verification_id else 2
            return {
                "backend": backend,
                "model": raw_probe["model"]["ollama_model"],
                "prompt_tokens": counter(fixture["messages"]) + extra,
                "completion_tokens": 1,
                "content": "fixture",
                "real_model_calls": 0,
                "network_calls": 0,
            }

        return transport

    result = execute_tokenizer_binding_probe(
        probe=probe,
        token_counter=counter,
        transports={
            backend: fake(backend)
            for backend in ("openai_compatible_local", "native_ollama_chat")
        },
        checkpoint_root=tmp_path / "mismatch",
        evidence_kind="contract_fake",
    )
    assert result["status"] == "binding_failed_retained"
    assert not all(result["verification_exact"].values())
    assert result["binding_verified"] is False


def test_p3_tokenizer_probe_transport_failure_cannot_retry(tmp_path):
    probe = load_tokenizer_binding_probe(TOKEN_PROBE_PATH)
    attempts = {"count": 0}

    def counter(messages):
        return 100

    def fail(fixture, raw_probe):
        attempts["count"] += 1
        raise TimeoutError("fixture")

    transports = {
        "openai_compatible_local": fail,
        "native_ollama_chat": fail,
    }
    root = tmp_path / "no-retry"
    assert_code(
        "token_probe_transport_failure_no_retry",
        lambda: execute_tokenizer_binding_probe(
            probe=probe,
            token_counter=counter,
            transports=transports,
            checkpoint_root=root,
            evidence_kind="contract_fake",
        ),
    )
    assert attempts["count"] == 1
    assert_code(
        "token_probe_intent_without_complete_no_retry",
        lambda: execute_tokenizer_binding_probe(
            probe=probe,
            token_counter=counter,
            transports=transports,
            checkpoint_root=root,
            evidence_kind="contract_fake",
        ),
    )
    assert attempts["count"] == 1


def test_p3_tokenizer_probe_local_evidence_must_be_exact_and_survives_reuse(tmp_path):
    probe = load_tokenizer_binding_probe(TOKEN_PROBE_PATH)

    def counter(messages):
        return 100 + len(messages)

    def local(backend):
        def transport(fixture, raw_probe):
            return {
                "backend": backend,
                "model": raw_probe["model"]["ollama_model"],
                "prompt_tokens": counter(fixture["messages"]) + 2,
                "completion_tokens": 1,
                "content": "discarded",
                "real_model_calls": 1,
                "network_calls": 1,
            }

        return transport

    root = tmp_path / "local-evidence"
    transports = {
        backend: local(backend)
        for backend in ("openai_compatible_local", "native_ollama_chat")
    }
    first = execute_tokenizer_binding_probe(
        probe=probe,
        token_counter=counter,
        transports=transports,
        checkpoint_root=root,
        evidence_kind="local_ollama_provider_usage",
    )
    assert first["status"] == "provider_binding_pass"
    assert first["provider_call_evidence"] == first["real_model_calls"] == 8
    assert all(not row["reused"] for row in first["rows"])

    def forbidden(fixture, raw_probe):
        raise AssertionError("complete checkpoints must prevent a second provider call")

    reused = execute_tokenizer_binding_probe(
        probe=probe,
        token_counter=counter,
        transports={backend: forbidden for backend in transports},
        checkpoint_root=root,
        evidence_kind="local_ollama_provider_usage",
    )
    assert reused["status"] == "provider_binding_pass"
    assert reused["provider_call_evidence"] == 8
    assert reused["real_model_calls"] == reused["network_calls"] == 0
    assert all(row["reused"] for row in reused["rows"])


def test_p3_tokenizer_probe_cannot_label_zero_call_rows_as_provider_evidence(tmp_path):
    probe = load_tokenizer_binding_probe(TOKEN_PROBE_PATH)

    def counter(messages):
        return 100 + len(messages)

    def fake(backend):
        def transport(fixture, raw_probe):
            return {
                "backend": backend,
                "model": raw_probe["model"]["ollama_model"],
                "prompt_tokens": counter(fixture["messages"]) + 2,
                "completion_tokens": 1,
                "content": "fixture",
                "real_model_calls": 0,
                "network_calls": 0,
            }

        return transport

    result = execute_tokenizer_binding_probe(
        probe=probe,
        token_counter=counter,
        transports={
            backend: fake(backend)
            for backend in ("openai_compatible_local", "native_ollama_chat")
        },
        checkpoint_root=tmp_path / "false-provider",
        evidence_kind="local_ollama_provider_usage",
    )
    assert result["status"] == "binding_failed_retained"
    assert result["provider_call_evidence"] == 0
    assert result["checks"]["provider_call_evidence_exact_for_scope"] is False
    assert result["binding_verified"] is False


def test_p3_tokenizer_probe_invalid_payload_is_recorded_and_cannot_retry(tmp_path):
    probe = load_tokenizer_binding_probe(TOKEN_PROBE_PATH)
    attempts = {"count": 0}

    def invalid(fixture, raw_probe):
        attempts["count"] += 1
        return {"unexpected": True}

    root = tmp_path / "invalid-payload"
    transports = {
        "openai_compatible_local": invalid,
        "native_ollama_chat": invalid,
    }
    assert_code(
        "token_probe_provider_payload_invalid",
        lambda: execute_tokenizer_binding_probe(
            probe=probe,
            token_counter=lambda messages: 100,
            transports=transports,
            checkpoint_root=root,
            evidence_kind="contract_fake",
        ),
    )
    assert attempts["count"] == 1
    failure = next(root.rglob("failure.json"))
    assert "token_probe_provider_payload_invalid" in failure.read_text(encoding="utf-8")
    assert_code(
        "token_probe_intent_without_complete_no_retry",
        lambda: execute_tokenizer_binding_probe(
            probe=probe,
            token_counter=lambda messages: 100,
            transports=transports,
            checkpoint_root=root,
            evidence_kind="contract_fake",
        ),
    )
    assert attempts["count"] == 1


def test_p3_product_call_shape_observer_never_forwards_raw_messages():
    design = load_design(DESIGN_PATH)
    observer = ProductCallShapeObserver(design, lambda messages: 23)
    assert_code(
        "product_call_shape_observed_no_generation",
        lambda: observer.observe_openai(
            (),
            {
                "model": "qwen2.5:7b",
                "messages": [{"role": "user", "content": "private fixture"}],
                "temperature": 0.1,
                "timeout": 20,
            },
        ),
    )
    assert len(observer.calls) == 1
    shape = observer.calls[0]
    assert shape["forwarded_to_transport"] is False
    assert shape["prompt_tokens"] == 23
    assert "messages" not in shape and "content" not in shape
    assert shape["normalization"]["model_exact"] is True
    assert shape["normalization"]["temperature_exact"] is False
    assert shape["normalization"]["completion_cap_present_and_within_system_limit"] is False


def test_p3_product_call_shape_audit_uses_real_product_without_generation(tmp_path):
    output = tmp_path / "p3-b4-call-shape.json"
    completed = subprocess.run(
        [
            str(ROOT / ".venv/product_checks/bin/python"),
            str(ROOT / "p3_product_worker.py"),
            "--mode",
            "call-shape-audit",
            "--design",
            str(DESIGN_PATH),
            "--output",
            str(output),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
        env={**os.environ, "URUHA_SKIP_AUTO_VENV": "1"},
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["status"] == "p3_b4_call_shape_audit_pass"
    assert payload["observed_attempts"] >= 1
    assert payload["real_model_calls"] == payload["network_calls"] == 0
    assert payload["developer_smoke_cases_accessed"] == 0
    assert payload["ephemeral_workspace_removed_after_audit"] is True
    assert all(payload["checks"].values())


def test_p3_product_adapter_adds_only_missing_frozen_generation_fields():
    design = load_design(DESIGN_PATH)
    messages = [{"role": "user", "content": "fixture"}]
    native_original = {
        "model": "qwen2.5:7b",
        "messages": messages,
        "stream": False,
        "think": False,
        "options": {"temperature": 0, "num_predict": 280},
    }
    native, native_trace = normalize_product_native_call(design, native_original)
    assert native == build_native_call(design, messages, 280)
    assert native_trace["inserted_fields"] == [
        "options.seed",
        "options.top_p",
        "options.num_ctx",
    ]
    assert native_trace["messages_preserved"] is True
    assert native_trace["completion_cap_preserved"] is True

    response_format = {"type": "json_object"}
    openai_original = {
        "model": "qwen2.5:7b",
        "messages": messages,
        "temperature": 0,
        "max_tokens": 128,
        "timeout": 20,
        "response_format": response_format,
    }
    openai, openai_trace = normalize_product_openai_call(design, openai_original)
    expected_generation = build_openai_call(design, messages, 128)
    assert {key: openai[key] for key in expected_generation} == expected_generation
    assert openai["timeout"] == 20
    assert openai["response_format"] == response_format
    assert openai_trace["messages_preserved"] is True
    assert openai_trace["completion_cap_preserved"] is True


def test_p3_product_adapter_rejects_unknown_or_conflicting_fields():
    design = load_design(DESIGN_PATH)
    messages = [{"role": "user", "content": "fixture"}]
    native = build_native_call(design, messages, 128)
    native["options"]["seed"] = 7
    assert_code(
        "native_product_seed_mismatch",
        lambda: normalize_product_native_call(design, native),
    )
    openai = build_openai_call(design, messages, 128)
    openai["frequency_penalty"] = 1
    assert_code(
        "openai_product_unknown_option",
        lambda: normalize_product_openai_call(design, openai),
    )


def test_p3_normalized_shape_audit_is_exact_without_generation(tmp_path):
    output = tmp_path / "p3-b5-normalized-shape.json"
    completed = subprocess.run(
        [
            str(ROOT / ".venv/product_checks/bin/python"),
            str(ROOT / "p3_product_worker.py"),
            "--mode",
            "normalized-shape-audit",
            "--design",
            str(DESIGN_PATH),
            "--output",
            str(output),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
        env={**os.environ, "URUHA_SKIP_AUTO_VENV": "1"},
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["status"] == "p3_b5_normalized_shape_audit_pass"
    assert payload["normalization_drift_counts"] == {}
    assert payload["real_model_calls"] == payload["network_calls"] == 0
    assert all(payload["checks"].values())
    trace = payload["call_shapes"][0]["adapter_normalization"]
    assert trace["inserted_fields"] == [
        "options.seed",
        "options.top_p",
        "options.num_ctx",
    ]
    assert trace["messages_preserved"] is True
    assert trace["completion_cap_preserved"] is True


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
