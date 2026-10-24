import json
from pathlib import Path
import tempfile

import chromadb

import uruha_multilingual_current_preference_p4 as p4i
import uruha_preference_scope_canonicalization_p4 as p4l
from uruha_brain_mac import MemoryManager


ROOT = Path(__file__).resolve().parent
CONTRACT = ROOT / "configs" / "p4_m_cross_language_correction_delivery_acceptance_v1.json"


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


def test_supported_chinese_write_and_japanese_correction_share_canonical_lineage(monkeypatch):
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    original_extract = p4i.extract_explicit_current_preference_p4
    original_typed_record = p4i._typed_record
    monkeypatch.setattr(p4l, "_ORIGINAL_TYPED_RECORD", original_typed_record)
    monkeypatch.setattr(
        p4i,
        "extract_explicit_current_preference_p4",
        lambda text: p4l.canonicalize_preference_scope_extraction_p4(original_extract(text)),
    )
    monkeypatch.setattr(p4i, "_typed_record", p4l.typed_record_with_preference_scope_canonicalization_p4)

    with tempfile.TemporaryDirectory(prefix="uruha_p4_m_before_") as tempdir:
        collection = chromadb.PersistentClient(path=tempdir).get_or_create_collection("p4_m")
        memory = _memory(collection)
        write = p4i.remember_explicit_current_preference_p4(
            memory,
            contract["session_1_write_turn"]["input"],
            timestamp="2026-09-21T17:00:00+08:00",
        )
        correction = p4i.remember_explicit_current_preference_p4(
            memory,
            contract["session_1_correction_turn"]["input"],
            timestamp="2026-09-21T17:01:00+08:00",
        )
        assert write["scope"] == correction["scope"] == "drink"
        assert write[p4l.LABEL]["alias_id"] == "drink:zh-Hant:v1"
        assert correction[p4l.LABEL]["alias_id"] == "drink:ja:v1"
        assert correction["previous_current_memory_id"] == write["current_memory_id"]
        assert correction["active_current_ids"] == [correction["current_memory_id"]]
        assert correction["historical_current_ids"] == [write["current_memory_id"]]
        assert correction["negative_old_memory_id"]
        assert correction["history_preserved"] is True
        assert memory.session_profile["likes"] == ["柚子茶"]
        assert memory.session_profile["dislikes"] == ["梅子ソーダ"]

        payload = collection.get(include=["metadatas"])
        assert len(payload["ids"]) == 3
        by_id = dict(zip(payload["ids"], payload["metadatas"]))
        assert by_id[write["current_memory_id"]]["preference_scope_alias_id"] == "drink:zh-Hant:v1"
        assert by_id[correction["current_memory_id"]]["preference_scope_alias_id"] == "drink:ja:v1"
        assert by_id[correction["current_memory_id"]]["previous_current_memory_id"] == write["current_memory_id"]
        assert by_id[correction["negative_old_memory_id"]]["correction_current_memory_id"] == correction["current_memory_id"]


def test_contract_forbids_answer_leak_retry_and_old_p4_l_case_reuse():
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert "柚子茶" not in contract["session_2_recall_turn"]["input"]
    assert contract["runtime_requirements"]["retry_count"] == 0
    assert contract["failure_policy"]["p4_l_real_case_rerun_allowed"] is False
    assert "麦茶" not in repr(contract)
