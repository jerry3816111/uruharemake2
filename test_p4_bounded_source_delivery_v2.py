"""Developer-authored fake-collection checks for the frozen P4 v2 contract.

These fixtures are exposed development data, not a fresh Safari scenario or
an independent holdout.  No real collection, model, or browser is used.
"""

from copy import deepcopy
import json
import os
import subprocess
import sys

import pytest

import uruha_past_statement_source_answer_p4 as source_answer


VALUE = "白桃烏龍茶"
QUERY = f"Did I ever say I loved {VALUE}? If not, who did?"
CHANNEL = "bounded_source_lookup"


def episode_doc(actor="文乃", *, value=VALUE, summary_actor=None, user=None, summary=None, reply="ん。"):
    user = user if user is not None else f"友達の{actor}は{value}が一番好きだ。{actor}が言った。"
    summary = summary if summary is not None else f"友達の{summary_actor or actor}は{value}が一番好きだ"
    return (
        "Time: 2026-10-01 08:00 | Intent: general_conversation | Scene: casual | "
        "CognitiveMode: direct | PremiseCheck: accept | Routing: high_road | "
        f"User: {user} | Summary: {summary} | Uruha: {reply} | Mood: neutral"
    )


def result_rows(*rows):
    return {
        "ids": [row[0] for row in rows],
        "documents": [row[1] for row in rows],
        "metadatas": [{"source": "turn_episode"} for _ in rows],
    }


def already_passed(memory_id, document):
    return {
        "source": "episode",
        "collection_name": "episode",
        "channel": "direct_episode",
        "memory_id": memory_id,
        "trace_id": f"stored:episode:{memory_id}",
        "text": document,
    }


class FakeCollection:
    def __init__(self, result=None, error=None):
        self.result = deepcopy(result) if result is not None else result_rows()
        self.error = error
        self.calls = []

    def get(self, **kwargs):
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return deepcopy(self.result)


class FakeMemory:
    def __init__(self, collection):
        self.episode_col = collection


def invoke(monkeypatch, collection, *, query=QUERY, passed=(), predecessor=None):
    if predecessor is None:
        predecessor = {
        "episodes": "既有 direct episode 結果不應改寫",
        "working_memory_items": [{"source": "episode", "memory_id": "ranked-keep"}],
        "memory_provenance": {
            "candidate_pool": [{"source": "episode", "memory_id": "ranked-keep", "rank": 1}],
            "selected_working_memory_trace_ids": ["stored:episode:ranked-keep"],
            "passed_to_leftbrain": deepcopy(list(passed)),
            "passed_to_leftbrain_trace_ids": [row["trace_id"] for row in passed],
        },
        }
    monkeypatch.setattr(
        source_answer,
        "_ORIGINAL_QUERY",
        lambda _self, _text: deepcopy(predecessor),
    )
    memory = source_answer.query_all_layers_with_past_statement_source_p4(
        FakeMemory(collection), query
    )
    return memory, memory[source_answer.LABEL]


def added_rows(memory):
    return [
        row
        for row in memory["memory_provenance"]["passed_to_leftbrain"]
        if row.get("channel") == CHANNEL
    ]


def assert_abstains(contract):
    assert contract["selected"] is True
    assert contract["answer_use_authorized"] is False
    assert contract["selected_actor"] is None
    assert "分からない" in contract["selected_core_jp"] or "断定しない" in contract["selected_core_jp"]


def test_literal_lookup_delivers_true_id_trace_and_friend_prefixed_summary(monkeypatch):
    document = episode_doc()
    collection = FakeCollection(result_rows(("fresh-episode-1", document)))

    memory, contract = invoke(monkeypatch, collection)

    assert collection.calls == [{
        "where": {"source": "turn_episode"},
        "where_document": {"$contains": VALUE},
        "limit": 9,
        "include": ["documents", "metadatas"],
    }]
    assert contract["status"] == "resolved_third_party_source"
    assert contract["selected_speaker_role"] == "third_party"
    assert contract["selected_actor"] == "文乃"
    assert contract["source_memory_ids"] == ["fresh-episode-1"]
    assert contract["source_trace_ids"] == ["stored:episode:fresh-episode-1"]
    assert "文乃" in contract["selected_core_jp"]
    assert "白桃烏龍茶" in contract["selected_core_jp"]
    assert len(added_rows(memory)) == 1
    assert added_rows(memory)[0]["memory_id"] == "fresh-episode-1"
    assert added_rows(memory)[0]["trace_id"] == "stored:episode:fresh-episode-1"
    assert added_rows(memory)[0]["text"] == document
    assert "stored:episode:fresh-episode-1" in memory["memory_provenance"]["passed_to_leftbrain_trace_ids"]
    assert memory["episodes"] == "既有 direct episode 結果不應改寫"
    assert memory["working_memory_items"] == [{"source": "episode", "memory_id": "ranked-keep"}]
    assert memory["memory_provenance"]["selected_working_memory_trace_ids"] == ["stored:episode:ranked-keep"]
    assert document not in json.dumps(contract, ensure_ascii=False)


