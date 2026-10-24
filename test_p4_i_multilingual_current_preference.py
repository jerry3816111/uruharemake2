import json
from pathlib import Path
import tempfile

import chromadb

import uruha_multilingual_current_preference_p4 as p4i
from uruha_brain_mac import MemoryManager


ROOT = Path(__file__).resolve().parent
CONTRACT = ROOT / "configs" / "p4_i_multilingual_current_preference_contract_v1.json"


def _contract():
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


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


def _collection(tempdir, name):
    return chromadb.PersistentClient(path=tempdir).get_or_create_collection(name)


def test_frozen_multilingual_sequences_extract_exact_values_and_scope():
    for row in _contract()["sequences"]:
        write = p4i.extract_explicit_current_preference_p4(row["write_input"])
        correction = p4i.extract_explicit_current_preference_p4(row["correction_input"])
        assert write["selected"] is True, row["id"]
        assert write["act"] == "write"
        assert write["language"] == row["language"]
        assert write["scope"] == row["scope"]
        assert write["current_value"] == row["write_value"]
        assert correction["selected"] is True, row["id"]
        assert correction["act"] == "correction"
        assert correction["language"] == row["language"]
        assert correction["previous_value"] == row["old_value"]
        assert correction["current_value"] == row["new_value"]
        assert row["write_input"] not in repr(write)
        assert row["correction_input"] not in repr(correction)


def test_each_language_write_and_correction_preserves_same_scope_history():
    for index, row in enumerate(_contract()["sequences"]):
        with tempfile.TemporaryDirectory(prefix=f"uruha_p4_i_{row['language']}_") as tempdir:
            memory = _memory(_collection(tempdir, f"p4_i_{row['language']}"))
            write = p4i.remember_explicit_current_preference_p4(
                memory,
                row["write_input"],
                timestamp=f"2026-09-21T10:00:0{index}+08:00",
            )
            assert write["status"] == "typed_current_preference_written", row["id"]
            assert write["profile_write_count"] == 1
            assert write["active_current_ids"] == [write["current_memory_id"]]
            assert write["historical_current_ids"] == []
            assert memory.session_profile["likes"] == [row["write_value"]]
            assert memory.session_profile["dislikes"] == []

            correction = p4i.remember_explicit_current_preference_p4(
                memory,
                row["correction_input"],
                timestamp=f"2026-09-21T10:01:0{index}+08:00",
            )
            assert correction["status"] == "typed_current_preference_written", row["id"]
            assert correction["scope"] == row["scope"]
            assert correction["scope_source"] == "inherited_unique_active_old_value"
            assert correction["profile_write_count"] == 2
            assert correction["previous_current_memory_id"] == write["current_memory_id"]
            assert correction["current_memory_id"] in correction["active_current_ids"]
            assert write["current_memory_id"] in correction["historical_current_ids"]
            assert correction["history_preserved"] is True
            assert correction["negative_old_memory_id"]
            assert memory.session_profile["likes"] == [row["new_value"]]
            assert memory.session_profile["dislikes"] == [row["old_value"]]
            assert memory._last_profile_state_shadow["answer_use_authorized"] is False

            payload = memory.profile_col.get(include=["documents", "metadatas"])
            assert len(payload["ids"]) == 3
            assert all(
                all(isinstance(value, (str, int, float, bool)) for value in metadata.values())
                for metadata in payload["metadatas"]
            )
            current = next(
                metadata
                for memory_id, metadata in zip(payload["ids"], payload["metadatas"])
                if memory_id == correction["current_memory_id"]
            )
            for field in _contract()["required_provenance_fields"]:
                assert current.get(field), (row["id"], field)
            assert current["predicate"] == p4i.current_preference_predicate(row["scope"])
            assert current["preference_semantics"] == "current_preference"


