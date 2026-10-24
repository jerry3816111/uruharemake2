"""Zero-model Web/Brain admission checks for the bounded P4 exact-text trial.

These tests use a synthetic prepared-run fixture and never start a model, Web
server, browser, or formal memory database.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from test_p4_source_event_exact_input_capability import (
    ENVELOPE, UNLISTED, prepared_run,
)
import uruha_source_event_exact_input_capability_p4 as cap


_REQUEST_A = SimpleNamespace(session_hash="isolated-browser-a")
_REQUEST_B = SimpleNamespace(session_hash="isolated-browser-b")


class _NoBrainRuntime:
    _session_id = "isolated-test-session"
    _mouth = None
    _brain = None

    def __init__(self):
        self.begins = 0
        self.finishes = 0
        self.activities = 0
        self.ears = 0

    def _admission_enabled(self):
        return False

    def begin_human_turn(self):
        self.begins += 1
        return 1.0

    def finish_human_turn(self):
        self.finishes += 1

    def mark_activity(self):
        self.activities += 1
        raise AssertionError("cognition_must_not_start")

    def get_ears(self):
        self.ears += 1
        raise AssertionError("transcription_must_not_start")


@pytest.fixture
def isolated_web(monkeypatch, prepared_run):
    import uruha_web_ui as web

    fake = _NoBrainRuntime()
    monkeypatch.setattr(web, "RUNTIME", fake)
    monkeypatch.setenv("URUHA_P4_SOURCE_EVENT_SURFACE_DIAGNOSTIC_ARM", "on")
    monkeypatch.setenv("URUHA_P4_EXACT_INPUT_CAPABILITY_ROOT", str(prepared_run))
    return web, fake


def test_unlisted_web_text_is_rejected_before_admission_or_pending_bubble(
    isolated_web, prepared_run,
):
    web, fake = isolated_web
    cap.issue_exact_input_permit(prepared_run, "cap_fixed_envelope", "on")
    original_history = [{"role": "user", "content": "already present"}]
    for source in UNLISTED:
        started, state = web.begin_exact_text_submission_with_session(source, request=_REQUEST_A)
        assert started == 0.0 and state["exact_input_rejected"]
        updates = list(web.submit_text_browser_bound(
            source, original_history, False, started, state,
        ))
        assert len(updates) == 1
        assert updates[0][0] is original_history
        assert updates[0][1] is original_history
        assert not any(row.get("content") == "..." for row in updates[0][0])
    assert fake.begins == fake.finishes == fake.activities == fake.ears == 0
    assert not (prepared_run / ".cache" / cap.CAPABILITY_DIRECTORY / cap.SPENT_NAME).exists()


def test_replayed_direct_rejection_without_claim_cannot_finish_another_admission(
    isolated_web, prepared_run,
):
    web, fake = isolated_web
    cap.issue_exact_input_permit(prepared_run, "cap_fixed_envelope", "on")
    started, state = web.begin_exact_text_submission_with_session(ENVELOPE, request=_REQUEST_A)
    assert state["exact_input_claim"] is not None and fake.begins == 1
    updates = list(web.submit_text(
        UNLISTED[0], [], False, frontend_enqueue_started=started,
        exact_input_claim=None,
    ))
    assert len(updates) == 1 and updates[0][0] == []
    assert fake.finishes == fake.activities == 0
    valid_stream = web.submit_text_browser_bound(ENVELOPE, [], False, started, state)
    assert next(valid_stream)[0][-1]["content"] == "..."
    valid_stream.close()
    assert fake.finishes == 1


def test_second_queue_free_submit_cancels_unreserved_first_before_state_overwrite(
    isolated_web, prepared_run,
):
    web, fake = isolated_web
    cap.issue_exact_input_permit(prepared_run, "cap_fixed_envelope", "on")
    first_started, first_state = web.begin_exact_text_submission_with_session(ENVELOPE, request=_REQUEST_A)
    assert first_started == 1.0 and fake.begins == 1 and fake.finishes == 0
    second_started, second_state = web.begin_exact_text_submission_with_session(ENVELOPE, request=_REQUEST_A)
    assert second_started == 0.0
    assert second_state["exact_input_rejected"] == "claim_already_in_progress"
    assert fake.begins == fake.finishes == 1
    assert list(web.submit_text_browser_bound(
        ENVELOPE, [], False, first_started, first_state,
    ))[0][0] == []
    assert list(web.submit_text_browser_bound(
        ENVELOPE, [], False, second_started, second_state,
    ))[0][0] == []
    assert fake.finishes == 1 and fake.activities == 0


def test_second_queue_free_submit_does_not_cancel_reserved_first(
    isolated_web, prepared_run,
):
    web, fake = isolated_web
    cap.issue_exact_input_permit(prepared_run, "cap_fixed_envelope", "on")
    started, state = web.begin_exact_text_submission_with_session(ENVELOPE, request=_REQUEST_A)
    stream = web.submit_text_browser_bound(ENVELOPE, [], False, started, state)
    assert next(stream)[0][-1]["content"] == "..."
    second_started, second_state = web.begin_exact_text_submission_with_session(ENVELOPE, request=_REQUEST_A)
    assert second_started == 0.0 and second_state["exact_input_rejected"]
    assert fake.finishes == 0
    assert cap.validate_exact_input_claim(
        state["exact_input_claim"], prepared_run, ENVELOPE, "on",
    ) is state["exact_input_claim"]
    stream.close()
    assert fake.begins == fake.finishes == 1


def test_unrelated_browser_session_cannot_cancel_pending_first(
    isolated_web, prepared_run,
):
    web, fake = isolated_web
    cap.issue_exact_input_permit(prepared_run, "cap_fixed_envelope", "on")
    started, state = web.begin_exact_text_submission_with_session(ENVELOPE, request=_REQUEST_A)
    other_started, other_state = web.begin_exact_text_submission_with_session(
        ENVELOPE, request=_REQUEST_B,
    )
    assert other_started == 0.0 and other_state["exact_input_rejected"]
    assert fake.begins == 1 and fake.finishes == 0
    assert cap.validate_exact_input_claim(
        state["exact_input_claim"], prepared_run, ENVELOPE, "on",
    ) is state["exact_input_claim"]
    stream = web.submit_text_browser_bound(ENVELOPE, [], False, started, state)
    assert next(stream)[0][-1]["content"] == "..."
    stream.close()
    assert fake.finishes == 1


def test_missing_browser_session_fails_before_claim_or_admission(
    isolated_web, prepared_run,
):
    web, fake = isolated_web
    cap.issue_exact_input_permit(prepared_run, "cap_fixed_envelope", "on")
    started, state = web.begin_exact_text_submission_with_session(ENVELOPE)
    assert started == 0.0 and state["exact_input_rejected"] == "browser_session_unavailable"
    assert fake.begins == fake.finishes == 0
    assert not (prepared_run / ".cache" / cap.CAPABILITY_DIRECTORY / cap.SPENT_NAME).exists()


def test_admission_setup_error_releases_reserved_coordinator_claim(
    isolated_web, prepared_run, monkeypatch,
):
    web, fake = isolated_web
    cap.issue_exact_input_permit(prepared_run, "cap_fixed_envelope", "on")
    _started, state = web.begin_exact_text_submission_with_session(ENVELOPE, request=_REQUEST_A)

    def fail_admission():
        raise RuntimeError("simulated_admission_setup_failure")

    monkeypatch.setattr(fake, "begin_human_turn", fail_admission)
    with pytest.raises(RuntimeError, match="simulated_admission_setup_failure"):
        list(web.submit_text(
            ENVELOPE, [], False, frontend_enqueue_started=0.0,
            exact_input_claim=state["exact_input_claim"],
        ))
    assert web._EXACT_PENDING_ADMISSION is None
    assert fake.activities == fake.ears == 0


def test_approved_text_claims_once_before_pending_and_closes_on_abort(
    isolated_web, prepared_run,
):
    web, fake = isolated_web
    cap.issue_exact_input_permit(prepared_run, "cap_fixed_envelope", "on")
    started, state = web.begin_exact_text_submission_with_session(ENVELOPE, request=_REQUEST_A)
    claim = state["exact_input_claim"]
    assert started == 1.0 and fake.begins == 1
    stream = web.submit_text_browser_bound(ENVELOPE, [], False, started, state)
    first = next(stream)
    assert [row["role"] for row in first[0]] == ["user", "assistant"]
    assert first[0][-1]["content"] == "..."
    stream.close()
    assert fake.finishes == 1 and fake.activities == 0
    with pytest.raises(cap.ExactInputCapabilityError):
        cap.validate_exact_input_claim(claim, prepared_run, ENVELOPE, "on")
    again, state2 = web.begin_exact_text_submission_with_session(ENVELOPE, request=_REQUEST_A)
    assert again == 0.0 and state2["exact_input_rejected"]
    assert fake.begins == 1


def test_changed_queued_text_rejects_without_cognition_or_bubble(
    isolated_web, prepared_run,
):
    web, fake = isolated_web
    cap.issue_exact_input_permit(prepared_run, "cap_fixed_envelope", "on")
    started, state = web.begin_exact_text_submission_with_session(ENVELOPE, request=_REQUEST_A)
    updates = list(web.submit_text_browser_bound(
        ENVELOPE + " ", [], False, started, state,
    ))
    assert len(updates) == 1 and updates[0][0] == []
    assert fake.activities == 0
    assert fake.begins == fake.finishes == 1


def test_same_server_side_claim_cannot_make_two_pending_bubbles(
    isolated_web, prepared_run,
):
    web, fake = isolated_web
    cap.issue_exact_input_permit(prepared_run, "cap_fixed_envelope", "on")
    started, state = web.begin_exact_text_submission_with_session(ENVELOPE, request=_REQUEST_A)
    first_stream = web.submit_text_browser_bound(ENVELOPE, [], False, started, state)
    first_update = next(first_stream)
    assert first_update[0][-1]["content"] == "..."
    second_updates = list(web.submit_text_browser_bound(
        ENVELOPE, [], False, started, state,
    ))
    assert len(second_updates) == 1 and second_updates[0][0] == []
    assert cap.validate_exact_input_claim(
        state["exact_input_claim"], prepared_run, ENVELOPE, "on",
    ) is state["exact_input_claim"]
    assert fake.finishes == 0
    first_stream.close()
    assert fake.begins == fake.finishes == 1 and fake.activities == 0


def test_changed_second_queued_text_cannot_abort_first_reserved_handler(
    isolated_web, prepared_run,
):
    web, fake = isolated_web
    cap.issue_exact_input_permit(prepared_run, "cap_fixed_envelope", "on")
    started, state = web.begin_exact_text_submission_with_session(ENVELOPE, request=_REQUEST_A)
    first_stream = web.submit_text_browser_bound(ENVELOPE, [], False, started, state)
    assert next(first_stream)[0][-1]["content"] == "..."
    second_updates = list(web.submit_text_browser_bound(
        ENVELOPE + " ", [], False, started, state,
    ))
    assert len(second_updates) == 1 and second_updates[0][0] == []
    assert cap.validate_exact_input_claim(
        state["exact_input_claim"], prepared_run, ENVELOPE, "on",
    ) is state["exact_input_claim"]
    assert fake.finishes == 0
    first_stream.close()
    assert fake.begins == fake.finishes == 1 and fake.activities == 0


def test_stale_claim_before_first_yield_rejects_without_pending_bubble(
    isolated_web, prepared_run,
):
    web, fake = isolated_web
    cap.issue_exact_input_permit(prepared_run, "cap_fixed_envelope", "on")
    started, state = web.begin_exact_text_submission_with_session(ENVELOPE, request=_REQUEST_A)
    cap.close_exact_input_claim(state["exact_input_claim"])
    updates = list(web.submit_text_browser_bound(
        ENVELOPE, [], False, started, state,
    ))
    assert len(updates) == 1 and updates[0][0] == []
    assert "未送入角色或記憶" in updates[0][9]
    assert fake.begins == fake.finishes == 1 and fake.activities == 0


@pytest.mark.parametrize("pre_turn_safe", [True, False])
def test_midflight_claim_abort_note_does_not_overstate_no_memory_write(
    isolated_web, prepared_run, monkeypatch, pre_turn_safe,
):
    web, fake = isolated_web
    cap.issue_exact_input_permit(prepared_run, "cap_fixed_envelope", "on")
    started, state = web.begin_exact_text_submission_with_session(ENVELOPE, request=_REQUEST_A)

    def fail_at_run(*_args, **_kwargs):
        raise cap.ExactInputCapabilityError(
            "same_turn_claim_closed", pre_turn_safe=pre_turn_safe,
        )

    monkeypatch.setattr(web, "_run_turn", fail_at_run)
    updates = list(web.submit_text_browser_bound(
        ENVELOPE, [], False, started, state,
    ))
    assert len(updates) == 2 and updates[0][0][-1]["content"] == "..."
    assert updates[-1][0] == []
    note = updates[-1][9]
    assert ("未送入角色或記憶" in note) is pre_turn_safe
    if not pre_turn_safe:
        assert "可能已有內部讀寫" in note
    assert fake.begins == fake.finishes == 1


def test_audio_entry_points_refuse_before_transcription_or_admission(isolated_web):
    web, fake = isolated_web
    started, state = web.begin_exact_audio_submission_with_session("/isolated/fake.wav")
    assert started == 0.0 and state["exact_input_rejected"]
    updates = list(web.submit_audio_browser_bound(
        "/isolated/fake.wav", [], False, started, state,
    ))
    assert len(updates) == 1 and updates[0][0] == []
    assert web.transcribe_audio_only("/isolated/fake.wav") == ""
    assert fake.ears == fake.begins == fake.activities == 0


def test_proactive_poll_cannot_emit_without_exact_input_claim(isolated_web):
    web, fake = isolated_web
    assert len(web.poll_proactive_turn([], False)) == 7
    assert fake.activities == fake.begins == fake.ears == 0


def test_direct_runtime_and_brain_entry_refuse_without_claim_before_side_effects(
    isolated_web,
):
    web, fake = isolated_web
    from uruha_brain_mac import UruhaBrainV4_Mac

    with pytest.raises(cap.ExactInputCapabilityError):
        web._run_turn(UNLISTED[0], False)
    with pytest.raises(cap.ExactInputCapabilityError):
        UruhaBrainV4_Mac.run_turn_debug(object(), UNLISTED[0])
    with pytest.raises(cap.ExactInputCapabilityError):
        UruhaBrainV4_Mac.emit_response_if_ready(
            object(), {"user_input": UNLISTED[0]}, {"logic": {}, "route_info": {}},
        )
    assert fake.activities == fake.begins == fake.ears == 0


def test_direct_runtime_and_brain_audio_mode_refused_even_with_valid_claim(
    isolated_web, prepared_run,
):
    web, fake = isolated_web
    from uruha_brain_mac import UruhaBrainV4_Mac

    cap.issue_exact_input_permit(prepared_run, "cap_fixed_envelope", "on")
    claim = cap.claim_exact_input_permit(prepared_run, ENVELOPE, "on")
    with pytest.raises(cap.ExactInputCapabilityError) as runtime_denied:
        web._run_turn(ENVELOPE, False, input_mode="audio", exact_input_claim=claim)
    assert runtime_denied.value.reason == "input_mode_not_text"
    with cap.scoped_exact_input_claim(claim):
        with pytest.raises(cap.ExactInputCapabilityError) as brain_denied:
            UruhaBrainV4_Mac.run_turn_debug(
                object(), ENVELOPE, input_context={"input_mode": "audio"},
            )
    assert brain_denied.value.reason == "input_mode_not_text"
    assert fake.activities == fake.begins == fake.ears == 0
