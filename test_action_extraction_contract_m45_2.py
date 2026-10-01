from copy import deepcopy
import pytest
import uruha_action_extraction_contract_m45_2 as m
import uruha_actionable_help_delivery_m45 as base
from uruha_actionable_help_eval_m45 import fixture


def test_dynamic_schema_only_allows_exact_current_sources_without_mutation():
    p, sources, _ = fixture()
    before = deepcopy(base.REVIEW_SCHEMA)
    schema = m.constrained_review_schema({"sources": sources})
    assert schema["properties"]["source_id"]["enum"] == [sources[0]["id"]]
    assert schema["properties"]["source_span"]["enum"] == [sources[0]["text"]]
    assert schema["properties"]["checks"] == before["properties"]["checks"]
    for key in ("object_jp", "verb_jp", "completion_jp"):
        assert "enum" not in schema["properties"][key]
    assert base.REVIEW_SCHEMA == before


def test_assistant_sources_cannot_enter_decoding_choices():
    with pytest.raises(ValueError):
        m.constrained_review_schema({"sources": [{"id": "x", "kind": "assistant_reply", "text": "invented"}]})


def test_metadata_constraints_apply_to_review_only_without_extra_call(monkeypatch):
    seen = []
    def transport(system, payload, schema, deadline, metrics):
        seen.append(schema)
        return {}
    monkeypatch.setattr(m, "_ORIGINAL_NATIVE", transport)
    _, sources, _ = fixture()
    metrics = {}
    m.constrained_native("", {"sources": sources}, base.PLAN_SCHEMA, 100, metrics)
    assert seen[-1] is base.PLAN_SCHEMA and not metrics
    m.constrained_native("", {"sources": sources}, base.REVIEW_SCHEMA, 100, metrics)
    assert len(seen) == 2 and seen[-1] is not base.REVIEW_SCHEMA
    assert metrics["source_decoding_constraint_m45_2"]["semantic_checks_relaxed"] is False


@pytest.mark.parametrize("noun", ["本", "紙"])
def test_one_kanji_object_is_a_format_not_semantic_failure(noun):
    p, sources, _ = fixture()
    p.update(object_jp=noun, instruction_jp=f"{noun}を一つだけ取り出してみよ。", verb_jp="取り出して")
    assert "invalid_object_jp" in m._ORIGINAL_STRUCTURAL(p, sources)
    assert "invalid_object_jp" not in m.structural_check(p, sources)
    p["verb_jp"] = "投げる"
    assert "unrealized_verb_jp" in m.structural_check(p, sources)


def test_other_invalid_objects_and_semantic_failures_are_not_relaxed():
    p, sources, review = fixture("empty_promise")
    assert m.structural_check(p, sources) == m._ORIGINAL_STRUCTURAL(p, sources)
    assert not base.inspect_action_delivery(p, sources, review)["delivered"]
    for value in ("", "A", "本" * 71, "一つ"):
        p["object_jp"] = value
        assert m.structural_check(p, sources) == m._ORIGINAL_STRUCTURAL(p, sources)
