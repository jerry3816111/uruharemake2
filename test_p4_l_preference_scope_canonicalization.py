import json
from pathlib import Path
import tempfile

import chromadb

import uruha_multilingual_current_preference_p4 as p4i
import uruha_preference_scope_canonicalization_p4 as p4l
from uruha_brain_mac import MemoryManager


ROOT = Path(__file__).resolve().parent
CONTRACT = ROOT / "configs" / "p4_l_preference_scope_canonicalization_contract_v1.json"


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
    memory._refresh_profile_state_shadow = lambda reference_time=None: None
    return memory


def test_supported_explicit_aliases_project_to_one_canonical_scope_without_value_change():
    for row in _contract()["positive_inputs"]:
        before = p4i.extract_explicit_current_preference_p4(row["input"])
        after = p4l.canonicalize_preference_scope_extraction_p4(before)
        assert before["scope"] == row["expected_original_scope"], row["id"]
        assert after["scope"] == row["expected_canonical_scope"]
        assert after["current_value"] == row["expected_value"]
        assert after["current_value_sha256"] == before["current_value_sha256"]
        assert after["scope_source"] == "canonical_alias_projection"
        audit = after[p4l.LABEL]
        assert audit["canonicalization_applied"] is True
        assert audit["alias_id"] == row["expected_alias_id"]
        assert audit["source_scope_alias_sha256"]
        assert audit["raw_dialogue_persisted"] is False
        assert row["input"] not in repr(after)


def test_unchanged_and_nonselected_scopes_are_not_inferred_or_remapped():
    for row in _contract()["nonselected_or_unchanged_cases"]:
        extraction = {
            "schema": p4i.SCHEMA,
            "selected": row.get("selected", True),
            "status": "explicit_current_preference_extracted",
            "act": "write",
            "language": row["language"],
            "scope": row["scope"],
            "scope_source": row["scope_source"],
            "input_sha256": "a" * 64,
            "current_value": "value",
            "current_value_sha256": "b" * 64,
            "raw_dialogue_persisted": False,
        }
        result = p4l.canonicalize_preference_scope_extraction_p4(extraction)
        assert result["scope"] == row["scope"], row["id"]
        assert result["scope_source"] == row["scope_source"]
        assert result[p4l.LABEL]["canonicalization_applied"] is False


def test_product_extractor_writes_canonical_scope_and_preserves_source_provenance(monkeypatch):
    base_extract = p4i.extract_explicit_current_preference_p4
    monkeypatch.setattr(
        p4i,
        "extract_explicit_current_preference_p4",
        lambda text: p4l.canonicalize_preference_scope_extraction_p4(base_extract(text)),
    )
    row = _contract()["positive_inputs"][0]
    with tempfile.TemporaryDirectory(prefix="uruha_p4_l_scope_") as tempdir:
        collection = chromadb.PersistentClient(path=tempdir).get_or_create_collection("scope")
        memory = _memory(collection)
        result = p4i.remember_explicit_current_preference_p4(
            memory, row["input"], timestamp="2026-09-21T14:00:00+08:00"
        )
        assert result["scope"] == "drink"
        assert result[p4l.LABEL]["canonicalization_applied"] is True
        payload = collection.get(include=["metadatas", "documents"])
        assert payload["metadatas"][0]["preference_scope"] == "drink"
        assert payload["metadatas"][0]["predicate"] == "current_preference_scope:218ae6b44966c8a9"
        assert payload["metadatas"][0]["source_language"] == row["expected_language"]
        assert payload["metadatas"][0]["source_input_sha256"]
        assert payload["metadatas"][0]["value"] == row["expected_value"]


def test_materialized_p4_l_graph_node_is_memory_stage_and_raw_free():
    payload = {
        "schema": p4i.SCHEMA,
        "selected": True,
        "status": "typed_current_preference_written",
        "current_memory_id": "current",
        "raw_dialogue_persisted": False,
        p4l.LABEL: {
            "schema": p4l.SCHEMA,
            "canonicalization_applied": True,
            "alias_id": "drink:zh-Hant:v1",
            "source_scope_alias_sha256": "a" * 64,
            "canonical_scope": "drink",
            "source_language": "zh",
            "raw_dialogue_persisted": False,
        },
    }
    result = {
        "logic": {p4i.LABEL: payload},
        "memory_runtime": {p4i.LABEL: payload},
        "runtime_trace": {"blackboard": [{"stage": "memory", "label": p4i.LABEL, "payload": payload}]},
    }
    p4l.materialize_preference_scope_canonicalization_p4(result)
    node = next(row for row in result["runtime_trace"]["blackboard"] if row["label"] == p4l.LABEL)
    assert node["stage"] == "memory"
    assert node["payload"]["current_memory_id"] == "current"
    assert node["payload"]["raw_dialogue_persisted"] is False


def test_product_entry_installs_p4_l_between_p4_i_and_p4_j():
    entry = (ROOT / "uruha_web_ui_product.py").read_text(encoding="utf-8")
    assert entry.index("install_multilingual_current_preference_p4()") < entry.index(
        "install_preference_scope_canonicalization_p4()"
    ) < entry.index("install_typed_current_preference_recall_p4()")
