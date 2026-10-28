import inspect
import json
from pathlib import Path

import pytest

import uruha_source_bound_japanese_value_surface_p4 as p4n
import uruha_typed_current_preference_recall_p4 as p4j


ROOT = Path(__file__).resolve().parent
CONTRACT = ROOT / "configs" / "p4_n_source_bound_japanese_identity_localization_contract_v1.json"
QUERY = "What is my current drink preference?"


def _contract():
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def _row(value, *, source_language="ja", overrides=None):
    metadata = {
        "preference_semantics_schema": "uruha_current_preference_typed_state_p4_v1",
        "preference_semantics": "current_preference",
        "preference_scope": "drink",
        "value": value,
        "source_language": source_language,
        "source_kind": "explicit_current_user_utterance",
        "epistemic_status": "observed_explicit_user_self_report",
        "source_input_sha256": "a" * 64,
        "preference_scope_sha256": "b" * 64,
    }
    metadata.update(overrides or {})
    return {"memory_id": "p4-n-active", "metadata": metadata}


def _install_active(monkeypatch, row):
    monkeypatch.setattr(
        p4n.p4i,
        "_current_preference_rows",
        lambda *_args, **_kwargs: {
            "active": [row],
            "historical": [],
            "decisions": {row["memory_id"]: {"partition": "eligible", "reason": "active"}},
        },
    )


@pytest.mark.parametrize("fixture", _contract()["positive_development_fixtures"])
def test_exact_japanese_provenance_can_use_bounded_identity_surface(monkeypatch, fixture):
    _install_active(monkeypatch, _row(fixture["value"]))
    result = p4n.build_source_bound_japanese_value_surface_p4(QUERY, object())
    assert result["status"] == "resolved_unique_active_typed_current_preference"
    assert result["answer_use_authorized"] is True
    assert result["localized_value_jp"] == fixture["value"]
    assert result["value_surface_strategy"] == fixture["expected_strategy"]
    assert result["identity_localization_applied"] is True
    assert result[p4n.LABEL]["normalized_codepoint_count"] == len(fixture["value"])
    assert result["model_call_added"] is False
    assert result["profile_write_count"] == 0
    assert result["episode_write_changed"] is False


@pytest.mark.parametrize("fixture", _contract()["negative_development_fixtures"])
def test_unknown_value_fails_closed_outside_source_and_script_boundary(monkeypatch, fixture):
    _install_active(
        monkeypatch,
        _row(fixture["value"], source_language=fixture.get("source_language", "ja")),
    )
    result = p4n.build_source_bound_japanese_value_surface_p4(QUERY, object())
    assert result["status"] == fixture["expected_status"]
    assert result["answer_use_authorized"] is False
    assert fixture["value"] not in repr(result)


@pytest.mark.parametrize(
    "field,value",
    [
        ("source_kind", "model_inference"),
        ("epistemic_status", "inferred"),
        ("preference_semantics_schema", "unknown_schema"),
        ("preference_semantics", "inferred_preference"),
    ],
)
def test_identity_surface_requires_all_frozen_provenance(monkeypatch, field, value):
    _install_active(monkeypatch, _row("玄米茶", overrides={field: value}))
    result = p4n.build_source_bound_japanese_value_surface_p4(QUERY, object())
    assert result["status"] == "unsupported_active_value_localization"
    assert result["answer_use_authorized"] is False
    assert "玄米茶" not in repr(result)


def test_existing_finite_map_still_precedes_identity_rule(monkeypatch):
    _install_active(monkeypatch, _row("麦茶"))
    result = p4n.build_source_bound_japanese_value_surface_p4(QUERY, object())
    assert result["localized_value_jp"] == "麦茶"
    assert result["value_surface_strategy"] == "finite_localization_map"
    assert result["identity_localization_applied"] is False


def test_p4_m_exposed_value_was_not_added_to_finite_map():
    assert "柚子茶" not in p4j._VALUE_SURFACE_JP
    assert p4j._localize_value("柚子茶") == ""


def test_product_entry_installs_adapter_after_p4_j_without_rewriting_p4_j():
    source = (ROOT / "uruha_web_ui_product.py").read_text(encoding="utf-8")
    assert source.index("install_typed_current_preference_recall_p4()") < source.index(
        "install_source_bound_japanese_value_surface_p4()"
    )
    assert inspect.getsourcefile(p4n) == str(ROOT / "uruha_source_bound_japanese_value_surface_p4.py")