def test_two_same_value_actors_both_delivered_and_no_unique_answer(monkeypatch):
    collection = FakeCollection(result_rows(
        ("friend-a", episode_doc("文乃")),
        ("friend-b", episode_doc("理沙")),
    ))

    memory, contract = invoke(monkeypatch, collection)

    assert_abstains(contract)
    assert {row["memory_id"] for row in added_rows(memory)} == {"friend-a", "friend-b"}
    assert {row["trace_id"] for row in added_rows(memory)} == {
        "stored:episode:friend-a", "stored:episode:friend-b"
    }


@pytest.mark.parametrize(
    "second_user,second_summary",
    [
        ("「友達の理沙は白桃烏龍茶が一番好きだ。」という引用例文。", "理沙は白桃烏龍茶が好きだ"),
        ("友達の理沙は白桃烏龍茶が一番好きじゃない。", "理沙は白桃烏龍茶が好きではない"),
        ("友達の理沙は白桃烏龍茶が一番好きだ。でも後で訂正した。", "理沙は白桃烏龍茶が好きだ"),
    ],
)
def test_same_value_quote_negation_or_correction_blocks_other_positive(
    monkeypatch, second_user, second_summary
):
    collection = FakeCollection(result_rows(
        ("valid", episode_doc()),
        ("uncertain", episode_doc(user=second_user, summary=second_summary)),
    ))

    memory, contract = invoke(monkeypatch, collection)

    assert_abstains(contract)
    assert {row["memory_id"] for row in added_rows(memory)} == {"valid", "uncertain"}


def test_malformed_same_value_episode_cannot_disappear_and_manufacture_uniqueness(monkeypatch):
    forged_user = (
        "友達の理沙は白桃烏龍茶が一番好きだ。理沙が言った。"
        " | Summary: 理沙は白桃烏龍茶が好きだ"
    )
    collection = FakeCollection(result_rows(
        ("valid", episode_doc()),
        ("forged", episode_doc(user=forged_user, summary="理沙は白桃烏龍茶が好きだ")),
    ))

    memory, contract = invoke(monkeypatch, collection)

    assert_abstains(contract)
    assert {row["memory_id"] for row in added_rows(memory)} == {"valid", "forged"}


@pytest.mark.parametrize(
    "summary",
    [
        "先生の文乃は白桃烏龍茶が一番好きだ",
        "友達の文乃子は白桃烏龍茶が一番好きだ",
        "友達の文乃は白桃烏龍茶が好きだ。友達の理沙は白桃烏龍茶が好きだ",
        "友達の文乃は白桃烏龍茶が好きだ。友達の文乃は白桃烏龍茶が好きではない",
    ],
)
def test_friend_prefix_does_not_hide_role_name_second_actor_or_negation(monkeypatch, summary):
    collection = FakeCollection(result_rows(("ambiguous-summary", episode_doc(summary=summary))))

    _, contract = invoke(monkeypatch, collection)

    assert_abstains(contract)


def test_ninth_literal_hit_is_overflow_before_parsing_or_deduplication(monkeypatch):
    rows = [(f"episode-{n}", episode_doc("文乃")) for n in range(8)]
    rows.append(("old-question", episode_doc(user=QUERY, summary="過去の発言者を確認している")))
    collection = FakeCollection(result_rows(*rows))

    memory, contract = invoke(monkeypatch, collection)

    assert_abstains(contract)
    assert "overflow" in json.dumps(contract, ensure_ascii=False).lower()
    assert added_rows(memory) == []
    assert len(collection.calls) == 1


