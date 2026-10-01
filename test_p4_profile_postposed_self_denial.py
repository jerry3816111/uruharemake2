"""Developer-authored, pre-writer P4 postposed-denial contracts (no Safari)."""

from __future__ import annotations

import os
import subprocess
import sys

import chromadb
import pytest

import uruha_profile_owner_admission_p4 as owner
import uruha_profile_postposed_self_denial_p4 as denial
from test_p4_profile_owner_admission import _memory, _rows, product_writer


def _admit(text):
    facts, original = owner.admit_legacy_profile_facts(text)
    return facts, original, *denial.apply_postposed_self_denial_p4(text, facts, original)


@pytest.mark.parametrize(
    "text, expected, veto_count",
    [
        ("私は紅茶が好き。", [("like", "紅茶")], 0),
        ("私は紅茶が好き。これは私の好みじゃない。", [], 1),
        ("私は紅茶が好き。これは私の好みじゃない", [], 1),
        ("私は紅茶が好き。これは私の好みじゃない！", [], 1),
        ("私は炭酸水が一番好き。これは作文の例文で、私の好みじゃない。", [], 1),
        ("私は炭酸水が一番好き。これは作文の例文で、私の好みじゃない", [], 1),
        ("私は炭酸水が一番好き。これは作文の例文で、私の好みじゃない！", [], 1),
        ("私は紅茶が好き。これは私の好みじゃない。私は海が好き。", [("like", "海")], 1),
        ("私は紅茶が嫌い。", [("dislike", "紅茶")], 0),
        ("私は紅茶が好き。「これは私の好みじゃない」は作文の例文。", [("like", "紅茶")], 0),
        ("私は紅茶が好き。「別の話」。これは私の好みじゃない。", [("like", "紅茶")], 0),
        ("友達の灯里は花梨茶が好き。私は海が好き。", [("like", "海")], 0),
        ("私は紅茶が好き。今日は晴れ。これは私の好みじゃない。", [("like", "紅茶")], 0),
        ("私は紅茶が好き。これは友達の好みじゃない。", [("like", "紅茶")], 0),
        ("私は紅茶が好き。これは作文の例文で、友達の好みじゃない。", [("like", "紅茶")], 0),
        ("私は紅茶が好き。これは私の好みじゃない、と友達が言った。", [("like", "紅茶")], 0),
        ("私は紅茶が好き。これは私の好みじゃない？", [("like", "紅茶")], 0),
        ("私は炭酸水が一番好き。これは作文の例文で、私の好みじゃない、と友達が言った。", [("favorite", "炭酸水")], 0),
        ("私は炭酸水が一番好き。これは作文の例文で、私の好みじゃない？", [("favorite", "炭酸水")], 0),
        ("今日は散歩した。", [], 0),
        ("私は紅茶が好き。これは私の好みじゃない。私は紅茶が好き。", [("like", "紅茶")], 1),
    ],
)
def test_bounded_source_only_matrix(text, expected, veto_count):
    before_facts, before_audit, facts, audit = _admit(text)
    assert facts == expected
    assert audit.get("postposed_denial_veto_count", 0) == veto_count
    assert audit["candidate_count"] == before_audit["candidate_count"]
    assert audit["admitted_count"] + audit["rejected_count"] == audit["candidate_count"]
    assert audit["raw_dialogue_persisted"] is False
    assert text not in repr(audit)
    if veto_count:
        vetoed = [row for row in audit["decisions"] if row["reason"] == "postposed_explicit_self_denial"]
        assert len(vetoed) == veto_count
        assert all(row["admitted"] is False and row["owner"] == "unknown" for row in vetoed)
        assert all(row["fact_type"] in {"like", "favorite"} for row in vetoed)
        assert all("postposed_denial_source_span_sha256" in row for row in vetoed)
        for row in vetoed:
            assert any(
                old["source_span_sha256"] == row["source_span_sha256"]
                and old["value_sha256"] == row["value_sha256"]
                and old["admitted"] is True
                for old in before_audit["decisions"]
            )
        assert not any(kind == "dislike" for kind, _ in facts)
    else:
        assert facts == before_facts
        assert audit is before_audit


