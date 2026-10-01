import hashlib
import json
from pathlib import Path

import p3_b52_metadata_only_source_freeze as v1


ROOT = Path(__file__).resolve().parent
RESULT = ROOT / "research" / "p3_b52_metadata_only_source_selection_v4_release_2026-09-17.json"


def load_result():
    return json.loads(RESULT.read_text(encoding="utf-8"))


def test_result_bindings_and_failures_are_content_addressed():
    result = load_result()
    for binding in result["bindings"].values():
        path = ROOT / binding["path"]
        assert path.is_file()
        assert hashlib.sha256(path.read_bytes()).hexdigest() == binding["sha256"]


def test_preselection_receipt_recomputes_from_content_blind_metadata():
    result = load_result()
    selected = result["selected_source"]
    pre = result["preselection"]
    material = {
        "schema": "uruha_p3_b52_atom_preselection_receipt_v3",
        "candidate_set_hash": pre["candidate_set_hash"],
        "selection_seed": pre["selection_seed"],
        "selected_source_id": selected["source_id"],
        "selected_video_id": selected["video_id"],
        "selected_published_at": selected["published_at"],
        "selection_score": pre["selection_score"],
    }
    assert v1.sha256_bytes(v1.canonical_json(material).encode("utf-8")) == (
        pre["preselection_receipt_hash"]
    )


def test_semantic_postcheck_result_hash_recomputes_and_no_replacement_occurred():
    result = load_result()
    selected = result["selected_source"]
    pre = result["preselection"]
    post = result["postselection"]
    material = {
        "schema": post["semantic_result_payload_schema"],
        "status": result["status"],
        "preselection_receipt_hash": pre["preselection_receipt_hash"],
        "selected_source_id": selected["source_id"],
        "selected_video_id": selected["video_id"],
        "selected_published_at": selected["published_at"],
        "selected_duration_seconds": selected["duration_seconds"],
        "postcheck_accepted": post["postcheck_accepted"],
        "postcheck_reasons": post["postcheck_reasons"],
        "automatic_replacement_performed": post[
            "automatic_replacement_performed"
        ],
    }
    assert v1.sha256_bytes(v1.canonical_json(material).encode("utf-8")) == (
        post["semantic_result_hash"]
    )
    assert post["automatic_replacement_performed"] is False


def test_selected_source_passes_frozen_metadata_limits_and_is_new():
    result = load_result()
    selected = result["selected_source"]
    base = v1.load_contract()
    exclusions = v1.load_json(
        ROOT / base["bindings"]["known_source_exclusions"]["path"]
    )
    assert selected["publisher_channel_id"] == base["target"]["publisher_channel_id"]
    assert base["candidate_window"]["minimum_duration_seconds"] <= selected[
        "duration_seconds"
    ] <= base["candidate_window"]["maximum_duration_seconds"]
    assert selected["availability"] == "public"
    assert selected["live_status"] == "was_live"
    assert selected["video_id"] not in exclusions["excluded_video_ids"]


def test_release_contains_no_content_or_formal_execution_evidence():
    result = load_result()
    counts = result["evidence_counts"]
    assert counts == {
        "atom_retrieval_count": 1,
        "selected_id_postcheck_count": 1,
        "stored_title_count": 0,
        "stored_description_count": 0,
        "stored_transcript_count": 0,
        "target_segment_access_count": 0,
        "future_response_access_count": 0,
        "gold_annotation_count": 0,
        "model_call_count": 0,
        "formal_m56_artifact_change_count": 0,
    }
    forbidden = {"title", "description", "transcript", "behavior_label", "gold"}
    assert forbidden.isdisjoint(set(result["selected_source"]))