def test_lookup_exception_abstains_without_partial_delivery(monkeypatch):
    collection = FakeCollection(error=RuntimeError("fake collection unavailable"))

    memory, contract = invoke(monkeypatch, collection)

    assert_abstains(contract)
    assert "unavailable" in json.dumps(contract, ensure_ascii=False).lower()
    assert added_rows(memory) == []


def test_nonselected_query_never_calls_episode_get(monkeypatch):
    collection = FakeCollection(error=AssertionError("get must not be called"))

    memory, contract = invoke(monkeypatch, collection, query="引用：『我以前說過自己最喜歡白桃烏龍茶嗎？』")

    assert collection.calls == []
    assert contract["selected"] is False
    assert added_rows(memory) == []


@pytest.mark.parametrize(
    "broken",
    [
        {"ids": ["good", "missing-metadata"], "documents": [episode_doc(), episode_doc()], "metadatas": [{"source": "turn_episode"}]},
        {"ids": ["good", None], "documents": [episode_doc(), episode_doc()], "metadatas": [{"source": "turn_episode"}, {"source": "turn_episode"}]},
        {"ids": ["same", "same"], "documents": [episode_doc(), episode_doc()], "metadatas": [{"source": "turn_episode"}, {"source": "turn_episode"}]},
        {"ids": ["good", "wrong-source"], "documents": [episode_doc(), episode_doc()], "metadatas": [{"source": "turn_episode"}, {"source": "episodic_consolidation"}]},
        {"ids": ["good", "not-a-document"], "documents": [episode_doc(), None], "metadatas": [{"source": "turn_episode"}, {"source": "turn_episode"}]},
        {"ids": ["good", "oversized"], "documents": [episode_doc(), episode_doc(reply="あ" * 2050)], "metadatas": [{"source": "turn_episode"}, {"source": "turn_episode"}]},
    ],
    ids=["length-mismatch", "missing-id", "duplicate-id", "wrong-metadata", "non-string-document", "oversized-document"],
)
def test_invalid_lookup_response_abstains_atomically(monkeypatch, broken):
    collection = FakeCollection(broken)

    memory, contract = invoke(monkeypatch, collection)

    assert_abstains(contract)
    assert "unavailable" in json.dumps(contract, ensure_ascii=False).lower()
    assert added_rows(memory) == []


def test_already_delivered_same_id_is_not_duplicated(monkeypatch):
    document = episode_doc()
    collection = FakeCollection(result_rows(("same-id", document)))

    memory, contract = invoke(monkeypatch, collection, passed=[already_passed("same-id", document)])

    assert contract["status"] == "resolved_third_party_source"
    assert added_rows(memory) == []
    assert memory["memory_provenance"]["passed_to_leftbrain_trace_ids"].count("stored:episode:same-id") == 1


def test_assistant_only_literal_match_cannot_supply_a_source_or_block_one(monkeypatch):
    assistant_only = episode_doc(
        user="今日は本棚を片づけた。",
        summary="本棚を片づける話をした",
        reply=f"{VALUE}を飲もう",
    )
    collection = FakeCollection(result_rows(
        ("valid", episode_doc()),
        ("assistant-only", assistant_only),
    ))

    memory, contract = invoke(monkeypatch, collection)

    assert contract["status"] == "resolved_third_party_source"
    assert contract["selected_actor"] == "文乃"
    assert {row["memory_id"] for row in added_rows(memory)} == {"valid", "assistant-only"}
    assert contract["source_memory_ids"] == ["valid"]


def test_complete_previous_question_is_nonassertive_even_when_lookup_matches(monkeypatch):
    prior_question = episode_doc(user=QUERY, summary="過去の発言者を確認している")
    collection = FakeCollection(result_rows(
        ("valid", episode_doc()),
        ("prior-question", prior_question),
    ))

    memory, contract = invoke(monkeypatch, collection)

    assert contract["status"] == "resolved_third_party_source"
    assert contract["selected_actor"] == "文乃"
    assert {row["memory_id"] for row in added_rows(memory)} == {"valid", "prior-question"}
    assert contract["source_memory_ids"] == ["valid"]