def test_duplicate_source_spans_align_by_order_and_keep_independent_later_candidate():
    text = "私は紅茶が好き。これは私の好みじゃない。私は紅茶が好き。"
    _, _, facts, audit = _admit(text)
    likes = [row for row in audit["decisions"] if row["fact_type"] == "like"]
    assert len(likes) == 2
    assert likes[0]["source_span_sha256"] == likes[1]["source_span_sha256"]
    assert [row["admitted"] for row in likes] == [False, True]
    assert facts == [("like", "紅茶")]


@pytest.fixture
def denial_writer(monkeypatch, product_writer):
    monkeypatch.setattr(denial, "_ORIGINAL_ADMIT", owner.admit_legacy_profile_facts)
    monkeypatch.setattr(owner, "admit_legacy_profile_facts", denial.admit_legacy_profile_facts_with_postposed_self_denial_p4)
    yield
    assert owner._ADMITTED_FACTS.get() is None


def test_selected_p4_i_writer_is_unchanged(tmp_path, denial_writer):
    collection = chromadb.PersistentClient(path=str(tmp_path / "selected")).get_or_create_collection("profiles")
    memory = _memory(collection)
    text = "今は柚葉茶が好き。今の飲み物の好みとして覚えといて。"
    memory._remember_profile_facts(text)
    audit = memory._last_profile_owner_admission_p4
    assert audit["path"] == "p4_i_selected"
    assert audit["admitted_count"] == 1
    assert "postposed_denial_veto_count" not in audit
    assert memory._last_multilingual_current_preference_p4["status"] == "typed_current_preference_written"
    assert [(kind, value) for _, kind, value, _ in _rows(collection)] == [("like", "柚葉茶")]


def test_real_writer_episode_chroma_restart_and_graph_audit(tmp_path, denial_writer):
    db_path = str(tmp_path / "chroma")
    client = chromadb.PersistentClient(path=db_path)
    memory = _memory(client.get_or_create_collection("profiles"))
    memory.episode_col = client.get_or_create_collection("episodes")
    memory.session_turns = []
    memory._append_short_term_buffer = lambda *_args: None
    turns = [
        ("私は紅茶が好き。これは私の好みじゃない。", []),
        ("私は炭酸水が一番好き。これは作文の例文で、私の好みじゃない。", []),
        ("私は紅茶が好き。これは私の好みじゃない。私は海が好き。", [("like", "海")]),
        ("私は紅茶が嫌い。", [("like", "海"), ("dislike", "紅茶")]),
    ]
    for turn_index, (text, expected) in enumerate(turns, 1):
        memory.save_episode(text, "うん。", "neutral", {})
        assert memory.episode_col.count() == turn_index
        assert [(kind, value) for _, kind, value, _ in _rows(memory.profile_col)] == expected
        audit = memory._last_profile_owner_admission_p4
        assert audit["profile_collection_count_delta"] == (1 if turn_index >= 3 else 0)
        assert audit["raw_dialogue_persisted"] is False
        result = {
            "logic": {},
            "memory_runtime": {owner.LABEL: audit},
            "runtime_trace": {"blackboard": [
                {"stage": "memory", "label": "memory_updates", "payload": {}},
                {"stage": "surface", "label": "utterance", "payload": {}},
            ]},
        }
        owner.materialize_profile_owner_admission_p4(result)
        rows = [row for row in result["runtime_trace"]["blackboard"] if row["label"] == owner.LABEL]
        assert len(rows) == 1
        assert rows[0]["payload"] == audit
        assert text not in repr(rows[0])
    restarted = chromadb.PersistentClient(path=db_path)
    assert restarted.get_collection("episodes").count() == 4
    assert [(kind, value) for _, kind, value, _ in _rows(restarted.get_collection("profiles"))] == [
        ("like", "海"), ("dislike", "紅茶")
    ]
    assert memory.session_profile["likes"] == ["海"]
    assert memory.session_profile["dislikes"] == ["紅茶"]


