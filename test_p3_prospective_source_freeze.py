from __future__ import annotations

import json
from pathlib import Path

import pytest

import p3_prospective_source_freeze as freeze
from p3_product_comparison import P3ContractError


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "datasets/p3_prospective_developer_source_v2.json"
PARENT = ROOT / "datasets/p3_developer_smoke_source_v1.json"


def write_variant(tmp_path, mutate):
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    mutate(data)
    path = tmp_path / "datasets" / SOURCE.name
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def test_actual_source_is_source_only_unique_and_future_turn_locked():
    result = freeze.validate_source(SOURCE, PARENT)
    assert result["status"] == "prospective_source_only_ready_to_freeze"
    assert result["counts"]["cases"] == 3
    assert result["counts"]["turns"] == 12
    assert result["counts"]["sessions"] == 6
    assert result["counts"]["languages"] == {"en": 1, "ja": 1, "zh": 1}
    assert result["counts"]["allowlisted_views"] == 12
    assert all(result["checks"].values())
    assert result["annotations_created_or_accessed"] == 0
    assert result["generation_calls"] == result["network_calls"] == 0
    by_case = {}
    for row in result["turn_visibility_manifest"]:
        by_case.setdefault(row["case_id"], []).append(row)
    for rows in by_case.values():
        assert [len(row["visible_turn_ids"]) for row in rows] == [1, 2, 3, 4]
        assert [len(row["locked_future_turn_ids"]) for row in rows] == [3, 2, 1, 0]


def test_parent_text_reuse_is_rejected_even_if_hash_is_updated(tmp_path):
    parent = json.loads(PARENT.read_text(encoding="utf-8"))
    reused = parent["cases"][0]["turns"][0]["content"]

    def mutate(data):
        turn = data["cases"][0]["turns"][0]
        turn["content"] = reused
        turn["content_sha256"] = freeze._digest_text(reused)

    variant = write_variant(tmp_path, mutate)
    with pytest.raises(P3ContractError) as exc:
        freeze.validate_source(variant, PARENT)
    assert exc.value.code == "p3_b33_parent_text_reuse"


@pytest.mark.parametrize("key", ["gold_reply", "rubric", "score", "condition_preference", "annotation"])
def test_case_payload_cannot_contain_answer_or_evaluation_fields(tmp_path, key):
    def mutate(data):
        data["cases"][0][key] = "forbidden"

    variant = write_variant(tmp_path, mutate)
    with pytest.raises(P3ContractError) as exc:
        freeze.validate_source(variant, PARENT)
    assert exc.value.code == "p3_b33_forbidden_case_payload"


def test_content_hash_session_boundary_and_call_status_are_enforced(tmp_path):
    bad_hash = write_variant(
        tmp_path / "hash",
        lambda data: data["cases"][0]["turns"][0].update(content_sha256="0" * 64),
    )
    with pytest.raises(P3ContractError) as exc:
        freeze.validate_source(bad_hash, PARENT)
    assert exc.value.code == "p3_b33_turn_hash_invalid"

    bad_session = write_variant(
        tmp_path / "session",
        lambda data: data["cases"][0]["sessions"][1].update(
            starts_at_turn_id=data["cases"][0]["turns"][1]["turn_id"]
        ),
    )
    with pytest.raises(P3ContractError) as exc:
        freeze.validate_source(bad_session, PARENT)
    assert exc.value.code == "p3_b33_session_boundary_invalid"

    bad_calls = write_variant(
        tmp_path / "calls",
        lambda data: data["source_only_boundary"].update(real_model_calls=1),
    )
    with pytest.raises(P3ContractError) as exc:
        freeze.validate_source(bad_calls, PARENT)
    assert exc.value.code == "p3_b33_source_boundary_invalid"
