"""Developer-authored P4 owner-admission regression and product-writer tests."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile

import chromadb
import pytest

from uruha_brain_mac import MemoryManager
import uruha_multilingual_current_preference_p4 as p4i
import uruha_profile_owner_admission_p4 as owner


ROOT = Path(__file__).resolve().parent


@pytest.fixture
def product_writer(monkeypatch):
    """Scope product monkeypatches to this test; adjacent frozen tests stay base."""
    legacy_writer = MemoryManager._remember_profile_facts
    legacy_extractor = MemoryManager._extract_profile_facts
    monkeypatch.setattr(p4i, "_ORIGINAL_REMEMBER_PROFILE_FACTS", legacy_writer)
    monkeypatch.setattr(owner, "_ORIGINAL_REMEMBER_PROFILE_FACTS", p4i.remember_profile_facts_with_current_preference_p4)
    monkeypatch.setattr(owner, "_ORIGINAL_EXTRACT_PROFILE_FACTS", legacy_extractor)
    monkeypatch.setattr(owner, "_ORIGINAL_MEMORY_SNAPSHOT", MemoryManager.get_runtime_snapshot)
    monkeypatch.setattr(MemoryManager, "_extract_profile_facts", owner._extract_with_admitted_facts)
    monkeypatch.setattr(MemoryManager, "_remember_profile_facts", owner.remember_profile_facts_with_owner_admission_p4)
    yield
    assert owner._ADMITTED_FACTS.get() is None


def _memory(collection):
    memory = object.__new__(MemoryManager)
    memory.profile_col = collection
    memory.session_profile = {"name": None, "likes": [], "dislikes": [], "favorites": []}
    memory._last_profile_state_shadow = {
        "status": "not_refreshed",
        "shadow_only": True,
        "affects_working_memory": False,
        "answer_use_authorized": False,
    }
    return memory


def _rows(collection):
    payload = collection.get(include=["documents", "metadatas"])
    return [
        (memory_id, metadata["fact_type"], metadata["value"], metadata)
        for memory_id, metadata in zip(payload["ids"], payload["metadatas"])
    ]


@pytest.mark.parametrize(
    "text",
    [
        "友達の凪紗はルイボス茶が一番好きだ。凪紗が言った。",
        "「私は炭酸水が一番好き」は作文の例文で、私の好みじゃない。",
        "友人の凪紗はルイボス茶が一番好き。",
        "私の友達はルイボス茶が好き。",
        "凪紗がルイボス茶が好き。",
        "凪紗もルイボス茶が好き。",
        "紅茶が一番好きじゃない。",
        "紅茶が好きではない。",
        "I like coffee?",
        "My friend said, 'I like coffee.'",
        "朋友說，我喜歡露營。",
        "凪紗、紅茶が好き。",
        "友達の凪紗はルイボス茶が好き、紅茶が好き。",
        "I like coffee and you like tea.",
        "私は海が好きけど凪紗は紅茶が好き。",
        "私は紅茶が好きじゃないけどコーヒーが好き。",
    ],
)
def test_legacy_negative_cases_have_no_admitted_profile_fact(text):
    facts, audit = owner.admit_legacy_profile_facts(text)
    assert facts == []
    assert audit["admitted_count"] == 0
    assert audit["raw_dialogue_persisted"] is False
    assert text not in repr(audit)


@pytest.mark.parametrize(
    "text, expected",
    [
        ("海が好き。", [("like", "海")]),
        ("私の一番好きな飲み物は玄米茶。", [("favorite", "玄米茶")]),
        ("私はほうじ茶が一番好き。", [("favorite", "ほうじ茶")]),
        ("I really like astronomy.", [("like", "astronomy")]),
        ("My favorite drink is coffee.", [("favorite", "coffee")]),
        ("我喜歡露營。", [("like", "露營")]),
        ("私は紅茶が嫌い。", [("dislike", "紅茶")]),
        ("私は紅茶が好きじゃない。", [("dislike", "紅茶")]),
        ("もう紅茶は好きじゃない。", [("dislike", "紅茶")]),
        ("I hate coffee.", [("dislike", "coffee")]),
        ("Call me Aki.", [("name", "Aki")]),
    ],
)
def test_direct_self_facts_keep_exact_values(text, expected):
    facts, audit = owner.admit_legacy_profile_facts(text)
    assert facts == expected
    assert audit["admitted_count"] == 1
    assert audit["rejected_count"] == 0
    assert text not in repr(audit)


@pytest.mark.parametrize(
    "text",
    [
        "友達の凪紗はルイボス茶が一番好き。私の一番好きな飲み物はほうじ茶。",
        "私の一番好きな飲み物はほうじ茶。友達の凪紗はルイボス茶が一番好き。",
        "「私は炭酸水が一番好き」は作文の例文。私の一番好きな飲み物はほうじ茶。",
        "友達の凪紗はルイボス茶が一番好き、私はほうじ茶が一番好き。",
    ],
)
def test_mixed_clauses_admit_only_independent_self_candidate(text):
    facts, audit = owner.admit_legacy_profile_facts(text)
    assert facts == [("favorite", "ほうじ茶")]
    assert audit["admitted_count"] == 1
    assert audit["rejected_count"] == 1
    assert all("source_span_sha256" in row for row in audit["decisions"])
    assert "凪紗" not in repr(audit)
    assert "炭酸水" not in repr(audit)


@pytest.mark.parametrize("text", ["「私は紅茶が好き", "海が好き。" * 13, "海が好き。" + "x" * 513])
def test_unbounded_or_unbalanced_source_fails_closed(text):
    facts, audit = owner.admit_legacy_profile_facts(text)
    assert facts == []
    assert audit["admitted_count"] == 0
    assert audit["reason"] in {"unbalanced_quote", "clause_over_limit", "input_over_limit"}


@pytest.mark.parametrize(
    "text",
    [
        "友達が『今は玄米甘酒が好き。今の好みとして覚えといて』と言った。",
        "友達は今は玄米甘酒が好き。今の好みとして覚えといて。",
        "『今は玄米甘酒が好き』は例文。今の好みとして覚えといて。",
        "友達が『訂正。もうほうじ茶は好みじゃない。今は玄米茶が好き』と言った。",
        "友達からの伝言。今は玄米甘酒が好き。今の好みとして覚えといて。",
        "次の文は架空の人物のセリフ。今は玄米甘酒が好き。今の好みとして覚えといて。",
    ],
)
def test_p4_i_selected_quote_and_third_party_extraction_is_rejected(text):
    extraction = p4i.extract_explicit_current_preference_p4(text)
    assert extraction["selected"] is True  # Exposes the old selected-path weakness.
    allowed, audit = owner.admit_selected_current_preference(text, extraction)
    assert allowed is False
    assert audit["admitted_count"] == 0
    assert audit["rejected_count"] == 1
    assert text not in repr(audit)


def test_p4_i_frozen_three_language_write_and_correction_remain_admitted():
    contract = json.loads((ROOT / "configs/p4_i_multilingual_current_preference_contract_v1.json").read_text())
    for row in contract["sequences"]:
        for field in ("write_input", "correction_input"):
            text = row[field]
            extraction = p4i.extract_explicit_current_preference_p4(text)
            assert extraction["selected"] is True, row["id"]
            allowed, audit = owner.admit_selected_current_preference(text, extraction)
            assert allowed is True, (row["id"], field, audit.get("reason"))
            assert audit["admitted_count"] == 1
    text = "今は玄米甘酒が好き。今の好みとして覚えといて。"
    allowed, _ = owner.admit_selected_current_preference(text, p4i.extract_explicit_current_preference_p4(text))
    assert allowed is True


def test_selected_act_with_ambiguous_p4_i_extraction_cannot_fall_back(product_writer):
    text = "I prefer tea. I prefer coffee. Please remember that as my current drink preference."
    extraction = p4i.extract_explicit_current_preference_p4(text)
    assert extraction["selected"] is False
    assert extraction["classifier_cue_id"]
    with tempfile.TemporaryDirectory(prefix="p4_profile_owner_ambiguous_") as directory:
        collection = chromadb.PersistentClient(path=directory).get_or_create_collection("profile_ambiguous")
        memory = _memory(collection)
        memory._remember_profile_facts(text)
        assert _rows(collection) == []
        assert memory.session_profile == {"name": None, "likes": [], "dislikes": [], "favorites": []}
        assert memory._last_profile_owner_admission_p4["reason"] == "selected_act_ambiguous_extraction"


def test_real_chroma_negative_mixed_positive_dislike_name_and_restart_readback(product_writer):
    with tempfile.TemporaryDirectory(prefix="p4_profile_owner_") as directory:
        collection = chromadb.PersistentClient(path=directory).get_or_create_collection("profile_owner")
        memory = _memory(collection)
        negatives = [
            "友達の凪紗はルイボス茶が一番好きだ。凪紗が言った。",
            "「私は炭酸水が一番好き」は作文の例文で、私の好みじゃない。",
            "紅茶が一番好きじゃない。",
            "I like coffee and you like tea.",
            "私は海が好きけど凪紗は紅茶が好き。",
            "私は紅茶が好きじゃないけどコーヒーが好き。",
        ]
        for text in negatives:
            memory._remember_profile_facts(text)
            assert memory._last_profile_owner_admission_p4["profile_collection_count_delta"] == 0
            assert _rows(collection) == []
            assert memory.session_profile == {"name": None, "likes": [], "dislikes": [], "favorites": []}

        for text in (
            "友達の凪紗はルイボス茶が一番好き。私の一番好きな飲み物はほうじ茶。",
            "私は玄米茶が好き。友達の凪紗はルイボス茶が一番好き。",
            "「私は炭酸水が一番好き」は例文。私は海が好き。",
            "私は紅茶が嫌い。",
            "Call me Aki.",
        ):
            memory._remember_profile_facts(text)
            assert memory._last_profile_owner_admission_p4["profile_collection_count_delta"] == 1
        assert memory.session_profile == {
            "name": "Aki",
            "likes": ["海", "玄米茶"],
            "dislikes": ["紅茶"],
            "favorites": ["ほうじ茶"],
        }
        first_rows = _rows(collection)
        assert [(kind, value) for _, kind, value, _ in first_rows] == [
            ("favorite", "ほうじ茶"),
            ("like", "玄米茶"),
            ("like", "海"),
            ("dislike", "紅茶"),
            ("name", "Aki"),
        ]
        assert all(metadata["subject"] == "user" for _, _, _, metadata in first_rows)
        assert memory._last_profile_state_shadow["answer_use_authorized"] is False
        restarted = chromadb.PersistentClient(path=directory).get_collection("profile_owner")
        assert [(kind, value) for _, kind, value, _ in _rows(restarted)] == [
            (kind, value) for _, kind, value, _ in first_rows
        ]


def test_p4_i_selected_writer_keeps_history_and_rejected_selected_never_delegates(product_writer):
    with tempfile.TemporaryDirectory(prefix="p4_profile_owner_typed_") as directory:
        collection = chromadb.PersistentClient(path=directory).get_or_create_collection("profile_typed")
        memory = _memory(collection)
        write = "今はほうじ茶が好き。今の好みとして覚えといて。"
        correction = "訂正。もうほうじ茶は好みじゃない。今は玄米茶が好き。"
        memory._remember_profile_facts(write)
        assert memory._last_profile_owner_admission_p4["profile_collection_count_delta"] == 1
        assert memory._last_multilingual_current_preference_p4["status"] == "typed_current_preference_written"
        memory._remember_profile_facts(correction)
        assert memory._last_profile_owner_admission_p4["profile_collection_count_delta"] == 2
        typed = memory._last_multilingual_current_preference_p4
        assert typed["history_preserved"] is True
        assert len(typed["active_current_ids"]) == 1
        assert len(typed["historical_current_ids"]) == 1
        assert memory.session_profile["likes"] == ["玄米茶"]
        assert memory.session_profile["dislikes"] == ["ほうじ茶"]
        before_rows = _rows(collection)
        before_session = dict((key, list(value) if isinstance(value, list) else value) for key, value in memory.session_profile.items())
        for bad in (
            "友達が『今は玄米甘酒が好き。今の好みとして覚えといて』と言った。",
            "友達は今は玄米甘酒が好き。今の好みとして覚えといて。",
            "友達が『訂正。もうほうじ茶は好みじゃない。今は玄米茶が好き』と言った。",
            "友達からの伝言。今は玄米甘酒が好き。今の好みとして覚えといて。",
            "次の文は架空の人物のセリフ。今は玄米甘酒が好き。今の好みとして覚えといて。",
        ):
            memory._remember_profile_facts(bad)
            assert memory._last_profile_owner_admission_p4["profile_collection_count_delta"] == 0
            assert memory._last_multilingual_current_preference_p4["status"] == "blocked_by_profile_owner_admission_p4"
        assert _rows(collection) == before_rows
        assert memory.session_profile == before_session


def test_episode_write_survives_profile_rejection(product_writer):
    class Episodes:
        def __init__(self):
            self.added = []

        def add(self, **kwargs):
            self.added.append(kwargs)

    with tempfile.TemporaryDirectory(prefix="p4_profile_owner_episode_") as directory:
        memory = _memory(chromadb.PersistentClient(path=directory).get_or_create_collection("profile_episode"))
        memory.episode_col = Episodes()
        memory.session_turns = []
        memory._append_short_term_buffer = lambda *_: None
        memory.save_episode("友達の凪紗はルイボス茶が一番好きだ。", "うん。", "neutral", {})
        assert len(memory.episode_col.added) == 1
        assert len(memory.session_turns) == 1
        assert memory._last_saved_episode_id == memory.episode_col.added[0]["ids"][0]
        assert _rows(memory.profile_col) == []


def test_context_is_restored_on_legacy_writer_exception(product_writer, monkeypatch):
    memory = _memory(type("Collection", (), {"get": lambda *_args, **_kwargs: {"ids": []}})())
    original = owner._ORIGINAL_REMEMBER_PROFILE_FACTS

    def explode(self, text):
        assert self._extract_profile_facts(text) == [("like", "海")]
        raise RuntimeError("writer failed")

    monkeypatch.setattr(owner, "_ORIGINAL_REMEMBER_PROFILE_FACTS", explode)
    with pytest.raises(RuntimeError, match="writer failed"):
        memory._remember_profile_facts("海が好き。")
    assert owner._ADMITTED_FACTS.get() is None
    assert memory._last_profile_owner_admission_p4["writer_status"] == "writer_exception"
    assert memory._extract_profile_facts("友達の凪紗はルイボス茶が一番好き。") == [
        ("favorite", "友達の凪紗はルイボス茶")
    ]
    monkeypatch.setattr(owner, "_ORIGINAL_REMEMBER_PROFILE_FACTS", original)


def test_real_writer_audit_materializes_memory_graph_without_dialogue(product_writer):
    with tempfile.TemporaryDirectory(prefix="p4_profile_owner_graph_") as directory:
        memory = _memory(chromadb.PersistentClient(path=directory).get_or_create_collection("profile_graph"))
        text = "友達の凪紗はルイボス茶が一番好き。私は海が好き。"
        memory._remember_profile_facts(text)
        audit = memory._last_profile_owner_admission_p4
        assert audit["profile_collection_count_delta"] == 1
        assert audit["persistence_evidence"] == "collection_count_delta_not_id_attributed"
        assert audit["admitted_count"] == 1
        assert audit["rejected_count"] == 1
        result = {
            "logic": {},
            "memory_runtime": {owner.LABEL: audit},
            "runtime_trace": {"blackboard": [
                {"stage": "memory", "label": "memory_updates", "payload": {}},
                {"stage": "surface", "label": "utterance", "payload": {}},
            ]},
        }
        owner.materialize_profile_owner_admission_p4(result)
        labels = [row["label"] for row in result["runtime_trace"]["blackboard"]]
        assert labels == ["memory_updates", owner.LABEL, "utterance"]
        node = result["runtime_trace"]["blackboard"][1]
        assert node["stage"] == "memory"
        assert node["payload"]["answer_use_authorized"] is False
        assert text not in repr(node)
        assert "凪紗" not in repr(node)
        assert "海が好き" not in repr(node)


def test_additive_product_entry_installs_after_current_product_without_global_test_patch():
    script = (
        "import json; import uruha_web_ui_product_p4_profile_owner as entry; "
        "import uruha_profile_owner_admission_p4 as overlay; "
        "print(json.dumps({'installed': overlay._INSTALLED, "
        "'runtime_reused': entry.RUNTIME is entry._prior.RUNTIME, "
        "'extract_wrapped': entry._prior._base is not None}))"
    )
    completed = subprocess.run(
        [sys.executable, "-c", script], cwd=ROOT, check=True, capture_output=True, text=True, timeout=60
    )
    output = json.loads(completed.stdout.splitlines()[-1])
    assert output == {"installed": True, "runtime_reused": True, "extract_wrapped": True}