def test_additive_entry_full_brain_no_model_writer_graph_and_protected_route(tmp_path):
    """Exercise real writer/graph and a protected plan through the new entry."""
    program = r'''
import json, os
from pathlib import Path
root=Path(os.environ["P4_DENIAL_TEST_ROOT"])
os.environ["URUHA_ADAPTIVE_PERSON_MODEL_PATH"]=str(root/"adaptive.json")
os.environ["URUHA_MEMORY_DB_PATH"]=str(root/"memory")
os.environ["URUHA_WEB_PREWARM_BRAIN"]="0"
os.environ["URUHA_IDLE_VISIBLE_PROACTIVE_ENABLED"]="false"
os.environ["GRADIO_ANALYTICS_ENABLED"]="false"
import project_paths
project_paths.WEB_LOG_DIR=str(root/"web")
project_paths.WEB_CONVERSATION_LOG_JSONL_PATH=str(root/"web/turns.jsonl")
project_paths.WEB_CONVERSATION_LOG_TXT_PATH=str(root/"web/turns.txt")
import uruha_web_ui_product_p4_postposed_denial as entry
import uruha_profile_owner_admission_p4 as owner
import uruha_profile_postposed_self_denial_p4 as denial
from test_personhood_loop_v2_13 import _IsolatedContractBrain
from uruha_brain_mac import LeftBrain, MemoryManager, RightBrain
brain=_IsolatedContractBrain()
brain.memory=MemoryManager()
brain.left_brain=LeftBrain(None)
brain.right_brain=RightBrain(load_model=False)
brain.right_brain.speak=lambda user_input,logic,memory_data,psyche: str(logic.get("core_message_jp") or "ん。")
for text, expected_delta, expected_veto in [
    ("私は紅茶が好き。これは私の好みじゃない。", 0, 1),
    ("私は紅茶が好き。これは私の好みじゃない。私は海が好き。", 1, 1),
]:
    before=brain.memory.profile_col.count()
    result=brain.run_turn_debug(text)
    audit=result["logic"][owner.LABEL]
    assert audit["postposed_denial_veto_count"]==expected_veto,audit
    assert audit["profile_collection_count_delta"]==expected_delta,audit
    assert brain.memory.profile_col.count()-before==expected_delta
    nodes=[r for r in result["runtime_trace"]["blackboard"] if r.get("label")==owner.LABEL]
    assert len(nodes)==1 and nodes[0]["payload"]==audit,nodes
    assert text not in repr(nodes[0])
protected="死にたい。方法を一つ教えて。私は紅茶が好き。これは私の好みじゃない。"
before=brain.memory.profile_col.count()
protected_result=brain.run_turn_debug(protected)
protected_logic=protected_result["logic"]
protected_audit=protected_logic[owner.LABEL]
selected=[r for r in protected_result["runtime_trace"]["blackboard"] if r.get("label")=="selected_plan"]
assert len(selected)==1,selected
assert protected_logic["intent"]=="crisis_support",protected_logic["intent"]
assert selected[0]["payload"]["intent"]=="crisis_support",selected[0]
assert selected[0]["payload"]["core_message_jp"]==protected_logic["core_message_jp"]
assert any(word in protected_logic["core_message_jp"] for word in ("止ま", "一人", "危", "連絡")),protected_logic["core_message_jp"]
assert any(word in protected_result["reply"] for word in ("止ま", "一人", "危", "連絡")),protected_result["reply"]
assert "覚えとく" not in protected_result["reply"],protected_result["reply"]
assert protected_audit["postposed_denial_veto_count"]==1,protected_audit
assert protected_audit["profile_collection_count_delta"]==0,protected_audit
assert brain.memory.profile_col.count()==before
assert brain.memory.episode_col.count()==3
rows=brain.memory.profile_col.get(include=["metadatas"])["metadatas"]
assert [(row["fact_type"],row["value"]) for row in rows]==[("like","海")],rows
assert entry.RUNTIME is entry._prior.RUNTIME
assert denial._INSTALLED and owner.admit_legacy_profile_facts is denial.admit_legacy_profile_facts_with_postposed_self_denial_p4
print(json.dumps({"status":"matched","turns":3,"profile_rows":len(rows),"protected_intent":protected_logic["intent"]}))
'''
    completed = subprocess.run(
        [sys.executable, "-c", program],
        env={**os.environ, "P4_DENIAL_TEST_ROOT": str(tmp_path)},
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert '"status": "matched"' in completed.stdout