def test_lookup_cannot_authorize_nfkc_only_document_without_literal_value(monkeypatch):
    query_value = "カモミール茶"
    query = f"Did I ever say I loved {query_value}? If not, who did?"
    variant = episode_doc("文乃", value="ｶﾓﾐｰﾙ茶")
    collection = FakeCollection(result_rows(("variant-only", variant)))

    _, contract = invoke(monkeypatch, collection, query=query)

    assert_abstains(contract)


def test_other_delivered_nfkc_equal_source_outside_lookup_ids_blocks_answer(monkeypatch):
    query_value = "カモミール茶"
    query = f"Did I ever say I loved {query_value}? If not, who did?"
    literal = episode_doc("文乃", value=query_value)
    variant = episode_doc("理沙", value="ｶﾓﾐｰﾙ茶")
    collection = FakeCollection(result_rows(("literal", literal)))

    memory, contract = invoke(
        monkeypatch,
        collection,
        query=query,
        passed=[already_passed("variant", variant)],
    )

    assert_abstains(contract)
    assert {row["memory_id"] for row in added_rows(memory)} == {"literal"}
    assert "stored:episode:variant" in memory["memory_provenance"]["passed_to_leftbrain_trace_ids"]


def test_prepassed_same_id_with_stale_text_cannot_hide_second_lookup_actor(monkeypatch):
    """A stale direct copy must not cause lookup A to be skipped and B selected."""
    current_a = episode_doc("文乃")
    current_b = episode_doc("理沙")
    stale_a = episode_doc("文乃", value="別の茶")
    collection = FakeCollection(result_rows(
        ("actor-a", current_a),
        ("actor-b", current_b),
    ))

    memory, contract = invoke(
        monkeypatch,
        collection,
        passed=[already_passed("actor-a", stale_a)],
    )

    assert_abstains(contract)
    assert contract["selected_actor"] is None
    assert memory["memory_provenance"]["passed_to_leftbrain"][0]["text"] == stale_a
    assert "incomplete" in json.dumps(contract, ensure_ascii=False).lower()


