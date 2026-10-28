"""Focused zero-model contract for the finite P4 f7 source-event utility."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from uruha_direct_reply_act_m29_priority_p4 import LABEL as M29_LABEL
from uruha_direct_reply_act_m29_priority_p4 import classify_direct_reply_act_p4
from uruha_direct_reply_act_planner_handoff_p4 import validate_handoff_p4
from uruha_source_event_core_utility_p4 import SCHEMA, assess_candidate_coverage_p4


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _handoff(source: str) -> dict | None:
    """Construct the real M29→M33 handoff, without running a model."""
    admitted = classify_direct_reply_act_p4(source)
    projection = {
        "status": "direct_reply_act_precedes_literal_projection_p4",
        "projection_required": False,
        "surface_authority": False,
        "input_digest": admitted["input_sha256"][:16],
        M29_LABEL: {
            **admitted,
            "status": "admitted_direct_reply_act",
            "original_projection_required": True,
            "original_m33_status": "source_pattern_unavailable",
            "m29_projection_after": False,
        },
    }
    atoms = {"status": "not_applicable", "reason": "m29_projection_not_required"}
    return validate_handoff_p4(source, projection, atoms)


def _plans(event_core: str) -> list[dict]:
    return [
        {"candidate_label": "default", "scene": "casual", "response_mode": "direct_answer", "core_message_jp": "おめでとう。"},
        {"candidate_label": "softer", "scene": "support", "response_mode": "direct_answer_with_hedge", "core_message_jp": event_core},
        {"candidate_label": "sharper", "scene": "casual", "response_mode": "direct_answer", "core_message_jp": "がんばったな。"},
    ]


@pytest.mark.parametrize(
    ("source", "obj", "action", "core"),
    [
        ("初めて自分で木の椅子を磨いた。今は一言だけ励まして。", "木の椅子", "磨いた", "木の椅子を磨いたの、いいね。"),
        ("自分で紙の灯りを組み立てた。今は一言だけ労って。", "紙の灯り", "組み立てた", "紙の灯りを組み立てたんだね。"),
    ],
)
def test_unseen_japanese_object_and_action_are_literal_not_inventory(source, obj, action, core):
    handoff = _handoff(source)
    assert handoff is not None
    before_handoff, before_plans = deepcopy(handoff), _plans(core)
    plans = deepcopy(before_plans)
    got = assess_candidate_coverage_p4(source, handoff, plans)
    assert got == {
        "schema": SCHEMA,
        "status": "grounded_candidate_available",
        "eligible": True,
        "reason": "grounded_candidate_available",
        "input_sha256": _sha(source),
        "event_sha256": _sha(source[:handoff["cue_span"][0]]),
        "object_sha256": _sha(obj),
        "action_sha256": _sha(action),
        "candidate_coverage": [
            {"original_index": 0, "core_sha256": _sha(plans[0]["core_message_jp"]), "grounded": False, "reason": "event_relation_unverified"},
            {"original_index": 1, "core_sha256": _sha(core), "grounded": True, "reason": "grounded"},
            {"original_index": 2, "core_sha256": _sha(plans[2]["core_message_jp"]), "grounded": False, "reason": "event_relation_unverified"},
        ],
    }
    assert plans == before_plans and handoff == before_handoff
    evidence = json.dumps(got, ensure_ascii=False)
    for raw in (source, obj, action, core, plans[0]["core_message_jp"]):
        assert raw not in evidence


def test_frozen_f7_probe_is_supported_without_source_specific_inventory():
    probe = json.loads((Path(__file__).parent / "datasets/p4_source_event_core_utility_f7_probe_2026-10-24.json").read_text())
    source = probe["source"]
    got = assess_candidate_coverage_p4(source, _handoff(source), _plans("庭のベンチを塗り直したの、いいね。"))
    assert got["eligible"] is True
    assert [row["grounded"] for row in got["candidate_coverage"]] == [False, True, False]


@pytest.mark.parametrize(
    ("core", "reason"),
    [
        ("おめでとう。", "event_relation_unverified"),
        ("木の椅子、いいね。", "event_relation_unverified"),
        ("磨いたんだね。", "event_relation_unverified"),
        ("木の机を磨いたね。", "event_relation_unverified"),
        ("木の椅子を塗ったね。", "event_relation_unverified"),
        ("木の椅子を買って、棚を磨いた。", "event_relation_unverified"),
        ("母が木の椅子を磨いたね。", "actor_unverified"),
        ("木の椅子を磨いたのは兄。", "actor_unverified"),
        ("木の椅子を磨いた母、すごい。", "actor_unverified"),
        ("木の椅子を磨いたの、母だよね。", "actor_unverified"),
        ("木の椅子を磨いたの、母よ。", "actor_unverified"),
        ("木の椅子を磨いたんだね母よ。", "actor_unverified"),
        ("木の椅子を磨いたの。母だよね。", "actor_unverified"),
        ("木の椅子を磨いたって、母が言ってた。", "reported_core"),
        ("木の椅子を磨いた？", "interrogative_core"),
        ("木の椅子を磨いたのか。", "interrogative_core"),
        ("木の椅子を磨いたわけじゃない。", "negated_core"),
        ("「木の椅子を磨いた」ね。", "quoted_core"),
        ("木の椅子を磨いたらしい。", "reported_core"),
    ],
)
def test_generic_object_only_wrong_relation_actor_polarity_and_quote_never_ground(core, reason):
    source = "自分で木の椅子を磨いた。今は一言だけ励まして。"
    plans = _plans("別の文。")
    plans[0]["core_message_jp"] = "いいね。"
    plans[1]["core_message_jp"] = core
    got = assess_candidate_coverage_p4(source, _handoff(source), plans)
    assert got["eligible"] is True
    assert got["status"] == "no_grounded_candidate"
    assert got["candidate_coverage"][1]["reason"] == reason
    assert not any(row["grounded"] for row in got["candidate_coverage"])
    assert core not in repr(got)


@pytest.mark.parametrize(("field", "value"), [
    ("schema", "forged"),
    ("input_sha256", "0" * 64),
    ("cue_sha256", "0" * 64),
    ("cue_span", [0, 2]),
    ("requested_act", "brief_care"),
    ("source_kind", "reported_or_non_user_text"),
    ("m29_status", "literal_topic_projection_required"),
    ("m33_status", "source_atoms_extracted"),
    ("raw_dialogue_persisted", True),
])
def test_stale_or_forged_m29_m33_handoff_fails_closed(field, value):
    source = "自分で木の椅子を磨いた。今は一言だけ励まして。"
    handoff = _handoff(source)
    assert handoff is not None
    handoff[field] = value
    got = assess_candidate_coverage_p4(source, handoff, _plans("木の椅子を磨いたね。"))
    assert got["eligible"] is False
    assert got["status"] == "unverifiable"
    assert got["reason"] == "invalid_handoff"
    assert all(not row["grounded"] for row in got["candidate_coverage"])


def test_handoff_from_prior_turn_cannot_certify_new_turn():
    first = "自分で木の椅子を磨いた。今は一言だけ励まして。"
    second = "自分で紙の灯りを組み立てた。今は一言だけ励まして。"
    got = assess_candidate_coverage_p4(second, _handoff(first), _plans("紙の灯りを組み立てたね。"))
    assert got["status"] == "unverifiable"
    assert got["reason"] == "invalid_handoff"


@pytest.mark.parametrize("source", [
    "I polished my chair myself.今は一言だけ励まして。",
    "我自己把木椅擦亮了。今は一言だけ励まして。",
    "自分で我的木椅を磨いた。今は一言だけ励まして。",
    "自分で机を磨いた。今は一言だけ励まして。",
    "自分で木の椅子を磨かなかった。今は一言だけ励まして。",
    "自分で木の椅子を磨いた。自分で棚を拭いた。今は一言だけ励まして。",
    "友達が自分で木の椅子を磨いた。今は一言だけ励まして。",
    "自分で母が木の椅子を磨いた。今は一言だけ励まして。",
    "自分で木の椅子を母が磨いた。今は一言だけ励まして。",
    "自分で木の椅子を磨いたお母さん。今は一言だけ励まして。",
    "自分で木の椅子を磨く兄だ。今は一言だけ励まして。",
    "自分で木の椅子を磨く兄でした。今は一言だけ励まして。",
    "自分で木の椅子を磨く兄に頼んだ。今は一言だけ励まして。",
    "自分で木の椅子を磨いた兄だ。今は一言だけ励まして。",
    "自分で木の椅子を磨いた兄だった。今は一言だけ励まして。",
    "「自分で木の椅子を磨いた」。今は一言だけ励まして。",
    "自分で木の椅子を磨いたわけじゃない。今は一言だけ励まして。",
])
def test_unsupported_source_languages_negation_quote_actor_or_multiple_sentences(source):
    got = assess_candidate_coverage_p4(source, _handoff(source), _plans("木の椅子を磨いたね。"))
    assert got["status"] == "unverifiable"
    assert got["eligible"] is False
    assert got["event_sha256"] is None
    assert not any(row["grounded"] for row in got["candidate_coverage"])
    assert source not in repr(got)


@pytest.mark.parametrize("mutate", [
    lambda plans: plans.__setitem__(0, {**plans[0], "candidate_label": "self_corrected_t1"}),
    lambda plans: plans.__setitem__(1, {**plans[1], "candidate_label": "default"}),
    lambda plans: plans.append({**plans[2], "candidate_label": "revised"}),
    lambda plans: plans.pop(),
    lambda plans: plans.__setitem__(2, {**plans[2], "core_message_jp": plans[1]["core_message_jp"]}),
    lambda plans: plans.__setitem__(1, {**plans[1], "core_message_jp": None}),
])
def test_revised_or_nonoriginal_three_candidate_set_is_not_eligible(mutate):
    source = "自分で木の椅子を磨いた。今は一言だけ励まして。"
    plans = _plans("木の椅子を磨いたね。")
    mutate(plans)
    got = assess_candidate_coverage_p4(source, _handoff(source), plans)
    assert got["status"] == "unverifiable"
    assert got["reason"] == "invalid_candidate_set"
    assert got["eligible"] is False
    assert not any(row["grounded"] for row in got["candidate_coverage"])


@pytest.mark.parametrize(("field", "value", "reason"), [
    ("scene", "invite", "unsupported_scene"),
    ("response_mode", "clarify_light", "unsupported_response_mode"),
])
def test_scene_and_response_mode_conflict_cannot_gain_utility(field, value, reason):
    source = "自分で木の椅子を磨いた。今は一言だけ励まして。"
    plans = _plans("木の椅子を磨いたね。")
    plans[1][field] = value
    got = assess_candidate_coverage_p4(source, _handoff(source), plans)
    assert got["eligible"] is True
    assert got["status"] == "no_grounded_candidate"
    assert got["candidate_coverage"][1]["reason"] == reason
