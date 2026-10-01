from __future__ import annotations

import json
from pathlib import Path

import pytest

from p3_prospective_v3_data_freeze import FreezeError, build_validation


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "datasets/p3_prospective_developer_source_v3.json"
ANNOTATIONS = ROOT / "datasets/p3_prospective_developer_annotations_v3.json"


def test_actual_v3_source_and_predeclared_rubric_are_ready_before_generation():
    result = build_validation(SOURCE, ANNOTATIONS, ROOT)
    assert result["status"] == "prospective_v3_data_ready_to_freeze"
    assert result["case_ids"] == [
        "p3-prospective-v3-growing-comments-zh",
        "p3-prospective-v3-concert-excitement-en",
        "p3-prospective-v3-team-pending-ja",
    ]
    assert len(result["turn_ids"]) == len(result["turn_visibility_manifest"]) == 12
    assert result["normalized_prior_overlap_count"] == 0
    assert result["real_model_calls"] == result["network_calls"] == 0
    assert result["annotations_exposed_to_generation"] == 0
    assert all(result["checks"].values())


def test_each_visibility_row_locks_only_future_turns():
    result = build_validation(SOURCE, ANNOTATIONS, ROOT)
    for index, row in enumerate(result["turn_visibility_manifest"]):
        case_index = index // 4
        turn_index = index % 4
        assert len(row["visible_turn_ids"]) == turn_index + 1
        assert len(row["locked_future_turn_ids"]) == 3 - turn_index
        assert row["annotation_visible_to_generation"] is False
        assert all(f"v3-0{case_index + 1}" in turn_id for turn_id in row["visible_turn_ids"] + row["locked_future_turn_ids"])


def test_source_contains_no_annotation_or_output_keys():
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    serialized = json.dumps(source, ensure_ascii=False).lower()
    for forbidden in ('"reply"', '"output"', '"answer"', '"score"', '"winner"', '"gold"', '"rubric"', '"annotation"'):
        assert forbidden not in serialized


def test_annotation_source_hash_or_future_evidence_mutation_fails(tmp_path):
    annotations = json.loads(ANNOTATIONS.read_text(encoding="utf-8"))
    annotations["source_manifest_sha256"] = "0" * 64
    changed = tmp_path / "bad-hash.json"
    changed.write_text(json.dumps(annotations, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(FreezeError, match="annotation_source_hash_mismatch"):
        build_validation(SOURCE, changed, ROOT)

    annotations = json.loads(ANNOTATIONS.read_text(encoding="utf-8"))
    annotations["cases"][0]["turns"][0]["evidence_turn_ids"].append("p3-prospective-v3-01-u4")
    changed = tmp_path / "future.json"
    changed.write_text(json.dumps(annotations, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(FreezeError, match="annotation_evidence_or_act_invalid"):
        build_validation(SOURCE, changed, ROOT)


def test_product_snapshot_or_generation_flag_mutation_fails(tmp_path):
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    source["product_snapshot"]["post_source_product_tuning_allowed_before_first_run"] = True
    changed_source = tmp_path / "source.json"
    changed_source.write_text(json.dumps(source, ensure_ascii=False), encoding="utf-8")
    annotations = json.loads(ANNOTATIONS.read_text(encoding="utf-8"))
    import hashlib
    annotations["source_manifest_sha256"] = hashlib.sha256(changed_source.read_bytes()).hexdigest()
    changed_annotations = tmp_path / "ann.json"
    changed_annotations.write_text(json.dumps(annotations, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(FreezeError, match="product_snapshot_mismatch"):
        build_validation(changed_source, changed_annotations, ROOT)