def test_unrelated_preference_scopes_remain_active_together():
    case = _contract()["scope_isolation_case"]
    with tempfile.TemporaryDirectory(prefix="uruha_p4_i_scope_") as tempdir:
        memory = _memory(_collection(tempdir, "p4_i_scope"))
        first = p4i.remember_explicit_current_preference_p4(
            memory, case["first_input"], timestamp="2026-09-21T11:00:00+08:00"
        )
        second = p4i.remember_explicit_current_preference_p4(
            memory, case["second_input"], timestamp="2026-09-21T11:01:00+08:00"
        )
        assert set(second["active_current_ids"]) == {
            first["current_memory_id"],
            second["current_memory_id"],
        }
        assert second["historical_current_ids"] == []
        assert memory.session_profile["likes"] == [case["second_value"], case["first_value"]]


def test_all_frozen_negative_cases_delegate_to_existing_writer(monkeypatch):
    calls = []
    monkeypatch.setattr(
        p4i,
        "_ORIGINAL_REMEMBER_PROFILE_FACTS",
        lambda self, user_input: calls.append(user_input),
    )
    memory = type("Memory", (), {})()
    for row in _contract()["negative_cases"]:
        result = p4i.remember_profile_facts_with_current_preference_p4(memory, row["input"])
        assert result is None
        assert memory._last_multilingual_current_preference_p4["selected"] is False, row["id"]
    assert calls == [row["input"] for row in _contract()["negative_cases"]]


def test_selected_typed_write_failure_is_visible_and_does_not_double_write(monkeypatch):
    calls = []
    monkeypatch.setattr(
        p4i,
        "_ORIGINAL_REMEMBER_PROFILE_FACTS",
        lambda self, user_input: calls.append(user_input),
    )
    monkeypatch.setattr(
        p4i,
        "remember_explicit_current_preference_p4",
        lambda self, user_input: (_ for _ in ()).throw(RuntimeError("write failed")),
    )
    memory = type("Memory", (), {})()
    text = _contract()["sequences"][0]["write_input"]
    assert p4i.remember_profile_facts_with_current_preference_p4(memory, text) is None
    assert calls == []
    audit = memory._last_multilingual_current_preference_p4
    assert audit["status"] == "typed_write_failed"
    assert audit["reason"] == "RuntimeError"
    assert audit["raw_dialogue_persisted"] is False


def test_materialized_graph_node_is_memory_stage_and_contains_no_raw_dialogue():
    payload = {
        "schema": p4i.SCHEMA,
        "status": "typed_current_preference_written",
        "selected": True,
        "act": "write",
        "language": "en",
        "scope": "drink",
        "current_value": "sencha",
        "current_memory_id": "current",
        "previous_current_memory_id": None,
        "negative_old_memory_id": None,
        "active_current_ids": ["current"],
        "historical_current_ids": [],
        "history_preserved": False,
        "answer_use_authorized": False,
        "raw_dialogue_persisted": False,
    }
    result = {
        "logic": {},
        "memory_runtime": {p4i.LABEL: payload},
        "runtime_trace": {
            "blackboard": [
                {"stage": "memory", "label": "memory_updates", "payload": {}},
                {"stage": "surface", "label": "utterance", "payload": {}},
            ]
        },
    }
    p4i.materialize_multilingual_current_preference_p4(result)
    node = next(row for row in result["runtime_trace"]["blackboard"] if row["label"] == p4i.LABEL)
    assert node["stage"] == "memory"
    assert node["payload"]["answer_use_authorized"] is False
    assert node["payload"]["raw_dialogue_persisted"] is False
    assert "I prefer sencha" not in repr(node)


def test_product_entry_installs_p4_i_after_p4_h_without_editing_core_runtime():
    entry = (ROOT / "uruha_web_ui_product.py").read_text(encoding="utf-8")
    assert entry.index("install_explicit_preference_acknowledgement_p4()") < entry.index(
        "install_multilingual_current_preference_p4()"
    )
    assert "profile_state_shadow" not in "".join(
        [
            __import__("inspect").getsource(MemoryManager._build_working_memory),
            __import__("inspect").getsource(MemoryManager.query_all_layers),
        ]
    )
