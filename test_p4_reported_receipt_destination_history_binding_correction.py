"""Zero-model regression for a source-correct reply with stale selected history."""

from collections import Counter
import hashlib
import json
from pathlib import Path

import pytest

from uruha_reported_receipt_destination_relation_p4 import (
    LABEL,
    _guard_with_reported_receipt_destination_p4,
    _post_check_with_reported_receipt_destination_p4,
    preserve_reported_receipt_destination_p4,
)


DATA = json.loads(
    (Path(__file__).resolve().parent / "datasets/p4_reported_receipt_destination_history_binding_probe_2026-10-23.json").read_text(encoding="utf-8")
)
SOURCE = DATA["cases"][0]["source"]
WRONG = "先輩は2103年2月17日に緑の温室の西通路で銀の懐中時計を受け取る場所を決定したらしいんだね。"
CORRECT, _ = preserve_reported_receipt_destination_p4(SOURCE, WRONG)
INTENT = "deterministic_semantic_commit_m32"


class _SpeechHistory:
    def __init__(self, content, intent=INTENT):
        self.history = [
            {"role": "user", "content": SOURCE, "intent": intent},
            {"role": "assistant", "content": content, "intent": intent},
        ]
        self.reply_variant_counts = Counter({content: 1})
        self.intent_variant_counts = Counter({(intent, content): 1})
        self.normalized_reply_counts = Counter({content: 1})
        self.intent_normalized_counts = Counter({(intent, content): 1})

    def _normalize_reply_key(self, value):
        return value

    def _bind_forbidden_projection_shadow_visible_reply(self, logic, visible):
        pass


def _prior_guard(brain, candidate, logic, *, user_input, memory_data):
    logic["visible_language_guard"] = {
        "final_reply": candidate,
        "final_reply_sha256": hashlib.sha256(candidate.encode("utf-8")).hexdigest(),
    }
    return candidate


def _guarded(actor, incoming=CORRECT, logic=None):
    state = logic or {"intent": INTENT, "jp_summary": SOURCE}
    visible = _guard_with_reported_receipt_destination_p4(
        actor, incoming, state, SOURCE, {}, _prior_guard,
    )
    return visible, state


def test_upstream_corrected_reply_rebinds_stale_current_history_before_episode():
    actor = _SpeechHistory(WRONG)
    visible, logic = _guarded(actor)
    assert visible == CORRECT
    assert logic[LABEL]["status"] == "accepted_verified"
    assert logic[LABEL]["changed"] is False
    assert logic[LABEL]["history_status"] == "current_assistant_synced"
    assert actor.history[-1]["content"] == visible
    for name, old, new in (
        ("reply_variant_counts", WRONG, CORRECT),
        ("intent_variant_counts", (INTENT, WRONG), (INTENT, CORRECT)),
        ("normalized_reply_counts", WRONG, CORRECT),
        ("intent_normalized_counts", (INTENT, WRONG), (INTENT, CORRECT)),
    ):
        counter = getattr(actor, name)
        assert counter[old] == 0
        assert counter[new] == 1

    class Brain:
        right_brain = actor

    assert _post_check_with_reported_receipt_destination_p4(
        Brain(), logic, SOURCE, visible, {}, lambda *args: "prior_post_checked",
    ) == "prior_post_checked"
    assert logic[LABEL]["pre_episode_status"] == "verified_before_episode_write"


def test_already_bound_current_history_keeps_all_variant_counters():
    actor = _SpeechHistory(CORRECT)
    before = tuple(dict(getattr(actor, name)) for name in (
        "reply_variant_counts", "intent_variant_counts", "normalized_reply_counts", "intent_normalized_counts",
    ))
    visible, logic = _guarded(actor)
    after = tuple(dict(getattr(actor, name)) for name in (
        "reply_variant_counts", "intent_variant_counts", "normalized_reply_counts", "intent_normalized_counts",
    ))
    assert visible == CORRECT
    assert logic[LABEL]["history_status"] == "current_assistant_already_bound"
    assert after == before


def test_wrong_intent_and_missing_counter_still_fail_closed():
    wrong_intent = _SpeechHistory(WRONG, intent="other_intent")
    with pytest.raises(RuntimeError, match="current history mismatch"):
        _guarded(wrong_intent)
    assert wrong_intent.history[-1]["content"] == WRONG

    missing_counter = _SpeechHistory(WRONG)
    missing_counter.reply_variant_counts.clear()
    with pytest.raises(RuntimeError, match="current history mismatch"):
        _guarded(missing_counter)
    assert missing_counter.history[-1]["content"] == WRONG


def test_foreign_same_intent_summary_wrong_role_and_missing_history_fail_closed():
    foreign = _SpeechHistory(WRONG)
    foreign.history[-2]["content"] = "前の別の発話の要約"
    with pytest.raises(RuntimeError, match="current history mismatch"):
        _guarded(foreign)
    assert foreign.history[-1]["content"] == WRONG

    foreign_intent = _SpeechHistory(WRONG)
    foreign_intent.history[-2]["intent"] = "other_intent"
    with pytest.raises(RuntimeError, match="current history mismatch"):
        _guarded(foreign_intent)
    assert foreign_intent.history[-1]["content"] == WRONG

    wrong_role = _SpeechHistory(WRONG)
    wrong_role.history[-1]["role"] = "user"
    with pytest.raises(RuntimeError, match="current history mismatch"):
        _guarded(wrong_role)

    missing = _SpeechHistory(WRONG)
    missing.history.clear()
    with pytest.raises(RuntimeError, match="current history mismatch"):
        _guarded(missing)


def test_post_check_reports_only_non_raw_reason_code():
    actor = _SpeechHistory(CORRECT)
    visible, logic = _guarded(actor)
    actor.history[-1]["content"] = WRONG

    class Brain:
        right_brain = actor

    with pytest.raises(RuntimeError, match="pre-episode mismatch: current_history") as error:
        _post_check_with_reported_receipt_destination_p4(
            Brain(), logic, SOURCE, visible, {}, lambda *args: None,
        )
    assert SOURCE not in str(error.value)
    assert WRONG not in str(error.value)
