"""Zero-provider contracts for Web admission crossing the P4-C product wrappers."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

import uruha_product_function_calling_p4 as product
import uruha_product_tool_failure_truth_p4 as truth
import uruha_web_ui as web
from test_p4_turn_admission_attribution import (
    RAW_INPUT,
    RAW_REPLY,
    _events,
    _private_web_logs,
    private_admission,
)
from test_p4_source_event_exact_input_capability import ENVELOPE, prepared_run
from test_uruha_product_tool_failure_truth_p4 import (
    EXPLICIT,
    FakeProvider,
    _installed_base,
)
import uruha_source_event_exact_input_capability_p4 as cap


TOKEN = "admission-token-test-opaque"
BASE_WEB_RUN_TURN = web._run_turn


def _install_on_web(monkeypatch, provider):
    # Install both real product wrappers over the real Web function. Restore
    # module globals at test teardown so other P4-C tests remain independent.
    monkeypatch.setattr(product, "_INSTALLED", False)
    monkeypatch.setattr(product, "_ORIGINAL_RUN_TURN", None)
    monkeypatch.setattr(product, "_PROVIDER_FACTORY", None)
    monkeypatch.setattr(web, "_run_turn", BASE_WEB_RUN_TURN)
    factory_calls = []

    def make_provider():
        factory_calls.append("factory")
        return provider

    assert product.install_product_function_calling_p4(
        web, provider_factory=make_provider
    ) is True
    assert truth.install_product_tool_failure_truth_p4(web) is True
    return factory_calls


def test_ordinary_double_wrapper_forwards_exact_token_once_without_tool(monkeypatch):
    provider = FakeProvider()
    base = _installed_base(monkeypatch, provider)

    result = base._run_turn(RAW_INPUT, False, admission_token=TOKEN)

    assert result is base.ordinary_result
    assert base.ordinary_calls == [(
        (RAW_INPUT, False),
        {
            "input_mode": "text",
            "acoustic_summary": None,
            "frontend_enqueue_started": 0.0,
            "handler_started": 0.0,
            "admission_token": TOKEN,
        },
    )]
    assert provider.invocations == []
    assert base.RUNTIME.activity_count == 0


@pytest.mark.parametrize("extra_kwargs", ({}, {"exact_input_claim": None}))
def test_ordinary_without_token_retains_legacy_keyword_shape(monkeypatch, extra_kwargs):
    provider = FakeProvider()
    base = _installed_base(monkeypatch, provider)

    assert base._run_turn(RAW_INPUT, False, **extra_kwargs) is base.ordinary_result
    assert base.ordinary_calls == [(
        (RAW_INPUT, False),
        {
            "input_mode": "text",
            "acoustic_summary": None,
            "frontend_enqueue_started": 0.0,
            "handler_started": 0.0,
        },
    )]
    assert provider.invocations == []


def test_ordinary_exact_claim_preserves_object_identity_through_both_wrappers(monkeypatch):
    provider = FakeProvider()
    base = _installed_base(monkeypatch, provider)
    claim = object()

    assert base._run_turn(
        RAW_INPUT, False, admission_token=TOKEN, exact_input_claim=claim,
    ) is base.ordinary_result

    assert len(base.ordinary_calls) == 1
    args, kwargs = base.ordinary_calls[0]
    assert args == (RAW_INPUT, False)
    assert kwargs == {
        "input_mode": "text",
        "acoustic_summary": None,
        "frontend_enqueue_started": 0.0,
        "handler_started": 0.0,
        "admission_token": TOKEN,
        "exact_input_claim": claim,
    }
    assert kwargs["exact_input_claim"] is claim
    assert provider.invocations == []
    assert base.RUNTIME.activity_count == 0


def test_tool_selected_with_claim_only_stays_fail_closed(monkeypatch):
    provider = FakeProvider()
    base = _installed_base(monkeypatch, provider)
    monkeypatch.setattr(
        product, "_PROVIDER_FACTORY",
        lambda: pytest.fail("tool provider factory must not run"),
    )
    monkeypatch.setattr(
        product, "read_product_runtime_status",
        lambda _runtime: pytest.fail("status reader must not run"),
    )

    with pytest.raises(RuntimeError, match="tool_route_admission_unavailable"):
        base._run_turn(EXPLICIT, False, exact_input_claim=object())

    assert base.ordinary_calls == []
    assert base.RUNTIME.activity_count == 0
    assert provider.invocations == []


@pytest.mark.parametrize("mode", ["text", "audio"])
def test_real_web_browser_submit_reaches_complete_journal_through_wrappers(
    private_admission, monkeypatch, mode,
):
    manager, brain, root, _memory_db, _session_db, journal = private_admission
    _private_web_logs(monkeypatch, root)
    provider = FakeProvider()
    factory_calls = _install_on_web(monkeypatch, provider)

    submitted = RAW_INPUT
    if mode == "audio":
        audio = root / "input.wav"
        audio.write_bytes(b"synthetic-audio-file-no-provider")
        monkeypatch.setattr(
            manager, "get_ears",
            lambda: SimpleNamespace(transcribe_audio_file=lambda _path: RAW_INPUT),
        )
        submitted = str(audio)
    started, session_state = web.begin_human_submission_with_session(submitted)
    token = session_state["admission_token"]
    stream = (
        web.submit_audio_browser_bound(submitted, [], False, started, session_state)
        if mode == "audio"
        else web.submit_text_browser_bound(submitted, [], False, started, session_state)
    )
    updates = list(stream)

    assert updates[-1][0][-1] == {"role": "assistant", "content": RAW_REPLY}
    rows = _events(journal)
    assert [row["event"] for row in rows] == [
        "arrival", "admission_snapshot", "cognition_start", "cognition_end", "terminal",
    ]
    assert all(row["submission_id"] == token for row in rows)
    assert rows[-1]["status"] == "delivered"
    assert brain.generation_calls == 1
    assert provider.invocations == []
    assert factory_calls == []


def test_approved_exact_claim_reaches_original_web_through_both_wrappers(
    private_admission, prepared_run, monkeypatch,
):
    manager, brain, root, _memory_db, _session_db, journal = private_admission
    _private_web_logs(monkeypatch, root)
    monkeypatch.setenv("URUHA_P4_SOURCE_EVENT_SURFACE_DIAGNOSTIC_ARM", "on")
    monkeypatch.setenv("URUHA_P4_EXACT_INPUT_CAPABILITY_ROOT", str(prepared_run))
    provider = FakeProvider()
    factory_calls = _install_on_web(monkeypatch, provider)
    original_cognition = brain.run_turn_debug
    seen_inputs = []

    def fake_cognition(user_text, input_context=None):
        seen_inputs.append(user_text)
        return original_cognition(RAW_INPUT, input_context=input_context)

    monkeypatch.setattr(brain, "run_turn_debug", fake_cognition)
    cap.issue_exact_input_permit(prepared_run, "cap_fixed_envelope", "on")
    started, session_state = web.begin_exact_text_submission_with_session(
        ENVELOPE, request=SimpleNamespace(session_hash="p4-wrapper-exact-isolated"),
    )
    assert session_state["exact_input_claim"] is not None

    updates = list(web.submit_text_browser_bound(
        ENVELOPE, [], False, started, session_state,
    ))

    assert updates[-1][0][-1] == {"role": "assistant", "content": RAW_REPLY}
    assert seen_inputs == [ENVELOPE]
    assert [row["event"] for row in _events(journal)] == [
        "arrival", "admission_snapshot", "cognition_start", "cognition_end", "terminal",
    ]
    assert _events(journal)[-1]["status"] == "delivered"
    assert brain.generation_calls == 1
    assert provider.invocations == factory_calls == []


def test_tool_selected_with_token_fails_before_activity_provider_or_status(
    private_admission, monkeypatch,
):
    manager, brain, root, _memory_db, _session_db, journal = private_admission
    _private_web_logs(monkeypatch, root)
    provider = FakeProvider()
    factory_calls = _install_on_web(monkeypatch, provider)
    calls = []
    monkeypatch.setattr(
        product, "read_product_runtime_status",
        lambda _runtime: calls.append("status_reader"),
    )
    monkeypatch.setattr(
        manager, "mark_activity",
        lambda: calls.append("mark_activity"),
    )
    started, session_state = web.begin_human_submission_with_session(EXPLICIT)
    # Browser registration itself marks activity.  The fail-closed contract
    # concerns additional activity from the selected synthetic tool route.
    calls.clear()

    with pytest.raises(RuntimeError, match="tool_route_admission_unavailable"):
        list(web.submit_text_browser_bound(EXPLICIT, [], False, started, session_state))

    assert [row["event"] for row in _events(journal)] == [
        "arrival", "admission_snapshot", "terminal",
    ]
    assert _events(journal)[-1]["status"] == "error"
    assert brain.generation_calls == 0
    assert provider.invocations == []
    assert factory_calls == []
    assert calls == []
