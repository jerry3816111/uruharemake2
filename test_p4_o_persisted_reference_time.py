import datetime
import json
from pathlib import Path
import tempfile

import chromadb
import pytest

import uruha_multilingual_current_preference_p4 as p4i
import uruha_preference_scope_canonicalization_p4 as p4l
import uruha_source_bound_japanese_value_surface_p4 as p4n
import uruha_persisted_reference_time_p4 as p4o


ROOT = Path(__file__).resolve().parent
CONTRACT = ROOT / "configs" / "p4_o_persisted_reference_time_contract_v1.json"


def _contract():
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


class _Memory:
    def __init__(self, collection):
        self.profile_col = collection
        self.session_profile = {"name": None, "likes": [], "dislikes": [], "favorites": []}
        self._last_profile_state_shadow = {
            "status": "not_refreshed",
            "shadow_only": True,
            "affects_working_memory": False,
            "answer_use_authorized": False,
        }

    def _refresh_profile_state_shadow(self, *, reference_time=None):
        self._last_profile_state_shadow = {
            "status": "refreshed_for_test",
            "reference_time": reference_time,
            "shadow_only": True,
            "affects_working_memory": False,
            "answer_use_authorized": False,
        }


@pytest.fixture
def canonical_writer(monkeypatch):
    original_extract = p4i.extract_explicit_current_preference_p4
    original_typed_record = p4i._typed_record
    monkeypatch.setattr(p4l, "_ORIGINAL_TYPED_RECORD", original_typed_record)
    monkeypatch.setattr(
        p4i,
        "extract_explicit_current_preference_p4",
        lambda text: p4l.canonicalize_preference_scope_extraction_p4(
            original_extract(text)
        ),
    )
    monkeypatch.setattr(
        p4i,
        "_typed_record",
        p4l.typed_record_with_preference_scope_canonicalization_p4,
    )


def _payload(collection):
    return collection.get(include=["documents", "metadatas"])


def test_real_persisted_chroma_default_reference_time_delivers_frozen_surface_without_mutation(
    canonical_writer,
):
    case = _contract()["development_case"]
    with tempfile.TemporaryDirectory(prefix="uruha_p4_o_after_") as tempdir:
        collection = chromadb.PersistentClient(path=tempdir).get_or_create_collection(
            "p4_o_after"
        )
        memory = _Memory(collection)
        write = p4i.remember_explicit_current_preference_p4(
            memory,
            case["write_input"],
        )
        before = _payload(collection)

        result = p4o.build_with_persisted_reference_time_p4(
            case["recall_input"],
            collection,
        )
        after = _payload(collection)

        assert write["status"] == "typed_current_preference_written"
        assert write["scope"] == case["expected_scope"]
        assert result["status"] == "resolved_unique_active_typed_current_preference"
        assert result["localized_value_jp"] == case["value"]
        assert result["selected_core_jp"] == case["expected_surface"]
        assert result["value_surface_strategy"] == case["expected_strategy"]
        assert result["active_memory_id"] == write["current_memory_id"]
        assert result["profile_write_count"] == 0
        assert result["model_call_added"] is False
        assert after == before


@pytest.mark.parametrize(
    "supplied",
    [None, "2026-09-22T05:30:00.123456+08:00"],
)
def test_one_identical_non_null_reference_time_reaches_both_reads(monkeypatch, supplied):
    observed = []

    def base(_input, _collection, *, reference_time=None):
        observed.append(("base", reference_time))
        return {"status": "unsupported_active_value_localization"}

    def upgrade(result, _collection, *, reference_time=None):
        observed.append(("upgrade", reference_time))
        return result

    monkeypatch.setattr(p4n, "_BASE_BUILD", base)
    monkeypatch.setattr(p4n, "_upgrade_unsupported_contract", upgrade)
    p4o.build_with_persisted_reference_time_p4(
        "What is my current drink preference?",
        object(),
        reference_time=supplied,
    )

    base_time = observed[0][1]
    upgrade_time = observed[1][1]
    assert base_time == upgrade_time
    assert base_time is not None
    assert datetime.datetime.fromisoformat(base_time)
    if supplied is not None:
        assert base_time == supplied


def test_explicit_reference_time_preserves_active_then_expired_semantics(canonical_writer):
    case = _contract()["development_case"]
    with tempfile.TemporaryDirectory(prefix="uruha_p4_o_validity_") as tempdir:
        collection = chromadb.PersistentClient(path=tempdir).get_or_create_collection(
            "p4_o_validity"
        )
        memory = _Memory(collection)
        write = p4i.remember_explicit_current_preference_p4(
            memory,
            case["write_input"],
            timestamp="2026-09-22T05:00:00+08:00",
        )
        payload = _payload(collection)
        metadata = dict(payload["metadatas"][0])
        metadata["valid_until"] = "2026-09-22T06:00:00+08:00"
        collection.update(
            ids=[write["current_memory_id"]],
            metadatas=[metadata],
        )

        active = p4o.build_with_persisted_reference_time_p4(
            case["recall_input"],
            collection,
            reference_time="2026-09-22T05:30:00+08:00",
        )
        expired = p4o.build_with_persisted_reference_time_p4(
            case["recall_input"],
            collection,
            reference_time="2026-09-22T06:00:00.000001+08:00",
        )

        assert active["answer_use_authorized"] is True
        assert active["localized_value_jp"] == case["value"]
        assert active["validity_reason"] == "active"
        assert expired["status"] == "no_active_typed_current_preference"
        assert expired["answer_use_authorized"] is False
        assert case["value"] not in repr(expired)


def test_development_and_exposed_product_values_are_not_added_to_finite_map():
    assert "ごぼう茶" not in p4n.p4j._VALUE_SURFACE_JP
    assert "そば茶" not in p4n.p4j._VALUE_SURFACE_JP


def test_product_installs_p4_o_after_released_p4_n():
    source = (ROOT / "uruha_web_ui_product_p4_o.py").read_text(encoding="utf-8")
    assert source.index("import uruha_web_ui_product as _product") < source.index(
        "install_persisted_reference_time_p4()"
    )
    assert "RUNTIME = _product.RUNTIME" in source