def test_real_isolated_chroma_get_preserves_cjk_literal_filter_metadata_and_flat_ids(tmp_path):
    """Verify the actual local Chroma response shape without embedding/model calls."""
    import chromadb

    client = chromadb.PersistentClient(path=str(tmp_path / "chroma"))
    collection = client.get_or_create_collection("p4_v2_literal_get")
    literal = episode_doc("文乃", value="カモミール茶")
    variant = episode_doc("理沙", value="ｶﾓﾐｰﾙ茶")
    collection.add(
        ids=["literal", "nfkc-variant", "wrong-metadata"],
        documents=[literal, variant, literal],
        metadatas=[
            {"source": "turn_episode"},
            {"source": "turn_episode"},
            {"source": "episodic_consolidation"},
        ],
        embeddings=[[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
    )

    result = collection.get(
        where={"source": "turn_episode"},
        where_document={"$contains": "カモミール茶"},
        limit=9,
        include=["documents", "metadatas"],
    )

    assert result["ids"] == ["literal"]  # flat, not query-style nested IDs
    assert result["documents"] == [literal]
    assert result["metadatas"] == [{"source": "turn_episode"}]
    assert "ｶﾓﾐｰﾙ茶" not in result["documents"][0]


def test_real_isolated_chroma_ninth_hit_is_overflow_sentinel(tmp_path, monkeypatch):
    import chromadb

    client = chromadb.PersistentClient(path=str(tmp_path / "chroma"))
    collection = client.get_or_create_collection("p4_v2_ninth_hit")
    ids = [f"literal-{index}" for index in range(9)]
    collection.add(
        ids=ids,
        documents=[episode_doc("文乃") for _ in ids],
        metadatas=[{"source": "turn_episode"} for _ in ids],
        embeddings=[[float(index), 0.0, 1.0] for index in range(9)],
    )
    collection.add(
        ids=["wrong-metadata"],
        documents=[episode_doc("理沙")],
        metadatas=[{"source": "episodic_consolidation"}],
        embeddings=[[9.0, 0.0, 1.0]],
    )

    response = collection.get(
        where={"source": "turn_episode"},
        where_document={"$contains": VALUE},
        limit=9,
        include=["documents", "metadatas"],
    )
    assert len(response["ids"]) == len(response["documents"]) == len(response["metadatas"]) == 9
    assert set(response["ids"]) == set(ids)
    assert all(metadata["source"] == "turn_episode" for metadata in response["metadatas"])

    memory, contract = invoke(monkeypatch, collection)
    assert_abstains(contract)
    assert "overflow" in json.dumps(contract, ensure_ascii=False).lower()
    assert added_rows(memory) == []


def test_lookup_and_source_nodes_connect_to_plan_with_matching_final_surface(monkeypatch):
    from uruha_memory_observatory import collect_cognitive_graph

    collection = FakeCollection(result_rows(("graph-source", episode_doc())))
    memory, contract = invoke(monkeypatch, collection)
    assert contract["status"] == "resolved_third_party_source"
    result = {
        "user_text": QUERY,
        "reply": contract["selected_core_jp"],
        "memory_data": memory,
        "logic": {source_answer.LABEL: deepcopy(contract)},
        "runtime_trace": {"blackboard": [
            {"stage": "retrieve", "label": "memory_layers", "payload": {}},
            {"stage": "retrieve", "label": "working_memory", "payload": {}},
            {"stage": "select", "label": "selected_plan", "payload": {}},
            {"stage": "surface", "label": "utterance", "payload": {"text": contract["selected_core_jp"]}},
        ]},
    }

    source_answer.materialize_past_statement_source_p4(result)
    source_answer.materialize_past_statement_source_p4(result)
    rows = result["runtime_trace"]["blackboard"]
    lookup_rows = [row for row in rows if row.get("label") == source_answer.SOURCE_LOOKUP_LABEL]
    source_rows = [row for row in rows if row.get("label") == source_answer.LABEL]
    assert len(lookup_rows) == len(source_rows) == 1
    assert lookup_rows[0]["payload"]["source_memory_ids"] == ["graph-source"]
    assert source_rows[0]["payload"]["source_memory_ids"] == ["graph-source"]
    assert source_rows[0]["payload"]["source_trace_ids"] == ["stored:episode:graph-source"]
    assert result["reply"] == result["logic"][source_answer.LABEL]["final_visible_surface_jp"]
    assert result["logic"][source_answer.LABEL]["final_visible_surface_matches_contract"] is True

    graph = collect_cognitive_graph(result)
    by_label = {node["label"]: node for node in graph["nodes"]}
    lookup_node = by_label[source_answer.SOURCE_LOOKUP_LABEL]
    source_node = by_label[source_answer.LABEL]
    plan_node = by_label["selected_plan"]
    edges = {(edge["source"], edge["target"], edge["class"]) for edge in graph["edges"]}
    assert (lookup_node["id"], source_node["id"], "is-main") in edges
    assert (source_node["id"], plan_node["id"], "is-main") in edges
    memory_nodes = [
        node for node in graph["nodes"]
        if node.get("memory") and node.get("trace_id") == "stored:episode:graph-source"
    ]
    assert len(memory_nodes) == 1
    assert memory_nodes[0]["active"] is True


def test_isolated_fake_full_brain_uses_bounded_lookup_for_named_japanese_answer(tmp_path, monkeypatch):
    """Exercise real route/plan/guard/graph with invoke-built evidence, no model."""
    collection = FakeCollection(result_rows(("full-brain-source", episode_doc())))
    memory_data, initial_contract = invoke(monkeypatch, collection, predecessor={
        "knowledge": "",
        "episodes": "",
        "wisdom": "",
        "profile": "",
        "profile_structured": {},
        "profile_grounding_request": None,
        "recent_turns": [],
        "working_memory_items": [],
        "working_memory_summary": "無短期緩衝",
        "memory_provenance": {},
        "procedural_summary": "無程序記憶",
    })
    assert initial_contract["status"] == "resolved_third_party_source"
    assert memory_data[source_answer.SOURCE_LOOKUP_LABEL]["status"] == "complete"
    assert added_rows(memory_data)[0]["trace_id"] == "stored:episode:full-brain-source"

    program = r'''
import json, os, sys
from copy import deepcopy
from pathlib import Path
root = Path(os.environ["P4_V2_FULL_BRAIN_ROOT"])
os.environ["URUHA_ADAPTIVE_PERSON_MODEL_PATH"] = str(root / "adaptive.json")
os.environ["URUHA_MEMORY_DB_PATH"] = str(root / "memory")
os.environ["URUHA_WEB_PREWARM_BRAIN"] = "0"
os.environ["URUHA_IDLE_VISIBLE_PROACTIVE_ENABLED"] = "false"
os.environ["GRADIO_ANALYTICS_ENABLED"] = "false"
import project_paths
project_paths.WEB_LOG_DIR = str(root / "web")
project_paths.WEB_CONVERSATION_LOG_JSONL_PATH = str(root / "web/turns.jsonl")
project_paths.WEB_CONVERSATION_LOG_TXT_PATH = str(root / "web/turns.txt")
import uruha_web_ui_product_p4_past_source as entry
from test_personhood_loop_v2_13 import _IsolatedContractBrain, _FakeMemory
from uruha_brain_mac import LeftBrain, RightBrain
from uruha_memory_observatory import collect_cognitive_graph
import uruha_past_statement_source_answer_p4 as source
fixture = json.load(sys.stdin)
query, memory_data = fixture["query"], fixture["memory_data"]
class Memory(_FakeMemory):
    def query_all_layers(self, text):
        assert text == query
        return deepcopy(memory_data)
brain = _IsolatedContractBrain()
brain.memory = Memory()
brain.left_brain = LeftBrain(None)
brain.right_brain = RightBrain(load_model=False)
brain.right_brain.speak = lambda _text, logic, _memory, _psyche: str(logic.get("core_message_jp") or "まだ分かんない。")
result = brain.run_turn_debug(query)
contract = result["logic"][source.LABEL]
assert contract["status"] == "resolved_third_party_source", contract
assert contract["answer_use_authorized"] is True, contract
assert contract["visible_surface_status"] == "matched", contract
assert contract["final_visible_surface_matches_contract"] is True, contract
assert result["reply"] == contract["selected_core_jp"] == contract["final_visible_surface_jp"]
assert result["reply"] != source._SOURCE_ABSTENTION_JP
assert "文乃" in result["reply"] and "白桃烏龍茶" in result["reply"]
assert "分からない" not in result["reply"] and "断定しない" not in result["reply"]
assert result["logic"]["visible_language_guard"]["final_reply"] == result["reply"]
route = result["logic"]["semantic_route_m22"]
assert route["selected_type"] == "factual_or_memory" and route["contract_status"] == "matched", route
assert route["performed_route"] == "deterministic_rule_plan", route
assert result["logic"]["bounded_slow_path_m21"]["model_call_attempted"] is False
assert contract["source_memory_ids"] == ["full-brain-source"]
assert contract["source_trace_ids"] == ["stored:episode:full-brain-source"]
assert "stored:episode:full-brain-source" in result["memory_data"]["memory_provenance"]["passed_to_leftbrain_trace_ids"]
graph = collect_cognitive_graph(result)
lookup_nodes = [node for node in graph["nodes"] if node["label"] == source.SOURCE_LOOKUP_LABEL]
source_nodes = [node for node in graph["nodes"] if node["label"] == source.LABEL]
assert len(lookup_nodes) == len(source_nodes) == 1, (lookup_nodes, source_nodes)
assert any(edge["source"] == lookup_nodes[0]["id"] and edge["target"] == source_nodes[0]["id"] for edge in graph["edges"])
memory_nodes = [node for node in graph["nodes"] if node.get("memory") and node.get("trace_id") == "stored:episode:full-brain-source"]
assert len(memory_nodes) == 1 and memory_nodes[0]["active"] is True, memory_nodes
assert result["runtime_trace"][source.LABEL]["final_visible_surface_jp"] == result["reply"]
assert entry.RUNTIME is entry._prior.RUNTIME
print(json.dumps({"reply": result["reply"], "route": route["selected_type"], "lookup": lookup_nodes[0]["label"]}, ensure_ascii=False))
'''
    completed = subprocess.run(
        [sys.executable, "-c", program],
        input=json.dumps({"query": QUERY, "memory_data": memory_data}, ensure_ascii=False),
        env={**os.environ, "P4_V2_FULL_BRAIN_ROOT": str(tmp_path)},
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    # The brain prints diagnostic trace to stdout; only the final JSON record
    # below represents the captured user-visible answer.
    final_record = json.loads(completed.stdout.splitlines()[-1])
    assert "full-brain-source" not in final_record["reply"]
    assert "文乃" in final_record["reply"] and "白桃烏龍茶" in final_record["reply"]
